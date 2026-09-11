//! #79 --preserve-raw: opt-in CAS of unescaped rfc822.
//!
//! Matrix IDs (gate grep):
//!
//! Not a Phase 1 must-ID. Do not add to test_plan.json.
//! Isolated from `tests/gmail.rs` so a missing `ImportOpts.preserve_raw` /
//! `messages.raw_cas_hash` cannot break M1–M3.
//!
//! Confirmed mix: flag on `import gmail` and `import takeout`, default off;
//! `cas_put` unescaped rfc822; `messages.raw_cas_hash` via 0002; schema_epoch
//! stays 1; GC/doctor treat the hash as referenced; size warning when on;
//! OQ5 when off; duplicate persist does not backfill. Placeholders only (`Ada`).

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{ImportOpts, SourceKind};
use interlace_fixtures::{write_takeout_tree, TakeoutGenConfig};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-pr-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn has_column(arch: &interlace_core::db::Archive, table: &str, col: &str) -> bool {
    let sql = format!("SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name = ?1");
    let n: i64 = arch.conn.query_row(&sql, [col], |r| r.get(0)).unwrap();
    n > 0
}

fn schema_epoch(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row("SELECT schema_epoch FROM archive_meta", [], |r| r.get(0))
        .unwrap()
}

fn warning_blob(arch: &interlace_core::db::Archive) -> String {
    let mut stmt = arch
        .conn
        .prepare("SELECT kind, detail FROM import_warnings")
        .unwrap();
    let rows = stmt
        .query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))
        .unwrap();
    let mut out = String::new();
    for row in rows {
        let (kind, detail) = row.unwrap();
        out.push_str(&kind);
        out.push(' ');
        out.push_str(&detail);
        out.push('\n');
    }
    out
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

fn looks_like_oq5_dump(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    (l.contains("delet") && (l.contains("takeout") || l.contains("rfc822") || l.contains("dump")))
        || l.contains("bit-perfect")
        || l.contains("bit perfect")
}

fn claims_export_mbox(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    l.contains("export mbox") || l.contains("export-mbox")
}

fn opts_preserve_raw(on: bool) -> ImportOpts {
    ImportOpts {
        preserve_raw: on,
        ..ImportOpts::default()
    }
}

/// Tiny Ada mbox. No `>From`, so unescaped rfc822 is the bytes after `From_`.
fn write_ada_mbox(path: &std::path::Path) {
    std::fs::write(
        path,
        "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: friend@example.com
Subject: hello
Message-ID: <ada-preserve-raw@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

hello from Ada
",
    )
    .unwrap();
}

fn write_ada_mbox_quoted_from(path: &std::path::Path) {
    std::fs::write(
        path,
        "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: friend@example.com
Subject: quoted
Message-ID: <ada-from@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

hello from Ada
>From someone quoted
",
    )
    .unwrap();
}

fn write_ada_mbox_no_id(path: &std::path::Path) {
    std::fs::write(
        path,
        "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: friend@example.com
Subject: no-id
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

hello from Ada
",
    )
    .unwrap();
}

fn plant_mail_skeleton(arch: &interlace_core::db::Archive) {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (1, 'done')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id) VALUES ('gmail', 'email_thread', 'g1')",
            [],
        )
        .unwrap();
}

fn insert_message_with_raw(arch: &interlace_core::db::Archive, key: &str, raw_hash: Option<&str>) {
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sent_at, sent_at_precision,
                kind, body_text, idempotency_key, raw_cas_hash
             ) VALUES (1, 1, 1, '2024-01-01T00:00:00Z', 'second', 'email', 'x', ?1, ?2)",
            rusqlite::params![key, raw_hash],
        )
        .unwrap();
}

#[test]
fn preserve_raw_opts_default_is_off() {
    assert!(
        !ImportOpts::default().preserve_raw,
        "ImportOpts::default().preserve_raw must be false"
    );
    assert!(
        !opts_preserve_raw(false).preserve_raw,
        "explicit off must stay off"
    );
    assert!(opts_preserve_raw(true).preserve_raw);
}

#[test]
fn preserve_raw_column_via_0002_epoch_stays_1() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    assert_eq!(
        schema_epoch(&arch),
        1,
        "schema_epoch stays 1 (#75 is not this ticket)"
    );
    assert!(
        has_column(&arch, "messages", "raw_cas_hash"),
        "0002 must ADD messages.raw_cas_hash"
    );
    let notnull: i64 = arch
        .conn
        .query_row(
            "SELECT \"notnull\" FROM pragma_table_info('messages') WHERE name = 'raw_cas_hash'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        notnull, 0,
        "raw_cas_hash is nullable (default-off / expand-only)"
    );
    let v2: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 2 OR name LIKE '0002%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(v2 >= 1, "0002_* migration must be applied; got none");

    let shipped = include_str!("../migrations/0001_init.sql");
    assert!(
        !shipped.contains("raw_cas_hash"),
        "do not edit shipped 0001; add 0002"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_default_off_stores_no_raw() {
    let root = tmp_root();
    let mbox = root.join("ada.mbox");
    write_ada_mbox(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats.inserted_messages, 1);
    assert!(
        has_column(&arch, "messages", "raw_cas_hash"),
        "messages.raw_cas_hash missing (fail-today)"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE raw_cas_hash IS NOT NULL"
        ),
        0,
        "default-off must not set raw_cas_hash"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM cas_blobs"),
        count(
            &arch,
            "SELECT COUNT(*) FROM attachments WHERE cas_hash IS NOT NULL"
        ),
        "default-off must not cas_put rfc822"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_on_gmail_cases_unescaped_rfc822() {
    let root = tmp_root();
    let mbox = root.join("ada.mbox");
    write_ada_mbox(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    assert_eq!(stats.inserted_messages, 1);
    let hash: String = arch
        .conn
        .query_row(
            "SELECT raw_cas_hash FROM messages WHERE subject = 'hello'",
            [],
            |r| r.get(0),
        )
        .expect("raw_cas_hash must be set when preserve_raw is on");
    assert_eq!(hash.len(), 64, "raw_cas_hash is a 64-hex blake3");
    let raw = arch
        .cas_get(&hash)
        .expect("cas_get of raw_cas_hash must succeed");
    let text = String::from_utf8_lossy(&raw);
    assert!(
        text.contains("From: Ada <ada@example.com>"),
        "stored bytes are rfc822, got {text:?}"
    );
    assert!(
        text.contains("hello from Ada"),
        "stored rfc822 missing body: {text:?}"
    );
    assert!(
        !text.starts_with("From ada@example.com"),
        "must not store the mbox From_ envelope: {text:?}"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM attachments"),
        0,
        "raw is messages.raw_cas_hash, not a fake attachment row"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_stores_unescaped_mboxrd_from() {
    let root = tmp_root();
    let mbox = root.join("quoted.mbox");
    write_ada_mbox_quoted_from(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    let hash: String = arch
        .conn
        .query_row("SELECT raw_cas_hash FROM messages", [], |r| r.get(0))
        .unwrap();
    let stored = arch.cas_get(&hash).unwrap();
    let text = String::from_utf8_lossy(&stored);
    assert!(
        text.contains("From someone quoted"),
        "cas_put must be unescaped rfc822: {text:?}"
    );
    assert!(
        !text.contains(">From someone quoted"),
        "must not store mboxrd-escaped >From: {text:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_same_bytes_as_gmail_hash() {
    let root = tmp_root();
    let mbox = root.join("noid.mbox");
    write_ada_mbox_no_id(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    let (key, hash): (String, String) = arch
        .conn
        .query_row(
            "SELECT idempotency_key, raw_cas_hash FROM messages",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert!(
        key.starts_with("gmail-hash:"),
        "expected gmail-hash: key, got {key}"
    );
    let hashed = key.strip_prefix("gmail-hash:").unwrap();
    assert_eq!(
        hashed, hash,
        "raw_cas_hash must be the same unescaped rfc822 bytes persist already hashes"
    );
    let _ = arch.cas_get(&hash).unwrap();
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_on_takeout_sets_column() {
    let root = tmp_root();
    let tree = write_takeout_tree(
        &root.join("to"),
        &TakeoutGenConfig {
            n_mail: 1,
            n_contacts: 0,
            seed: 11,
        },
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::TakeoutDir, &tree, &opts_preserve_raw(true))
        .unwrap();
    assert!(stats.inserted_messages >= 1, "takeout mail");
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE raw_cas_hash IS NULL"
        ),
        0,
        "flagged takeout must set raw_cas_hash on inserted mail"
    );
    let hash: String = arch
        .conn
        .query_row("SELECT raw_cas_hash FROM messages LIMIT 1", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert!(!arch.cas_get(&hash).unwrap().is_empty());
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_size_warn_when_on_not_oq5() {
    let root = tmp_root();
    let mbox = root.join("ada.mbox");
    write_ada_mbox(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    let blob = warning_blob(&arch);
    assert!(
        stats.warnings >= 1 || looks_like_size_warning(&blob),
        "flag on must emit a size warning; warnings={} blob={blob}",
        stats.warnings
    );
    assert!(
        looks_like_size_warning(&blob),
        "size warning must mention disk/size (not encrypt); blob={blob}"
    );
    assert!(
        !blob.to_ascii_lowercase().contains("encrypt"),
        "must not say encrypted: {blob}"
    );
    assert!(
        !blob.to_ascii_lowercase().contains("sqlcipher"),
        "must not say SQLCipher: {blob}"
    );
    assert!(
        !claims_export_mbox(&blob),
        "must not claim export mbox exists: {blob}"
    );
    // Size warning is not a recast of OQ5 dump-deletion copy.
    assert!(
        looks_like_size_warning(&blob),
        "do not recast OQ5 dump-deletion as the size warning: {blob}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_oq5_when_off_takeout() {
    let root = tmp_root();
    let tree = write_takeout_tree(
        &root.join("to"),
        &TakeoutGenConfig {
            n_mail: 1,
            n_contacts: 0,
            seed: 13,
        },
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::TakeoutDir, &tree, &ImportOpts::default())
        .unwrap();
    assert!(
        stats.warnings >= 1,
        "OQ5 dump-deletion warning stays when flag is off"
    );
    let blob = warning_blob(&arch);
    assert!(
        looks_like_oq5_dump(&blob),
        "off-path OQ5 is dump deletion / rfc822, not a size recast; blob={blob}"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE raw_cas_hash IS NOT NULL"
        ),
        0
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_duplicate_does_not_backfill() {
    let root = tmp_root();
    let mbox = root.join("ada.mbox");
    write_ada_mbox(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let first = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(first.inserted_messages, 1);
    let second = arch
        .run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    assert_eq!(second.inserted_messages, 0);
    assert_eq!(second.skipped_dupes, 1);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE raw_cas_hash IS NOT NULL"
        ),
        0,
        "duplicate persist must not backfill raw_cas_hash"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM cas_blobs"),
        count(
            &arch,
            "SELECT COUNT(*) FROM attachments WHERE cas_hash IS NOT NULL"
        ),
        "duplicate flagged pass must not leave an unreferenced raw blob"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_second_flagged_import_is_one_blob() {
    let root = tmp_root();
    let mbox = root.join("ada.mbox");
    write_ada_mbox(&mbox);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    let hash1: String = arch
        .conn
        .query_row("SELECT raw_cas_hash FROM messages", [], |r| r.get(0))
        .unwrap();
    let blobs_after_first = count(&arch, "SELECT COUNT(*) FROM cas_blobs");
    let again = arch
        .run_import(SourceKind::GmailMbox, &mbox, &opts_preserve_raw(true))
        .unwrap();
    assert_eq!(again.inserted_messages, 0);
    assert_eq!(again.skipped_dupes, 1);
    let hash2: String = arch
        .conn
        .query_row("SELECT raw_cas_hash FROM messages", [], |r| r.get(0))
        .unwrap();
    assert_eq!(hash1, hash2);
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM cas_blobs"),
        blobs_after_first,
        "second flagged import is CAS1: one cas_blobs row"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_gc_keeps_referenced_raw_deletes_orphan() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    assert!(
        has_column(&arch, "messages", "raw_cas_hash"),
        "messages.raw_cas_hash missing (fail-today)"
    );
    plant_mail_skeleton(&arch);
    let keep = arch
        .cas_put(b"raw rfc822 ada", Some("message/rfc822"))
        .unwrap();
    insert_message_with_raw(&arch, "gmail:<ada-gc@example.com>", Some(&keep));
    let orphan = arch.cas_put(b"orphan-raw", None).unwrap();

    let unref = arch.estimate_unreferenced_cas_bytes().unwrap();
    assert!(unref > 0, "orphan must still count as unreferenced");
    arch.gc_cas().unwrap();
    assert_eq!(
        arch.cas_get(&keep).unwrap(),
        b"raw rfc822 ada",
        "GC/doctor must treat raw_cas_hash as referenced"
    );
    assert!(
        arch.cas_get(&orphan).is_err(),
        "true orphan must still be collected"
    );
    assert_eq!(arch.estimate_unreferenced_cas_bytes().unwrap(), 0);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_doctor_reports_missing_raw_blob() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    assert!(
        has_column(&arch, "messages", "raw_cas_hash"),
        "messages.raw_cas_hash missing (fail-today)"
    );
    plant_mail_skeleton(&arch);
    let missing = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    arch.conn
        .execute(
            "INSERT INTO cas_blobs(hash, size) VALUES (?1, 1)",
            [missing],
        )
        .unwrap();
    insert_message_with_raw(&arch, "gmail:<ada-missing@example.com>", Some(missing));
    let issues = arch.doctor_issues().unwrap();
    assert!(
        issues.iter().any(|i| i.contains("CAS blob missing")),
        "doctor must treat raw_cas_hash like attachments.cas_hash; got {issues:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn preserve_raw_docs_shipped_default_off_no_export() {
    let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let docs = std::fs::read_to_string(root.join("docs/user/import-takeout.md")).unwrap();
    let log = std::fs::read_to_string(root.join("CHANGELOG.md")).unwrap();
    assert!(
        docs.contains("--preserve-raw"),
        "docs must document --preserve-raw"
    );
    assert!(
        !docs.contains("Not in Phase 1"),
        "must drop “Not in Phase 1” for the flag: preserve-raw section"
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
        "CHANGELOG [Unreleased] must mention --preserve-raw"
    );
}
