//! CAS1–CAS3 must-pass matrix.
//!
//! Matrix IDs (gate grep): CAS1 CAS2 CAS3 CRASH-GC STORE-MISMATCH RECLAIM-MISMATCH-OPEN REATTACH-DIR-OPEN RECLAIM-STAT-RETRY RECLAIM-NOTDIR-RETRY

mod crash_kill;

use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::cas::{cas_blob_path, validate_zip_entry_name};
use interlace_core::db::{init_archive, LockMode};
use interlace_core::{open_archive, CoreError};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-cas-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    p
}

#[test]
fn cas1_put_get_idempotent() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let h1 = arch.cas_put(b"hello cas", Some("text/plain")).unwrap();
    let h2 = arch.cas_put(b"hello cas", Some("text/plain")).unwrap();
    assert_eq!(h1, h2);
    assert_eq!(h1.len(), 64);
    assert_eq!(arch.cas_get(&h1).unwrap(), b"hello cas");
    let n: i64 = arch
        .conn
        .query_row("SELECT COUNT(*) FROM cas_blobs", [], |r| r.get(0))
        .unwrap();
    assert_eq!(n, 1);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn cas2_zip_slip_rejected() {
    let _guard = crash_kill::one_test_at_a_time();
    assert!(matches!(
        validate_zip_entry_name("../etc/passwd"),
        Err(CoreError::ZipSlip(_))
    ));
    assert!(matches!(
        validate_zip_entry_name("/absolute/path.jpg"),
        Err(CoreError::ZipSlip(_))
    ));
    assert!(matches!(
        validate_zip_entry_name("C:/windows/x"),
        Err(CoreError::ZipSlip(_))
    ));
    assert!(matches!(
        validate_zip_entry_name("~/.ssh/id_rsa"),
        Err(CoreError::ZipSlip(_))
    ));
    assert!(matches!(
        validate_zip_entry_name("foo/../../etc/passwd"),
        Err(CoreError::ZipSlip(_))
    ));
    assert!(validate_zip_entry_name("IMG-2024-WA0001.jpg").is_ok());
    assert!(validate_zip_entry_name("media/sub/file.opus").is_ok());
}

#[test]
fn cas3_gc_unreferenced_only() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let orphan = arch.cas_put(b"orphan", None).unwrap();
    let keep = arch.cas_put(b"keep-me", None).unwrap();

    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 't', '/t.vcf')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, photo_cas_hash) VALUES (1, 'u1', ?1)",
            [&keep],
        )
        .unwrap();

    let removed = arch.doctor(false, true, true).unwrap();
    let _ = removed;
    let gone = arch.cas_get(&orphan);
    assert!(gone.is_err(), "orphan blob must be collected");
    assert_eq!(arch.cas_get(&keep).unwrap(), b"keep-me");

    // after dropping the reference, gc removes keep too
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).unwrap();
    arch.conn
        .execute("UPDATE contacts_raw SET photo_cas_hash = NULL", [])
        .unwrap();
    arch.gc_cas().unwrap();
    assert!(arch.cas_get(&keep).is_err());
    let _ = std::fs::remove_dir_all(&root);
}

fn gc_child() {
    let root = std::path::PathBuf::from(std::env::var("INTERLACE_CRASH_ROOT").unwrap());
    let arm = std::env::var("INTERLACE_CRASH_ARM").unwrap();
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-GC child open");
    std::fs::write(&arm, b"1").unwrap();
    let result = arch.gc_cas();
    eprintln!("CRASH-GC gc_cas returned: {result:?}");
    std::process::exit(86);
}

#[test]
fn crash_gc() {
    let _guard = crash_kill::one_test_at_a_time();
    if crash_kill::child_enter() {
        gc_child();
        return;
    }
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let orphan_bytes = b"merhaba iki".to_vec();
    let orphan = arch.cas_put(&orphan_bytes, None).unwrap();
    let photo = b"merhaba".to_vec();
    let photo_hash = arch.cas_put(&photo, Some("image/jpeg")).unwrap();
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
            rusqlite::params![src, photo_hash],
        )
        .unwrap();
    let orphan_path = cas_blob_path(&root, &orphan).unwrap();
    let photo_path = cas_blob_path(&root, &photo_hash).unwrap();
    assert!(orphan_path.is_file(), "fixture orphan file");
    assert_eq!(std::fs::read(&photo_path).unwrap(), photo);
    let root = arch.root.clone();
    drop(arch);
    crash_kill::kill_at_seam(crash_kill::KillSpec {
        test_name: "crash_gc",
        mode: "gc",
        root: &root,
        target: &orphan,
        extra: &[],
    });
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-GC open_archive");
    assert_eq!(
        std::fs::read(&photo_path).unwrap(),
        photo,
        "CRASH-GC replaced Ada's photo"
    );
    assert_eq!(arch.cas_get(&photo_hash).unwrap(), photo);
    assert!(
        !orphan_path.exists(),
        "CRASH-GC orphan file still present after the kill"
    );
    let row: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&orphan],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(row, 0, "CRASH-GC cas_blobs row remained for {orphan}");
    let err = arch
        .cas_get(&orphan)
        .expect_err("CRASH-GC cas_get should be the missing error");
    let shown = err.to_string();
    assert!(
        shown.contains(&format!("cas blob missing: {orphan}")),
        "CRASH-GC cas_get: {shown}"
    );
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).expect("CRASH-GC second open");
    assert_eq!(
        std::fs::read(&photo_path).unwrap(),
        photo,
        "CRASH-GC second open replaced Ada's photo"
    );
    assert!(
        !orphan_path.exists(),
        "CRASH-GC second open recreated the unreferenced bytes"
    );
    let err = arch
        .cas_get(&orphan)
        .expect_err("CRASH-GC second open cas_get");
    assert!(
        err.to_string()
            .contains(&format!("cas blob missing: {orphan}")),
        "CRASH-GC second open cas_get: {err}"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn store_mismatch() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let b1 = b"merhaba".to_vec();
    let b2 = b"merhaba iki".to_vec();
    let h = arch.cas_put(&b1, None).unwrap();
    let path = cas_blob_path(&root, &h).unwrap();
    std::fs::write(&path, &b2).unwrap();
    let other = b"ada photo".to_vec();
    let h2 = arch.cas_put(&other, Some("image/jpeg")).unwrap();
    let other_path = cas_blob_path(&root, &h2).unwrap();
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
            rusqlite::params![src, h2],
        )
        .unwrap();
    let put = arch.cas_put(&b1, None);
    let put_shown = match &put {
        Ok(hash) => format!("Ok({hash})"),
        Err(err) => err.to_string(),
    };
    assert!(
        put_shown.contains(&format!("cas blob bytes are not {h}")),
        "STORE-MISMATCH cas_put: {put_shown}"
    );
    let got = arch.cas_get(&h);
    assert_store_mismatch_get(&got, &h, &b1, &b2, "STORE-MISMATCH");
    let before = std::fs::read(&path).unwrap();
    assert_eq!(
        before, b2,
        "STORE-MISMATCH file is not the different bytes before second open"
    );
    assert_ne!(before, other, "fixture collision");
    assert_eq!(std::fs::read(&other_path).unwrap(), other);
    let root = arch.root.clone();
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).expect("STORE-MISMATCH second open");
    let after = std::fs::read(&path).unwrap();
    assert_eq!(
        after, before,
        "STORE-MISMATCH second open copied or replaced bytes at hash(B1)"
    );
    assert_eq!(
        after, b2,
        "STORE-MISMATCH file is not the different bytes after second open"
    );
    assert_ne!(
        after, other,
        "STORE-MISMATCH second open put Ada's other photo on hash(B1)"
    );
    assert_store_mismatch_get(
        &arch.cas_get(&h),
        &h,
        &b1,
        &b2,
        "STORE-MISMATCH second open",
    );
    assert_eq!(std::fs::read(&other_path).unwrap(), other);
    assert_eq!(arch.cas_get(&h2).unwrap(), other);
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

fn assert_store_mismatch_get(
    got: &Result<Vec<u8>, CoreError>,
    hash: &str,
    b1: &[u8],
    b2: &[u8],
    label: &str,
) {
    let shown = match got {
        Ok(bytes) => format!("{bytes:?}"),
        Err(err) => err.to_string(),
    };
    assert!(
        got.as_deref().ok() != Some(b1) && got.as_deref().ok() != Some(b2),
        "{label} cas_get returned a buffer: {shown}"
    );
    assert!(
        shown.contains(&format!("cas blob missing: {hash}")),
        "{label} cas_get: {shown}"
    );
}

#[test]
fn reclaim_mismatch_open() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let hash = "ab".repeat(32);
    assert_eq!(hash.len(), 64);
    let rel = format!("cas/ab/ab/{hash}");
    let value = format!("1\nu\t{hash}\t{rel}\n");
    arch.conn
        .execute(
            "INSERT INTO settings(key, value) VALUES ('cas_pending_files', ?1)",
            [&value],
        )
        .unwrap();
    let dir = root.join("cas").join("ab").join("ab").join(&hash);
    std::fs::create_dir_all(&dir).unwrap();
    let keep = dir.join("keep.txt");
    std::fs::write(&keep, b"not-the-blob").unwrap();
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "fixture planted a cas_blobs row");
    let root = arch.root.clone();
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).expect("RECLAIM-MISMATCH-OPEN");
    let settings: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM settings WHERE key = 'cas_pending_files'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(settings, 0, "RECLAIM-MISMATCH-OPEN settings row remained");
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "RECLAIM-MISMATCH-OPEN cas_blobs row was put back");
    assert_eq!(
        std::fs::read(&keep).unwrap(),
        b"not-the-blob",
        "RECLAIM-MISMATCH-OPEN keep.txt changed"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn reattach_dir_open() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let hash = "ab".repeat(32);
    assert_eq!(hash.len(), 64);
    let source_rel = format!("cas/ff/ff/{hash}");
    let dest_rel = format!("cas/ab/ab/{hash}");
    let value = format!("1\nr\t{hash}\t{source_rel}\t{dest_rel}\n");
    arch.conn
        .execute(
            "INSERT INTO settings(key, value) VALUES ('cas_pending_files', ?1)",
            [&value],
        )
        .unwrap();
    let source = root.join("cas").join("ff").join("ff").join(&hash);
    std::fs::create_dir_all(source.parent().unwrap()).unwrap();
    std::fs::write(&source, b"not-the-blob").unwrap();
    let dest = root.join("cas").join("ab").join("ab").join(&hash);
    std::fs::create_dir_all(&dest).unwrap();
    let keep = dest.join("keep.txt");
    std::fs::write(&keep, b"keep-dir").unwrap();
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "fixture planted a cas_blobs row");
    let root = arch.root.clone();
    drop(arch);
    let arch = open_archive(&root, LockMode::Exclusive).expect("REATTACH-DIR-OPEN");
    let settings: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM settings WHERE key = 'cas_pending_files'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(settings, 0, "REATTACH-DIR-OPEN settings row remained");
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "REATTACH-DIR-OPEN cas_blobs row was put back");
    assert_eq!(
        std::fs::read(&keep).unwrap(),
        b"keep-dir",
        "REATTACH-DIR-OPEN keep.txt changed"
    );
    assert_eq!(
        std::fs::read(&source).unwrap(),
        b"not-the-blob",
        "REATTACH-DIR-OPEN source file changed"
    );
    let got = arch.cas_get(&hash);
    let shown = match &got {
        Ok(bytes) => format!("{bytes:?}"),
        Err(err) => err.to_string(),
    };
    assert!(
        got.is_err(),
        "REATTACH-DIR-OPEN cas_get returned Ok: {shown}"
    );
    assert!(
        shown.contains(&format!("cas blob missing: {hash}")),
        "REATTACH-DIR-OPEN cas_get: {shown}"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn reclaim_stat_retry() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let hash = "ab".repeat(32);
    assert_eq!(hash.len(), 64);
    let rel = format!("cas/ab/ab/{hash}");
    let value = format!("1\nu\t{hash}\t{rel}\n");
    arch.conn
        .execute(
            "INSERT INTO settings(key, value) VALUES ('cas_pending_files', ?1)",
            [&value],
        )
        .unwrap();
    let parent = root.join("cas").join("ab").join("ab");
    std::fs::create_dir_all(&parent).unwrap();
    let path = parent.join(&hash);
    std::fs::write(&path, b"still-there").unwrap();
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "fixture planted a cas_blobs row");
    let root = arch.root.clone();
    drop(arch);
    let _mode = ModeGuard { path: &parent };
    let mut perms = std::fs::metadata(&parent).unwrap().permissions();
    perms.set_mode(0o000);
    std::fs::set_permissions(&parent, perms).unwrap();
    let opened_ok = open_archive(&root, LockMode::Exclusive).is_ok();
    let conn = rusqlite::Connection::open(root.join("archive.sqlite"))
        .expect("RECLAIM-STAT-RETRY direct sqlite");
    let pending: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM settings WHERE key = 'cas_pending_files'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    drop(conn);
    assert!(
        !opened_ok,
        "RECLAIM-STAT-RETRY open succeeded while cas/ab/ab was mode 0o000; pending rows={pending}"
    );
    assert_eq!(pending, 1, "RECLAIM-STAT-RETRY pending row was dropped");
    restore_mode_755(&parent);
    assert_eq!(
        std::fs::read(&path).unwrap(),
        b"still-there",
        "RECLAIM-STAT-RETRY file bytes changed"
    );
    let arch = open_archive(&root, LockMode::Exclusive).expect("RECLAIM-STAT-RETRY retry");
    let settings: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM settings WHERE key = 'cas_pending_files'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(settings, 0, "RECLAIM-STAT-RETRY settings row remained");
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "RECLAIM-STAT-RETRY cas_blobs row was put back");
    assert!(!path.exists(), "RECLAIM-STAT-RETRY file remained");
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn reclaim_notdir_retry() {
    let _guard = crash_kill::one_test_at_a_time();
    let root = tmp_root();
    let arch = init_archive(&root).unwrap();
    let hash = "ab".repeat(32);
    assert_eq!(hash.len(), 64);
    let rel = format!("cas/ab/ab/{hash}");
    let value = format!("1\nu\t{hash}\t{rel}\n");
    arch.conn
        .execute(
            "INSERT INTO settings(key, value) VALUES ('cas_pending_files', ?1)",
            [&value],
        )
        .unwrap();
    let cas_ab = root.join("cas").join("ab");
    std::fs::write(&cas_ab, b"not-a-dir").unwrap();
    let blobs: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(blobs, 0, "fixture planted a cas_blobs row");
    let root = arch.root.clone();
    drop(arch);
    let opened_ok = open_archive(&root, LockMode::Exclusive).is_ok();
    let conn = rusqlite::Connection::open(root.join("archive.sqlite"))
        .expect("RECLAIM-NOTDIR-RETRY direct sqlite");
    let pending: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM settings WHERE key = 'cas_pending_files'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    let blobs: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
            [&hash],
            |row| row.get(0),
        )
        .unwrap();
    drop(conn);
    assert!(
        !opened_ok,
        "RECLAIM-NOTDIR-RETRY open succeeded while cas/ab is a file; pending rows={pending}"
    );
    assert_eq!(pending, 1, "RECLAIM-NOTDIR-RETRY pending row was dropped");
    assert_eq!(
        std::fs::read(&cas_ab).unwrap(),
        b"not-a-dir",
        "RECLAIM-NOTDIR-RETRY cas/ab bytes changed"
    );
    assert_eq!(blobs, 0, "RECLAIM-NOTDIR-RETRY cas_blobs row was put back");
    let _ = std::fs::remove_dir_all(&root);
}

fn restore_mode_755(path: &Path) {
    let mut perms = std::fs::metadata(path)
        .expect("RECLAIM-STAT-RETRY mode metadata")
        .permissions();
    perms.set_mode(0o755);
    std::fs::set_permissions(path, perms).expect("RECLAIM-STAT-RETRY mode restore");
}

struct ModeGuard<'a> {
    path: &'a Path,
}

impl Drop for ModeGuard<'_> {
    fn drop(&mut self) {
        if std::fs::metadata(self.path).is_ok() {
            restore_mode_755(self.path);
        }
    }
}
