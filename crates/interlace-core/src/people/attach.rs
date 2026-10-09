use std::collections::HashMap;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::CoreError;

use super::{AttachmentRef, TimelineReaction, TimelineRecipients, TimelineRow};

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
            "SELECT id, cas_hash, filename, mime, kind, omitted, missing, derivative_cas_hash
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
                    derivative_cas_hash: r.get(7)?,
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
                derivative_cas_hash: None,
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
        "SELECT id, message_id, cas_hash, filename, mime, kind, omitted, missing, derivative_cas_hash
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
                derivative_cas_hash: r.get(8)?,
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

/// Names from `labels` ⨝ `message_labels` for the page's `message_id`s.
/// One `IN` join; order is stable as attached (no Inbox/Sent-first reorder).
pub(super) fn attach_labels(archive: &Archive, rows: &mut [TimelineRow]) -> Result<(), CoreError> {
    if rows.is_empty() {
        return Ok(());
    }
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    let placeholders = ids.iter().map(|_| "?").collect::<Vec<_>>().join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT ml.message_id, l.name FROM message_labels ml
         JOIN labels l ON l.id = ml.label_id
         WHERE ml.message_id IN ({placeholders})"
    ))?;
    let mapped = stmt.query_map(rusqlite::params_from_iter(&ids), |r| {
        Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?))
    })?;
    let mut map: HashMap<i64, Vec<String>> = HashMap::new();
    for pair in mapped {
        let (mid, name) = pair?;
        map.entry(mid).or_default().push(name);
    }
    for row in rows.iter_mut() {
        row.labels = map.remove(&row.message_id).unwrap_or_default();
    }
    Ok(())
}

/// Names from `message_recipients` ⨝ `identities` for the page's `message_id`s.
/// One `IN` join. Name is identity `display_name` then `value_normalized` /
/// `value_raw`. Includes Self. Empty roles stay `[]`.
pub(super) fn attach_recipients(
    archive: &Archive,
    rows: &mut [TimelineRow],
) -> Result<(), CoreError> {
    if rows.is_empty() {
        return Ok(());
    }
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    let placeholders = ids.iter().map(|_| "?").collect::<Vec<_>>().join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT mr.message_id, mr.role, i.display_name, i.value_normalized, i.value_raw
         FROM message_recipients mr
         JOIN identities i ON i.id = mr.identity_id
         WHERE mr.message_id IN ({placeholders})
         ORDER BY mr.message_id, mr.role, i.id"
    ))?;
    let mapped = stmt.query_map(rusqlite::params_from_iter(&ids), |r| {
        Ok((
            r.get::<_, i64>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, Option<String>>(2)?,
            r.get::<_, String>(3)?,
            r.get::<_, String>(4)?,
        ))
    })?;
    let mut map: HashMap<i64, TimelineRecipients> = HashMap::new();
    for pair in mapped {
        let (mid, role, display_name, value_normalized, value_raw) = pair?;
        let name = match display_name
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
        {
            Some(d) => d.to_string(),
            None => {
                let n = value_normalized.trim();
                if !n.is_empty() {
                    n.to_string()
                } else {
                    value_raw.trim().to_string()
                }
            }
        };
        if name.is_empty() {
            continue;
        }
        let slot = map.entry(mid).or_default();
        match role.as_str() {
            "to" => slot.to.push(name),
            "cc" => slot.cc.push(name),
            "bcc" => slot.bcc.push(name),
            _ => {}
        }
    }
    for row in rows.iter_mut() {
        row.recipients = map.remove(&row.message_id).unwrap_or_default();
    }
    Ok(())
}

/// Reactions for this page: `message_reactions` joined to `identities.display_name`.
/// One `IN` query. Rows with none stay `[]`. Does not write an identity.
pub(super) fn attach_reactions(
    archive: &Archive,
    rows: &mut [TimelineRow],
) -> Result<(), CoreError> {
    if rows.is_empty() {
        return Ok(());
    }
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    let placeholders = ids.iter().map(|_| "?").collect::<Vec<_>>().join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT mr.message_id, COALESCE(i.display_name, ''), mr.emoji
         FROM message_reactions mr
         JOIN identities i ON i.id = mr.actor_identity_id
         WHERE mr.message_id IN ({placeholders})
         ORDER BY mr.id"
    ))?;
    let mapped = stmt.query_map(rusqlite::params_from_iter(&ids), |r| {
        Ok((
            r.get::<_, i64>(0)?,
            TimelineReaction {
                actor_display_name: r.get(1)?,
                emoji: r.get(2)?,
            },
        ))
    })?;
    let mut map: HashMap<i64, Vec<TimelineReaction>> = HashMap::new();
    for pair in mapped {
        let (mid, reaction) = pair?;
        map.entry(mid).or_default().push(reaction);
    }
    for row in rows.iter_mut() {
        row.reactions = map.remove(&row.message_id).unwrap_or_default();
    }
    Ok(())
}

/// Older wordings for this page: one `IN` query on `message_revisions`.
/// A tombstone or `edit_state = deleted` stays `[]`. A null revision body is
/// omitted. A body that exactly equals stored `messages.body_text` is omitted
/// (no trim); a null stored body does not drop a non-null revision. Order is
/// `rev_no` ascending. Does not append the current body or delete revisions.
pub(super) fn attach_previous_bodies(
    archive: &Archive,
    rows: &mut [TimelineRow],
) -> Result<(), CoreError> {
    if rows.is_empty() {
        return Ok(());
    }
    let ids: Vec<i64> = rows.iter().map(|r| r.message_id).collect();
    let placeholders = ids.iter().map(|_| "?").collect::<Vec<_>>().join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT rv.message_id, rv.body_text
         FROM message_revisions rv
         JOIN messages m ON m.id = rv.message_id
         WHERE rv.message_id IN ({placeholders})
           AND NOT (m.tombstone != 0 OR m.edit_state = 'deleted')
           AND rv.body_text IS NOT NULL
           AND (m.body_text IS NULL OR rv.body_text != m.body_text)
         ORDER BY rv.rev_no ASC"
    ))?;
    let mapped = stmt.query_map(rusqlite::params_from_iter(&ids), |r| {
        Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?))
    })?;
    let mut map: HashMap<i64, Vec<String>> = HashMap::new();
    for pair in mapped {
        let (mid, body) = pair?;
        map.entry(mid).or_default().push(body);
    }
    for row in rows.iter_mut() {
        row.previous_bodies = map.remove(&row.message_id).unwrap_or_default();
    }
    Ok(())
}
