//! CLI smoke: --help, required --phone-region, init/status/doctor/search.

use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-cli-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_interlace"))
}

#[test]
fn help_exits_zero_and_lists_catalog() {
    let out = bin().arg("--help").output().unwrap();
    assert!(out.status.success(), "{:?}", out);
    let s = String::from_utf8_lossy(&out.stdout);
    for w in [
        "init", "open", "status", "import", "search", "person", "review", "doctor", "log",
    ] {
        assert!(s.contains(w), "help missing {w}: {s}");
    }
}

#[test]
fn init_requires_phone_region() {
    let dir = tmp();
    let out = bin()
        .args(["init", "--path", dir.join("a").to_str().unwrap()])
        .output()
        .unwrap();
    assert!(!out.status.success());
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn init_status_search_doctor_roundtrip() {
    let dir = tmp();
    let arch = dir.join("arch");
    let cfg = dir.join("cfg");
    std::fs::create_dir_all(&cfg).unwrap();
    let init = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "init",
            "--path",
            arch.to_str().unwrap(),
            "--phone-region",
            "TR",
            "--name",
            "Mustafa",
            "--email",
            "me@example.com",
        ])
        .output()
        .unwrap();
    assert!(
        init.status.success(),
        "init stderr={}",
        String::from_utf8_lossy(&init.stderr)
    );
    let stdout = String::from_utf8_lossy(&init.stdout);
    assert!(stdout.contains("created archive"));
    assert!(stdout.contains("self person id="));

    let st = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args(["status", "--json", "--path", arch.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(st.status.success());
    let js = String::from_utf8_lossy(&st.stdout);
    assert!(js.contains("persons_live"));

    let doc = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args(["doctor", "--integrity", "--path", arch.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(
        doc.status.success(),
        "doctor: {}",
        String::from_utf8_lossy(&doc.stderr)
    );

    let se = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "search",
            "hello",
            "--json",
            "--path",
            arch.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(se.status.success());
    assert!(String::from_utf8_lossy(&se.stdout).trim().starts_with('['));

    let twin = Command::new(env!("CARGO_BIN_EXE_interlace").replace("interlace", "interlace-cli"));
    // twin path may not exist from this package; skip if missing
    let _ = twin;

    let _ = std::fs::remove_dir_all(&dir);
}
