use std::collections::HashMap;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::CoreError;

use super::{AttachmentRef, TimelineRow};

/// iOS `<attached: file.jpg>` in body (same line or continuation).
pub fn extract_attached_filenames(body: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut s = body;
    while let Some(i) = s.find("<attached:") {
        s = s[i + "<attached:".len()..].trim_start();
        let Some(j) = s.find('>') else {
            break;
        };
        let name = s[..j].trim();
        if !name.is_empty() && !name.contains("..") && !name.contains('/') {
            out.push(name.to_string());
        }
        s = &s[j + 1..];
    }
    out
}

fn guess_kind(filename: &str) -> String {
    let n = filename.to_ascii_lowercase();
    if n.contains("PHOTO")
        || n.contains("photo")
        || n.ends_with(".jpg")
        || n.ends_with(".jpeg")
        || n.ends_with(".png")
        || n.ends_with(".webp")
        || n.ends_with(".gif")
    {
        "image".into()
    } else if n.contains("STICKER") || n.contains("sticker") {
        "sticker".into()
    } else if n.contains("AUDIO")
        || n.contains("PTT")
        || n.ends_with(".opus")
        || n.ends_with(".mp3")
        || n.ends_with(".m4a")
    {
        "voice".into()
    } else {
        "file".into()
    }
}

fn lookup_filename(archive: &Archive, name: &str) -> Result<Option<AttachmentRef>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT id, cas_hash, filename, mime, kind, omitted, missing
             FROM attachments WHERE filename = ?1 AND cas_hash IS NOT NULL LIMIT 1",
            [name],
            |r| {
                Ok(AttachmentRef {
                    id: r.get(0)?,
                    cas_hash: r.get(1)?,
                    filename: r.get(2)?,
                    mime: r.get(3)?,
                    kind: r.get(4)?,
                    omitted: r.get::<_, i64>(5)? != 0,
                    missing: r.get::<_, i64>(6)? != 0,
                })
            },
        )
        .optional()
        .map_err(Into::into)
}

pub fn complete_attachments(
    archive: &Archive,
    message_id: i64,
    body: &str,
    mut v: Vec<AttachmentRef>,
) -> Result<Vec<AttachmentRef>, CoreError> {
    for name in extract_attached_filenames(body) {
        if v.iter()
            .any(|a| a.filename.as_deref() == Some(name.as_str()))
        {
            continue;
        }
        if let Some(found) = lookup_filename(archive, &name)? {
            v.push(found);
        } else {
            v.push(AttachmentRef {
                id: -message_id,
                cas_hash: None,
                filename: Some(name.clone()),
                mime: None,
                kind: guess_kind(&name),
                omitted: false,
                missing: true,
            });
        }
    }
    Ok(v)
}

pub(super) fn enrich_from_body_tokens(
    archive: &Archive,
    rows: &mut [TimelineRow],
) -> Result<(), CoreError> {
    for row in rows {
        row.attachments = complete_attachments(
            archive,
            row.message_id,
            &row.body_text,
            std::mem::take(&mut row.attachments),
        )?;
    }
    Ok(())
}

/// Attachments for a set of messages (timeline + search).
pub fn attachments_for(
    archive: &Archive,
    message_ids: &[i64],
) -> Result<HashMap<i64, Vec<AttachmentRef>>, CoreError> {
    let mut map: HashMap<i64, Vec<AttachmentRef>> = HashMap::new();
    let mut stmt = archive.conn.prepare(
        "SELECT id, message_id, cas_hash, filename, mime, kind, omitted, missing
         FROM attachments WHERE message_id = ?1 ORDER BY id",
    )?;
    for id in message_ids {
        let rows = stmt.query_map([id], |r| {
            Ok(AttachmentRef {
                id: r.get(0)?,
                cas_hash: r.get(2)?,
                filename: r.get(3)?,
                mime: r.get(4)?,
                kind: r.get(5)?,
                omitted: r.get::<_, i64>(6)? != 0,
                missing: r.get::<_, i64>(7)? != 0,
            })
        })?;
        let mut v = Vec::new();
        for row in rows {
            v.push(row?);
        }
        if !v.is_empty() {
            map.insert(*id, v);
        }
    }
    Ok(map)
}

pub(super) fn attach_attachments(
    archive: &Archive,
    rows: &mut [TimelineRow],
) -> Result<(), CoreError> {
    if rows.is_empty() {
        return Ok(());
    }
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    let mut map = attachments_for(archive, &ids)?;
    for row in rows.iter_mut() {
        row.attachments = map.remove(&row.message_id).unwrap_or_default();
    }
    Ok(())
}
