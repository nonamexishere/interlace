//! Matrix IDs (gate grep): OCR-HIT OCR-FOLD OCR-RERUN OCR-HIDDEN OCR-OFF OCR-BLUR OCR-WHICH OCR-VOICE OCR-EPOCH OCR-IMPORT
//!
//! Photo text in search. Placeholder Ada. The rare token is never planted in a
//! body, subject, or filename. Photo filenames are `ada-photo.jpg`. Kind is
//! `image` in a DM. The stub decode returns the token or `None`. These tests
//! do not read weights.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, Archive};
use interlace_core::{
    index_import_run, migrate, ocr_image_attachments, ocr_images_enabled, pending_ocr_rows, search,
    set_ocr_images_enabled, store_ocr_text, CoreError, SearchQuery,
};
use rusqlite::OptionalExtension;

const TOKEN: &str = "quartzphoto91";
const PHOTO_FILE: &str = "ada-photo.jpg";
const VOICE_TOKEN: &str = "quartzvoice91";

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
        "il-photo-{}-{}-{n}-{seq}",
        std::process::id(),
        label
    ));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn photo<'a>(body: &'a str, key: &'a str, bytes: Option<&'a [u8]>) -> Note<'a> {
    Note {
        body,
        key,
        filename: PHOTO_FILE,
        mime: Some("image/jpeg"),
        kind: "image",
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

fn insert_attachment(ada: &Ada, message_id: i64, note: &Note<'_>) -> i64 {
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
    let attachment_id = insert_attachment(ada, message_id, note);
    (message_id, attachment_id)
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

fn subject_of(arch: &Archive, message_id: i64) -> String {
    arch.conn
        .query_row(
            "SELECT subject FROM messages WHERE id = ?1",
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

fn ocr_of(arch: &Archive, attachment_id: i64) -> Option<String> {
    arch.conn
        .query_row(
            "SELECT ocr_text FROM attachments WHERE id = ?1",
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
            "SELECT value FROM settings WHERE key = 'ocr_images'",
            [],
            |r| r.get(0),
        )
        .optional()
        .unwrap()
}

fn present_weights(root: &Path) -> PathBuf {
    let path = root.join("weights.bin");
    std::fs::write(&path, b"not-ocr").unwrap();
    path
}

fn close(ada: Ada) {
    let root = ada.root.clone();
    drop(ada);
    let _ = std::fs::remove_dir_all(root);
}

#[test]
fn ocr_hit_rare_token_is_a_search_hit() {
    let ada = open_ada("hit");
    let bytes = b"ada-photo-hit";
    let (message_id, attachment_id) =
        add_note(&ada, &photo("hello from Ada", "ocr-hit", Some(bytes)));
    index_import_run(&ada.arch, ada.run_id).unwrap();
    let body = body_of(&ada.arch, message_id);
    let subject = subject_of(&ada.arch, message_id);
    assert!(!body.contains(TOKEN), "OCR-HIT: body contains {TOKEN}");
    assert!(
        !subject.contains(TOKEN),
        "OCR-HIT: subject contains {TOKEN}"
    );
    assert_eq!(PHOTO_FILE, "ada-photo.jpg", "OCR-HIT: filename");
    assert!(
        !PHOTO_FILE.contains(TOKEN),
        "OCR-HIT: filename contains {TOKEN}"
    );
    assert!(
        !search_ids(&ada.arch, TOKEN).contains(&message_id),
        "OCR-HIT: token must not hit before the stub pass"
    );
    set_ocr_images_enabled(&ada.arch, true).unwrap();
    assert!(
        ocr_images_enabled(&ada.arch).unwrap(),
        "OCR-HIT: setting on"
    );
    let weights = present_weights(&ada.root);
    let mut calls: Vec<Vec<u8>> = Vec::new();
    ocr_image_attachments(
        &ada.arch,
        &weights,
        |seen: &[u8]| -> Result<Option<String>, CoreError> {
            calls.push(seen.to_vec());
            Ok(Some(TOKEN.to_string()))
        },
    )
    .unwrap();
    assert_eq!(
        calls,
        vec![bytes.to_vec()],
        "OCR-HIT: one stub pass decodes the image"
    );
    assert_eq!(body_of(&ada.arch, message_id), body, "OCR-HIT: body_text");
    assert_eq!(
        ocr_of(&ada.arch, attachment_id).as_deref(),
        Some(TOKEN),
        "OCR-HIT: ocr_text column"
    );
    assert!(
        search_ids(&ada.arch, TOKEN).contains(&message_id),
        "OCR-HIT: search must return {message_id}"
    );
    assert_eq!(
        token_copies(&search_text_of(&ada.arch, message_id)),
        2,
        "OCR-HIT: ASCII token is stored twice, once per fold"
    );
    close(ada);
}

#[test]
fn ocr_fold_turkish_i_matches_both_queries() {
    let ada = open_ada("fold");
    let (message_id, attachment_id) = add_note(
        &ada,
        &photo("hello from Ada", "ocr-fold", Some(b"ada-photo-fold")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_ocr_images_enabled(&ada.arch, true).unwrap();
    let weights = present_weights(&ada.root);
    ocr_image_attachments(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            let _ = bytes;
            Ok(Some("ISLAK".to_string()))
        },
    )
    .unwrap();
    assert_eq!(
        ocr_of(&ada.arch, attachment_id).as_deref(),
        Some("ISLAK"),
        "OCR-FOLD: stored text is the stub string, not pre-folded"
    );
    assert!(
        search_ids(&ada.arch, "ıslak").contains(&message_id),
        "OCR-FOLD: query ıslak must hit {message_id}"
    );
    assert!(
        search_ids(&ada.arch, "islak").contains(&message_id),
        "OCR-FOLD: query islak must hit {message_id}"
    );
    close(ada);
}

#[test]
fn ocr_rerun_same_string_keeps_dual_fold_count() {
    let ada = open_ada("rerun");
    let (message_id, attachment_id) = add_note(
        &ada,
        &photo("hello from Ada", "ocr-rerun", Some(b"ada-photo-rerun")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    store_ocr_text(&ada.arch, attachment_id, TOKEN).unwrap();
    let text = search_text_of(&ada.arch, message_id);
    assert_eq!(
        token_copies(&text),
        2,
        "OCR-RERUN: first store is the dual-fold count"
    );
    store_ocr_text(&ada.arch, attachment_id, TOKEN).unwrap();
    let again = search_text_of(&ada.arch, message_id);
    assert_eq!(
        again, text,
        "OCR-RERUN: a second assignment of the same string keeps search_text"
    );
    assert_eq!(
        token_copies(&again),
        2,
        "OCR-RERUN: dual-fold count must stay 2, not 4"
    );
    assert_eq!(
        ocr_of(&ada.arch, attachment_id).as_deref(),
        Some(TOKEN),
        "OCR-RERUN: column is replaced, not concatenated"
    );
    close(ada);
}

#[test]
fn ocr_hidden_misses_token_and_secret() {
    let ada = open_ada("hidden");
    let mut deleted = photo("secret", "ocr-hidden-deleted", Some(b"ada-photo-deleted"));
    deleted.edit_state = "deleted";
    let mut stone = photo("secret", "ocr-hidden-stone", Some(b"ada-photo-stone"));
    stone.tombstone = 1;
    let (deleted_msg, deleted_att) = add_note(&ada, &deleted);
    let (stone_msg, stone_att) = add_note(&ada, &stone);
    index_import_run(&ada.arch, ada.run_id).unwrap();
    store_ocr_text(&ada.arch, deleted_att, TOKEN).unwrap();
    store_ocr_text(&ada.arch, stone_att, TOKEN).unwrap();
    assert_eq!(
        body_of(&ada.arch, deleted_msg),
        "secret",
        "OCR-HIDDEN: deleted body stays secret"
    );
    assert_eq!(
        body_of(&ada.arch, stone_msg),
        "secret",
        "OCR-HIDDEN: tombstone body stays secret"
    );
    assert_eq!(
        ocr_of(&ada.arch, deleted_att).as_deref(),
        Some(TOKEN),
        "OCR-HIDDEN: deleted row still stores ocr_text"
    );
    assert_eq!(
        ocr_of(&ada.arch, stone_att).as_deref(),
        Some(TOKEN),
        "OCR-HIDDEN: tombstoned row still stores ocr_text"
    );
    let token_hits = search_ids(&ada.arch, TOKEN);
    assert!(
        !token_hits.contains(&deleted_msg) && !token_hits.contains(&stone_msg),
        "OCR-HIDDEN: search must miss the token, got {token_hits:?}"
    );
    let secret_hits = search_ids(&ada.arch, "secret");
    assert!(
        !secret_hits.contains(&deleted_msg) && !secret_hits.contains(&stone_msg),
        "OCR-HIDDEN: search must miss secret, got {secret_hits:?}"
    );
    for message_id in [deleted_msg, stone_msg] {
        let text = search_text_of(&ada.arch, message_id);
        assert!(
            !text.contains(TOKEN),
            "OCR-HIDDEN: ocr_text folded into search_text: {text}"
        );
        assert!(
            !text.contains("secret"),
            "OCR-HIDDEN: hidden body is still in search_text: {text}"
        );
    }
    close(ada);
}

#[test]
fn ocr_off_writes_nothing_and_keeps_stored() {
    let ada = open_ada("off");
    let (stored_msg, stored_att) = add_note(
        &ada,
        &photo(
            "hello from Ada",
            "ocr-off-stored",
            Some(b"ada-photo-off-stored"),
        ),
    );
    let (_null_msg, null_att) = add_note(
        &ada,
        &photo(
            "second note from Ada",
            "ocr-off-null",
            Some(b"ada-photo-off-null"),
        ),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    store_ocr_text(&ada.arch, stored_att, TOKEN).unwrap();
    let stored_text = search_text_of(&ada.arch, stored_msg);
    let weights = present_weights(&ada.root);
    assert!(
        !ocr_images_enabled(&ada.arch).unwrap(),
        "OCR-OFF: a missing settings row is off"
    );
    assert!(
        setting_value(&ada.arch).is_none(),
        "OCR-OFF: init does not insert ocr_images"
    );
    let mut calls = 0u32;
    ocr_image_attachments(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls += 1;
            let _ = bytes;
            Ok(Some("offquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(calls, 0, "OCR-OFF: missing setting must not call decode");
    assert_eq!(
        ocr_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "OCR-OFF: existing ocr_text stays while the setting is missing"
    );
    assert!(
        ocr_of(&ada.arch, null_att).is_none(),
        "OCR-OFF: NULL image row stays NULL while the setting is missing"
    );
    assert!(
        search_ids(&ada.arch, TOKEN).contains(&stored_msg),
        "OCR-OFF: an existing ocr_text stays searchable"
    );
    assert!(
        !search_ids(&ada.arch, "offquartzother").contains(&stored_msg),
        "OCR-OFF: decode text was not written"
    );
    set_ocr_images_enabled(&ada.arch, false).unwrap();
    assert!(!ocr_images_enabled(&ada.arch).unwrap(), "OCR-OFF: off");
    assert_eq!(
        setting_value(&ada.arch).as_deref(),
        Some("off"),
        "OCR-OFF: settings value"
    );
    assert_eq!(
        ocr_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "OCR-OFF: set_ocr_images_enabled(false) leaves the column"
    );
    ocr_image_attachments(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls += 1;
            let _ = bytes;
            Ok(Some("offquartzother".into()))
        },
    )
    .unwrap();
    assert_eq!(calls, 0, "OCR-OFF: off must not call decode");
    assert_eq!(
        ocr_of(&ada.arch, stored_att).as_deref(),
        Some(TOKEN),
        "OCR-OFF: off does not clear a stored ocr_text"
    );
    assert!(
        ocr_of(&ada.arch, null_att).is_none(),
        "OCR-OFF: off does not fill a NULL image row"
    );
    assert_eq!(
        search_text_of(&ada.arch, stored_msg),
        stored_text,
        "OCR-OFF: search_text unchanged"
    );
    assert_eq!(
        token_copies(&search_text_of(&ada.arch, stored_msg)),
        2,
        "OCR-OFF: dual-fold count stays"
    );
    close(ada);
}

#[test]
fn ocr_blur_none_leaves_row_unchanged() {
    let ada = open_ada("blur");
    let (message_id, attachment_id) = add_note(
        &ada,
        &photo("hello from Ada", "ocr-blur", Some(b"ada-photo-blur")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_ocr_images_enabled(&ada.arch, true).unwrap();
    let body = body_of(&ada.arch, message_id);
    let text = search_text_of(&ada.arch, message_id);
    let weights = present_weights(&ada.root);
    let mut calls = 0u32;
    let result = ocr_image_attachments(
        &ada.arch,
        &weights,
        |bytes: &[u8]| -> Result<Option<String>, CoreError> {
            calls += 1;
            let _ = bytes;
            Ok(None)
        },
    );
    assert!(
        result.is_ok(),
        "OCR-BLUR: None still returns success, got {result:?}"
    );
    assert_eq!(calls, 1, "OCR-BLUR: the image is decoded");
    assert!(
        ocr_of(&ada.arch, attachment_id).is_none(),
        "OCR-BLUR: ocr_text stays null"
    );
    assert_eq!(body_of(&ada.arch, message_id), body, "OCR-BLUR: body_text");
    assert_eq!(
        search_text_of(&ada.arch, message_id),
        text,
        "OCR-BLUR: search_text unchanged"
    );
    close(ada);
}

#[test]
fn ocr_which_decodes_only_eligible_images() {
    let ada = open_ada("which");
    let sticker_bytes = b"which-sticker";
    let voice_bytes = b"which-voice";
    let file_bytes = b"which-file-null-mime";
    let video_bytes = b"which-video";
    let inline_bytes = b"which-inline-jpeg";
    let png_bytes = b"which-file-png";

    let mut sticker = photo("hello from Ada", "ocr-which-sticker", Some(sticker_bytes));
    sticker.kind = "sticker";
    sticker.mime = Some("image/webp");
    sticker.filename = "ada-sticker.webp";
    let (_sticker_msg, sticker_att) = add_note(&ada, &sticker);

    let mut voice = photo("hello from Ada", "ocr-which-voice", Some(voice_bytes));
    voice.kind = "voice";
    voice.mime = Some("audio/ogg");
    voice.filename = "ada-voice.opus";
    let (_voice_msg, voice_att) = add_note(&ada, &voice);

    let mut file = photo("hello from Ada", "ocr-which-file", Some(file_bytes));
    file.kind = "file";
    file.mime = None;
    file.filename = "ada-file.bin";
    let (_file_msg, file_att) = add_note(&ada, &file);

    let mut nocas = photo("hello from Ada", "ocr-which-nocas", None);
    nocas.kind = "image";
    let (_nocas_msg, nocas_att) = add_note(&ada, &nocas);

    let mut video = photo("hello from Ada", "ocr-which-video", Some(video_bytes));
    video.kind = "video";
    video.mime = Some("video/mp4");
    video.filename = "ada-clip.mp4";
    let (_video_msg, video_att) = add_note(&ada, &video);

    let mut inline = photo("hello from Ada", "ocr-which-inline", Some(inline_bytes));
    inline.kind = "inline";
    inline.mime = Some("image/jpeg");
    inline.filename = "ada-inline.jpg";
    let (inline_msg, inline_att) = add_note(&ada, &inline);

    let mut png = photo("hello from Ada", "ocr-which-png", Some(png_bytes));
    png.kind = "file";
    png.mime = Some("image/png");
    png.filename = "ada-file.png";
    let (png_msg, png_att) = add_note(&ada, &png);

    index_import_run(&ada.arch, ada.run_id).unwrap();
    set_ocr_images_enabled(&ada.arch, true).unwrap();
    let pending: Vec<i64> = pending_ocr_rows(&ada.arch)
        .unwrap()
        .into_iter()
        .map(|(id, _hash)| id)
        .collect();
    assert_eq!(
        pending,
        vec![inline_att, png_att],
        "OCR-WHICH: only inline image/jpeg and file image/png are pending"
    );
    let weights = present_weights(&ada.root);
    let mut calls: Vec<Vec<u8>> = Vec::new();
    ocr_image_attachments(
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
        vec![inline_bytes.to_vec(), png_bytes.to_vec()],
        "OCR-WHICH: sticker, voice, null-mime file, null cas_hash, and video are not decoded"
    );
    for attachment_id in [sticker_att, voice_att, file_att, nocas_att, video_att] {
        assert!(
            ocr_of(&ada.arch, attachment_id).is_none(),
            "OCR-WHICH: skipped row {attachment_id} ocr_text stays null"
        );
    }
    assert_eq!(
        ocr_of(&ada.arch, inline_att).as_deref(),
        Some(TOKEN),
        "OCR-WHICH: inline image/jpeg is stored"
    );
    assert_eq!(
        ocr_of(&ada.arch, png_att).as_deref(),
        Some(TOKEN),
        "OCR-WHICH: file image/png is stored"
    );
    let hits = search_ids(&ada.arch, TOKEN);
    assert!(
        hits.contains(&inline_msg) && hits.contains(&png_msg),
        "OCR-WHICH: eligible images hit, got {hits:?}"
    );
    close(ada);
}

#[test]
fn ocr_voice_transcript_stays_searchable() {
    let ada = open_ada("voice");
    let mut voice = photo("hello from Ada", "ocr-voice-note", Some(b"ada-voice-row"));
    voice.kind = "voice";
    voice.mime = Some("audio/ogg");
    voice.filename = "ada-voice.opus";
    let (message_id, voice_att) = add_note(&ada, &voice);
    let photo_att = insert_attachment(
        &ada,
        message_id,
        &photo("hello from Ada", "ocr-voice-photo", Some(b"ada-photo-row")),
    );
    ada.arch
        .conn
        .execute(
            "UPDATE attachments SET transcript = ?1 WHERE id = ?2",
            rusqlite::params![VOICE_TOKEN, voice_att],
        )
        .unwrap();
    index_import_run(&ada.arch, ada.run_id).unwrap();
    assert_eq!(
        transcript_of(&ada.arch, voice_att).as_deref(),
        Some(VOICE_TOKEN),
        "OCR-VOICE: transcript column"
    );
    assert!(
        search_ids(&ada.arch, VOICE_TOKEN).contains(&message_id),
        "OCR-VOICE: transcript is searchable before the photo store"
    );
    store_ocr_text(&ada.arch, photo_att, TOKEN).unwrap();
    assert_eq!(
        transcript_of(&ada.arch, voice_att).as_deref(),
        Some(VOICE_TOKEN),
        "OCR-VOICE: photo store leaves the transcript column"
    );
    assert_eq!(
        ocr_of(&ada.arch, photo_att).as_deref(),
        Some(TOKEN),
        "OCR-VOICE: ocr_text column"
    );
    assert!(
        search_ids(&ada.arch, VOICE_TOKEN).contains(&message_id),
        "OCR-VOICE: transcript is still searchable after the photo store"
    );
    assert!(
        search_ids(&ada.arch, TOKEN).contains(&message_id),
        "OCR-VOICE: photo token is searchable"
    );
    let text = search_text_of(&ada.arch, message_id);
    assert_eq!(
        text.matches(VOICE_TOKEN).count(),
        2,
        "OCR-VOICE: transcript dual-fold count stays 2"
    );
    assert_eq!(
        token_copies(&text),
        2,
        "OCR-VOICE: photo token dual-fold count is 2"
    );
    close(ada);
}

#[test]
fn ocr_epoch_stays_1() {
    let root = tmp_root("epoch");
    let arch = init_archive(&root).unwrap();
    migrate(&arch.conn).unwrap();
    migrate(&arch.conn).unwrap();
    assert_eq!(schema_epoch(&arch), 1, "OCR-EPOCH");
    drop(arch);
    let _ = std::fs::remove_dir_all(root);
}

#[test]
fn ocr_import_leaves_ocr_text_null() {
    let ada = open_ada("import");
    let (message_id, attachment_id) = add_note(
        &ada,
        &photo("hello from Ada", "ocr-import", Some(b"ada-photo-import")),
    );
    index_import_run(&ada.arch, ada.run_id).unwrap();
    assert!(
        ocr_of(&ada.arch, attachment_id).is_none(),
        "OCR-IMPORT: index_import_run leaves ocr_text null"
    );
    assert!(
        !ocr_images_enabled(&ada.arch).unwrap(),
        "OCR-IMPORT: import does not enable the switch"
    );
    assert!(
        !search_ids(&ada.arch, TOKEN).contains(&message_id),
        "OCR-IMPORT: import does not call a model"
    );
    let pending: Vec<i64> = pending_ocr_rows(&ada.arch)
        .unwrap()
        .into_iter()
        .map(|(id, _hash)| id)
        .collect();
    assert!(
        pending.contains(&attachment_id),
        "OCR-IMPORT: the image stays pending, got {pending:?}"
    );
    let run_id = another_run(&ada);
    let mut second = photo(
        "second hello from Ada",
        "ocr-import-2",
        Some(b"ada-photo-import-2"),
    );
    second.run_id = Some(run_id);
    let (_second_msg, second_att) = add_note(&ada, &second);
    index_import_run(&ada.arch, run_id).unwrap();
    assert!(
        ocr_of(&ada.arch, attachment_id).is_none() && ocr_of(&ada.arch, second_att).is_none(),
        "OCR-IMPORT: indexing another run does not set ocr_text"
    );
    close(ada);
}
