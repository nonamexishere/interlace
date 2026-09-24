//! #418 day lookup. Public function: `person_day_message`.
//!
//! Earliest message on that local day (lowest `sent_at`, then lowest id).
//! WhatsApp uses stored `YYYY-MM-DD` digits. Gmail uses host `localtime`
//! (same calendar as `person_year_counts`; blank or null platform would
//! use the stored digits too, but `conversations.platform` only allows
//! whatsapp and gmail). `include_groups` false keeps `dm` and
//! `email_thread`. A missing day is `None`. No message bodies.
//! Placeholders Ada / Berk / Self only.

use std::ffi::CString;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::person_day_message;

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
    let p = std::env::temp_dir().join(format!("il-day-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
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

fn person(arch: &interlace_core::db::Archive, name: &str, is_self: i64) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, ?2)",
            rusqlite::params![name, is_self],
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

#[test]
fn person_day_message_earliest_on_local_day() {
    force_los_angeles();
    let dir = tmp();
    let arch = init_archive(&dir).unwrap();
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
    let self_iid = ident(&arch, "whatsapp", "Self", "self");
    let ada = person(&arch, "Ada", 0);
    let berk = person(&arch, "Berk", 0);
    let self_id = person(&arch, "Self", 1);
    link(&arch, ada, ada_iid);
    link(&arch, berk, berk_iid);
    link(&arch, self_id, self_iid);

    let ada_dm = conv(&arch, "whatsapp", "dm", "whatsapp:ada");
    let ada_group = conv(&arch, "whatsapp", "group", "whatsapp:ada-group");
    let berk_mail = conv(&arch, "gmail", "email_thread", "gmail:berk");
    let self_dm = conv(&arch, "whatsapp", "dm", "whatsapp:self");
    part(&arch, ada_dm, ada_iid);
    part(&arch, ada_group, ada_iid);
    part(&arch, berk_mail, berk_iid);
    part(&arch, self_dm, self_iid);

    let later = msg(
        &arch,
        ada_dm,
        src,
        run,
        ada_iid,
        "2020-05-02T08:00:00Z",
        "ada-later",
    );
    let earlier = msg(
        &arch,
        ada_dm,
        src,
        run,
        ada_iid,
        "2020-05-02T07:00:00Z",
        "ada-earlier",
    );
    let same_later_id = msg(
        &arch,
        ada_dm,
        src,
        run,
        ada_iid,
        "2020-05-02T07:00:00Z",
        "ada-tie",
    );
    let group_early = msg(
        &arch,
        ada_group,
        src,
        run,
        ada_iid,
        "2020-05-02T01:00:00Z",
        "ada-group",
    );
    let group_only = msg(
        &arch,
        ada_group,
        src,
        run,
        ada_iid,
        "2020-08-01T12:00:00Z",
        "ada-group-only",
    );
    let stored_digits = msg(
        &arch,
        ada_dm,
        src,
        run,
        ada_iid,
        "2020-06-16T06:30:00Z",
        "ada-stored",
    );
    let mail = msg(
        &arch,
        berk_mail,
        src,
        run,
        berk_iid,
        "2020-06-16T06:30:00Z",
        "berk-mail",
    );
    let self_msg = msg(
        &arch,
        self_dm,
        src,
        run,
        self_iid,
        "2020-03-01T12:00:00Z",
        "self-note",
    );
    assert!(earlier > later);
    assert!(same_later_id > earlier);

    assert_eq!(
        person_day_message(&arch, ada, "2020-05-02", false).unwrap(),
        Some((earlier, "2020-05-02T07:00:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, ada, "2020-05-02", true).unwrap(),
        Some((group_early, "2020-05-02T01:00:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, ada, "2020-08-01", false).unwrap(),
        None
    );
    assert_eq!(
        person_day_message(&arch, ada, "2020-08-01", true).unwrap(),
        Some((group_only, "2020-08-01T12:00:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, ada, "2020-06-16", false).unwrap(),
        Some((stored_digits, "2020-06-16T06:30:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, ada, "2020-06-15", false).unwrap(),
        None
    );
    assert_eq!(
        person_day_message(&arch, berk, "2020-06-15", false).unwrap(),
        Some((mail, "2020-06-16T06:30:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, berk, "2020-06-16", false).unwrap(),
        None
    );
    assert_eq!(
        person_day_message(&arch, self_id, "2020-03-01", false).unwrap(),
        Some((self_msg, "2020-03-01T12:00:00Z".to_string()))
    );
    assert_eq!(
        person_day_message(&arch, ada, "1999-01-01", false).unwrap(),
        None
    );
    assert_eq!(
        person_day_message(&arch, 0, "2020-05-02", true).unwrap(),
        None
    );
}
