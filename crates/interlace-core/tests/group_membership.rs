//! #423 group membership over time (locked mix).
//!
//! Matrix IDs (gate grep):
//! GM423-SCHEMA GM423-ASOF-LEAVE GM423-NO-EVENT-NO-FAKE-DATES
//! GM423-ADDED-JOIN-Y GM423-CREATED-JOIN-X GM423-REMOVED-LEAVE-Y
//! GM423-TWO-NAMES-NOOP GM423-NO-IDENTITY-MERGE GM423-SENDER-UNCHANGED
//! GM423-REIMPORT-IDEMPOTENT GM423-SENDER-ONLY-NO-INTERVAL GM423-HALF-OPEN
//! GM423-LATER-JOIN-FILLS-LEAVE GM423-LATER-LEAVE-KEEPS-REJOIN
//! GM423-SAME-TS-LEAVE GM423-LEAVE-CLOSES-ALL-OPEN
//!
//! Placeholders Ada / Berk / Self only. Drive import via public Archive API;
//! assert intervals and as-of presence via SQL on the open connection.
//! Do not call a non-exported as-of helper.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{conversation_participant_names, ImportOpts, SourceKind};
use rusqlite::OptionalExtension;

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

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn count_params(
    arch: &interlace_core::db::Archive,
    sql: &str,
    params: impl rusqlite::Params,
) -> i64 {
    arch.conn.query_row(sql, params, |r| r.get(0)).unwrap()
}

fn has_table(arch: &interlace_core::db::Archive, name: &str) -> bool {
    let n: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?1",
            [name],
            |r| r.get(0),
        )
        .unwrap();
    n > 0
}

fn has_column(arch: &interlace_core::db::Archive, table: &str, col: &str) -> bool {
    let sql = format!("SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name = ?1");
    let n: i64 = arch.conn.query_row(&sql, [col], |r| r.get(0)).unwrap();
    n > 0
}

fn schema_epoch(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row("SELECT schema_epoch FROM archive_meta", [], |r| r.get(0))
        .unwrap()
}

fn write_ios_zip(dir: &Path, stem: &str, chat: &str) -> PathBuf {
    std::fs::create_dir_all(dir).unwrap();
    let p = dir.join(format!("{stem}.zip"));
    let f = std::fs::File::create(&p).unwrap();
    let mut z = zip::ZipWriter::new(f);
    z.start_file(
        "_chat.txt",
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
    )
    .unwrap();
    z.write_all(chat.as_bytes()).unwrap();
    z.finish().unwrap();
    p
}

fn wa_opts() -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some("book-club".into()),
        ..ImportOpts::default()
    }
}

fn import_chat(arch: &mut interlace_core::db::Archive, zip: &Path) {
    arch.run_import(SourceKind::WhatsappIosZip, zip, &wa_opts())
        .expect("whatsapp import");
}

fn group_cid(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM conversations WHERE kind = 'group' ORDER BY id LIMIT 1",
            [],
            |r| r.get(0),
        )
        .expect("expected a group conversation")
}

fn identity_id_by_display(arch: &interlace_core::db::Archive, name: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM identities
             WHERE platform = 'whatsapp' AND kind = 'display_name' AND display_name = ?1
             ORDER BY id LIMIT 1",
            [name],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("identity {name}: {e}"))
}

fn message_id_by_body(arch: &interlace_core::db::Archive, body: &str) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM messages WHERE body_text = ?1 ORDER BY id LIMIT 1",
            [body],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("message {body}: {e}"))
}

fn message_sent_at(arch: &interlace_core::db::Archive, message_id: i64) -> Option<String> {
    arch.conn
        .query_row(
            "SELECT sent_at FROM messages WHERE id = ?1",
            [message_id],
            |r| r.get(0),
        )
        .unwrap()
}

/// Spec half-open presence for identity at time t:
/// in at joined_at, out at left_at.
fn span_covers(joined_at: Option<&str>, left_at: Option<&str>, t: &str) -> bool {
    let in_ok = match joined_at {
        None => true,
        Some(j) => j <= t,
    };
    let out_ok = match left_at {
        None => true,
        Some(l) => l > t,
    };
    in_ok && out_ok
}

/// Expected as-of roster from locked mix: no membership rows → current CP list;
/// with rows → covering spans union identities on CP with zero spans.
fn names_present_at(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
    at: &str,
) -> Vec<String> {
    // No table yet → current undated roster (fail-today path for as-of behavior).
    if !has_table(arch, "group_membership") {
        return conversation_participant_names(arch, conversation_id)
            .unwrap()
            .into_iter()
            .map(|p| p.display_name.unwrap_or(p.value))
            .collect();
    }
    let n_spans: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM group_membership WHERE conversation_id = ?1",
            [conversation_id],
            |r| r.get(0),
        )
        .unwrap_or(0);
    if n_spans == 0 {
        return conversation_participant_names(arch, conversation_id)
            .unwrap()
            .into_iter()
            .map(|p| p.display_name.unwrap_or(p.value))
            .collect();
    }

    let mut stmt = arch
        .conn
        .prepare(
            "SELECT i.display_name, i.value_raw, gm.joined_at, gm.left_at
             FROM group_membership gm
             JOIN identities i ON i.id = gm.identity_id
             WHERE gm.conversation_id = ?1",
        )
        .expect("group_membership select");
    let mut covered = std::collections::BTreeSet::new();
    let mut spanned = std::collections::BTreeSet::new();
    let rows = stmt
        .query_map([conversation_id], |r| {
            Ok((
                r.get::<_, Option<String>>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, Option<String>>(2)?,
                r.get::<_, Option<String>>(3)?,
            ))
        })
        .unwrap();
    for row in rows {
        let (display, value, joined, left) = row.unwrap();
        let label = display.unwrap_or(value);
        spanned.insert(label.clone());
        if span_covers(joined.as_deref(), left.as_deref(), at) {
            covered.insert(label);
        }
    }

    // Persons with no span stay on the current list.
    let current = conversation_participant_names(arch, conversation_id).unwrap();
    for p in current {
        let label = p.display_name.unwrap_or(p.value);
        if !spanned.contains(&label) {
            covered.insert(label);
        }
    }
    covered.into_iter().collect()
}

fn membership_rows(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
) -> Vec<(String, Option<String>, Option<String>)> {
    if !has_table(arch, "group_membership") {
        return Vec::new();
    }
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT COALESCE(i.display_name, i.value_raw), gm.joined_at, gm.left_at
             FROM group_membership gm
             JOIN identities i ON i.id = gm.identity_id
             WHERE gm.conversation_id = ?1
             ORDER BY i.display_name, gm.joined_at, gm.left_at",
        )
        .expect("group_membership select");
    let rows = stmt
        .query_map([conversation_id], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, Option<String>>(2)?,
            ))
        })
        .unwrap();
    rows.map(|r| r.unwrap()).collect()
}

fn membership_count(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
    identity_id: Option<i64>,
) -> i64 {
    if !has_table(arch, "group_membership") {
        return 0;
    }
    match identity_id {
        Some(iid) => count_params(
            arch,
            "SELECT COUNT(*) FROM group_membership
             WHERE conversation_id = ?1 AND identity_id = ?2",
            rusqlite::params![conversation_id, iid],
        ),
        None => count_params(
            arch,
            "SELECT COUNT(*) FROM group_membership WHERE conversation_id = ?1",
            [conversation_id],
        ),
    }
}

fn membership_bound(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
    identity_id: i64,
    col: &str,
) -> Option<String> {
    if !has_table(arch, "group_membership") {
        return None;
    }
    let sql = format!(
        "SELECT {col} FROM group_membership
         WHERE conversation_id = ?1 AND identity_id = ?2
         ORDER BY id DESC LIMIT 1"
    );
    arch.conn
        .query_row(&sql, rusqlite::params![conversation_id, identity_id], |r| {
            r.get(0)
        })
        .optional()
        .unwrap()
        .flatten()
}

fn ada_spans_for(
    arch: &interlace_core::db::Archive,
    conversation_id: i64,
) -> Vec<(Option<String>, Option<String>)> {
    if !has_table(arch, "group_membership") {
        return Vec::new();
    }
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT gm.joined_at, gm.left_at
             FROM group_membership gm
             JOIN identities i ON i.id = gm.identity_id
             WHERE gm.conversation_id = ?1 AND i.display_name = 'Ada'",
        )
        .expect("group_membership select");
    stmt.query_map([conversation_id], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn require_group_membership_schema(arch: &interlace_core::db::Archive) {
    assert_eq!(
        schema_epoch(arch),
        1,
        "schema_epoch stays 1 for additive group_membership"
    );
    assert!(
        has_table(arch, "group_membership"),
        "GM423-SCHEMA: group_membership table must exist after migrate (0006)"
    );
    assert!(
        has_column(arch, "group_membership", "conversation_id"),
        "group_membership.conversation_id required"
    );
    assert!(
        has_column(arch, "group_membership", "identity_id"),
        "group_membership.identity_id required"
    );
    assert!(
        has_column(arch, "group_membership", "joined_at"),
        "group_membership.joined_at required"
    );
    assert!(
        has_column(arch, "group_membership", "left_at"),
        "group_membership.left_at required"
    );
    // conversation_participants stays undated (not approach B).
    assert!(
        !has_column(arch, "conversation_participants", "joined_at"),
        "conversation_participants must stay undated (no joined_at)"
    );
    assert!(
        !has_column(arch, "conversation_participants", "left_at"),
        "conversation_participants must stay undated (no left_at)"
    );
}

/// GM423-SCHEMA: additive group_membership table; epoch stays 1; CP undated.
#[test]
fn group_membership_schema_via_0006_epoch_stays_1() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    require_group_membership_schema(&arch);
    let v6: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 6 OR name LIKE '0006%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(v6 >= 1, "0006_* migration must be applied; got none");
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-ASOF-LEAVE: Ada left in 2020 → present at 2019 message, absent at 2024.
#[test]
fn membership_ada_leave_2019_in_2024_out() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 10:00:01] Berk created group \"Book Club\"
[2019-06-01, 10:00:02] Berk added Ada
[2019-06-01, 10:00:03] Ada: hello before leave
[2019-06-01, 10:00:04] Berk: hi ada
[2020-03-15, 12:00:00] Ada left
[2024-01-10, 09:00:00] Berk: hello after leave
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Book Club", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    // Behavior first when schema is absent (schema lock is its own test).
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let mid_2019 = message_id_by_body(&arch, "hello before leave");
    let mid_2024 = message_id_by_body(&arch, "hello after leave");
    let at_2019 = message_sent_at(&arch, mid_2019).expect("2019 message sent_at");
    let at_2024 = message_sent_at(&arch, mid_2024).expect("2024 message sent_at");
    assert!(
        at_2019.starts_with("2019"),
        "2019 message sent_at={at_2019}"
    );
    assert!(
        at_2024.starts_with("2024"),
        "2024 message sent_at={at_2024}"
    );

    // Current undated roster still includes Ada (ever-member via CP).
    let current = conversation_participant_names(&arch, cid).unwrap();
    assert!(
        current
            .iter()
            .any(|p| p.display_name.as_deref() == Some("Ada")),
        "conversation_participants ever-set still includes Ada"
    );

    if has_table(&arch, "group_membership") {
        let ada_spans = ada_spans_for(&arch, cid);
        assert!(
            !ada_spans.is_empty(),
            "GM423-ASOF-LEAVE: Ada must have a group_membership span after 'Ada left'"
        );
        assert!(
            ada_spans
                .iter()
                .any(|(_, left)| { left.as_ref().is_some_and(|l| l.starts_with("2020")) }),
            "GM423-ASOF-LEAVE: Ada left_at must be in 2020, got {ada_spans:?}"
        );
    }

    let at_2019_names = names_present_at(&arch, cid, &at_2019);
    assert!(
        at_2019_names.iter().any(|n| n == "Ada"),
        "GM423-ASOF-LEAVE: 2019 message must still list Ada, got {at_2019_names:?}"
    );

    // Fail-today without intervals: undated CP still lists Ada for 2024.
    // When the table exists, names_present_at keeps the SQL span checks above.
    let at_2024_names = if has_table(&arch, "group_membership") {
        names_present_at(&arch, cid, &at_2024)
    } else {
        conversation_participant_names(&arch, cid)
            .unwrap()
            .into_iter()
            .map(|p| p.display_name.unwrap_or(p.value))
            .collect::<Vec<_>>()
    };
    assert!(
        at_2024_names.iter().all(|n| n != "Ada"),
        "GM423-ASOF-LEAVE: 2024 roster still contains Ada, got {at_2024_names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-NO-EVENT-NO-FAKE-DATES: no join/leave lines → current list, no invented dates.
#[test]
fn membership_no_events_current_list_no_fake_dates() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Ada: note one
[2024-03-15, 14:32:20] Berk: note two
[2024-03-15, 14:32:21] Ada: note three
";
    let zip = write_ios_zip(&root.join("zips"), "random-export-club", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let current = conversation_participant_names(&arch, cid).unwrap();
    let labels: Vec<String> = current
        .iter()
        .map(|p| p.display_name.clone().unwrap_or_else(|| p.value.clone()))
        .collect();
    assert!(
        labels.iter().any(|n| n == "Ada"),
        "no-event group still lists Ada on current roster: {labels:?}"
    );
    assert!(
        labels.iter().any(|n| n == "Berk"),
        "no-event group still lists Berk on current roster: {labels:?}"
    );

    if has_table(&arch, "group_membership") {
        let n_spans = membership_count(&arch, cid, None);
        assert_eq!(
            n_spans, 0,
            "GM423-NO-EVENT-NO-FAKE-DATES: no join/leave evidence → zero group_membership rows, got {n_spans}"
        );
        let non_null = count(
            &arch,
            "SELECT COUNT(*) FROM group_membership
             WHERE joined_at IS NOT NULL OR left_at IS NOT NULL",
        );
        assert_eq!(
            non_null, 0,
            "GM423-NO-EVENT-NO-FAKE-DATES: must not invent joined/left timestamps"
        );
    } else {
        // Fail-today: no interval store yet — still lock undated CP has no fake dates.
        assert!(
            !has_column(&arch, "conversation_participants", "joined_at"),
            "GM423-NO-EVENT-NO-FAKE-DATES: conversation_participants must stay undated"
        );
        assert!(
            !has_column(&arch, "conversation_participants", "left_at"),
            "GM423-NO-EVENT-NO-FAKE-DATES: conversation_participants must stay undated"
        );
    }
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-ADDED-JOIN-Y: `X added Y` records join for Y only (not actor X).
#[test]
fn membership_added_records_join_for_y_only() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada
[2024-03-15, 14:32:21] Ada: hi
[2024-03-15, 14:32:22] Berk: welcome
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Club", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let ada_iid = identity_id_by_display(&arch, "Ada");
    let berk_iid = identity_id_by_display(&arch, "Berk");

    let ada_join = membership_bound(&arch, cid, ada_iid, "joined_at");
    assert!(
        ada_join.is_some(),
        "GM423-ADDED-JOIN-Y: 'Berk added Ada' must set joined_at for Ada"
    );

    // Actor Berk may have a create-group join, but not from the added line alone.
    // The added line must not create an *extra* join-only span for Berk beyond create.
    let berk_rows = membership_count(&arch, cid, Some(berk_iid));
    // Berk gets at most one span from "created group" — not a second from "added".
    assert!(
        berk_rows <= 1,
        "GM423-ADDED-JOIN-Y: added line must not give Berk an extra span (rows={berk_rows})"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-CREATED-JOIN-X: `X created group …` records join for X.
#[test]
fn membership_created_group_records_join_for_x() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk: opening
[2024-03-15, 14:32:21] Ada: here
";
    let zip = write_ios_zip(&root.join("zips"), "random-club-export", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let berk_iid = identity_id_by_display(&arch, "Berk");
    let joined = membership_bound(&arch, cid, berk_iid, "joined_at");
    assert!(
        joined.is_some(),
        "GM423-CREATED-JOIN-X: 'Berk created group' must set joined_at for Berk"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-REMOVED-LEAVE-Y: `X removed Y` records leave for Y.
#[test]
fn membership_removed_records_leave_for_y() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada
[2024-03-15, 14:32:21] Ada: hi
[2024-03-16, 10:00:00] Berk removed Ada
[2024-03-16, 11:00:00] Berk: alone now
";
    let zip = write_ios_zip(&root.join("zips"), "random-removed-club", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let ada_iid = identity_id_by_display(&arch, "Ada");
    let left = membership_bound(&arch, cid, ada_iid, "left_at");
    assert!(
        left.is_some(),
        "GM423-REMOVED-LEAVE-Y: 'Berk removed Ada' must set left_at for Ada"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-TWO-NAMES-NOOP: a line naming two people records nothing.
#[test]
fn membership_two_names_on_line_records_nothing() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada and Self
[2024-03-15, 14:32:21] Ada: hi
[2024-03-15, 14:32:22] Berk: hi
";
    let zip = write_ios_zip(&root.join("zips"), "random-multi-add", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    // Multi-name "added" must not create Ada join from that line.
    // Ada may still lack a span (sender-only) — that's fine.
    // The key lock: the multi-name line itself stores nothing for Ada/Self joins.
    // Compare against a baseline: only Berk's created-group span is allowed from system lines.
    let rows = membership_rows(&arch, cid);
    let ada_joins: Vec<_> = rows
        .iter()
        .filter(|(n, j, _)| n == "Ada" && j.is_some())
        .collect();
    assert!(
        ada_joins.is_empty(),
        "GM423-TWO-NAMES-NOOP: multi-name added line must not record Ada join, got {rows:?}"
    );
    let self_joins: Vec<_> = rows
        .iter()
        .filter(|(n, j, _)| n == "Self" && j.is_some())
        .collect();
    assert!(
        self_joins.is_empty(),
        "GM423-TWO-NAMES-NOOP: multi-name added line must not record Self join, got {rows:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-NO-IDENTITY-MERGE: import with join/leave does not merge Ada and Berk.
#[test]
fn membership_no_identity_merge_ada_berk() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada
[2024-03-15, 14:32:21] Ada: hello
[2024-03-15, 14:32:22] Berk: hi
[2024-03-16, 12:00:00] Ada left
";
    let zip = write_ios_zip(&root.join("zips"), "random-no-merge", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);

    let ada_persons = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND display_name = 'Ada'",
    );
    let berk_persons = count(
        &arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND display_name = 'Berk'",
    );
    assert!(ada_persons >= 1, "Ada person must exist");
    assert!(berk_persons >= 1, "Berk person must exist");
    assert_ne!(
        identity_id_by_display(&arch, "Ada"),
        identity_id_by_display(&arch, "Berk"),
        "GM423-NO-IDENTITY-MERGE: Ada and Berk stay distinct identities"
    );

    let merges = count(
        &arch,
        "SELECT COUNT(*) FROM identity_link_events WHERE op = 'merge_persons'",
    );
    assert_eq!(
        merges, 0,
        "GM423-NO-IDENTITY-MERGE: membership apply must not merge_persons (got {merges})"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// I4 / GM423-SENDER-UNCHANGED: membership import does not rewrite sender_identity_id.
#[test]
fn membership_sender_identity_id_unchanged() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada
[2024-03-15, 14:32:21] Ada: hello sender lock
[2024-03-15, 14:32:22] Berk: hi sender lock
[2024-03-16, 12:00:00] Ada left
";
    let zip = write_ios_zip(&root.join("zips"), "random-sender-lock", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);

    let ada_msg = message_id_by_body(&arch, "hello sender lock");
    let berk_msg = message_id_by_body(&arch, "hi sender lock");
    let ada_sender: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id = ?1",
            [ada_msg],
            |r| r.get(0),
        )
        .unwrap();
    let berk_sender: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id = ?1",
            [berk_msg],
            |r| r.get(0),
        )
        .unwrap();
    let ada_iid = identity_id_by_display(&arch, "Ada");
    let berk_iid = identity_id_by_display(&arch, "Berk");
    assert_eq!(
        ada_sender, ada_iid,
        "GM423-SENDER-UNCHANGED: Ada message sender_identity_id must stay Ada's identity"
    );
    assert_eq!(
        berk_sender, berk_iid,
        "GM423-SENDER-UNCHANGED: Berk message sender_identity_id must stay Berk's identity"
    );
    assert_ne!(ada_sender, berk_sender);

    // Re-import same zip — senders stay bitwise stable.
    import_chat(&mut arch, &zip);
    let ada_sender2: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id = ?1",
            [ada_msg],
            |r| r.get(0),
        )
        .unwrap();
    let berk_sender2: i64 = arch
        .conn
        .query_row(
            "SELECT sender_identity_id FROM messages WHERE id = ?1",
            [berk_msg],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        ada_sender2, ada_sender,
        "GM423-SENDER-UNCHANGED: re-import must not rewrite Ada sender_identity_id"
    );
    assert_eq!(
        berk_sender2, berk_sender,
        "GM423-SENDER-UNCHANGED: re-import must not rewrite Berk sender_identity_id"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-REIMPORT-IDEMPOTENT: same leave line again does not insert a second span.
#[test]
fn membership_reimport_same_leave_no_second_span() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 10:00:01] Berk created group \"Book Club\"
[2019-06-01, 10:00:02] Berk added Ada
[2019-06-01, 10:00:03] Ada: before
[2020-03-15, 12:00:00] Ada left
[2024-01-10, 09:00:00] Berk: after
";
    let zip = write_ios_zip(&root.join("zips"), "random-reimport-leave", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let ada_iid = identity_id_by_display(&arch, "Ada");
    let n_first = membership_count(&arch, cid, Some(ada_iid));
    assert!(
        n_first >= 1,
        "GM423-REIMPORT-IDEMPOTENT: first import must store Ada span"
    );

    import_chat(&mut arch, &zip);
    let n_second = membership_count(&arch, cid, Some(ada_iid));
    assert_eq!(
        n_second, n_first,
        "GM423-REIMPORT-IDEMPOTENT: same leave line again must not insert a second span ({n_first} -> {n_second})"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-SENDER-ONLY-NO-INTERVAL: only sends, no system line → no interval row; stays on current list.
#[test]
fn membership_sender_only_no_interval_stays_on_current_list() {
    let root = tmp_root();
    // Berk creates group and adds Ada; Self only sends — no system line naming Self.
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Berk created group \"Club\"
[2024-03-15, 14:32:20] Berk added Ada
[2024-03-15, 14:32:21] Ada: hi
[2024-03-15, 14:32:22] Berk: hi
[2024-03-15, 14:32:23] Self: only sending no system line
";
    let zip = write_ios_zip(&root.join("zips"), "random-sender-only", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    // Seed owner so Self can resolve if export uses You — here Self is a display name sender.
    arch.conn
        .execute(
            "UPDATE archive_meta SET owner_display_name = 'Owner' WHERE id = 1",
            [],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Owner', 1)",
            [],
        )
        .unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let current = conversation_participant_names(&arch, cid).unwrap();
    assert!(
        current
            .iter()
            .any(|p| p.display_name.as_deref() == Some("Self")),
        "GM423-SENDER-ONLY-NO-INTERVAL: Self who only sent must remain on current participant list"
    );

    let self_iid = identity_id_by_display(&arch, "Self");
    let self_spans = membership_count(&arch, cid, Some(self_iid));
    assert_eq!(
        self_spans, 0,
        "GM423-SENDER-ONLY-NO-INTERVAL: sender-only Self must have zero interval rows, got {self_spans}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-HALF-OPEN: in at joined_at, out at left_at (planted spans).
#[test]
fn membership_half_open_in_at_joined_out_at_left() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let table_ok = has_table(&arch, "group_membership");
    if table_ok {
        require_group_membership_schema(&arch);
    }

    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
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
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Berk', 'berk', 'Berk')",
            [],
        )
        .unwrap();
    let berk_iid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('whatsapp', 'group', 'whatsapp:club', 'Club')",
            [],
        )
        .unwrap();
    let cid = arch.conn.last_insert_rowid();
    for iid in [ada_iid, berk_iid] {
        arch.conn
            .execute(
                "INSERT INTO conversation_participants(conversation_id, identity_id, role)
                 VALUES (?1, ?2, 'member')",
                rusqlite::params![cid, iid],
            )
            .unwrap();
    }

    let join = "2020-01-01T10:00:00Z";
    let leave = "2020-06-01T12:00:00Z";
    if table_ok {
        arch.conn
            .execute(
                "INSERT INTO group_membership(conversation_id, identity_id, joined_at, left_at)
                 VALUES (?1, ?2, ?3, ?4)",
                rusqlite::params![cid, ada_iid, join, leave],
            )
            .expect("insert group_membership span");
        // Berk: open-ended join only.
        arch.conn
            .execute(
                "INSERT INTO group_membership(conversation_id, identity_id, joined_at, left_at)
                 VALUES (?1, ?2, ?3, NULL)",
                rusqlite::params![cid, berk_iid, join],
            )
            .unwrap();
    }

    // Exactly at joined_at → in.
    assert!(
        span_covers(Some(join), Some(leave), join),
        "GM423-HALF-OPEN: in at joined_at"
    );
    let at_join = names_present_at(&arch, cid, join);
    assert!(
        at_join.iter().any(|n| n == "Ada"),
        "GM423-HALF-OPEN: Ada present at joined_at, got {at_join:?}"
    );

    // Exactly at left_at → out.
    assert!(
        !span_covers(Some(join), Some(leave), leave),
        "GM423-HALF-OPEN: out at left_at"
    );
    // Fail-today without table: undated CP still lists Ada at left_at.
    let at_leave = names_present_at(&arch, cid, leave);
    assert!(
        at_leave.iter().all(|n| n != "Ada"),
        "GM423-HALF-OPEN: Ada absent at left_at, got {at_leave:?}"
    );

    // Mid-span → in; after leave → out.
    let mid = names_present_at(&arch, cid, "2020-03-01T00:00:00Z");
    assert!(mid.iter().any(|n| n == "Ada"), "mid-span Ada in: {mid:?}");
    let after = names_present_at(&arch, cid, "2020-07-01T00:00:00Z");
    assert!(
        after.iter().all(|n| n != "Ada"),
        "after leave Ada out: {after:?}"
    );
    // Berk still present after Ada left.
    assert!(
        after.iter().any(|n| n == "Berk"),
        "Berk open left_at stays after Ada leave: {after:?}"
    );

    let _ = run; // silence if unused on some paths
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-LATER-JOIN-FILLS-LEAVE: a later `Berk added Ada` fills a leave-only span.
/// Shorter export stored only `Ada left`. The same chat's later export repeats
/// that leave and adds the earlier join. After Tleave Ada is out; between
/// Tjoin and Tleave Ada is in. One kept conversation.
#[test]
fn membership_later_join_fills_leave_only_span() {
    let root = tmp_root();
    let shorter = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 10:05:00] Ada: between join and leave
[2019-06-01, 10:06:00] Berk: still in
[2020-03-15, 12:00:00] Ada left
[2024-01-10, 09:00:00] Berk: after leave
";
    let later = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 10:00:02] Berk added Ada
[2019-06-01, 10:05:00] Ada: between join and leave
[2019-06-01, 10:06:00] Berk: still in
[2020-03-15, 12:00:00] Ada left
[2024-01-10, 09:00:00] Berk: after leave
";
    let zip_short = write_ios_zip(&root.join("zips"), "shorter-book-club", shorter);
    let zip_later = write_ios_zip(&root.join("zips"), "later-book-club", later);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip_short);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let n_conv = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv, 1,
        "shorter export must keep one conversation, got {n_conv}"
    );
    if has_table(&arch, "group_membership") {
        let ada_spans = ada_spans_for(&arch, cid);
        assert!(
            ada_spans.iter().any(|(joined, left)| {
                joined.is_none() && left.as_ref().is_some_and(|l| l.starts_with("2020"))
            }),
            "GM423-LATER-JOIN-FILLS-LEAVE: shorter export must store Ada (joined_at NULL, left_at Tleave), got {ada_spans:?}"
        );
    }

    import_chat(&mut arch, &zip_later);
    let n_conv_later = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv_later, 1,
        "later export of the same chat must stay on the kept conversation, got {n_conv_later}"
    );
    let cid = group_cid(&arch);

    let mid_id = message_id_by_body(&arch, "between join and leave");
    let after_id = message_id_by_body(&arch, "after leave");
    let at_mid = message_sent_at(&arch, mid_id).expect("between message sent_at");
    let at_after = message_sent_at(&arch, after_id).expect("after message sent_at");
    assert!(
        at_mid.starts_with("2019"),
        "between message sent_at={at_mid}"
    );
    assert!(
        at_after.starts_with("2024"),
        "after message sent_at={at_after}"
    );

    let mid_names = names_present_at(&arch, cid, &at_mid);
    assert!(
        mid_names.iter().any(|n| n == "Ada"),
        "GM423-LATER-JOIN-FILLS-LEAVE: message between Tjoin and Tleave must list Ada, got {mid_names:?}"
    );

    let after_names = names_present_at(&arch, cid, &at_after);
    assert!(
        after_names.iter().all(|n| n != "Ada"),
        "GM423-LATER-JOIN-FILLS-LEAVE: message after Tleave must not list Ada, got {after_names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-LATER-LEAVE-KEEPS-REJOIN: a later `Ada left` at T2 must not close a
/// rejoin that already started at T3 > T2. Shorter export stored only
/// `Berk added Ada` (joined_at T3, left_at NULL). The same chat's later export
/// adds that earlier leave and repeats the add. Ada stays listed after T3.
/// No row is (joined_at T3, left_at T2).
#[test]
fn membership_later_leave_does_not_close_later_rejoin() {
    let root = tmp_root();
    // T3 only. No leave in this file, so the kept span stays open.
    let shorter = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 12:00:00] Berk added Ada
[2019-06-01, 12:05:00] Ada: after rejoin
[2019-06-01, 12:06:00] Berk: still here
";
    // T2 < T3, then the same add again.
    let later = "\
[2019-06-01, 10:00:00] Messages and calls are end-to-end encrypted
[2019-06-01, 10:30:00] Ada left
[2019-06-01, 10:30:00] Berk: at leave instant
[2019-06-01, 11:00:00] Berk: between leave and rejoin
[2019-06-01, 12:00:00] Berk added Ada
[2019-06-01, 12:05:00] Ada: after rejoin
[2019-06-01, 12:06:00] Berk: still here
";
    let zip_short = write_ios_zip(&root.join("zips"), "shorter-rejoin-club", shorter);
    let zip_later = write_ios_zip(&root.join("zips"), "later-rejoin-club", later);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip_short);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let n_conv = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv, 1,
        "shorter export must keep one conversation, got {n_conv}"
    );
    let t3 = if has_table(&arch, "group_membership") {
        let ada_spans = ada_spans_for(&arch, cid);
        let open = ada_spans
            .iter()
            .find(|(joined, left)| joined.is_some() && left.is_none());
        assert!(
            open.is_some(),
            "GM423-LATER-LEAVE-KEEPS-REJOIN: shorter export must store Ada (joined_at T3, left_at NULL), got {ada_spans:?}"
        );
        open.unwrap().0.clone().unwrap()
    } else {
        String::new()
    };

    import_chat(&mut arch, &zip_later);
    let n_conv_later = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv_later, 1,
        "later export of the same chat must stay on the kept conversation, got {n_conv_later}"
    );
    let cid = group_cid(&arch);

    let after_id = message_id_by_body(&arch, "after rejoin");
    let at_after = message_sent_at(&arch, after_id).expect("after rejoin sent_at");
    assert!(
        at_after.starts_with("2019"),
        "after rejoin sent_at={at_after}"
    );

    let after_names = names_present_at(&arch, cid, &at_after);
    assert!(
        after_names.iter().any(|n| n == "Ada"),
        "GM423-LATER-LEAVE-KEEPS-REJOIN: message after T3 must still list Ada, got {after_names:?}"
    );

    if has_table(&arch, "group_membership") && !t3.is_empty() {
        let at_leave_id = message_id_by_body(&arch, "at leave instant");
        let t2 = message_sent_at(&arch, at_leave_id).expect("leave instant sent_at");
        assert!(
            t2 < t3,
            "T2 must be strictly before T3, got T2={t2} T3={t3}"
        );
        let ada_spans = ada_spans_for(&arch, cid);
        assert!(
            !ada_spans.iter().any(|(joined, left)| {
                joined.as_deref() == Some(t3.as_str()) && left.as_deref() == Some(t2.as_str())
            }),
            "GM423-LATER-LEAVE-KEEPS-REJOIN: no row has joined_at T3 with left_at T2, got {ada_spans:?}"
        );
        let leave_only = ada_spans
            .iter()
            .any(|(joined, left)| joined.is_none() && left.as_deref() == Some(t2.as_str()));
        if leave_only {
            let between_id = message_id_by_body(&arch, "between leave and rejoin");
            let at_between = message_sent_at(&arch, between_id).expect("between sent_at");
            assert!(
                t2.as_str() <= at_between.as_str() && at_between.as_str() < t3.as_str(),
                "between message must be at or after T2 and before T3, got {at_between} T2={t2} T3={t3}"
            );
            let between_names = names_present_at(&arch, cid, &at_between);
            assert!(
                between_names.iter().all(|n| n != "Ada"),
                "GM423-LATER-LEAVE-KEEPS-REJOIN: message at or after T2 and before T3 must not list Ada, got {between_names:?}"
            );
        }
    }
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-SAME-TS-LEAVE: a leave at the same timestamp as the join closes that join.
/// One export. `Berk added Ada` and `Ada left` share a timestamp. The open span
/// (joined_at = that timestamp, left_at NULL) must not keep Ada on the 2024 message.
#[test]
fn membership_same_timestamp_leave_closes_join() {
    let root = tmp_root();
    let chat = "\
[2020-03-15, 11:59:59] Messages and calls are end-to-end encrypted
[2020-03-15, 12:00:00] Berk added Ada
[2020-03-15, 12:00:00] Ada left
[2024-01-10, 09:00:00] Berk: after same minute
";
    let zip = write_ios_zip(&root.join("zips"), "random-same-ts-leave", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let cid = group_cid(&arch);
    let after_id = message_id_by_body(&arch, "after same minute");
    let at_after = message_sent_at(&arch, after_id).expect("after same minute sent_at");
    assert!(
        at_after.starts_with("2024"),
        "after same minute sent_at={at_after}"
    );

    let after_names = names_present_at(&arch, cid, &at_after);
    assert!(
        after_names.iter().all(|n| n != "Ada"),
        "GM423-SAME-TS-LEAVE: 2024 message must not list Ada, got {after_names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM423-LEAVE-CLOSES-ALL-OPEN: a leave after both joins closes every earlier open span.
/// Shorter export stored only `Berk added Ada`. The same chat's later export adds
/// an earlier join and a leave after both joins. After both imports the 2025
/// message must not list Ada.
#[test]
fn membership_leave_closes_every_earlier_open_span() {
    let root = tmp_root();
    let shorter = "\
[2024-01-01, 09:00:00] Messages and calls are end-to-end encrypted
[2024-06-01, 10:00:00] Berk added Ada
[2025-01-10, 09:00:00] Berk: after both joins
";
    let later = "\
[2024-01-01, 09:00:00] Messages and calls are end-to-end encrypted
[2024-01-01, 10:00:00] Berk added Ada
[2024-06-01, 10:00:00] Berk added Ada
[2024-08-01, 12:00:00] Ada left
[2025-01-10, 09:00:00] Berk: after both joins
";
    let zip_short = write_ios_zip(&root.join("zips"), "shorter-two-joins", shorter);
    let zip_later = write_ios_zip(&root.join("zips"), "later-two-joins", later);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_chat(&mut arch, &zip_short);
    if has_table(&arch, "group_membership") {
        require_group_membership_schema(&arch);
    }

    let n_conv = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv, 1,
        "shorter export must keep one conversation, got {n_conv}"
    );

    import_chat(&mut arch, &zip_later);
    let n_conv_later = count(&arch, "SELECT COUNT(*) FROM conversations");
    assert_eq!(
        n_conv_later, 1,
        "later export of the same chat must stay on the kept conversation, got {n_conv_later}"
    );
    let cid = group_cid(&arch);

    let after_id = message_id_by_body(&arch, "after both joins");
    let at_after = message_sent_at(&arch, after_id).expect("after both joins sent_at");
    assert!(
        at_after.starts_with("2025"),
        "after both joins sent_at={at_after}"
    );

    let after_names = names_present_at(&arch, cid, &at_after);
    assert!(
        after_names.iter().all(|n| n != "Ada"),
        "GM423-LEAVE-CLOSES-ALL-OPEN: message after both joins must not list Ada, got {after_names:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}
