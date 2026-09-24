//! #419 stored year index. Placeholders Ada / Berk / Self only.
//!
//! `person_year_index` is one row per person, year, and include-groups flag.
//! `person_year_counts` reads that table (JSON `count` is `message_count`).
//! It does not scan `messages`. An empty person, Berk with no rows, and an
//! unknown id are empty vecs. No sentinel and no count 0.
//!
//! The writer stores the timeline day key: WhatsApp keeps the stored
//! `YYYY-MM-DD` digits; gmail uses host `localtime`.

use std::ffi::CString;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::person_year_counts;

unsafe extern "C" {
    fn setenv(name: *const i8, value: *const i8, overwrite: i32) -> i32;
    fn tzset();
}

static SEQ: AtomicU64 = AtomicU64::new(0);

fn force_los_angeles() {
    let key = CString::new("TZ").unwrap();
    let val = CString::new("America/Los_Angeles").unwrap();
    unsafe {
        setenv(key.as_ptr(), val.as_ptr(), 1);
        tzset();
    }
}

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-year-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

/// Execute SQL against `person_year_index`. A missing migration fails here
/// at runtime (`no such table`), not only by failing to compile.
fn require_year_index(arch: &interlace_core::db::Archive) {
    let listed: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM sqlite_master
             WHERE type = 'table' AND name = 'person_year_index'",
            [],
            |row| row.get(0),
        )
        .expect("sqlite_master");
    arch.conn
        .query_row("SELECT COUNT(*) FROM person_year_index", [], |row| {
            row.get::<_, i64>(0)
        })
        .expect("no such table: person_year_index");
    assert_eq!(listed, 1, "sqlite_master has no person_year_index");
}

fn person(arch: &interlace_core::db::Archive, name: &str, is_self: i64) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, ?2)",
            rusqlite::params![name, is_self],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn seed_year(
    arch: &interlace_core::db::Archive,
    person_id: i64,
    include_groups: i64,
    year: i64,
    message_count: i64,
    first_local_day: &str,
) {
    arch.conn
        .execute(
            "INSERT INTO person_year_index(
                person_id, include_groups, year, message_count, first_local_day
             ) VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![
                person_id,
                include_groups,
                year,
                message_count,
                first_local_day
            ],
        )
        .unwrap();
}

fn ident(arch: &interlace_core::db::Archive, platform: &str, raw: &str, norm: &str) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES (?1, 'display_name', ?2, ?3, ?2)",
            rusqlite::params![platform, raw, norm],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn link(arch: &interlace_core::db::Archive, pid: i64, iid: i64) {
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![pid, iid],
        )
        .unwrap();
}

fn conv(arch: &interlace_core::db::Archive, platform: &str, kind: &str, native: &str) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES (?1, ?2, ?3, ?3)",
            rusqlite::params![platform, kind, native],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn part(arch: &interlace_core::db::Archive, cid: i64, iid: i64) {
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![cid, iid],
        )
        .unwrap();
}

fn msg(
    arch: &interlace_core::db::Archive,
    cid: i64,
    src: i64,
    run: i64,
    sender: i64,
    sent_at: &str,
    key: &str,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6)",
            rusqlite::params![cid, src, run, sender, sent_at, key],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn stored_year(
    arch: &interlace_core::db::Archive,
    person_id: i64,
    include_groups: i64,
) -> (i64, i64, String) {
    arch.conn
        .query_row(
            "SELECT year, message_count, first_local_day
             FROM person_year_index
             WHERE person_id = ?1 AND include_groups = ?2",
            rusqlite::params![person_id, include_groups],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .expect("no such table: person_year_index")
}

#[test]
fn person_year_index_missing_after_migrate() {
    let dir = tmp();
    let arch = init_archive(&dir).unwrap();
    require_year_index(&arch);
}

#[test]
fn person_year_counts_reads_seeded_index_not_messages() {
    let dir = tmp();
    let arch = init_archive(&dir).unwrap();
    require_year_index(&arch);

    let ada = person(&arch, "Ada", 0);
    let berk = person(&arch, "Berk", 0);
    let empty = person(&arch, "Self", 1);
    let unknown = empty + 1000;

    seed_year(&arch, ada, 0, 2024, 4, "2024-11-02");
    seed_year(&arch, ada, 0, 2019, 2, "2019-04-01");
    seed_year(&arch, ada, 1, 2021, 9, "2021-08-08");
    seed_year(&arch, ada, 1, 2018, 3, "2018-07-04");

    let messages: i64 = arch
        .conn
        .query_row("SELECT COUNT(*) FROM messages", [], |row| row.get(0))
        .unwrap();
    assert_eq!(
        messages, 0,
        "seeded years must not come from a message scan"
    );

    let dm = person_year_counts(&arch, ada, false).unwrap();
    assert_eq!(dm.len(), 2, "include_groups false is Ada 2024 then 2019");
    assert_eq!(dm[0].year, 2024);
    assert_eq!(dm[0].count, 4);
    assert_eq!(dm[0].first_local_day, "2024-11-02");
    assert_eq!(dm[1].year, 2019);
    assert_eq!(dm[1].count, 2);
    assert_eq!(dm[1].first_local_day, "2019-04-01");
    assert!(
        dm.iter().all(|row| row.year != 2021 && row.year != 2018),
        "a year stored only for include_groups true is absent for false"
    );

    let groups = person_year_counts(&arch, ada, true).unwrap();
    assert!(
        groups.iter().any(|row| row.year == 2021 && row.count == 9),
        "2021 is only on include_groups true"
    );
    assert!(
        groups.iter().any(|row| {
            row.year == 2018 && row.count == 3 && row.first_local_day == "2018-07-04"
        }),
        "the group-only year is present for include_groups true"
    );
    assert!(
        groups
            .iter()
            .all(|row| row.year != 2024 && row.year != 2019),
        "include_groups true must not return the false-flag rows"
    );
    let true_years: Vec<i64> = groups.iter().map(|row| row.year).collect();
    let mut sorted = true_years.clone();
    sorted.sort_unstable_by(|a, b| b.cmp(a));
    assert_eq!(true_years, sorted, "newest year first");

    assert!(person_year_counts(&arch, empty, false).unwrap().is_empty());
    assert!(person_year_counts(&arch, empty, true).unwrap().is_empty());
    assert!(person_year_counts(&arch, unknown, false)
        .unwrap()
        .is_empty());
    assert!(person_year_counts(&arch, unknown, true).unwrap().is_empty());
    assert!(
        person_year_counts(&arch, berk, false).unwrap().is_empty(),
        "Berk with no rows is empty"
    );
    assert!(person_year_counts(&arch, berk, true).unwrap().is_empty());
}

#[test]
fn person_year_index_stores_timeline_day_key() {
    force_los_angeles();
    let dir = tmp();
    let arch = init_archive(&dir).unwrap();
    require_year_index(&arch);

    let local: String = arch
        .conn
        .query_row(
            "SELECT strftime('%Y-%m-%d', '2020-06-16T06:30:00Z', 'localtime')",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(
        local, "2020-06-15",
        "probe: gmail localtime is not the stored digits"
    );

    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_android_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();

    let ada_iid = ident(&arch, "whatsapp", "Ada", "ada");
    let berk_iid = ident(&arch, "gmail", "Berk", "berk");
    let ada = person(&arch, "Ada", 0);
    let berk = person(&arch, "Berk", 0);
    link(&arch, ada, ada_iid);
    link(&arch, berk, berk_iid);

    let ada_dm = conv(&arch, "whatsapp", "dm", "whatsapp:ada");
    let berk_mail = conv(&arch, "gmail", "email_thread", "gmail:berk");
    part(&arch, ada_dm, ada_iid);
    part(&arch, berk_mail, berk_iid);
    msg(
        &arch,
        ada_dm,
        src,
        run,
        ada_iid,
        "2020-06-16T06:30:00Z",
        "ada-wa",
    );
    msg(
        &arch,
        berk_mail,
        src,
        run,
        berk_iid,
        "2020-06-16T06:30:00Z",
        "berk-gmail",
    );

    interlace_core::rebuild_activity_years(&arch, Some(ada)).unwrap();
    interlace_core::rebuild_activity_years(&arch, Some(berk)).unwrap();

    let (ada_year, _ada_count, ada_day) = stored_year(&arch, ada, 0);
    assert_eq!(ada_year, 2020);
    assert_eq!(
        ada_day, "2020-06-16",
        "WhatsApp keeps the stored YYYY-MM-DD digits"
    );
    let (berk_year, _berk_count, berk_day) = stored_year(&arch, berk, 0);
    assert_eq!(berk_year, 2020);
    assert_eq!(
        berk_day, "2020-06-15",
        "gmail America/Los_Angeles stores the local day, not the UTC digits"
    );
}
