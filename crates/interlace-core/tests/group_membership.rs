//! Group membership intervals from en-US WhatsApp export lines.
//!
//! System lines have no `: ` between the name and the verb. User lines do.
//! Placeholders Ada / Berk / Self only.
//!
//! Matrix IDs (gate grep): WA423-LEAVE-INTERVAL WA423-JOIN-OPEN
//! WA423-NO-FAKE-BOUNDS WA423-PARTICIPANT-UNCHANGED WA423-RETARGET-LEAVE
//! WA423-SUBJECT-SKIP

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    conversation_participant_names, ConversationParticipantName, ImportOpts, SourceKind,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-gm423-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn opts() -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        ..ImportOpts::default()
    }
}

fn archive_with_self(root: &Path) -> interlace_core::db::Archive {
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
    arch
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

fn ios_chat(lines: &[&str]) -> String {
    let mut chat =
        String::from("[1/15/19, 9:00:00 AM] Messages and calls are end-to-end encrypted\n");
    for line in lines {
        chat.push_str(line);
        chat.push('\n');
    }
    chat
}

fn android_chat(lines: &[&str]) -> String {
    let mut chat = String::from("1/15/19, 9:00 AM - Messages and calls are end-to-end encrypted\n");
    for line in lines {
        chat.push_str(line);
        chat.push('\n');
    }
    chat
}

fn ios_zip(dir: &Path, lines: &[&str]) -> PathBuf {
    let path = dir.join("Picnic.zip");
    let chat = ios_chat(lines);
    write_zip(&path, &[("_chat.txt", chat.as_bytes())]);
    path
}

fn android_zip(dir: &Path, lines: &[&str]) -> PathBuf {
    let path = dir.join("android-picnic.zip");
    let chat = android_chat(lines);
    write_zip(&path, &[("Picnic.txt", chat.as_bytes())]);
    path
}

fn import_ios(arch: &mut interlace_core::db::Archive, zip: &Path) {
    arch.run_import(SourceKind::WhatsappIosZip, zip, &opts())
        .unwrap();
}

fn import_android(arch: &mut interlace_core::db::Archive, zip: &Path) {
    arch.run_import(SourceKind::WhatsappAndroidZip, zip, &opts())
        .unwrap();
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn group_id(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM conversations WHERE kind = 'group'",
            [],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("expected one group conversation: {e}"))
}

fn sent_at_containing(arch: &interlace_core::db::Archive, needle: &str) -> String {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT body_text, sent_at FROM messages
             WHERE body_text LIKE ?1 AND sent_at IS NOT NULL
             ORDER BY id",
        )
        .unwrap();
    let rows: Vec<(String, String)> = stmt
        .query_map([format!("%{needle}%")], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(
        rows.len(),
        1,
        "expected one dated message containing {needle}, got {rows:?}"
    );
    rows.into_iter().next().unwrap().1
}

fn names_at(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
    at: Option<&str>,
) -> Vec<ConversationParticipantName> {
    interlace_core::conversation_participant_names_at(arch, conversation_id, at)
        .unwrap_or_else(|e| panic!("conversation_participant_names_at: {e}"))
}

fn shows(rows: &[ConversationParticipantName], name: &str) -> bool {
    rows.iter()
        .any(|row| row.display_name.as_deref() == Some(name))
}

fn assert_identity_order(rows: &[ConversationParticipantName]) {
    let ids: Vec<i64> = rows.iter().map(|row| row.identity_id).collect();
    let mut sorted = ids.clone();
    sorted.sort();
    assert_eq!(ids, sorted, "participant names stay ordered by identity_id");
    let unique = {
        let mut seen = ids.clone();
        seen.dedup();
        seen.len() == ids.len()
    };
    assert!(unique, "two identities stay two identities: {ids:?}");
}

/// The public name row has no joined or left field. A new field fails this match.
fn assert_name_has_no_bounds(row: &ConversationParticipantName) {
    let ConversationParticipantName {
        identity_id: _,
        display_name: _,
        value: _,
        person_id: _,
    } = row;
}

struct Span {
    joined_at: Option<String>,
    left_at: Option<String>,
}

fn spans_for(arch: &interlace_core::db::Archive, conversation_id: i64, name: &str) -> Vec<Span> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT gm.joined_at, gm.left_at
             FROM group_membership gm
             JOIN identities i ON i.id = gm.identity_id
             WHERE gm.conversation_id = ?1 AND i.display_name = ?2
             ORDER BY gm.joined_at IS NULL, gm.joined_at, gm.left_at IS NULL, gm.left_at",
        )
        .unwrap();
    stmt.query_map(rusqlite::params![conversation_id, name], |r| {
        Ok(Span {
            joined_at: r.get(0)?,
            left_at: r.get(1)?,
        })
    })
    .unwrap()
    .map(|r| r.unwrap())
    .collect()
}

fn identity_rows_named(arch: &interlace_core::db::Archive, name: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM identities WHERE display_name = ?1",
            [name],
            |r| r.get(0),
        )
        .unwrap()
}

fn merge_person_events(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM identity_link_events WHERE op = 'merge_persons'",
    )
}

fn participant_count(arch: &interlace_core::db::Archive, conversation_id: i64, name: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT COUNT(*) FROM conversation_participants cp
             JOIN identities i ON i.id = cp.identity_id
             WHERE cp.conversation_id = ?1 AND i.display_name = ?2",
            rusqlite::params![conversation_id, name],
            |r| r.get(0),
        )
        .unwrap()
}

/// WA423-LEAVE-INTERVAL: Ada created the group, Berk was added, Ada left in 2020.
#[test]
fn ada_left_2020_included_in_2019_omitted_in_2024() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:00:00 AM] Ada created group \"Picnic\"",
            "[1/15/19, 10:05:00 AM] Berk was added",
            "[1/15/19, 10:06:00 AM] Berk: berk-in-2019",
            "[6/1/20, 10:00:00 AM] Ada left",
            "[3/1/24, 10:00:00 AM] Berk: berk-in-2024",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    let create_at = sent_at_containing(&arch, "Ada created group");
    let leave_at = sent_at_containing(&arch, "Ada left");
    let in_2019 = sent_at_containing(&arch, "berk-in-2019");
    let in_2024 = sent_at_containing(&arch, "berk-in-2024");
    assert!(
        create_at.starts_with("2019-"),
        "create instant stays in 2019, got {create_at}"
    );
    assert!(
        leave_at.starts_with("2020-"),
        "leave instant stays in 2020, got {leave_at}"
    );

    let early = names_at(&arch, cid, Some(&in_2019));
    let late = names_at(&arch, cid, Some(&in_2024));
    assert_identity_order(&early);
    assert_identity_order(&late);
    assert!(
        shows(&early, "Ada"),
        "2019 message includes Ada, got {early:?}"
    );
    assert!(
        shows(&early, "Berk"),
        "2019 message includes Berk, got {early:?}"
    );
    assert!(
        !shows(&late, "Ada"),
        "2024 message omits Ada after the 2020 leave, got {late:?}"
    );
    assert!(
        shows(&late, "Berk"),
        "2024 message includes Berk, got {late:?}"
    );
    assert!(
        !shows(&early, "Picnic") && !shows(&late, "Picnic"),
        "the quoted title is not a person"
    );

    let ada = spans_for(&arch, cid, "Ada");
    assert_eq!(ada.len(), 1, "Ada has one span, got {}", ada.len());
    assert_eq!(ada[0].left_at.as_deref(), Some(leave_at.as_str()));
    assert!(
        ada[0].joined_at.is_none() || ada[0].joined_at.as_deref() == Some(create_at.as_str()),
        "joined_at is null or the 2019 create instant, not an invented bound, got {:?}",
        ada[0].joined_at
    );
    assert_eq!(
        identity_rows_named(&arch, "Ada"),
        1,
        "no second identity is merged into Ada"
    );
    assert_eq!(identity_rows_named(&arch, "Picnic"), 0);
    assert_eq!(merge_person_events(&arch), 0);
    assert_eq!(
        participant_count(&arch, cid, "Ada"),
        0,
        "a system line does not insert a current participant row"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA423-NO-FAKE-BOUNDS: user lines only. Both dates return today's names.
#[test]
fn no_join_leave_returns_current_roster_and_no_intervals() {
    let root = tmp_root();
    let zip = android_zip(
        &root.join("zips"),
        &[
            "1/15/19, 10:06 AM - Ada: ada-plain",
            "1/15/19, 10:07 AM - Berk: berk-plain",
            "3/1/24, 10:00 AM - Ada: ada-later",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_android(&mut arch, &zip);
    let cid = group_id(&arch);
    let early_at = sent_at_containing(&arch, "ada-plain");
    let late_at = sent_at_containing(&arch, "ada-later");
    let current = conversation_participant_names(&arch, cid).unwrap();
    assert!(
        shows(&current, "Ada") && shows(&current, "Berk"),
        "{current:?}"
    );
    for row in &current {
        assert_name_has_no_bounds(row);
    }
    let early = names_at(&arch, cid, Some(&early_at));
    let late = names_at(&arch, cid, Some(&late_at));
    assert_identity_order(&early);
    assert_identity_order(&late);
    let ids = |rows: &[ConversationParticipantName]| -> Vec<i64> {
        rows.iter().map(|row| row.identity_id).collect()
    };
    assert_eq!(ids(&early), ids(&current));
    assert_eq!(ids(&late), ids(&current));
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM group_membership"), 0);
    let _ = std::fs::remove_dir_all(&root);
}

/// A message with null sent_at returns the current roster, not an empty list.
#[test]
fn null_sent_at_returns_current_roster() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:06:00 AM] Ada: ada-then",
            "[1/15/19, 10:07:00 AM] Berk: berk-then",
            "[6/1/20, 10:00:00 AM] Ada left",
            "[3/1/24, 10:00:00 AM] Berk: berk-later",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    arch.conn
        .execute(
            "INSERT INTO messages (
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key
             )
             SELECT conversation_id, source_id, import_run_id, NULL,
                    NULL, 'unknown', 'unknown', 'undated-row', 'gm-undated-row'
             FROM messages WHERE conversation_id = ?1 LIMIT 1",
            [cid],
        )
        .unwrap();
    let stored: Option<String> = arch
        .conn
        .query_row(
            "SELECT sent_at FROM messages WHERE body_text = 'undated-row'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(stored.is_none());
    let current = conversation_participant_names(&arch, cid).unwrap();
    assert!(!current.is_empty(), "current roster is not empty");
    assert!(shows(&current, "Ada") && shows(&current, "Berk"));
    let at_null = names_at(&arch, cid, stored.as_deref());
    let ids = |rows: &[ConversationParticipantName]| -> Vec<i64> {
        rows.iter().map(|row| row.identity_id).collect()
    };
    assert_eq!(ids(&at_null), ids(&current));
    let late = names_at(&arch, cid, Some(&sent_at_containing(&arch, "berk-later")));
    assert!(!shows(&late, "Ada"), "dated 2024 read still omits Ada");
    assert!(
        shows(&at_null, "Ada"),
        "null sent_at keeps Ada on the current roster"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Ada removed Berk sets left_at for Berk only. Ada stays.
#[test]
fn ada_removed_berk_sets_left_at_for_berk_only() {
    let root = tmp_root();
    let zip = android_zip(
        &root.join("zips"),
        &[
            "1/15/19, 10:06 AM - Ada: ada-before",
            "1/15/19, 10:07 AM - Berk: berk-before",
            "6/1/20, 10:00 AM - Ada removed Berk",
            "3/1/24, 10:00 AM - Ada: ada-after",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_android(&mut arch, &zip);
    let cid = group_id(&arch);
    let before = sent_at_containing(&arch, "berk-before");
    let removal = sent_at_containing(&arch, "Ada removed Berk");
    let after = sent_at_containing(&arch, "ada-after");
    assert!(removal.starts_with("2020-"), "{removal}");

    let early = names_at(&arch, cid, Some(&before));
    let late = names_at(&arch, cid, Some(&after));
    assert!(shows(&early, "Ada") && shows(&early, "Berk"), "{early:?}");
    assert!(
        shows(&late, "Ada"),
        "Ada stays after she removes Berk, got {late:?}"
    );
    assert!(
        !shows(&late, "Berk"),
        "Berk is out after removal, got {late:?}"
    );

    let berk = spans_for(&arch, cid, "Berk");
    assert_eq!(berk.len(), 1, "Berk has one leave span");
    assert!(berk[0].joined_at.is_none(), "unknown join stays null");
    assert_eq!(berk[0].left_at.as_deref(), Some(removal.as_str()));
    let ada = spans_for(&arch, cid, "Ada");
    assert!(
        ada.iter().all(|span| span.left_at.is_none()),
        "Ada removed Berk does not set left_at for Ada, got {} ada spans",
        ada.len()
    );
    assert_eq!(merge_person_events(&arch), 0);
    let _ = std::fs::remove_dir_all(&root);
}

/// WA423-JOIN-OPEN: add then leave is one closed span. A later add is a second span.
#[test]
fn join_then_leave_is_one_span_readd_is_second() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:00:00 AM] Ada added Berk",
            "[2/1/19, 10:00:00 AM] Berk: berk-in",
            "[2/1/19, 10:01:00 AM] Ada: ada-in",
            "[6/1/20, 10:00:00 AM] Berk left",
            "[1/1/21, 10:00:00 AM] Ada: ada-while-berk-out",
            "[3/1/24, 10:00:00 AM] Berk was added",
            "[3/2/24, 10:00:00 AM] Berk: berk-back",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    let added = sent_at_containing(&arch, "Ada added Berk");
    let left = sent_at_containing(&arch, "Berk left");
    let readded = sent_at_containing(&arch, "Berk was added");
    let berk = spans_for(&arch, cid, "Berk");
    assert_eq!(
        berk.len(),
        2,
        "leave closes the open join; readd is a second span"
    );
    assert_eq!(berk[0].joined_at.as_deref(), Some(added.as_str()));
    assert_eq!(berk[0].left_at.as_deref(), Some(left.as_str()));
    assert_eq!(berk[1].joined_at.as_deref(), Some(readded.as_str()));
    assert!(berk[1].left_at.is_none(), "the new span stays open");
    let ada = spans_for(&arch, cid, "Ada");
    assert!(
        ada.is_empty(),
        "Ada added Berk does not open a span for Ada"
    );

    assert!(shows(
        &names_at(&arch, cid, Some(&sent_at_containing(&arch, "berk-in"))),
        "Berk"
    ));
    assert!(!shows(
        &names_at(
            &arch,
            cid,
            Some(&sent_at_containing(&arch, "ada-while-berk-out"))
        ),
        "Berk"
    ));
    assert!(shows(
        &names_at(&arch, cid, Some(&sent_at_containing(&arch, "berk-back"))),
        "Berk"
    ));
    let _ = std::fs::remove_dir_all(&root);
}

/// WA423-SUBJECT-SKIP: a subject line writes no interval row.
#[test]
fn subject_change_writes_no_interval() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:00:00 AM] You changed the subject to Picnic",
            "[1/15/19, 10:06:00 AM] Ada: ada-subject-early",
            "[1/15/19, 10:07:00 AM] Berk: berk-subject",
            "[3/1/24, 10:00:00 AM] Ada: ada-subject-later",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM group_membership"), 0);
    assert_eq!(identity_rows_named(&arch, "Picnic"), 0);
    let early = names_at(
        &arch,
        cid,
        Some(&sent_at_containing(&arch, "ada-subject-early")),
    );
    let late = names_at(
        &arch,
        cid,
        Some(&sent_at_containing(&arch, "ada-subject-later")),
    );
    assert!(shows(&early, "Ada") && shows(&early, "Berk"));
    assert!(shows(&late, "Ada") && shows(&late, "Berk"));
    let _ = std::fs::remove_dir_all(&root);
}

/// The same zip twice does not double Ada's leave span.
#[test]
fn same_zip_twice_does_not_double_leave_span() {
    let root = tmp_root();
    let zip = android_zip(
        &root.join("zips"),
        &[
            "1/15/19, 10:00 AM - Ada created group \"Picnic\"",
            "1/15/19, 10:06 AM - Berk: berk-once",
            "6/1/20, 10:00 AM - Ada left",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_android(&mut arch, &zip);
    import_android(&mut arch, &zip);
    let cid = group_id(&arch);
    assert_eq!(spans_for(&arch, cid, "Ada").len(), 1);
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM group_membership"),
        spans_for(&arch, cid, "Ada").len() as i64 + spans_for(&arch, cid, "Berk").len() as i64
    );
    let ada = spans_for(&arch, cid, "Ada");
    assert_eq!(ada.len(), 1);
    assert!(ada[0].left_at.as_deref().unwrap_or("").starts_with("2020-"));
    let _ = std::fs::remove_dir_all(&root);
}

/// A line that names two people writes no interval row.
#[test]
fn two_names_on_one_line_write_no_interval() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:00:00 AM] Ada added Berk and Self",
            "[1/15/19, 10:06:00 AM] Ada: ada-multi",
            "[1/15/19, 10:07:00 AM] Berk: berk-multi",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM group_membership"), 0);
    assert!(spans_for(&arch, cid, "Berk").is_empty());
    assert!(spans_for(&arch, cid, "Ada").is_empty());
    assert!(spans_for(&arch, cid, "Self").is_empty());
    let rows = names_at(&arch, cid, Some(&sent_at_containing(&arch, "ada-multi")));
    assert!(shows(&rows, "Ada") && shows(&rows, "Berk"));
    let _ = std::fs::remove_dir_all(&root);
}

/// DM has no member list. A planted Berk who is not in the group stays put.
#[test]
fn dm_and_outside_berk_stay_unchanged() {
    let root = tmp_root();
    let mut arch = archive_with_self(&root.join("arch"));
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Berk', 0)",
            [],
        )
        .unwrap();
    let berk_id: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM persons WHERE display_name = 'Berk' AND tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();

    let dm_chat = "\
[1/15/19, 9:00:00 AM] Messages and calls are end-to-end encrypted
[1/15/19, 10:06:00 AM] Ada: dm-hello
[1/15/19, 10:07:00 AM] Self: dm-reply
";
    let dm_zip = root.join("zips").join("WhatsApp Chat - Ada.zip");
    write_zip(&dm_zip, &[("_chat.txt", dm_chat.as_bytes())]);
    import_ios(&mut arch, &dm_zip);
    let dm_id: i64 = arch
        .conn
        .query_row("SELECT id FROM conversations WHERE kind = 'dm'", [], |r| {
            r.get(0)
        })
        .unwrap();
    let dm_members_before: Vec<(i64, String)> = {
        let mut stmt = arch
            .conn
            .prepare(
                "SELECT cp.identity_id, cp.role FROM conversation_participants cp
                 WHERE cp.conversation_id = ?1 ORDER BY cp.identity_id",
            )
            .unwrap();
        stmt.query_map([dm_id], |r| Ok((r.get(0)?, r.get(1)?)))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };

    let group_zip = ios_zip(
        &root.join("zips"),
        &[
            "[2/2/19, 10:00:00 AM] Ada created group \"Picnic\"",
            "[2/2/19, 10:06:00 AM] Ada: group-note",
            "[2/2/19, 10:07:00 AM] Self: group-reply",
        ],
    );
    import_ios(&mut arch, &group_zip);
    let gid = group_id(&arch);
    assert_ne!(gid, dm_id);

    let (id, tomb): (i64, Option<String>) = arch
        .conn
        .query_row(
            "SELECT id, tombstoned_at FROM persons WHERE display_name = 'Berk'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(id, berk_id);
    assert!(tomb.is_none());
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM persons WHERE display_name = 'Berk' AND tombstoned_at IS NULL"
        ),
        1
    );
    assert_eq!(merge_person_events(&arch), 0);
    assert_eq!(participant_count(&arch, gid, "Berk"), 0);

    let dm_members_after: Vec<(i64, String)> = {
        let mut stmt = arch
            .conn
            .prepare(
                "SELECT cp.identity_id, cp.role FROM conversation_participants cp
                 WHERE cp.conversation_id = ?1 ORDER BY cp.identity_id",
            )
            .unwrap();
        stmt.query_map([dm_id], |r| Ok((r.get(0)?, r.get(1)?)))
            .unwrap()
            .map(|r| r.unwrap())
            .collect()
    };
    assert_eq!(dm_members_after, dm_members_before);
    let dm_at = sent_at_containing(&arch, "dm-hello");
    assert!(
        names_at(&arch, dm_id, Some(&dm_at)).is_empty(),
        "a DM has no member list"
    );
    assert!(
        names_at(&arch, dm_id, None).is_empty(),
        "a DM has no member list without a highlight"
    );
    let dm_spans: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM group_membership WHERE conversation_id = ?1",
            [dm_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(dm_spans, 0);
    let _ = std::fs::remove_dir_all(&root);
}

/// You were added sets joined_at on the identity that speaks as You.
#[test]
fn you_were_added_sets_joined_at_on_you_identity() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:00:00 AM] Ada created group \"Picnic\"",
            "[1/15/19, 10:04:00 AM] You were added",
            "[1/15/19, 10:06:00 AM] You: you-speaks",
            "[1/15/19, 10:07:00 AM] Ada: ada-speaks",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    let you_id: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE body_text = 'you-speaks'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let added = sent_at_containing(&arch, "You were added");
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT joined_at, left_at FROM group_membership
             WHERE conversation_id = ?1 AND identity_id = ?2",
        )
        .unwrap();
    let rows: Vec<(Option<String>, Option<String>)> = stmt
        .query_map(rusqlite::params![cid, you_id], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(rows.len(), 1, "one open join for you");
    assert_eq!(rows[0].0.as_deref(), Some(added.as_str()));
    assert!(rows[0].1.is_none());
    assert_eq!(
        identity_rows_named(&arch, "You") + identity_rows_named(&arch, "Self"),
        1
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// You left sets left_at for the existing you identity. Ada stays.
#[test]
fn you_left_sets_left_at_on_you_identity() {
    let root = tmp_root();
    let zip = android_zip(
        &root.join("zips"),
        &[
            "1/15/19, 10:00 AM - Ada created group \"Picnic\"",
            "1/15/19, 10:06 AM - You: you-before",
            "1/15/19, 10:07 AM - Ada: ada-before-you-left",
            "6/1/20, 10:00 AM - You left",
            "3/1/24, 10:00 AM - Ada: ada-after-you-left",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_android(&mut arch, &zip);
    let cid = group_id(&arch);
    let you_id: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE body_text = 'you-before'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let left = sent_at_containing(&arch, "You left");
    assert!(left.starts_with("2020-"), "{left}");
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT joined_at, left_at FROM group_membership
             WHERE conversation_id = ?1 AND identity_id = ?2
             ORDER BY joined_at IS NULL, joined_at",
        )
        .unwrap();
    let rows: Vec<(Option<String>, Option<String>)> = stmt
        .query_map(rusqlite::params![cid, you_id], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(rows.len(), 1);
    assert!(rows[0].0.is_none() || rows[0].0.as_deref().unwrap() < left.as_str());
    assert_eq!(rows[0].1.as_deref(), Some(left.as_str()));
    let you_name: String = arch
        .conn
        .query_row(
            "SELECT COALESCE(display_name, '') FROM identities WHERE id = ?1",
            [you_id],
            |r| r.get(0),
        )
        .unwrap();
    let early = names_at(
        &arch,
        cid,
        Some(&sent_at_containing(&arch, "ada-before-you-left")),
    );
    let late = names_at(
        &arch,
        cid,
        Some(&sent_at_containing(&arch, "ada-after-you-left")),
    );
    assert!(shows(&early, &you_name), "{early:?}");
    assert!(!shows(&late, &you_name), "{late:?}");
    assert!(shows(&late, "Ada"));
    let _ = std::fs::remove_dir_all(&root);
}

/// A system line with no sent_at writes nothing.
#[test]
fn undated_system_line_writes_no_interval() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[1/15/19, 10:06:00 AM] Ada: ada-dated",
            "[1/15/19, 10:07:00 AM] Berk: berk-dated",
            "Ada left",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM group_membership"), 0);
    let _ = std::fs::remove_dir_all(&root);
}

/// WA423-RETARGET-LEAVE: a later export's leave is stored on the kept conversation.
#[test]
fn later_export_leave_lands_on_kept_conversation() {
    let root = tmp_root();
    let first = android_zip(
        &root.join("a"),
        &[
            "1/15/19, 10:01 AM - Ada: note-from-ada",
            "1/15/19, 10:02 AM - Berk: note-from-berk",
            "1/15/19, 10:03 AM - Self: note-from-self",
        ],
    );
    let later = ios_zip(
        &root.join("b"),
        &[
            "[1/15/19, 10:01:18 AM] Ada: note-from-ada",
            "[1/15/19, 10:02:18 AM] Berk: note-from-berk",
            "[1/15/19, 10:03:18 AM] Self: note-from-self",
            "[6/1/20, 10:00:00 AM] Ada left",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_android(&mut arch, &first);
    let kept = group_id(&arch);
    import_ios(&mut arch, &later);
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM conversations"),
        1,
        "the later export stays on the kept conversation"
    );
    let ada = spans_for(&arch, kept, "Ada");
    assert_eq!(
        ada.len(),
        1,
        "the leave span is stored even when the system line is not copied"
    );
    assert!(
        ada[0].left_at.as_deref().unwrap_or("").starts_with("2020-"),
        "{:?}",
        ada[0].left_at
    );
    assert!(ada[0].joined_at.is_none());
    let _ = std::fs::remove_dir_all(&root);
}

/// An earlier join imported after a leave fills that span. It does not open a new one.
#[test]
fn earlier_join_fills_existing_leave() {
    let root = tmp_root();
    let zip = ios_zip(
        &root.join("zips"),
        &[
            "[6/1/20, 10:00:00 AM] Ada left",
            "[1/15/19, 10:00:00 AM] Ada created group \"Picnic\"",
            "[1/15/19, 10:06:00 AM] Berk: berk-in-2019",
            "[3/1/24, 10:00:00 AM] Berk: berk-in-2024",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch"));
    import_ios(&mut arch, &zip);
    let cid = group_id(&arch);
    let early = names_at(&arch, cid, Some(&sent_at_containing(&arch, "berk-in-2019")));
    let late = names_at(&arch, cid, Some(&sent_at_containing(&arch, "berk-in-2024")));
    assert!(
        shows(&early, "Ada"),
        "2019 still includes Ada, got {early:?}"
    );
    assert!(!shows(&late, "Ada"), "2024 omits Ada, got {late:?}");
    let ada = spans_for(&arch, cid, "Ada");
    assert_eq!(ada.len(), 1, "the join fills the leave span");
    assert!(ada[0]
        .joined_at
        .as_deref()
        .unwrap_or("")
        .starts_with("2019-"));
    assert!(ada[0].left_at.as_deref().unwrap_or("").starts_with("2020-"));
    let _ = std::fs::remove_dir_all(&root);
}

/// A leave that is not after the open join must not invert the span or drop Berk.
#[test]
fn leave_does_not_close_a_join_at_or_after_it() {
    let root = tmp_root();
    let same_minute = android_zip(
        &root.join("minute"),
        &[
            "1/15/19, 10:00 AM - Ada added Berk",
            "1/15/19, 10:00 AM - Berk left",
            "1/15/19, 10:05 AM - Ada: ada-after-minute",
        ],
    );
    let mut arch = archive_with_self(&root.join("arch-minute"));
    import_android(&mut arch, &same_minute);
    let cid = group_id(&arch);
    let after = names_at(
        &arch,
        cid,
        Some(&sent_at_containing(&arch, "ada-after-minute")),
    );
    assert!(
        shows(&after, "Berk"),
        "a same-minute leave must not drop Berk, got {after:?}"
    );

    let root2 = tmp_root();
    let inverted = ios_zip(
        &root2.join("zips"),
        &[
            "[3/1/21, 10:00:00 AM] Berk was added",
            "[6/1/20, 10:00:00 AM] Berk left",
            "[1/15/19, 10:06:00 AM] Ada: ada-in-2019",
            "[7/1/20, 10:00:00 AM] Ada: ada-after-leave",
            "[3/1/22, 10:00:00 AM] Ada: ada-after-rejoin",
        ],
    );
    let mut arch2 = archive_with_self(&root2.join("arch"));
    import_ios(&mut arch2, &inverted);
    let cid2 = group_id(&arch2);
    assert!(shows(
        &names_at(
            &arch2,
            cid2,
            Some(&sent_at_containing(&arch2, "ada-in-2019"))
        ),
        "Berk"
    ));
    assert!(!shows(
        &names_at(
            &arch2,
            cid2,
            Some(&sent_at_containing(&arch2, "ada-after-leave"))
        ),
        "Berk"
    ));
    assert!(shows(
        &names_at(
            &arch2,
            cid2,
            Some(&sent_at_containing(&arch2, "ada-after-rejoin"))
        ),
        "Berk"
    ));
    let _ = std::fs::remove_dir_all(&root);
    let _ = std::fs::remove_dir_all(&root2);
}
