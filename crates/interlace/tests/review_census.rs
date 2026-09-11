//! #342 CLI: `interlace [--path DIR] [--json] review census`.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//! Unknown subcommand is fail-today. Integer JSON only; Shared lock.

use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::{open_archive, LockMode};

static SEQ: AtomicU64 = AtomicU64::new(0);

const CENSUS_KEYS: &[&str] = &[
    "identities",
    "persons_live",
    "review_open",
    "name_only_wa_exact_fold_contacts",
    "name_only_wa_no_phone_email",
    "name_score_pairs_under_040",
    "name_score_best_under_040",
    "exact_fold_clusters_rejected",
    "exact_fold_clusters_never_enqueued",
];

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-cli-rc-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_interlace"))
}

fn init_arch() -> (std::path::PathBuf, std::path::PathBuf, std::path::PathBuf) {
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
            "Owner",
        ])
        .output()
        .unwrap();
    assert!(
        init.status.success(),
        "init stderr={}",
        String::from_utf8_lossy(&init.stderr)
    );
    (dir, arch, cfg)
}

fn json_int(v: &serde_json::Value, key: &str) -> i64 {
    if let Some(n) = v.get(key).and_then(|x| x.as_i64()) {
        return n;
    }
    if let Some(obj) = v.as_object() {
        for child in obj.values() {
            if child.is_object() {
                if let Some(n) = child.get(key).and_then(|x| x.as_i64()) {
                    return n;
                }
            }
        }
    }
    panic!("census JSON missing integer key {key}: {v}");
}

fn walk_integers_only(node: &serde_json::Value) {
    match node {
        serde_json::Value::Object(map) => {
            for child in map.values() {
                walk_integers_only(child);
            }
        }
        serde_json::Value::Array(arr) => {
            for child in arr {
                walk_integers_only(child);
            }
        }
        serde_json::Value::Number(n) => {
            assert!(
                n.is_i64() || n.as_u64().is_some(),
                "census values must be integers: {n}"
            );
        }
        serde_json::Value::Null => {}
        other => panic!("census JSON must be integers only, got {other}"),
    }
}

#[test]
fn review_census_json_prints_integer_keys() {
    let (dir, arch, cfg) = init_arch();
    let db = rusqlite::Connection::open(arch.join("archive.sqlite")).unwrap();
    db.execute(
        "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
        [],
    )
    .unwrap();
    db.execute(
        "INSERT INTO persons(display_name, is_self) VALUES ('Cemre Yıldız', 0)",
        [],
    )
    .unwrap();
    drop(db);

    let out = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "--json",
            "review",
            "census",
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "review census --json must succeed (unknown subcommand is fail-today); stdout={} stderr={}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    let v: serde_json::Value = serde_json::from_str(stdout.trim()).unwrap_or_else(|e| {
        panic!("census stdout must be integer JSON: {e}; stdout={stdout}");
    });
    for key in CENSUS_KEYS {
        let _ = json_int(&v, key);
    }
    walk_integers_only(&v);
    assert!(
        !stdout.contains("Ada"),
        "census stdout must not contain planted Ada: {stdout}"
    );
    assert!(
        !stdout.contains("Cemre"),
        "census stdout must not contain planted Cemre Yıldız: {stdout}"
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn review_census_shared_ok_exclusive_blocks() {
    let (dir, arch, cfg) = init_arch();

    let shared = open_archive(&arch, LockMode::Shared).expect("shared holder");
    let with_shared = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "--json",
            "review",
            "census",
        ])
        .output()
        .unwrap();
    assert!(
        with_shared.status.success(),
        "census must open Shared (two Shared ok); stdout={} stderr={}",
        String::from_utf8_lossy(&with_shared.stdout),
        String::from_utf8_lossy(&with_shared.stderr)
    );
    drop(shared);

    let exclusive = open_archive(&arch, LockMode::Exclusive).expect("exclusive holder");
    let with_ex = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "--json",
            "review",
            "census",
        ])
        .output()
        .unwrap();
    assert_eq!(
        with_ex.status.code(),
        Some(1),
        "Exclusive holder must yield CoreError::Lock / exit 1; stdout={} stderr={}",
        String::from_utf8_lossy(&with_ex.stdout),
        String::from_utf8_lossy(&with_ex.stderr)
    );
    let err = String::from_utf8_lossy(&with_ex.stderr);
    assert!(
        err.contains("archive in use") || err.contains("lock"),
        "stderr must be the existing lock error, not rm INTERLACE.lock; stderr={err}"
    );
    drop(exclusive);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn review_census_not_on_status() {
    let (dir, arch, cfg) = init_arch();
    let st = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args(["--path", arch.to_str().unwrap(), "--json", "status"])
        .output()
        .unwrap();
    assert!(st.status.success());
    let js = String::from_utf8_lossy(&st.stdout);
    assert!(js.contains("persons_live"));
    for key in [
        "name_only_wa_exact_fold_contacts",
        "name_only_wa_no_phone_email",
        "name_score_pairs_under_040",
        "name_score_best_under_040",
        "exact_fold_clusters_rejected",
        "exact_fold_clusters_never_enqueued",
    ] {
        assert!(
            !js.contains(key),
            "status --json must not grow census key {key}: {js}"
        );
    }
    let _ = std::fs::remove_dir_all(&dir);
}
