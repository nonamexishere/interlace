use std::collections::HashMap;

use rusqlite::{Connection, OptionalExtension};

use crate::db::Archive;
use crate::model::CoreError;

use super::{ConversationParticipantName, PersonIdentity, PersonSummary};

const PREVIEW_MAX_CHARS: usize = 160;

/// One-line list preview: subject if the last D18 row has one, else truncated
/// `body_text` with HTML tags stripped. Empty / missing text → `None`.
pub(super) fn list_preview(subject: Option<&str>, body_text: &str) -> Option<String> {
    let subject = subject.map(str::trim).filter(|s| !s.is_empty());
    if let Some(s) = subject {
        let t = truncate_one_line(s, PREVIEW_MAX_CHARS);
        return if t.is_empty() { None } else { Some(t) };
    }
    let plain = strip_html_tags(body_text);
    let t = truncate_one_line(&plain, PREVIEW_MAX_CHARS);
    if t.is_empty() {
        None
    } else {
        Some(t)
    }
}

fn strip_html_tags(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut in_tag = false;
    for c in s.chars() {
        match c {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => out.push(c),
            _ => {}
        }
    }
    out
}

fn truncate_one_line(s: &str, max: usize) -> String {
    let line: String = s
        .chars()
        .map(|c| if c == '\n' || c == '\r' { ' ' } else { c })
        .take(max)
        .collect();
    line.trim().to_string()
}

/// Fill each person's linked `value_normalized` for client-side people filter (#138).
pub(super) fn attach_identity_values(
    conn: &Connection,
    people: &mut [PersonSummary],
) -> Result<(), CoreError> {
    if people.is_empty() {
        return Ok(());
    }
    let mut by_person: HashMap<i64, Vec<String>> = HashMap::new();
    let mut stmt = conn.prepare(
        "SELECT pi.person_id, i.value_normalized
         FROM person_identities pi
         JOIN identities i ON i.id = pi.identity_id
         ORDER BY pi.person_id, i.id",
    )?;
    let rows = stmt.query_map([], |r| {
        let pid: i64 = r.get(0)?;
        let value: String = r.get(1)?;
        Ok((pid, value))
    })?;
    for row in rows {
        let (pid, value) = row?;
        if !value.is_empty() {
            by_person.entry(pid).or_default().push(value);
        }
    }
    for p in people.iter_mut() {
        p.identity_values = by_person.remove(&p.id).unwrap_or_default();
    }
    Ok(())
}

/// Fill each person's first Contacts PHOTO hash (`MIN(contacts_raw.id)` among non-null).
pub(super) fn attach_photo_hashes(
    conn: &Connection,
    people: &mut [PersonSummary],
) -> Result<(), CoreError> {
    if people.is_empty() {
        return Ok(());
    }
    let mut by_person: HashMap<i64, String> = HashMap::new();
    let mut stmt = conn.prepare(
        "SELECT pi.person_id, cr.photo_cas_hash
         FROM person_identities pi
         JOIN contact_channels cc ON cc.identity_id = pi.identity_id
         JOIN contacts_raw cr ON cr.id = cc.contact_id
         WHERE cr.photo_cas_hash IS NOT NULL AND TRIM(cr.photo_cas_hash) != ''
         ORDER BY cr.id",
    )?;
    let rows = stmt.query_map([], |r| {
        let pid: i64 = r.get(0)?;
        let hash: String = r.get(1)?;
        Ok((pid, hash))
    })?;
    for row in rows {
        let (pid, hash) = row?;
        by_person.entry(pid).or_insert(hash);
    }
    for p in people.iter_mut() {
        p.photo_cas_hash = by_person.remove(&p.id);
    }
    Ok(())
}

/// People the UI may offer as merge targets for `selected_id`.
///
/// Drops the selected person and, unless `allow_self`, anyone with `is_self`.
/// `query` is a casefold substring of `display_name` only — a query that looks
/// like a numeric id matches nobody. Empty query keeps every remaining person.
pub fn merge_targets(
    people: &[PersonSummary],
    selected_id: i64,
    allow_self: bool,
    query: &str,
) -> Vec<PersonSummary> {
    let q = query.trim().to_lowercase();
    people
        .iter()
        .filter(|p| p.id != selected_id)
        .filter(|p| allow_self || !p.is_self)
        .filter(|p| q.is_empty() || p.display_name.to_lowercase().contains(&q))
        .cloned()
        .collect()
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

/// Names on one conversation: identity `display_name` then `value`. Includes `role=me`.
pub fn conversation_participant_names(
    archive: &Archive,
    conversation_id: i64,
) -> Result<Vec<ConversationParticipantName>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT cp.identity_id, i.display_name, COALESCE(i.value_normalized, i.value_raw), p.id
         FROM conversation_participants cp
         JOIN identities i ON i.id = cp.identity_id
         LEFT JOIN person_identities pi ON pi.identity_id = cp.identity_id
         LEFT JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
         WHERE cp.conversation_id = ?1
         ORDER BY cp.identity_id",
    )?;
    let rows = stmt.query_map([conversation_id], |r| {
        Ok(ConversationParticipantName {
            identity_id: r.get(0)?,
            display_name: r.get(1)?,
            value: r.get(2)?,
            person_id: r.get(3)?,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

/// Who was in this group at `message_id`'s `sent_at`.
/// No id, no `sent_at`, or no membership rows → the current undated list.
/// Half-open spans (in at `joined_at`, out at `left_at`). A person with no
/// span stays on the current list. NULL bounds do not hide that side.
pub fn conversation_participant_names_at(
    archive: &Archive,
    conversation_id: i64,
    message_id: Option<i64>,
) -> Result<Vec<ConversationParticipantName>, CoreError> {
    let Some(message_id) = message_id else {
        return conversation_participant_names(archive, conversation_id);
    };
    let sent_at = archive
        .conn
        .query_row(
            "SELECT sent_at FROM messages WHERE id = ?1",
            [message_id],
            |r| r.get::<_, Option<String>>(0),
        )
        .optional()?
        .flatten();
    let Some(at) = sent_at.filter(|s| !s.is_empty()) else {
        return conversation_participant_names(archive, conversation_id);
    };
    let n_spans: i64 = archive.conn.query_row(
        "SELECT COUNT(*) FROM group_membership WHERE conversation_id = ?1",
        [conversation_id],
        |r| r.get(0),
    )?;
    if n_spans == 0 {
        return conversation_participant_names(archive, conversation_id);
    }
    let mut stmt = archive.conn.prepare(
        "SELECT i.id, i.display_name, COALESCE(i.value_normalized, i.value_raw), p.id
         FROM identities i
         LEFT JOIN person_identities pi ON pi.identity_id = i.id
         LEFT JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
         WHERE i.id IN (
            SELECT gm.identity_id FROM group_membership gm
            WHERE gm.conversation_id = ?1
              AND (gm.joined_at IS NULL OR gm.joined_at <= ?2)
              AND (gm.left_at IS NULL OR gm.left_at > ?2)
            UNION
            SELECT cp.identity_id FROM conversation_participants cp
            WHERE cp.conversation_id = ?1
              AND NOT EXISTS (
                SELECT 1 FROM group_membership gm
                WHERE gm.conversation_id = cp.conversation_id
                  AND gm.identity_id = cp.identity_id
              )
         )
         ORDER BY i.id",
    )?;
    let rows = stmt.query_map(rusqlite::params![conversation_id, at], |r| {
        Ok(ConversationParticipantName {
            identity_id: r.get(0)?,
            display_name: r.get(1)?,
            value: r.get(2)?,
            person_id: r.get(3)?,
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
