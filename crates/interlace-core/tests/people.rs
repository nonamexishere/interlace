//! Person list + D18 timeline rows (UI3).

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::people::{person_list, person_timeline_rows};
use interlace_core::{person_merge, person_undo, PersonMergeOpts};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-ppl-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn plant(arch: &interlace_core::db::Archive) -> (i64, i64, i64) {
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
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('gmail', 'email', 'a@x.com', 'a@x.com', 'Ali')",
            [],
        )
        .unwrap();
    let ali_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ali', 0)",
            [],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![pid, ali_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-t', 'hello')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, ali_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:g', 'Project')",
            [],
        )
        .unwrap();
    let grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![grp, ali_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'dm hi', 'k-dm')",
            rusqlite::params![dm, src, run, ali_id],
        )
        .unwrap();
    let dm_msg = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Other', 'other', 'Other')",
            [],
        )
        .unwrap();
    let other = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![grp, other],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, '2024-03-16T10:00:00Z', 'second', 'text', 'group hi', 'k-g')",
            rusqlite::params![grp, src, run, other],
        )
        .unwrap();
    (pid, dm_msg, arch.conn.last_insert_rowid())
}

#[test]
fn list_live_persons_only() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let (pid, _, _) = plant(&arch);
    let list = person_list(&arch).unwrap();
    assert!(list.iter().any(|p| p.id == pid && p.display_name == "Ali"));
    assert!(list.iter().all(|p| !p.display_name.is_empty()));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn timeline_hides_groups_by_default() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let (pid, dm_msg, grp_msg) = plant(&arch);
    let rows = person_timeline_rows(&arch, pid, false, 50, None).unwrap();
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    assert!(ids.contains(&dm_msg), "{ids:?}");
    assert!(!ids.contains(&grp_msg), "group leaked: {ids:?}");
    assert_eq!(rows[0].platform, "gmail");
    assert_eq!(rows[0].body_text, "dm hi");
    let with_g = person_timeline_rows(&arch, pid, true, 50, None).unwrap();
    assert!(with_g.iter().any(|r| r.message_id == grp_msg));
    arch
        .conn
        .execute(
            "INSERT INTO attachments(message_id, filename, kind, omitted, missing)
             VALUES (?1, 'pic.jpg', 'image', 1, 0)",
            [dm_msg],
        )
        .unwrap();
    let with_a = person_timeline_rows(&arch, pid, false, 50, None).unwrap();
    let dm = with_a.iter().find(|r| r.message_id == dm_msg).unwrap();
    assert_eq!(dm.attachments.len(), 1);
    assert!(dm.attachments[0].omitted);
    assert_eq!(dm.attachments[0].filename.as_deref(), Some("pic.jpg"));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn merge_undo_leaves_sender_identity_id() {
    let root = tmp();
    let mut arch = init_archive(&root.join("a")).unwrap();
    let (pid, dm_msg, _) = plant(&arch);
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized)
             VALUES ('gmail', 'email', 'b@x.com', 'b@x.com')",
            [],
        )
        .unwrap();
    let iid2 = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ali2', 0)",
            [],
        )
        .unwrap();
    let pid2 = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![pid2, iid2],
        )
        .unwrap();
    let before: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id=?1",
            [dm_msg],
            |r| r.get(0),
        )
        .unwrap();
    person_merge(&mut arch, pid, pid2, PersonMergeOpts { keep: None }).unwrap();
    let ev: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM identity_link_events WHERE op='merge_persons' ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    person_undo(&mut arch, ev).unwrap();
    let after: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id=?1",
            [dm_msg],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(before, after);
    let _ = std::fs::remove_dir_all(&root);
}
