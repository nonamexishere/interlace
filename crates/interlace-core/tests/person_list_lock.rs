//! #265: people list must not hold the sole archive connection for the
//! whole window-function scan. Exclusive flock stays. Status counts stay
//! honest. #138 identity haystack stays on the list.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//!
//! Expected public API (impl adds; re-export from `interlace_core`):
//!
//! ```ignore
//! pub fn person_list_on(
//!     conn: &rusqlite::Connection,
//! ) -> Result<Vec<PersonSummary>, CoreError>
//! ```
//!
//! Same contract as `person_list` (groups off): live persons only, self
//! first, last D18 activity, one-line preview, `identity_values`. Runs on a
//! caller-owned SQLite connection (second WAL snapshot) so the primary
//! `Archive` connection stays free. Do **not** flock; do **not** call
//! `open_archive` (that would take `INTERLACE.lock` again).
//!
//! Placeholders only: Ada / Cemre Yıldız / Ali; phone +905321234567;
//! email contact.ada@example.com.

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc;
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, open_archive, LockMode};
use interlace_core::people::{person_list, PersonSummary};
use interlace_core::{person_list_on, review_list, CoreError};

static SEQ: AtomicU64 = AtomicU64::new(0);

const CEMRE_NAME: &str = "Cemre Yıldız";
const CEMRE_PHONE: &str = "+905321234567";
const ADA_NAME: &str = "Ada";
const ADA_EMAIL: &str = "contact.ada@example.com";
const ALI_NAME: &str = "Ali";

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-ppl-lock-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn open_snapshot(root: &std::path::Path) -> rusqlite::Connection {
    let conn = rusqlite::Connection::open(root.join("archive.sqlite")).expect("snapshot conn");
    conn.pragma_update(None, "busy_timeout", 5_000i64)
        .expect("busy_timeout");
    conn
}

fn identity_material(p: &PersonSummary) -> String {
    let v = serde_json::to_value(p).expect("PersonSummary serializes");
    let mut out = String::new();
    if let Some(arr) = v.get("identity_values").and_then(|x| x.as_array()) {
        for item in arr {
            if let Some(s) = item.as_str() {
                out.push_str(s);
                out.push(' ');
            }
        }
    }
    if let Some(s) = v.get("filter_haystack").and_then(|x| x.as_str()) {
        out.push_str(s);
        out.push(' ');
    }
    if let Some(arr) = v.get("identities").and_then(|x| x.as_array()) {
        for item in arr {
            for key in ["value", "value_normalized", "display_name"] {
                if let Some(s) = item.get(key).and_then(|x| x.as_str()) {
                    out.push_str(s);
                    out.push(' ');
                }
            }
        }
    }
    out
}

/// Ali (live + 1 DM) + Ada (live, email) + Ghost (tombstoned) + one open review.
fn plant_status_roster(arch: &interlace_core::db::Archive) {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
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

    let link = |arch: &interlace_core::db::Archive,
                name: &str,
                platform: &str,
                kind: &str,
                raw: &str,
                norm: &str|
     -> (i64, i64) {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                rusqlite::params![platform, kind, raw, norm, name],
            )
            .unwrap();
        let iid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
                [name],
            )
            .unwrap();
        let pid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
                 VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
        (pid, iid)
    };

    let (ali_pid, ali_iid) = link(
        arch,
        ALI_NAME,
        "gmail",
        "email",
        "ali@example.com",
        "ali@example.com",
    );
    let (_ada_pid, _ada_iid) = link(arch, ADA_NAME, "gmail", "email", ADA_EMAIL, ADA_EMAIL);
    let (ghost_pid, _ghost_iid) = link(
        arch,
        "Ghost",
        "contacts",
        "email",
        "ghost@example.com",
        "ghost@example.com",
    );
    arch.conn
        .execute(
            "UPDATE persons SET tombstoned_at = '2024-03-01T00:00:00Z' WHERE id = ?1",
            [ghost_pid],
        )
        .unwrap();

    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-ali', 'hello')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, ali_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'ali hi', 'k-ali')",
            rusqlite::params![dm, src, run, ali_iid],
        )
        .unwrap();

    arch.conn
        .execute(
            "INSERT INTO merge_review_queue(
                status, left_identity_id, right_person_id, suggested_score, reason_summary
             ) VALUES ('open', ?1, ?2, 0.70, 'exact_name_fold')",
            rusqlite::params![ali_iid, ali_pid],
        )
        .unwrap();
}

/// Cemre (WA phone, name without digits) + Ada (email local part ≠ name).
fn plant_identity_roster(arch: &interlace_core::db::Archive) {
    let link = |arch: &interlace_core::db::Archive,
                name: &str,
                platform: &str,
                kind: &str,
                raw: &str,
                norm: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                rusqlite::params![platform, kind, raw, norm, name],
            )
            .unwrap();
        let iid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
                [name],
            )
            .unwrap();
        let pid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
                 VALUES (?1, ?2, 'auto_phone', 0.99, 'system')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
        pid
    };

    let _ = link(
        arch,
        CEMRE_NAME,
        "whatsapp",
        "phone",
        CEMRE_PHONE,
        CEMRE_PHONE,
    );
    let _ = link(arch, ADA_NAME, "gmail", "email", ADA_EMAIL, ADA_EMAIL);
}

fn assert_status_matches_sql(arch: &interlace_core::db::Archive, st: &serde_json::Value) {
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
        "status.messages must be SQL COUNT(*)"
    );
    assert_eq!(
        st["identities"], identities,
        "status.identities must be SQL COUNT(*)"
    );
    assert_eq!(
        st["persons_live"], persons_live,
        "status.persons_live must be SQL COUNT(*) of live persons (tombstoned_at IS NULL)"
    );
    assert_eq!(
        st["review_open"], review_open,
        "status.review_open must be SQL COUNT(*) of open review rows"
    );
}

fn assert_list_carries_identity(list: &[PersonSummary], phone: &str, email: &str) {
    let blob = list
        .iter()
        .map(|p| identity_material(p))
        .collect::<Vec<_>>()
        .join(" ");
    assert!(
        !blob.trim().is_empty(),
        "list payload must expose identity material \
         (identity_values / filter_haystack / identities); got {:?}",
        list.iter()
            .map(|p| serde_json::to_string(p).unwrap())
            .collect::<Vec<_>>()
    );
    assert!(
        blob.contains(phone) || blob.contains("532"),
        "identity material must include phone {phone} (or last-4 532); material={blob:?}"
    );
    let local = email.split('@').next().unwrap();
    assert!(
        blob.contains(email) || blob.contains(local),
        "identity material must include email {email} (or local part {local}); material={blob:?}"
    );
}

#[test]
fn exclusive_flock_stays() {
    let root = tmp();
    let arch_root = root.join("a");
    let arch = init_archive(&arch_root).expect("init");
    let _ = person_list(&arch).expect("person_list");
    assert!(
        arch_root.join("INTERLACE.lock").is_file(),
        "do not drop INTERLACE.lock"
    );
    match open_archive(&arch_root, LockMode::Exclusive) {
        Err(CoreError::Lock { .. }) => {}
        Err(other) => panic!("expected Lock, got {other:?}"),
        Ok(_) => panic!("second exclusive lock must fail"),
    }
    match open_archive(&arch_root, LockMode::Shared) {
        Err(CoreError::Lock { .. }) => {}
        Err(other) => panic!("expected Lock, got {other:?}"),
        Ok(_) => panic!("shared lock must fail while exclusive is held"),
    }
    assert!(
        arch_root.join("INTERLACE.lock").is_file(),
        "failed second open must not remove INTERLACE.lock"
    );
    drop(arch);
    open_archive(&arch_root, LockMode::Exclusive).expect("after drop, EX ok");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn status_counts_stay_honest_after_person_list() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    plant_status_roster(&arch);

    let expect_messages = count(&arch, "SELECT COUNT(*) FROM messages");
    let expect_identities = count(&arch, "SELECT COUNT(*) FROM identities");
    let expect_live = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    );
    let expect_review = count(
        &arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status = 'open'",
    );
    assert!(expect_live >= 2, "fixture: at least Ali + Ada live");
    assert_eq!(expect_review, 1, "fixture: one open review");
    assert!(expect_messages >= 1, "fixture: at least one message");
    assert!(
        expect_identities >= 3,
        "fixture: Ali + Ada + Ghost identities"
    );

    let list = person_list(&arch).unwrap();
    assert!(
        list.iter().any(|p| p.display_name == ALI_NAME),
        "person_list must still return live Ali"
    );
    assert!(
        list.iter().all(|p| p.display_name != "Ghost"),
        "person_list must not return the tombstoned person"
    );

    let st = arch.status().unwrap();
    assert_status_matches_sql(&arch, &st);
    assert_eq!(st["messages"], expect_messages);
    assert_eq!(st["identities"], expect_identities);
    assert_eq!(st["persons_live"], expect_live);
    assert_eq!(st["review_open"], expect_review);

    let snap = open_snapshot(&arch.root);
    let snap_list = person_list_on(&snap).unwrap();
    assert!(
        snap_list.iter().any(|p| p.display_name == ALI_NAME),
        "person_list_on must still return live Ali"
    );
    assert!(
        snap_list.iter().all(|p| p.display_name != "Ghost"),
        "person_list_on must not return the tombstoned person"
    );
    let st2 = arch.status().unwrap();
    assert_status_matches_sql(&arch, &st2);
    assert_eq!(st2["messages"], expect_messages);
    assert_eq!(st2["identities"], expect_identities);
    assert_eq!(st2["persons_live"], expect_live);
    assert_eq!(st2["review_open"], expect_review);

    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn person_list_still_carries_identity_values() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    plant_identity_roster(&arch);

    let list = person_list(&arch).unwrap();
    assert_list_carries_identity(&list, CEMRE_PHONE, ADA_EMAIL);

    let snap = open_snapshot(&arch.root);
    let snap_list = person_list_on(&snap).unwrap();
    assert_list_carries_identity(&snap_list, CEMRE_PHONE, ADA_EMAIL);

    let _ = std::fs::remove_dir_all(&root);
}

/// Handshake, not a wall-clock bound: the snapshot people query parks in a
/// progress handler until `status` / `review_list` finish on the primary
/// `Archive`. Today's `person_list(&Archive)` cannot do this (sole connection).
#[test]
fn status_and_review_complete_while_people_list_runs_on_snapshot_conn() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    plant_status_roster(&arch);

    let expect_messages = count(&arch, "SELECT COUNT(*) FROM messages");
    let expect_identities = count(&arch, "SELECT COUNT(*) FROM identities");
    let expect_live = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    );
    let expect_review = count(
        &arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status = 'open'",
    );

    let snap = open_snapshot(&arch.root);
    let entered = Arc::new(AtomicBool::new(false));
    let release = Arc::new(AtomicBool::new(false));
    {
        let entered = Arc::clone(&entered);
        let release = Arc::clone(&release);
        snap.progress_handler(
            1,
            Some(move || {
                entered.store(true, Ordering::SeqCst);
                let start = Instant::now();
                while !release.load(Ordering::SeqCst) && start.elapsed() < Duration::from_secs(5) {
                    thread::yield_now();
                    thread::sleep(Duration::from_millis(1));
                }
                false
            }),
        );
    }

    let people_done = Arc::new(AtomicBool::new(false));
    let people_done_a = Arc::clone(&people_done);
    let handle_a = thread::spawn(move || {
        let list = person_list_on(&snap);
        people_done_a.store(true, Ordering::SeqCst);
        list
    });

    let deadline = Instant::now() + Duration::from_secs(5);
    while !entered.load(Ordering::SeqCst) && Instant::now() < deadline {
        thread::yield_now();
        thread::sleep(Duration::from_millis(1));
    }
    assert!(
        entered.load(Ordering::SeqCst),
        "person_list_on must run the people query on the given snapshot connection \
         (progress_handler did not fire)"
    );
    assert!(
        !people_done.load(Ordering::SeqCst),
        "people scan must still be in flight when status/review_list run"
    );

    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        let st = arch
            .status()
            .expect("status while people list is in flight");
        let rev = review_list(&arch).expect("review_list while people list is in flight");
        let _ = tx.send((st, rev));
    });

    let (st, rev) = match rx.recv_timeout(Duration::from_secs(5)) {
        Ok(pair) => pair,
        Err(_) => {
            release.store(true, Ordering::SeqCst);
            let _ = handle_a.join();
            panic!(
                "status / review_list did not complete while person_list_on was in flight — \
                 people list must not hold the sole archive connection for the whole scan"
            );
        }
    };
    release.store(true, Ordering::SeqCst);

    assert_eq!(st["messages"], expect_messages);
    assert_eq!(st["identities"], expect_identities);
    assert_eq!(st["persons_live"], expect_live);
    assert_eq!(st["review_open"], expect_review);
    assert!(
        rev.len() as i64 == expect_review || !rev.is_empty() || expect_review == 0,
        "review_list must run (not block on people); got {} rows, expect_open={expect_review}",
        rev.len()
    );

    let list = handle_a
        .join()
        .expect("people thread")
        .expect("person_list_on");
    assert!(
        list.iter().any(|p| p.display_name == ALI_NAME),
        "snapshot person_list_on must still return live Ali"
    );

    let _ = std::fs::remove_dir_all(&root);
}
