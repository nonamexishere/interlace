//! Matrix IDs (gate grep): DOC-DRY-FTS DOC-DRY-ORPHAN DOC-REATTACH DOC-APPLY-REFUSE DOC-SECOND-APPLY DOC-PLAN-QUIET DOC-RECLAIM-OFFSHARD DOC-REATTACH-STALE CRASH-REATTACH CRASH-REATTACH-NOAPPLY CRASH-RECLAIM

mod crash_kill;

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, Archive, LockMode};
use interlace_core::search::index_import_run;
use interlace_core::{open_archive, search, CoreError, SearchQuery};

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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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

fn insert_berk(arch: &Archive) {
    let (conv, src, run): (i64, i64, i64) = arch
        .conn
        .query_row(
            "SELECT conversation_id, source_id, import_run_id FROM messages LIMIT 1",
            [],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('gmail', 'email', 'berk@example.com', 'berk@example.com', 'Berk')",
            [],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'merhaba', 'berk-merhaba')",
            rusqlite::params![conv, src, run, iid],
        )
        .unwrap();
}

fn insert_ada_photo(arch: &Archive, hash: &str) {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 'ada', '/ada.vcf')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, fn, photo_cas_hash) VALUES (?1, 'ada-photo', 'Ada', ?2)",
            rusqlite::params![src, hash],
        )
        .unwrap();
}

fn berk_body(arch: &Archive) -> String {
    arch.conn
        .query_row(
            "SELECT body_text FROM messages WHERE idempotency_key = 'berk-merhaba'",
            [],
            |row| row.get(0),
        )
        .unwrap()
}

fn cas_row(arch: &Archive, hash: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [hash],
            |row| row.get(0),
        )
        .unwrap()
}

struct ReattachFix {
    root: PathBuf,
    h: String,
    b1: Vec<u8>,
    misplaced: PathBuf,
    other_name: String,
    h2: String,
    b2: Vec<u8>,
    h2_path: PathBuf,
}

fn setup_reattach() -> ReattachFix {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    insert_berk(&arch);
    let b1 = b"merhaba".to_vec();
    let h = arch.cas_put(&b1, None).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, kind, omitted, missing)
             VALUES (?1, ?2, 'file', 0, 0)",
            rusqlite::params![message_id, h],
        )
        .unwrap();
    let b2 = b"merhaba iki".to_vec();
    let h2 = arch.cas_put(&b2, Some("image/jpeg")).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
             VALUES (?1, ?2, 'ada.jpg', 'image/jpeg', 'image', 0, 0)",
            rusqlite::params![message_id, h2],
        )
        .unwrap();
    insert_ada_photo(&arch, &h2);
    let canonical = blob_file(&root, &h);
    let mut other_name = other_hex(&h);
    if other_name == h2 {
        other_name = other_hex(&other_name);
    }
    let misplaced = canonical.parent().unwrap().join(&other_name);
    assert_ne!(misplaced, blob_file(&root, &h2), "fixture paths collided");
    std::fs::rename(&canonical, &misplaced).unwrap();
    let planned = plan(&arch);
    assert!(
        planned.reattach.iter().any(|item| item == &h),
        "fixture reattach {:?}",
        planned.reattach
    );
    assert!(
        !planned
            .reclaim
            .iter()
            .any(|item| item == &h2 || item == &other_name),
        "fixture reclaim {:?}",
        planned.reclaim
    );
    let h2_path = blob_file(&root, &h2);
    let root = arch.root.clone();
    drop(arch);
    ReattachFix {
        root,
        h,
        b1,
        misplaced,
        other_name,
        h2,
        b2,
        h2_path,
    }
}

fn reattach_child() {
    let root = PathBuf::from(std::env::var("INTERLACE_CRASH_ROOT").unwrap());
    let arm = std::env::var("INTERLACE_CRASH_ARM").unwrap();
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-REATTACH child open");
    let _planned = plan(&arch);
    std::fs::write(&arm, b"1").unwrap();
    let result = arch.doctor_apply(&_planned);
    eprintln!("CRASH-REATTACH apply returned: {result:?}");
    std::process::exit(86);
}

fn assert_b2_and_berk(arch: &Archive, fix: &ReattachFix, id: &str) {
    assert_eq!(
        std::fs::read(&fix.h2_path).expect(id),
        fix.b2,
        "{id} B2 bytes or path changed"
    );
    assert_eq!(arch.cas_get(&fix.h2).unwrap(), fix.b2, "{id} cas_get(H2)");
    assert_eq!(berk_body(arch), "merhaba", "{id} Berk body");
}

#[test]
fn crash_reattach() {
    let _guard = crash_kill::one_test_at_a_time();
    if crash_kill::child_enter() {
        reattach_child();
        return;
    }
    let fix = setup_reattach();
    crash_kill::kill_at_seam(crash_kill::KillSpec {
        test_name: "crash_reattach",
        mode: "reattach",
        root: &fix.root,
        target: &fix.h,
        extra: &[],
    });
    let arch = open_archive(&fix.root, LockMode::Exclusive).expect("CRASH-REATTACH open_archive");
    let got = arch.cas_get(&fix.h);
    assert!(
        got.as_deref().ok() == Some(fix.b1.as_slice()),
        "CRASH-REATTACH cas_get(H) must be B1, got {}",
        match &got {
            Ok(bytes) => format!("{bytes:?}"),
            Err(err) => err.to_string(),
        }
    );
    let other = arch.cas_get(&fix.other_name);
    assert!(
        other.as_deref().ok() != Some(fix.b1.as_slice()),
        "CRASH-REATTACH cas_get of the misplaced name returned B1"
    );
    assert_b2_and_berk(&arch, &fix, "CRASH-REATTACH");
    drop(arch);
    let arch = open_archive(&fix.root, LockMode::Exclusive).expect("CRASH-REATTACH second open");
    assert_eq!(
        arch.cas_get(&fix.h).unwrap(),
        fix.b1,
        "CRASH-REATTACH second open put other bytes at H"
    );
    assert_ne!(
        arch.cas_get(&fix.h).unwrap(),
        fix.b2,
        "CRASH-REATTACH second open put B2 at H"
    );
    assert_b2_and_berk(&arch, &fix, "CRASH-REATTACH second open");
    drop(arch);
    let _ = std::fs::remove_dir_all(&fix.root);
}

#[test]
fn crash_reattach_noapply() {
    let _guard = crash_kill::one_test_at_a_time();
    let fix = setup_reattach();
    for pass in 1..=2 {
        let arch =
            open_archive(&fix.root, LockMode::Exclusive).expect("CRASH-REATTACH-NOAPPLY open");
        assert_eq!(
            std::fs::read(&fix.misplaced).expect("misplaced path"),
            fix.b1,
            "CRASH-REATTACH-NOAPPLY open {pass} moved B1"
        );
        assert!(
            !blob_file(&fix.root, &fix.h).exists(),
            "CRASH-REATTACH-NOAPPLY open {pass} created the canonical path"
        );
        assert!(
            arch.cas_get(&fix.h).as_deref().ok() != Some(fix.b1.as_slice()),
            "CRASH-REATTACH-NOAPPLY open {pass} served B1 for H without apply"
        );
        assert_b2_and_berk(&arch, &fix, "CRASH-REATTACH-NOAPPLY");
        let planned = plan(&arch);
        assert!(
            planned.reattach.iter().any(|item| item == &fix.h),
            "CRASH-REATTACH-NOAPPLY open {pass} plan {:?}",
            planned.reattach
        );
        drop(arch);
    }
    let _ = std::fs::remove_dir_all(&fix.root);
}

struct ReclaimFix {
    root: PathBuf,
    orphan: String,
    orphan_bytes: Vec<u8>,
    orphan_path: PathBuf,
    kept_bytes: Vec<u8>,
    kept_path: PathBuf,
}

fn setup_reclaim() -> ReclaimFix {
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let message_id = plant_ada(&arch);
    insert_berk(&arch);
    let kept_bytes = b"merhaba".to_vec();
    let kept = arch.cas_put(&kept_bytes, Some("image/jpeg")).unwrap();
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
             VALUES (?1, ?2, 'ada.jpg', 'image/jpeg', 'image', 0, 0)",
            rusqlite::params![message_id, kept],
        )
        .unwrap();
    insert_ada_photo(&arch, &kept);
    let orphan_bytes = b"merhaba iki".to_vec();
    let orphan = arch.cas_put(&orphan_bytes, None).unwrap();
    let planned = plan(&arch);
    assert!(
        planned.reclaim.iter().any(|item| item == &orphan),
        "fixture reclaim {:?}",
        planned.reclaim
    );
    assert!(
        !planned.reclaim.iter().any(|item| item == &kept),
        "fixture reclaimed Ada's photo {:?}",
        planned.reclaim
    );
    assert!(
        planned.reattach.is_empty(),
        "fixture reattach {:?}",
        planned.reattach
    );
    let orphan_path = blob_file(&root, &orphan);
    let kept_path = blob_file(&root, &kept);
    let root = arch.root.clone();
    drop(arch);
    ReclaimFix {
        root,
        orphan,
        orphan_bytes,
        orphan_path,
        kept_bytes,
        kept_path,
    }
}

fn reclaim_child() {
    let root = PathBuf::from(std::env::var("INTERLACE_CRASH_ROOT").unwrap());
    let arm = std::env::var("INTERLACE_CRASH_ARM").unwrap();
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-RECLAIM child open");
    let _planned = plan(&arch);
    std::fs::write(&arm, b"1").unwrap();
    let result = arch.doctor_apply(&_planned);
    eprintln!("CRASH-RECLAIM apply returned: {result:?}");
    std::process::exit(86);
}

fn reclaim_consistent(arch: &Archive, fix: &ReclaimFix) -> bool {
    let row = cas_row(arch, &fix.orphan);
    let exists = fix.orphan_path.is_file();
    if !exists && row == 0 {
        return true;
    }
    if row == 1 && exists {
        let file = std::fs::read(&fix.orphan_path).ok();
        let got = arch.cas_get(&fix.orphan).ok();
        return file.as_deref() == Some(fix.orphan_bytes.as_slice())
            && got.as_deref() == Some(fix.orphan_bytes.as_slice());
    }
    false
}

fn assert_kept_not_on_orphan(fix: &ReclaimFix, id: &str) {
    assert_eq!(
        std::fs::read(&fix.kept_path).expect(id),
        fix.kept_bytes,
        "{id} Ada's photo bytes changed"
    );
    assert_ne!(
        std::fs::read(&fix.orphan_path).ok().as_deref(),
        Some(fix.kept_bytes.as_slice()),
        "{id} renamed Ada's photo onto the reclaimed hash"
    );
}

#[test]
fn crash_reclaim() {
    let _guard = crash_kill::one_test_at_a_time();
    if crash_kill::child_enter() {
        reclaim_child();
        return;
    }
    let fix = setup_reclaim();
    crash_kill::kill_at_seam(crash_kill::KillSpec {
        test_name: "crash_reclaim",
        mode: "reclaim",
        root: &fix.root,
        target: &fix.orphan,
        extra: &[],
    });
    let arch = open_archive(&fix.root, LockMode::Exclusive).expect("CRASH-RECLAIM open_archive");
    assert_eq!(berk_body(&arch), "merhaba", "CRASH-RECLAIM Berk body");
    assert_kept_not_on_orphan(&fix, "CRASH-RECLAIM");
    let row = cas_row(&arch, &fix.orphan);
    let exists = fix.orphan_path.is_file();
    assert!(
        reclaim_consistent(&arch, &fix),
        "CRASH-RECLAIM neither the file and cas_blobs row are gone nor the row is back with the file bytes (row={row}, file={exists})"
    );
    drop(arch);
    let arch = open_archive(&fix.root, LockMode::Exclusive).expect("CRASH-RECLAIM second open");
    assert_eq!(
        berk_body(&arch),
        "merhaba",
        "CRASH-RECLAIM second open Berk body"
    );
    assert_kept_not_on_orphan(&fix, "CRASH-RECLAIM second open");
    assert_ne!(
        arch.cas_get(&fix.orphan).ok().as_deref(),
        Some(fix.kept_bytes.as_slice()),
        "CRASH-RECLAIM second open put Ada's photo bytes at the reclaimed hash"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&fix.root);
}
