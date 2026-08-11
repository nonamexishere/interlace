//! Owner init + last-archive-path pointer (UI1 / CLI share).
//! Bookmark blob + sandbox-denied copy (#109 / #137).

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

static ENV: Mutex<()> = Mutex::new(());

use interlace_core::session::{
    cloud_warning, init_owner_archive, read_last_bookmark, read_last_path,
    sandbox_denied_message, validate_phone_region, write_last_bookmark, write_last_path,
};
use interlace_core::{open_archive, LockMode};

/// Exact #137 copy. Unicode ellipsis (U+2026), not three dots.
const SANDBOX_DENIED_COPY: &str =
    "macOS blocked that folder. Use Open existing… once so Interlace can remember it.";

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

#[test]
fn cloud_warning_flags_icloud_dropbox_google_not_local() {
    use std::path::Path;
    assert!(cloud_warning(Path::new(
        "/Users/x/Library/Mobile Documents/com~apple~CloudDocs/Interlace"
    ))
    .is_some());
    assert!(cloud_warning(Path::new("/Users/x/iCloud Drive/Interlace")).is_some());
    assert!(cloud_warning(Path::new("/Users/x/Dropbox/Interlace")).is_some());
    assert!(cloud_warning(Path::new("/Users/x/Google Drive/Interlace")).is_some());
    assert!(cloud_warning(Path::new("/Users/x/Interlace")).is_none());
    assert!(cloud_warning(Path::new("/Volumes/Time Machine/Interlace")).is_none());
}

#[test]
fn status_warnings_include_cloud_path() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    let arch_path = root.join("Dropbox").join("Interlace");
    let arch = init_owner_archive(&arch_path, "TR", None, vec![], vec![]).unwrap();
    let st = arch.status().unwrap();
    let warnings = st["warnings"].as_array().expect("warnings array");
    assert!(
        warnings
            .iter()
            .any(|w| w.as_str().unwrap_or("").contains("iCloud/Dropbox")),
        "status.warnings must surface cloud_warning: {warnings:?}"
    );
    drop(arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn sandbox_denied_message_permission_denied_is_exact_copy() {
    let denied = std::io::Error::new(
        std::io::ErrorKind::PermissionDenied,
        "operation not permitted",
    );
    assert_eq!(sandbox_denied_message(&denied), Some(SANDBOX_DENIED_COPY));

    #[cfg(unix)]
    {
        // EPERM is os error 1 on macOS / Unix.
        let eperm = std::io::Error::from_raw_os_error(1);
        assert_eq!(eperm.kind(), std::io::ErrorKind::PermissionDenied);
        assert_eq!(sandbox_denied_message(&eperm), Some(SANDBOX_DENIED_COPY));
    }
}

#[test]
fn sandbox_denied_message_other_errors_are_not_that_sentence() {
    let kinds = [
        std::io::ErrorKind::NotFound,
        std::io::ErrorKind::AlreadyExists,
        std::io::ErrorKind::InvalidInput,
        std::io::ErrorKind::UnexpectedEof,
        std::io::ErrorKind::BrokenPipe,
        std::io::ErrorKind::Other,
    ];
    for kind in kinds {
        let err = std::io::Error::new(kind, "placeholder Ada path");
        let got = sandbox_denied_message(&err);
        assert_ne!(
            got,
            Some(SANDBOX_DENIED_COPY),
            "non-EPERM {kind:?} must not become the sandbox sentence: {got:?}"
        );
        assert_eq!(
            got, None,
            "non-EPERM {kind:?} must not map to sandbox_denied_message"
        );
    }
}

#[test]
fn read_last_bookmark_missing_file_is_none() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    assert_eq!(read_last_bookmark(), None);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn last_bookmark_round_trips_opaque_bytes() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    // Opaque blob: not UTF-8, not a URL, not TOML.
    let blob: &[u8] = b"\x00book\xff\xfe\x01mark";
    write_last_bookmark(blob).unwrap();
    assert_eq!(read_last_bookmark().as_deref(), Some(blob));
    assert_eq!(read_last_path(), None);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn last_bookmark_empty_or_invalid_is_still_some() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    write_last_bookmark(&[]).unwrap();
    assert_eq!(read_last_bookmark(), Some(Vec::new()));
    // Stale / unparseable bytes are still Some — Tauri decides staleness.
    let junk = b"not-a-bookmark";
    write_last_bookmark(junk).unwrap();
    assert_eq!(read_last_bookmark().as_deref(), Some(&junk[..]));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn write_last_bookmark_does_not_break_config_toml_last_archive_path() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    let arch_dir = root.join("AdaArchive");
    std::fs::create_dir_all(&arch_dir).unwrap();
    write_last_path(&arch_dir).unwrap();
    let pointer = read_last_path().expect("path pointer");
    write_last_bookmark(b"\x00\x01opaque").unwrap();
    assert_eq!(read_last_path().as_ref(), Some(&pointer));
    let toml = std::fs::read_to_string(cfg.join("config.toml")).expect("config.toml");
    assert!(
        toml.contains("last_archive_path"),
        "config.toml must keep last_archive_path after bookmark write: {toml}"
    );
    assert_eq!(read_last_bookmark(), Some(b"\x00\x01opaque".to_vec()));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn cli_init_writes_path_pointer_never_bookmark() {
    let _g = ENV.lock().unwrap();
    let root = tmp();
    let cfg = root.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    std::env::set_var("INTERLACE_CONFIG_DIR", &cfg);
    let arch_path = root.join("Interlace");
    let arch = init_owner_archive(&arch_path, "TR", Some("Ada".into()), vec![], vec![]).unwrap();
    drop(arch);
    let remembered = read_last_path().expect("pointer");
    assert!(remembered.ends_with("Interlace"));
    assert_eq!(
        read_last_bookmark(),
        None,
        "CLI-only init writes last_archive_path, never a bookmark"
    );
    let _ = std::fs::remove_dir_all(&root);
}
