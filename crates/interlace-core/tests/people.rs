//! Person list + D18 timeline rows (UI3). Last-activity sort + preview (#110).

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::people::{person_list, person_timeline_rows};
use interlace_core::{person_merge, person_timeline, person_undo, PersonMergeOpts};

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

/// Ada is the sender in a DM and a `kind=group` chat (D18 sender-branch hole).
fn plant_ada_sender(arch: &interlace_core::db::Archive) -> (i64, i64, i64) {
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
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Ada', 'ada', 'Ada')",
            [],
        )
        .unwrap();
    let ada_iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let ada_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![ada_id, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:ada', 'Ada')",
            [],
        )
        .unwrap();
    let dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![dm, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:g-ada', 'Project')",
            [],
        )
        .unwrap();
    let grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![grp, ada_iid],
        )
        .unwrap();
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
             VALUES (?1, ?2, ?3, ?4, '2024-03-15T14:32:00Z', 'second', 'text', 'ada dm', 'k-ada-dm')",
            rusqlite::params![dm, src, run, ada_iid],
        )
        .unwrap();
    let dm_msg = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, '2024-03-16T10:00:00Z', 'second', 'text', 'ada group', 'k-ada-g')",
            rusqlite::params![grp, src, run, ada_iid],
        )
        .unwrap();
    (ada_id, dm_msg, arch.conn.last_insert_rowid())
}

/// Self + Ada (newer DM) + Ali (older DM + newer group-only) + Cemre (no messages).
struct ActivityPlant {
    ada_id: i64,
    ali_id: i64,
    cemre_id: i64,
}

const ADA_LATEST_AT: &str = "2024-03-20T10:00:00Z";
const ADA_LATEST_BODY: &str = "Ada latest note";
const ADA_LATEST_HTML: &str = "<p>Ada latest note</p>";
const ALI_DM_AT: &str = "2024-03-15T14:32:00Z";
const ALI_GROUP_AT: &str = "2024-03-25T10:00:00Z";

fn plant_activity(arch: &interlace_core::db::Archive) -> ActivityPlant {
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
            "INSERT INTO persons(display_name, is_self) VALUES ('Me', 1)",
            [],
        )
        .unwrap();

    let person = |arch: &interlace_core::db::Archive,
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

    let (ada_id, ada_iid) = person(arch, "Ada", "whatsapp", "display_name", "Ada", "ada");
    let (ali_id, ali_iid) = person(arch, "Ali", "gmail", "email", "a@x.com", "a@x.com");
    let (cemre_id, _) = person(arch, "Cemre", "contacts", "email", "c@x.com", "c@x.com");

    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:ada', 'Ada')",
            [],
        )
        .unwrap();
    let ada_dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_dm, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-ali', 'hello')",
            [],
        )
        .unwrap();
    let ali_dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ali_dm, ali_iid],
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
            rusqlite::params![grp, ali_iid],
        )
        .unwrap();
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
             VALUES (?1, ?2, ?3, ?4, '2024-01-01T09:00:00Z', 'second', 'text', 'Ada old note', 'k-ada-old')",
            rusqlite::params![ada_dm, src, run, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, body_html, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7, 'k-ada-new')",
            rusqlite::params![
                ada_dm,
                src,
                run,
                ada_iid,
                ADA_LATEST_AT,
                ADA_LATEST_BODY,
                ADA_LATEST_HTML
            ],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', 'ali dm hi', 'k-ali-dm')",
            rusqlite::params![ali_dm, src, run, ali_iid, ALI_DM_AT],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', 'ali group hi', 'k-ali-g')",
            rusqlite::params![grp, src, run, other, ALI_GROUP_AT],
        )
        .unwrap();

    ActivityPlant {
        ada_id,
        ali_id,
        cemre_id,
    }
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
    arch.conn
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

    arch.conn
        .execute(
            "UPDATE messages SET body_text = 'hi <attached: orphan-photo.jpg>' WHERE id = ?1",
            [dm_msg],
        )
        .unwrap();
    let with_tok = person_timeline_rows(&arch, pid, false, 50, None).unwrap();
    let dm2 = with_tok.iter().find(|r| r.message_id == dm_msg).unwrap();
    assert!(
        dm2.attachments
            .iter()
            .any(|a| a.filename.as_deref() == Some("orphan-photo.jpg") && a.missing),
        "{:?}",
        dm2.attachments
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn timeline_hides_ada_group_sends_by_default() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let (ada, dm_msg, grp_msg) = plant_ada_sender(&arch);
    let rows = person_timeline_rows(&arch, ada, false, 50, None).unwrap();
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    assert!(ids.contains(&dm_msg), "{ids:?}");
    assert!(!ids.contains(&grp_msg), "Ada group send leaked: {ids:?}");
    assert!(
        rows.iter().all(|r| r.conversation_kind != "group"),
        "group-kind row leaked: {ids:?}"
    );
    let with_g = person_timeline_rows(&arch, ada, true, 50, None).unwrap();
    assert!(
        with_g.iter().any(|r| r.message_id == grp_msg),
        "include_groups=true must return Ada's group send, got {:?}",
        with_g.iter().map(|r| r.message_id).collect::<Vec<_>>()
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn cli_person_timeline_hides_ada_group_sends_by_default() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let (ada, dm_msg, grp_msg) = plant_ada_sender(&arch);
    let tl = person_timeline(&arch, ada, false, 50).unwrap();
    let ids: Vec<i64> = tl.iter().map(|h| h.message_id).collect();
    assert!(ids.contains(&dm_msg), "{ids:?}");
    assert!(!ids.contains(&grp_msg), "Ada group send leaked: {ids:?}");
    let tl_g = person_timeline(&arch, ada, true, 50).unwrap();
    assert!(
        tl_g.iter().any(|h| h.message_id == grp_msg),
        "include_groups=true must return Ada's group send, got {:?}",
        tl_g.iter().map(|h| h.message_id).collect::<Vec<_>>()
    );
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

#[test]
fn list_pins_self_then_newer_activity_then_null() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_activity(&arch);
    let list = person_list(&arch).unwrap();
    assert_eq!(
        list.len(),
        4,
        "{:?}",
        list.iter().map(|p| &p.display_name).collect::<Vec<_>>()
    );
    assert!(list[0].is_self, "{:?}", list[0].display_name);
    assert!(list.iter().skip(1).all(|p| !p.is_self));
    assert_eq!(list[1].id, planted.ada_id);
    assert_eq!(list[1].display_name, "Ada");
    assert_eq!(list[2].id, planted.ali_id);
    assert_eq!(list[2].display_name, "Ali");
    assert_eq!(list[3].id, planted.cemre_id);
    assert_eq!(list[3].display_name, "Cemre");
    assert_eq!(list[1].last_activity_at.as_deref(), Some(ADA_LATEST_AT));
    assert_eq!(list[2].last_activity_at.as_deref(), Some(ALI_DM_AT));
    assert_eq!(list[3].last_activity_at, None);
    assert_eq!(list[0].last_activity_at, None);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn list_preview_is_plain_prefix_of_latest_body() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_activity(&arch);
    let list = person_list(&arch).unwrap();
    let ada = list.iter().find(|p| p.id == planted.ada_id).unwrap();
    let preview = ada.preview.as_deref().expect("Ada preview");
    assert!(
        !preview.is_empty() && ADA_LATEST_BODY.starts_with(preview),
        "preview {preview:?} is not a prefix of {ADA_LATEST_BODY:?}"
    );
    assert!(
        !preview.contains('<') && !preview.contains('>'),
        "preview must be plain text, got {preview:?}"
    );
    assert_ne!(preview, ADA_LATEST_HTML);
    let cemre = list.iter().find(|p| p.id == planted.cemre_id).unwrap();
    assert_eq!(cemre.preview, None);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn list_group_only_activity_does_not_reorder_when_groups_off() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_activity(&arch);
    let list = person_list(&arch).unwrap();
    let names: Vec<&str> = list.iter().map(|p| p.display_name.as_str()).collect();
    let ada = list.iter().position(|p| p.id == planted.ada_id).unwrap();
    let ali = list.iter().position(|p| p.id == planted.ali_id).unwrap();
    assert!(
        ada < ali,
        "Ada must sort before Ali when Ali's newer row is group-only; got {names:?}"
    );
    assert_eq!(list[ali].last_activity_at.as_deref(), Some(ALI_DM_AT));
    assert_ne!(list[ali].last_activity_at.as_deref(), Some(ALI_GROUP_AT));
    let _ = std::fs::remove_dir_all(&root);
}
