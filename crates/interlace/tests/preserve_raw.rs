//! #79 CLI: `--preserve-raw` on `import gmail` and `import takeout`.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//! Help + default-off + on-path. Isolated from `tests/cli.rs`.
//! Placeholders only (`Ada`). No export-mbox claim.

use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::{open_archive, LockMode};
use interlace_fixtures::{write_takeout_tree, TakeoutGenConfig};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-cli-pr-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_interlace"))
}

fn repo_root() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
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
            "Ada",
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

fn write_ada_mbox(path: &std::path::Path) {
    std::fs::write(
        path,
        "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: friend@example.com
Subject: hello
Message-ID: <ada-cli-preserve-raw@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

hello from Ada
",
    )
    .unwrap();
}

fn looks_like_size_warning(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    let sizeish = l.contains("size")
        || l.contains("disk")
        || l.contains("gigabyte")
        || l.contains("gb")
        || l.contains("storage")
        || l.contains("large");
    let encrypt = l.contains("encrypt") || l.contains("sqlcipher");
    sizeish && !encrypt
}

fn claims_export_mbox(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    l.contains("export mbox") || l.contains("export-mbox")
}

fn looks_like_oq5_dump(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    (l.contains("delet") && (l.contains("takeout") || l.contains("rfc822") || l.contains("dump")))
        || l.contains("bit-perfect")
        || l.contains("bit perfect")
}

fn help_text(args: &[&str]) -> String {
    let out = bin().args(args).output().unwrap();
    assert!(
        out.status.success(),
        "help must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let mut s = String::from_utf8_lossy(&out.stdout).into_owned();
    s.push_str(&String::from_utf8_lossy(&out.stderr));
    s
}

fn assert_preserve_raw_help(s: &str, cmd: &str) {
    assert!(
        s.contains("--preserve-raw"),
        "{cmd} --help must list --preserve-raw (missing flag is fail-today); help={s}"
    );
    let lower = s.to_ascii_lowercase();
    assert!(
        !lower.contains("default: true") && !lower.contains("default on"),
        "{cmd} help must not describe the flag as default-on; help={s}"
    );
    assert!(
        looks_like_size_warning(s),
        "{cmd} help must include a size warning; help={s}"
    );
    assert!(
        !claims_export_mbox(s),
        "{cmd} help must not claim export mbox exists; help={s}"
    );
}

fn raw_hashes(arch: &std::path::Path) -> Vec<Option<String>> {
    let db = rusqlite::Connection::open(arch.join("archive.sqlite")).unwrap();
    let mut stmt = db
        .prepare("SELECT raw_cas_hash FROM messages")
        .unwrap_or_else(|e| {
            panic!("messages.raw_cas_hash missing (fail-today): {e}");
        });
    stmt.query_map([], |r| r.get::<_, Option<String>>(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn schema_epoch(arch: &std::path::Path) -> i64 {
    let db = rusqlite::Connection::open(arch.join("archive.sqlite")).unwrap();
    db.query_row("SELECT schema_epoch FROM archive_meta", [], |r| r.get(0))
        .unwrap()
}

fn has_raw_column(arch: &std::path::Path) -> bool {
    let db = rusqlite::Connection::open(arch.join("archive.sqlite")).unwrap();
    let n: i64 = db
        .query_row(
            "SELECT COUNT(*) FROM pragma_table_info('messages') WHERE name = 'raw_cas_hash'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    n > 0
}

#[test]
fn import_gmail_help_lists_preserve_raw() {
    let s = help_text(&["import", "gmail", "--help"]);
    assert_preserve_raw_help(&s, "import gmail");
}

#[test]
fn import_takeout_help_lists_preserve_raw() {
    let s = help_text(&["import", "takeout", "--help"]);
    assert_preserve_raw_help(&s, "import takeout");
}

#[test]
fn preserve_raw_docs_and_changelog() {
    let root = repo_root();
    let docs = std::fs::read_to_string(root.join("docs/user/import-takeout.md")).unwrap();
    let log = std::fs::read_to_string(root.join("CHANGELOG.md")).unwrap();
    assert!(
        docs.contains("--preserve-raw"),
        "docs/user/import-takeout.md must document --preserve-raw"
    );
    assert!(
        !docs.contains("Not in Phase 1"),
        "must drop “Not in Phase 1” for the shipped flag"
    );
    assert!(
        !docs.contains("When it lands (Phase 2)"),
        "must not say the flag has not landed"
    );
    assert!(
        !docs.contains("arrives in Phase 2"),
        "must not say --preserve-raw arrives in Phase 2"
    );
    assert!(
        !docs.contains("`--preserve-raw` is **Phase 2"),
        "must not say Phase 2 not shipped"
    );
    let lower = docs.to_ascii_lowercase();
    assert!(
        lower.contains("default") && lower.contains("off"),
        "docs must say default off"
    );
    assert!(
        looks_like_size_warning(&docs),
        "docs must include a size warning"
    );
    assert!(
        !claims_export_mbox(&docs),
        "docs must not claim export mbox / #73"
    );
    assert!(
        log.contains("--preserve-raw"),
        "CHANGELOG must mention --preserve-raw"
    );
}

#[test]
fn preserve_raw_0002_not_0001_epoch_stays_1() {
    let (dir, arch, _cfg) = init_arch();
    assert_eq!(schema_epoch(&arch), 1, "schema_epoch stays 1");
    assert!(
        has_raw_column(&arch),
        "init/migrate must apply 0002 ADD COLUMN messages.raw_cas_hash"
    );
    let shipped =
        std::fs::read_to_string(repo_root().join("crates/interlace-core/migrations/0001_init.sql"))
            .unwrap();
    assert!(
        !shipped.contains("raw_cas_hash"),
        "do not edit shipped 0001; add 0002"
    );
    let mig = repo_root().join("crates/interlace-core/migrations");
    let has_0002 = std::fs::read_dir(&mig)
        .unwrap()
        .any(|e| e.unwrap().file_name().to_string_lossy().starts_with("0002"));
    assert!(has_0002, "migrations/ must contain 0002_*.sql");
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn import_gmail_default_off_stores_no_raw() {
    let (dir, arch, cfg) = init_arch();
    let mbox = dir.join("ada.mbox");
    write_ada_mbox(&mbox);
    let out = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "import",
            "gmail",
            mbox.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "import gmail without --preserve-raw must succeed; stdout={} stderr={}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        has_raw_column(&arch),
        "messages.raw_cas_hash missing (fail-today)"
    );
    let hashes = raw_hashes(&arch);
    assert_eq!(hashes.len(), 1);
    assert!(
        hashes.iter().all(|h| h.is_none()),
        "omitting --preserve-raw must leave raw_cas_hash NULL; got {hashes:?}"
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn import_takeout_default_off_keeps_oq5() {
    let (dir, arch, cfg) = init_arch();
    let tree = write_takeout_tree(
        &dir.join("to"),
        &TakeoutGenConfig {
            n_mail: 1,
            n_contacts: 0,
            seed: 17,
        },
    );
    let out = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "import",
            "takeout",
            tree.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "import takeout without --preserve-raw must succeed; stdout={} stderr={}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let combined = format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        looks_like_oq5_dump(&combined) || combined.contains("warnings="),
        "off-path Takeout must keep OQ5 dump-deletion warning; out={combined}"
    );
    assert!(
        !combined.contains("arrives in Phase 2"),
        "OQ5 must not still say the flag arrives in Phase 2; out={combined}"
    );
    if has_raw_column(&arch) {
        assert!(
            raw_hashes(&arch).iter().all(|h| h.is_none()),
            "default-off takeout must not set raw_cas_hash"
        );
    }
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn import_gmail_preserve_raw_on_stores_and_warns() {
    let (dir, arch, cfg) = init_arch();
    let mbox = dir.join("ada.mbox");
    write_ada_mbox(&mbox);
    let out = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "import",
            "gmail",
            mbox.to_str().unwrap(),
            "--preserve-raw",
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "import gmail --preserve-raw must succeed (unknown flag is fail-today); stdout={} stderr={}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let combined = format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        looks_like_size_warning(&combined),
        "flag on must print a size warning; out={combined}"
    );
    assert!(
        !claims_export_mbox(&combined),
        "must not claim export mbox; out={combined}"
    );
    assert!(
        !combined.to_ascii_lowercase().contains("encrypt"),
        "must not say encrypted; out={combined}"
    );
    let hashes = raw_hashes(&arch);
    let hash = hashes
        .iter()
        .find_map(|h| h.as_ref())
        .expect("flagged gmail import must set raw_cas_hash");
    let opened = open_archive(&arch, LockMode::Shared).unwrap();
    let raw = opened.cas_get(hash).expect("raw blob must be in CAS");
    let text = String::from_utf8_lossy(&raw);
    assert!(text.contains("From: Ada <ada@example.com>"));
    assert!(text.contains("hello from Ada"));
    assert!(!text.starts_with("From ada@example.com"));
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn import_takeout_preserve_raw_on_stores_and_warns() {
    let (dir, arch, cfg) = init_arch();
    let tree = write_takeout_tree(
        &dir.join("to"),
        &TakeoutGenConfig {
            n_mail: 1,
            n_contacts: 0,
            seed: 19,
        },
    );
    let out = bin()
        .env("INTERLACE_CONFIG_DIR", &cfg)
        .args([
            "--path",
            arch.to_str().unwrap(),
            "import",
            "takeout",
            tree.to_str().unwrap(),
            "--preserve-raw",
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "import takeout --preserve-raw must succeed (unknown flag is fail-today); stdout={} stderr={}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let combined = format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        looks_like_size_warning(&combined),
        "flag on must print a size warning; out={combined}"
    );
    assert!(
        !claims_export_mbox(&combined),
        "must not claim export mbox; out={combined}"
    );
    let hashes = raw_hashes(&arch);
    assert!(
        hashes.iter().any(|h| h.is_some()),
        "flagged takeout must set raw_cas_hash; got {hashes:?}"
    );
    let hash = hashes.iter().find_map(|h| h.as_ref()).unwrap();
    let opened = open_archive(&arch, LockMode::Shared).unwrap();
    assert!(!opened.cas_get(hash).unwrap().is_empty());
    let _ = std::fs::remove_dir_all(&dir);
}
