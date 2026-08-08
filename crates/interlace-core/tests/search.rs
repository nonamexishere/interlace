//! FTS must-pass matrix.
//!
//! Matrix IDs (gate grep): S1 S2 S3

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::search::{index_import_run, turkish_fold};
use interlace_core::{person_timeline, search, SearchQuery};

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
