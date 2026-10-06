//! Matrix IDs (gate grep): SNAP-HELD-EX SNAP-WAL SNAP-CAS-PAIR SNAP-READER SNAP-UNCOMMITTED SNAP-NOT-COPY REST-COUNT REST-QUIET REST-TRUNC REST-LOCK
//!
//! Snapshot and restore. Placeholder Ada / Berk only. The rare token
//! `quartzsnap91` is planted only in the Berk zip. These tests call the
//! public snapshot API. They do not copy the live database by hand.

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use interlace_core::cas::cas_blob_path;
use interlace_core::db::init_archive;
use interlace_core::{
    list_snapshots, open_archive, restore_snapshot, restore_snapshot_at, snapshot_archive, Archive,
    CoreError, ImportOpts, LockMode, SourceKind,
};
use rusqlite::{Connection, OpenFlags};

const TOKEN: &str = "quartzsnap91";
const BLOB: &[u8] = b"ada-blob-quartz";

static SEQ: AtomicU64 = AtomicU64::new(0);

struct Held {
    arch: Archive,
    source_id: i64,
    run_id: i64,
    conversation_id: i64,
    identity_id: i64,
}

fn tmp_root(label: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!(
        "il-snap-{}-{}-{n}-{seq}",
        std::process::id(),
        label
    ));
    let _ = fs::remove_dir_all(&p);
    fs::create_dir_all(&p).unwrap();
    p
}

fn plant(label: &str) -> Held {
    let root = tmp_root(label);
    let arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path)
             VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
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
    let run_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Ada', 'ada', 'Ada')",
            [],
        )
        .unwrap();
    let identity_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let person_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![person_id, identity_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, source_id, native_id, title)
             VALUES ('whatsapp', 'dm', ?1, 'whatsapp:dm-ada', 'Ada')",
            [source_id],
        )
        .unwrap();
    let conversation_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conversation_id, identity_id],
        )
        .unwrap();
    Held {
        arch,
        source_id,
        run_id,
        conversation_id,
        identity_id,
    }
}

fn insert_message(held: &Held, body: &str, key: &str) {
    held.arch
        .conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', ?5, ?6)",
            rusqlite::params![
                held.conversation_id,
                held.source_id,
                held.run_id,
                held.identity_id,
                body,
                key
            ],
        )
        .unwrap();
}

fn message_count(arch: &Archive) -> i64 {
    arch.conn
        .query_row("SELECT COUNT(*) FROM messages", [], |r| r.get(0))
        .unwrap()
}

fn key_on(arch: &Archive, key: &str) -> bool {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM messages WHERE idempotency_key = ?1",
            [key],
            |r| r.get::<_, i64>(0),
        )
        .unwrap()
        > 0
}

fn body_on(arch: &Archive, needle: &str) -> bool {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM messages WHERE body_text LIKE '%' || ?1 || '%'",
            [needle],
            |r| r.get::<_, i64>(0),
        )
        .unwrap()
        > 0
}

fn running_imports(arch: &Archive) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM import_runs WHERE status = 'running'",
            [],
            |r| r.get(0),
        )
        .unwrap()
}

fn hold_wal(arch: &Archive) {
    arch.conn
        .pragma_update(None, "wal_autocheckpoint", 0i64)
        .unwrap();
}

fn snap_dir(arch: &Archive, id: &str) -> PathBuf {
    arch.root.join("snapshots").join(id)
}

fn assert_id_component(id: &str) {
    assert!(!id.is_empty(), "snapshot id is empty");
    assert!(!id.contains('/'), "snapshot id contains a slash: {id}");
    assert!(!id.contains(".."), "snapshot id contains ..: {id}");
}

fn assert_snapshot_top(dir: &Path) {
    let mut names: Vec<String> = fs::read_dir(dir)
        .unwrap()
        .map(|e| e.unwrap().file_name().into_string().unwrap())
        .collect();
    names.sort();
    assert_eq!(
        names,
        vec![
            "INTERLACE.toml".to_string(),
            "MANIFEST.blake3".to_string(),
            "archive.sqlite".to_string(),
            "cas".to_string(),
        ],
        "snapshot top level in {}",
        dir.display()
    );
    assert!(dir.join("cas").is_dir());
    assert!(!dir.join("archive.sqlite-wal").exists());
    assert!(!dir.join("archive.sqlite-shm").exists());
    assert!(!dir.join("snapshots").exists());
    assert!(!dir.join("logs").exists());
    assert!(!dir.join("imports").exists());
    assert!(!dir.join("exports").exists());
    assert!(!dir.join("tmp").exists());
    assert!(!dir.join("INTERLACE.lock").exists());
}

fn sqlite_copy(src: &Path) -> PathBuf {
    let dst = tmp_root("open").join("archive.sqlite");
    fs::copy(src, &dst).unwrap();
    dst
}

fn key_in_file(path: &Path, key: &str) -> bool {
    let Ok(conn) = Connection::open(path) else {
        return false;
    };
    conn.query_row(
        "SELECT COUNT(*) FROM messages WHERE idempotency_key = ?1",
        [key],
        |r| r.get::<_, i64>(0),
    )
    .unwrap_or(0)
        > 0
}

fn integrity_ok(path: &Path) -> bool {
    let conn = Connection::open(path).unwrap();
    let status: String = conn
        .query_row("PRAGMA integrity_check", [], |r| r.get(0))
        .unwrap();
    status == "ok"
}

fn assert_manifest(dir: &Path) {
    let text = fs::read_to_string(dir.join("MANIFEST.blake3")).unwrap();
    assert!(text.ends_with('\n'), "manifest must end with LF");
    assert!(!text.ends_with("\n\n"), "manifest has a blank line");
    let lines: Vec<&str> = text.trim_end_matches('\n').split('\n').collect();
    assert!(!lines.is_empty());
    let mut paths = Vec::new();
    for line in &lines {
        let (hex, rel) = line
            .split_once(' ')
            .unwrap_or_else(|| panic!("manifest line has no space: {line}"));
        assert_eq!(hex.len(), 64, "{line}");
        assert!(
            hex.chars()
                .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
            "{line}"
        );
        assert!(!rel.is_empty() && !rel.starts_with('/') && !rel.contains('\\'));
        let bytes = fs::read(dir.join(rel)).unwrap();
        let got = blake3::hash(&bytes).to_hex().to_string();
        assert_eq!(got, hex, "manifest digest for {rel}");
        paths.push(rel.to_string());
    }
    let mut sorted = paths.clone();
    sorted.sort();
    assert_eq!(paths, sorted, "manifest paths are not sorted");
    let mut expected = vec!["INTERLACE.toml".to_string(), "archive.sqlite".to_string()];
    let mut cas_files = Vec::new();
    walk_files(&dir.join("cas"), dir, &mut cas_files);
    expected.extend(cas_files);
    expected.sort();
    assert_eq!(paths, expected);
}

fn walk_files(dir: &Path, root: &Path, out: &mut Vec<String>) {
    if !dir.is_dir() {
        return;
    }
    let mut entries: Vec<_> = fs::read_dir(dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    entries.sort();
    for path in entries {
        if path.is_dir() {
            walk_files(&path, root, out);
        } else if path.is_file() {
            let rel = path
                .strip_prefix(root)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/");
            out.push(rel);
        }
    }
}

fn write_ios_zip(dir: &Path, stem: &str, sender: &str, body: &str) -> PathBuf {
    fs::create_dir_all(dir).unwrap();
    let p = dir.join(format!("{stem}.zip"));
    let f = fs::File::create(&p).unwrap();
    let mut z = zip::ZipWriter::new(f);
    z.start_file(
        "_chat.txt",
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
    )
    .unwrap();
    let chat = format!(
        "[2024-01-15, 10:00:00] Messages and calls are end-to-end encrypted\n\
         [2024-01-15, 10:00:01] {sender}: {body}\n"
    );
    z.write_all(chat.as_bytes()).unwrap();
    z.finish().unwrap();
    p
}

fn import_chat(arch: &mut Archive, sender: &str, body: &str, conversation: &str) {
    let dir = tmp_root("zip");
    let zip = write_ios_zip(&dir, "chat", sender, body);
    let opts = ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some(conversation.into()),
        ..ImportOpts::default()
    };
    arch.run_import(SourceKind::WhatsappIosZip, &zip, &opts)
        .unwrap();
}

fn open_reader(path: &Path) -> Connection {
    let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
    conn.pragma_update(None, "query_only", "ON").unwrap();
    conn.pragma_update(None, "busy_timeout", 5_000i64).unwrap();
    conn
}

#[test]
fn snap_held_ex() {
    let held = plant("held");
    insert_message(&held, "ada held", "k-held");
    let id = snapshot_archive(&held.arch).unwrap();
    assert_id_component(&id);
    let again = open_archive(&held.arch.root, LockMode::Exclusive);
    match again {
        Err(CoreError::Lock { .. }) => {}
        Ok(_) => panic!("second exclusive open succeeded while the archive is held"),
        Err(other) => panic!("expected CoreError::Lock, got {other}"),
    }
    let ids = list_snapshots(&held.arch.root).unwrap();
    assert!(ids.contains(&id), "list_snapshots missed {id}: {ids:?}");
    assert!(
        ids.iter().all(|s| !s.contains('/') && !s.contains("..")),
        "list_snapshots returned a path: {ids:?}"
    );
}

#[test]
fn snap_wal() {
    let held = plant("wal");
    hold_wal(&held.arch);
    held.arch.conn.execute_batch("BEGIN IMMEDIATE").unwrap();
    insert_message(&held, "ada wal", "k-wal-quartz");
    held.arch.conn.execute_batch("COMMIT").unwrap();
    let wal = held.arch.root.join("archive.sqlite-wal");
    let wal_len = fs::metadata(&wal).expect("live wal").len();
    assert!(wal_len > 0, "committed row did not land in the wal");
    let main_only = sqlite_copy(&held.arch.root.join("archive.sqlite"));
    assert!(
        !key_in_file(&main_only, "k-wal-quartz"),
        "copying archive.sqlite alone already has the wal row"
    );
    let id = snapshot_archive(&held.arch).unwrap();
    let dir = snap_dir(&held.arch, &id);
    assert_snapshot_top(&dir);
    let copy = sqlite_copy(&dir.join("archive.sqlite"));
    assert!(key_in_file(&copy, "k-wal-quartz"));
    assert!(integrity_ok(&copy));
}

#[test]
fn snap_cas_pair() {
    let held = plant("cas");
    insert_message(&held, "ada blob", "k-blob");
    let message_id = held.arch.conn.last_insert_rowid();
    let hash = held.arch.cas_put(BLOB, Some("image/jpeg")).unwrap();
    held.arch
        .conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
             VALUES (?1, ?2, 'ada-photo.jpg', 'image/jpeg', 'image', 0, 0)",
            rusqlite::params![message_id, hash],
        )
        .unwrap();
    let id = snapshot_archive(&held.arch).unwrap();
    let dir = snap_dir(&held.arch, &id);
    assert_snapshot_top(&dir);
    let copy = sqlite_copy(&dir.join("archive.sqlite"));
    let conn = Connection::open(&copy).unwrap();
    let mut stmt = conn
        .prepare(
            "SELECT cas_hash FROM attachments WHERE cas_hash IS NOT NULL
             UNION
             SELECT hash FROM cas_blobs",
        )
        .unwrap();
    let hashes: Vec<String> = stmt
        .query_map([], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert!(hashes.contains(&hash), "snapshot db does not name {hash}");
    for h in &hashes {
        let live = fs::read(cas_blob_path(&held.arch.root, h).unwrap()).unwrap();
        let snap = fs::read(cas_blob_path(&dir, h).unwrap()).unwrap();
        assert_eq!(live, snap, "cas bytes differ for {h}");
    }
    let snap_bytes = fs::read(cas_blob_path(&dir, &hash).unwrap()).unwrap();
    assert_eq!(snap_bytes, BLOB);
    assert_manifest(&dir);
}

#[test]
fn snap_reader() {
    let held = plant("reader");
    insert_message(&held, "ada reader", "k-reader");
    let path = held.arch.root.join("archive.sqlite");
    let go = Arc::new(AtomicBool::new(false));
    let stop = Arc::new(AtomicBool::new(false));
    let go2 = Arc::clone(&go);
    let stop2 = Arc::clone(&stop);
    let handle = thread::spawn(move || {
        let conn = open_reader(&path);
        let _: i64 = conn
            .query_row("SELECT COUNT(*) FROM messages", [], |r| r.get(0))
            .unwrap();
        go2.store(true, Ordering::SeqCst);
        while !stop2.load(Ordering::SeqCst) {
            thread::sleep(Duration::from_millis(10));
            let _: i64 = conn
                .query_row("SELECT COUNT(*) FROM messages", [], |r| r.get(0))
                .unwrap();
        }
    });
    while !go.load(Ordering::SeqCst) {
        thread::sleep(Duration::from_millis(10));
    }
    let id = snapshot_archive(&held.arch).unwrap();
    stop.store(true, Ordering::SeqCst);
    handle.join().unwrap();
    let copy = sqlite_copy(&snap_dir(&held.arch, &id).join("archive.sqlite"));
    assert!(integrity_ok(&copy));
    assert!(key_in_file(&copy, "k-reader"));
}

#[test]
fn snap_uncommitted() {
    let held = plant("open-tx");
    insert_message(&held, "ada committed", "k-committed");
    let before = message_count(&held.arch);
    held.arch.conn.execute_batch("BEGIN IMMEDIATE").unwrap();
    insert_message(&held, "ada open", "k-open-quartz");
    let id = snapshot_archive(&held.arch).unwrap();
    let copy = sqlite_copy(&snap_dir(&held.arch, &id).join("archive.sqlite"));
    assert!(!key_in_file(&copy, "k-open-quartz"));
    assert!(key_in_file(&copy, "k-committed"));
    assert!(key_on(&held.arch, "k-open-quartz"));
    assert_eq!(message_count(&held.arch), before + 1);
    held.arch.conn.execute_batch("ROLLBACK").unwrap();
    assert!(!key_on(&held.arch, "k-open-quartz"));
    assert_eq!(message_count(&held.arch), before);
}

#[test]
fn snap_not_copy() {
    let held = plant("not-copy");
    insert_message(&held, "ada one", "k-one");
    let outside = tmp_root("picked");
    let id1 = snapshot_archive(&held.arch).unwrap();
    let dir1 = snap_dir(&held.arch, &id1);
    assert!(dir1.is_dir());
    assert!(dir1.starts_with(&held.arch.root));
    assert!(!outside.join("snapshots").join(&id1).exists());
    assert!(!outside.join(&id1).exists());
    thread::sleep(Duration::from_millis(1100));
    let id2 = snapshot_archive(&held.arch).unwrap();
    assert!(dir1.is_dir(), "second snapshot deleted the first");
    assert!(snap_dir(&held.arch, &id2).is_dir());
    let ids = list_snapshots(&held.arch.root).unwrap();
    assert_eq!(ids, vec![id2.clone(), id1.clone()]);
    let mut desc = ids.clone();
    desc.sort();
    desc.reverse();
    assert_eq!(ids, desc, "list_snapshots is not newest first");
}

#[test]
fn rest_count() {
    let root = tmp_root("rest-count");
    let mut arch = init_archive(&root).unwrap();
    import_chat(&mut arch, "Ada", "ada-before", "Ada");
    assert!(body_on(&arch, "ada-before"));
    let quiet = message_count(&arch);
    assert!(quiet > 0);
    let id = snapshot_archive(&arch).unwrap();
    hold_wal(&arch);
    import_chat(&mut arch, "Berk", TOKEN, "Berk");
    let wal = root.join("archive.sqlite-wal");
    assert!(fs::metadata(&wal).expect("berk wal").len() > 0);
    assert!(body_on(&arch, TOKEN));
    let keys: Vec<String> = {
        let mut stmt = arch
            .conn
            .prepare("SELECT idempotency_key FROM messages WHERE body_text LIKE '%' || ?1 || '%'")
            .unwrap();
        stmt.query_map([TOKEN], |r| r.get(0))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };
    assert!(!keys.is_empty(), "Berk import wrote no idempotency key");
    restore_snapshot(&mut arch, &id).unwrap();
    // The returned connection is the snapshot. A later open must not replay
    // the pre-restore wal and bring Berk back.
    assert_eq!(message_count(&arch), quiet);
    assert!(body_on(&arch, "ada-before"));
    assert!(!body_on(&arch, TOKEN));
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).unwrap();
    assert_eq!(message_count(&arch), quiet);
    assert!(body_on(&arch, "ada-before"));
    assert!(!body_on(&arch, TOKEN));
    for key in &keys {
        assert!(!key_on(&arch, key), "Berk key survived restore: {key}");
    }
}

#[test]
fn rest_quiet() {
    let root = tmp_root("rest-quiet");
    let mut arch = init_archive(&root).unwrap();
    import_chat(&mut arch, "Ada", "ada-quiet", "Ada");
    assert_eq!(running_imports(&arch), 0);
    let quiet = message_count(&arch);
    let id = snapshot_archive(&arch).unwrap();
    import_chat(&mut arch, "Ada", "ada-later", "Ada");
    assert!(body_on(&arch, "ada-later"));
    restore_snapshot(&mut arch, &id).unwrap();
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).unwrap();
    let status: String = arch
        .conn
        .query_row("PRAGMA integrity_check", [], |r| r.get(0))
        .unwrap();
    assert_eq!(status, "ok");
    assert_eq!(message_count(&arch), quiet);
    assert!(body_on(&arch, "ada-quiet"));
    assert!(!body_on(&arch, "ada-later"));
}

#[test]
fn rest_trunc() {
    let mut held = plant("trunc");
    insert_message(&held, "ada live", "k-live");
    let id = snapshot_archive(&held.arch).unwrap();
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let n = message_count(&held.arch);
    let short = snap_dir(&held.arch, &id).join("archive.sqlite");
    let f = OpenOptions::new().write(true).open(&short).unwrap();
    f.set_len(16).unwrap();
    drop(f);
    let err = restore_snapshot(&mut held.arch, &id).unwrap_err();
    match err {
        CoreError::Fatal(msg) => {
            assert!(msg.starts_with("snapshot hash"), "fatal message was {msg}")
        }
        other => panic!("expected snapshot hash, got {other}"),
    }
    assert_eq!(fs::read(&live).unwrap(), before);
    assert_eq!(message_count(&held.arch), n);
    assert_eq!(fs::metadata(&short).unwrap().len(), 16);
}

#[test]
fn rest_lock() {
    let held = plant("lock");
    insert_message(&held, "ada lock", "k-lock");
    let id = snapshot_archive(&held.arch).unwrap();
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let n = message_count(&held.arch);
    let err = restore_snapshot_at(&held.arch.root, &id).unwrap_err();
    match err {
        CoreError::Lock { .. } => {}
        other => panic!("expected CoreError::Lock, got {other}"),
    }
    assert_eq!(fs::read(&live).unwrap(), before);
    assert_eq!(message_count(&held.arch), n);
}

#[test]
fn rest_missing_id() {
    let mut held = plant("missing");
    insert_message(&held, "ada missing", "k-missing");
    let id = snapshot_archive(&held.arch).unwrap();
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let n = message_count(&held.arch);
    for bad in ["a/b", ".."] {
        let err = restore_snapshot(&mut held.arch, bad).unwrap_err();
        match err {
            CoreError::Fatal(msg) => assert!(
                msg.starts_with("snapshot missing"),
                "{bad} fatal message was {msg}"
            ),
            other => panic!("{bad}: expected snapshot missing, got {other}"),
        }
        assert_eq!(fs::read(&live).unwrap(), before);
        assert_eq!(message_count(&held.arch), n);
    }
    assert!(snap_dir(&held.arch, &id).is_dir());
}
