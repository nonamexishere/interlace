//! Person list / show / timeline rows for CLI and Tauri (D18).

use std::collections::HashMap;

use rusqlite::OptionalExtension;
use serde::Serialize;

use crate::db::Archive;
use crate::model::CoreError;

const TIMELINE_DEFAULT: u32 = 100;
const TIMELINE_MAX: u32 = 200;

#[derive(Debug, Clone, Serialize)]
pub struct PersonSummary {
    pub id: i64,
    pub display_name: String,
    pub is_self: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct PersonIdentity {
    pub id: i64,
    pub platform: String,
    pub kind: String,
    pub value: String,
    pub display_name: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AttachmentRef {
    pub id: i64,
    pub cas_hash: Option<String>,
    pub filename: Option<String>,
    pub mime: Option<String>,
    pub kind: String,
    pub omitted: bool,
    pub missing: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct TimelineRow {
    pub message_id: i64,
    pub sent_at: Option<String>,
    pub conversation_id: i64,
    pub conversation_title: Option<String>,
    pub conversation_kind: String,
    pub platform: String,
    pub sender_identity_id: Option<i64>,
    pub from_me: bool,
    pub subject: Option<String>,
    pub body_text: String,
    pub attachments: Vec<AttachmentRef>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LinkEvent {
    pub id: i64,
    pub ts: String,
    pub op: String,
}

pub fn person_list(archive: &Archive) -> Result<Vec<PersonSummary>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT id, display_name, is_self FROM persons
         WHERE tombstoned_at IS NULL
         ORDER BY is_self DESC, display_name COLLATE NOCASE, id",
    )?;
    let rows = stmt.query_map([], |r| {
        Ok(PersonSummary {
            id: r.get(0)?,
            display_name: r.get(1)?,
            is_self: r.get::<_, i64>(2)? == 1,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

pub fn person_identities(
    archive: &Archive,
    person_id: i64,
) -> Result<Vec<PersonIdentity>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT i.id, i.platform, i.kind, i.value_normalized, i.display_name
         FROM person_identities pi
         JOIN identities i ON i.id = pi.identity_id
         WHERE pi.person_id = ?1
         ORDER BY i.id",
    )?;
    let rows = stmt.query_map([person_id], |r| {
        Ok(PersonIdentity {
            id: r.get(0)?,
            platform: r.get(1)?,
            kind: r.get(2)?,
            value: r.get(3)?,
            display_name: r.get(4)?,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

pub fn person_display_name(archive: &Archive, person_id: i64) -> Result<String, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT display_name FROM persons WHERE id=?1 AND tombstoned_at IS NULL",
            [person_id],
            |r| r.get(0),
        )
        .map_err(|_| CoreError::Config(format!("no live person {person_id}")))
}

/// D18 timeline with optional `before` sent_at cursor (exclusive, descending).
pub fn person_timeline_rows(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
) -> Result<Vec<TimelineRow>, CoreError> {
    let limit = limit.clamp(1, TIMELINE_MAX);
    let limit = if limit == 0 { TIMELINE_DEFAULT } else { limit };
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let cursor_sql = if before.is_some() {
        "AND m.sent_at IS NOT NULL AND m.sent_at < ?3"
    } else {
        ""
    };
    let sql = format!(
        "SELECT m.id, m.sent_at, m.conversation_id, c.title, c.kind, c.platform,
                m.sender_identity_id, m.subject, COALESCE(m.body_text, ''),
                CASE WHEN m.sender_identity_id IS NOT NULL AND (
                    EXISTS (SELECT 1 FROM self_identities si
                            WHERE si.identity_id = m.sender_identity_id)
                 OR EXISTS (
                        SELECT 1 FROM person_identities pi
                        JOIN persons p ON p.id = pi.person_id
                        WHERE pi.identity_id = m.sender_identity_id
                          AND p.is_self = 1 AND p.tombstoned_at IS NULL
                    )
                ) THEN 1 ELSE 0 END
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE (
                m.sender_identity_id IN (
                    SELECT identity_id FROM person_identities WHERE person_id = ?1
                )
             OR (
                    m.conversation_id IN (
                      SELECT cp.conversation_id
                      FROM conversation_participants cp
                      JOIN person_identities pi ON pi.identity_id = cp.identity_id
                      WHERE pi.person_id = ?1
                    )
                    {group_sql}
                )
              )
           {cursor_sql}
         ORDER BY m.sent_at IS NULL, m.sent_at DESC, m.id DESC
         LIMIT ?2"
    );
    let mut stmt = archive.conn.prepare(&sql)?;
    let map_row = |r: &rusqlite::Row<'_>| {
        Ok(TimelineRow {
            message_id: r.get(0)?,
            sent_at: r.get(1)?,
            conversation_id: r.get(2)?,
            conversation_title: r.get(3)?,
            conversation_kind: r.get(4)?,
            platform: r.get(5)?,
            sender_identity_id: r.get(6)?,
            subject: r.get(7)?,
            body_text: r.get(8)?,
            from_me: r.get::<_, i64>(9)? == 1,
            attachments: Vec::new(),
        })
    };
    // helper kept below attach_attachments
    let rows = if let Some(b) = before {
        stmt.query_map(rusqlite::params![person_id, limit as i64, b], map_row)?
    } else {
        stmt.query_map(rusqlite::params![person_id, limit as i64], map_row)?
    };
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    attach_attachments(archive, &mut out)?;
    enrich_from_body_tokens(archive, &mut out)?;
    Ok(out)
}

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

fn enrich_from_body_tokens(archive: &Archive, rows: &mut [TimelineRow]) -> Result<(), CoreError> {
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

fn attach_attachments(archive: &Archive, rows: &mut [TimelineRow]) -> Result<(), CoreError> {
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

pub fn recent_link_events(archive: &Archive, limit: u32) -> Result<Vec<LinkEvent>, CoreError> {
    let limit = limit.clamp(1, 50);
    let mut stmt = archive
        .conn
        .prepare("SELECT id, ts, op FROM identity_link_events ORDER BY id DESC LIMIT ?1")?;
    let rows = stmt.query_map([limit as i64], |r| {
        Ok(LinkEvent {
            id: r.get(0)?,
            ts: r.get(1)?,
            op: r.get(2)?,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}
