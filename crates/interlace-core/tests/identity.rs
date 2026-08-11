//! Identity must-pass matrix.
//!
//! Matrix IDs (gate grep): I1 I2 I3 I4 I5 I6 I6b

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::{name_fold_join, normalize_email};
use interlace_core::{person_merge, person_undo, resolve_run, review_resolve, PersonMergeOpts};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-id-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn ensure_source(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 't', '/t.vcf')",
            [],
        )
        .ok();
    arch.conn
        .query_row("SELECT id FROM sources LIMIT 1", [], |r| r.get(0))
        .unwrap()
}

fn insert_ident(
    arch: &interlace_core::db::Archive,
    platform: &str,
    kind: &str,
    raw: &str,
    norm: &str,
    display: Option<&str>,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![platform, kind, raw, norm, display],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn persist_card(
    arch: &mut interlace_core::db::Archive,
    uid: &str,
    fn_: &str,
    phone: Option<&str>,
    email: Option<&str>,
) {
    let source = ensure_source(arch);
    arch.conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, fn) VALUES (?1, ?2, ?3)",
            rusqlite::params![source, uid, fn_],
        )
        .unwrap();
    let cid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [fn_],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    let mut chans: Vec<(String, String, String)> = Vec::new();
    if let Some(p) = phone {
        chans.push(("phone".into(), p.into(), p.into()));
    }
    if let Some(e) = email {
        let norm = normalize_email(e).unwrap_or_else(|| e.to_lowercase());
        chans.push(("email".into(), e.into(), norm));
    }
    for (kind, raw, norm) in chans {
        arch.conn
            .execute(
                "INSERT OR IGNORE INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES ('contacts', ?1, ?2, ?3, ?4)",
                rusqlite::params![&kind, &raw, &norm, fn_],
            )
            .unwrap();
        let iid: i64 = arch
            .conn
            .query_row(
                "SELECT id FROM identities WHERE platform='contacts' AND kind=?1 AND value_normalized=?2",
                rusqlite::params![&kind, &norm],
                |r| r.get(0),
            )
            .unwrap();
        arch.conn
            .execute(
                "INSERT INTO contact_channels(contact_id, kind, value_raw, value_normalized, pref, identity_id)
                 VALUES (?1, ?2, ?3, ?4, 0, ?5)",
                rusqlite::params![cid, &kind, &raw, &norm, iid],
            )
            .unwrap();
        arch.conn
            .execute(
                "INSERT OR IGNORE INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
                 VALUES (?1, ?2, 'takeout_vcard', 1.0, 'system')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
    }
}

fn live_persons_for(arch: &interlace_core::db::Archive, kind: &str, norm: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(DISTINCT p.id) FROM identities i
             JOIN person_identities pi ON pi.identity_id = i.id
             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
             WHERE i.kind = ?1 AND i.value_normalized = ?2",
            rusqlite::params![kind, norm],
            |r| r.get(0),
        )
        .unwrap()
}

/// Already-linked WhatsApp `display_name` person (no parser).
fn persist_wa_display_person(
    arch: &interlace_core::db::Archive,
    display: &str,
    norm: &str,
) -> (i64, i64) {
    let iid = insert_ident(
        arch,
        "whatsapp",
        "display_name",
        display,
        norm,
        Some(display),
    );
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [display],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![pid, iid],
        )
        .unwrap();
    (pid, iid)
}

fn live_non_self(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND is_self = 0",
    )
}

fn open_reviews(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'",
    )
}

#[test]
fn identity_i1_same_e164_wa_and_contacts_automerge() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+90 532 111 22 33",
        "+905321112233",
        Some("Ahmet"),
    );
    persist_card(
        &mut arch,
        "card-1",
        "Ahmet Yılmaz",
        Some("+905321112233"),
        None,
    );
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_persons_for(&arch, "phone", "+905321112233"), 1);
    assert!(
        stats.auto_person_merges >= 1 || live_persons_for(&arch, "phone", "+905321112233") == 1,
        "I1 auto-merge"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i2_same_display_name_review_not_auto() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(
        &mut arch,
        "c1",
        "Ahmet Yılmaz",
        None,
        Some("ahmet@ornek.tld"),
    );
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ahmet Yılmaz",
        "ahmet yılmaz",
        Some("Ahmet Yılmaz"),
    );
    let stats = resolve_run(&mut arch, 0).unwrap();
    let contacts_pid: i64 = arch
        .conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.platform = 'contacts' AND i.kind = 'email'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let wa_pid: i64 = arch
        .conn
        .query_row(
            "SELECT pi.person_id FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.platform = 'whatsapp' AND i.kind = 'display_name'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_ne!(
        wa_pid, contacts_pid,
        "I2 display_name must not auto-link onto the vCard person"
    );
    assert!(
        stats.review_enqueued >= 1
            || count(
                &arch,
                "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'"
            ) >= 1,
        "I2 expected review"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_wa_only_display_name_gets_own_person() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ada Yılmaz",
        "ada yılmaz",
        Some("Ada Yılmaz"),
    );
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Eren Kaya",
        "eren kaya",
        Some("Eren Kaya"),
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND is_self = 0"
        ),
        2,
        "each leftover display_name is its own person"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM merge_review_queue"),
        0,
        "no counterpart → no review"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_skip_group_title_display_name() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_ios_zip', 'g', '/g.zip')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:bookclub', 'Book Club')",
            [],
        )
        .unwrap();
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Book Club",
        "book club",
        Some("Book Club"),
    );
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Deniz Koç",
        "deniz koç",
        Some("Deniz Koç"),
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.value_normalized = 'book club'"
        ),
        0,
        "group title identity is not a person"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.display_name = 'Deniz Koç'"
        ),
        1,
        "group peer still becomes a person"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i3_same_phone_two_cards_different_names_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "bank", "Alice Bank", Some("+905321110001"), None);
    persist_card(
        &mut arch,
        "other",
        "Bob Credit",
        Some("+905321110001"),
        None,
    );
    let wa = insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+905321110001",
        "+905321110001",
        Some("Alice"),
    );
    resolve_run(&mut arch, 0).unwrap();
    let linked: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM person_identities WHERE identity_id = ?1",
            [wa],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        linked, 0,
        "I3 WA phone must not auto-link under name conflict"
    );
    assert!(
        count(
            &arch,
            "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'"
        ) >= 1,
        "I3 expected review"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i3_accept_links_unlinked_phone() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "bank", "Alice Bank", Some("+905321110001"), None);
    persist_card(
        &mut arch,
        "other",
        "Bob Credit",
        Some("+905321110001"),
        None,
    );
    let wa = insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+905321110001",
        "+905321110001",
        Some("Alice"),
    );
    resolve_run(&mut arch, 0).unwrap();
    let rid: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM merge_review_queue WHERE status='open' ORDER BY id LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    review_resolve(&mut arch, rid, true).unwrap();
    let (pid, reason): (i64, String) = arch
        .conn
        .query_row(
            "SELECT person_id, link_reason FROM person_identities WHERE identity_id = ?1",
            [wa],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(reason, "review_accepted");
    assert!(pid > 0);
    assert_eq!(
        live_non_self(&arch),
        2,
        "I3 Accept links the phone; does not merge the two contact persons"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i4_undo_merge_leaves_sender_identity_id() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let src = ensure_source(&arch);
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();
    let ia = insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+905321110010",
        "+905321110010",
        None,
    );
    let ib = insert_ident(&arch, "gmail", "email", "a@x.com", "a@x.com", None);
    resolve_run(&mut arch, 0).unwrap();
    let pa: i64 = arch
        .conn
        .query_row(
            "SELECT person_id FROM person_identities WHERE identity_id=?1",
            [ia],
            |r| r.get(0),
        )
        .unwrap();
    let pb: i64 = arch
        .conn
        .query_row(
            "SELECT person_id FROM person_identities WHERE identity_id=?1",
            [ib],
            |r| r.get(0),
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:t', 't')",
            [],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, '2024-01-01T00:00:00Z', 'second', 'text', 'hi', 'k1')",
            rusqlite::params![conv, src, run, ia],
        )
        .unwrap();
    person_merge(&mut arch, pa, pb, PersonMergeOpts { keep: None }).unwrap();
    let ev: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM identity_link_events WHERE op='merge_persons' ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    person_undo(&mut arch, ev).unwrap();
    let sender: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE idempotency_key='k1'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(sender, ia, "I4 sender_identity_id must be unchanged");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i5_wa_then_contacts_one_person_zero_phone_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+905321112233",
        "+905321112233",
        Some("Ahmet Yılmaz"),
    );
    resolve_run(&mut arch, 0).unwrap();
    persist_card(
        &mut arch,
        "vcard-ahmet",
        "Ahmet Yılmaz",
        Some("+905321112233"),
        Some("ahmet@ornek.tld"),
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_persons_for(&arch, "phone", "+905321112233"), 1);
    let phone_reviews = count(
        &arch,
        "SELECT COUNT(*) FROM merge_review_queue r
         JOIN merge_evidence e ON e.review_id = r.id
         WHERE r.status='open' AND e.evidence_type='phone_e164'",
    );
    assert_eq!(phone_reviews, 0, "I5 zero unresolved exact-phone review");
    let live = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    );
    assert_eq!(live, 1, "I5 one live person");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i6_gmail_plus_dots_googlemail_one_person() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    assert_eq!(
        normalize_email("a.b+x@gmail.com").as_deref(),
        Some("ab@gmail.com")
    );
    assert_eq!(
        normalize_email("ab@googlemail.com").as_deref(),
        Some("ab@gmail.com")
    );
    assert_eq!(
        normalize_email("a+x@gmail.com").as_deref(),
        Some("a@gmail.com")
    );
    insert_ident(
        &arch,
        "gmail",
        "email",
        "a.b+x@gmail.com",
        "ab@gmail.com",
        None,
    );
    persist_card(&mut arch, "g1", "A B", None, Some("ab@googlemail.com"));
    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        live_persons_for(&arch, "email", "ab@gmail.com"),
        1,
        "I6 D25"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_i6b_corp_plus_tag_does_not_automerge() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    assert_eq!(
        normalize_email("a+x@corp.com").as_deref(),
        Some("a+x@corp.com")
    );
    assert_ne!(
        normalize_email("a+x@corp.com"),
        normalize_email("a@corp.com")
    );
    insert_ident(
        &arch,
        "gmail",
        "email",
        "a+x@corp.com",
        "a+x@corp.com",
        None,
    );
    insert_ident(&arch, "contacts", "email", "a@corp.com", "a@corp.com", None);
    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_persons_for(&arch, "email", "a+x@corp.com"), 1);
    assert_eq!(live_persons_for(&arch, "email", "a@corp.com"), 1);
    let live = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    );
    assert_eq!(live, 2, "I6b separate persons");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_unrelated_display_names_do_not_enqueue_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(
        &mut arch,
        "c-ada",
        "Cemre Yıldız",
        None,
        Some("ada@ornek.tld"),
    );
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Berk Özdemir",
        "berk özdemir",
        Some("Berk Özdemir"),
    );
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        stats.review_enqueued, 0,
        "unrelated 2-token names must not review"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM merge_review_queue"), 0);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_surname_typo_still_enqueues_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(
        &mut arch,
        "c-typo",
        "Ahmet Yılmaz",
        None,
        Some("ahmet@ornek.tld"),
    );
    insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ahmet Yilmas",
        "ahmet yilmas",
        Some("Ahmet Yilmas"),
    );
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert!(
        stats.review_enqueued >= 1
            || count(
                &arch,
                "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'"
            ) >= 1,
        "one-letter surname typo must still review"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_exact_folded_name_contacts_and_wa_persons_enqueue_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    let (wa_pid, _) = persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let contacts_pid: i64 = arch
        .conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.platform = 'contacts' AND i.kind = 'phone'
               AND p.tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_ne!(wa_pid, contacts_pid);
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        live_non_self(&arch),
        2,
        "exact folded name must not auto-merge"
    );
    assert_eq!(stats.auto_person_merges, 0, "never auto-merge on name");
    assert!(
        stats.review_enqueued >= 1,
        "exact name_fold_join Contacts+WA must enqueue review"
    );
    assert_eq!(open_reviews(&arch), 1, "one open review row");
    let still_contacts: i64 = arch
        .conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.platform = 'contacts' AND i.kind = 'phone'
               AND p.tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let still_wa: i64 = arch
        .conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.platform = 'whatsapp' AND i.kind = 'display_name'
               AND p.tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(still_contacts, contacts_pid);
    assert_eq!(still_wa, wa_pid);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn identity_ada_contacts_vs_ali_wa_display_name_no_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    assert_ne!(name_fold_join("Ada"), name_fold_join("Ali"));
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110200"), None);
    persist_wa_display_person(&arch, "Ali", &name_fold_join("Ali"));
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(
        stats.review_enqueued, 0,
        "Ada contacts vs Ali WA display_name must not enqueue review"
    );
    assert_eq!(
        open_reviews(&arch),
        0,
        "no new open review for the Ada/Ali pair"
    );
    let _ = std::fs::remove_dir_all(&root);
}
