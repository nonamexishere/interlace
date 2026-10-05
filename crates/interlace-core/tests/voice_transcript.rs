//! Voice transcripts in search. No checkpoint is loaded.
//!
//! Matrix IDs (gate grep): VOICE-RARE VOICE-RERUN VOICE-KEEP VOICE-OFF
//! VOICE-UNREADABLE VOICE-DELETED VOICE-IMPORT VOICE-DOCTOR VOICE-WHICH
//! VOICE-EPOCH
//!
//! Placeholder Ada. The rare token is never planted in a body or filename.
//! Voice filenames are `ada-voice.opus`. `transcribe_voice_notes` takes the
//! decode closure; these tests do not read ggml weights.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, Archive};
use interlace_core::{
    index_import_run, migrate, search, set_voice_transcribe_enabled, store_voice_transcript,
    transcribe_voice_notes, voice_transcribe_enabled, CoreError, SearchQuery,
};
use rusqlite::OptionalExtension;

const TOKEN: &str = "xylophonequartz";
const VOICE_FILE: &str = "ada-voice.opus";

static SEQ: AtomicU64 = AtomicU64::new(0);

struct Ada {
    root: PathBuf,
    arch: Archive,
    source_id: i64,
    run_id: i64,
    conversation_id: i64,
    identity_id: i64,
}

struct Note<'a> {
    body: &'a str,
    key: &'a str,
    filename: &'a str,
    mime: Option<&'a str>,
    kind: &'a str,
    bytes: Option<&'a [u8]>,
    edit_state: &'a str,
    tombstone: i64,
    missing: i64,
    run_id: Option<i64>,
}

fn tmp_root(label: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!(
        "il-voice-{}-{}-{n}-{seq}",
        std::process::id(),
        label
    ));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn voice<'a>(body: &'a str, key: &'a str, bytes: Option<&'a [u8]>) -> Note<'a> {
    Note {
        body,
        key,
        filename: VOICE_FILE,
        mime: Some("audio/ogg"),
        kind: "voice",
        bytes,
        edit_state: "original",
        tombstone: 0,
        missing: if bytes.is_none() { 1 } else { 0 },
        run_id: None,
    }
}

fn open_ada(label: &str) -> Ada {
    let root = tmp_root(label);
    let arch = init_archive(&root).unwrap();
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path)
             VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let source_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [source_id],
        )
        .unwrap();
    let run_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('whatsapp', 'display_name', 'Ada', 'ada', 'Ada')",
            [],
        )
        .unwrap();
    let identity_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let person_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![person_id, identity_id],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, source_id, native_id, title)
             VALUES ('whatsapp', 'dm', ?1, 'whatsapp:dm-ada', 'Ada')",
            [source_id],
        )
        .unwrap();
    let conversation_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conversation_id, identity_id],
        )
        .unwrap();
    Ada {
        root,
        arch,
        source_id,
        run_id,
        conversation_id,
        identity_id,
    }
}

fn another_run(ada: &Ada) -> i64 {
    ada.arch
        .conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [ada.source_id],
        )
        .unwrap();
    ada.arch.conn.last_insert_rowid()
}

fn add_note(ada: &Ada, note: &Note<'_>) -> (i64, i64) {
    assert!(
        !note.body.contains(TOKEN),
        "planted body contains the rare token"
    );
    assert!(
        !note.filename.contains(TOKEN),
        "filename contains the rare token"
    );
    let run_id = note.run_id.unwrap_or(ada.run_id);
    ada.arch
        .conn
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
                ada.conversation_id,
                ada.source_id,
                run_id,
                ada.identity_id,
                note.body,
                note.key,
                note.edit_state,
                note.tombstone
            ],
        )
        .unwrap();
    let message_id = ada.arch.conn.last_insert_rowid();
    let (cas, missing) = match note.bytes {
        Some(bytes) => (Some(ada.arch.cas_put(bytes, note.mime).unwrap()), 0),
        None => (None, note.missing),
    };
    ada.arch
        .conn
        .execute(
            "INSERT INTO attachments(message_id, cas_hash, filename, mime, kind, omitted, missing)
             VALUES (?1, ?2, ?3, ?4, ?5, 0, ?6)",
            rusqlite::params![
                message_id,
                cas,
                note.filename,
                note.mime,
                note.kind,
                missing
            ],
        )
        .unwrap();
    (message_id, ada.arch.conn.last_insert_rowid())
}

fn body_of(arch: &Archive, message_id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT body_text FROM messages WHERE id = ?1",
            [message_id],
            |r| r.get::<_, Option<String>>(0),
        )
        .unwrap()
        .unwrap_or_default()
}

fn transcript_of(arch: &Archive, attachment_id: i64) -> Option<String> {
    arch.conn
        .query_row(
            "SELECT transcript FROM attachments WHERE id = ?1",
            [attachment_id],
            |r| r.get(0),
        )
        .unwrap()
}

fn indexed_text(arch: &Archive, message_id: i64) -> Option<String> {
    arch.conn
        .query_row(
            "SELECT search_text FROM search_doc WHERE message_id = ?1",
            [message_id],
            |r| r.get(0),
        )
        .optional()
        .unwrap()
}

fn search_text_of(arch: &Archive, message_id: i64) -> String {
    indexed_text(arch, message_id).unwrap_or_else(|| panic!("search_doc missing for {message_id}"))
}

fn token_copies(text: &str) -> usize {
    text.matches(TOKEN).count()
}

fn schema_epoch(arch: &Archive) -> i64 {
    arch.conn
        .query_row("SELECT schema_epoch FROM archive_meta", [], |r| r.get(0))
        .unwrap()
}

fn search_ids(arch: &Archive, q: &str) -> Vec<i64> {
    search(
        arch,
        &SearchQuery {
            q: q.to_string(),
            ..SearchQuery::default()
        },
    )
    .unwrap()
    .into_iter()
    .map(|hit| hit.message_id)
    .collect()
}

fn setting_value(arch: &Archive) -> Option<String> {
    arch.conn
        .query_row(
            "SELECT value FROM settings WHERE key = 'transcribe_voice'",
            [],
            |r| r.get(0),
        )
        .optional()
        .unwrap()
}

fn present_weights(root: &Path) -> PathBuf {
    let path = root.join("weights.bin");
    std::fs::write(&path, b"not-ggml").unwrap();
    path
}

fn close(ada: Ada) {
    let root = ada.root.clone();
    drop(ada);
    let _ = std::fs::remove_dir_all(root);
}

#[test]
fn voice_rare_token_is_a_search_hit() {
    let ada = open_ada("rare");
    let (message_id, attachment_id) = add_note(
        &ada,
        &voice("hello from Ada", "voice-rare", Some(b"ada-voice-rare")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    assert!(
        !search_ids(&ada.arch, TOKEN).contains(&message_id),
        "VOICE-RARE: token must not hit before the transcript is stored"
    );
    let body = body_of(&ada.arch, message_id);
    store_voice_transcript(&ada.arch, attachment_id, TOKEN).unwrap();
    assert_eq!(
        body_of(&ada.arch, message_id),
        body,
        "VOICE-RARE: body_text"
    );
    assert_eq!(
        transcript_of(&ada.arch, attachment_id).as_deref(),
        Some(TOKEN),
        "VOICE-RARE: transcript column"
    );
    assert!(
        search_ids(&ada.arch, TOKEN).contains(&message_id),
        "VOICE-RARE: search must return {message_id}"
    );
    assert_eq!(
        token_copies(&search_text_of(&ada.arch, message_id)),
        2,
        "VOICE-RARE: ASCII token is stored twice, once per fold"
    );
    assert_eq!(schema_epoch(&ada.arch), 1, "VOICE-RARE: schema_epoch");
    close(ada);
}

#[test]
fn voice_rerun_same_string_keeps_dual_fold_count() {
    let ada = open_ada("rerun");
    let (message_id, attachment_id) = add_note(
        &ada,
        &voice("hello from Ada", "voice-rerun", Some(b"ada-voice-rerun")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    store_voice_transcript(&ada.arch, attachment_id, TOKEN).unwrap();
    let text = search_text_of(&ada.arch, message_id);
    assert_eq!(
        token_copies(&text),
        2,
        "VOICE-RERUN: first store is the dual-fold count"
    );
    store_voice_transcript(&ada.arch, attachment_id, TOKEN).unwrap();
    let again = search_text_of(&ada.arch, message_id);
    assert_eq!(
        again, text,
        "VOICE-RERUN: a second assignment of the same string keeps search_text"
    );
    assert_eq!(
        token_copies(&again),
        2,
        "VOICE-RERUN: dual-fold count must stay 2, not 4"
    );
    assert_eq!(
        transcript_of(&ada.arch, attachment_id).as_deref(),
        Some(TOKEN),
        "VOICE-RERUN: column is replaced, not concatenated"
    );
    close(ada);
}

#[test]
fn voice_keep_skips_stored_and_missing_weights() {
    let ada = open_ada("keep");
    let stored_bytes = b"ada-voice-keep-stored";
    let null_bytes = b"ada-voice-keep-null";
    let (stored_msg, stored_att) = add_note(
        &ada,
        &voice("hello from Ada", "voice-keep-stored", Some(stored_bytes)),
    );
    let (_null_msg, null_att) = add_note(
        &ada,
        &voice("second note from Ada", "voice-keep-null", Some(null_bytes)),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_voice_transcribe_enabled(&ada.arch, true).unwrap();
    assert!(
        voice_transcribe_enabled(&ada.arch).unwrap(),
        "VOICE-KEEP: setting on"
    );
    assert_eq!(
        setting_value(&ada.arch).as_deref(),
        Some("on"),
        "VOICE-KEEP: settings key"
    );
    assert!(
        transcript_of(&ada.arch, null_att).is_none(),
        "VOICE-KEEP: set_voice_transcribe_enabled does not transcribe"
    );
    store_voice_transcript(&ada.arch, stored_att, TOKEN).unwrap();
    let stored_text = search_text_of(&ada.arch, stored_msg);
    assert_eq!(
        token_copies(&stored_text),
        2,
        "VOICE-KEEP: count before the pass"
    );

    let missing = ada.root.join("missing-weights.bin");
    let mut missing_calls = 0u32;
    transcribe_voice_notes(
        &ada.arch,
        &missing,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            missing_calls += 1;
            let _ = bytes;
            Ok(Some("keepquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(
        missing_calls, 0,
        "VOICE-KEEP: a missing weights path must not call decode"
    );
    assert!(
        transcript_of(&ada.arch, null_att).is_none(),
        "VOICE-KEEP: NULL voice row stays NULL when weights are missing"
    );
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-KEEP: stored column survives a missing weights path"
    );
    assert_eq!(
        search_text_of(&ada.arch, stored_msg),
        stored_text,
        "VOICE-KEEP: search_text unchanged when weights are missing"
    );

    let weights = present_weights(&ada.root);
    let mut calls: Vec<Vec<u8>> = Vec::new();
    transcribe_voice_notes(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls.push(bytes.to_vec());
            Ok(Some("keepquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(
        calls,
        vec![null_bytes.to_vec()],
        "VOICE-KEEP: decode is not called for the stored row"
    );
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-KEEP: first stored string stays"
    );
    assert_eq!(
        search_text_of(&ada.arch, stored_msg),
        stored_text,
        "VOICE-KEEP: search_text count stays"
    );
    assert_eq!(token_copies(&search_text_of(&ada.arch, stored_msg)), 2);
    assert_eq!(
        transcript_of(&ada.arch, null_att).as_deref(),
        Some("keepquartzother"),
        "VOICE-KEEP: Ok(Some) on the NULL row is stored"
    );
    close(ada);
}

#[test]
fn voice_off_does_not_transcribe() {
    let ada = open_ada("off");
    let (stored_msg, stored_att) = add_note(
        &ada,
        &voice(
            "hello from Ada",
            "voice-off-stored",
            Some(b"ada-voice-off-stored"),
        ),
    );
    let (_null_msg, null_att) = add_note(
        &ada,
        &voice(
            "second note from Ada",
            "voice-off-null",
            Some(b"ada-voice-off-null"),
        ),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    store_voice_transcript(&ada.arch, stored_att, TOKEN).unwrap();
    let stored_text = search_text_of(&ada.arch, stored_msg);
    let weights = present_weights(&ada.root);

    assert!(
        !voice_transcribe_enabled(&ada.arch).unwrap(),
        "VOICE-OFF: a missing settings row is off"
    );
    assert!(
        setting_value(&ada.arch).is_none(),
        "VOICE-OFF: init does not insert transcribe_voice"
    );
    let mut calls = 0u32;
    transcribe_voice_notes(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls += 1;
            let _ = bytes;
            Ok(Some("offquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(calls, 0, "VOICE-OFF: missing setting must not call decode");
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-OFF: existing transcript stays while the setting is missing"
    );
    assert!(
        transcript_of(&ada.arch, null_att).is_none(),
        "VOICE-OFF: NULL voice row stays NULL while the setting is missing"
    );
    assert!(
        search_ids(&ada.arch, TOKEN).contains(&stored_msg),
        "VOICE-OFF: an existing transcript stays searchable"
    );
    assert!(
        !search_ids(&ada.arch, "offquartzother").contains(&stored_msg),
        "VOICE-OFF: decode text was not written"
    );

    set_voice_transcribe_enabled(&ada.arch, false).unwrap();
    assert!(
        !voice_transcribe_enabled(&ada.arch).unwrap(),
        "VOICE-OFF: off"
    );
    assert_eq!(
        setting_value(&ada.arch).as_deref(),
        Some("off"),
        "VOICE-OFF: settings value"
    );
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-OFF: set_voice_transcribe_enabled(false) leaves the column"
    );
    transcribe_voice_notes(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls += 1;
            let _ = bytes;
            Ok(Some("offquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(calls, 0, "VOICE-OFF: off must not call decode");
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-OFF: existing transcript stays while off"
    );
    assert!(
        transcript_of(&ada.arch, null_att).is_none(),
        "VOICE-OFF: off does not fill a NULL voice row"
    );
    assert_eq!(
        search_text_of(&ada.arch, stored_msg),
        stored_text,
        "VOICE-OFF: search_text unchanged"
    );
    assert_eq!(token_copies(&search_text_of(&ada.arch, stored_msg)), 2);
    close(ada);
}

#[test]
fn voice_unreadable_leaves_rows_unchanged() {
    let ada = open_ada("unreadable");
    let empty_bytes = b"";
    let jpeg_bytes = b"\xFF\xD8\xFF\xD9";
    let ogg_bytes = b"OggS";
    let (empty_msg, empty_att) = add_note(
        &ada,
        &voice("hello from Ada", "voice-empty", Some(empty_bytes)),
    );
    let (jpeg_msg, jpeg_att) = add_note(
        &ada,
        &voice("hello from Ada", "voice-jpeg", Some(jpeg_bytes)),
    );
    let (ogg_msg, ogg_att) = add_note(&ada, &voice("hello from Ada", "voice-ogg", Some(ogg_bytes)));
    let (nocas_msg, nocas_att) = add_note(&ada, &voice("hello from Ada", "voice-nocas", None));
    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_voice_transcribe_enabled(&ada.arch, true).unwrap();
    assert!(voice_transcribe_enabled(&ada.arch).unwrap());

    let rows = [empty_msg, jpeg_msg, ogg_msg, nocas_msg];
    let atts = [empty_att, jpeg_att, ogg_att, nocas_att];
    let before: Vec<(String, Option<String>, String)> = rows
        .iter()
        .zip(atts)
        .map(|(message_id, attachment_id)| {
            (
                body_of(&ada.arch, *message_id),
                transcript_of(&ada.arch, attachment_id),
                search_text_of(&ada.arch, *message_id),
            )
        })
        .collect();
    assert!(before.iter().all(|(_, transcript, _)| transcript.is_none()));

    let weights = present_weights(&ada.root);
    let mut seen: Vec<Vec<u8>> = Vec::new();
    transcribe_voice_notes(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            seen.push(bytes.to_vec());
            if bytes.is_empty() || bytes.starts_with(&[0xFF, 0xD8]) || bytes.starts_with(b"OggS") {
                Ok(None)
            } else {
                Ok(Some(TOKEN.to_string()))
            }
        },
    )
    .unwrap();

    assert_eq!(
        seen.iter().filter(|bytes| bytes.is_empty()).count(),
        1,
        "VOICE-UNREADABLE: empty bytes are passed to decode"
    );
    assert_eq!(
        seen.iter()
            .filter(|bytes| bytes.starts_with(&[0xFF, 0xD8]))
            .count(),
        1,
        "VOICE-UNREADABLE: JPEG bytes are passed to decode"
    );
    assert_eq!(
        seen.iter()
            .filter(|bytes| bytes.starts_with(b"OggS"))
            .count(),
        1,
        "VOICE-UNREADABLE: truncated OggS is passed to decode"
    );
    assert_eq!(
        seen.len(),
        3,
        "VOICE-UNREADABLE: a voice row with no cas_hash is not passed to decode"
    );
    for (idx, message_id) in rows.iter().enumerate() {
        assert_eq!(
            body_of(&ada.arch, *message_id).as_str(),
            before[idx].0.as_str(),
            "VOICE-UNREADABLE: body_text"
        );
        assert_eq!(
            transcript_of(&ada.arch, atts[idx]).as_deref(),
            before[idx].1.as_deref(),
            "VOICE-UNREADABLE: transcript"
        );
        assert_eq!(
            search_text_of(&ada.arch, *message_id).as_str(),
            before[idx].2.as_str(),
            "VOICE-UNREADABLE: search_text"
        );
    }
    close(ada);
}

#[test]
fn voice_deleted_hides_transcript_from_search() {
    let ada = open_ada("deleted");
    let mut deleted = voice("hiddenadabody", "voice-deleted", Some(b"ada-voice-deleted"));
    deleted.edit_state = "deleted";
    let mut stone = voice("stonedadabody", "voice-stone", Some(b"ada-voice-stone"));
    stone.tombstone = 1;
    let (deleted_msg, deleted_att) = add_note(&ada, &deleted);
    let (stone_msg, stone_att) = add_note(&ada, &stone);
    index_import_run(&ada.arch, ada.run_id).unwrap();
    assert!(
        !indexed_text(&ada.arch, deleted_msg)
            .unwrap_or_default()
            .contains("hiddenadabody"),
        "VOICE-DELETED: deleted body is already hidden"
    );
    assert!(
        !indexed_text(&ada.arch, stone_msg)
            .unwrap_or_default()
            .contains("stonedadabody"),
        "VOICE-DELETED: tombstoned body is already hidden"
    );

    store_voice_transcript(&ada.arch, deleted_att, TOKEN).unwrap();
    store_voice_transcript(&ada.arch, stone_att, TOKEN).unwrap();

    assert_eq!(body_of(&ada.arch, deleted_msg), "hiddenadabody");
    assert_eq!(body_of(&ada.arch, stone_msg), "stonedadabody");
    assert_eq!(
        transcript_of(&ada.arch, deleted_att).as_deref(),
        Some(TOKEN),
        "VOICE-DELETED: deleted row still stores the column"
    );
    assert_eq!(
        transcript_of(&ada.arch, stone_att).as_deref(),
        Some(TOKEN),
        "VOICE-DELETED: tombstoned row still stores the column"
    );
    let hits = search_ids(&ada.arch, TOKEN);
    assert!(
        !hits.contains(&deleted_msg) && !hits.contains(&stone_msg),
        "VOICE-DELETED: search must not hit the token, got {hits:?}"
    );
    for (message_id, hidden) in [(deleted_msg, "hiddenadabody"), (stone_msg, "stonedadabody")] {
        let text = search_text_of(&ada.arch, message_id);
        assert!(
            !text.contains(TOKEN),
            "VOICE-DELETED: transcript folded into search_text: {text}"
        );
        assert!(
            !text.contains(hidden),
            "VOICE-DELETED: hidden body_text is still in search_text: {text}"
        );
    }
    close(ada);
}

#[test]
fn voice_import_indexes_stored_transcript_without_model() {
    let ada = open_ada("import");
    let (bare_msg, bare_att) = add_note(
        &ada,
        &voice(
            "hello from Ada",
            "voice-import-bare",
            Some(b"ada-voice-import-bare"),
        ),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    assert!(
        transcript_of(&ada.arch, bare_att).is_none(),
        "VOICE-IMPORT: index_import_run alone does not create a transcript"
    );

    let run_id = another_run(&ada);
    let mut stored = voice(
        "second hello from Ada",
        "voice-import-stored",
        Some(b"ada-voice-import-stored"),
    );
    stored.run_id = Some(run_id);
    let (stored_msg, stored_att) = add_note(&ada, &stored);
    let body = body_of(&ada.arch, stored_msg);
    store_voice_transcript(&ada.arch, stored_att, TOKEN).unwrap();
    index_import_run(&ada.arch, run_id).unwrap();

    assert!(
        transcript_of(&ada.arch, bare_att).is_none(),
        "VOICE-IMPORT: indexing another run does not backfill a transcript"
    );
    assert_eq!(
        transcript_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "VOICE-IMPORT: transcript stored before index_import_run"
    );
    assert_eq!(
        body_of(&ada.arch, stored_msg),
        body,
        "VOICE-IMPORT: body_text"
    );
    let hits = search_ids(&ada.arch, TOKEN);
    assert!(
        hits.contains(&stored_msg),
        "VOICE-IMPORT: stored transcript is still a hit after index_import_run, got {hits:?}"
    );
    assert!(
        !hits.contains(&bare_msg),
        "VOICE-IMPORT: the untranscribed note is not a hit"
    );
    close(ada);
}

#[test]
fn voice_doctor_does_not_transcribe() {
    let ada = open_ada("doctor");
    let bytes = b"ada-voice-doctor";
    let (message_id, attachment_id) =
        add_note(&ada, &voice("hello from Ada", "voice-doctor", Some(bytes)));
    let hash: String = ada
        .arch
        .conn
        .query_row(
            "SELECT cas_hash FROM attachments WHERE id = ?1",
            [attachment_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(ada.arch.cas_get(&hash).unwrap(), bytes);
    assert!(
        transcript_of(&ada.arch, attachment_id).is_none(),
        "VOICE-DOCTOR: transcript starts NULL"
    );
    let quick = ada.arch.doctor_issues_quick().unwrap();
    let full = ada.arch.doctor_issues().unwrap();
    assert!(
        transcript_of(&ada.arch, attachment_id).is_none(),
        "VOICE-DOCTOR: doctor leaves attachments.transcript NULL"
    );
    assert!(
        !quick.iter().any(|issue| issue.contains("CAS blob missing")),
        "VOICE-DOCTOR: quick issues must not report a model failure as CAS blob missing, got {quick:?}"
    );
    assert!(
        !full.iter().any(|issue| issue.contains("CAS blob missing")),
        "VOICE-DOCTOR: doctor_issues must not report a model failure as CAS blob missing, got {full:?}"
    );
    assert_eq!(body_of(&ada.arch, message_id), "hello from Ada");
    close(ada);
}

#[test]
fn voice_which_skips_audio_file_kind() {
    let ada = open_ada("which");
    let voice_bytes = b"ada-voice-which";
    let file_bytes = b"ada-file-audio";
    let (_voice_msg, _voice_att) = add_note(
        &ada,
        &voice("hello from Ada", "voice-which", Some(voice_bytes)),
    );
    let mut file = voice("hello from Ada", "file-which", Some(file_bytes));
    file.filename = "ada-clip.ogg";
    file.kind = "file";
    file.mime = Some("audio/ogg");
    let (file_msg, file_att) = add_note(&ada, &file);
    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_voice_transcribe_enabled(&ada.arch, true).unwrap();
    let file_body = body_of(&ada.arch, file_msg);
    let file_text = search_text_of(&ada.arch, file_msg);
    let weights = present_weights(&ada.root);
    let mut calls: Vec<Vec<u8>> = Vec::new();
    transcribe_voice_notes(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls.push(bytes.to_vec());
            Ok(Some(TOKEN.into()))
        },
    )
    .unwrap();
    assert_eq!(
        calls,
        vec![voice_bytes.to_vec()],
        "VOICE-WHICH: decode is not called for kind=file"
    );
    assert!(
        transcript_of(&ada.arch, file_att).is_none(),
        "VOICE-WHICH: file row transcript stays NULL"
    );
    assert_eq!(
        body_of(&ada.arch, file_msg),
        file_body,
        "VOICE-WHICH: body_text"
    );
    assert_eq!(
        search_text_of(&ada.arch, file_msg),
        file_text,
        "VOICE-WHICH: search_text"
    );
    assert!(!search_text_of(&ada.arch, file_msg).contains(TOKEN));
    close(ada);
}

#[test]
fn voice_epoch_stays_1() {
    let root = tmp_root("epoch");
    let arch = init_archive(&root).unwrap();
    migrate(&arch.conn).unwrap();
    migrate(&arch.conn).unwrap();
    assert_eq!(schema_epoch(&arch), 1, "VOICE-EPOCH");
    drop(arch);
    let _ = std::fs::remove_dir_all(root);
}
