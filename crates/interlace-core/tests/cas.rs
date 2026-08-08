//! CAS1–CAS3 must-pass matrix.
//!
//! Matrix IDs (gate grep): CAS1 CAS2 CAS3

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::cas::validate_zip_entry_name;
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
