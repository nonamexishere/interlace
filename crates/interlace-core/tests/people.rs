//! Person list + D18 timeline rows (UI3). Last-activity sort + preview (#110).

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::people::{
    person_list, person_media_rows_for, person_timeline_rows, person_timeline_rows_for,
    PersonSummary,
};
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

/// Stored CAS hash for gallery plants (64 hex; cas_blobs FK).
const GALLERY_CAS: &str = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";

struct GalleryPlant {
    ada_id: i64,
    berk_id: i64,
    ada_day1: i64,
    ada_day2: i64,
    ada_omit: i64,
    ada_missing: i64,
    ada_voice: i64,
    ada_group: i64,
    ada_inline_img: i64,
    ada_inline_other: i64,
    ada_from_me: i64,
    berk_img: i64,
}

/// Ada + Berk gallery plant. Placeholders only. Attachments table is the source
/// of truth (no `<attached:` token rows).
fn plant_ada_gallery(arch: &interlace_core::db::Archive) -> GalleryPlant {
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

    let ident = |arch: &interlace_core::db::Archive, name: &str, raw: &str, norm: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES ('whatsapp', 'display_name', ?1, ?2, ?3)",
                rusqlite::params![raw, norm, name],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let person = |arch: &interlace_core::db::Archive, name: &str, iid: i64, is_self: i64| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO persons(display_name, is_self) VALUES (?1, ?2)",
                rusqlite::params![name, is_self],
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
        pid
    };

    let ada_iid = ident(arch, "Ada", "Ada", "ada");
    let ada_id = person(arch, "Ada", ada_iid, 0);
    let me_iid = ident(arch, "Me", "Me", "me");
    let _me_id = person(arch, "Me", me_iid, 1);
    let berk_iid = ident(arch, "Berk", "Berk", "berk");
    let berk_id = person(arch, "Berk", berk_iid, 0);
    let other_iid = ident(arch, "Other", "Other", "other");

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
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_dm, me_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:g-ada', 'Project')",
            [],
        )
        .unwrap();
    let ada_grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_grp, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_grp, other_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![berk_dm, berk_iid],
        )
        .unwrap();

    arch.conn
        .execute(
            "INSERT INTO cas_blobs(hash, size) VALUES (?1, 4)",
            [GALLERY_CAS],
        )
        .unwrap();

    let msg = |arch: &interlace_core::db::Archive,
               conv: i64,
               sender: i64,
               sent_at: &str,
               key: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key)
                 VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', '', ?6)",
                rusqlite::params![conv, src, run, sender, sent_at, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let stored = |arch: &interlace_core::db::Archive,
                  mid: i64,
                  filename: &str,
                  mime: Option<&str>,
                  kind: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
                 VALUES (?1, ?2, ?3, ?4, ?5, 0, 0)",
                rusqlite::params![mid, GALLERY_CAS, filename, mime, kind],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };

    // Two stored DM images on different days (newest = day2).
    let day1_msg = msg(arch, ada_dm, ada_iid, "2024-03-10T10:00:00Z", "k-ada-d1");
    let ada_day1 = stored(arch, day1_msg, "ada-day1.jpg", Some("image/jpeg"), "image");
    let day2_msg = msg(arch, ada_dm, ada_iid, "2024-03-11T10:00:00Z", "k-ada-d2");
    let ada_day2 = stored(arch, day2_msg, "ada-day2.jpg", Some("image/jpeg"), "image");

    // Omitted image, missing / no-hash image, voice (hash set — still out).
    let omit_msg = msg(arch, ada_dm, ada_iid, "2024-03-09T10:00:00Z", "k-ada-omit");
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, kind, omitted, missing)
             VALUES (?1, 'ada-omit.jpg', 'image', 1, 0)",
            [omit_msg],
        )
        .unwrap();
    let ada_omit = arch.conn.last_insert_rowid();
    let miss_msg = msg(arch, ada_dm, ada_iid, "2024-03-09T11:00:00Z", "k-ada-miss");
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, kind, omitted, missing)
             VALUES (?1, 'ada-missing.jpg', 'image', 0, 1)",
            [miss_msg],
        )
        .unwrap();
    let ada_missing = arch.conn.last_insert_rowid();
    // Body token is not a source of truth (timeline may synthesize a missing row).
    arch.conn
        .execute(
            "UPDATE messages SET body_text = 'hi <attached: orphan-photo.jpg>' WHERE id = ?1",
            [miss_msg],
        )
        .unwrap();
    let voice_msg = msg(arch, ada_dm, ada_iid, "2024-03-09T12:00:00Z", "k-ada-voice");
    let ada_voice = stored(
        arch,
        voice_msg,
        "ada-voice.opus",
        Some("audio/ogg"),
        "voice",
    );

    // Stored group image (only when include_groups).
    let grp_msg = msg(arch, ada_grp, ada_iid, "2024-03-16T10:00:00Z", "k-ada-grp");
    let ada_group = stored(arch, grp_msg, "ada-group.jpg", Some("image/jpeg"), "image");

    // kind=inline image/* in; non-image inline out.
    let inline_img_msg = msg(arch, ada_dm, ada_iid, "2024-03-12T10:00:00Z", "k-ada-inl");
    let ada_inline_img = stored(
        arch,
        inline_img_msg,
        "ada-inline.jpg",
        Some("image/jpeg"),
        "inline",
    );
    let inline_other_msg = msg(arch, ada_dm, ada_iid, "2024-03-12T11:00:00Z", "k-ada-pdf");
    let ada_inline_other = stored(
        arch,
        inline_other_msg,
        "ada-inline.pdf",
        Some("application/pdf"),
        "inline",
    );

    // from_me stored image on the DM (whole membership — sender or participant).
    let from_me_msg = msg(arch, ada_dm, me_iid, "2024-03-13T10:00:00Z", "k-ada-me");
    let ada_from_me = stored(
        arch,
        from_me_msg,
        "ada-from-me.jpg",
        Some("image/jpeg"),
        "image",
    );

    // Berk's stored image must not appear in Ada's query.
    let berk_msg = msg(
        arch,
        berk_dm,
        berk_iid,
        "2024-03-14T10:00:00Z",
        "k-berk-img",
    );
    let berk_img = stored(arch, berk_msg, "berk.jpg", Some("image/jpeg"), "image");

    GalleryPlant {
        ada_id,
        berk_id,
        ada_day1,
        ada_day2,
        ada_omit,
        ada_missing,
        ada_voice,
        ada_group,
        ada_inline_img,
        ada_inline_other,
        ada_from_me,
        berk_img,
    }
}

/// gallery-core-ada-two: Ada include_groups=false has the two stored DM images
/// (plus from_me + inline image/*). Newest first. len >= 2.
#[test]
fn gallery_core_ada_two() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gallery(&arch);
    let rows = person_media_rows_for(&arch, p.ada_id, false, 50, None).unwrap();
    let ids: Vec<i64> = rows.iter().map(|r| r.attachment_id).collect();
    assert!(
        rows.len() >= 2,
        "Ada include_groups=false must return at least the two stored DM images, got {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_day1),
        "day1 stored DM image missing: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_day2),
        "day2 stored DM image missing: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_from_me),
        "from_me stored DM image must be in Ada's list (whole membership): {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_inline_img),
        "kind=inline mime=image/jpeg must be included: {ids:?}"
    );
    let pos1 = ids.iter().position(|id| *id == p.ada_day1).unwrap();
    let pos2 = ids.iter().position(|id| *id == p.ada_day2).unwrap();
    assert!(
        pos2 < pos1,
        "newest first (sent_at DESC): day2 before day1, got {ids:?}"
    );
    for w in rows.windows(2) {
        let a = w[0].sent_at.as_deref().unwrap_or("");
        let b = w[1].sent_at.as_deref().unwrap_or("");
        assert!(
            a >= b,
            "newest first (sent_at DESC): {a} then {b} (ids {:?})",
            ids
        );
    }
    let _ = std::fs::remove_dir_all(&root);
}

/// gallery-core-omit: omitted + missing + voice + no-hash + non-image inline
/// stay out. No broken-thumb rows. Body `<attached:` tokens are not a source.
#[test]
fn gallery_core_omit() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gallery(&arch);
    let rows = person_media_rows_for(&arch, p.ada_id, false, 50, None).unwrap();
    let ids: Vec<i64> = rows.iter().map(|r| r.attachment_id).collect();
    assert!(!ids.contains(&p.ada_omit), "omitted image leaked: {ids:?}");
    assert!(
        !ids.contains(&p.ada_missing),
        "missing / no-hash image leaked: {ids:?}"
    );
    assert!(!ids.contains(&p.ada_voice), "voice leaked: {ids:?}");
    assert!(
        !ids.contains(&p.ada_inline_other),
        "non-image inline leaked: {ids:?}"
    );
    for r in &rows {
        let k = r.kind.as_str();
        let mime = r.mime.as_deref().unwrap_or("");
        let ok = matches!(k, "image" | "video" | "sticker")
            || (k == "inline" && (mime.starts_with("image/") || mime.starts_with("video/")));
        assert!(ok, "unexpected kind/mime in gallery: {k} {mime}");
    }
    let _ = std::fs::remove_dir_all(&root);
}

/// gallery-core-groups: group image absent when include_groups=false, present when true.
#[test]
fn gallery_core_groups() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gallery(&arch);
    let off = person_media_rows_for(&arch, p.ada_id, false, 50, None).unwrap();
    let off_ids: Vec<i64> = off.iter().map(|r| r.attachment_id).collect();
    assert!(
        !off_ids.contains(&p.ada_group),
        "group image leaked with include_groups=false: {off_ids:?}"
    );
    let on = person_media_rows_for(&arch, p.ada_id, true, 50, None).unwrap();
    let on_ids: Vec<i64> = on.iter().map(|r| r.attachment_id).collect();
    assert!(
        on_ids.contains(&p.ada_group),
        "group image missing with include_groups=true: {on_ids:?}"
    );
    let grp = on.iter().find(|r| r.attachment_id == p.ada_group).unwrap();
    assert_eq!(grp.conversation_kind, "group");
    let _ = std::fs::remove_dir_all(&root);
}

/// gallery-core-berk: Berk's query does not return Ada's attachment ids; Ada's
/// query does not return Berk's.
#[test]
fn gallery_core_berk() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gallery(&arch);
    let ada = person_media_rows_for(&arch, p.ada_id, true, 50, None).unwrap();
    let ada_ids: Vec<i64> = ada.iter().map(|r| r.attachment_id).collect();
    let berk = person_media_rows_for(&arch, p.berk_id, true, 50, None).unwrap();
    let berk_ids: Vec<i64> = berk.iter().map(|r| r.attachment_id).collect();
    assert!(
        !ada_ids.contains(&p.berk_img),
        "Berk's attachment leaked into Ada's gallery: {ada_ids:?}"
    );
    let ada_own = [
        p.ada_day1,
        p.ada_day2,
        p.ada_group,
        p.ada_inline_img,
        p.ada_from_me,
    ];
    for id in ada_own {
        assert!(
            !berk_ids.contains(&id),
            "Ada attachment {id} leaked into Berk's gallery: {berk_ids:?}"
        );
    }
    assert!(
        berk_ids.contains(&p.berk_img),
        "Berk's stored image missing from Berk's gallery: {berk_ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Stored CAS hash for #362 timeline attach-kind plants (64 hex; cas_blobs FK).
const MEDIA_KIND_CAS: &str = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";

struct MediaKindPlant {
    ada_id: i64,
    berk_id: i64,
    ada_image: i64,
    ada_voice: i64,
    ada_video: i64,
    ada_file_pdf: i64,
    ada_file_null_mime: i64,
    ada_file_empty_mime: i64,
    ada_sticker: i64,
    ada_omit_voice: i64,
    ada_inline_img: i64,
    ada_file_image: i64,
    ada_file_audio: i64,
    ada_inline_audio: i64,
    ada_photo_voice: i64,
    ada_group_voice: i64,
    ada_text: i64,
    ada_body_token: i64,
    berk_voice: i64,
}

/// Ada + Berk attach-kind plant. Placeholders only. Attachments table is the
/// source of truth (body `<attached:` tokens must not mint a Voice/Photos row).
fn plant_ada_media_kind(arch: &interlace_core::db::Archive) -> MediaKindPlant {
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

    let ident = |arch: &interlace_core::db::Archive, name: &str, raw: &str, norm: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES ('whatsapp', 'display_name', ?1, ?2, ?3)",
                rusqlite::params![raw, norm, name],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let person = |arch: &interlace_core::db::Archive, name: &str, iid: i64| -> i64 {
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
        pid
    };

    let ada_iid = ident(arch, "Ada", "Ada", "ada");
    let ada_id = person(arch, "Ada", ada_iid);
    let berk_iid = ident(arch, "Berk", "Berk", "berk");
    let berk_id = person(arch, "Berk", berk_iid);
    let other_iid = ident(arch, "Other", "Other", "other");

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
             VALUES ('whatsapp', 'group', 'whatsapp:g-ada', 'Project')",
            [],
        )
        .unwrap();
    let ada_grp = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_grp, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_grp, other_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![berk_dm, berk_iid],
        )
        .unwrap();

    arch.conn
        .execute(
            "INSERT INTO cas_blobs(hash, size) VALUES (?1, 4)",
            [MEDIA_KIND_CAS],
        )
        .unwrap();

    let msg = |arch: &interlace_core::db::Archive,
               conv: i64,
               sender: i64,
               sent_at: &str,
               key: &str,
               body: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key)
                 VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7)",
                rusqlite::params![conv, src, run, sender, sent_at, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let stored = |arch: &interlace_core::db::Archive,
                  mid: i64,
                  filename: &str,
                  mime: Option<&str>,
                  kind: &str| {
        arch.conn
            .execute(
                "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
                 VALUES (?1, ?2, ?3, ?4, ?5, 0, 0)",
                rusqlite::params![mid, MEDIA_KIND_CAS, filename, mime, kind],
            )
            .unwrap();
    };

    let ada_text = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-01T10:00:00Z",
        "k-ada-text",
        "ada text",
    );
    let ada_image = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-02T10:00:00Z",
        "k-ada-img",
        "",
    );
    stored(arch, ada_image, "ada.jpg", Some("image/jpeg"), "image");
    let ada_voice = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-03T10:00:00Z",
        "k-ada-voice",
        "",
    );
    stored(
        arch,
        ada_voice,
        "ada-voice.opus",
        Some("audio/ogg"),
        "voice",
    );
    let ada_video = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-04T10:00:00Z",
        "k-ada-vid",
        "",
    );
    stored(arch, ada_video, "ada.mp4", Some("video/mp4"), "video");
    let ada_file_pdf = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-05T10:00:00Z",
        "k-ada-pdf",
        "",
    );
    stored(
        arch,
        ada_file_pdf,
        "ada.pdf",
        Some("application/pdf"),
        "file",
    );
    let ada_sticker = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-06T10:00:00Z",
        "k-ada-stk",
        "",
    );
    stored(arch, ada_sticker, "ada.webp", Some("image/webp"), "sticker");
    let ada_omit_voice = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-07T10:00:00Z",
        "k-ada-omit-voice",
        "",
    );
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, mime, kind, omitted, missing)
             VALUES (?1, 'ada-omit.opus', 'audio/ogg', 'voice', 1, 0)",
            [ada_omit_voice],
        )
        .unwrap();
    let ada_inline_img = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-08T10:00:00Z",
        "k-ada-inl-img",
        "",
    );
    stored(
        arch,
        ada_inline_img,
        "ada-cid.jpg",
        Some("image/jpeg"),
        "inline",
    );
    let ada_file_image = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-09T10:00:00Z",
        "k-ada-file-img",
        "",
    );
    stored(
        arch,
        ada_file_image,
        "ada-file.jpg",
        Some("image/jpeg"),
        "file",
    );
    let ada_file_audio = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-10T10:00:00Z",
        "k-ada-file-aud",
        "",
    );
    stored(
        arch,
        ada_file_audio,
        "ada-file.ogg",
        Some("audio/ogg"),
        "file",
    );
    let ada_inline_audio = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-11T10:00:00Z",
        "k-ada-inl-aud",
        "",
    );
    stored(
        arch,
        ada_inline_audio,
        "ada-cid.ogg",
        Some("audio/ogg"),
        "inline",
    );
    let ada_photo_voice = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-12T10:00:00Z",
        "k-ada-photo-voice",
        "",
    );
    stored(
        arch,
        ada_photo_voice,
        "ada-both.jpg",
        Some("image/jpeg"),
        "image",
    );
    stored(
        arch,
        ada_photo_voice,
        "ada-both.opus",
        Some("audio/ogg"),
        "voice",
    );
    let ada_body_token = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-13T10:00:00Z",
        "k-ada-tok",
        "hi <attached: orphan-voice.opus>",
    );
    let ada_group_voice = msg(
        arch,
        ada_grp,
        ada_iid,
        "2024-03-16T10:00:00Z",
        "k-ada-grp-voice",
        "",
    );
    stored(
        arch,
        ada_group_voice,
        "ada-group.opus",
        Some("audio/ogg"),
        "voice",
    );
    let berk_voice = msg(
        arch,
        berk_dm,
        berk_iid,
        "2024-03-14T10:00:00Z",
        "k-berk-voice",
        "",
    );
    stored(arch, berk_voice, "berk.opus", Some("audio/ogg"), "voice");
    // WhatsApp PDF / omitted-file shape (kind=file, mime NULL/empty) that Files must keep.
    let ada_file_null_mime = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-15T10:00:00Z",
        "k-ada-file-null",
        "",
    );
    stored(arch, ada_file_null_mime, "ada-null.pdf", None, "file");
    let ada_file_empty_mime = msg(
        arch,
        ada_dm,
        ada_iid,
        "2024-03-17T10:00:00Z",
        "k-ada-file-empty",
        "",
    );
    stored(arch, ada_file_empty_mime, "ada-empty.pdf", Some(""), "file");

    MediaKindPlant {
        ada_id,
        berk_id,
        ada_image,
        ada_voice,
        ada_video,
        ada_file_pdf,
        ada_file_null_mime,
        ada_file_empty_mime,
        ada_sticker,
        ada_omit_voice,
        ada_inline_img,
        ada_file_image,
        ada_file_audio,
        ada_inline_audio,
        ada_photo_voice,
        ada_group_voice,
        ada_text,
        ada_body_token,
        berk_voice,
    }
}

fn media_kind_ids(rows: &[interlace_core::people::TimelineRow]) -> Vec<i64> {
    rows.iter().map(|r| r.message_id).collect()
}

/// media-kind-core-voice: Voice → kind=voice + file/inline audio/* (omitted
/// still matches). Not the photo-only row. Photo+voice EXISTS-any. Table only.
#[test]
fn media_kind_core_voice() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let rows = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("voice"))
        .expect("Voice must be Ok");
    let ids = media_kind_ids(&rows);
    assert!(
        ids.contains(&p.ada_voice),
        "stored kind=voice missing: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_omit_voice),
        "omitted voice must still match Voice (no cas_hash / omitted=0 requirement): {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_file_audio),
        "kind=file mime=audio/* must match Voice: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_inline_audio),
        "kind=inline mime=audio/* must match Voice: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_photo_voice),
        "photo+voice message must appear under Voice (EXISTS any): {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_image),
        "photo-only row leaked into Voice: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_sticker),
        "sticker leaked into Voice: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_inline_img),
        "inline image leaked into Voice: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_file_image),
        "file+image/* leaked into Voice: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_text),
        "text-only row leaked into Voice: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_body_token),
        "body-token synthetic must not match Voice (attachments table only): {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_group_voice),
        "group voice leaked with include_groups=false: {ids:?}"
    );
    assert!(
        !ids.contains(&p.berk_voice),
        "Berk's voice leaked into Ada Voice: {ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-photos-not-voice: Photos → image/sticker/inline|file image/*.
/// Not voice-only. Photo+voice in. file+image/* is Photos, not Files.
#[test]
fn media_kind_core_photos_not_voice() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let rows = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("photos"))
        .expect("Photos must be Ok");
    let ids = media_kind_ids(&rows);
    assert!(
        ids.contains(&p.ada_image),
        "kind=image missing from Photos: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_sticker),
        "kind=sticker must be Photos: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_inline_img),
        "kind=inline mime=image/* must be Photos: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_file_image),
        "kind=file mime=image/* must be Photos (not Files): {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_photo_voice),
        "photo+voice message must appear under Photos (EXISTS any): {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_voice),
        "voice-only row leaked into Photos: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_omit_voice),
        "omitted voice leaked into Photos: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_file_audio),
        "file+audio/* leaked into Photos: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_file_pdf),
        "file+pdf leaked into Photos: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_text),
        "text-only row leaked into Photos: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_body_token),
        "body-token synthetic must not match Photos (attachments table only): {ids:?}"
    );

    let files = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("files"))
        .expect("Files must be Ok");
    let file_ids = media_kind_ids(&files);
    assert!(
        file_ids.contains(&p.ada_file_pdf),
        "file+pdf must be Files: {file_ids:?}"
    );
    assert!(
        !file_ids.contains(&p.ada_file_image),
        "file+image/* is Photos, not Files: {file_ids:?}"
    );
    assert!(
        !file_ids.contains(&p.ada_file_audio),
        "file+audio/* is Voice, not Files: {file_ids:?}"
    );
    assert!(
        !file_ids.contains(&p.ada_image),
        "kind=image leaked into Files: {file_ids:?}"
    );
    assert!(
        !file_ids.contains(&p.ada_voice),
        "kind=voice leaked into Files: {file_ids:?}"
    );
    assert!(
        !file_ids.contains(&p.ada_video),
        "kind=video leaked into Files: {file_ids:?}"
    );

    let video = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("video"))
        .expect("Video must be Ok");
    let video_ids = media_kind_ids(&video);
    assert!(
        video_ids.contains(&p.ada_video),
        "kind=video missing from Video: {video_ids:?}"
    );
    assert!(
        !video_ids.contains(&p.ada_image),
        "photo-only row leaked into Video: {video_ids:?}"
    );
    assert!(
        !video_ids.contains(&p.ada_voice),
        "voice-only row leaked into Video: {video_ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-all: All / None → merged stream includes photo + voice + text.
#[test]
fn media_kind_core_all() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let rows = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, None)
        .expect("All (omit attach-kind) must be Ok");
    let ids = media_kind_ids(&rows);
    assert!(
        ids.contains(&p.ada_image),
        "All must keep the photo row: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_voice),
        "All must keep the voice row: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_text),
        "All must keep the text-only row: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_video),
        "All must keep the video row: {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_file_pdf),
        "All must keep the file/pdf row: {ids:?}"
    );
    assert!(
        !ids.contains(&p.ada_group_voice),
        "All still hides group rows when include_groups=false: {ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-empty: Ada with no video + Video → Ok([]), not Err.
#[test]
fn media_kind_core_empty() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let (ada, dm_msg, _) = plant_ada_sender(&arch);
    arch.conn
        .execute(
            "INSERT INTO attachments(message_id, filename, mime, kind, omitted, missing)
             VALUES (?1, 'ada.jpg', 'image/jpeg', 'image', 0, 0)",
            [dm_msg],
        )
        .unwrap();
    let rows = person_timeline_rows_for(&arch, ada, false, 50, None, None, Some("video"))
        .expect("Video on Ada with no video must be Ok, not Err");
    assert!(
        rows.is_empty(),
        "Ada with no video + Video must be empty, got {:?}",
        media_kind_ids(&rows)
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-groups: group voice absent when include_groups=false,
/// present when true.
#[test]
fn media_kind_core_groups() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let off = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("voice"))
        .expect("Voice include_groups=false must be Ok");
    let off_ids = media_kind_ids(&off);
    assert!(
        !off_ids.contains(&p.ada_group_voice),
        "group voice leaked with include_groups=false: {off_ids:?}"
    );
    assert!(
        off_ids.contains(&p.ada_voice),
        "DM voice must remain when groups are off: {off_ids:?}"
    );
    let on = person_timeline_rows_for(&arch, p.ada_id, true, 50, None, None, Some("voice"))
        .expect("Voice include_groups=true must be Ok");
    let on_ids = media_kind_ids(&on);
    assert!(
        on_ids.contains(&p.ada_group_voice),
        "group voice missing with include_groups=true: {on_ids:?}"
    );
    let grp = on
        .iter()
        .find(|r| r.message_id == p.ada_group_voice)
        .unwrap();
    assert_eq!(grp.conversation_kind, "group");
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-berk: Berk Voice does not return Ada's voice message_id.
#[test]
fn media_kind_core_berk() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let ada = person_timeline_rows_for(&arch, p.ada_id, true, 50, None, None, Some("voice"))
        .expect("Ada Voice must be Ok");
    let ada_ids = media_kind_ids(&ada);
    let berk = person_timeline_rows_for(&arch, p.berk_id, true, 50, None, None, Some("voice"))
        .expect("Berk Voice must be Ok");
    let berk_ids = media_kind_ids(&berk);
    assert!(
        !berk_ids.contains(&p.ada_voice),
        "Ada's voice leaked into Berk Voice: {berk_ids:?}"
    );
    assert!(
        !berk_ids.contains(&p.ada_omit_voice),
        "Ada omitted voice leaked into Berk Voice: {berk_ids:?}"
    );
    assert!(
        !berk_ids.contains(&p.ada_photo_voice),
        "Ada photo+voice leaked into Berk Voice: {berk_ids:?}"
    );
    assert!(
        !ada_ids.contains(&p.berk_voice),
        "Berk's voice leaked into Ada Voice: {ada_ids:?}"
    );
    assert!(
        berk_ids.contains(&p.berk_voice),
        "Berk's voice missing from Berk Voice: {berk_ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// media-kind-core-files-null-mime: Files treats NULL/empty mime as not
/// image/video/audio (same as client isFilesAttach). kind=file + mime IS
/// NULL (WhatsApp PDF / omitted file) must return that message_id.
#[test]
fn media_kind_core_files_null_mime() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_media_kind(&arch);
    let files = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, Some("files"))
        .expect("Files must be Ok");
    let ids = media_kind_ids(&files);
    assert!(
        ids.contains(&p.ada_file_null_mime),
        "kind=file mime=NULL must match Files (WhatsApp PDF / omitted file): {ids:?}"
    );
    assert!(
        ids.contains(&p.ada_file_empty_mime),
        "kind=file mime='' must match Files: {ids:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Ada Gmail / email_thread + Berk WhatsApp label plant. Placeholders only.
/// Labels are SQL-planted (`labels` + `message_labels`); no persist/parse.
struct LabelsPlant {
    ada_id: i64,
    berk_id: i64,
    ada_labeled: i64,
    ada_unlabeled: i64,
    berk_wa: i64,
    berk_wa_labeled: i64,
}

fn plant_ada_gmail_labels(arch: &interlace_core::db::Archive) -> LabelsPlant {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 't', '/t.mbox')",
            [],
        )
        .unwrap();
    let gsrc = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [gsrc],
        )
        .unwrap();
    let grun = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_android_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let wsrc = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [wsrc],
        )
        .unwrap();
    let wrun = arch.conn.last_insert_rowid();

    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('gmail', 'email', 'ada@x.com', 'ada@x.com', 'Ada')",
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
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Berk', 'berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Berk', 0)",
            [],
        )
        .unwrap();
    let berk_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'auto_email', 0.99, 'system')",
            rusqlite::params![berk_id, berk_iid],
        )
        .unwrap();

    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-ada', 'Ada thread')",
            [],
        )
        .unwrap();
    let ada_th = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![ada_th, ada_iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'dm', 'whatsapp:berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_dm = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![berk_dm, berk_iid],
        )
        .unwrap();

    let mail = |arch: &interlace_core::db::Archive,
                sent_at: &str,
                key: &str,
                subject: &str,
                body: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, subject, body_text, idempotency_key)
                 VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'email', ?6, ?7, ?8)",
                rusqlite::params![ada_th, gsrc, grun, ada_iid, sent_at, subject, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let wa = |arch: &interlace_core::db::Archive, sent_at: &str, key: &str, body: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                    sent_at, sent_at_precision, kind, body_text, idempotency_key)
                 VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7)",
                rusqlite::params![berk_dm, wsrc, wrun, berk_iid, sent_at, body, key],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };

    let ada_labeled = mail(
        arch,
        "2024-03-10T10:00:00Z",
        "k-ada-mail-labeled",
        "Ada hello",
        "ada labeled",
    );
    let ada_unlabeled = mail(
        arch,
        "2024-03-11T10:00:00Z",
        "k-ada-mail-unlabeled",
        "Ada later",
        "ada unlabeled",
    );
    let berk_wa = wa(arch, "2024-03-12T10:00:00Z", "k-berk-wa", "berk hi");
    let berk_wa_labeled = wa(
        arch,
        "2024-03-13T10:00:00Z",
        "k-berk-wa-labeled",
        "berk labeled",
    );

    let lab = |arch: &interlace_core::db::Archive, name: &str| -> i64 {
        arch.conn
            .execute(
                "INSERT INTO labels(platform, name) VALUES ('gmail', ?1)",
                [name],
            )
            .unwrap();
        arch.conn.last_insert_rowid()
    };
    let link = |arch: &interlace_core::db::Archive, mid: i64, lid: i64| {
        arch.conn
            .execute(
                "INSERT INTO message_labels(message_id, label_id) VALUES (?1, ?2)",
                rusqlite::params![mid, lid],
            )
            .unwrap();
    };

    let inbox = lab(arch, "Inbox");
    let sent = lab(arch, "Sent");
    let family = lab(arch, "Family");
    link(arch, ada_labeled, inbox);
    link(arch, ada_labeled, sent);
    link(arch, ada_labeled, family);
    // Optional: a WhatsApp row that also has message_labels (table reuse).
    // Core may attach the name; the UI gate keeps WA chip-less.
    link(arch, berk_wa_labeled, family);

    LabelsPlant {
        ada_id,
        berk_id,
        ada_labeled,
        ada_unlabeled,
        berk_wa,
        berk_wa_labeled,
    }
}

fn labels_of(rows: &[interlace_core::people::TimelineRow], id: i64) -> Vec<String> {
    let row = rows
        .iter()
        .find(|r| r.message_id == id)
        .unwrap_or_else(|| panic!("missing timeline row {id}"));
    row.labels.clone()
}

/// tl-labels-core-mail: Ada gmail / email_thread with Inbox/Sent/Family on one
/// message_id → those names on that TimelineRow. Three message_labels is the
/// duplicate-union (all names visible). Sort is stable-as-attached — do not
/// lock Inbox/Sent-first.
#[test]
fn tl_labels_core_mail() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gmail_labels(&arch);
    let rows = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, None)
        .expect("Ada timeline must be Ok");
    let names = labels_of(&rows, p.ada_labeled);
    assert!(
        names.iter().any(|n| n == "Inbox"),
        "Inbox missing on Ada labeled mail: {names:?}"
    );
    assert!(
        names.iter().any(|n| n == "Sent"),
        "Sent missing on Ada labeled mail: {names:?}"
    );
    assert!(
        names.iter().any(|n| n == "Family"),
        "Family missing on Ada labeled mail: {names:?}"
    );
    assert_eq!(
        names.len(),
        3,
        "duplicate-union must keep all three names, got {names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// tl-labels-core-mail empty: Ada mail with no message_labels → empty labels
/// (not leftover names from the labeled Ada row in the same page).
#[test]
fn tl_labels_core_mail_empty() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gmail_labels(&arch);
    let rows = person_timeline_rows_for(&arch, p.ada_id, false, 50, None, None, None)
        .expect("Ada timeline must be Ok");
    let names = labels_of(&rows, p.ada_unlabeled);
    assert!(
        names.is_empty(),
        "Ada unlabeled mail must not inherit Inbox/Sent/Family: {names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// tl-labels-core-wa: Berk WhatsApp plant (no label rows) → empty labels.
/// A sibling WA row may have planted message_labels; that must not leak here.
#[test]
fn tl_labels_core_wa() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_ada_gmail_labels(&arch);
    let rows = person_timeline_rows_for(&arch, p.berk_id, false, 50, None, None, None)
        .expect("Berk timeline must be Ok");
    let names = labels_of(&rows, p.berk_wa);
    assert!(
        names.is_empty(),
        "Berk WhatsApp with no message_labels must be empty: {names:?}"
    );
    let _labeled = rows
        .iter()
        .find(|r| r.message_id == p.berk_wa_labeled)
        .expect("Berk WA row with planted message_labels must still load");
    // Core may attach Family on berk_wa_labeled (same family as attachments).
    // Do not fail if names appear on the DTO — the UI gate keeps WA chip-less.
    let _ = &_labeled.labels;
    let _ = std::fs::remove_dir_all(&root);
}

/// #366: `person_list` batch-attaches `contacts_raw.photo_cas_hash`.
/// SQL plant only (no import persist / no fake JID). Placeholders Ada / Berk.
/// which-photo: MIN(contacts_raw.id) among non-null hashes.

const ADA_PHOTO_WIN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const ADA_PHOTO_LOSE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

struct PhotoPlant {
    ada_id: i64,
    berk_id: i64,
    win_contact_id: i64,
    lose_contact_id: i64,
}

fn plant_linked_contact(
    arch: &interlace_core::db::Archive,
    source_id: i64,
    person_id: i64,
    uid: &str,
    email: &str,
    hash: Option<&str>,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('contacts', 'email', ?1, ?2, 'Ada')",
            rusqlite::params![email, email],
        )
        .unwrap();
    let iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'takeout_vcard', 1.0, 'system')",
            rusqlite::params![person_id, iid],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, fn, photo_cas_hash) VALUES (?1, ?2, 'Ada', ?3)",
            rusqlite::params![source_id, uid, hash],
        )
        .unwrap();
    let cid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO contact_channels(contact_id, kind, value_raw, value_normalized, pref, identity_id)
             VALUES (?1, 'email', ?2, ?3, 0, ?4)",
            rusqlite::params![cid, email, email, iid],
        )
        .unwrap();
    cid
}

fn plant_photo_ada_berk(arch: &interlace_core::db::Archive) -> PhotoPlant {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 't', '/t.vcf')",
            [],
        )
        .unwrap();
    let source_id = arch.conn.last_insert_rowid();

    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let ada_id = arch.conn.last_insert_rowid();
    // Lowest id is a linked card with a NULL hash — must not win which-photo.
    let _null_contact_id = plant_linked_contact(
        arch,
        source_id,
        ada_id,
        "ada-photo-null",
        "ada-photo-null@example.com",
        None,
    );
    let win_contact_id = plant_linked_contact(
        arch,
        source_id,
        ada_id,
        "ada-photo-win",
        "ada-photo-win@example.com",
        Some(ADA_PHOTO_WIN),
    );
    let lose_contact_id = plant_linked_contact(
        arch,
        source_id,
        ada_id,
        "ada-photo-lose",
        "ada-photo-lose@example.com",
        Some(ADA_PHOTO_LOSE),
    );

    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Berk', 'berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Berk', 0)",
            [],
        )
        .unwrap();
    let berk_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'system')",
            rusqlite::params![berk_id, berk_iid],
        )
        .unwrap();

    PhotoPlant {
        ada_id,
        berk_id,
        win_contact_id,
        lose_contact_id,
    }
}

fn photo_person<'a>(list: &'a [PersonSummary], id: i64, who: &str) -> &'a PersonSummary {
    list.iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("{who} (id={id}) missing from person_list"))
}

/// list-payload-photo-hash: planted Ada hash rides `person_list` (no CAS bytes).
#[test]
fn person_list_photo_hash_ada() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_photo_ada_berk(&arch);
    let list = person_list(&arch).expect("person_list must be Ok without CAS bytes on disk");
    let ada = photo_person(&list, p.ada_id, "Ada");
    assert_eq!(
        ada.photo_cas_hash.as_deref(),
        Some(ADA_PHOTO_WIN),
        "Ada must carry the planted 64-hex (not bytes / data:)"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// name-only-no-hash: Berk WhatsApp display_name, no contacts_raw → None.
#[test]
fn person_list_photo_hash_berk_name_only() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_photo_ada_berk(&arch);
    let list = person_list(&arch).expect("person_list must be Ok without CAS bytes on disk");
    let berk = photo_person(&list, p.berk_id, "Berk");
    assert_eq!(
        berk.photo_cas_hash, None,
        "Berk name-only WA must not inherit Ada's photo_cas_hash"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// which-photo: MIN(contacts_raw.id) among non-null hashes (NULL row does not win).
#[test]
fn person_list_photo_hash_min_id_wins() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant_photo_ada_berk(&arch);
    assert!(
        p.win_contact_id < p.lose_contact_id,
        "plant must insert the winning hash at a lower contacts_raw.id"
    );
    let list = person_list(&arch).expect("person_list must be Ok without CAS bytes on disk");
    let ada = photo_person(&list, p.ada_id, "Ada");
    assert_eq!(
        ada.photo_cas_hash.as_deref(),
        Some(ADA_PHOTO_WIN),
        "MIN(contacts_raw.id) among non-null hashes must win, not the later card"
    );
    assert_ne!(
        ada.photo_cas_hash.as_deref(),
        Some(ADA_PHOTO_LOSE),
        "later contacts_raw.id must not win which-photo"
    );
    let _ = std::fs::remove_dir_all(&root);
}
