//! #421 two WhatsApp exports of one chat.
//!
//! Matrix IDs (gate grep): WA421-A-NO-COLLIDE WA421-A-TITLE WA421-A-SECONDS
//! WA421-A-SENDER WA421-A-MEDIA-BODY WA421-A-SEQ title_split_two_conversations
//! two_sources_stay_two chat_match_not_person_review photo-on-kept-message
//! shared-line-one-row ambiguous-stays-two berk-stays-second-person
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
use interlace_core::{review_list, review_resolve, ImportOpts, SourceKind};

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
#[test]
fn wa_two_exports_near_accept_joins_messages_not_people() {
    let root = tmp_root();
    let (mut arch, berk, blue, red) = import_near_pair(&root);
    let rid = near_review_id(&arch);
    let people = live_person_ids(&arch);
    let ops = link_ops(&arch);

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
        "photo follows the kept id"
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

    let people = live_person_count(&arch);
    let ops = link_ops(&arch);
    review_resolve(&mut arch, linen, true).unwrap();

    let left = user_rows(&arch);
    assert_eq!(rows_with_body(&left, "linen note").len(), 1);
    assert!(
        rows_with_body(&left, "canvas note").is_empty(),
        "Accept joins only the linen/canvas pair, got {left:?}"
    );
    assert_eq!(rows_with_body(&left, "basket note").len(), 1);
    assert_eq!(rows_with_body(&left, "cooler note").len(), 1);
    let still = review_list(&arch).unwrap();
    let still_near: Vec<&serde_json::Value> = still
        .iter()
        .filter(|row| reason_text(row).contains("\"wa_near\":true"))
        .collect();
    assert_eq!(
        still_near.len(),
        1,
        "the other near row stays open, got {still:?}"
    );
    assert_eq!(open_pair_id(&arch, "basket note", "cooler note"), basket);

    review_resolve(&mut arch, basket, true).unwrap();
    let done = user_rows(&arch);
    assert_eq!(rows_with_body(&done, "basket note").len(), 1);
    assert!(
        rows_with_body(&done, "cooler note").is_empty(),
        "the later Accept joins the basket/cooler pair, got {done:?}"
    );
    assert_eq!(rows_with_body(&done, "linen note").len(), 1);
    assert_eq!(live_person_count(&arch), people, "people count stays put");
    assert_eq!(link_ops(&arch), ops, "Accept does not merge or link people");
    assert_berk_untouched(&arch, berk);
    let _ = std::fs::remove_dir_all(&root);
}

/// Accept of a near pair deletes the newest message. Derived rows follow.
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
    let people = live_person_count(&arch);
    review_resolve(&mut arch, rid, true).unwrap();

    let rows = user_rows(&arch);
    assert_eq!(rows_with_body(&rows, "ada blue note").len(), 1);
    assert!(
        rows_with_body(&rows, "ada red note").is_empty(),
        "Accept deletes the later near message, got {rows:?}"
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
