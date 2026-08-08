//! Owner init + last-archive-path pointer (UI1 / CLI share).

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

static ENV: Mutex<()> = Mutex::new(());

use interlace_core::session::{init_owner_archive, read_last_path, validate_phone_region};
use interlace_core::{open_archive, LockMode};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-sess-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

#[test]
fn phone_region_required_shape() {
    assert!(validate_phone_region("tr").unwrap() == "TR");
    assert!(validate_phone_region("USA").is_err());
    assert!(validate_phone_region("").is_err());
}

#[test]
fn init_owner_writes_pointer_and_status_fields() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    let arch_path = root.join("Interlace");
    let arch = init_owner_archive(
        &arch_path,
        "TR",
        Some("Mustafa".into()),
        vec!["me@example.com".into()],
        vec![],
    )
    .unwrap();
    drop(arch);
    let remembered = read_last_path().expect("pointer");
    assert!(remembered.ends_with("Interlace"));
    let opened = open_archive(&arch_path, LockMode::Shared).unwrap();
    let st = opened.status().unwrap();
    assert_eq!(st["owner_display_name"], "Mustafa");
    assert_eq!(st["default_phone_region"], "TR");
    assert_eq!(st["persons_live"], 1);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn init_owner_rejects_existing_archive() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    let arch_path = root.join("a");
    init_owner_archive(&arch_path, "US", None, vec![], vec![]).unwrap();
    match init_owner_archive(&arch_path, "US", None, vec![], vec![]) {
        Err(e) => assert!(e.to_string().contains("already an archive")),
        Ok(_) => panic!("expected already-an-archive"),
    }
    let _ = std::fs::remove_dir_all(&root);
}
