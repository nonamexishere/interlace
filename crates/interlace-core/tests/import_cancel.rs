//! Cooperative import cancel (#266).
//!
//! Not a Phase 1 matrix ID — do not add to `test_plan.json`.
//!
//! Expected public API (tests fail to compile until impl lands):
//!
//! ```ignore
//! // `crates/interlace-core/src/model.rs`, re-exported from the crate root.
//! #[derive(Debug, Clone)]
//! pub struct ImportCancel { /* internally Arc<AtomicBool> */ }
//! impl ImportCancel {
//!     pub fn new() -> Self;
//!     pub fn cancel(&self);
//!     pub fn is_cancelled(&self) -> bool;
//! }
//!
//! // Additional field on `ImportOpts` (`Default` = `None`):
//! pub cancel: Option<ImportCancel>,
//! ```
//!
//! `run_import` (start of each file), `ImportContext::heartbeat`, and
//! `maybe_commit` must observe the flag. When set: stop new work, roll back
//! only the open uncommitted txn, mark that `import_runs` row `interrupted`
//! (preferred) or `failed`, and return a distinct cancel error whose Display
//! contains "cancel" or "interrupt". Do not delete already-committed rows.
//! Do not `thread::kill` / `JoinHandle::abort`.
//!
//! In-file cancel (#266 follow-up): the flag must also abort the *current*
//! `run_import` during ZIP open / list / BLAKE3 hash / persist — not only
//! between files or at `run_import` entry. Mid-flight handshake (public
//! shape; no new merge hook): `ImportCancel` is `Clone` + `Send`. Spawn
//! `run_import`, poll WAL `archive.sqlite` until `import_runs.status =
//! running` (probe/hash has started), then `cancel()` and join with a short
//! timeout. Must return `CoreError::Cancelled` and must not finish the file
//! (inserted / skipped_dupes well below the fixture). Placeholder `Ada` only.
//!
//! Same-file re-import after cancel-before-start: one `sources` row for
//! that kind + origin; `file_blake3` filled on the success path (not a
//! leftover hashless fork).

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{CoreError, ImportCancel, ImportOpts, SourceKind};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-ic-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn origin_key(path: &std::path::Path) -> String {
    path.canonicalize()
        .unwrap_or_else(|_| path.to_path_buf())
        .to_string_lossy()
        .to_string()
}

fn sources_for_origin(arch: &interlace_core::db::Archive, kind: &str, origin: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM sources WHERE kind = ?1 AND origin_path = ?2",
            rusqlite::params![kind, origin],
            |r| r.get(0),
        )
        .unwrap()
}

/// Tiny contacts card. Placeholder name only.
fn write_ada_vcf(path: &std::path::Path) {
    std::fs::write(
        path,
        "BEGIN:VCARD\n\
         VERSION:3.0\n\
         FN:Ada\n\
         N:Ada;;;;\n\
         TEL;TYPE=CELL:+15555550100\n\
         EMAIL;TYPE=INTERNET:ada@example.com\n\
         END:VCARD\n",
    )
    .unwrap();
}

fn cancelled_opts() -> ImportOpts {
    let token = ImportCancel::new();
    token.cancel();
    ImportOpts {
        cancel: Some(token),
        ..ImportOpts::default()
    }
}

fn ada_wa_opts(cancel: Option<ImportCancel>) -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some("Ada".into()),
        cancel,
        ..ImportOpts::default()
    }
}

/// iOS ZIP, placeholder Ada only. `file_stem` is not a real export title.
fn write_ada_ios_zip(
    dir: &std::path::Path,
    file_stem: &str,
    n_messages: usize,
    body_prefix: &str,
) -> std::path::PathBuf {
    use std::io::Write;
    std::fs::create_dir_all(dir).unwrap();
    let p = dir.join(format!("{file_stem}.zip"));
    let f = std::fs::File::create(&p).unwrap();
    let mut z = zip::ZipWriter::new(f);
    z.start_file(
        "_chat.txt",
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
    )
    .unwrap();
    let mut chat = String::with_capacity(n_messages * 56 + 96);
    chat.push_str("[2024-01-15, 10:00:00] Messages and calls are end-to-end encrypted\n");
    for i in 1..=n_messages {
        let sec = i % 60;
        let min = (i / 60) % 60;
        let hour = 10 + (i / 3600);
        chat.push_str(&format!(
            "[2024-01-15, {hour:02}:{min:02}:{sec:02}] Ada: {body_prefix}{i}\n"
        ));
    }
    z.write_all(chat.as_bytes()).unwrap();
    z.finish().unwrap();
    p
}

/// WAL reader — Exclusive flock stays with the import `Archive`.
fn wait_latest_run(
    db: &std::path::Path,
    timeout: Duration,
    pred: impl Fn(i64, &str) -> bool,
) -> bool {
    use rusqlite::OptionalExtension;
    let conn = rusqlite::Connection::open(db).expect("wal reader for import_runs handshake");
    let start = Instant::now();
    while start.elapsed() < timeout {
        let row: Option<(i64, String)> = conn
            .query_row(
                "SELECT id, status FROM import_runs ORDER BY id DESC LIMIT 1",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .optional()
            .expect("poll import_runs");
        if let Some((id, st)) = row {
            if pred(id, &st) {
                return true;
            }
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    false
}

fn join_with_timeout<T: Send + 'static>(
    handle: std::thread::JoinHandle<T>,
    timeout: Duration,
) -> Result<T, &'static str> {
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let _ = tx.send(handle.join());
    });
    match rx.recv_timeout(timeout) {
        Ok(Ok(v)) => Ok(v),
        Ok(Err(_)) => panic!("run_import thread panicked"),
        Err(_) => Err("timed out waiting for cancelled run_import (in-file cancel must abort)"),
    }
}

fn latest_run_status(arch: &interlace_core::db::Archive) -> String {
    arch.conn
        .query_row(
            "SELECT status FROM import_runs ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .expect("cancelled run_import must leave an import_runs row")
}

fn assert_distinct_cancel_err(err: &interlace_core::CoreError, vcf: &std::path::Path) {
    let msg = err.to_string();
    let lower = msg.to_ascii_lowercase();
    assert!(
        lower.contains("cancel") || lower.contains("interrupt"),
        "distinct cancel error (Display contains cancel/interrupt), got {err}"
    );
    assert!(
        !msg.contains("Ada"),
        "cancel error must not dump a contact name: {msg}"
    );
    let path_s = vcf.to_string_lossy();
    assert!(
        !msg.contains(path_s.as_ref()),
        "cancel error must not dump the import path: {msg}"
    );
}

fn plant_committed_ada(arch: &interlace_core::db::Archive) {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('contacts', 'email', 'ada@example.com', 'ada@example.com', 'Ada')",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
}

fn assert_status_matches_sql(arch: &interlace_core::db::Archive) {
    let st = arch.status().unwrap();
    let messages = count(arch, "SELECT COUNT(*) FROM messages");
    let identities = count(arch, "SELECT COUNT(*) FROM identities");
    let persons_live = count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    );
    let review_open = count(
        arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status = 'open'",
    );
    assert_eq!(
        st["messages"], messages,
        "status.messages must be SQL COUNT"
    );
    assert_eq!(
        st["identities"], identities,
        "status.identities must be SQL COUNT"
    );
    assert_eq!(
        st["persons_live"], persons_live,
        "status.persons_live must be SQL COUNT"
    );
    assert_eq!(
        st["review_open"], review_open,
        "status.review_open must be SQL COUNT"
    );
}

/// Cancel is a real core path: flag set before `run_import` stops the run.
#[test]
fn cancel_before_run_import_marks_run_interrupted() {
    let root = tmp_root();
    let vcf = root.join("ada.vcf");
    write_ada_vcf(&vcf);
    let mut arch = init_archive(&root.join("arch")).unwrap();

    let err = arch
        .run_import(SourceKind::ContactsVcf, &vcf, &cancelled_opts())
        .expect_err("cancel must not succeed as a full done import");
    assert_distinct_cancel_err(&err, &vcf);

    let status = latest_run_status(&arch);
    assert!(
        status == "interrupted" || status == "failed",
        "cancel must mark import_runs.status interrupted (preferred) or failed, got {status}"
    );
    assert_ne!(status, "done", "cancelled run must not be marked done");
    assert_ne!(status, "running", "cancelled run must not stay running");
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM import_runs WHERE status = 'done'"
        ),
        0,
        "cancel-before-start must not insert a success done row"
    );

    let _ = std::fs::remove_dir_all(&root);
}

/// Partial committed work stays. Cancel is not a fake full rollback.
#[test]
fn cancel_does_not_rollback_committed_rows() {
    let root = tmp_root();
    let vcf = root.join("ada.vcf");
    write_ada_vcf(&vcf);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    plant_committed_ada(&arch);

    let identities_before = count(&arch, "SELECT COUNT(*) FROM identities");
    let persons_before = count(&arch, "SELECT COUNT(*) FROM persons");
    assert!(
        identities_before > 0 && persons_before > 0,
        "fixture must commit Ada before cancel"
    );

    let err = arch
        .run_import(SourceKind::ContactsVcf, &vcf, &cancelled_opts())
        .expect_err("cancel must not succeed as a full done import");
    assert_distinct_cancel_err(&err, &vcf);

    let identities_after = count(&arch, "SELECT COUNT(*) FROM identities");
    let persons_after = count(&arch, "SELECT COUNT(*) FROM persons");
    assert!(
        identities_after >= identities_before,
        "committed identities must stay (no fake rollback to zero); before={identities_before} after={identities_after}"
    );
    assert!(
        persons_after >= persons_before,
        "committed persons must stay (no fake rollback to zero); before={persons_before} after={persons_after}"
    );
    assert_ne!(
        identities_after, 0,
        "COUNT must not go to zero when the fixture already committed"
    );

    assert_status_matches_sql(&arch);

    let _ = std::fs::remove_dir_all(&root);
}

/// Not a thread kill: after cancel, a second `run_import` can start.
#[test]
fn second_run_import_after_cancel_starts() {
    let root = tmp_root();
    let vcf = root.join("ada.vcf");
    write_ada_vcf(&vcf);
    let mut arch = init_archive(&root.join("arch")).unwrap();

    let err = arch
        .run_import(SourceKind::ContactsVcf, &vcf, &cancelled_opts())
        .expect_err("cancel must not succeed as a full done import");
    assert_distinct_cancel_err(&err, &vcf);

    let again = arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default());
    assert!(
        again.is_ok(),
        "archive must stay usable after cancel (no thread kill); second run_import: {again:?}"
    );

    assert_status_matches_sql(&arch);

    let _ = std::fs::remove_dir_all(&root);
}

/// Cancel-before-start then a successful re-import of the same Ada vcf
/// must reuse one `sources` row and fill `file_blake3`.
#[test]
fn cancel_then_success_reuses_one_sources_row() {
    let root = tmp_root();
    let vcf = root.join("ada.vcf");
    write_ada_vcf(&vcf);
    let mut arch = init_archive(&root.join("arch")).unwrap();

    let err = arch
        .run_import(SourceKind::ContactsVcf, &vcf, &cancelled_opts())
        .expect_err("cancel must not succeed as a full done import");
    assert_distinct_cancel_err(&err, &vcf);

    let origin = origin_key(&vcf);
    arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default())
        .expect("second run_import of the same file must succeed");

    let n = sources_for_origin(&arch, "contacts_vcf", &origin);
    assert_eq!(
        n, 1,
        "re-import of the same file must reuse one sources row; got {n}"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM sources WHERE kind = 'contacts_vcf'"
        ),
        1,
        "same-file re-import must not fork a second sources row for contacts_vcf"
    );

    let blake3: Option<String> = arch
        .conn
        .query_row(
            "SELECT file_blake3 FROM sources WHERE kind = ?1 AND origin_path = ?2",
            rusqlite::params!["contacts_vcf", origin],
            |r| r.get(0),
        )
        .unwrap();
    assert!(
        blake3.as_deref().is_some_and(|h| !h.is_empty()),
        "success path must fill file_blake3 on the reused row (not a leftover hashless fork); got {blake3:?}"
    );

    let _ = std::fs::remove_dir_all(&root);
}

/// Cancel during file 1 of a 4-ZIP folder must abort that `run_import`
/// (not finish file 1, not skip/insert the rest).
#[test]
fn cancel_mid_run_import_does_not_finish_file_one() {
    const N1: usize = 2000;
    let root = tmp_root();
    let zips_dir = root.join("zips");
    let zip1 = write_ada_ios_zip(&zips_dir, "ada-1", N1, "f1-");
    let zip2 = write_ada_ios_zip(&zips_dir, "ada-2", 8, "f2-");
    let zip3 = write_ada_ios_zip(&zips_dir, "ada-3", 8, "f3-");
    let zip4 = write_ada_ios_zip(&zips_dir, "ada-4", 8, "f4-");
    let zips = vec![zip1.clone(), zip2, zip3, zip4];

    let arch_path = root.join("arch");
    let db = arch_path.join("archive.sqlite");
    let arch = init_archive(&arch_path).unwrap();
    let token = ImportCancel::new();
    let token_loop = token.clone();
    let opts = ada_wa_opts(Some(token.clone()));

    let handle = std::thread::spawn(move || {
        let mut arch = arch;
        let mut last: Option<Result<interlace_core::ImportStats, CoreError>> = None;
        for z in &zips {
            if token_loop.is_cancelled() {
                break;
            }
            let r = arch.run_import(SourceKind::WhatsappIosZip, z, &opts);
            let stop = r.is_err();
            last = Some(r);
            if stop {
                break;
            }
        }
        (last, arch)
    });

    assert!(
        wait_latest_run(&db, Duration::from_secs(15), |_, st| st == "running"),
        "file 1 persist/hash must start so cancel is mid-run_import, not before start"
    );
    token.cancel();

    let (last, arch) = join_with_timeout(handle, Duration::from_secs(5))
        .expect("cancel must abort the current ZIP before file 1 finishes");
    let last = last.expect("file 1 run_import must have started");
    let err = last.expect_err("cancel during file 1 must not succeed as a full done import");
    assert!(
        matches!(err, CoreError::Cancelled),
        "mid-file cancel must be CoreError::Cancelled, got {err}"
    );
    assert_distinct_cancel_err(&err, &zip1);

    let n = count(&arch, "SELECT COUNT(*) FROM messages");
    assert!(
        n < N1 as i64,
        "must not finish file 1 (must not insert/skip the rest); messages={n} fixture={N1}"
    );
    let rest = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE body_text LIKE 'f2-%' \
         OR body_text LIKE 'f3-%' OR body_text LIKE 'f4-%'",
    );
    assert_eq!(
        rest, 0,
        "must not skip/insert files 2–4 after cancel during file 1"
    );

    let status = latest_run_status(&arch);
    assert!(
        status == "interrupted" || status == "failed",
        "mid-file cancel must mark import_runs interrupted (preferred) or failed, got {status}"
    );
    assert_ne!(status, "done", "cancelled file 1 must not be marked done");
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM import_runs WHERE status = 'done'"
        ),
        0,
        "4-ZIP cancel during file 1 must not leave a done run"
    );

    let _ = std::fs::remove_dir_all(&root);
}

/// Re-import of an already-imported Ada ZIP: cancel must not drain the rest
/// of the file as skipped dupes (dogfood: 2269 dupes after Cancel).
#[test]
fn cancel_mid_reimport_does_not_drain_dupes() {
    const N: usize = 2000;
    let root = tmp_root();
    let zip = write_ada_ios_zip(&root.join("zips"), "ada-re", N, "re-");
    let arch_path = root.join("arch");
    let db = arch_path.join("archive.sqlite");
    let mut arch = init_archive(&arch_path).unwrap();

    let first = arch
        .run_import(SourceKind::WhatsappIosZip, &zip, &ada_wa_opts(None))
        .expect("seed import of Ada ZIP");
    assert!(
        first.inserted_messages >= N as u64 || first.skipped_dupes >= N as u64,
        "seed import must process the fixture; inserted={} skipped={}",
        first.inserted_messages,
        first.skipped_dupes
    );
    let baseline = count(&arch, "SELECT COUNT(*) FROM messages");
    assert!(
        baseline >= N as i64,
        "seed import must leave the fixture in messages; count={baseline}"
    );
    let first_id: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM import_runs ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();

    let token = ImportCancel::new();
    let opts = ada_wa_opts(Some(token.clone()));
    let zip_t = zip.clone();
    let handle = std::thread::spawn(move || {
        let result = arch.run_import(SourceKind::WhatsappIosZip, &zip_t, &opts);
        (result, arch)
    });

    assert!(
        wait_latest_run(&db, Duration::from_secs(15), |id, st| {
            id > first_id && st == "running"
        }),
        "re-import persist/hash must start so cancel is mid-run_import"
    );
    token.cancel();

    let (result, arch) = join_with_timeout(handle, Duration::from_secs(5))
        .expect("cancel must abort the re-import before the ZIP is fully skipped");
    let err = result.expect_err("mid-reimport cancel must not succeed as a full done import");
    assert!(
        matches!(err, CoreError::Cancelled),
        "mid-reimport cancel must be CoreError::Cancelled, got {err}"
    );
    assert_distinct_cancel_err(&err, &zip);

    let status = latest_run_status(&arch);
    assert!(
        status == "interrupted" || status == "failed",
        "mid-reimport cancel must mark import_runs interrupted (preferred) or failed, got {status}"
    );
    assert_ne!(
        status, "done",
        "cancelled re-import must not be marked done"
    );

    let skipped: i64 = arch
        .conn
        .query_row(
            "SELECT COALESCE(json_extract(stats_json, '$.skipped_dupes'), 0)
             FROM import_runs ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap_or(0);
    assert!(
        skipped < N as i64,
        "skipped_dupes must be only work before the flag, not the whole file; skipped={skipped} fixture={N}"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        baseline,
        "re-import cancel must not invent a rollback of the seed import"
    );

    let _ = std::fs::remove_dir_all(&root);
}
