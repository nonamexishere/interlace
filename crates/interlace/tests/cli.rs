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
fn version_flag_prints_semver() {
    for flag in ["--version", "-V"] {
        let out = bin().arg(flag).output().unwrap();
        assert!(out.status.success(), "{flag} {:?}", out);
        let s = String::from_utf8_lossy(&out.stdout);
        assert!(s.contains(env!("CARGO_PKG_VERSION")), "{flag} stdout={s}");
        assert!(s.to_lowercase().contains("interlace"), "{flag} stdout={s}");
    }
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

#[test]
fn doctor_exit_3_on_stale_heartbeat() {
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
        ])
        .output()
        .unwrap();
    assert!(init.status.success());

    let db = rusqlite::Connection::open(arch.join("archive.sqlite")).unwrap();
    db.execute(
        "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
        [],
    )
    .unwrap();
    db.execute(
        "INSERT INTO import_runs(source_id, status, heartbeat_at)
         VALUES (1, 'running', '2000-01-01T00:00:00.000Z')",
        [],
    )
    .unwrap();
    drop(db);

    let doc = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args(["doctor", "--integrity", "--path", arch.to_str().unwrap()])
        .output()
        .unwrap();
    assert_eq!(
        doc.status.code(),
        Some(3),
        "stderr={}",
        String::from_utf8_lossy(&doc.stderr)
    );
    assert!(String::from_utf8_lossy(&doc.stderr).contains("heartbeat"));
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn import_whatsapp_zip_is_not_treated_as_archive() {
    use interlace_fixtures::{write_whatsapp_zip, WaGenConfig};
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
        ])
        .output()
        .unwrap();
    assert!(init.status.success());

    let zip = write_whatsapp_zip(
        &dir.join("zips"),
        &WaGenConfig {
            locale: "en-US",
            ios: true,
            with_media: false,
            n_messages: 20,
            n_participants: 2,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.0,
            system_every: None,
            seed: 1,
        },
    );
    let imp = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "import",
            "whatsapp",
            zip.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        imp.status.success(),
        "stdout={} stderr={}",
        String::from_utf8_lossy(&imp.stdout),
        String::from_utf8_lossy(&imp.stderr)
    );
    assert!(
        String::from_utf8_lossy(&imp.stdout).contains("inserted="),
        "stdout={}",
        String::from_utf8_lossy(&imp.stdout)
    );
    let _ = std::fs::remove_dir_all(&dir);
}
