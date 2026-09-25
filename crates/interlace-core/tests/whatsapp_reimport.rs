//! #420 incremental WhatsApp re-import.
//!
//! Matrix IDs (gate grep): wa-v1-week wa_second_zip_week_keeps_ids
//! wa_reimport_week_ids_stable wa_second_zip_again_adds_nothing
//! wa_reimport_second_zip_again_inserts_nothing wa_reimport_year_index_rises_then_flat
//! wa_interrupted_second_zip_does_not_publish_years wa_quit_second_zip_resumes_same_run
//! wa_resume_rejects_other_source wa_reimport_doctor_inserted_messages
//! wa_reimport_display_name_does_not_merge people-no-name-merge
//! doctor_pane_shows_last_done_inserted
//!
//! Two text-only iOS zips, same chat. Zip B is zip A plus messages seven days
//! later in the same year. Placeholders Ada / Berk / Self only.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    person_list, person_year_counts, CoreError, ImportCancel, ImportOpts, SourceKind,
};
use rusqlite::OptionalExtension;

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-wa420-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn wa_opts(cancel: Option<ImportCancel>) -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some("week-chat".into()),
        cancel,
        ..ImportOpts::default()
    }
}

fn write_ios_zip(dir: &Path, file_stem: &str, lines: &[String]) -> PathBuf {
    std::fs::create_dir_all(dir).unwrap();
    let p = dir.join(format!("{file_stem}.zip"));
    let f = std::fs::File::create(&p).unwrap();
    let mut z = zip::ZipWriter::new(f);
    z.start_file(
        "_chat.txt",
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
    )
    .unwrap();
    let mut chat =
        String::from("[2024-06-01, 09:00:00] Messages and calls are end-to-end encrypted\n");
    for line in lines {
        chat.push_str(line);
        chat.push('\n');
    }
    z.write_all(chat.as_bytes()).unwrap();
    z.finish().unwrap();
    p
}

fn line(day: &str, hms: &str, sender: &str, body: &str) -> String {
    format!("[{day}, {hms}] {sender}: {body}")
}

fn stamp_hms(i: usize) -> String {
    let sec = i % 60;
    let min = (i / 60) % 60;
    let hour = (i / 3600) % 24;
    format!("{hour:02}:{min:02}:{sec:02}")
}

/// Shared chat on 2024-06-01. Zip B appends `extra` lines on 2024-06-08.
fn zip_pair(dir: &Path, extra: usize) -> (PathBuf, PathBuf, Vec<String>, Vec<String>) {
    let base = vec![
        line("2024-06-01", "10:00:01", "Ada", "note-a-1"),
        line("2024-06-01", "10:00:02", "Berk", "note-b-1"),
        line("2024-06-01", "10:00:03", "Self", "note-s-1"),
        line("2024-06-01", "10:00:04", "Ada", "note-a-2"),
    ];
    let mut week = Vec::with_capacity(extra);
    for i in 1..=extra {
        let sender = match i % 3 {
            1 => "Ada",
            2 => "Berk",
            _ => "Self",
        };
        week.push(line(
            "2024-06-08",
            &stamp_hms(i),
            sender,
            &format!("note-w-{i}"),
        ));
    }
    let zip_a = write_ios_zip(&dir.join("a"), "chat-a", &base);
    let mut both = base.clone();
    both.extend(week.iter().cloned());
    let zip_b = write_ios_zip(&dir.join("b"), "chat-b", &both);
    (zip_a, zip_b, base, week)
}

fn message_id(arch: &interlace_core::db::Archive, body: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM messages WHERE body_text = ?1",
            [body],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("message {body}: {e}"))
}

fn latest_run(arch: &interlace_core::db::Archive) -> (i64, String) {
    arch.conn
        .query_row(
            "SELECT id, status FROM import_runs ORDER BY id DESC LIMIT 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap()
}

fn groups_flag(arch: &interlace_core::db::Archive) -> bool {
    let kind: String = arch
        .conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap();
    kind == "group"
}

fn ada_id(arch: &interlace_core::db::Archive) -> i64 {
    person_list(arch)
        .unwrap()
        .into_iter()
        .find(|p| p.display_name == "Ada")
        .unwrap_or_else(|| panic!("Ada person missing"))
        .id
}

fn ada_year(arch: &interlace_core::db::Archive) -> (i64, String) {
    let rows = person_year_counts(arch, ada_id(arch), groups_flag(arch)).unwrap();
    let row = rows
        .iter()
        .find(|r| r.year == 2024)
        .unwrap_or_else(|| panic!("Ada 2024 year row missing: {rows:?}"));
    (row.count, row.first_local_day.clone())
}

fn assert_numeric_inserted(arch: &interlace_core::db::Archive, expect: u64) {
    let st = arch.status().unwrap();
    let li = &st["last_import"];
    let n = li.get("inserted_messages").and_then(|v| v.as_u64());
    assert!(
        n.is_some(),
        "#420: status().last_import has no numeric inserted_messages (got {li})"
    );
    assert_eq!(
        n.unwrap(),
        expect,
        "#420: status().last_import inserted_messages {n:?} != {expect} (newest done run; got {li})"
    );
}

fn wait_committed_messages(db: &Path, at_least: i64, timeout: Duration) -> bool {
    let conn = rusqlite::Connection::open(db).expect("wal reader");
    let start = Instant::now();
    while start.elapsed() < timeout {
        let n: Option<i64> = conn
            .query_row("SELECT COUNT(*) FROM messages", [], |r| r.get(0))
            .optional()
            .ok()
            .flatten();
        if n.is_some_and(|n| n >= at_least) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    false
}

fn join_import<T: Send + 'static>(handle: std::thread::JoinHandle<T>, timeout: Duration) -> T {
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let _ = tx.send(handle.join());
    });
    match rx.recv_timeout(timeout) {
        Ok(Ok(v)) => v,
        Ok(Err(_)) => panic!("run_import thread panicked"),
        Err(_) => panic!("timed out waiting for cancelled run_import"),
    }
}

#[test]
fn wa_reimport_week_ids_stable_and_again_inserts_nothing() {
    const EXTRA: usize = 6;
    let root = tmp_root();
    let (zip_a, zip_b, base, week) = zip_pair(&root.join("zips"), EXTRA);
    let mut arch = init_archive(&root.join("arch")).unwrap();

    let stats_a = arch
        .run_import(SourceKind::WhatsappIosZip, &zip_a, &wa_opts(None))
        .unwrap();
    assert!(stats_a.inserted_messages >= base.len() as u64);
    let n_after_a = count(&arch, "SELECT COUNT(*) FROM messages");
    let overlap: Vec<i64> = base
        .iter()
        .map(|l| {
            let body = l.rsplit(": ").next().unwrap();
            message_id(&arch, body)
        })
        .collect();
    let (year_a, day_a) = ada_year(&arch);

    let stats_b = arch
        .run_import(SourceKind::WhatsappIosZip, &zip_b, &wa_opts(None))
        .unwrap();
    assert_eq!(
        stats_b.inserted_messages, EXTRA as u64,
        "B inserted_messages must equal the added lines"
    );
    let n_after_b = count(&arch, "SELECT COUNT(*) FROM messages");
    assert_eq!(n_after_b, n_after_a + EXTRA as i64);
    for (i, line) in base.iter().enumerate() {
        let body = line.rsplit(": ").next().unwrap();
        assert_eq!(
            message_id(&arch, body),
            overlap[i],
            "overlap messages.id changed for {body}"
        );
    }
    for line in &week {
        let body = line.rsplit(": ").next().unwrap();
        let _ = message_id(&arch, body);
    }
    let (year_b, day_b) = ada_year(&arch);
    assert_eq!(day_b, day_a, "Ada first_local_day must stay");
    assert!(
        year_b > year_a,
        "Ada year message_count must rise once after B ({year_a} -> {year_b})"
    );
    let rise = year_b - year_a;

    let stats_again = arch
        .run_import(SourceKind::WhatsappIosZip, &zip_b, &wa_opts(None))
        .unwrap();
    assert_eq!(
        stats_again.inserted_messages, 0,
        "importing B again must insert 0"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), n_after_b);
    let (year_flat, day_flat) = ada_year(&arch);
    assert_eq!(day_flat, day_a);
    assert_eq!(
        year_flat, year_b,
        "Ada year count must stay flat after B is done (rose {rise}, then {year_b} -> {year_flat})"
    );
    for (i, line) in base.iter().enumerate() {
        let body = line.rsplit(": ").next().unwrap();
        assert_eq!(message_id(&arch, body), overlap[i]);
    }

    assert_numeric_inserted(&arch, 0);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn wa_quit_second_zip_resumes_same_run() {
    let root = tmp_root();
    let (zip_a, zip_b, _, week) = zip_pair(&root.join("zips"), 6);
    let arch_path = root.join("arch");
    let db = arch_path.join("archive.sqlite");
    let mut arch = init_archive(&arch_path).unwrap();
    arch.run_import(SourceKind::WhatsappIosZip, &zip_a, &wa_opts(None))
        .unwrap();
    let (run_a, _) = latest_run(&arch);

    let token = ImportCancel::new();
    let opts = wa_opts(Some(token.clone()));
    let zip_t = zip_b.clone();
    let handle = std::thread::spawn(move || {
        let result = arch.run_import(SourceKind::WhatsappIosZip, &zip_t, &opts);
        (result, arch)
    });
    let started = {
        let conn = rusqlite::Connection::open(&db).unwrap();
        let start = Instant::now();
        let mut ok = false;
        while start.elapsed() < Duration::from_secs(15) {
            let row: Option<(i64, String)> = conn
                .query_row(
                    "SELECT id, status FROM import_runs ORDER BY id DESC LIMIT 1",
                    [],
                    |r| Ok((r.get(0)?, r.get(1)?)),
                )
                .optional()
                .unwrap();
            if let Some((id, st)) = row {
                if id != run_a && st == "running" {
                    ok = true;
                    break;
                }
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        ok
    };
    assert!(started, "zip B import must reach running before cancel");
    token.cancel();
    let (result, mut arch) = join_import(handle, Duration::from_secs(15));
    let err = result.expect_err("cancel must interrupt zip B");
    assert!(
        matches!(err, CoreError::Cancelled),
        "interrupt must be Cancelled, got {err}"
    );
    let (interrupted_id, status) = latest_run(&arch);
    assert_ne!(interrupted_id, run_a);
    assert_eq!(
        status, "interrupted",
        "quit must leave B interrupted, got {status}"
    );

    let stats = arch
        .run_import(SourceKind::WhatsappIosZip, &zip_b, &wa_opts(None))
        .expect("resume of B with resume_run_id None");
    let (after_id, after_status) = latest_run(&arch);
    assert_eq!(
        after_id, interrupted_id,
        "#420: run_import of the same zip after an interrupt, with resume_run_id None, \
         starts a new run instead of reusing the interrupted one \
         (interrupted={interrupted_id} latest={after_id})"
    );
    assert_eq!(after_status, "done");
    assert_eq!(
        stats.inserted_messages,
        week.len() as u64,
        "resumed B must publish the week once"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn wa_interrupted_prefix_is_not_published_by_later_done() {
    const EXTRA: usize = 1_200;
    let root = tmp_root();
    let (zip_a, zip_b, _, _) = zip_pair(&root.join("zips"), EXTRA);
    let arch_path = root.join("arch");
    let db = arch_path.join("archive.sqlite");
    let mut arch = init_archive(&arch_path).unwrap();
    arch.run_import(SourceKind::WhatsappIosZip, &zip_a, &wa_opts(None))
        .unwrap();
    let (year_a, day_a) = ada_year(&arch);
    let n_after_a = count(&arch, "SELECT COUNT(*) FROM messages");

    let token = ImportCancel::new();
    let opts = wa_opts(Some(token.clone()));
    let zip_t = zip_b.clone();
    let handle = std::thread::spawn(move || {
        let result = arch.run_import(SourceKind::WhatsappIosZip, &zip_t, &opts);
        (result, arch)
    });
    assert!(
        wait_committed_messages(&db, n_after_a + 1_000, Duration::from_secs(60)),
        "zip B must commit a prefix before cancel"
    );
    token.cancel();
    let (result, mut arch) = join_import(handle, Duration::from_secs(20));
    assert!(
        matches!(result, Err(CoreError::Cancelled)),
        "prefix cancel must be Cancelled, got {result:?}"
    );
    let (year_mid, _) = ada_year(&arch);
    assert_eq!(
        year_mid, year_a,
        "cancel must leave year rows at the post-A snapshot ({year_a} vs {year_mid})"
    );
    assert_ne!(latest_run(&arch).1, "done");

    let vcf = root.join("berk.vcf");
    std::fs::write(
        &vcf,
        "BEGIN:VCARD\nVERSION:3.0\nFN:Berk\nN:Berk;;;;\n\
         EMAIL;TYPE=INTERNET:berk@example.com\nEND:VCARD\n",
    )
    .unwrap();
    arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default())
        .expect("later contacts import");
    let (year_after, day_after) = ada_year(&arch);
    assert_eq!(day_after, day_a);
    assert_eq!(
        year_after, year_a,
        "#420: after a committed prefix of zip B is interrupted, a later successful import \
         publishes those rows into person_year_counts (year count rose before zip B is done: \
         post-A={year_a} after later done={year_after})"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn wa_resume_rejects_other_source() {
    let root = tmp_root();
    let (zip_a, zip_b, _, _) = zip_pair(&root.join("zips"), 3);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::WhatsappIosZip, &zip_a, &wa_opts(None))
        .unwrap();
    let (run_a, status_a) = latest_run(&arch);
    assert_eq!(status_a, "done");

    let err = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip_b,
            &ImportOpts {
                resume_run_id: Some(run_a),
                ..wa_opts(None)
            },
        )
        .expect_err("resume of A's run against B must error");
    let msg = err.to_string();
    assert!(
        msg.contains("different source"),
        "resume of A's run against B must say different source, got {msg}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn wa_reimport_display_name_does_not_merge() {
    let root = tmp_root();
    let (zip_a, _, _, _) = zip_pair(&root.join("zips"), 0);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::WhatsappIosZip, &zip_a, &wa_opts(None))
        .unwrap();
    let vcf = root.join("ada.vcf");
    std::fs::write(
        &vcf,
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ada\nN:Ada;;;;\n\
         EMAIL;TYPE=INTERNET:ada@example.com\nEND:VCARD\n",
    )
    .unwrap();
    arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default())
        .unwrap();

    let adas = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND display_name = 'Ada'",
    );
    assert_eq!(
        adas, 2,
        "two display names must not become one person (Ada count={adas})"
    );
    let ada_ids: Vec<i64> = {
        let mut stmt = arch
            .conn
            .prepare(
                "SELECT id FROM persons WHERE tombstoned_at IS NULL AND display_name = 'Ada' ORDER BY id",
            )
            .unwrap();
        stmt.query_map([], |r| r.get(0))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };
    assert_eq!(ada_ids.len(), 2);
    assert_ne!(ada_ids[0], ada_ids[1]);
    let _ = std::fs::remove_dir_all(&root);
}
