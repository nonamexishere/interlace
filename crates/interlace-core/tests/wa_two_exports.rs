//! #421 two WhatsApp exports of one chat.
//!
//! Matrix IDs (gate grep): WA421-A-NO-COLLIDE WA421-A-TITLE WA421-A-SECONDS
//! WA421-A-SENDER WA421-A-MEDIA-BODY WA421-A-SEQ title_split_two_conversations
//! two_sources_stay_two chat_match_not_person_review photo-on-kept-message
//! shared-line-one-row ambiguous-stays-two berk-stays-second-person
//!
//! #471 (gate grep): WA471-SHOW-ORDER WA471-SHOW-NOT-KEEP WA471-ACCEPT-BODY
//! WA471-REJECT WA471-ONE-ZIP WA471-NO-MERGE WA471-SEARCH WA471-REIMPORT
//! WA471-OTHER-PAIR
//! Matrix IDs (gate grep): WA471-REIMPORT-CLOCK-FIRST WA471-REIMPORT-CLOCK-LATER
//!
//! Android zip, then an iOS zip whose stem does not fold to Ada. Placeholders
//! Ada / Berk / Self only. `wa-v1` is not the content hash: these fixtures
//! differ by title, minute-versus-second clock text, You versus the owner
//! name, and a per-file seq shift from an earlier Android-only line.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    person_list, person_show, person_timeline, person_timeline_rows, review_list, review_resolve,
    review_show, search, ImportOpts, SearchQuery, SourceKind,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

const ANDROID_CHAT: &str = "WhatsApp Chat with Ada.txt";
const IOS_STEM: &str = "WhatsApp Chat - Pocket";

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-wa421-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn opts() -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        ..ImportOpts::default()
    }
}

fn archive_with_self_and_berk(root: &Path) -> (interlace_core::db::Archive, i64) {
    let arch = init_archive(root).unwrap();
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
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Berk', 0)",
            [],
        )
        .unwrap();
    let berk: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM persons WHERE display_name = 'Berk' AND tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    (arch, berk)
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

fn android_chat(lines: &[&str]) -> String {
    let mut chat = String::from("3/15/24, 2:00 PM - Messages and calls are end-to-end encrypted\n");
    for line in lines {
        chat.push_str(line);
        chat.push('\n');
    }
    chat
}

fn ios_chat(lines: &[&str]) -> String {
    let mut chat =
        String::from("[3/15/24, 2:00:00 PM] Messages and calls are end-to-end encrypted\n");
    for line in lines {
        chat.push_str(line);
        chat.push('\n');
    }
    chat
}

fn android_zip(dir: &Path, lines: &[&str]) -> PathBuf {
    let path = dir.join("android-ada.zip");
    let chat = android_chat(lines);
    write_zip(&path, &[(ANDROID_CHAT, chat.as_bytes())]);
    path
}

fn ios_zip(dir: &Path, lines: &[&str], files: &[(&str, &[u8])]) -> PathBuf {
    let path = dir.join(format!("{IOS_STEM}.zip"));
    let chat = ios_chat(lines);
    let mut entries: Vec<(&str, &[u8])> = vec![("_chat.txt", chat.as_bytes())];
    entries.extend_from_slice(files);
    write_zip(&path, &entries);
    path
}

fn import_android(arch: &mut interlace_core::db::Archive, zip: &Path) {
    arch.run_import(SourceKind::WhatsappAndroidZip, zip, &opts())
        .unwrap();
}

fn import_ios(arch: &mut interlace_core::db::Archive, zip: &Path) {
    arch.run_import(SourceKind::WhatsappIosZip, zip, &opts())
        .unwrap();
}

fn user_rows(arch: &interlace_core::db::Archive) -> Vec<(i64, i64, String)> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT id, conversation_id, COALESCE(body_text, '')
             FROM messages
             WHERE COALESCE(body_text, '') NOT LIKE '%end-to-end encrypted%'
             ORDER BY id",
        )
        .unwrap();
    stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn rows_with_body<'a>(rows: &'a [(i64, i64, String)], body: &str) -> Vec<&'a (i64, i64, String)> {
    rows.iter().filter(|(_, _, b)| b == body).collect()
}

fn assert_two_source_kinds(arch: &interlace_core::db::Archive) {
    let mut kinds: Vec<String> = {
        let mut stmt = arch
            .conn
            .prepare("SELECT kind FROM sources ORDER BY kind")
            .unwrap();
        stmt.query_map([], |r| r.get(0))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };
    kinds.sort();
    assert_eq!(
        kinds,
        vec![
            "whatsapp_android_zip".to_string(),
            "whatsapp_ios_zip".to_string(),
        ],
        "the two zips stay two sources"
    );
}

fn assert_berk_untouched(arch: &interlace_core::db::Archive, berk_id: i64) {
    let (id, tomb): (i64, Option<String>) = arch
        .conn
        .query_row(
            "SELECT id, tombstoned_at FROM persons WHERE display_name = 'Berk'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(id, berk_id, "Berk must stay the planted person");
    assert!(tomb.is_none(), "Berk must stay a live person");
    let live_berks = count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE display_name = 'Berk' AND tombstoned_at IS NULL",
    );
    assert_eq!(live_berks, 1, "Berk stays one separate person");
    let merges = count(
        arch,
        "SELECT COUNT(*) FROM identity_link_events WHERE op = 'merge_persons'",
    );
    assert_eq!(merges, 0, "this import must not call merge_persons");
}

fn assert_no_person_review(arch: &interlace_core::db::Archive) {
    let rows = review_list(arch).unwrap();
    assert!(
        rows.is_empty(),
        "exact content overlap must not enqueue a person review, got {rows:?}"
    );
}

fn live_person_ids(arch: &interlace_core::db::Archive) -> Vec<i64> {
    let mut stmt = arch
        .conn
        .prepare("SELECT id FROM persons WHERE tombstoned_at IS NULL ORDER BY id")
        .unwrap();
    stmt.query_map([], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn link_ops(arch: &interlace_core::db::Archive) -> (i64, i64) {
    let merges = count(
        arch,
        "SELECT COUNT(*) FROM identity_link_events WHERE op = 'merge_persons'",
    );
    let links = count(
        arch,
        "SELECT COUNT(*) FROM identity_link_events WHERE op = 'link'",
    );
    (merges, links)
}

fn near_review_id(arch: &interlace_core::db::Archive) -> i64 {
    let rows = review_list(arch).unwrap();
    let hits: Vec<i64> = rows
        .iter()
        .filter(|row| {
            let blob = row.to_string();
            blob.contains("bring the blue cup") && blob.contains("bring the red cup")
        })
        .map(|row| row["id"].as_i64().expect("review id"))
        .collect();
    assert_eq!(
        hits.len(),
        1,
        "near pair must be one open review whose list payload names both bodies, got {rows:?}"
    );
    hits[0]
}

fn photo_on(arch: &interlace_core::db::Archive, filename: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT message_id FROM attachments
             WHERE filename = ?1 AND cas_hash IS NOT NULL AND omitted = 0",
            [filename],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("photo {filename}: {e}"))
}

/// One shared plain line collapses to one row. The iOS-only line stays on
/// the other conversation. An earlier Android-only line must not shift the
/// shared line off the content hash (no seq). You and the owner name Self
/// are the same sender. Two sources remain. Berk is not merged.
#[test]
fn wa_two_exports_one_shared_line_is_one_row_two_sources() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:39 PM - Ada: earlier-android-only",
            "3/15/24, 2:41 PM - You: shared-plain",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:41:18 PM] Self: shared-plain",
            "[3/15/24, 2:42:18 PM] Ada: only-ios-line",
        ],
        &[],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let android_conv: i64 = arch
        .conn
        .query_row("SELECT id FROM conversations", [], |r| r.get(0))
        .unwrap();
    import_ios(&mut arch, &ios);

    assert_two_source_kinds(&arch);
    assert_berk_untouched(&arch, berk);
    assert_no_person_review(&arch);

    let rows = user_rows(&arch);
    let shared = rows_with_body(&rows, "shared-plain");
    assert_eq!(
        shared.len(),
        1,
        "one shared plain line is one messages row, got {rows:?}"
    );
    assert_eq!(
        shared[0].1, android_conv,
        "the shared row stays on the conversation that already held the hash"
    );
    let ios_only = rows_with_body(&rows, "only-ios-line");
    assert_eq!(ios_only.len(), 1, "the iOS-only line is kept, got {rows:?}");
    assert_ne!(
        ios_only[0].1, android_conv,
        "one shared hash must not pull the rest of the later zip onto the first conversation"
    );
    let native: Vec<String> = {
        let mut stmt = arch
            .conn
            .prepare("SELECT native_id FROM conversations ORDER BY id")
            .unwrap();
        stmt.query_map([], |r| r.get(0))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };
    assert_eq!(native.len(), 2, "one shared hash leaves two conversations");
    assert_ne!(
        native[0], native[1],
        "iOS stem must not fold to the Android chat title"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Two distinct shared hashes: the later zip's non-matching line lands on
/// the conversation that already holds the matches.
#[test]
fn wa_two_exports_two_hashes_land_later_lines_on_existing_conversation() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:32 PM - Ada: alpha-shared",
            "3/15/24, 2:33 PM - You: beta-shared",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:32:18 PM] Ada: alpha-shared",
            "[3/15/24, 2:33:18 PM] Self: beta-shared",
            "[3/15/24, 2:35:18 PM] Ada: only-ios-line",
        ],
        &[],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let android_conv: i64 = arch
        .conn
        .query_row("SELECT id FROM conversations", [], |r| r.get(0))
        .unwrap();
    import_ios(&mut arch, &ios);

    assert_two_source_kinds(&arch);
    assert_berk_untouched(&arch, berk);
    assert_no_person_review(&arch);

    let rows = user_rows(&arch);
    assert_eq!(
        rows_with_body(&rows, "alpha-shared").len(),
        1,
        "alpha-shared is one row, got {rows:?}"
    );
    assert_eq!(
        rows_with_body(&rows, "beta-shared").len(),
        1,
        "beta-shared is one row (You and Self), got {rows:?}"
    );
    let only = rows_with_body(&rows, "only-ios-line");
    assert_eq!(
        only.len(),
        1,
        "later zip's other line is kept, got {rows:?}"
    );
    assert_eq!(
        only[0].1, android_conv,
        "two shared hashes put the later zip's other lines on the existing conversation"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Photo only in the iOS zip attaches to the kept message. The Android
/// omitted placeholder row stays.
#[test]
fn wa_two_exports_ios_photo_on_kept_message_keeps_omitted_row() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &["3/15/24, 2:50 PM - Ada: <Media omitted>"],
    );
    let jpeg = b"\xFF\xD8fakejpeg";
    let ios = ios_zip(
        &root.join("b"),
        &["[3/15/24, 2:50:18 PM] Ada: <attached: IMG-0001.jpg>"],
        &[("IMG-0001.jpg", jpeg)],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let kept: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM messages WHERE COALESCE(body_text, '') NOT LIKE '%end-to-end encrypted%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    import_ios(&mut arch, &ios);

    assert_two_source_kinds(&arch);
    assert_berk_untouched(&arch, berk);
    let rows = user_rows(&arch);
    assert_eq!(
        rows.len(),
        1,
        "omitted line and iOS photo are one message, got {rows:?}"
    );
    assert_eq!(rows[0].0, kept, "the kept id is the Android message");

    let omitted: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM attachments
             WHERE message_id = ?1 AND omitted = 1 AND cas_hash IS NULL",
            [kept],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        omitted, 1,
        "Android omitted placeholder stays on the kept id"
    );
    assert_eq!(
        photo_on(&arch, "IMG-0001.jpg"),
        kept,
        "iOS photo attaches to the kept message id"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Android `(file attached)` and iOS `<attached: …>` strip to the same body.
#[test]
fn wa_two_exports_file_attached_phrase_shares_one_message() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &["3/15/24, 2:51 PM - Ada: picnic.jpg (file attached)"],
    );
    let jpeg = b"\xFF\xD8fakejpeg";
    let ios = ios_zip(
        &root.join("b"),
        &["[3/15/24, 2:51:44 PM] Ada: <attached: picnic.jpg>"],
        &[("picnic.jpg", jpeg)],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let kept: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM messages WHERE COALESCE(body_text, '') NOT LIKE '%end-to-end encrypted%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    import_ios(&mut arch, &ios);

    assert_berk_untouched(&arch, berk);
    let rows = user_rows(&arch);
    assert_eq!(
        rows.len(),
        1,
        "file-attached phrase and attached-token are one message, got {rows:?}"
    );
    assert_eq!(rows[0].0, kept);
    assert_eq!(photo_on(&arch, "picnic.jpg"), kept);
    let _ = std::fs::remove_dir_all(&root);
}

fn near_pair_zips(root: &Path) -> (PathBuf, PathBuf) {
    let jpeg = b"\xFF\xD8fakejpeg";
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:30 PM - Ada: side-note-android",
            "3/15/24, 2:32 PM - You: bring the blue cup",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:31:18 PM] Ada: side-note-ios",
            "[3/15/24, 2:32:18 PM] Self: bring the red cup <attached: IMG-0007.jpg>",
        ],
        &[("IMG-0007.jpg", jpeg)],
    );
    (android, ios)
}

fn import_near_pair(root: &Path) -> (interlace_core::db::Archive, i64, i64, i64) {
    let (android, ios) = near_pair_zips(root);
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let blue: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM messages WHERE body_text = 'bring the blue cup'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    import_ios(&mut arch, &ios);
    let red: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM messages WHERE body_text LIKE '%bring the red cup%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_ne!(blue, red, "near pair stays two rows until Review");
    assert_eq!(
        photo_on(&arch, "IMG-0007.jpg"),
        red,
        "photo starts on the later message"
    );
    assert_berk_untouched(&arch, berk);
    (arch, berk, blue, red)
}

/// Same minute, same canonical sender, different stripped body: two rows.
/// Accept joins them onto the kept id and the photo follows. People stay.
/// WA471-ACCEPT-BODY / WA471-OTHER-PAIR: `body_text` is the later zip's
/// sentence, the earlier sentence is the only revision, and the photo stays
/// on today's keep id.
#[test]
fn wa_two_exports_near_accept_joins_messages_not_people() {
    let root = tmp_root();
    let (mut arch, berk, blue, red) = import_near_pair(&root);
    let rid = near_review_id(&arch);
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);
    let earlier = body_of(&arch, blue);
    let later = body_of(&arch, red);
    assert_eq!(earlier, "bring the blue cup");
    assert!(
        later.contains("bring the red cup"),
        "later zip sentence, got {later:?}"
    );
    assert_eq!(
        today_keep_id(&arch, blue, red),
        blue,
        "survivor id is today's keep id"
    );

    review_resolve(&mut arch, rid, true).unwrap();

    let rows = user_rows(&arch);
    let ids: Vec<i64> = rows.iter().map(|r| r.0).collect();
    assert!(
        ids.contains(&blue) && !ids.contains(&red),
        "Accept joins the near pair onto the kept id, got {rows:?}"
    );
    assert_eq!(rows_with_body(&rows, "side-note-android").len(), 1);
    assert_eq!(rows_with_body(&rows, "side-note-ios").len(), 1);
    assert_eq!(
        photo_on(&arch, "IMG-0007.jpg"),
        blue,
        "WA471-OTHER-PAIR: photo follows the survivor"
    );
    assert_eq!(
        live_person_ids(&arch),
        people,
        "Accept does not merge people"
    );
    assert_eq!(
        link_ops(&arch),
        ops,
        "Accept does not merge_persons or link_identity for this pair"
    );
    assert_berk_untouched(&arch, berk);
    assert_eq!(
        body_of(&arch, blue),
        later,
        "WA471-ACCEPT-BODY: body_text is the later zip's sentence, got {rows:?}"
    );
    assert_eq!(
        revision_bodies(&arch, blue),
        vec![Some(earlier)],
        "WA471-ACCEPT-BODY: the earlier sentence is the only revision"
    );
    let (state, stone) = edit_state_of(&arch, blue);
    assert_eq!(state, "edited", "WA471-ACCEPT-BODY: edit_state");
    assert_eq!(stone, 0, "WA471-ACCEPT-BODY: the row is not a tombstone");
    let _ = std::fs::remove_dir_all(&root);
}

/// Reject leaves the near pair as two rows. The photo stays put.
#[test]
fn wa_two_exports_near_reject_leaves_two_rows() {
    let root = tmp_root();
    let (mut arch, berk, blue, red) = import_near_pair(&root);
    let rid = near_review_id(&arch);
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);

    review_resolve(&mut arch, rid, false).unwrap();

    let rows = user_rows(&arch);
    let ids: Vec<i64> = rows.iter().map(|r| r.0).collect();
    assert!(
        ids.contains(&blue) && ids.contains(&red),
        "Reject leaves two message rows, got {rows:?}"
    );
    assert_eq!(rows_with_body(&rows, "bring the blue cup").len(), 1);
    assert_eq!(
        rows.iter()
            .filter(|(_, _, b)| b.contains("bring the red cup"))
            .count(),
        1
    );
    assert_eq!(
        photo_on(&arch, "IMG-0007.jpg"),
        red,
        "Reject does not move the photo"
    );
    assert_eq!(live_person_ids(&arch), people);
    assert_eq!(link_ops(&arch), ops);
    assert_berk_untouched(&arch, berk);
    let _ = std::fs::remove_dir_all(&root);
}

/// Same Android zip twice still does not duplicate the shared line (`wa-v1`).
#[test]
fn wa_two_exports_same_android_zip_twice_does_not_duplicate() {
    let root = tmp_root();
    let android = android_zip(&root.join("a"), &["3/15/24, 2:41 PM - You: shared-plain"]);
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_android(&mut arch, &android);
    let rows = user_rows(&arch);
    assert_eq!(
        rows_with_body(&rows, "shared-plain").len(),
        1,
        "importing the same Android zip twice must not duplicate the line, got {rows:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

fn reason_text(row: &serde_json::Value) -> String {
    row.get("reason")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string()
}

fn live_person_count(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    )
}

fn review_ids_for_pair(arch: &interlace_core::db::Archive, a: &str, b: &str) -> Vec<i64> {
    review_list(arch)
        .unwrap()
        .into_iter()
        .filter(|row| {
            let reason = reason_text(row);
            reason.contains("\"wa_near\":true") && reason.contains(a) && reason.contains(b)
        })
        .map(|row| row["id"].as_i64().expect("review id"))
        .collect()
}

fn open_pair_id(arch: &interlace_core::db::Archive, a: &str, b: &str) -> i64 {
    let ids = review_ids_for_pair(arch, a, b);
    assert_eq!(
        ids.len(),
        1,
        "expected one open wa_near row naming {a:?} and {b:?}, got {:?}",
        review_list(arch).unwrap()
    );
    ids[0]
}

fn ada_year_counts(arch: &interlace_core::db::Archive) -> Vec<(i64, i64)> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT py.include_groups, py.message_count
             FROM person_year_index py
             JOIN persons p ON p.id = py.person_id
             WHERE p.display_name = 'Ada' AND py.year = 2024
             ORDER BY py.include_groups",
        )
        .unwrap();
    stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn assert_last_message_at_matches_remaining(arch: &interlace_core::db::Archive) {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT c.id, c.last_message_at,
                    (SELECT MAX(m.sent_at) FROM messages m WHERE m.conversation_id = c.id)
             FROM conversations c
             ORDER BY c.id",
        )
        .unwrap();
    let rows: Vec<(i64, Option<String>, Option<String>)> = stmt
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert!(!rows.is_empty(), "conversation row missing");
    for (id, stored, latest) in rows {
        assert_eq!(
            stored, latest,
            "conversations.last_message_at for {id} must be the latest remaining sent_at"
        );
    }
}

/// Two different near lines from Ada in one minute are two open reviews.
/// Accepting one joins only that pair; the other stays open and joins later.
/// WA471-OTHER-PAIR: the second pair stays open until its own Accept.
/// WA471-ACCEPT-BODY: each survivor's body is that pair's later sentence.
#[test]
fn wa_two_exports_two_near_lines_accept_one_pair_then_the_other() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:32 PM - Ada: linen note",
            "3/15/24, 2:32 PM - Ada: basket note",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:32:18 PM] Ada: canvas note",
            "[3/15/24, 2:32:18 PM] Ada: cooler note",
        ],
        &[],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);

    let rows = review_list(&arch).unwrap();
    let near: Vec<&serde_json::Value> = rows
        .iter()
        .filter(|row| reason_text(row).contains("\"wa_near\":true"))
        .collect();
    assert_eq!(
        near.len(),
        2,
        "two near lines in one minute are two open rows, got {rows:?}"
    );
    let linen = open_pair_id(&arch, "linen note", "canvas note");
    let basket = open_pair_id(&arch, "basket note", "cooler note");
    assert_ne!(linen, basket, "the two pairs must not share one review row");
    for row in &near {
        let reason = reason_text(row);
        let linen_pair = reason.contains("linen note") && reason.contains("canvas note");
        let basket_pair = reason.contains("basket note") && reason.contains("cooler note");
        assert!(
            linen_pair ^ basket_pair,
            "each wa_near row names one pair only, got {reason}"
        );
    }

    let linen_id = message_id_with_body(&arch, "linen note");
    let canvas_id = message_id_with_body(&arch, "canvas note");
    let basket_id = message_id_with_body(&arch, "basket note");
    let cooler_id = message_id_with_body(&arch, "cooler note");
    assert_eq!(today_keep_id(&arch, linen_id, canvas_id), linen_id);
    assert_eq!(today_keep_id(&arch, basket_id, cooler_id), basket_id);
    let people = live_person_count(&arch);
    let ops = link_ops(&arch);
    review_resolve(&mut arch, linen, true).unwrap();

    assert!(
        message_alive(&arch, linen_id) && !message_alive(&arch, canvas_id),
        "WA471-OTHER-PAIR: Accept joins only the linen/canvas ids"
    );
    assert!(
        message_alive(&arch, basket_id) && message_alive(&arch, cooler_id),
        "WA471-OTHER-PAIR: the other pair's messages stay"
    );
    let still = review_list(&arch).unwrap();
    let still_near: Vec<&serde_json::Value> = still
        .iter()
        .filter(|row| reason_text(row).contains("\"wa_near\":true"))
        .collect();
    assert_eq!(
        still_near.len(),
        1,
        "WA471-OTHER-PAIR: the other near row stays open, got {still:?}"
    );
    assert_eq!(open_pair_id(&arch, "basket note", "cooler note"), basket);
    assert_eq!(body_of(&arch, basket_id), "basket note");
    assert_eq!(body_of(&arch, cooler_id), "cooler note");
    assert!(
        revision_bodies(&arch, basket_id).is_empty(),
        "the open pair has no revision"
    );
    assert_eq!(
        body_of(&arch, linen_id),
        "canvas note",
        "WA471-ACCEPT-BODY: body_text is the later zip's sentence"
    );
    assert_eq!(
        revision_bodies(&arch, linen_id),
        vec![Some("linen note".into())],
        "WA471-ACCEPT-BODY: the earlier sentence is the only revision"
    );
    let (state, stone) = edit_state_of(&arch, linen_id);
    assert_eq!(state, "edited");
    assert_eq!(stone, 0);

    review_resolve(&mut arch, basket, true).unwrap();
    assert!(
        message_alive(&arch, basket_id) && !message_alive(&arch, cooler_id),
        "the later Accept joins the basket/cooler ids"
    );
    assert_eq!(
        body_of(&arch, basket_id),
        "cooler note",
        "WA471-ACCEPT-BODY: the second pair's body is the later sentence"
    );
    assert_eq!(
        revision_bodies(&arch, basket_id),
        vec![Some("basket note".into())],
        "WA471-ACCEPT-BODY: the second pair's earlier sentence is the revision"
    );
    assert_eq!(body_of(&arch, linen_id), "canvas note");
    assert_eq!(
        revision_bodies(&arch, linen_id),
        vec![Some("linen note".into())]
    );
    assert_eq!(live_person_count(&arch), people, "people count stays put");
    assert_eq!(link_ops(&arch), ops, "Accept does not merge or link people");
    assert_berk_untouched(&arch, berk);
    let _ = std::fs::remove_dir_all(&root);
}

fn year_counts_for(arch: &interlace_core::db::Archive, name: &str) -> Vec<(i64, i64)> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT py.include_groups, py.message_count
             FROM person_year_index py
             JOIN persons p ON p.id = py.person_id
             WHERE p.display_name = ?1 AND py.year = 2024
             ORDER BY py.include_groups",
        )
        .unwrap();
    stmt.query_map([name], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

/// Accept drops the deleted message from every participant's year count.
/// WA471-OTHER-PAIR: that drop is the deleted message, for every participant.
#[test]
fn wa_two_exports_near_accept_refreshes_other_participant_year() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:30 PM - You: alpha-shared",
            "3/15/24, 2:31 PM - Ada: beta-shared",
            "3/15/24, 2:40 PM - Ada: ada blue note",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:30:18 PM] Self: alpha-shared",
            "[3/15/24, 2:31:18 PM] Ada: beta-shared",
            "[3/15/24, 2:40:30 PM] Ada: ada red note",
        ],
        &[],
    );
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);
    let before_you = year_counts_for(&arch, "You");
    let before_ada = year_counts_for(&arch, "Ada");
    assert!(!before_you.is_empty(), "You year row must exist");
    assert!(!before_ada.is_empty(), "Ada year row must exist");
    let rid = open_pair_id(&arch, "ada blue note", "ada red note");
    review_resolve(&mut arch, rid, true).unwrap();
    for (name, before) in [("You", before_you), ("Ada", before_ada)] {
        let after = year_counts_for(&arch, name);
        assert_eq!(after.len(), before.len(), "{name} year rows stay");
        for ((flag, prev), (_, next)) in before.iter().zip(after.iter()) {
            assert_eq!(
                *next,
                prev - 1,
                "{name} message_count must drop the deleted message (include_groups={flag})"
            );
        }
    }
    let _ = std::fs::remove_dir_all(&root);
}

/// Accept of a near pair deletes the other message. Derived rows follow.
/// WA471-OTHER-PAIR: the year count drops that deleted message.
/// WA471-ACCEPT-BODY: body_text is the later zip's sentence.
#[test]
fn wa_two_exports_near_accept_refreshes_last_message_and_year_count() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:30 PM - Ada: ada earlier note",
            "3/15/24, 2:40 PM - Ada: ada blue note",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &["[3/15/24, 2:40:30 PM] Ada: ada red note"],
        &[],
    );
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);

    let not_done = count(
        &arch,
        "SELECT COUNT(*) FROM import_runs WHERE status != 'done'",
    );
    assert_eq!(not_done, 0, "import finished with status=done");
    let before = ada_year_counts(&arch);
    assert!(
        !before.is_empty(),
        "person_year_index row for Ada must exist because the import finished"
    );
    let rid = open_pair_id(&arch, "ada blue note", "ada red note");
    let blue_id = message_id_with_body(&arch, "ada blue note");
    let red_id = message_id_with_body(&arch, "ada red note");
    assert_eq!(today_keep_id(&arch, blue_id, red_id), blue_id);
    let people = live_person_count(&arch);
    review_resolve(&mut arch, rid, true).unwrap();

    assert!(
        message_alive(&arch, blue_id) && !message_alive(&arch, red_id),
        "Accept deletes the later near message id"
    );
    assert_eq!(
        rows_with_body(&user_rows(&arch), "ada earlier note").len(),
        1
    );
    let after = ada_year_counts(&arch);
    assert_eq!(
        after.len(),
        before.len(),
        "year rows stay, counts drop the deleted message, before {before:?} after {after:?}"
    );
    for ((flag, prev), (flag_after, next)) in before.iter().zip(after.iter()) {
        assert_eq!(flag_after, flag);
        assert_eq!(
            *next,
            prev - 1,
            "Ada message_count must not include the deleted message (include_groups={flag})"
        );
    }
    assert_last_message_at_matches_remaining(&arch);
    assert_eq!(live_person_count(&arch), people);
    assert_eq!(
        body_of(&arch, blue_id),
        "ada red note",
        "WA471-ACCEPT-BODY: body_text is the later zip's sentence"
    );
    assert_eq!(
        revision_bodies(&arch, blue_id),
        vec![Some("ada blue note".into())],
        "WA471-ACCEPT-BODY: the earlier sentence is the only revision"
    );
    let (state, stone) = edit_state_of(&arch, blue_id);
    assert_eq!(state, "edited");
    assert_eq!(stone, 0, "not a tombstone");
    let _ = std::fs::remove_dir_all(&root);
}

fn encrypted_on(arch: &interlace_core::db::Archive, conversation_id: i64) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM messages
             WHERE conversation_id = ?1
               AND COALESCE(body_text, '') LIKE '%end-to-end encrypted%'",
            [conversation_id],
            |r| r.get(0),
        )
        .unwrap()
}

/// Two shared hashes skip the later encryption line and drop the empty chat.
/// One shared hash still leaves the iOS user line and the iOS system line.
#[test]
fn wa_two_exports_two_hashes_skip_system_line_and_drop_empty_chat() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:32 PM - Ada: alpha-shared",
            "3/15/24, 2:33 PM - You: beta-shared",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:32:18 PM] Ada: alpha-shared",
            "[3/15/24, 2:33:18 PM] Self: beta-shared",
        ],
        &[],
    );
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    let kept: i64 = arch
        .conn
        .query_row("SELECT id FROM conversations", [], |r| r.get(0))
        .unwrap();
    import_ios(&mut arch, &ios);

    assert_eq!(
        encrypted_on(&arch, kept),
        1,
        "the later zip encryption line must not be stored on the kept conversation"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM conversations"),
        1,
        "later conversation with no non-system messages must not remain"
    );
    let rows = user_rows(&arch);
    assert_eq!(rows_with_body(&rows, "alpha-shared").len(), 1);
    assert_eq!(rows_with_body(&rows, "beta-shared").len(), 1);

    let control_android = android_zip(&root.join("c"), &["3/15/24, 2:41 PM - You: shared-plain"]);
    let control_ios = ios_zip(
        &root.join("d"),
        &[
            "[3/15/24, 2:41:18 PM] Self: shared-plain",
            "[3/15/24, 2:42:18 PM] Ada: only-ios-line",
        ],
        &[],
    );
    let (mut control, _) = archive_with_self_and_berk(&root.join("arch-one"));
    import_android(&mut control, &control_android);
    let android_conv: i64 = control
        .conn
        .query_row("SELECT id FROM conversations", [], |r| r.get(0))
        .unwrap();
    import_ios(&mut control, &control_ios);
    let later: i64 = control
        .conn
        .query_row(
            "SELECT conversation_id FROM messages WHERE body_text = 'only-ios-line'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_ne!(
        later, android_conv,
        "one shared hash leaves the iOS-only user line on the later conversation"
    );
    assert_eq!(
        encrypted_on(&control, later),
        1,
        "one shared hash leaves the iOS system line on the later conversation"
    );
    assert_eq!(count(&control, "SELECT COUNT(*) FROM conversations"), 2);
    let _ = std::fs::remove_dir_all(&root);
}

/// Same Android zip again must store the content hash on the wa-v1 duplicate,
/// so a later iOS zip collapses the shared line. skipped_dupes still counts.
#[test]
fn wa_two_exports_reimport_stores_content_hash_then_ios_collapses() {
    let root = tmp_root();
    let android = android_zip(&root.join("a"), &["3/15/24, 2:41 PM - You: shared-plain"]);
    let ios = ios_zip(
        &root.join("b"),
        &["[3/15/24, 2:41:18 PM] Self: shared-plain"],
        &[],
    );
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    // First insert already wrote the content row. Clear it so the same-file
    // wa-v1 hit is the path that must store the hash.
    arch.conn
        .execute("DELETE FROM wa_message_content", [])
        .unwrap();
    let again = arch
        .run_import(SourceKind::WhatsappAndroidZip, &android, &opts())
        .unwrap();
    assert!(
        again.skipped_dupes > 0,
        "same-file reimport still counts skipped_dupes, got {}",
        again.skipped_dupes
    );
    import_ios(&mut arch, &ios);
    let rows = user_rows(&arch);
    assert_eq!(
        rows_with_body(&rows, "shared-plain").len(),
        1,
        "reimport must store the content hash so the later zip collapses the line, got {rows:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// A caption plus the Android file phrase hashes as the caption, same as iOS.
#[test]
fn wa_two_exports_caption_and_file_phrase_are_one_message_not_near() {
    let root = tmp_root();
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:51 PM - Ada: picnic caption",
            "picnic.jpg (file attached)",
        ],
    );
    let jpeg = b"\xFF\xD8fakejpeg";
    let ios = ios_zip(
        &root.join("b"),
        &["[3/15/24, 2:51:18 PM] Ada: picnic caption <attached: picnic.jpg>"],
        &[("picnic.jpg", jpeg)],
    );
    let (mut arch, _berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);

    let rows = user_rows(&arch);
    assert_eq!(
        rows.len(),
        1,
        "caption plus file-attached phrase is one message, got {rows:?}"
    );
    let listed = review_list(&arch).unwrap();
    let near: Vec<&serde_json::Value> = listed
        .iter()
        .filter(|row| {
            let reason = reason_text(row);
            reason.contains("\"wa_near\":true")
                && (reason.contains("picnic caption") || reason.contains("picnic.jpg"))
        })
        .collect();
    assert!(
        near.is_empty(),
        "that caption pair must not be a near review, got {listed:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

const OLDER_WORDING: &str = "merhaba";
const NEWER_WORDING: &str = "merhaba canim";

fn body_of(arch: &interlace_core::db::Archive, id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT COALESCE(body_text, '') FROM messages WHERE id = ?1",
            [id],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("message {id}: {e}"))
}

fn revision_bodies(arch: &interlace_core::db::Archive, message_id: i64) -> Vec<Option<String>> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT body_text FROM message_revisions
             WHERE message_id = ?1 ORDER BY rev_no",
        )
        .unwrap();
    stmt.query_map([message_id], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn edit_state_of(arch: &interlace_core::db::Archive, id: i64) -> (String, i64) {
    arch.conn
        .query_row(
            "SELECT edit_state, tombstone FROM messages WHERE id = ?1",
            [id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap_or_else(|e| panic!("message {id}: {e}"))
}

fn sent_at_of(arch: &interlace_core::db::Archive, id: i64) -> String {
    arch.conn
        .query_row("SELECT sent_at FROM messages WHERE id = ?1", [id], |r| {
            r.get(0)
        })
        .unwrap_or_else(|e| panic!("sent_at {id}: {e}"))
}

/// Today's keep id: earlier `sent_at`, then the lower id.
fn today_keep_id(arch: &interlace_core::db::Archive, a: i64, b: i64) -> i64 {
    match sent_at_of(arch, a).cmp(&sent_at_of(arch, b)) {
        std::cmp::Ordering::Less => a,
        std::cmp::Ordering::Greater => b,
        std::cmp::Ordering::Equal => a.min(b),
    }
}

fn message_alive(arch: &interlace_core::db::Archive, id: i64) -> bool {
    arch.conn
        .query_row("SELECT COUNT(*) FROM messages WHERE id = ?1", [id], |r| {
            r.get::<_, i64>(0)
        })
        .unwrap()
        == 1
}

fn message_id_with_body(arch: &interlace_core::db::Archive, body: &str) -> i64 {
    let mut stmt = arch
        .conn
        .prepare("SELECT id FROM messages WHERE body_text = ?1 ORDER BY id")
        .unwrap();
    let ids: Vec<i64> = stmt
        .query_map([body], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(
        ids.len(),
        1,
        "body {body:?} ids {ids:?}, rows {:?}",
        user_rows(arch)
    );
    ids[0]
}

fn ids_containing(arch: &interlace_core::db::Archive, text: &str) -> Vec<i64> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT id FROM messages
             WHERE COALESCE(body_text, '') LIKE '%' || ?1 || '%'
             ORDER BY id",
        )
        .unwrap();
    stmt.query_map([text], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn wa_near_ids(arch: &interlace_core::db::Archive) -> Vec<i64> {
    review_list(arch)
        .unwrap()
        .into_iter()
        .filter(|row| reason_text(row).contains("\"wa_near\":true"))
        .map(|row| row["id"].as_i64().expect("review id"))
        .collect()
}

fn only_wa_near_id(arch: &interlace_core::db::Archive) -> i64 {
    let ids = wa_near_ids(arch);
    assert_eq!(
        ids.len(),
        1,
        "expected one open wa_near row, got {:?}",
        review_list(arch).unwrap()
    );
    ids[0]
}

fn live_person_named(arch: &interlace_core::db::Archive, name: &str) -> i64 {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT id FROM persons
             WHERE display_name = ?1 AND tombstoned_at IS NULL
             ORDER BY id",
        )
        .unwrap();
    let ids: Vec<i64> = stmt
        .query_map([name], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(ids.len(), 1, "one live person {name}, got {ids:?}");
    ids[0]
}

fn content_hash_of(arch: &interlace_core::db::Archive, id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT content_hash FROM wa_message_content WHERE message_id = ?1",
            [id],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("content hash for {id}: {e}"))
}

fn idempotency_of(arch: &interlace_core::db::Archive, id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT idempotency_key FROM messages WHERE id = ?1",
            [id],
            |r| r.get(0),
        )
        .unwrap()
}

fn event_count(arch: &interlace_core::db::Archive) -> i64 {
    count(arch, "SELECT COUNT(*) FROM identity_link_events")
}

fn conv_kinds(arch: &interlace_core::db::Archive) -> Vec<String> {
    let mut stmt = arch
        .conn
        .prepare("SELECT kind FROM conversations ORDER BY id")
        .unwrap();
    stmt.query_map([], |r| r.get(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn archive_with_self_and_ada(root: &Path) -> (interlace_core::db::Archive, i64) {
    let arch = init_archive(root).unwrap();
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
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let ada: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM persons WHERE display_name = 'Ada' AND tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    (arch, ada)
}

fn berk_android(dir: &Path, lines: &[&str]) -> PathBuf {
    let path = dir.join("android-berk.zip");
    let chat = android_chat(lines);
    write_zip(&path, &[("WhatsApp Chat with Berk.txt", chat.as_bytes())]);
    path
}

fn berk_ios(dir: &Path, lines: &[&str], files: &[(&str, &[u8])]) -> PathBuf {
    let path = dir.join("WhatsApp Chat - Berk.zip");
    let chat = ios_chat(lines);
    let mut entries: Vec<(&str, &[u8])> = vec![("_chat.txt", chat.as_bytes())];
    entries.extend_from_slice(files);
    write_zip(&path, &entries);
    path
}

fn import_berk_zips(
    root: &Path,
    first_android: bool,
    android_lines: &[&str],
    ios_lines: &[&str],
) -> (interlace_core::db::Archive, i64) {
    let android = berk_android(&root.join("a"), android_lines);
    let ios = berk_ios(&root.join("b"), ios_lines, &[]);
    let (mut arch, ada) = archive_with_self_and_ada(&root.join("arch"));
    if first_android {
        import_android(&mut arch, &android);
        import_ios(&mut arch, &ios);
    } else {
        import_ios(&mut arch, &ios);
        import_android(&mut arch, &android);
    }
    (arch, ada)
}

fn wording_pair_ids(arch: &interlace_core::db::Archive) -> (i64, i64) {
    let older = message_id_with_body(arch, OLDER_WORDING);
    let newer = message_id_with_body(arch, NEWER_WORDING);
    assert!(
        older < newer,
        "the first zip is the lower id (older {older} sent {} , newer {newer} sent {})",
        sent_at_of(arch, older),
        sent_at_of(arch, newer)
    );
    (older, newer)
}

fn assert_wording_show(arch: &interlace_core::db::Archive, id_label: &str) {
    let shown = review_show(arch, only_wa_near_id(arch)).unwrap();
    assert!(
        shown.get("review").is_some(),
        "{id_label}: review object stays beside the wording keys, got {shown}"
    );
    assert_eq!(
        shown.get("older_wording").and_then(|v| v.as_str()),
        Some(OLDER_WORDING),
        "{id_label}: older_wording, got {shown}"
    );
    assert_eq!(
        shown.get("newer_wording").and_then(|v| v.as_str()),
        Some(NEWER_WORDING),
        "{id_label}: newer_wording, got {shown}"
    );
}

/// WA471-SHOW-ORDER: first zip `merhaba`, later zip `merhaba canim` at the
/// same minute. `review_show` names those wordings in that order.
#[test]
fn wa471_show_order_older_then_newer() {
    let root = tmp_root();
    let (arch, ada) = import_berk_zips(
        &root,
        true,
        &["3/15/24, 10:00 AM - Berk: merhaba"],
        &["[3/15/24, 10:00:18 AM] Berk: merhaba canim"],
    );
    let (older, newer) = wording_pair_ids(&arch);
    assert_eq!(body_of(&arch, older), OLDER_WORDING);
    assert_eq!(body_of(&arch, newer), NEWER_WORDING);
    assert_eq!(
        today_keep_id(&arch, older, newer),
        older,
        "the later clock is not the keep id (older sent {}, newer sent {})",
        sent_at_of(&arch, older),
        sent_at_of(&arch, newer)
    );
    assert_ne!(ada, live_person_named(&arch, "Berk"));
    assert_wording_show(&arch, "WA471-SHOW-ORDER");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-SHOW-NOT-KEEP: the later zip's clock sorts earlier inside the minute.
/// Older is still the first zip's `merhaba`. Newer is still `merhaba canim`.
#[test]
fn wa471_show_not_keep_when_later_clock_is_earlier() {
    let root = tmp_root();
    let (arch, _ada) = import_berk_zips(
        &root,
        false,
        &["3/15/24, 10:00 AM - Berk: merhaba canim"],
        &["[3/15/24, 10:00:40 AM] Berk: merhaba"],
    );
    let (older, newer) = wording_pair_ids(&arch);
    let keep = today_keep_id(&arch, older, newer);
    assert_eq!(
        keep,
        newer,
        "WA471-SHOW-NOT-KEEP: keep follows the earlier clock, not import order \
         (older id {older} sent {}, newer id {newer} sent {})",
        sent_at_of(&arch, older),
        sent_at_of(&arch, newer)
    );
    assert_eq!(body_of(&arch, keep), NEWER_WORDING);
    assert_wording_show(&arch, "WA471-SHOW-NOT-KEEP");
    let shown = review_show(&arch, only_wa_near_id(&arch)).unwrap();
    assert_ne!(
        shown.get("older_wording").and_then(|v| v.as_str()),
        Some(body_of(&arch, keep).as_str()),
        "WA471-SHOW-NOT-KEEP: older wording is not the keep body, got {shown}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

fn accept_wording_pair(root: &Path) -> (interlace_core::db::Archive, i64, i64, i64) {
    let (mut arch, ada) = import_berk_zips(
        &root,
        true,
        // After the helper's 2:00 PM encryption line, so that line is not the preview.
        &["3/15/24, 3:00 PM - Berk: merhaba"],
        &["[3/15/24, 3:00:18 PM] Berk: merhaba canim"],
    );
    let (older, newer) = wording_pair_ids(&arch);
    let keep = today_keep_id(&arch, older, newer);
    assert_eq!(keep, older, "today's keep id is the first zip");
    let rid = only_wa_near_id(&arch);
    review_resolve(&mut arch, rid, true).unwrap();
    (arch, ada, keep, newer)
}

/// WA471-ACCEPT-BODY: one message, body `merhaba canim`, one revision
/// `merhaba`, `edit_state` edited, timeline `previous_bodies` is that older
/// sentence only. The other id is gone. The survivor is today's keep id.
#[test]
fn wa471_accept_body_newer_sentence_and_older_revision() {
    let root = tmp_root();
    let (arch, ada, keep, dropped) = accept_wording_pair(&root);
    assert!(message_alive(&arch, keep), "survivor id is today's keep id");
    assert!(
        !message_alive(&arch, dropped),
        "the other message id is gone"
    );
    assert_eq!(
        body_of(&arch, keep),
        NEWER_WORDING,
        "WA471-ACCEPT-BODY: body is the newer sentence"
    );
    assert_eq!(
        revision_bodies(&arch, keep),
        vec![Some(OLDER_WORDING.into())],
        "WA471-ACCEPT-BODY: one revision is the older sentence"
    );
    let (state, stone) = edit_state_of(&arch, keep);
    assert_eq!(state, "edited", "WA471-ACCEPT-BODY: edit_state");
    assert_eq!(stone, 0, "WA471-ACCEPT-BODY: not a tombstone");
    let berk = live_person_named(&arch, "Berk");
    assert_ne!(ada, berk, "WA471-NO-MERGE: Ada is not Berk");
    let rows = person_timeline_rows(&arch, berk, false, 20, None).unwrap();
    let row = rows
        .iter()
        .find(|r| r.message_id == keep)
        .unwrap_or_else(|| {
            panic!(
                "WA471-ACCEPT-BODY: timeline missing survivor, kinds {:?} rows {rows:?}",
                conv_kinds(&arch)
            )
        });
    assert_eq!(row.body_text, NEWER_WORDING);
    assert_eq!(row.edit_state, "edited");
    assert_eq!(
        row.previous_bodies,
        vec![OLDER_WORDING.to_string()],
        "WA471-ACCEPT-BODY: previous_bodies is exactly the older sentence"
    );
    assert!(rows.iter().all(|r| r.message_id != dropped));
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-REJECT: Reject on a second pair leaves both messages, no revision,
/// and `edit_state` stays `original` (no Edited chip). The other pair stays open.
#[test]
fn wa471_reject_second_pair_leaves_both_original() {
    let root = tmp_root();
    let (mut arch, ada) = import_berk_zips(
        &root,
        true,
        &[
            "3/15/24, 10:00 AM - Berk: merhaba",
            "3/15/24, 11:00 AM - Berk: linen note",
        ],
        &[
            "[3/15/24, 10:00:18 AM] Berk: merhaba canim",
            "[3/15/24, 11:00:18 AM] Berk: canvas note",
        ],
    );
    let wording = only_open_wording_id(&arch);
    let second = open_pair_id(&arch, "linen note", "canvas note");
    assert_ne!(wording, second, "the second pair is its own review row");
    let linen_id = message_id_with_body(&arch, "linen note");
    let canvas_id = message_id_with_body(&arch, "canvas note");
    let berk = live_person_named(&arch, "Berk");
    assert_ne!(ada, berk);
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);
    let events = event_count(&arch);

    review_resolve(&mut arch, second, false).unwrap();

    assert!(
        message_alive(&arch, linen_id) && message_alive(&arch, canvas_id),
        "WA471-REJECT: both messages stay"
    );
    assert_eq!(body_of(&arch, linen_id), "linen note");
    assert_eq!(body_of(&arch, canvas_id), "canvas note");
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        0,
        "WA471-REJECT: no revision"
    );
    let edited = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE edit_state != 'original' OR tombstone != 0",
    );
    assert_eq!(edited, 0, "WA471-REJECT: edit_state stays original");
    assert_eq!(
        wa_near_ids(&arch),
        vec![wording],
        "WA471-REJECT: the other pair stays open"
    );
    let rows = person_timeline_rows(&arch, berk, false, 20, None).unwrap();
    for id in [linen_id, canvas_id] {
        let row = rows.iter().find(|r| r.message_id == id).unwrap_or_else(|| {
            panic!(
                "WA471-REJECT: timeline missing {id}, kinds {:?} rows {rows:?}",
                conv_kinds(&arch)
            )
        });
        assert_eq!(row.edit_state, "original");
        assert!(
            row.previous_bodies.is_empty(),
            "WA471-REJECT: no chip, previous_bodies {:?}",
            row.previous_bodies
        );
    }
    assert_eq!(live_person_ids(&arch), people);
    assert_eq!(link_ops(&arch), ops);
    assert_eq!(event_count(&arch), events, "Reject adds no link op");
    assert_eq!(live_person_named(&arch, "Ada"), ada);
    let _ = std::fs::remove_dir_all(&root);
}

fn only_open_wording_id(arch: &interlace_core::db::Archive) -> i64 {
    let ids = review_ids_for_pair(arch, OLDER_WORDING, NEWER_WORDING);
    assert_eq!(
        ids.len(),
        1,
        "one open wording pair, got {:?}",
        review_list(arch).unwrap()
    );
    ids[0]
}

/// WA471-ONE-ZIP: one zip of the current sentence only. One row, no revision,
/// no Edited chip, no `wa_near` row.
#[test]
fn wa471_one_zip_current_sentence_has_no_chip() {
    let root = tmp_root();
    let zip = berk_ios(
        &root.join("z"),
        &["[3/15/24, 10:00:18 AM] Berk: merhaba canim"],
        &[],
    );
    let (mut arch, ada) = archive_with_self_and_ada(&root.join("arch"));
    import_ios(&mut arch, &zip);

    let rows = user_rows(&arch);
    assert_eq!(rows.len(), 1, "WA471-ONE-ZIP: one bubble, got {rows:?}");
    assert_eq!(rows[0].2, NEWER_WORDING);
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        0,
        "WA471-ONE-ZIP: no revision"
    );
    let (state, stone) = edit_state_of(&arch, rows[0].0);
    assert_eq!(state, "original", "WA471-ONE-ZIP: edit_state");
    assert_eq!(stone, 0);
    assert!(
        wa_near_ids(&arch).is_empty(),
        "WA471-ONE-ZIP: no wa_near row, got {:?}",
        review_list(&arch).unwrap()
    );
    let berk = live_person_named(&arch, "Berk");
    assert_ne!(ada, berk, "Ada is not Berk");
    let timeline = person_timeline_rows(&arch, berk, false, 20, None).unwrap();
    let row = timeline
        .iter()
        .find(|r| r.message_id == rows[0].0)
        .unwrap_or_else(|| {
            panic!(
                "WA471-ONE-ZIP: timeline missing the row, kinds {:?} rows {timeline:?}",
                conv_kinds(&arch)
            )
        });
    assert_eq!(row.body_text, NEWER_WORDING);
    assert_eq!(row.edit_state, "original");
    assert!(
        row.previous_bodies.is_empty(),
        "WA471-ONE-ZIP: no chip, previous_bodies {:?}",
        row.previous_bodies
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-NO-MERGE: Ada's person stays distinct from Berk's. Accept does not
/// merge people or add a link op.
#[test]
fn wa471_no_merge_ada_stays_distinct_from_berk() {
    let root = tmp_root();
    let (mut arch, ada) = import_berk_zips(
        &root,
        true,
        &["3/15/24, 10:00 AM - Berk: merhaba"],
        &["[3/15/24, 10:00:18 AM] Berk: merhaba canim"],
    );
    let berk = live_person_named(&arch, "Berk");
    assert_ne!(ada, berk, "WA471-NO-MERGE: Ada is not Berk before Accept");
    assert_eq!(live_person_named(&arch, "Ada"), ada);
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);
    let events = event_count(&arch);
    let rid = only_wa_near_id(&arch);
    review_resolve(&mut arch, rid, true).unwrap();
    assert_eq!(
        live_person_named(&arch, "Ada"),
        ada,
        "WA471-NO-MERGE: Ada's person stays"
    );
    assert_eq!(
        live_person_named(&arch, "Berk"),
        berk,
        "WA471-NO-MERGE: Berk's person stays"
    );
    assert_ne!(ada, berk);
    assert_eq!(
        live_person_ids(&arch),
        people,
        "Accept does not merge people"
    );
    assert_eq!(
        link_ops(&arch),
        ops,
        "Accept adds no merge_persons or link op"
    );
    assert_eq!(event_count(&arch), events, "Accept adds no link op");
    let ada_show = person_show(&arch, ada).unwrap();
    let berk_show = person_show(&arch, berk).unwrap();
    assert_eq!(ada_show.display_name, "Ada");
    assert_eq!(berk_show.display_name, "Berk");
    assert_eq!(ada_show.id, ada);
    assert_eq!(berk_show.id, berk);
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-SEARCH: after Accept, search for `canim` hits that message.
/// The people-list preview and person show use the newer body.
#[test]
fn wa471_search_preview_and_person_show_use_newer_body() {
    let root = tmp_root();
    let (arch, _ada, keep, _dropped) = accept_wording_pair(&root);
    let berk = live_person_named(&arch, "Berk");
    let show = person_show(&arch, berk).unwrap();
    assert_eq!(show.id, berk);
    assert_eq!(show.display_name, "Berk");

    let hits = search(
        &arch,
        &SearchQuery {
            q: "canim".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        hits.iter().any(|h| h.message_id == keep),
        "WA471-SEARCH: search for canim hits that message, got {hits:?}"
    );

    let preview = person_list(&arch)
        .unwrap()
        .into_iter()
        .find(|p| p.id == berk)
        .and_then(|p| p.preview)
        .unwrap_or_default();
    assert!(
        preview.contains(NEWER_WORDING),
        "WA471-SEARCH: people-list preview uses the newer body, got {preview:?}"
    );

    let timeline = person_timeline(&arch, berk, false, 20).unwrap();
    let hit = timeline
        .iter()
        .find(|h| h.message_id == keep)
        .unwrap_or_else(|| {
            panic!(
                "WA471-SEARCH: person show timeline missing {keep}, kinds {:?} hits {timeline:?}",
                conv_kinds(&arch)
            )
        });
    assert!(
        hit.snippet.contains("canim"),
        "WA471-SEARCH: person show uses the newer body, snippet {:?}",
        hit.snippet
    );
    let rows = person_timeline_rows(&arch, berk, false, 20, None).unwrap();
    let row = rows
        .iter()
        .find(|r| r.message_id == keep)
        .expect("timeline row");
    assert_eq!(row.body_text, NEWER_WORDING);
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-REIMPORT: importing the later zip again after Accept does not insert
/// a second message. The first zip's line does not insert one either.
#[test]
fn wa471_reimport_later_zip_does_not_insert() {
    let root = tmp_root();
    let android = berk_android(&root.join("a"), &["3/15/24, 10:00 AM - Berk: merhaba"]);
    let ios = berk_ios(
        &root.join("b"),
        &["[3/15/24, 10:00:18 AM] Berk: merhaba canim"],
        &[],
    );
    let (mut arch, _ada) = archive_with_self_and_ada(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);
    let (older, newer) = wording_pair_ids(&arch);
    let keep = today_keep_id(&arch, older, newer);
    assert_eq!(keep, older);
    let newer_hash = content_hash_of(&arch, newer);
    let keep_key = idempotency_of(&arch, keep);
    assert_ne!(content_hash_of(&arch, keep), newer_hash);
    let rid = only_wa_near_id(&arch);
    review_resolve(&mut arch, rid, true).unwrap();

    assert!(message_alive(&arch, keep) && !message_alive(&arch, newer));
    assert_eq!(
        body_of(&arch, keep),
        NEWER_WORDING,
        "WA471-REIMPORT: the survivor body is the newer sentence before reimport"
    );
    assert_eq!(
        revision_bodies(&arch, keep),
        vec![Some(OLDER_WORDING.into())]
    );
    assert_eq!(
        idempotency_of(&arch, keep),
        keep_key,
        "WA471-REIMPORT: the survivor idempotency key stays"
    );
    assert_eq!(
        content_hash_of(&arch, keep),
        newer_hash,
        "WA471-REIMPORT: the newer line's content hash is on the survivor"
    );

    let after_accept = user_rows(&arch).len();
    import_ios(&mut arch, &ios);
    assert_eq!(
        user_rows(&arch).len(),
        after_accept,
        "WA471-REIMPORT: importing the later zip again inserts no second message, got {:?}",
        user_rows(&arch)
    );
    assert_eq!(body_of(&arch, keep), NEWER_WORDING);
    assert!(message_alive(&arch, keep) && !message_alive(&arch, newer));
    assert!(
        wa_near_ids(&arch).is_empty(),
        "reimport must not open another wa_near row, got {:?}",
        review_list(&arch).unwrap()
    );

    import_android(&mut arch, &android);
    assert_eq!(
        user_rows(&arch).len(),
        after_accept,
        "reimport of the first zip's line inserts no second message, got {:?}",
        user_rows(&arch)
    );
    assert_eq!(body_of(&arch, keep), NEWER_WORDING);
    assert_eq!(idempotency_of(&arch, keep), keep_key);
    assert_eq!(
        revision_bodies(&arch, keep),
        vec![Some(OLDER_WORDING.into())]
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// iOS Berk `merhaba` at 10:00:40, then Android Berk `merhaba canim` at 10:00.
/// Accept. Survivor is the higher id. Body is `merhaba canim`, one revision
/// is `merhaba`, `edit_state` is `edited`, tombstone is 0.
fn accept_clock_inverted_pair(
    root: &Path,
) -> (interlace_core::db::Archive, i64, i64, PathBuf, PathBuf) {
    let first = berk_ios(
        &root.join("b"),
        &["[3/15/24, 10:00:40 AM] Berk: merhaba"],
        &[],
    );
    let later = berk_android(
        &root.join("a"),
        &["3/15/24, 10:00 AM - Berk: merhaba canim"],
    );
    let (mut arch, ada) = archive_with_self_and_ada(&root.join("arch"));
    import_ios(&mut arch, &first);
    import_android(&mut arch, &later);
    let (older, newer) = wording_pair_ids(&arch);
    let keep = today_keep_id(&arch, older, newer);
    assert_eq!(keep, newer, "survivor is the higher id, not the first zip");
    assert!(older < keep, "the first zip stays the lower id");
    let rid = only_wa_near_id(&arch);
    review_resolve(&mut arch, rid, true).unwrap();

    assert!(message_alive(&arch, keep), "survivor id is today's keep id");
    assert!(
        !message_alive(&arch, older),
        "the first zip's message id is gone"
    );
    assert_eq!(body_of(&arch, keep), NEWER_WORDING);
    assert_eq!(
        revision_bodies(&arch, keep),
        vec![Some(OLDER_WORDING.into())],
        "one revision is merhaba"
    );
    let (state, stone) = edit_state_of(&arch, keep);
    assert_eq!(state, "edited");
    assert_eq!(stone, 0, "not a tombstone");
    let rows = user_rows(&arch);
    assert_eq!(
        rows.len(),
        1,
        "clock-inverted Accept leaves one message, got {rows:?}"
    );
    assert_eq!(rows[0].0, keep, "the one row is the higher id");
    assert!(
        wa_near_ids(&arch).is_empty(),
        "Accept closes wa_near before either reimport, got {:?}",
        review_list(&arch).unwrap()
    );
    assert_ne!(
        ada,
        live_person_named(&arch, "Berk"),
        "Ada stays distinct from Berk"
    );
    (arch, keep, older, first, later)
}

fn assert_clock_reimport_stays(
    arch: &interlace_core::db::Archive,
    keep: i64,
    dropped: i64,
    label: &str,
) {
    let rows = user_rows(arch);
    let near = wa_near_ids(arch);
    assert_eq!(
        rows.len(),
        1,
        "{label}: row count stays 1, wa_near={near:?}, rows={rows:?}"
    );
    assert_eq!(rows[0].0, keep, "{label}: survivor id stays");
    assert!(
        message_alive(arch, keep) && !message_alive(arch, dropped),
        "{label}: survivor id stays and the deleted id stays gone"
    );
    assert_eq!(
        body_of(arch, keep),
        NEWER_WORDING,
        "{label}: body stays merhaba canim"
    );
    assert_eq!(
        revision_bodies(arch, keep),
        vec![Some(OLDER_WORDING.into())],
        "{label}: one revision stays merhaba"
    );
    let (state, stone) = edit_state_of(arch, keep);
    assert_eq!(state, "edited", "{label}: edit_state stays edited");
    assert_eq!(stone, 0, "{label}: not a tombstone");
    assert!(
        near.is_empty(),
        "{label}: no open wa_near, got {near:?}, rows={rows:?}"
    );
    assert_ne!(
        live_person_named(arch, "Ada"),
        live_person_named(arch, "Berk"),
        "{label}: Ada stays distinct from Berk"
    );
}

/// WA471-REIMPORT-CLOCK-FIRST: after that Accept, importing the first zip
/// again from the same path does not insert a second `merhaba` and does not
/// open `wa_near`. Row count, survivor id, body, and the one revision stay.
#[test]
fn wa471_reimport_clock_first_zip_does_not_insert() {
    let root = tmp_root();
    let (mut arch, keep, dropped, first, _later) = accept_clock_inverted_pair(&root);
    import_ios(&mut arch, &first);
    assert_clock_reimport_stays(&arch, keep, dropped, "WA471-REIMPORT-CLOCK-FIRST");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-REIMPORT-CLOCK-LATER: fresh Accept of that same pair, then the later
/// zip only, from the same path, before any first-zip reimport. Row count
/// stays 1. No `wa_near`. Body and the one revision stay.
#[test]
fn wa471_reimport_clock_later_zip_does_not_insert() {
    let root = tmp_root();
    let (mut arch, keep, dropped, _first, later) = accept_clock_inverted_pair(&root);
    import_android(&mut arch, &later);
    assert_clock_reimport_stays(&arch, keep, dropped, "WA471-REIMPORT-CLOCK-LATER");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA471-OTHER-PAIR: accepting one pair leaves the other open. The year count
/// drops the deleted message. A photo that arrived on that message follows
/// the survivor. The survivor id is today's keep id.
#[test]
fn wa471_other_pair_photo_follows_and_year_drops() {
    let root = tmp_root();
    let jpeg = b"\xFF\xD8fakejpeg";
    let android = android_zip(
        &root.join("a"),
        &[
            "3/15/24, 2:32 PM - Ada: linen note",
            "3/15/24, 2:32 PM - Ada: basket note",
        ],
    );
    let ios = ios_zip(
        &root.join("b"),
        &[
            "[3/15/24, 2:32:18 PM] Ada: canvas note <attached: IMG-0007.jpg>",
            "[3/15/24, 2:32:18 PM] Ada: cooler note",
        ],
        &[("IMG-0007.jpg", jpeg)],
    );
    let (mut arch, berk) = archive_with_self_and_berk(&root.join("arch"));
    import_android(&mut arch, &android);
    import_ios(&mut arch, &ios);

    let linen = open_pair_id(&arch, "linen note", "canvas note");
    let basket = open_pair_id(&arch, "basket note", "cooler note");
    let linen_id = message_id_with_body(&arch, "linen note");
    let canvas_ids = ids_containing(&arch, "canvas note");
    assert_eq!(canvas_ids.len(), 1, "canvas ids {canvas_ids:?}");
    let canvas_id = canvas_ids[0];
    let canvas_body = body_of(&arch, canvas_id);
    let basket_id = message_id_with_body(&arch, "basket note");
    let cooler_id = message_id_with_body(&arch, "cooler note");
    assert_eq!(today_keep_id(&arch, linen_id, canvas_id), linen_id);
    assert_eq!(
        photo_on(&arch, "IMG-0007.jpg"),
        canvas_id,
        "photo starts on the later message"
    );
    let before = ada_year_counts(&arch);
    assert!(!before.is_empty(), "Ada year row must exist before Accept");
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);

    review_resolve(&mut arch, linen, true).unwrap();

    assert!(
        message_alive(&arch, linen_id) && !message_alive(&arch, canvas_id),
        "WA471-OTHER-PAIR: survivor is today's keep id and the other id is gone"
    );
    assert!(message_alive(&arch, basket_id) && message_alive(&arch, cooler_id));
    assert_eq!(
        open_pair_id(&arch, "basket note", "cooler note"),
        basket,
        "WA471-OTHER-PAIR: the other pair stays open"
    );
    assert_eq!(wa_near_ids(&arch).len(), 1);
    assert_eq!(
        photo_on(&arch, "IMG-0007.jpg"),
        linen_id,
        "WA471-OTHER-PAIR: the photo follows the survivor"
    );
    let after = ada_year_counts(&arch);
    assert_eq!(after.len(), before.len(), "year rows stay");
    for ((flag, prev), (flag_after, next)) in before.iter().zip(after.iter()) {
        assert_eq!(flag_after, flag);
        assert_eq!(
            *next,
            prev - 1,
            "WA471-OTHER-PAIR: year count drops the deleted message (include_groups={flag})"
        );
    }
    assert_eq!(live_person_ids(&arch), people);
    assert_eq!(link_ops(&arch), ops, "people and link ops are unchanged");
    assert_berk_untouched(&arch, berk);
    assert_eq!(
        body_of(&arch, linen_id),
        canvas_body,
        "WA471-OTHER-PAIR: body_text is the later zip's sentence"
    );
    assert_eq!(
        revision_bodies(&arch, linen_id),
        vec![Some("linen note".into())],
        "the earlier sentence is the only revision"
    );
    let _ = std::fs::remove_dir_all(&root);
}
