//! #422 replaced-phone review. Queue only from shared chat, overlap, and quiet.
//! Confirm merges the new-number person into the older one. Messages stay put.
//!
//! Matrix IDs (gate grep): PH422-A-NO-QUEUE PH422-A-NAME-ONLY PH422-A-NOT-NEAR
//! phone_replace_confirm_merges_only_ada_and_the_new_number_person
//! phone_replace_undo_restores_two_people_and_sender_identity_id
//! phone_replaced_accept_does_not_close_wa_near
//!
//! Placeholders Ada / Berk / Self. Phones +905550000001 (old) and +905550000002 (new).

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    person_undo, resolve_run, review_list, review_resolve, ImportOpts, SourceKind,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

const OLD_PHONE: &str = "+905550000001";
const NEW_PHONE: &str = "+905550000002";

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-ph422-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn insert_phone(arch: &interlace_core::db::Archive, phone: &str) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'phone', ?1, ?1, 'Ada')",
            [phone],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn live_person_for(arch: &interlace_core::db::Archive, identity_id: i64) -> Option<i64> {
    arch.conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             WHERE pi.identity_id = ?1 AND p.tombstoned_at IS NULL",
            [identity_id],
            |r| r.get(0),
        )
        .ok()
}

fn name_ada(arch: &interlace_core::db::Archive, person_id: i64) {
    arch.conn
        .execute(
            "UPDATE persons SET display_name = 'Ada' WHERE id = ?1",
            [person_id],
        )
        .unwrap();
}

/// Two phone identities, each already on its own live person named Ada.
fn two_phone_people(root: &Path) -> (interlace_core::db::Archive, i64, i64, i64, i64) {
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let old_iid = insert_phone(&arch, OLD_PHONE);
    let new_iid = insert_phone(&arch, NEW_PHONE);
    resolve_run(&mut arch, 0).unwrap();
    let old_pid = live_person_for(&arch, old_iid).expect("old phone has its own live person");
    let new_pid = live_person_for(&arch, new_iid).expect("new phone has its own live person");
    assert_ne!(old_pid, new_pid, "the two phones start as two people");
    name_ada(&arch, old_pid);
    name_ada(&arch, new_pid);
    (arch, old_iid, new_iid, old_pid, new_pid)
}

fn ensure_run(arch: &interlace_core::db::Archive) -> (i64, i64) {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path)
             VALUES ('whatsapp_android_zip', 't', '/t.zip')",
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
    (src, arch.conn.last_insert_rowid())
}

fn insert_conversation(arch: &interlace_core::db::Archive, kind: &str, native_id: &str) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', ?1, ?2, 'Ada')",
            rusqlite::params![kind, native_id],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn insert_text(
    arch: &interlace_core::db::Archive,
    conv: i64,
    src: i64,
    run: i64,
    sender: i64,
    sent_at: &str,
    key: &str,
) {
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7)",
            rusqlite::params![conv, src, run, sender, sent_at, key, key],
        )
        .unwrap();
}

fn sender_ids(arch: &interlace_core::db::Archive) -> Vec<(i64, Option<i64>)> {
    let mut stmt = arch
        .conn
        .prepare("SELECT id, sender_identity_id FROM messages ORDER BY id")
        .unwrap();
    stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn reason_text(row: &serde_json::Value) -> String {
    row.get("reason")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string()
}

fn phone_rows(arch: &interlace_core::db::Archive) -> Vec<serde_json::Value> {
    review_list(arch)
        .unwrap()
        .into_iter()
        .filter(|row| reason_text(row).contains("\"phone_replaced\":true"))
        .collect()
}

fn assert_no_phone_replaced(arch: &interlace_core::db::Archive) {
    let rows = review_list(arch).unwrap();
    let hits: Vec<_> = rows
        .iter()
        .filter(|row| reason_text(row).contains("phone_replaced"))
        .collect();
    assert!(hits.is_empty(), "no phone_replaced review, got {rows:?}");
}

fn assert_positive_row(
    arch: &interlace_core::db::Archive,
    conv: i64,
    old_iid: i64,
    new_iid: i64,
    old_pid: i64,
) -> i64 {
    let rows = phone_rows(arch);
    assert_eq!(
        rows.len(),
        1,
        "one open phone_replaced row, got {:?}",
        review_list(arch).unwrap()
    );
    let row = &rows[0];
    let reason = reason_text(row);
    assert!(
        !reason.contains("\"wa_near\":true"),
        "phone_replaced is not a wa_near row: {reason}"
    );
    let names_phones = reason.contains(OLD_PHONE) && reason.contains(NEW_PHONE);
    let names_facts = reason.contains(&conv.to_string())
        || reason.contains("quiet")
        || reason.contains("overlap")
        || reason.contains("shared");
    assert!(
        names_phones || names_facts,
        "reason must name both phones or the shared-chat / overlap / quiet facts: {reason}"
    );
    let score = row["score"].as_f64().expect("score");
    assert!(
        (score - 0.60).abs() < 1e-9,
        "phone_replaced score is 0.60, got {score}"
    );
    assert_eq!(
        row["left_identity_id"].as_i64(),
        Some(new_iid),
        "left_identity_id is the newer phone"
    );
    assert_eq!(
        row["right_person_id"].as_i64(),
        Some(old_pid),
        "right_person_id is the older person"
    );
    assert_eq!(
        row["right_identity_id"].as_i64(),
        Some(old_iid),
        "right_identity_id is the older phone"
    );
    let id = row["id"].as_i64().expect("review id");
    let evidence = count(
        arch,
        &format!("SELECT COUNT(*) FROM merge_evidence WHERE review_id = {id}"),
    );
    assert_eq!(
        evidence, 0,
        "phone_replaced stores facts in reason_summary only"
    );
    id
}

fn live_non_self(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND is_self = 0",
    )
}

fn phone_identity_count(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM identities
         WHERE kind = 'phone'
           AND value_normalized IN ('+905550000001', '+905550000002')",
    )
}

/// Shared group. Old phone 2024-01-01 and 2024-01-10. New phone 2024-01-12 and 2024-02-01.
fn positive_fixture(root: &Path) -> (interlace_core::db::Archive, i64, i64, i64, i64, i64) {
    let (mut arch, old_iid, new_iid, old_pid, new_pid) = two_phone_people(root);
    let (src, run) = ensure_run(&arch);
    let conv = insert_conversation(&arch, "group", "whatsapp:group-ada");
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-01T00:00:00Z",
        "old-day-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-10T00:00:00Z",
        "old-day-b",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-01-12T00:00:00Z",
        "new-day-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-02-01T00:00:00Z",
        "new-day-b",
    );
    resolve_run(&mut arch, 0).unwrap();
    (arch, old_iid, new_iid, old_pid, new_pid, conv)
}

#[test]
fn phone_replaced_group_queues_one_open_row() {
    let root = tmp_root();
    let (arch, old_iid, new_iid, old_pid, new_pid, conv) = positive_fixture(&root);
    assert_eq!(phone_identity_count(&arch), 2, "two phone identities");
    assert_eq!(live_person_for(&arch, old_iid), Some(old_pid));
    assert_eq!(live_person_for(&arch, new_iid), Some(new_pid));
    assert_eq!(live_non_self(&arch), 2, "two live people before confirm");
    assert_positive_row(&arch, conv, old_iid, new_iid, old_pid);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn phone_replaced_confirm_keeps_third_ada_and_sender_ids() {
    let root = tmp_root();
    let (mut arch, old_iid, new_iid, old_pid, _new_pid, conv) = positive_fixture(&root);
    let rid = assert_positive_row(&arch, conv, old_iid, new_iid, old_pid);
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let third = arch.conn.last_insert_rowid();
    let before = sender_ids(&arch);
    review_resolve(&mut arch, rid, true).unwrap();
    let holder = live_person_for(&arch, old_iid).expect("old phone still linked");
    assert_eq!(
        live_person_for(&arch, new_iid),
        Some(holder),
        "confirm attaches the new phone to the same live person"
    );
    assert_eq!(
        holder, old_pid,
        "the survivor is the older person, not every Ada"
    );
    assert_eq!(before, sender_ids(&arch), "sender_identity_id is unchanged");
    let third_live: Option<String> = arch
        .conn
        .query_row(
            "SELECT tombstoned_at FROM persons WHERE id = ?1",
            [third],
            |r| r.get(0),
        )
        .unwrap();
    assert!(third_live.is_none(), "the third Ada stays live");
    assert_ne!(third, holder, "the third Ada is not merged");
    let third_phones: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             WHERE pi.person_id = ?1 AND i.kind = 'phone'",
            [third],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(third_phones, 0, "the third Ada still has neither phone");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn phone_replaced_undo_restores_two_people_and_sender_ids() {
    let root = tmp_root();
    let (mut arch, old_iid, new_iid, old_pid, new_pid, conv) = positive_fixture(&root);
    let rid = assert_positive_row(&arch, conv, old_iid, new_iid, old_pid);
    let before = sender_ids(&arch);
    review_resolve(&mut arch, rid, true).unwrap();
    let ev: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM identity_link_events WHERE op = 'merge_persons' ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    person_undo(&mut arch, ev).unwrap();
    assert_eq!(
        before,
        sender_ids(&arch),
        "undo leaves sender_identity_id unchanged"
    );
    assert_eq!(live_non_self(&arch), 2, "undo restores two live people");
    let restored_old = live_person_for(&arch, old_iid).expect("old phone person");
    let restored_new = live_person_for(&arch, new_iid).expect("new phone person");
    assert_eq!(restored_old, old_pid);
    assert_eq!(
        restored_new, new_pid,
        "the new phone is back on its own person"
    );
    assert_ne!(restored_old, restored_new);
    let status: String = arch
        .conn
        .query_row(
            "SELECT status FROM merge_review_queue WHERE id = ?1",
            [rid],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(status, "open", "undo puts the suggestion back on Review");
    let listed = review_list(&arch).unwrap();
    assert!(
        listed.iter().any(|row| row["id"].as_i64() == Some(rid)),
        "the reopened row is on the review list, got {listed:?}"
    );
    review_resolve(&mut arch, rid, false).unwrap();
    assert!(
        review_list(&arch)
            .unwrap()
            .iter()
            .all(|row| row["id"].as_i64() != Some(rid)),
        "reject removes the suggestion from Review"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn phone_replaced_two_dms_with_self_does_not_queue() {
    let root = tmp_root();
    let (mut arch, old_iid, new_iid, _old_pid, _new_pid) = two_phone_people(&root);
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Self', 1)",
            [],
        )
        .unwrap();
    let (src, run) = ensure_run(&arch);
    let old_dm = insert_conversation(&arch, "dm", "whatsapp:dm-old");
    let new_dm = insert_conversation(&arch, "dm", "whatsapp:dm-new");
    insert_text(
        &arch,
        old_dm,
        src,
        run,
        old_iid,
        "2024-01-01T00:00:00Z",
        "dm-old-a",
    );
    insert_text(
        &arch,
        old_dm,
        src,
        run,
        old_iid,
        "2024-01-10T00:00:00Z",
        "dm-old-b",
    );
    insert_text(
        &arch,
        new_dm,
        src,
        run,
        new_iid,
        "2024-01-12T00:00:00Z",
        "dm-new-a",
    );
    insert_text(
        &arch,
        new_dm,
        src,
        run,
        new_iid,
        "2024-02-01T00:00:00Z",
        "dm-new-b",
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_no_phone_replaced(&arch);
    assert_eq!(live_person_for(&arch, old_iid).is_some(), true);
    assert_ne!(
        live_person_for(&arch, old_iid),
        live_person_for(&arch, new_iid),
        "same display name without a shared chat stays two people"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn phone_replaced_gap_past_30_days_does_not_queue() {
    let root = tmp_root();
    let (mut arch, old_iid, new_iid, _old_pid, _new_pid) = two_phone_people(&root);
    let (src, run) = ensure_run(&arch);
    let conv = insert_conversation(&arch, "group", "whatsapp:group-gap");
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-01T00:00:00Z",
        "gap-old-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-10T00:00:00Z",
        "gap-old-b",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-02-11T00:00:00Z",
        "gap-new-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-03-01T00:00:00Z",
        "gap-new-b",
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_no_phone_replaced(&arch);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn phone_replaced_old_send_after_quiet_window_does_not_queue() {
    let root = tmp_root();
    let (mut arch, old_iid, new_iid, _old_pid, _new_pid) = two_phone_people(&root);
    let (src, run) = ensure_run(&arch);
    let conv = insert_conversation(&arch, "group", "whatsapp:group-quiet");
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-01T00:00:00Z",
        "quiet-old-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-10T00:00:00Z",
        "quiet-old-b",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-01-12T00:00:00Z",
        "quiet-new-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-20T00:00:00Z",
        "quiet-old-c",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-02-01T00:00:00Z",
        "quiet-new-b",
    );
    resolve_run(&mut arch, 0).unwrap();
    assert_no_phone_replaced(&arch);
    let _ = std::fs::remove_dir_all(&root);
}

fn opts() -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        ..ImportOpts::default()
    }
}

fn write_zip(path: &Path, entries: &[(&str, &[u8])]) {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).unwrap();
    }
    let f = std::fs::File::create(path).unwrap();
    let mut z = zip::ZipWriter::new(f);
    let stored =
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored);
    for (name, bytes) in entries {
        z.start_file(*name, stored).unwrap();
        z.write_all(bytes).unwrap();
    }
    z.finish().unwrap();
}

fn near_message_count(arch: &interlace_core::db::Archive) -> i64 {
    count(arch, "SELECT COUNT(*) FROM messages")
}

fn wa_near_ids(arch: &interlace_core::db::Archive) -> Vec<i64> {
    review_list(arch)
        .unwrap()
        .into_iter()
        .filter(|row| reason_text(row).contains("\"wa_near\":true"))
        .map(|row| row["id"].as_i64().expect("review id"))
        .collect()
}

#[test]
fn phone_replaced_accept_leaves_wa_near_open_and_messages() {
    let root = tmp_root();
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.conn
        .execute(
            "UPDATE archive_meta SET owner_display_name = 'Self' WHERE id = 1",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Self', 1)",
            [],
        )
        .unwrap();
    let jpeg = b"\xFF\xD8fakejpeg";
    let android_chat = "\
3/15/24, 2:00 PM - Messages and calls are end-to-end encrypted
3/15/24, 2:30 PM - Ada: side-note-android
3/15/24, 2:32 PM - You: bring the blue cup
";
    let ios_chat = "\
[3/15/24, 2:00:00 PM] Messages and calls are end-to-end encrypted
[3/15/24, 2:31:18 PM] Ada: side-note-ios
[3/15/24, 2:32:18 PM] Self: bring the red cup <attached: IMG-0007.jpg>
";
    let android = root.join("a").join("android-ada.zip");
    let ios = root.join("b").join("WhatsApp Chat - Pocket.zip");
    write_zip(
        &android,
        &[("WhatsApp Chat with Ada.txt", android_chat.as_bytes())],
    );
    write_zip(
        &ios,
        &[("_chat.txt", ios_chat.as_bytes()), ("IMG-0007.jpg", jpeg)],
    );
    arch.run_import(SourceKind::WhatsappAndroidZip, &android, &opts())
        .unwrap();
    arch.run_import(SourceKind::WhatsappIosZip, &ios, &opts())
        .unwrap();
    let near = wa_near_ids(&arch);
    assert_eq!(
        near.len(),
        1,
        "the near pair is its own open row, got {near:?}"
    );
    let near_id = near[0];

    let old_iid = insert_phone(&arch, OLD_PHONE);
    let new_iid = insert_phone(&arch, NEW_PHONE);
    resolve_run(&mut arch, 0).unwrap();
    let old_pid = live_person_for(&arch, old_iid).expect("old phone person");
    let new_pid = live_person_for(&arch, new_iid).expect("new phone person");
    assert_ne!(old_pid, new_pid);
    name_ada(&arch, old_pid);
    name_ada(&arch, new_pid);
    let (src, run) = ensure_run(&arch);
    let conv = insert_conversation(&arch, "group", "whatsapp:group-near");
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-01T00:00:00Z",
        "near-old-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        old_iid,
        "2024-01-10T00:00:00Z",
        "near-old-b",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-01-12T00:00:00Z",
        "near-new-a",
    );
    insert_text(
        &arch,
        conv,
        src,
        run,
        new_iid,
        "2024-02-01T00:00:00Z",
        "near-new-b",
    );
    resolve_run(&mut arch, 0).unwrap();
    let phone_id = assert_positive_row(&arch, conv, old_iid, new_iid, old_pid);
    assert!(
        wa_near_ids(&arch).contains(&near_id),
        "wa_near stays open beside phone_replaced"
    );
    let messages_before = near_message_count(&arch);
    let bodies_before = sender_ids(&arch);
    review_resolve(&mut arch, phone_id, true).unwrap();
    assert_eq!(
        near_message_count(&arch),
        messages_before,
        "accepting phone_replaced does not delete a message"
    );
    assert_eq!(
        sender_ids(&arch),
        bodies_before,
        "message rows stay on the same sender ids"
    );
    let near_status: String = arch
        .conn
        .query_row(
            "SELECT status FROM merge_review_queue WHERE id = ?1",
            [near_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        near_status, "open",
        "phone_replaced accept does not accept wa_near"
    );
    assert!(
        wa_near_ids(&arch).contains(&near_id),
        "wa_near is still listed open"
    );
    let _ = std::fs::remove_dir_all(&root);
}
