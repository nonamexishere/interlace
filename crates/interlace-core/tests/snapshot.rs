//! Matrix IDs (gate grep): SNAP-HELD-EX SNAP-WAL SNAP-CAS-PAIR SNAP-READER SNAP-UNCOMMITTED SNAP-NOT-COPY REST-COUNT REST-QUIET REST-TRUNC REST-LOCK REST-SIDECAR REST-ORDER REST-LIVE REST-PUBLISH REST-BUSY REST-RESUME CRASH-SNAPSHOT REST-REPLAY-CAS-NOSTAGE REST-REPLAY-CAS-OVER REST-REPLAY-ASIDE-GONE REST-REPLAY-ASIDE-MISSING REST-REPLAY-HOLD REST-REPLAY-ROLLBACK-CAS REST-REPLAY-ASIDE-UNREADABLE
//!
//! Snapshot and restore. Placeholder Ada / Berk only. The rare token
//! `quartzsnap91` is planted only in the Berk zip. These tests call the
//! public snapshot API. They do not copy the live database by hand.
//! Restart residues plant `tmp/snap-restore-journal`, then call `open_archive`.

mod crash_kill;

use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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
    let _guard = crash_kill::one_test_at_a_time();
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

fn main_db_file(arch: &Archive) -> String {
    let mut file = String::new();
    let queried = arch.conn.pragma_query(None, "database_list", |row| {
        let name: String = row.get(1)?;
        if name == "main" {
            file = row.get::<_, Option<String>>(2)?.unwrap_or_default();
        }
        Ok(())
    });
    if queried.is_err() {
        return String::new();
    }
    file
}

fn main_db_file_name(arch: &Archive) -> Option<String> {
    let file = main_db_file(arch);
    if file.is_empty() {
        return None;
    }
    Path::new(&file)
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .filter(|name| !name.is_empty())
}

fn snap_aside_dirs(root: &Path) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(root.join("tmp")) else {
        return found;
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if name.starts_with("snap-aside-") && entry.path().is_dir() {
            found.push(entry.path());
        }
    }
    found
}

fn aside_has_sqlite(root: &Path, bytes: &[u8]) -> bool {
    snap_aside_dirs(root)
        .into_iter()
        .any(|dir| fs::read(dir.join("archive.sqlite")).ok().as_deref() == Some(bytes))
}

/// `fn install_staged` through the line before the next function.
fn install_staged_slice(src: &str) -> &str {
    let start = src.find("fn install_staged").expect("fn install_staged");
    let rest = &src[start..];
    let after_line = rest.find('\n').map(|i| i + 1).unwrap_or(rest.len());
    let tail = &rest[after_line..];
    let mut rel = 0;
    for line in tail.split_inclusive('\n') {
        if function_line(line) {
            return &rest[..after_line + rel];
        }
        rel += line.len();
    }
    rest
}

fn function_line(line: &str) -> bool {
    let trimmed = line.trim_start();
    let rest = trimmed
        .strip_prefix("pub(crate) ")
        .or_else(|| trimmed.strip_prefix("pub(super) "))
        .or_else(|| trimmed.strip_prefix("pub "))
        .unwrap_or(trimmed);
    let rest = rest.strip_prefix("async ").unwrap_or(rest);
    let rest = rest.strip_prefix("unsafe ").unwrap_or(rest);
    rest.starts_with("fn ")
}

/// First index of `needle` outside comments and string literals.
fn call_pos(src: &str, needle: &str) -> Option<usize> {
    let bytes = src.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'/' && i + 1 < bytes.len() && bytes[i + 1] == b'/' {
            i += 2;
            while i < bytes.len() && bytes[i] != b'\n' {
                i += 1;
            }
            continue;
        }
        if bytes[i] == b'/' && i + 1 < bytes.len() && bytes[i + 1] == b'*' {
            i += 2;
            while i + 1 < bytes.len() && !(bytes[i] == b'*' && bytes[i + 1] == b'/') {
                i += 1;
            }
            i = (i + 2).min(bytes.len());
            continue;
        }
        if bytes[i] == b'"' {
            i += 1;
            while i < bytes.len() && bytes[i] != b'"' {
                if bytes[i] == b'\\' {
                    i += 2;
                    continue;
                }
                i += 1;
            }
            i = (i + 1).min(bytes.len());
            continue;
        }
        if src[i..].starts_with(needle) {
            return Some(i);
        }
        i += 1;
    }
    None
}

#[test]
fn rest_sidecar() {
    let _guard = crash_kill::one_test_at_a_time();
    let mut held = plant("side-ok");
    insert_message(&held, "ada before", "k-side-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-side-after");
    restore_snapshot(&mut held.arch, &id).unwrap();
    assert!(
        body_on(&held.arch, "ada before"),
        "ada before missing after restore"
    );
    assert!(
        !body_on(&held.arch, "ada after"),
        "ada after survived restore"
    );
    assert_eq!(
        main_db_file_name(&held.arch).as_deref(),
        Some("archive.sqlite"),
        "pragma_database_list main file is {:?}",
        main_db_file(&held.arch)
    );
    let asides = snap_aside_dirs(&held.arch.root);
    assert!(
        asides.is_empty(),
        "snap-aside directory remained under tmp: {asides:?}"
    );

    let mut held = plant("side-fault");
    insert_message(&held, "ada before", "k-side-fault-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-side-fault-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let snap_path = snap_dir(&held.arch, &id).join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    fs::create_dir(held.arch.root.join("archive.sqlite-journal")).unwrap();
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        err.is_err(),
        "restore_snapshot returned Ok while archive.sqlite-journal is a directory"
    );
    if live.exists() {
        let now = fs::read(&live).expect("live archive.sqlite exists but is not readable");
        assert!(
            now == before,
            "live archive.sqlite bytes are not the pre-restore database (len {} vs before {}, same as snapshot {})",
            now.len(),
            before.len(),
            now == snap
        );
        assert_eq!(
            main_db_file_name(&held.arch).as_deref(),
            Some("archive.sqlite"),
            "pragma_database_list main file is {:?}",
            main_db_file(&held.arch)
        );
    } else {
        assert_ne!(
            main_db_file_name(&held.arch).as_deref(),
            Some("archive.sqlite"),
            "pragma_database_list main file is {:?} while archive.sqlite is absent",
            main_db_file(&held.arch)
        );
    }
    let kept = (live.is_file() && fs::read(&live).ok().as_deref() == Some(before.as_slice()))
        || aside_has_sqlite(&held.arch.root, &before);
    assert!(
        kept,
        "pre-restore archive.sqlite bytes are neither the live file nor inside tmp/snap-aside-*"
    );
    assert!(
        fs::read(&snap_path).unwrap() == snap,
        "snapshot archive.sqlite changed"
    );
}

#[test]
fn rest_order() {
    let _guard = crash_kill::one_test_at_a_time();
    let src = include_str!("../src/db/snapshot.rs");
    let slice = install_staged_slice(src);
    assert!(
        slice.starts_with("fn install_staged"),
        "slice did not start at fn install_staged"
    );
    let delete_at = call_pos(slice, "delete_live_sidecars(");
    let move_at = call_pos(slice, "move_required(stage");
    assert!(
        matches!((delete_at, move_at), (Some(delete), Some(publish)) if delete < publish),
        "install_staged must call delete_live_sidecars( before move_required(stage) (delete at {delete_at:?}, move_required(stage) at {move_at:?})"
    );
}

#[test]
fn rest_live() {
    let _guard = crash_kill::one_test_at_a_time();
    let mut held = plant("live");
    insert_message(&held, "ada before", "k-live-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-live-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let snap_path = snap_dir(&held.arch, &id).join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    fs::create_dir(held.arch.root.join("archive.sqlite-journal")).unwrap();
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        err.is_err(),
        "restore_snapshot returned Ok while archive.sqlite-journal is a directory"
    );
    let now = fs::read(&live).ok();
    assert!(
        now.as_deref() == Some(before.as_slice()),
        "live archive.sqlite bytes are not the pre-restore database (exists {}, len {:?} vs before {}, same as snapshot {})",
        live.is_file(),
        now.as_ref().map(|b| b.len()),
        before.len(),
        now.as_deref() == Some(snap.as_slice())
    );
    assert_eq!(
        main_db_file_name(&held.arch).as_deref(),
        Some("archive.sqlite"),
        "pragma_database_list main file is {:?}",
        main_db_file(&held.arch)
    );
    assert!(
        body_on(&held.arch, "ada after"),
        "ada after missing after failed restore"
    );
    assert!(
        body_on(&held.arch, "ada before"),
        "ada before missing after failed restore"
    );
    assert!(
        fs::read(&snap_path).unwrap() == snap,
        "snapshot archive.sqlite changed"
    );
}

#[test]
fn rest_publish() {
    let _guard = crash_kill::one_test_at_a_time();
    let src = include_str!("../src/db/snapshot.rs");
    let slice = install_staged_slice(src);
    assert!(
        slice.starts_with("fn install_staged"),
        "slice did not start at fn install_staged"
    );
    let stage_at = call_pos(slice, "move_required(stage");
    assert!(
        stage_at.is_some(),
        "install_staged has no move_required(stage call"
    );
    let suffix = &slice[stage_at.unwrap() + "move_required(stage".len()..];
    let present_at = call_pos(suffix, "move_present(&aside");
    let err_at = call_pos(suffix, "return Err");
    assert!(
        matches!((present_at, err_at), (Some(present), Some(err)) if present < err),
        "after move_required(stage, move_present(&aside must occur before the first return Err (move_present(&aside at {present_at:?}, return Err at {err_at:?})"
    );
}

#[test]
fn rest_busy() {
    let _guard = crash_kill::one_test_at_a_time();
    let mut held = plant("busy-sql");
    insert_message(&held, "ada before", "k-busy-sql-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-busy-sql-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let snap_path = snap_dir(&held.arch, &id).join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    let reader = open_reader(&live);
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        matches!(
            &err,
            Err(CoreError::Fatal(msg)) if msg.starts_with("snapshot busy")
        ),
        "expected CoreError::Fatal starting with snapshot busy, got {err:?}"
    );
    let now = fs::read(&live).ok();
    assert!(
        now.as_deref() == Some(before.as_slice()),
        "live archive.sqlite bytes changed while the reader was open (exists {}, len {:?} vs before {})",
        live.is_file(),
        now.as_ref().map(|b| b.len()),
        before.len()
    );
    assert!(
        body_on(&held.arch, "ada after"),
        "ada after missing while restore was refused"
    );
    assert!(
        fs::read(&snap_path).unwrap() == snap,
        "snapshot archive.sqlite changed"
    );
    drop(reader);
    restore_snapshot(&mut held.arch, &id).unwrap();
    assert!(
        !body_on(&held.arch, "ada after"),
        "ada after survived restore"
    );
    assert!(
        body_on(&held.arch, "ada before"),
        "ada before missing after restore"
    );

    let mut held = plant("busy-toml");
    insert_message(&held, "ada before", "k-busy-toml-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-busy-toml-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let snap_path = snap_dir(&held.arch, &id).join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    let toml = File::open(held.arch.root.join("INTERLACE.toml")).unwrap();
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        matches!(
            &err,
            Err(CoreError::Fatal(msg)) if msg.starts_with("snapshot busy")
        ),
        "expected CoreError::Fatal starting with snapshot busy, got {err:?}"
    );
    let now = fs::read(&live).ok();
    assert!(
        now.as_deref() == Some(before.as_slice()),
        "live archive.sqlite bytes changed while INTERLACE.toml was open (exists {}, len {:?} vs before {})",
        live.is_file(),
        now.as_ref().map(|b| b.len()),
        before.len()
    );
    assert!(
        fs::read(&snap_path).unwrap() == snap,
        "snapshot archive.sqlite changed"
    );
    drop(toml);
    restore_snapshot(&mut held.arch, &id).unwrap();

    let mut held = plant("busy-cas");
    insert_message(&held, "ada before", "k-busy-cas-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-busy-cas-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let snap_path = snap_dir(&held.arch, &id).join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    let cas = held.arch.root.join("cas");
    fs::create_dir_all(&cas).unwrap();
    let hold = cas.join("hold.bin");
    fs::write(&hold, b"ada").unwrap();
    let hold_file = File::open(&hold).unwrap();
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        matches!(
            &err,
            Err(CoreError::Fatal(msg)) if msg.starts_with("snapshot busy")
        ),
        "expected CoreError::Fatal starting with snapshot busy, got {err:?}"
    );
    let now = fs::read(&live).ok();
    assert!(
        now.as_deref() == Some(before.as_slice()),
        "live archive.sqlite bytes changed while cas/hold.bin was open (exists {}, len {:?} vs before {})",
        live.is_file(),
        now.as_ref().map(|b| b.len()),
        before.len()
    );
    assert!(
        fs::read(&snap_path).unwrap() == snap,
        "snapshot archive.sqlite changed"
    );
    drop(hold_file);
    restore_snapshot(&mut held.arch, &id).unwrap();
}

#[test]
fn rest_resume() {
    let _guard = crash_kill::one_test_at_a_time();
    let mut held = plant("resume");
    insert_message(&held, "ada before", "k-resume-before");
    let id = snapshot_archive(&held.arch).unwrap();
    insert_message(&held, "ada after", "k-resume-after");
    let live = held.arch.root.join("archive.sqlite");
    let before = fs::read(&live).unwrap();
    let dir = snap_dir(&held.arch, &id);
    let snap_path = dir.join("archive.sqlite");
    let snap = fs::read(&snap_path).unwrap();
    assert!(
        before != snap,
        "void: live archive.sqlite and the snapshot file are the same bytes ({})",
        before.len()
    );
    let garbage = b"not-a-sqlite-database";
    fs::write(&snap_path, garbage).unwrap();
    let manifest_path = dir.join("MANIFEST.blake3");
    let text = fs::read_to_string(&manifest_path).unwrap();
    assert!(text.ends_with('\n') && !text.ends_with("\n\n"));
    let hex = blake3::hash(garbage).to_hex().to_string();
    let mut rewritten = String::new();
    let mut saw = false;
    for line in text.trim_end_matches('\n').split('\n') {
        let (old_hex, rel) = line.split_once(' ').expect("manifest line has no space");
        if rel == "archive.sqlite" {
            assert!(!saw, "manifest lists archive.sqlite twice");
            assert_eq!(old_hex.len(), 64);
            assert_ne!(old_hex, hex);
            rewritten.push_str(&hex);
            rewritten.push(' ');
            rewritten.push_str(rel);
            saw = true;
        } else {
            rewritten.push_str(line);
        }
        rewritten.push('\n');
    }
    assert!(saw, "manifest has no archive.sqlite line");
    fs::write(&manifest_path, rewritten).unwrap();
    let err = restore_snapshot(&mut held.arch, &id);
    assert!(
        err.is_err(),
        "restore_snapshot returned Ok for not-a-sqlite-database"
    );
    let now = fs::read(&live).ok();
    assert!(
        live.is_file() && now.as_deref() == Some(before.as_slice()),
        "live archive.sqlite bytes are not the pre-restore database (exists {}, len {:?} vs before {})",
        live.is_file(),
        now.as_ref().map(|b| b.len()),
        before.len()
    );
    assert_eq!(
        main_db_file_name(&held.arch).as_deref(),
        Some("archive.sqlite"),
        "pragma_database_list main file is {:?}",
        main_db_file(&held.arch)
    );
    assert!(
        body_on(&held.arch, "ada before"),
        "ada before missing after failed resume"
    );
    assert!(
        body_on(&held.arch, "ada after"),
        "ada after missing after failed resume"
    );
    assert_eq!(
        fs::read(&snap_path).unwrap(),
        garbage,
        "snapshot archive.sqlite no longer holds not-a-sqlite-database"
    );
}

fn body_exact(arch: &Archive, body: &str) -> bool {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM messages WHERE body_text = ?1",
            [body],
            |row| row.get::<_, i64>(0),
        )
        .unwrap()
        > 0
}

fn insert_berk_body(held: &Held, identity_id: i64, body: &str, key: &str) {
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
                identity_id,
                body,
                key
            ],
        )
        .unwrap();
}

fn crash_snapshot_child() {
    let root = PathBuf::from(std::env::var("INTERLACE_CRASH_ROOT").unwrap());
    let id = std::env::var("INTERLACE_CRASH_SNAP").unwrap();
    let arm = std::env::var("INTERLACE_CRASH_ARM").unwrap();
    let mut arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-SNAPSHOT child open");
    std::fs::write(&arm, b"1").unwrap();
    let result = restore_snapshot(&mut arch, &id);
    eprintln!("CRASH-SNAPSHOT restore returned: {result:?}");
    std::process::exit(86);
}

fn photo_hash(arch: &Archive) -> String {
    arch.conn
        .query_row(
            "SELECT photo_cas_hash FROM contacts_raw WHERE uid = 'ada-photo'",
            [],
            |row| row.get(0),
        )
        .unwrap()
}

#[test]
fn crash_snapshot() {
    let _guard = crash_kill::one_test_at_a_time();
    if crash_kill::child_enter() {
        crash_snapshot_child();
        return;
    }
    let held = plant("crash-snap");
    held.arch
        .conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Berk', 'berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk = held.arch.conn.last_insert_rowid();
    let b_snap = b"merhaba".to_vec();
    let b_live = b"merhaba iki".to_vec();
    insert_berk_body(&held, berk, "merhaba", "berk-m1");
    let h_snap = held.arch.cas_put(&b_snap, Some("image/jpeg")).unwrap();
    held.arch
        .conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 'ada', '/ada.vcf')",
            [],
        )
        .unwrap();
    let contact_src = held.arch.conn.last_insert_rowid();
    held.arch
        .conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, fn, photo_cas_hash) VALUES (?1, 'ada-photo', 'Ada', ?2)",
            rusqlite::params![contact_src, h_snap],
        )
        .unwrap();
    let id = snapshot_archive(&held.arch).unwrap();
    insert_berk_body(&held, berk, "merhaba iki", "berk-m2");
    let h_live = held.arch.cas_put(&b_live, Some("image/jpeg")).unwrap();
    held.arch
        .conn
        .execute(
            "UPDATE contacts_raw SET photo_cas_hash = ?1 WHERE uid = 'ada-photo'",
            [&h_live],
        )
        .unwrap();
    assert!(body_exact(&held.arch, "merhaba"));
    assert!(body_exact(&held.arch, "merhaba iki"));
    assert_eq!(held.arch.cas_get(&h_snap).unwrap(), b_snap);
    assert_eq!(held.arch.cas_get(&h_live).unwrap(), b_live);
    let root = held.arch.root.clone();
    drop(held);
    crash_kill::kill_at_seam(crash_kill::KillSpec {
        test_name: "crash_snapshot",
        mode: "snapshot",
        root: &root,
        target: "",
        extra: &[("INTERLACE_CRASH_SNAP", id.as_str())],
    });
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-SNAPSHOT open_archive");
    assert_snapshot_pair(&arch, &h_snap, &b_snap, &h_live, &b_live);
    let snap_got = arch.cas_get(&h_snap).ok();
    let live_got = arch.cas_get(&h_live).ok();
    let m1 = body_exact(&arch, "merhaba");
    let m2 = body_exact(&arch, "merhaba iki");
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-SNAPSHOT second open");
    assert_eq!(
        arch.cas_get(&h_snap).ok(),
        snap_got,
        "CRASH-SNAPSHOT second open changed H snapshot bytes"
    );
    assert_eq!(
        arch.cas_get(&h_live).ok(),
        live_got,
        "CRASH-SNAPSHOT second open changed H live bytes"
    );
    assert_eq!(body_exact(&arch, "merhaba"), m1);
    assert_eq!(body_exact(&arch, "merhaba iki"), m2);
    assert_snapshot_pair(&arch, &h_snap, &b_snap, &h_live, &b_live);
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

fn assert_snapshot_pair(arch: &Archive, h_snap: &str, b_snap: &[u8], h_live: &str, b_live: &[u8]) {
    let m1 = body_exact(arch, "merhaba");
    let m2 = body_exact(arch, "merhaba iki");
    let snap_got = arch.cas_get(h_snap).ok();
    let live_got = arch.cas_get(h_live).ok();
    let photo = photo_hash(arch);
    let pair_snap = m1
        && !m2
        && snap_got.as_deref() == Some(b_snap)
        && live_got.as_deref() != Some(b_live)
        && live_got.as_deref() != Some(b_snap)
        && photo == h_snap;
    let pair_live = m1
        && m2
        && snap_got.as_deref() == Some(b_snap)
        && live_got.as_deref() == Some(b_live)
        && photo == h_live;
    assert!(
        pair_snap,
        "CRASH-SNAPSHOT expected the snapshot pair (m1={m1}, m2={m2}, photo={photo}, snap_get={}, live_get={}, cas_dir={}, pair_live={pair_live})",
        fmt_bytes(snap_got.as_deref()),
        fmt_bytes(live_got.as_deref()),
        arch.root.join("cas").exists()
    );
}

fn fmt_bytes(bytes: Option<&[u8]>) -> String {
    match bytes {
        Some(bytes) => format!("{bytes:?}"),
        None => "missing".to_string(),
    }
}

fn replay_journal(root: &Path) -> PathBuf {
    root.join("tmp").join("snap-restore-journal")
}

fn plant_restore_journal(root: &Path, stage_name: &str, aside_name: &str) {
    fs::create_dir_all(root.join("tmp")).unwrap();
    let body = format!("1\nstage\ttmp/{stage_name}\naside\ttmp/{aside_name}\n");
    fs::write(replay_journal(root), body).unwrap();
}

fn move_if_present(from: &Path, to: &Path) {
    if from.exists() {
        fs::rename(from, to).unwrap();
    }
}

fn identity_on(arch: &Archive, normalized: &str) -> bool {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM identities WHERE value_normalized = ?1",
            [normalized],
            |row| row.get::<_, i64>(0),
        )
        .unwrap()
        > 0
}

/// Previous generation parked in the aside, new tree live, stage sqlite already gone.
fn plant_finished_publish(root: &Path) -> PathBuf {
    let stage = root.join("tmp").join("snap-stage-done");
    let aside = root.join("tmp").join("snap-aside-done");
    fs::create_dir_all(&stage).unwrap();
    fs::create_dir_all(&aside).unwrap();
    fs::write(stage.join("keep.txt"), b"keep").unwrap();
    fs::write(aside.join("archive.sqlite"), b"previous-generation").unwrap();
    fs::create_dir_all(aside.join("cas")).unwrap();
    fs::write(aside.join("cas").join("marker.txt"), b"old").unwrap();
    fs::write(aside.join("archive.sqlite-wal"), b"parked-old-wal").unwrap();
    fs::write(root.join("cas").join("marker.txt"), b"new").unwrap();
    plant_restore_journal(root, "snap-stage-done", "snap-aside-done");
    aside
}

fn assert_finished_aside(root: &Path, aside: &Path) {
    assert!(
        !replay_journal(root).exists(),
        "finished publish left the journal"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"new"
    );
    assert_eq!(
        fs::read(aside.join("archive.sqlite")).unwrap(),
        b"previous-generation"
    );
    assert_eq!(
        fs::read(aside.join("cas").join("marker.txt")).unwrap(),
        b"old"
    );
    assert_eq!(
        fs::read(aside.join("archive.sqlite-wal")).unwrap(),
        b"parked-old-wal"
    );
    assert!(!root
        .join("tmp")
        .join("snap-stage-done")
        .join("archive.sqlite")
        .exists());
}

#[test]
fn rest_replay_aside_cas() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("replay-cas");
    insert_message(&held, "ada before", "k-replay-cas");
    let root = held.arch.root.clone();
    drop(held);
    let stage = root.join("tmp").join("snap-stage-cas");
    let aside = root.join("tmp").join("snap-aside-cas");
    fs::create_dir_all(&stage).unwrap();
    fs::create_dir_all(&aside).unwrap();
    let dummy = b"stage-sqlite-not-published";
    fs::write(stage.join("archive.sqlite"), dummy).unwrap();
    fs::write(root.join("cas").join("marker.txt"), b"live-cas").unwrap();
    fs::rename(root.join("cas"), aside.join("cas")).unwrap();
    plant_restore_journal(&root, "snap-stage-cas", "snap-aside-cas");
    let arch = open_archive(&root, LockMode::Exclusive).expect("aside cas replay");
    assert!(body_on(&arch, "ada before"), "pre-restore message missing");
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"live-cas"
    );
    assert!(!aside.join("cas").exists(), "aside cas was not put back");
    assert_eq!(fs::read(stage.join("archive.sqlite")).unwrap(), dummy);
    assert_ne!(fs::read(root.join("archive.sqlite")).unwrap(), dummy);
    assert!(!replay_journal(&root).exists(), "journal survived put-back");
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

fn replay_stranded_wal(stage_present: bool) {
    let label = if stage_present {
        "replay-wal"
    } else {
        "replay-wal-nostage"
    };
    let held = plant(label);
    insert_message(&held, "ada before", "k-replay-wal");
    let _: i64 = held
        .arch
        .conn
        .query_row("PRAGMA wal_checkpoint(TRUNCATE)", [], |row| row.get(0))
        .unwrap();
    held.arch
        .conn
        .pragma_update(None, "wal_autocheckpoint", 0i64)
        .unwrap();
    held.arch
        .conn
        .set_db_config(
            rusqlite::config::DbConfig::SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,
            true,
        )
        .unwrap();
    held.arch
        .conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Wal', 'wal-residue', 'Wal')",
            [],
        )
        .unwrap();
    let root = held.arch.root.clone();
    drop(held);
    let wal = root.join("archive.sqlite-wal");
    assert!(
        wal.is_file() && fs::metadata(&wal).unwrap().len() > 0,
        "wal was checkpointed on close; residue fixture is void"
    );
    let stage_name = "snap-stage-wal";
    let aside = root.join("tmp").join("snap-aside-wal");
    fs::create_dir_all(&aside).unwrap();
    fs::rename(&wal, aside.join("archive.sqlite-wal")).unwrap();
    move_if_present(
        &root.join("archive.sqlite-shm"),
        &aside.join("archive.sqlite-shm"),
    );
    fs::write(root.join("cas").join("marker.txt"), b"cas-stays").unwrap();
    if stage_present {
        let stage = root.join("tmp").join(stage_name);
        fs::create_dir_all(&stage).unwrap();
        fs::write(stage.join("archive.sqlite"), b"stage-sqlite-still-here").unwrap();
    }
    plant_restore_journal(&root, stage_name, "snap-aside-wal");
    let arch = open_archive(&root, LockMode::Exclusive).expect("stranded wal replay");
    assert!(body_on(&arch, "ada before"), "checkpointed message missing");
    assert!(
        identity_on(&arch, "wal-residue"),
        "wal frame was not put back"
    );
    assert!(
        !aside.join("archive.sqlite-wal").exists(),
        "wal stayed in the aside"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"cas-stays"
    );
    assert!(
        !replay_journal(&root).exists(),
        "journal survived wal put-back"
    );
    let stage = root.join("tmp").join(stage_name);
    if stage_present {
        assert_eq!(
            fs::read(stage.join("archive.sqlite")).unwrap(),
            b"stage-sqlite-still-here"
        );
    } else {
        assert!(!stage.exists(), "replay created a stage directory");
    }
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_aside_wal() {
    let _guard = crash_kill::one_test_at_a_time();
    replay_stranded_wal(true);
}

#[test]
fn rest_replay_wal_without_stage() {
    let _guard = crash_kill::one_test_at_a_time();
    replay_stranded_wal(false);
}

/// Puts the aside back to `0o755` on drop, including when an assert panics.
struct AsideModeGuard {
    path: PathBuf,
}

impl AsideModeGuard {
    fn deny(path: &Path) -> Self {
        let guard = Self {
            path: path.to_path_buf(),
        };
        let mut perms = fs::metadata(&guard.path)
            .expect("REST-REPLAY-ASIDE-UNREADABLE aside metadata")
            .permissions();
        perms.set_mode(0o000);
        fs::set_permissions(&guard.path, perms).expect("REST-REPLAY-ASIDE-UNREADABLE chmod 0o000");
        guard
    }
}

impl Drop for AsideModeGuard {
    fn drop(&mut self) {
        let perms = fs::Permissions::from_mode(0o755);
        if let Err(err) = fs::set_permissions(&self.path, perms) {
            if !std::thread::panicking() {
                panic!("REST-REPLAY-ASIDE-UNREADABLE mode restore failed: {err}");
            }
        }
    }
}

#[test]
fn rest_replay_aside_unreadable() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("replay-wal-unreadable");
    insert_message(&held, "ada before", "k-replay-wal");
    let _: i64 = held
        .arch
        .conn
        .query_row("PRAGMA wal_checkpoint(TRUNCATE)", [], |row| row.get(0))
        .unwrap();
    held.arch
        .conn
        .pragma_update(None, "wal_autocheckpoint", 0i64)
        .unwrap();
    held.arch
        .conn
        .set_db_config(
            rusqlite::config::DbConfig::SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,
            true,
        )
        .unwrap();
    held.arch
        .conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Wal', 'wal-residue', 'Wal')",
            [],
        )
        .unwrap();
    let root = held.arch.root.clone();
    drop(held);
    let wal = root.join("archive.sqlite-wal");
    assert!(
        wal.is_file() && fs::metadata(&wal).unwrap().len() > 0,
        "wal was checkpointed on close; residue fixture is void"
    );
    let stage_name = "snap-stage-wal";
    let aside = root.join("tmp").join("snap-aside-wal");
    fs::create_dir_all(&aside).unwrap();
    fs::rename(&wal, aside.join("archive.sqlite-wal")).unwrap();
    move_if_present(
        &root.join("archive.sqlite-shm"),
        &aside.join("archive.sqlite-shm"),
    );
    fs::write(root.join("cas").join("marker.txt"), b"cas-stays").unwrap();
    let stage = root.join("tmp").join(stage_name);
    assert!(
        !stage.exists(),
        "REST-REPLAY-ASIDE-UNREADABLE stage directory was planted"
    );
    let wal_aside = aside.join("archive.sqlite-wal");
    let parked = fs::read(&wal_aside).unwrap();
    assert!(
        !parked.is_empty(),
        "wal was checkpointed on close; residue fixture is void"
    );
    plant_restore_journal(&root, stage_name, "snap-aside-wal");
    {
        let _mode = AsideModeGuard::deny(&aside);
        assert_eq!(
            fs::metadata(&aside).unwrap().permissions().mode() & 0o777,
            0o000,
            "REST-REPLAY-ASIDE-UNREADABLE aside mode was not 0o000"
        );
        let opened = open_archive(&root, LockMode::Exclusive);
        let journal_there = replay_journal(&root).is_file();
        let err = match opened {
            Ok(_) => panic!(
                "REST-REPLAY-ASIDE-UNREADABLE open_archive returned Ok while aside was mode 0o000; journal still present={journal_there}"
            ),
            Err(err) => err,
        };
        assert!(
            journal_there,
            "REST-REPLAY-ASIDE-UNREADABLE journal was removed ({err})"
        );
    }
    assert!(
        wal_aside.is_file() && fs::read(&wal_aside).unwrap() == parked,
        "REST-REPLAY-ASIDE-UNREADABLE aside wal was not still non-empty after mode restore"
    );
    let arch = open_archive(&root, LockMode::Exclusive).expect("REST-REPLAY-ASIDE-UNREADABLE");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-ASIDE-UNREADABLE checkpointed message missing"
    );
    assert!(
        identity_on(&arch, "wal-residue"),
        "REST-REPLAY-ASIDE-UNREADABLE wal-residue missing"
    );
    assert!(
        !wal_aside.exists(),
        "REST-REPLAY-ASIDE-UNREADABLE aside wal remained"
    );
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-ASIDE-UNREADABLE journal remained"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"cas-stays",
        "REST-REPLAY-ASIDE-UNREADABLE cas marker"
    );
    assert!(
        !stage.exists(),
        "REST-REPLAY-ASIDE-UNREADABLE created the stage directory"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_missing_stage() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("replay-stage");
    insert_message(&held, "ada before", "k-replay-stage");
    let root = held.arch.root.clone();
    drop(held);
    let aside = root.join("tmp").join("snap-aside-residue");
    fs::create_dir_all(&aside).unwrap();
    for name in [
        "INTERLACE.toml",
        "archive.sqlite",
        "cas",
        "archive.sqlite-wal",
        "archive.sqlite-shm",
        "archive.sqlite-journal",
    ] {
        move_if_present(&root.join(name), &aside.join(name));
    }
    assert!(aside.join("archive.sqlite").is_file());
    assert!(!root.join("tmp").join("snap-stage-residue").exists());
    plant_restore_journal(&root, "snap-stage-residue", "snap-aside-residue");
    let arch = open_archive(&root, LockMode::Exclusive).expect("missing stage replay");
    assert!(
        body_on(&arch, "ada before"),
        "aside database was not put back"
    );
    assert!(root.join("INTERLACE.toml").is_file());
    assert!(root.join("cas").is_dir());
    assert!(
        !replay_journal(&root).exists(),
        "journal survived missing-stage put-back"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_finished_publish() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("replay-done");
    insert_message(&held, "ada before", "k-replay-done");
    let root = held.arch.root.clone();
    drop(held);
    let aside = plant_finished_publish(&root);
    let arch = open_archive(&root, LockMode::Exclusive).expect("finished publish replay");
    assert!(body_on(&arch, "ada before"), "live database changed");
    assert_finished_aside(&root, &aside);
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

fn replay_lock_child() -> ! {
    let root = PathBuf::from(std::env::var("INTERLACE_REPLAY_LOCK_ROOT").unwrap());
    match open_archive(&root, LockMode::Shared) {
        Err(CoreError::Lock { .. }) => std::process::exit(0),
        Ok(_) => std::process::exit(2),
        Err(err) => {
            eprintln!("replay lock child: {err}");
            std::process::exit(3);
        }
    }
}

#[test]
fn rest_replay_shared_exclusive() {
    let _guard = crash_kill::one_test_at_a_time();
    if std::env::var_os("INTERLACE_REPLAY_LOCK_CHILD").is_some() {
        replay_lock_child();
    }
    let held = plant("replay-lock");
    insert_message(&held, "ada before", "k-replay-lock");
    let root = held.arch.root.clone();
    drop(held);
    let holder = open_archive(&root, LockMode::Shared).expect("shared holder");
    assert!(body_on(&holder, "ada before"));
    let aside = plant_finished_publish(&root);
    let exe = std::env::current_exe().expect("current_exe");
    let child = Command::new(exe)
        .arg("rest_replay_shared_exclusive")
        .arg("--exact")
        .arg("--test-threads=1")
        .env("INTERLACE_REPLAY_LOCK_CHILD", "1")
        .env("INTERLACE_REPLAY_LOCK_ROOT", &root)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn replay lock child");
    let out = child.wait_with_output().expect("wait replay lock child");
    assert_eq!(
        out.status.code(),
        Some(0),
        "shared open with a journal took the lock (stdout {}, stderr {})",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        replay_journal(&root).is_file(),
        "child replayed the journal under the shared holder"
    );
    drop(holder);
    let arch = open_archive(&root, LockMode::Exclusive).expect("replay after shared holder");
    assert!(body_on(&arch, "ada before"));
    assert_finished_aside(&root, &aside);
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_cas_nostage() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("cas-nostage");
    insert_message(&held, "ada before", "k-cas-nostage");
    let root = held.arch.root.clone();
    drop(held);
    let aside = root.join("tmp").join("snap-aside-casnostage");
    let stage = root.join("tmp").join("snap-stage-casnostage");
    fs::create_dir_all(&aside).unwrap();
    fs::write(root.join("cas").join("marker.txt"), b"live-cas").unwrap();
    fs::rename(root.join("cas"), aside.join("cas")).unwrap();
    assert!(root.join("archive.sqlite").is_file(), "live sqlite moved");
    assert!(root.join("INTERLACE.toml").is_file(), "live toml moved");
    assert!(!root.join("cas").exists(), "live cas was not parked");
    assert!(!stage.exists(), "stage directory was planted");
    plant_restore_journal(&root, "snap-stage-casnostage", "snap-aside-casnostage");
    let arch = open_archive(&root, LockMode::Shared).expect("REST-REPLAY-CAS-NOSTAGE");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-CAS-NOSTAGE pre-restore message missing"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"live-cas",
        "REST-REPLAY-CAS-NOSTAGE cas marker"
    );
    assert!(
        !aside.join("cas").exists(),
        "REST-REPLAY-CAS-NOSTAGE aside cas remained"
    );
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-CAS-NOSTAGE journal remained"
    );
    assert!(
        !stage.exists(),
        "REST-REPLAY-CAS-NOSTAGE created the stage directory"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_cas_over() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("cas-over");
    insert_message(&held, "ada before", "k-cas-over");
    let _: i64 = held
        .arch
        .conn
        .query_row("PRAGMA wal_checkpoint(TRUNCATE)", [], |row| row.get(0))
        .unwrap();
    held.arch
        .conn
        .pragma_update(None, "wal_autocheckpoint", 0i64)
        .unwrap();
    held.arch
        .conn
        .set_db_config(
            rusqlite::config::DbConfig::SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,
            true,
        )
        .unwrap();
    held.arch
        .conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Wal', 'wal-over-live', 'Wal')",
            [],
        )
        .unwrap();
    let root = held.arch.root.clone();
    drop(held);
    let wal = root.join("archive.sqlite-wal");
    assert!(
        wal.is_file() && fs::metadata(&wal).unwrap().len() > 0,
        "wal was checkpointed on close; residue fixture is void"
    );
    let aside = root.join("tmp").join("snap-aside-casover");
    let stage = root.join("tmp").join("snap-stage-casover");
    fs::create_dir_all(&aside).unwrap();
    fs::rename(&wal, aside.join("archive.sqlite-wal")).unwrap();
    let had_shm = root.join("archive.sqlite-shm").exists();
    move_if_present(
        &root.join("archive.sqlite-shm"),
        &aside.join("archive.sqlite-shm"),
    );
    fs::write(root.join("cas").join("marker.txt"), b"live-cas").unwrap();
    fs::create_dir_all(aside.join("cas")).unwrap();
    fs::write(aside.join("cas").join("marker.txt"), b"aside-cas").unwrap();
    assert!(
        !aside.join("archive.sqlite").exists(),
        "aside holds archive.sqlite"
    );
    assert!(!stage.exists(), "stage directory was planted");
    assert!(root.join("INTERLACE.toml").is_file());
    assert!(root.join("archive.sqlite").is_file());
    assert!(root.join("cas").is_dir());
    plant_restore_journal(&root, "snap-stage-casover", "snap-aside-casover");
    let arch = open_archive(&root, LockMode::Exclusive).expect("REST-REPLAY-CAS-OVER");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-CAS-OVER checkpointed message missing"
    );
    assert!(
        identity_on(&arch, "wal-over-live"),
        "REST-REPLAY-CAS-OVER wal-over-live missing"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"aside-cas",
        "REST-REPLAY-CAS-OVER live cas was not replaced"
    );
    assert!(
        !aside.join("cas").exists(),
        "REST-REPLAY-CAS-OVER aside cas remained"
    );
    assert!(
        !aside.join("archive.sqlite-wal").exists(),
        "REST-REPLAY-CAS-OVER aside wal remained"
    );
    if had_shm {
        assert!(
            !aside.join("archive.sqlite-shm").exists(),
            "REST-REPLAY-CAS-OVER aside shm remained"
        );
    }
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-CAS-OVER journal remained"
    );
    assert!(
        !stage.exists(),
        "REST-REPLAY-CAS-OVER created the stage directory"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_aside_gone() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("aside-gone");
    insert_message(&held, "ada before", "k-aside-gone");
    let root = held.arch.root.clone();
    drop(held);
    let stage = root.join("tmp").join("snap-stage-asidegone");
    fs::create_dir_all(&stage).unwrap();
    fs::write(stage.join("archive.sqlite"), b"stage-not-live").unwrap();
    fs::write(root.join("cas").join("marker.txt"), b"live-cas").unwrap();
    assert!(
        !root.join("tmp").join("snap-aside-asidegone").exists(),
        "aside directory was planted"
    );
    plant_restore_journal(&root, "snap-stage-asidegone", "snap-aside-asidegone");
    let arch = open_archive(&root, LockMode::Shared).expect("REST-REPLAY-ASIDE-GONE");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-ASIDE-GONE Ada's message missing"
    );
    assert!(
        identity_on(&arch, "ada"),
        "REST-REPLAY-ASIDE-GONE Ada is missing"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"live-cas",
        "REST-REPLAY-ASIDE-GONE cas marker"
    );
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-ASIDE-GONE journal remained"
    );
    assert_eq!(
        fs::read(stage.join("archive.sqlite")).unwrap(),
        b"stage-not-live",
        "REST-REPLAY-ASIDE-GONE stage sqlite changed"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_aside_missing() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("aside-missing");
    insert_message(&held, "ada before", "k-aside-missing");
    let root = held.arch.root.clone();
    drop(held);
    let stage = root.join("tmp").join("snap-stage-asidegone");
    fs::create_dir_all(&stage).unwrap();
    fs::write(stage.join("archive.sqlite"), b"stage-not-live").unwrap();
    fs::remove_file(root.join("archive.sqlite")).unwrap();
    assert!(
        !root.join("tmp").join("snap-aside-asidegone").exists(),
        "aside directory was planted"
    );
    plant_restore_journal(&root, "snap-stage-asidegone", "snap-aside-asidegone");
    let err = match open_archive(&root, LockMode::Shared) {
        Ok(_) => panic!("REST-REPLAY-ASIDE-MISSING opened"),
        Err(err) => err,
    };
    assert!(
        replay_journal(&root).is_file(),
        "REST-REPLAY-ASIDE-MISSING journal was removed ({err})"
    );
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_hold() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("hold");
    insert_message(&held, "ada before", "k-hold");
    let root = held.arch.root.clone();
    drop(held);
    fs::write(root.join("cas").join("marker.txt"), b"live-cas").unwrap();
    let stage = root.join("tmp").join("snap-stage-hold");
    let aside = root.join("tmp").join("snap-aside-hold");
    fs::create_dir_all(&stage).unwrap();
    fs::create_dir_all(&aside).unwrap();
    for name in [
        "INTERLACE.toml",
        "archive.sqlite",
        "cas",
        "archive.sqlite-journal",
        "archive.sqlite-shm",
        "archive.sqlite-wal",
    ] {
        assert!(
            !aside.join(name).exists(),
            "REST-REPLAY-HOLD aside planted {name}"
        );
    }
    assert!(
        !stage.join("archive.sqlite").exists(),
        "REST-REPLAY-HOLD stage sqlite was planted"
    );
    let hold = root.join("tmp").join("snap-hold-cas-residue");
    fs::create_dir_all(&hold).unwrap();
    fs::write(hold.join("marker.txt"), b"held").unwrap();
    plant_restore_journal(&root, "snap-stage-hold", "snap-aside-hold");
    let arch = open_archive(&root, LockMode::Exclusive).expect("REST-REPLAY-HOLD");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-HOLD Ada's message missing"
    );
    assert!(identity_on(&arch, "ada"), "REST-REPLAY-HOLD Ada is missing");
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"live-cas",
        "REST-REPLAY-HOLD cas marker"
    );
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-HOLD journal remained"
    );
    assert!(
        !hold.exists(),
        "REST-REPLAY-HOLD snap-hold residue remained"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}

#[test]
fn rest_replay_rollback_cas() {
    let _guard = crash_kill::one_test_at_a_time();
    let held = plant("rollback-cas");
    insert_message(&held, "ada before", "k-rollback-cas");
    let root = held.arch.root.clone();
    drop(held);
    let aside = root.join("tmp").join("snap-aside-rollbackcas");
    let stage = root.join("tmp").join("snap-stage-rollbackcas");
    fs::create_dir_all(&aside).unwrap();
    fs::write(root.join("cas").join("marker.txt"), b"old-cas").unwrap();
    fs::rename(root.join("cas"), aside.join("cas")).unwrap();
    fs::create_dir_all(stage.join("cas")).unwrap();
    fs::write(stage.join("cas").join("marker.txt"), b"stage-cas").unwrap();
    assert!(
        root.join("archive.sqlite").is_file(),
        "REST-REPLAY-ROLLBACK-CAS live sqlite moved"
    );
    assert!(
        root.join("INTERLACE.toml").is_file(),
        "REST-REPLAY-ROLLBACK-CAS live toml moved"
    );
    assert!(
        !root.join("cas").exists(),
        "REST-REPLAY-ROLLBACK-CAS live cas was not parked"
    );
    assert!(
        !aside.join("archive.sqlite").exists(),
        "REST-REPLAY-ROLLBACK-CAS aside holds archive.sqlite"
    );
    assert!(
        !stage.join("archive.sqlite").exists(),
        "REST-REPLAY-ROLLBACK-CAS stage sqlite was planted"
    );
    plant_restore_journal(&root, "snap-stage-rollbackcas", "snap-aside-rollbackcas");
    let arch = open_archive(&root, LockMode::Exclusive).expect("REST-REPLAY-ROLLBACK-CAS");
    assert!(
        body_on(&arch, "ada before"),
        "REST-REPLAY-ROLLBACK-CAS Ada's message missing"
    );
    assert_eq!(
        fs::read(root.join("cas").join("marker.txt")).unwrap(),
        b"old-cas",
        "REST-REPLAY-ROLLBACK-CAS live cas marker"
    );
    assert_eq!(
        fs::read(stage.join("cas").join("marker.txt")).unwrap(),
        b"stage-cas",
        "REST-REPLAY-ROLLBACK-CAS stage cas marker"
    );
    assert!(
        !aside.join("cas").exists(),
        "REST-REPLAY-ROLLBACK-CAS aside cas remained"
    );
    assert!(
        !replay_journal(&root).exists(),
        "REST-REPLAY-ROLLBACK-CAS journal remained"
    );
    drop(arch);
    let _ = fs::remove_dir_all(&root);
}
