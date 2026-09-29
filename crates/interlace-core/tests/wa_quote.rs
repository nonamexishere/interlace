//! #425 jump from a WhatsApp quote to the original (locked mix).
//!
//! Matrix IDs (gate grep):
//! WA425-RESOLVED WA425-MISSING WA425-SAME-TEXT WA425-OTHER
//! WA425-REIMPORT WA425-NO-PARENT
//!
//! Placeholders Ada / Berk / Self only. Bodies are "hello" and "reply".
//! A same-line iOS body keeps one embedded export line. A following physical
//! header line is its own message, so fixtures stay on one physical line.
//! No quote resolver is exported. `thread_parent_id` stays NULL. The jump
//! lock is `assert_wa_quote_jump`.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::{
    person_list, person_timeline_rows, resolve_wa_quote, ImportOpts, SourceKind, WaQuoteJump,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

const QUOTE: &str = "[2019-06-01, 10:00:03] Berk: hello";

fn tmp_root() -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-wa425-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
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

fn wa_opts(name: &str) -> ImportOpts {
    ImportOpts {
        locale: Some("en-US".into()),
        conversation_name: Some(name.into()),
        ..ImportOpts::default()
    }
}

fn import_zip(arch: &mut interlace_core::db::Archive, zip: &Path, name: &str) {
    arch.run_import(SourceKind::WhatsappIosZip, zip, &wa_opts(name))
        .expect("whatsapp import");
}

#[derive(Debug)]
struct Msg {
    id: i64,
    conversation_id: i64,
    body: Option<String>,
    parent: Option<i64>,
    in_reply_to: Option<String>,
    references: Option<String>,
    payload: Option<String>,
    subject: Option<String>,
}

fn messages(arch: &interlace_core::db::Archive) -> Vec<Msg> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT id, conversation_id, body_text, thread_parent_id, in_reply_to,
                    \"references\", payload_json, subject
             FROM messages ORDER BY id",
        )
        .unwrap();
    stmt.query_map([], |r| {
        Ok(Msg {
            id: r.get(0)?,
            conversation_id: r.get(1)?,
            body: r.get(2)?,
            parent: r.get(3)?,
            in_reply_to: r.get(4)?,
            references: r.get(5)?,
            payload: r.get(6)?,
            subject: r.get(7)?,
        })
    })
    .unwrap()
    .map(|r| r.unwrap())
    .collect()
}

fn assert_wa_parentless(arch: &interlace_core::db::Archive, id: &str) {
    for m in messages(arch) {
        assert!(
            m.parent.is_none(),
            "{id}: WhatsApp thread_parent_id must stay NULL (message {})",
            m.id
        );
        assert!(
            m.in_reply_to.is_none(),
            "{id}: WhatsApp in_reply_to must stay NULL (message {})",
            m.id
        );
        assert!(
            m.references.is_none(),
            "{id}: WhatsApp references must stay NULL (message {})",
            m.id
        );
        let _ = &m.payload;
    }
}

/// Integer columns and payload on `row_id` that store `target` (not the row's own id).
fn stored_target(arch: &interlace_core::db::Archive, row_id: i64, target: i64) -> Option<String> {
    let mut info = arch
        .conn
        .prepare("SELECT name, type FROM pragma_table_info('messages')")
        .unwrap();
    let cols: Vec<(String, String)> = info
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    drop(info);
    for (name, ty) in cols {
        if matches!(
            name.as_str(),
            "id" | "conversation_id"
                | "source_id"
                | "import_run_id"
                | "sender_identity_id"
                | "tombstone"
        ) || !ty.to_ascii_lowercase().contains("int")
        {
            continue;
        }
        let sql = format!("SELECT \"{name}\" FROM messages WHERE id = ?1");
        let v: Option<i64> = arch.conn.query_row(&sql, [row_id], |r| r.get(0)).unwrap();
        if v == Some(target) {
            return Some(name);
        }
    }
    let payload: Option<String> = arch
        .conn
        .query_row(
            "SELECT payload_json FROM messages WHERE id = ?1",
            [row_id],
            |r| r.get(0),
        )
        .unwrap();
    if payload.as_deref().is_some_and(|p| {
        p.split(|c: char| !c.is_ascii_digit())
            .any(|n| n == target.to_string())
    }) {
        return Some("payload_json".into());
    }
    None
}

fn person_id(arch: &interlace_core::db::Archive, name: &str) -> i64 {
    person_list(arch)
        .unwrap()
        .into_iter()
        .find(|p| p.display_name == name)
        .unwrap_or_else(|| panic!("{name} missing"))
        .id
}

/// WA425-RESOLVED: Ada quotes Berk in the same chat. No extra row. Body stays
/// the embedded line. Nothing stored points at Berk. The jump is the chrome gate.
#[test]
fn wa_quote_resolved_same_chat_keeps_body_and_stores_no_target() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:03] Berk: hello
[2019-06-01, 10:05:00] Ada: [2019-06-01, 10:00:03] Berk: hello
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-berk");

    let msgs = messages(&arch);
    assert_eq!(
        msgs.len(),
        2,
        "WA425-RESOLVED: quote must not insert a placeholder row, got {msgs:?}"
    );
    let berk = msgs
        .iter()
        .find(|m| m.body.as_deref() == Some("hello"))
        .expect("Berk hello");
    let ada = msgs
        .iter()
        .find(|m| m.body.as_deref() == Some(QUOTE))
        .expect("Ada quote body");
    assert_eq!(ada.conversation_id, berk.conversation_id);
    assert_eq!(
        ada.body.as_deref(),
        Some(QUOTE),
        "WA425-RESOLVED: body_text changed"
    );
    assert!(
        stored_target(&arch, ada.id, berk.id).is_none(),
        "WA425-RESOLVED: quote row stores a target at Berk ({})",
        stored_target(&arch, ada.id, berk.id).unwrap_or_default()
    );
    assert_wa_parentless(&arch, "WA425-RESOLVED");

    let timeline = person_timeline_rows(&arch, person_id(&arch, "Ada"), true, 20, None).unwrap();
    let quoted = timeline
        .iter()
        .find(|r| r.body_text.contains(QUOTE))
        .expect("WA425-RESOLVED: timeline lookup cannot see the quote in body_text");
    assert_eq!(quoted.body_text, QUOTE);
    assert!(
        quoted.thread_parent_id.is_none(),
        "WA425-RESOLVED: thread_parent_id must stay NULL"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// WA425-MISSING: Berk's line is not in the archive. No extra message.
#[test]
fn wa_quote_missing_original_inserts_nothing() {
    let root = tmp_root();
    let chat = "[2019-06-01, 10:05:00] Ada: [2019-06-01, 10:00:03] Berk: hello\n";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-only");

    let msgs = messages(&arch);
    assert_eq!(
        msgs.len(),
        1,
        "WA425-MISSING: a missing original must not insert a message, got {msgs:?}"
    );
    assert_eq!(msgs[0].body.as_deref(), Some(QUOTE));
    assert!(msgs[0].parent.is_none());
    assert_wa_parentless(&arch, "WA425-MISSING");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA425-SAME-TEXT: two Berk lines, same text, quote has no timestamp. Not one target.
#[test]
fn wa_quote_same_text_without_timestamp_is_not_one_target() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:01] Berk: hello
[2019-06-01, 10:00:02] Berk: hello
[2019-06-01, 10:05:00] Ada: Berk: hello
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "two-hello");

    let msgs = messages(&arch);
    let hellos: Vec<_> = msgs
        .iter()
        .filter(|m| m.body.as_deref() == Some("hello"))
        .collect();
    let quotes: Vec<_> = msgs
        .iter()
        .filter(|m| m.body.as_deref() == Some("Berk: hello"))
        .collect();
    assert_eq!(hellos.len(), 2, "WA425-SAME-TEXT: both Berk rows must stay");
    assert_eq!(
        quotes.len(),
        1,
        "WA425-SAME-TEXT: quote must not insert a row, got {msgs:?}"
    );
    assert_eq!(msgs.len(), 3, "WA425-SAME-TEXT: got {msgs:?}");
    assert!(hellos[0].id != hellos[1].id);
    for h in &hellos {
        assert!(
            stored_target(&arch, quotes[0].id, h.id).is_none(),
            "WA425-SAME-TEXT: ambiguous quote became one jump target ({h:?})"
        );
    }
    assert_wa_parentless(&arch, "WA425-SAME-TEXT");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA425-OTHER: same subject, or a quote of another conversation, does not resolve.
#[test]
fn wa_quote_subject_or_other_chat_does_not_resolve() {
    let root = tmp_root();
    let same = "\
[2019-06-01, 10:00:01] Berk: hello
[2019-06-01, 10:00:02] Ada: reply
";
    let other = "[2019-07-01, 11:00:00] Ada: [2019-06-01, 10:00:03] Berk: hello\n";
    let zip_a = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Home", same);
    let zip_b = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Other", other);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip_a, "home-chat");
    import_zip(&mut arch, &zip_b, "other-chat");
    arch.conn
        .execute(
            "UPDATE messages SET subject = 'hello' WHERE body_text IN ('hello', 'reply')",
            [],
        )
        .unwrap();

    let msgs = messages(&arch);
    assert_eq!(msgs.len(), 3, "WA425-OTHER: got {msgs:?}");
    let home: Vec<_> = msgs
        .iter()
        .filter(|m| m.body.as_deref() == Some("hello") || m.body.as_deref() == Some("reply"))
        .collect();
    assert_eq!(home.len(), 2);
    assert_eq!(home[0].conversation_id, home[1].conversation_id);
    assert_eq!(home[0].subject.as_deref(), Some("hello"));
    assert_eq!(home[1].subject.as_deref(), Some("hello"));
    assert!(home[0].parent.is_none() && home[1].parent.is_none());
    let quoted = msgs
        .iter()
        .find(|m| m.body.as_deref() == Some(QUOTE))
        .expect("other-chat quote");
    assert_ne!(quoted.conversation_id, home[0].conversation_id);
    assert_eq!(quoted.body.as_deref(), Some(QUOTE));
    let berk_id = home
        .iter()
        .find(|m| m.body.as_deref() == Some("hello"))
        .unwrap()
        .id;
    assert!(
        stored_target(&arch, quoted.id, berk_id).is_none(),
        "WA425-OTHER: other-conversation quote resolved to Berk"
    );
    assert_wa_parentless(&arch, "WA425-OTHER");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA425-REIMPORT: the same zip does not insert a second quoting message.
#[test]
fn wa_quote_reimport_keeps_one_body() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:03] Berk: hello
[2019-06-01, 10:05:00] Ada: [2019-06-01, 10:00:03] Berk: hello
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-berk");
    let before = messages(&arch);
    let quote_id = before
        .iter()
        .find(|m| m.body.as_deref() == Some(QUOTE))
        .unwrap()
        .id;
    import_zip(&mut arch, &zip, "ada-berk");
    let after = messages(&arch);
    let quotes: Vec<_> = after
        .iter()
        .filter(|m| m.body.as_deref() == Some(QUOTE))
        .collect();
    assert_eq!(
        quotes.len(),
        1,
        "WA425-REIMPORT: second import inserted another quoting message"
    );
    assert_eq!(quotes[0].id, quote_id);
    assert_eq!(quotes[0].body.as_deref(), Some(QUOTE));
    assert_eq!(after.len(), before.len());
    assert_wa_parentless(&arch, "WA425-REIMPORT");
    let _ = std::fs::remove_dir_all(&root);
}

/// WA425-NO-PARENT: WhatsApp rows do not get thread_parent_id. No Gmail import.
#[test]
fn wa_quote_whatsapp_rows_leave_thread_parent_null() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:03] Berk: hello
[2019-06-01, 10:05:00] Ada: [2019-06-01, 10:00:03] Berk: hello
[2019-06-01, 10:06:00] Self: reply
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-berk");
    let msgs = messages(&arch);
    assert!(msgs.len() >= 3, "WA425-NO-PARENT: expected the three lines");
    assert!(
        msgs.iter().any(|m| m.body.as_deref() == Some(QUOTE)),
        "WA425-NO-PARENT: quoting body missing"
    );
    assert_wa_parentless(&arch, "WA425-NO-PARENT");
    let _ = std::fs::remove_dir_all(&root);
}

fn resolve_body(
    arch: &interlace_core::db::Archive,
    body: &str,
) -> Result<Option<WaQuoteJump>, interlace_core::CoreError> {
    let msg = messages(arch)
        .into_iter()
        .find(|m| m.body.as_deref() == Some(body))
        .unwrap_or_else(|| panic!("body missing: {body:?}"));
    resolve_wa_quote(arch, msg.conversation_id, body)
}

/// A prose label is not a quote when the body also has an earlier line.
#[test]
fn wa_quote_prose_colon_is_not_a_quote() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:05:00] Ada: Remember this
Note: bring milk
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-note");
    let hit = resolve_body(&arch, "Remember this\nNote: bring milk").expect("resolve");
    assert!(
        hit.is_none(),
        "a prose colon after another line is not a quote, got {hit:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Nobody in the chat is named Note, so the whole body is not a quote.
#[test]
fn wa_quote_unknown_sender_line_is_not_a_quote() {
    let root = tmp_root();
    let chat = "[2019-06-01, 10:05:00] Ada: Note: bring milk\n";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-note");
    let hit = resolve_body(&arch, "Note: bring milk").expect("resolve");
    assert!(
        hit.is_none(),
        "an unknown sender line is not a quote, got {hit:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// Several timeless matches stay plain text. They must not say the original is missing.
#[test]
fn wa_quote_two_hellos_without_time_stay_plain() {
    let root = tmp_root();
    let chat = "\
[2019-06-01, 10:00:01] Berk: hello
[2019-06-01, 10:00:02] Berk: hello
[2019-06-01, 10:05:00] Ada: Berk: hello
";
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "two-hello");
    let hit = resolve_body(&arch, "Berk: hello").expect("resolve");
    assert!(
        hit.is_none(),
        "two timeless hellos stay plain text, got {hit:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// A timestamped line that is not in the chat stays a real miss.
#[test]
fn wa_quote_timestamped_missing_stays_a_miss() {
    let root = tmp_root();
    let body = "[2019-06-01, 10:00:03] Berk: gone";
    let chat = format!("[2019-06-01, 10:05:00] Ada: {body}\n");
    let zip = write_ios_zip(&root.join("zips"), "WhatsApp Chat - Ada", &chat);
    let mut arch = init_archive(&root.join("arch")).unwrap();
    import_zip(&mut arch, &zip, "ada-gone");
    let hit = resolve_body(&arch, body)
        .expect("resolve")
        .expect("timestamped missing line stays a quote");
    assert!(
        hit.message_id.is_none(),
        "timestamped miss must not name a message, got {hit:?}"
    );
    let _ = std::fs::remove_dir_all(&root);
}
