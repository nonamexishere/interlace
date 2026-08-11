//! N-way same-name Review: one cluster, Accept folds every Ada (#151).
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//! Matrix IDs (gate grep):
//!
//! Live non-self persons with the same `name_fold_join(display_name)` are one
//! cluster (I2: never auto-merge on name). `review_show` keeps `review` /
//! `evidence` / `left` / `right` and adds `sides` (one panel per live person).
//! Accept merges every live person in the cluster; identities move; zero
//! `messages` rows change. Do not assume left is WhatsApp.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::{name_fold_join, normalize_email};
use interlace_core::{resolve_run, review_resolve, review_resolve_selected, review_show};
use rusqlite::OptionalExtension;

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-nw-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
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

fn tombstoned_non_self(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NOT NULL AND is_self = 0",
    )
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

/// Already-linked Gmail email person (no parser). Leftover name cluster member.
fn persist_gmail_email_person(
    arch: &interlace_core::db::Archive,
    display: &str,
    email: &str,
) -> (i64, i64) {
    let norm = normalize_email(email).unwrap_or_else(|| email.to_lowercase());
    let iid = insert_ident(arch, "gmail", "email", email, &norm, Some(display));
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

fn live_person_for_identity(arch: &interlace_core::db::Archive, iid: i64) -> Option<i64> {
    arch.conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             WHERE pi.identity_id = ?1 AND p.tombstoned_at IS NULL",
            [iid],
            |r| r.get(0),
        )
        .optional()
        .unwrap()
}

struct ThreeAdas {
    contacts_iid: i64,
    wa_iid: i64,
    gmail_iid: i64,
}

fn plant_three_adas(arch: &mut interlace_core::db::Archive) -> ThreeAdas {
    persist_card(arch, "card-ada", "Ada", Some("+905321110100"), None);
    let (wa_pid, wa_iid) = persist_wa_display_person(arch, "Ada", &name_fold_join("Ada"));
    let (gmail_pid, gmail_iid) = persist_gmail_email_person(arch, "Ada", "ada@ornek.tld");
    let contacts_iid: i64 = arch
        .conn
        .query_row(
            "SELECT i.id FROM identities i
             WHERE i.platform = 'contacts' AND i.kind = 'phone'
               AND i.value_normalized = '+905321110100'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let contacts_pid =
        live_person_for_identity(arch, contacts_iid).expect("contacts Ada must be a live person");
    assert_ne!(
        wa_pid, contacts_pid,
        "plant must start with distinct Ada persons"
    );
    assert_ne!(gmail_pid, contacts_pid);
    assert_ne!(gmail_pid, wa_pid);
    ThreeAdas {
        contacts_iid,
        wa_iid,
        gmail_iid,
    }
}

struct MsgInfra {
    source_id: i64,
    run_id: i64,
}

fn ensure_msg_infra(arch: &interlace_core::db::Archive) -> MsgInfra {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let source_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [source_id],
        )
        .unwrap();
    MsgInfra {
        source_id,
        run_id: arch.conn.last_insert_rowid(),
    }
}

fn plant_dm_from(
    arch: &interlace_core::db::Archive,
    infra: &MsgInfra,
    sender: i64,
    native_id: &str,
    sent_at: &str,
    body: &str,
    key: &str,
) {
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', ?1, 'Ada')",
            [native_id],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conv, sender],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7)",
            rusqlite::params![
                conv,
                infra.source_id,
                infra.run_id,
                sender,
                sent_at,
                body,
                key
            ],
        )
        .unwrap();
}

fn sender_identity_id(arch: &interlace_core::db::Archive, key: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE idempotency_key = ?1",
            [key],
            |r| r.get(0),
        )
        .unwrap()
}

fn open_review_id(arch: &interlace_core::db::Archive) -> i64 {
    let n = open_reviews(arch);
    assert_eq!(n, 1, "expected exactly one open review, got {n}");
    arch.conn
        .query_row(
            "SELECT id FROM merge_review_queue WHERE status='open'",
            [],
            |r| r.get(0),
        )
        .unwrap()
}

fn show(arch: &interlace_core::db::Archive) -> serde_json::Value {
    review_show(arch, open_review_id(arch)).unwrap()
}

fn json_count(v: &serde_json::Value) -> i64 {
    v.as_i64()
        .or_else(|| v.as_u64().map(|n| i64::try_from(n).unwrap()))
        .unwrap_or_else(|| panic!("expected number, got {v}"))
}

fn platforms_of(panel: &serde_json::Value) -> Vec<String> {
    panel["platforms"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|v| v.as_str().unwrap_or("").to_string())
                .collect()
        })
        .unwrap_or_default()
}

fn sample_bodies(panel: &serde_json::Value) -> Vec<String> {
    panel["samples"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|s| {
                    assert!(
                        s.get("body_html").is_none(),
                        "samples must not return body_html: {s}"
                    );
                    let body = s["body_text"]
                        .as_str()
                        .unwrap_or_else(|| panic!("body_text must be a string: {s}"));
                    assert!(
                        body.chars().count() <= 240,
                        "body_text longer than 240 chars: {}",
                        body.chars().count()
                    );
                    body.to_string()
                })
                .collect()
        })
        .unwrap_or_else(|| panic!("samples must be an array, got {panel}"))
}

fn assert_panel_fields(panel: &serde_json::Value, label: &str) {
    assert!(
        panel.get("display_name").and_then(|v| v.as_str()).is_some(),
        "{label} display_name: {panel}"
    );
    assert!(
        panel.get("platforms").and_then(|v| v.as_array()).is_some(),
        "{label} platforms: {panel}"
    );
    assert!(
        panel.get("message_count").is_some(),
        "{label} message_count: {panel}"
    );
    assert!(
        panel.get("samples").and_then(|v| v.as_array()).is_some(),
        "{label} samples: {panel}"
    );
}

fn assert_kept_shell(shown: &serde_json::Value) {
    assert!(
        shown.get("review").is_some(),
        "review object must be kept: {shown}"
    );
    assert!(
        shown.get("evidence").and_then(|e| e.as_array()).is_some(),
        "evidence array must be kept: {shown}"
    );
    assert!(
        shown.get("left").map(|v| v.is_object()).unwrap_or(false),
        "expected left panel object, got {shown}"
    );
    assert!(
        shown.get("right").map(|v| v.is_object()).unwrap_or(false),
        "expected right panel object, got {shown}"
    );
    assert_panel_fields(&shown["left"], "left");
    assert_panel_fields(&shown["right"], "right");
}

fn sides_of(shown: &serde_json::Value) -> &[serde_json::Value] {
    shown["sides"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_else(|| panic!("sides must be an array, got {shown}"))
}

fn platform_rank(plats: &[String]) -> u8 {
    if plats.iter().any(|p| p == "contacts") {
        0
    } else if plats.iter().any(|p| p == "whatsapp") {
        1
    } else if plats.iter().any(|p| p == "gmail") {
        2
    } else {
        3
    }
}

fn panel_fingerprint(panel: &serde_json::Value) -> (String, Vec<String>, i64, Vec<String>) {
    let mut plats = platforms_of(panel);
    plats.sort();
    (
        panel["display_name"].as_str().unwrap_or("").to_string(),
        plats,
        json_count(&panel["message_count"]),
        sample_bodies(panel),
    )
}

fn sides_cover_platforms(sides: &[serde_json::Value], want: &[&str]) {
    let got: Vec<String> = sides.iter().flat_map(platforms_of).collect();
    for p in want {
        assert!(
            got.iter().any(|g| g == p),
            "sides platforms missing {p}: {got:?} sides={sides:?}"
        );
    }
}

fn live_person_ids_for_identities(arch: &interlace_core::db::Archive, iids: &[i64]) -> Vec<i64> {
    let mut pids = Vec::new();
    for iid in iids {
        pids.push(
            live_person_for_identity(arch, *iid)
                .unwrap_or_else(|| panic!("identity {iid} must stay linked to a live person")),
        );
    }
    pids
}

#[test]
fn review_nway_three_adas_one_review_no_auto() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    plant_three_adas(&mut arch);

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert!(
        stats.review_enqueued >= 1,
        "three same-fold Adas must enqueue review"
    );
    assert_eq!(
        open_reviews(&arch),
        1,
        "one open Review row per cluster, not one per pair"
    );
    assert_eq!(live_non_self(&arch), 3, "I2: names never auto-merge");
    assert_eq!(stats.auto_person_merges, 0, "never auto-merge on name");

    let shown = show(&arch);
    assert_kept_shell(&shown);
    let sides = sides_of(&shown);
    assert_eq!(sides.len(), 3, "one panel per live person in the cluster");
    for (i, side) in sides.iter().enumerate() {
        assert_panel_fields(side, &format!("sides[{i}]"));
    }
    sides_cover_platforms(sides, &["contacts", "whatsapp", "gmail"]);
    let ranks: Vec<u8> = sides
        .iter()
        .map(|s| platform_rank(&platforms_of(s)))
        .collect();
    assert!(
        ranks.windows(2).all(|w| w[0] <= w[1]),
        "sides order Contacts, WhatsApp, Gmail, others; got ranks {ranks:?} shown={shown}"
    );
    let side_prints: Vec<_> = sides.iter().map(panel_fingerprint).collect();
    assert!(
        side_prints.contains(&panel_fingerprint(&shown["left"])),
        "sides must include the left identity's person: left={} sides={side_prints:?}",
        shown["left"]
    );
    assert!(
        side_prints.contains(&panel_fingerprint(&shown["right"])),
        "sides must include the right person: right={} sides={side_prints:?}",
        shown["right"]
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_accept_folds_all_three() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let plant = plant_three_adas(&mut arch);
    let infra = ensure_msg_infra(&arch);
    plant_dm_from(
        &arch,
        &infra,
        plant.wa_iid,
        "whatsapp:ada-dm",
        "2024-03-01T10:00:00Z",
        "Ada dm hi",
        "k-ada-nway-dm",
    );

    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 3);

    let rid = open_review_id(&arch);
    let shown = review_show(&arch, rid).unwrap();
    let right_pid = shown["review"]["right_person_id"]
        .as_i64()
        .expect("queued same-name review has right_person_id");
    let right_live: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM persons WHERE id = ?1 AND tombstoned_at IS NULL",
            [right_pid],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(right_live, 1, "queued right_person_id must still be live");

    review_resolve(&mut arch, rid, true).unwrap();

    assert_eq!(
        live_non_self(&arch),
        1,
        "Accept merges every live person in the cluster"
    );
    assert_eq!(
        tombstoned_non_self(&arch),
        2,
        "the other two person rows are tombstoned"
    );

    let pids =
        live_person_ids_for_identities(&arch, &[plant.contacts_iid, plant.wa_iid, plant.gmail_iid]);
    assert!(
        pids.iter().all(|p| *p == pids[0]),
        "Contacts phone, WA display_name, and Gmail email must share one live person, got {pids:?}"
    );
    assert_eq!(
        pids[0], right_pid,
        "survivor is queued right_person_id when that person is still live"
    );

    assert_eq!(
        sender_identity_id(&arch, "k-ada-nway-dm"),
        plant.wa_iid,
        "identities move; zero messages rows change"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_reject_leaves_all_three() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    plant_three_adas(&mut arch);

    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 3);
    let rid = open_review_id(&arch);

    review_resolve(&mut arch, rid, false).unwrap();

    assert_eq!(live_non_self(&arch), 3, "Reject does not merge the cluster");
    assert_eq!(open_reviews(&arch), 0, "rejected cluster is no longer open");

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        open_reviews(&arch),
        0,
        "rejected cluster must not be suggested again"
    );
    assert_eq!(stats.review_enqueued, 0, "no new review after reject");
    assert_eq!(live_non_self(&arch), 3);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_ada_vs_ali_still_none() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    assert_ne!(name_fold_join("Ada"), name_fold_join("Ali"));
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ali", &name_fold_join("Ali"));

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(
        stats.review_enqueued, 0,
        "Ada vs Ali (different fold) must not enqueue review"
    );
    assert_eq!(open_reviews(&arch), 0);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_two_person_card_still_works() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    let (_, wa_iid) = persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let infra = ensure_msg_infra(&arch);
    plant_dm_from(
        &arch,
        &infra,
        wa_iid,
        "whatsapp:ada-pair",
        "2024-03-02T10:00:00Z",
        "Ada pair dm",
        "k-ada-pair-dm",
    );

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);
    assert!(stats.review_enqueued >= 1);
    assert_eq!(open_reviews(&arch), 1);

    let shown = show(&arch);
    assert_kept_shell(&shown);
    let sides = sides_of(&shown);
    assert_eq!(
        sides.len(),
        2,
        "queued pair only → sides.len() == 2, got {sides:?}"
    );
    for (i, side) in sides.iter().enumerate() {
        assert_panel_fields(side, &format!("sides[{i}]"));
    }
    sides_cover_platforms(sides, &["contacts", "whatsapp"]);
    let mut side_prints: Vec<_> = sides.iter().map(panel_fingerprint).collect();
    let mut pair_prints = vec![
        panel_fingerprint(&shown["left"]),
        panel_fingerprint(&shown["right"]),
    ];
    side_prints.sort();
    pair_prints.sort();
    assert_eq!(
        side_prints, pair_prints,
        "two-person sides must match left/right content (order independent)"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_two_contacts_one_wa_one_review() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada-a", "Ada", Some("+905321110100"), None);
    persist_card(&mut arch, "card-ada-b", "Ada", Some("+905321110101"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 3);
    assert_eq!(stats.auto_person_merges, 0);
    assert_eq!(open_reviews(&arch), 1, "one review per fold, not per pair");
    let shown = show(&arch);
    assert_eq!(sides_of(&shown).len(), 3);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_accept_subset_leaves_unchecked() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let plant = plant_three_adas(&mut arch);
    resolve_run(&mut arch, 0).unwrap();
    let rid = open_review_id(&arch);
    let shown = review_show(&arch, rid).unwrap();
    let sides = sides_of(&shown);
    let gmail_pid = sides
        .iter()
        .find(|s| platforms_of(s).iter().any(|p| p == "gmail"))
        .and_then(|s| s["person_id"].as_i64())
        .expect("gmail side has person_id");
    let keep: Vec<i64> = sides
        .iter()
        .filter_map(|s| s["person_id"].as_i64())
        .filter(|pid| *pid != gmail_pid)
        .collect();
    assert_eq!(keep.len(), 2);
    review_resolve_selected(&mut arch, rid, true, Some(&keep)).unwrap();
    assert_eq!(live_non_self(&arch), 2, "unchecked Gmail Ada stays live");
    let gmail_live = live_person_for_identity(&arch, plant.gmail_iid).expect("gmail linked");
    assert_eq!(gmail_live, gmail_pid);
    let contacts_live = live_person_for_identity(&arch, plant.contacts_iid).expect("contacts");
    let wa_live = live_person_for_identity(&arch, plant.wa_iid).expect("wa");
    assert_eq!(contacts_live, wa_live);
    assert_ne!(contacts_live, gmail_live);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_nway_unlinked_left_stays_in_sides() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    let left = insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ada",
        &name_fold_join("Ada"),
        Some("Ada"),
    );
    let contacts_pid = live_person_for_identity(
        &arch,
        arch.conn
            .query_row(
                "SELECT id FROM identities WHERE platform='contacts' AND kind='phone'
                 AND value_normalized='+905321110100'",
                [],
                |r| r.get(0),
            )
            .unwrap(),
    )
    .unwrap();
    arch.conn
        .execute(
            "INSERT INTO merge_review_queue(
                status, left_identity_id, right_person_id, suggested_score, reason_summary
             ) VALUES ('open', ?1, ?2, 0.70, 'exact_name_fold')",
            rusqlite::params![left, contacts_pid],
        )
        .unwrap();
    let shown = show(&arch);
    let sides = sides_of(&shown);
    assert!(
        sides
            .iter()
            .any(|s| s["person_id"].is_null() && platforms_of(s).iter().any(|p| p == "whatsapp")),
        "unlinked left identity must stay in sides: {sides:?}"
    );
    assert!(
        sides
            .iter()
            .any(|s| s["person_id"].as_i64() == Some(contacts_pid)),
        "contacts person must stay in sides: {sides:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}
