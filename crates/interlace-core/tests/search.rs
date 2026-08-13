//! FTS must-pass matrix.
//!
//! Matrix IDs (gate grep): S1 S2 S3

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::search::{index_import_run, turkish_fold};
use interlace_core::{
    person_timeline, search, AttachmentFilter, ConversationKind, SearchQuery,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-s-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

struct Planted {
    istanbul: i64,
    islak: i64,
    other: i64,
    person: i64,
    group_msg: i64,
}

fn plant(arch: &interlace_core::db::Archive) -> Planted {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('gmail', 'email', 'a@x.com', 'a@x.com', 'Ali')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Other', 'other', 'Other')",
            [],
        )
        .unwrap();
    let other_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ali', 0)",
            [],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![pid, iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-t', 't')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:g', 'Project')",
            [],
        )
        .unwrap();
    let grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![grp, iid],
        )
        .unwrap();

    let ins = |conv: i64, body: &str, key: &str, sender: Option<i64>| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(
                    conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key
                 ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', ?5, ?6)",
                rusqlite::params![conv, src, run, sender, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let istanbul = ins(dm, "Gidiyoruz İstanbul yarın", "k-ist", Some(iid));
    let islak = ins(dm, "Yol ISLAK sakın kayma", "k-isl", Some(iid));
    let other = ins(dm, "hello world only", "k-other", Some(iid));
    let group_msg = ins(grp, "group chatter ISLAK too", "k-grp", Some(other_id));
    index_import_run(arch, run).unwrap();
    Planted {
        istanbul,
        islak,
        other,
        person: pid,
        group_msg,
    }
}

fn ids(hits: &[interlace_core::SearchHit]) -> Vec<i64> {
    hits.iter().map(|h| h.message_id).collect()
}

#[test]
fn search_s1_istanbul_hits_dotted_capital_i() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant(&arch);
    assert_eq!(turkish_fold("İstanbul"), "istanbul");
    let hits = search(
        &arch,
        &SearchQuery {
            q: "istanbul".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        ids(&hits).contains(&p.istanbul),
        "S1 istanbul must hit İstanbul, got {hits:?}"
    );
    assert!(!ids(&hits).contains(&p.other));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_s2_dotless_islak_hits_islak() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant(&arch);
    assert_eq!(turkish_fold("ISLAK"), "ıslak");
    let hits = search(
        &arch,
        &SearchQuery {
            q: "ıslak".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        ids(&hits).contains(&p.islak),
        "S2 ıslak must hit ISLAK, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_s3_ascii_islak_hits_islak() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "islak".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        ids(&hits).contains(&p.islak),
        "S3 islak must hit ISLAK via ascii fold, got {hits:?}"
    );

    let tl = person_timeline(&arch, p.person, false, 50).unwrap();
    assert!(ids(&tl).contains(&p.istanbul));
    assert!(
        !ids(&tl).contains(&p.group_msg),
        "D18 default timeline excludes groups"
    );
    let tl_g = person_timeline(&arch, p.person, true, 50).unwrap();
    assert!(ids(&tl_g).contains(&p.group_msg));
    let _ = std::fs::remove_dir_all(&root);
}

/// #122 — same FTS token in a dm and a group; kind=dm must not return the group.
struct KindPlanted {
    dm_msg: i64,
    group_msg: i64,
}

fn plant_kind(arch: &interlace_core::db::Archive) -> KindPlanted {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_android_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Ada', 'ada', 'Ada')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:dm-ada', 'Ada')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:g-kind', 'Project Ada')",
            [],
        )
        .unwrap();
    let grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![grp, iid],
        )
        .unwrap();

    let ins = |conv: i64, body: &str, key: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(
                    conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key
                 ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', ?5, ?6)",
                rusqlite::params![conv, src, run, iid, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    // Shared FTS token in both dm and group.
    let dm_msg = ins(dm, "sharedhit from Ada dm", "k-kind-dm");
    let group_msg = ins(grp, "sharedhit from Ada group", "k-kind-grp");
    index_import_run(arch, run).unwrap();
    KindPlanted { dm_msg, group_msg }
}

#[test]
fn search_kind_dm_excludes_group_hits() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_kind(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "sharedhit".into(),
            conversation_kind: Some(ConversationKind::Dm),
            include_groups: true,
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let got = ids(&hits);
    assert!(
        got.contains(&p.dm_msg),
        "kind=dm must return the dm message, got {hits:?}"
    );
    assert!(
        !got.contains(&p.group_msg),
        "kind=dm must not return group hits even with include_groups, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_kind_group_respects_include_groups() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_kind(&arch);

    let without = search(
        &arch,
        &SearchQuery {
            q: "sharedhit".into(),
            conversation_kind: Some(ConversationKind::Group),
            include_groups: false,
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        !ids(&without).contains(&p.group_msg),
        "kind=group with include_groups=false must not return group hits, got {without:?}"
    );
    assert!(
        !ids(&without).contains(&p.dm_msg),
        "kind=group must not return dm hits, got {without:?}"
    );

    let with = search(
        &arch,
        &SearchQuery {
            q: "sharedhit".into(),
            conversation_kind: Some(ConversationKind::Group),
            include_groups: true,
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        ids(&with).contains(&p.group_msg),
        "kind=group with include_groups=true must return the group message, got {with:?}"
    );
    assert!(
        !ids(&with).contains(&p.dm_msg),
        "kind=group must not return dm hits, got {with:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// #125 — same FTS token on messages with different attachment presence.
struct AttPlanted {
    has_file: i64,
    omitted: i64,
    missing: i64,
    plain: i64,
}

fn plant_attachment(arch: &interlace_core::db::Archive) -> AttPlanted {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_android_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Ada', 'ada', 'Ada')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:dm-ada-att', 'Ada')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, iid],
        )
        .unwrap();

    let ins = |body: &str, key: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(
                    conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key
                 ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', ?5, ?6)",
                rusqlite::params![dm, src, run, iid, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    // Shared FTS token across all four messages (placeholder Ada only).
    let has_file = ins("attachtoken has file for Ada", "k-att-has");
    let omitted = ins("attachtoken omitted for Ada", "k-att-omit");
    let missing = ins("attachtoken missing for Ada", "k-att-miss");
    let plain = ins("attachtoken plain for Ada", "k-att-plain");

    // Stored CAS blob: cas_blobs row + attachments.cas_hash set.
    let cas = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    arch.conn
        .execute(
            "INSERT INTO cas_blobs(hash, size) VALUES (?1, 4)",
            [cas],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, filename, kind, omitted, missing)
             VALUES (?1, ?2, 'photo.jpg', 'image', 0, 0)",
            rusqlite::params![has_file, cas],
        )
        .unwrap();
    // Omitted placeholder attachment (no CAS).
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, kind, omitted, missing)
             VALUES (?1, 'omitted.bin', 'file', 1, 0)",
            [omitted],
        )
        .unwrap();
    // Missing referenced attachment (no CAS).
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, kind, omitted, missing)
             VALUES (?1, 'gone.bin', 'file', 0, 1)",
            [missing],
        )
        .unwrap();
    // plain: no attachments row.

    index_import_run(arch, run).unwrap();
    AttPlanted {
        has_file,
        omitted,
        missing,
        plain,
    }
}

#[test]
fn search_attachment_has_file_only_cas_backed() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_attachment(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "attachtoken".into(),
            attachment_filter: Some(AttachmentFilter::HasFile),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let got = ids(&hits);
    assert_eq!(
        got,
        vec![p.has_file],
        "HasFile must return only the CAS-backed row, got {hits:?}"
    );
    assert!(
        !got.contains(&p.omitted) && !got.contains(&p.missing) && !got.contains(&p.plain),
        "HasFile must exclude omitted/missing/plain, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_attachment_omitted_only() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_attachment(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "attachtoken".into(),
            attachment_filter: Some(AttachmentFilter::Omitted),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let got = ids(&hits);
    assert_eq!(
        got,
        vec![p.omitted],
        "Omitted must return only the omitted-attachment row, got {hits:?}"
    );
    assert!(
        !got.contains(&p.has_file) && !got.contains(&p.missing) && !got.contains(&p.plain),
        "Omitted must exclude has_file/missing/plain, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_attachment_missing_only() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_attachment(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "attachtoken".into(),
            attachment_filter: Some(AttachmentFilter::Missing),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let got = ids(&hits);
    assert_eq!(
        got,
        vec![p.missing],
        "Missing must return only the missing-attachment row, got {hits:?}"
    );
    assert!(
        !got.contains(&p.has_file) && !got.contains(&p.omitted) && !got.contains(&p.plain),
        "Missing must exclude has_file/omitted/plain, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn search_attachment_any_returns_all_fts_hits() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let p = plant_attachment(&arch);
    let hits = search(
        &arch,
        &SearchQuery {
            q: "attachtoken".into(),
            attachment_filter: None,
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let got = ids(&hits);
    for id in [p.has_file, p.omitted, p.missing, p.plain] {
        assert!(
            got.contains(&id),
            "Any (no attachment_filter) must return all FTS hits including {id}, got {hits:?}"
        );
    }
    let _ = std::fs::remove_dir_all(&root);
}
