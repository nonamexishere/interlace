//! #426 edits, deletes, and reactions are events on one message.
//!
//! Matrix IDs (gate grep):
//! WA426-EDIT WA426-DELETE WA426-REACT WA426-PLAIN WA426-CASCADE
//! WA464-PREV WA464-ORDER WA464-TOMB-ROW WA464-VISIBLE WA464-SPACE
//! IL464-NO-SECOND-HIT IL464-TOMBSTONE-REV
//!
//! Placeholders Ada / Berk / Self only. Current text is "hello". Deleted text
//! is "secret". Emoji is "👍". Rows are seeded with SQL on `init_archive`.
//! No export line is invented. A normal WhatsApp header stays one message.
//! `thread_parent_id` stays NULL. No import-undo command.
//!
//! A row is hidden when `edit_state` is `deleted` or `tombstone` is not 0.
//! Stored `messages.body_text` stays. `person_timeline` snippets,
//! `review_show` samples, and `visible_message_body` omit that text.
//! `<attached: note.txt>` inside a hidden body is not a chip. Subject
//! "invoice" may still find the row.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    complete_attachments, index_import_run, person_list, person_timeline, person_timeline_rows,
    review_show, search, ImportOpts, SearchQuery, SourceKind, TimelineRow,
};
use rusqlite::OptionalExtension;

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-wa426-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

struct Seed {
    run_id: i64,
    message_id: i64,
    berk_person: i64,
    ada_person: Option<i64>,
    ada_identity: Option<i64>,
}

/// One WhatsApp DM message. Ada is created only when `with_ada` is set.
fn seed(
    arch: &interlace_core::db::Archive,
    body: &str,
    edit_state: &str,
    tombstone: i64,
    key: &str,
    with_ada: bool,
) -> Seed {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path)
             VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
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
    let run_id = arch.conn.last_insert_rowid();

    let person = |name: &str, norm: &str| -> (i64, i64) {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES ('whatsapp', 'display_name', ?1, ?2, ?1)",
                rusqlite::params![name, norm],
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
                 VALUES (?1, ?2, 'manual', 1.0, 'user')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
        (pid, iid)
    };

    let (berk_person, berk_identity) = person("Berk", "berk");
    let (ada_person, ada_identity) = if with_ada {
        let (pid, iid) = person("Ada", "ada");
        (Some(pid), Some(iid))
    } else {
        (None, None)
    };

    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, source_id, native_id, title)
             VALUES ('whatsapp', 'dm', ?1, ?2, 'chat')",
            rusqlite::params![src, key],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conv, berk_identity],
        )
        .unwrap();
    if let Some(iid) = ada_identity {
        arch.conn
            .execute(
                "INSERT INTO conversation_participants(conversation_id, identity_id, role)
                 VALUES (?1, ?2, 'member')",
                rusqlite::params![conv, iid],
            )
            .unwrap();
    }

    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key,
                edit_state, tombstone
             ) VALUES (
                ?1, ?2, ?3, ?4,
                '2024-06-01T10:00:03Z', 'second', 'text', ?5, ?6,
                ?7, ?8
             )",
            rusqlite::params![
                conv,
                src,
                run_id,
                berk_identity,
                body,
                key,
                edit_state,
                tombstone
            ],
        )
        .unwrap();
    Seed {
        run_id,
        message_id: arch.conn.last_insert_rowid(),
        berk_person,
        ada_person,
        ada_identity,
    }
}

fn timeline(arch: &interlace_core::db::Archive, person_id: i64) -> Vec<TimelineRow> {
    person_timeline_rows(arch, person_id, false, 20, None).unwrap()
}

fn shows_edited(v: &serde_json::Value) -> bool {
    match v {
        serde_json::Value::String(s) => s == "edited",
        serde_json::Value::Array(items) => items.iter().any(shows_edited),
        serde_json::Value::Object(map) => map.iter().any(|(k, val)| {
            let key = k.to_ascii_lowercase().replace('-', "_");
            if matches!(key.as_str(), "edited" | "is_edited") && val.as_bool() == Some(true) {
                return true;
            }
            shows_edited(val)
        }),
        _ => false,
    }
}

fn json_has(v: &serde_json::Value, needle: &str) -> bool {
    match v {
        serde_json::Value::String(s) => s.contains(needle),
        serde_json::Value::Array(items) => items.iter().any(|item| json_has(item, needle)),
        serde_json::Value::Object(map) => map.values().any(|item| json_has(item, needle)),
        _ => false,
    }
}

fn assert_parent_null(arch: &interlace_core::db::Archive, id: &str) {
    let n: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM messages WHERE thread_parent_id IS NOT NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(n, 0, "{id}: thread_parent_id must stay NULL");
}

/// WA426-EDIT: one edited message and one revision. The timeline is one row
/// whose JSON shows the edited state. The current body stays "hello".
#[test]
fn wa426_edit_timeline_shows_edited_on_one_row() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "hello", "edited", 0, "wa426-edit", false);
    arch.conn
        .execute(
            "INSERT INTO message_revisions(message_id, rev_no, body_text, edited_at)
             VALUES (?1, 1, 'hello', '2024-06-01T10:05:00Z')",
            [s.message_id],
        )
        .unwrap();

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "WA426-EDIT: messages count"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        1,
        "WA426-EDIT: one revision"
    );
    let state: String = arch
        .conn
        .query_row(
            "SELECT edit_state FROM messages WHERE id = ?1",
            [s.message_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(state, "edited");
    assert_parent_null(&arch, "WA426-EDIT");

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA426-EDIT: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "hello", "WA426-EDIT: current body");
    assert!(
        rows[0].thread_parent_id.is_none(),
        "WA426-EDIT: thread_parent_id must stay NULL"
    );
    let v = serde_json::to_value(&rows[0]).unwrap();
    assert!(
        shows_edited(&v),
        "WA426-EDIT: timeline row must show edited state, got {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA426-DELETE: tombstone 1, stored body "secret". Timeline body is empty.
/// Search and the people-list preview do not return "secret".
#[test]
fn wa426_delete_hides_body_from_timeline_search_and_preview() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "secret", "deleted", 1, "wa426-delete", false);

    let (state, stone, body): (String, i64, String) = arch
        .conn
        .query_row(
            "SELECT edit_state, tombstone, body_text FROM messages WHERE id = ?1",
            [s.message_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .unwrap();
    assert_eq!(state, "deleted");
    assert_eq!(stone, 1);
    assert_eq!(body, "secret");
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "WA426-DELETE: messages count"
    );
    assert_parent_null(&arch, "WA426-DELETE");

    index_import_run(&arch, s.run_id).unwrap();
    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA426-DELETE: one timeline row, got {}",
        rows.len()
    );
    assert!(
        rows[0].thread_parent_id.is_none(),
        "WA426-DELETE: thread_parent_id must stay NULL"
    );

    let hits = search(
        &arch,
        &SearchQuery {
            q: "secret".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let indexed: Option<String> = arch
        .conn
        .query_row(
            "SELECT search_text FROM search_doc WHERE message_id = ?1",
            [s.message_id],
            |r| r.get(0),
        )
        .optional()
        .unwrap();
    let previews: Vec<String> = person_list(&arch)
        .unwrap()
        .into_iter()
        .filter_map(|p| p.preview)
        .collect();

    let mut gaps = Vec::new();
    if !rows[0].body_text.is_empty() {
        gaps.push(format!("timeline body {:?}", rows[0].body_text));
    }
    if hits
        .iter()
        .any(|h| h.message_id == s.message_id || h.snippet.contains("secret"))
        || indexed
            .as_ref()
            .is_some_and(|text| text.to_lowercase().contains("secret"))
    {
        gaps.push(format!("search hits={hits:?} search_doc={indexed:?}"));
    }
    if previews.iter().any(|p| p.contains("secret")) {
        gaps.push(format!("preview {previews:?}"));
    }
    assert!(
        gaps.is_empty(),
        "WA426-DELETE: deleted body is still readable: {}",
        gaps.join("; ")
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA426-REACT: Ada reacts "👍" on Berk's one message. Ada stays a separate
/// person. The one timeline row lists Ada and "👍".
#[test]
fn wa426_react_timeline_lists_ada_and_emoji() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "hello", "original", 0, "wa426-react", true);
    let ada_identity = s.ada_identity.expect("Ada identity");
    let ada_person = s.ada_person.expect("Ada person");
    arch.conn
        .execute(
            "INSERT INTO message_reactions(message_id, actor_identity_id, emoji, reacted_at)
             VALUES (?1, ?2, '👍', '2024-06-01T10:05:00Z')",
            rusqlite::params![s.message_id, ada_identity],
        )
        .unwrap();

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "WA426-REACT: messages count"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_reactions"),
        1,
        "WA426-REACT: one reaction"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM identities WHERE kind = 'whatsapp_jid'"
        ),
        0,
        "WA426-REACT: no whatsapp_jid"
    );
    assert_ne!(
        ada_person, s.berk_person,
        "WA426-REACT: Ada and Berk merged"
    );
    let ada_name: String = arch
        .conn
        .query_row(
            "SELECT p.display_name
             FROM person_identities pi
             JOIN persons p ON p.id = pi.person_id
             JOIN identities i ON i.id = pi.identity_id
             WHERE i.display_name = 'Ada' AND p.tombstoned_at IS NULL AND p.merged_into IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        ada_name, "Ada",
        "WA426-REACT: Ada's identity changed person"
    );
    let live: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM persons
             WHERE display_name IN ('Ada', 'Berk')
               AND tombstoned_at IS NULL AND merged_into IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(live, 2, "WA426-REACT: Ada and Berk must stay distinct");
    let listed = person_list(&arch).unwrap();
    assert!(listed
        .iter()
        .any(|p| p.id == ada_person && p.display_name == "Ada"));
    assert!(listed
        .iter()
        .any(|p| p.id == s.berk_person && p.display_name == "Berk"));
    assert_parent_null(&arch, "WA426-REACT");

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA426-REACT: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "hello");
    assert!(rows[0].thread_parent_id.is_none());
    let v = serde_json::to_value(&rows[0]).unwrap();
    assert!(
        json_has(&v, "Ada") && json_has(&v, "👍"),
        "WA426-REACT: timeline row must list Ada and 👍, got {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
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

/// WA426-PLAIN: a normal WhatsApp header stays one original text message.
/// No revision and no reaction.
#[test]
fn wa426_plain_header_stays_one_original_message() {
    let root = tmp_root();
    let chat = "[2019-06-01, 10:00:03] Berk: hello\n";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Berk", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let opts = ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some("berk".into()),
        ..ImportOpts::default()
    };
    arch.run_import(SourceKind::WhatsappIosZip, &zip, &opts)
        .expect("WA426-PLAIN: whatsapp import");

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "WA426-PLAIN: messages count"
    );
    let (state, stone, body, parent, kind): (String, i64, String, Option<i64>, String) = arch
        .conn
        .query_row(
            "SELECT edit_state, tombstone, body_text, thread_parent_id, kind FROM messages",
            [],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
        )
        .unwrap();
    assert_eq!(state, "original", "WA426-PLAIN: edit_state");
    assert_eq!(stone, 0, "WA426-PLAIN: tombstone");
    assert_eq!(body, "hello", "WA426-PLAIN: body");
    assert!(
        parent.is_none(),
        "WA426-PLAIN: thread_parent_id must stay NULL"
    );
    assert_eq!(kind, "text", "WA426-PLAIN: kind");
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        0,
        "WA426-PLAIN: revisions"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_reactions"),
        0,
        "WA426-PLAIN: reactions"
    );
    let berk = person_list(&arch)
        .unwrap()
        .into_iter()
        .find(|p| p.display_name == "Berk")
        .expect("WA426-PLAIN: Berk");
    let rows = timeline(&arch, berk.id);
    assert_eq!(
        rows.len(),
        1,
        "WA426-PLAIN: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "hello");
    assert!(rows[0].thread_parent_id.is_none());
    let _ = std::fs::remove_dir_all(&root);
}

/// WA426-CASCADE: deleting the message removes its revision and reaction.
/// No import-undo command.
#[test]
fn wa426_cascade_delete_removes_revision_and_reaction() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "hello", "original", 0, "wa426-cascade", true);
    let ada_identity = s.ada_identity.expect("Ada identity");
    arch.conn
        .execute(
            "INSERT INTO message_revisions(message_id, rev_no, body_text, edited_at)
             VALUES (?1, 1, 'hello', '2024-06-01T10:05:00Z')",
            [s.message_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO message_reactions(message_id, actor_identity_id, emoji, reacted_at)
             VALUES (?1, ?2, '👍', '2024-06-01T10:05:00Z')",
            rusqlite::params![s.message_id, ada_identity],
        )
        .unwrap();
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM message_revisions"), 1);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM message_reactions"), 1);
    assert_parent_null(&arch, "WA426-CASCADE");

    arch.conn
        .execute("DELETE FROM messages WHERE id = ?1", [s.message_id])
        .unwrap();
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        0,
        "WA426-CASCADE: message row"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        0,
        "WA426-CASCADE: revision orphan"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_reactions"),
        0,
        "WA426-CASCADE: reaction orphan"
    );
    let _ = std::fs::remove_dir_all(&root);
}

fn stored_body(arch: &interlace_core::db::Archive, id: i64) -> String {
    arch.conn
        .query_row("SELECT body_text FROM messages WHERE id = ?1", [id], |r| {
            r.get(0)
        })
        .unwrap()
}

/// Deleted tombstone ("secret") plus an older original ("hello") in one DM.
/// Ada is present. Berk sent both. SQLite keeps the deleted body.
fn seed_hidden_pair(arch: &interlace_core::db::Archive, key: &str) -> (Seed, i64) {
    let s = seed(arch, "secret", "deleted", 1, key, true);
    arch.conn
        .execute(
            "UPDATE messages
             SET subject = 'invoice', body_text = 'secret <attached: note.txt>'
             WHERE id = ?1",
            [s.message_id],
        )
        .unwrap();
    let (conv, src, run, sender): (i64, i64, i64, i64) = arch
        .conn
        .query_row(
            "SELECT conversation_id, source_id, import_run_id, sender_identity_id
             FROM messages WHERE id = ?1",
            [s.message_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key,
                edit_state, tombstone
             ) VALUES (
                ?1, ?2, ?3, ?4,
                '2024-06-01T09:00:00Z', 'second', 'text', 'hello', ?5,
                'original', 0
             )",
            rusqlite::params![conv, src, run, sender, format!("{key}-hello")],
        )
        .unwrap();
    (s, arch.conn.last_insert_rowid())
}

/// `person_timeline` snippet omits a deleted body. The older original still
/// shows "hello". Stored `messages.body_text` keeps "secret".
#[test]
fn wa426_delete_hidden_from_person_timeline_snippet() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let (s, hello_id) = seed_hidden_pair(&arch, "wa426-tl-snip");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), 2);
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );

    let hits = person_timeline(&arch, s.berk_person, false, 20).unwrap();
    let deleted = hits
        .iter()
        .find(|h| h.message_id == s.message_id)
        .unwrap_or_else(|| panic!("deleted row missing from person_timeline: {hits:?}"));
    let hello = hits
        .iter()
        .find(|h| h.message_id == hello_id)
        .unwrap_or_else(|| panic!("hello row missing from person_timeline: {hits:?}"));
    assert!(
        !deleted.snippet.contains("secret"),
        "person_timeline snippet leaked deleted body: {:?}",
        deleted.snippet
    );
    assert!(
        hello.snippet.contains("hello"),
        "person_timeline snippet dropped visible body: {:?}",
        hello.snippet
    );
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// `review_show` samples omit a deleted body and still include "hello".
/// Stored `messages.body_text` keeps "secret".
#[test]
fn wa426_delete_hidden_from_review_samples() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let (s, _hello_id) = seed_hidden_pair(&arch, "wa426-review-sample");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), 2);
    let ada_person = s.ada_person.expect("Ada");
    let berk_identity: i64 = arch
        .conn
        .query_row(
            "SELECT identity_id FROM person_identities WHERE person_id = ?1",
            [s.berk_person],
            |r| r.get(0),
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO merge_review_queue(
                status, left_identity_id, right_person_id, suggested_score, reason_summary
             ) VALUES ('open', ?1, ?2, 0.5, 'same name')",
            rusqlite::params![berk_identity, ada_person],
        )
        .unwrap();
    let queue_id = arch.conn.last_insert_rowid();
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );

    let shown = review_show(&arch, queue_id).unwrap();
    assert!(
        json_has(&shown, "hello"),
        "review_show dropped the visible sample: {shown}"
    );
    assert!(
        !json_has(&shown, "secret"),
        "review_show leaked deleted body: {shown}"
    );
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Subject "invoice" may find a deleted row. The hit snippet, the visible
/// body, and attachment chips omit "secret" and "note.txt". Tombstone 1
/// hides the body even when `edit_state` is `original`.
#[test]
fn wa426_visible_body_hides_deleted_text_and_attached_name() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let (s, hello_id) = seed_hidden_pair(&arch, "wa426-visible-body");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), 2);
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );

    index_import_run(&arch, s.run_id).unwrap();
    let invoice_hits = search(
        &arch,
        &SearchQuery {
            q: "invoice".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    let deleted_hit = invoice_hits
        .iter()
        .find(|h| h.message_id == s.message_id)
        .unwrap_or_else(|| panic!("deleted row missing from invoice search: {invoice_hits:?}"));
    assert!(
        !deleted_hit.snippet.contains("secret"),
        "search snippet leaked deleted body: {:?}",
        deleted_hit.snippet
    );
    let secret_hits = search(
        &arch,
        &SearchQuery {
            q: "secret".into(),
            ..SearchQuery::default()
        },
    )
    .unwrap();
    assert!(
        secret_hits.iter().all(|h| h.message_id != s.message_id),
        "secret search returned the deleted message: {secret_hits:?}"
    );

    let visible = interlace_core::visible_message_body(&arch, s.message_id).unwrap();
    assert_eq!(visible, "", "deleted visible body: {visible:?}");
    let plain = interlace_core::visible_message_body(&arch, hello_id).unwrap();
    assert!(plain.contains("hello"), "visible original body: {plain:?}");
    let chips = complete_attachments(&arch, s.message_id, &visible, Vec::new()).unwrap();
    assert!(
        chips
            .iter()
            .all(|a| a.filename.as_deref() != Some("note.txt")),
        "attached name leaked from hidden body: {chips:?}"
    );

    arch.conn
        .execute(
            "UPDATE messages SET edit_state = 'original' WHERE id = ?1",
            [s.message_id],
        )
        .unwrap();
    let (state, stone): (String, i64) = arch
        .conn
        .query_row(
            "SELECT edit_state, tombstone FROM messages WHERE id = ?1",
            [s.message_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(state, "original");
    assert_eq!(stone, 1);
    let tombstone_only = interlace_core::visible_message_body(&arch, s.message_id).unwrap();
    assert_eq!(
        tombstone_only, "",
        "tombstone visible body: {tombstone_only:?}"
    );
    assert!(
        stored_body(&arch, s.message_id).contains("secret"),
        "stored body was cleared"
    );
    let _ = std::fs::remove_dir_all(&root);
}

fn insert_rev(
    arch: &interlace_core::db::Archive,
    message_id: i64,
    rev_no: i64,
    body: Option<&str>,
) {
    arch.conn
        .execute(
            "INSERT INTO message_revisions(message_id, rev_no, body_text, edited_at)
             VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![
                message_id,
                rev_no,
                body,
                format!("2024-06-01T10:0{rev_no}:00Z")
            ],
        )
        .unwrap();
}

fn row_value(row: &TimelineRow) -> serde_json::Value {
    serde_json::to_value(row).unwrap()
}

/// WA464-PREV: current body `merhaba canim`. Revisions are `merhaba`, the same
/// current body again, and a null body. `previous_bodies` is `["merhaba"]` only.
#[test]
fn wa464_prev_previous_bodies_is_the_older_wording_only() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "merhaba canim", "edited", 0, "wa464-prev", false);
    insert_rev(&arch, s.message_id, 1, Some("merhaba"));
    insert_rev(&arch, s.message_id, 2, Some("merhaba canim"));
    insert_rev(&arch, s.message_id, 3, None);

    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), 1);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM message_revisions"), 3);
    let nulls: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM message_revisions
             WHERE message_id = ?1 AND body_text IS NULL",
            [s.message_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(nulls, 1, "WA464-PREV: null revision");
    let same: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM message_revisions
             WHERE message_id = ?1 AND body_text = 'merhaba canim'",
            [s.message_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(same, 1, "WA464-PREV: revision equal to the current body");
    let (state, stone): (String, i64) = arch
        .conn
        .query_row(
            "SELECT edit_state, tombstone FROM messages WHERE id = ?1",
            [s.message_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(state, "edited");
    assert_eq!(stone, 0);

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA464-PREV: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(
        rows[0].body_text, "merhaba canim",
        "WA464-PREV: current body"
    );
    assert_eq!(rows[0].edit_state, "edited");
    let v = row_value(&rows[0]);
    let want = serde_json::json!(["merhaba"]);
    assert_eq!(
        v.get("previous_bodies"),
        Some(&want),
        "WA464-PREV: previous_bodies missing or wrong: {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA464-ORDER: two older wordings, oldest first, even if inserted out of order.
#[test]
fn wa464_order_previous_bodies_follow_rev_no() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(
        &arch,
        "merhaba canim yine",
        "edited",
        0,
        "wa464-order",
        false,
    );
    insert_rev(&arch, s.message_id, 2, Some("merhaba canim"));
    insert_rev(&arch, s.message_id, 1, Some("merhaba"));

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "WA464-ORDER: one messages row"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM message_revisions"), 2);
    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA464-ORDER: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "merhaba canim yine");
    assert_eq!(rows[0].edit_state, "edited");
    let v = row_value(&rows[0]);
    let want = serde_json::json!(["merhaba", "merhaba canim"]);
    assert_eq!(
        v.get("previous_bodies"),
        Some(&want),
        "WA464-ORDER: previous_bodies missing or wrong: {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA464-TOMB-ROW: the same two revisions stay in SQLite. A deleted tombstone
/// timeline row has an empty body and `previous_bodies` `[]`, with neither
/// sentence in the row JSON.
#[test]
fn wa464_tomb_row_previous_bodies_are_empty() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(
        &arch,
        "merhaba canim yine",
        "deleted",
        1,
        "wa464-tomb-row",
        false,
    );
    insert_rev(&arch, s.message_id, 1, Some("merhaba"));
    insert_rev(&arch, s.message_id, 2, Some("merhaba canim"));

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        2,
        "WA464-TOMB-ROW: revision COUNT(*)"
    );
    let (state, stone): (String, i64) = arch
        .conn
        .query_row(
            "SELECT edit_state, tombstone FROM messages WHERE id = ?1",
            [s.message_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(state, "deleted");
    assert_eq!(stone, 1);
    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA464-TOMB-ROW: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "", "WA464-TOMB-ROW: timeline body");
    assert_eq!(rows[0].edit_state, "deleted");
    let v = row_value(&rows[0]);
    let want = serde_json::json!([]);
    assert_eq!(
        v.get("previous_bodies"),
        Some(&want),
        "WA464-TOMB-ROW: previous_bodies missing or wrong: {v}"
    );
    let text = serde_json::to_string(&v).unwrap();
    assert!(
        !text.contains("merhaba"),
        "WA464-TOMB-ROW: timeline JSON contains merhaba: {text}"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM message_revisions"),
        2,
        "WA464-TOMB-ROW: revision COUNT(*)"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA464-VISIBLE: current body `merhaba`. Revisions in `rev_no` order are
/// `merhaba canim`, `  merhaba  `, and `merhaba <attached: note.txt>`.
/// `previous_bodies` is exactly `["merhaba canim"]`. The trim-only revision
/// and the marker-only revision are absent. All three revision rows stay.
#[test]
fn wa464_visible_drops_trim_and_marker_only_revisions() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(&arch, "merhaba", "edited", 0, "wa464-visible", false);
    insert_rev(&arch, s.message_id, 1, Some("merhaba canim"));
    insert_rev(&arch, s.message_id, 2, Some("  merhaba  "));
    insert_rev(&arch, s.message_id, 3, Some("merhaba <attached: note.txt>"));

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA464-VISIBLE: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(rows[0].body_text, "merhaba", "WA464-VISIBLE: current body");
    assert_eq!(rows[0].edit_state, "edited");
    let n: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM message_revisions WHERE message_id = ?1",
            [s.message_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(n, 3, "WA464-VISIBLE: revision COUNT(*)");
    let v = row_value(&rows[0]);
    let want = serde_json::json!(["merhaba canim"]);
    assert_eq!(
        v.get("previous_bodies"),
        Some(&want),
        "WA464-VISIBLE: previous_bodies missing or wrong: {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA464-SPACE: current body `merhaba canim yine`. Revisions are
/// `merhaba  canim` (two spaces between the words), then
/// `merhaba <attached: note.txt>`. `previous_bodies` is exactly those stored
/// strings, in that order. The vec does not strip the marker.
#[test]
fn wa464_space_keeps_internal_space_and_stored_marker() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(
        &arch,
        "merhaba canim yine",
        "edited",
        0,
        "wa464-space",
        false,
    );
    insert_rev(&arch, s.message_id, 1, Some("merhaba  canim"));
    insert_rev(&arch, s.message_id, 2, Some("merhaba <attached: note.txt>"));

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "WA464-SPACE: one timeline row, got {}",
        rows.len()
    );
    assert_eq!(
        rows[0].body_text, "merhaba canim yine",
        "WA464-SPACE: current body"
    );
    let v = row_value(&rows[0]);
    let want = serde_json::json!(["merhaba  canim", "merhaba <attached: note.txt>"]);
    assert_eq!(
        v.get("previous_bodies"),
        Some(&want),
        "WA464-SPACE: previous_bodies missing or wrong: {v}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// IL464-NO-SECOND-HIT: two revisions stay one message, one timeline row, and
/// one `person_timeline` hit. Does not read `previous_bodies`.
#[test]
fn il464_no_second_hit_for_revisions() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let s = seed(
        &arch,
        "merhaba canim yine",
        "edited",
        0,
        "il464-no-second-hit",
        false,
    );
    insert_rev(&arch, s.message_id, 1, Some("merhaba"));
    insert_rev(&arch, s.message_id, 2, Some("merhaba canim"));

    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "IL464-NO-SECOND-HIT: messages"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM message_revisions"), 2);
    let current = stored_body(&arch, s.message_id);
    assert_eq!(current, "merhaba canim yine");
    assert_ne!(current, "merhaba");
    assert_ne!(current, "merhaba canim");

    let rows = timeline(&arch, s.berk_person);
    assert_eq!(
        rows.len(),
        1,
        "IL464-NO-SECOND-HIT: person_timeline_rows, got {}",
        rows.len()
    );
    assert_eq!(rows[0].message_id, s.message_id);
    assert_eq!(rows[0].body_text, "merhaba canim yine");
    let hits = person_timeline(&arch, s.berk_person, false, 20).unwrap();
    let n = hits.iter().filter(|h| h.message_id == s.message_id).count();
    assert_eq!(
        n, 1,
        "IL464-NO-SECOND-HIT: person_timeline hits for the message, got {hits:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
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

fn omits_token(text: &str, token: &str) -> bool {
    !text.contains(token)
}

/// IL464-TOMBSTONE-REV: tombstone keeps the stored body and the revision rows.
/// Visible surfaces omit `rev-alpha` and `rev-beta`. Search, find, and copy of
/// a live edited row are not asserted.
#[test]
fn il464_tombstone_omits_revision_tokens() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    let stored = "merhaba canim yine";
    let alpha = "rev-alpha";
    let beta = "rev-beta";
    assert!(!stored.contains(alpha) && !stored.contains(beta));
    assert!(!alpha.starts_with(beta) && !beta.starts_with(alpha));
    assert!(!stored.starts_with(alpha) && !stored.starts_with(beta));

    let s = seed(&arch, stored, "deleted", 1, "il464-tomb-rev", true);
    insert_rev(&arch, s.message_id, 1, Some(alpha));
    insert_rev(&arch, s.message_id, 2, Some(beta));
    let ada_person = s.ada_person.expect("Ada");
    let berk_identity: i64 = arch
        .conn
        .query_row(
            "SELECT identity_id FROM person_identities WHERE person_id = ?1",
            [s.berk_person],
            |r| r.get(0),
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO merge_review_queue(
                status, left_identity_id, right_person_id, suggested_score, reason_summary
             ) VALUES ('open', ?1, ?2, 0.5, 'same name')",
            rusqlite::params![berk_identity, ada_person],
        )
        .unwrap();
    let queue_id = arch.conn.last_insert_rowid();

    index_import_run(&arch, s.run_id).unwrap();
    let visible = interlace_core::visible_message_body(&arch, s.message_id).unwrap();
    assert_eq!(
        visible, "",
        "IL464-TOMBSTONE-REV: visible_message_body: {visible:?}"
    );

    for token in [alpha, beta] {
        let hits = search(
            &arch,
            &SearchQuery {
                q: token.into(),
                ..SearchQuery::default()
            },
        )
        .unwrap();
        assert!(
            hits.iter()
                .all(|h| omits_token(&h.snippet, alpha) && omits_token(&h.snippet, beta)),
            "IL464-TOMBSTONE-REV: FTS snippet leaked {token}: {hits:?}"
        );
    }
    let indexed: Option<String> = arch
        .conn
        .query_row(
            "SELECT search_text FROM search_doc WHERE message_id = ?1",
            [s.message_id],
            |r| r.get(0),
        )
        .optional()
        .unwrap();
    let indexed_text = indexed.unwrap_or_default();
    assert!(
        omits_token(&indexed_text, alpha) && omits_token(&indexed_text, beta),
        "IL464-TOMBSTONE-REV: search_doc.search_text leaked: {indexed_text:?}"
    );

    let timeline_hits = person_timeline(&arch, s.berk_person, false, 20).unwrap();
    let row = timeline_hits
        .iter()
        .find(|h| h.message_id == s.message_id)
        .unwrap_or_else(|| panic!("tombstone missing from person_timeline: {timeline_hits:?}"));
    assert!(
        omits_token(&row.snippet, alpha) && omits_token(&row.snippet, beta),
        "IL464-TOMBSTONE-REV: person_timeline snippet leaked: {:?}",
        row.snippet
    );

    let previews: Vec<String> = person_list(&arch)
        .unwrap()
        .into_iter()
        .filter_map(|p| p.preview)
        .collect();
    assert!(
        previews
            .iter()
            .all(|p| omits_token(p, alpha) && omits_token(p, beta)),
        "IL464-TOMBSTONE-REV: people-list preview leaked: {previews:?}"
    );

    let shown = review_show(&arch, queue_id).unwrap();
    assert!(
        !json_has(&shown, alpha) && !json_has(&shown, beta),
        "IL464-TOMBSTONE-REV: review_show samples leaked: {shown}"
    );

    assert_eq!(
        stored_body(&arch, s.message_id),
        stored,
        "IL464-TOMBSTONE-REV: stored body"
    );
    assert_eq!(
        revision_bodies(&arch, s.message_id),
        vec![Some(alpha.to_string()), Some(beta.to_string())],
        "IL464-TOMBSTONE-REV: revision rows"
    );
    let _ = std::fs::remove_dir_all(&root);
}
