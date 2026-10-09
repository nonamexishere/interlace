//! Matrix IDs (gate grep): DOC-DRY-FTS DOC-DRY-ORPHAN DOC-REATTACH DOC-APPLY-REFUSE DOC-SECOND-APPLY DOC-PLAN-QUIET DOC-RECLAIM-OFFSHARD DOC-REATTACH-STALE

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, Archive};
use interlace_core::search::index_import_run;
use interlace_core::{search, CoreError, SearchQuery};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-docrepair-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn blob_file(root: &Path, hash: &str) -> PathBuf {
    root.join("cas")
        .join(&hash[..2])
        .join(&hash[2..4])
        .join(hash)
}

fn other_hex(hash: &str) -> String {
    let mut name = hash.to_string();
    let last = name.len() - 1;
    let flip = if name.as_bytes()[last] == b'a' {
        b'b'
    } else {
        b'a'
    };
    name.replace_range(last.., std::str::from_utf8(&[flip]).unwrap());
    name
}

fn hits(arch: &Archive, q: &str) -> Vec<i64> {
    search(
        arch,
        &SearchQuery {
            q: q.to_string(),
            ..SearchQuery::default()
        },
    )
    .unwrap()
    .into_iter()
    .map(|hit| hit.message_id)
    .collect()
}

fn plant_ada(arch: &Archive) -> i64 {
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
             VALUES ('gmail', 'email', 'ada@example.com', 'ada@example.com', 'Ada')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
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
             VALUES ('gmail', 'email_thread', 'ada-lantern', 'Ada')",
            [],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conv, iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'ada lantern', 'ada-lantern')",
            rusqlite::params![conv, src, run, iid],
        )
        .unwrap();
    let message_id = arch.conn.last_insert_rowid();
    index_import_run(arch, run).unwrap();
    message_id
}

fn punch_fts(arch: &Archive, message_id: i64) {
    arch.conn
        .execute(
            "INSERT INTO messages_fts(messages_fts, rowid) VALUES ('delete', ?1)",
            [message_id],
        )
        .unwrap();
}

fn search_doc_text(arch: &Archive, message_id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT search_text FROM search_doc WHERE message_id = ?1",
            [message_id],
            |row| row.get(0),
        )
        .unwrap()
}

fn plan(arch: &Archive) -> interlace_core::DoctorPlan {
    arch.doctor_plan().expect("doctor_plan")
}

fn data_version(conn: &rusqlite::Connection) -> i64 {
    conn.query_row("PRAGMA data_version", [], |row| row.get(0))
        .unwrap()
}

#[test]
fn doc_dry_fts() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    assert!(
        hits(&arch, "lantern").contains(&message_id),
        "DOC-DRY-FTS indexed search must hit"
    );
    punch_fts(&arch, message_id);
    let planned = plan(&arch);
    assert!(planned.rebuild_search, "DOC-DRY-FTS rebuild_search");
    assert!(
        !hits(&arch, "lantern").contains(&message_id),
        "DOC-DRY-FTS search still misses"
    );
    assert!(
        search_doc_text(&arch, message_id).contains("lantern"),
        "DOC-DRY-FTS search_doc still holds lantern"
    );
    arch.doctor_apply(&planned)
        .expect("DOC-DRY-FTS doctor_apply");
    assert!(
        hits(&arch, "lantern").contains(&message_id),
        "DOC-DRY-FTS apply makes search hit"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_dry_orphan() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    let orphan = arch.cas_put(b"ada lantern orphan", None).unwrap();
    let keep = arch.cas_put(b"ada lantern keep", None).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'file', 0, 0)",
            rusqlite::params![message_id, keep],
        )
        .unwrap();
    let orphan_path = blob_file(&root, &orphan);
    let keep_path = blob_file(&root, &keep);
    let planned = plan(&arch);
    assert!(
        planned.reclaim.iter().any(|hash| hash == &orphan),
        "DOC-DRY-ORPHAN reclaim {:?}",
        planned.reclaim
    );
    assert!(
        orphan_path.is_file(),
        "DOC-DRY-ORPHAN file still there after plan"
    );
    arch.doctor_apply(&planned)
        .expect("DOC-DRY-ORPHAN doctor_apply");
    assert!(
        !orphan_path.exists(),
        "DOC-DRY-ORPHAN apply removes the file"
    );
    let left: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&orphan],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(left, 0, "DOC-DRY-ORPHAN cas_blobs row removed");
    assert!(
        keep_path.is_file(),
        "DOC-DRY-ORPHAN referenced blob is not removed"
    );
    assert_eq!(std::fs::read(&keep_path).unwrap(), b"ada lantern keep");
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_reattach() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    let bytes = b"ada lantern reattach".to_vec();
    let hash = arch.cas_put(&bytes, None).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'file', 0, 0)",
            rusqlite::params![message_id, hash],
        )
        .unwrap();
    let canonical = blob_file(&root, &hash);
    let other = other_hex(&hash);
    let misplaced = canonical.parent().unwrap().join(&other);
    std::fs::rename(&canonical, &misplaced).unwrap();
    assert!(
        !canonical.exists(),
        "DOC-REATTACH canonical path is missing"
    );
    let planned = plan(&arch);
    assert!(
        planned.reattach.iter().any(|item| item == &hash),
        "DOC-REATTACH reattach {:?}",
        planned.reattach
    );
    assert!(
        !planned.reclaim.iter().any(|item| item == &other),
        "DOC-REATTACH reclaim listed the misplaced name {:?}",
        planned.reclaim
    );
    assert!(
        misplaced.is_file(),
        "DOC-REATTACH misplaced file still there"
    );
    arch.doctor_apply(&planned)
        .expect("DOC-REATTACH doctor_apply");
    assert_eq!(
        std::fs::read(&canonical).expect("DOC-REATTACH canonical bytes"),
        bytes
    );
    assert!(
        !misplaced.exists(),
        "DOC-REATTACH apply removes the misplaced file"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_apply_refuse() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    punch_fts(&arch, message_id);
    let orphan = arch.cas_put(b"ada lantern orphan", None).unwrap();
    let orphan_path = blob_file(&root, &orphan);
    let planned = plan(&arch);
    assert!(planned.rebuild_search, "DOC-APPLY-REFUSE lists rebuild");
    assert!(
        planned.reclaim.iter().any(|hash| hash == &orphan),
        "DOC-APPLY-REFUSE lists reclaim {:?}",
        planned.reclaim
    );
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'file', 0, 0)",
            rusqlite::params![message_id, orphan],
        )
        .unwrap();
    let err = arch.doctor_apply(&planned).expect_err("DOC-APPLY-REFUSE");
    let shown = err.to_string();
    assert!(
        shown.starts_with("doctor plan") || shown.contains("doctor plan"),
        "DOC-APPLY-REFUSE: {shown}"
    );
    match &err {
        CoreError::Fatal(msg) => assert!(
            msg.starts_with("doctor plan"),
            "DOC-APPLY-REFUSE fatal message: {msg}"
        ),
        other => panic!("DOC-APPLY-REFUSE: {other}"),
    }
    assert_eq!(
        std::fs::read(&orphan_path).expect("DOC-APPLY-REFUSE file still there"),
        b"ada lantern orphan"
    );
    assert!(
        !hits(&arch, "lantern").contains(&message_id),
        "DOC-APPLY-REFUSE search for lantern still misses"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_second_apply() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    punch_fts(&arch, message_id);
    let orphan = arch.cas_put(b"ada lantern orphan", None).unwrap();
    let orphan_path = blob_file(&root, &orphan);
    let planned = plan(&arch);
    assert!(planned.rebuild_search, "DOC-SECOND-APPLY lists rebuild");
    assert!(
        planned.reclaim.iter().any(|hash| hash == &orphan),
        "DOC-SECOND-APPLY lists reclaim"
    );
    arch.doctor_apply(&planned)
        .expect("DOC-SECOND-APPLY first apply");
    assert!(
        hits(&arch, "lantern").contains(&message_id),
        "DOC-SECOND-APPLY search hits after first apply"
    );
    assert!(!orphan_path.exists(), "DOC-SECOND-APPLY orphan removed");
    // Same-connection PRAGMA data_version ignores that connection's own commits.
    let watcher = rusqlite::Connection::open(root.join("archive.sqlite")).unwrap();
    watcher
        .busy_timeout(std::time::Duration::from_secs(5))
        .unwrap();
    let _prime = data_version(&watcher);
    let before = data_version(&watcher);
    arch.doctor_apply(&planned)
        .expect("DOC-SECOND-APPLY second apply");
    let after = data_version(&watcher);
    assert_eq!(before, after, "DOC-SECOND-APPLY data_version");
    assert!(
        hits(&arch, "lantern").contains(&message_id),
        "DOC-SECOND-APPLY search still hits"
    );
    assert!(
        !orphan_path.exists(),
        "DOC-SECOND-APPLY orphan file stays gone"
    );
    drop(watcher);
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_plan_quiet() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status, heartbeat_at)
             VALUES (?1, 'running', '2000-01-01T00:00:00.000Z')",
            [src],
        )
        .unwrap();
    let run_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('gmail', 'email', 'ada@example.com', 'ada@example.com', 'Ada')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'ada-quiet', 'Ada')",
            [],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'ada lantern', 'ada-quiet')",
            rusqlite::params![conv, src, run_id, iid],
        )
        .unwrap();
    let message_id = arch.conn.last_insert_rowid();
    let hash = arch.cas_put(b"ada lantern still", None).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, derivative_cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'image', 0, 0)",
            rusqlite::params![message_id, hash],
        )
        .unwrap();
    let attachment_id = arch.conn.last_insert_rowid();
    let before: String = arch
        .conn
        .query_row(
            "SELECT derivative_cas_hash FROM attachments WHERE id = ?1",
            [attachment_id],
            |row| row.get(0),
        )
        .unwrap();
    let _planned = plan(&arch);
    let status: String = arch
        .conn
        .query_row(
            "SELECT status FROM import_runs WHERE id = ?1",
            [run_id],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(status, "running", "DOC-PLAN-QUIET status");
    let after: String = arch
        .conn
        .query_row(
            "SELECT derivative_cas_hash FROM attachments WHERE id = ?1",
            [attachment_id],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(before, hash, "DOC-PLAN-QUIET planted derivative");
    assert_eq!(after, before, "DOC-PLAN-QUIET derivative_cas_hash");
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_reclaim_offshard() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let _message_id = plant_ada(&arch);
    // cas_put writes cas/<hash[0..2]>/<hash[2..4]>/<hash>. This file is another shard.
    let hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    let walked = root.join("cas").join("ab").join("cd").join(hash);
    let canonical = blob_file(&root, hash);
    assert_ne!(
        walked.parent().unwrap(),
        canonical.parent().unwrap(),
        "DOC-RECLAIM-OFFSHARD plant is not the canonical shard"
    );
    std::fs::create_dir_all(walked.parent().unwrap()).unwrap();
    std::fs::write(&walked, b"ada lantern offshard").unwrap();
    let rows: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(rows, 0, "DOC-RECLAIM-OFFSHARD no cas_blobs row");
    let planned = plan(&arch);
    assert!(
        planned.reclaim.iter().any(|item| item == hash),
        "DOC-RECLAIM-OFFSHARD reclaim {:?}",
        planned.reclaim
    );
    assert!(
        walked.is_file(),
        "DOC-RECLAIM-OFFSHARD file still there after plan"
    );
    assert!(
        !canonical.exists(),
        "DOC-RECLAIM-OFFSHARD canonical path does not exist"
    );
    arch.doctor_apply(&planned)
        .expect("DOC-RECLAIM-OFFSHARD doctor_apply");
    assert!(
        !walked.exists(),
        "DOC-RECLAIM-OFFSHARD apply removes the walked file"
    );
    assert!(
        !canonical.exists(),
        "DOC-RECLAIM-OFFSHARD canonical path still does not exist"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn doc_reattach_stale() {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    punch_fts(&arch, message_id);
    let bytes = b"ada lantern reattach".to_vec();
    let hash = arch.cas_put(&bytes, None).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'file', 0, 0)",
            rusqlite::params![message_id, hash],
        )
        .unwrap();
    let canonical = blob_file(&root, &hash);
    let other = other_hex(&hash);
    let misplaced = canonical.parent().unwrap().join(&other);
    std::fs::rename(&canonical, &misplaced).unwrap();
    let planned = plan(&arch);
    assert!(planned.rebuild_search, "DOC-REATTACH-STALE rebuild_search");
    assert!(
        planned.reattach.iter().any(|item| item == &hash),
        "DOC-REATTACH-STALE reattach {:?}",
        planned.reattach
    );
    let cleared = arch
        .conn
        .execute(
            "UPDATE attachments SET cas_hash = NULL WHERE cas_hash = ?1",
            [&hash],
        )
        .unwrap();
    assert_eq!(cleared, 1, "DOC-REATTACH-STALE cleared cas_hash");
    let err = arch.doctor_apply(&planned).expect_err("DOC-REATTACH-STALE");
    match &err {
        CoreError::Fatal(msg) => assert!(
            msg.starts_with("doctor plan"),
            "DOC-REATTACH-STALE fatal message: {msg}"
        ),
        other => panic!("DOC-REATTACH-STALE: {other}"),
    }
    assert_eq!(
        std::fs::read(&misplaced).expect("DOC-REATTACH-STALE misplaced bytes"),
        bytes
    );
    assert!(
        !canonical.exists(),
        "DOC-REATTACH-STALE canonical path is still missing"
    );
    assert!(
        !hits(&arch, "lantern").contains(&message_id),
        "DOC-REATTACH-STALE search for lantern still misses"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}
