//! Voice-note transcripts. This crate stores text. It does not link a model.

use std::path::Path;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::CoreError;
use crate::search::reindex_message_search;

const KEY: &str = "transcribe_voice";

pub fn voice_transcribe_enabled(archive: &Archive) -> Result<bool, CoreError> {
    let value: Option<String> = archive
        .conn
        .query_row("SELECT value FROM settings WHERE key = ?1", [KEY], |r| {
            r.get(0)
        })
        .optional()?;
    Ok(value.as_deref() == Some("on"))
}

pub fn set_voice_transcribe_enabled(archive: &Archive, on: bool) -> Result<(), CoreError> {
    let value = if on { "on" } else { "off" };
    archive.conn.execute(
        "INSERT INTO settings(key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        rusqlite::params![KEY, value],
    )?;
    Ok(())
}

pub fn store_voice_transcript(
    archive: &Archive,
    attachment_id: i64,
    text: &str,
) -> Result<(), CoreError> {
    if text.trim().is_empty() {
        return Err(CoreError::Parse("empty voice transcript".into()));
    }
    with_immediate(archive, || {
        let changed = archive.conn.execute(
            "UPDATE attachments SET transcript = ?1 WHERE id = ?2",
            rusqlite::params![text, attachment_id],
        )?;
        if changed == 0 {
            return Err(CoreError::Parse(format!(
                "attachment {attachment_id} not found"
            )));
        }
        let message_id: i64 = archive.conn.query_row(
            "SELECT message_id FROM attachments WHERE id = ?1",
            [attachment_id],
            |r| r.get(0),
        )?;
        reindex_message_search(archive, message_id)
    })
}

pub fn transcribe_voice_notes(
    archive: &Archive,
    weights_path: &Path,
    mut decode: impl FnMut(&[u8]) -> Result<Option<String>, CoreError>,
) -> Result<(), CoreError> {
    if !voice_transcribe_enabled(archive)? || !weights_path.is_file() {
        return Ok(());
    }
    let rows: Vec<(i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT id, cas_hash FROM attachments
             WHERE kind = 'voice' AND cas_hash IS NOT NULL AND transcript IS NULL
             ORDER BY id",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (id, hash) in rows {
        let bytes = match archive.cas_get(&hash) {
            Ok(bytes) => bytes,
            Err(_) => continue,
        };
        let text = match decode(&bytes) {
            Ok(Some(text)) => text,
            Ok(None) | Err(_) => continue,
        };
        if text.trim().is_empty() {
            continue;
        }
        store_voice_transcript(archive, id, &text)?;
    }
    Ok(())
}

fn with_immediate<T>(
    archive: &Archive,
    body: impl FnOnce() -> Result<T, CoreError>,
) -> Result<T, CoreError> {
    archive.conn.execute_batch("BEGIN IMMEDIATE")?;
    match body() {
        Ok(value) => match archive.conn.execute_batch("COMMIT") {
            Ok(()) => Ok(value),
            Err(err) => {
                let _ = archive.conn.execute_batch("ROLLBACK");
                Err(err.into())
            }
        },
        Err(err) => {
            let _ = archive.conn.execute_batch("ROLLBACK");
            Err(err)
        }
    }
}
