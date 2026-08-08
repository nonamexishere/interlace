//! Doctor smoke: stale heartbeat → interrupted; issues non-empty.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-doc-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

#[test]
fn doctor_stale_running_marked_interrupted() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status, heartbeat_at)
             VALUES (1, 'running', '2000-01-01T00:00:00.000Z')",
            [],
        )
        .unwrap();
    let issues = arch.doctor_issues().unwrap();
    assert!(
        issues.iter().any(|i| i.contains("heartbeat")),
        "expected stale heartbeat issue, got {issues:?}"
    );
    let status: String = arch
        .conn
        .query_row("SELECT status FROM import_runs WHERE id = 1", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert_eq!(status, "interrupted");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doctor_missing_cas_blob_is_issue() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (1, 'done')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id) VALUES ('gmail', 'email_thread', 'g1')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sent_at, sent_at_precision,
                kind, body_text, idempotency_key
             ) VALUES (1, 1, 1, '2024-01-01T00:00:00Z', 'second', 'text', 'x', 'k')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO cas_blobs(hash, size) VALUES ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 1)",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (1, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'file', 0, 0)",
            [],
        )
        .unwrap();
    let issues = arch.doctor_issues().unwrap();
    assert!(
        issues.iter().any(|i| i.contains("CAS blob missing")),
        "expected missing CAS, got {issues:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}
