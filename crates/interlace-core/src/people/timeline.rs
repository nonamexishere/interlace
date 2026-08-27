use crate::db::Archive;
use crate::model::CoreError;

use super::attach::{attach_attachments, enrich_from_body_tokens};
use super::{PersonConversation, TimelineRow};

const TIMELINE_DEFAULT: u32 = 100;
const TIMELINE_MAX: u32 = 200;

/// D18 timeline with optional `before` sent_at cursor (exclusive, descending).
pub fn person_timeline_rows(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
) -> Result<Vec<TimelineRow>, CoreError> {
    person_timeline_rows_for(archive, person_id, include_groups, limit, before, None)
}

/// D18 timeline; `conversation_id = None` is All (merged stream).
pub fn person_timeline_rows_for(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
    conversation_id: Option<i64>,
) -> Result<Vec<TimelineRow>, CoreError> {
    let limit = limit.clamp(1, TIMELINE_MAX);
    let limit = if limit == 0 { TIMELINE_DEFAULT } else { limit };
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let cursor_sql = if before.is_some() {
        "AND m.sent_at IS NOT NULL AND m.sent_at < :before"
    } else {
        ""
    };
    let conv_sql = if conversation_id.is_some() {
        "AND m.conversation_id = :conv"
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
                    SELECT identity_id FROM person_identities WHERE person_id = :pid
                )
             OR (
                    m.conversation_id IN (
                      SELECT cp.conversation_id
                      FROM conversation_participants cp
                      JOIN person_identities pi ON pi.identity_id = cp.identity_id
                      WHERE pi.person_id = :pid
                    )
                    {group_sql}
                )
              )
           {cursor_sql}
           {conv_sql}
         ORDER BY m.sent_at IS NULL, m.sent_at DESC, m.id DESC
         LIMIT :lim"
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
    let lim = limit as i64;
    let rows = match (before, conversation_id) {
        (Some(b), Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b, ":conv": cid },
            map_row,
        )?,
        (Some(b), None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b },
            map_row,
        )?,
        (None, Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":conv": cid },
            map_row,
        )?,
        (None, None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim },
            map_row,
        )?,
    };
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    attach_attachments(archive, &mut out)?;
    enrich_from_body_tokens(archive, &mut out)?;
    Ok(out)
}

/// Conversations this person appears in (title, platform, kind, last_at).
/// Groups are omitted unless `include_groups`.
pub fn person_conversations(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
) -> Result<Vec<PersonConversation>, CoreError> {
    // Hide every group unless the toggle is on — including ones this person sent in.
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let sql = format!(
        "SELECT c.id, c.title, c.platform, c.kind, MAX(m.sent_at)
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE (
                m.sender_identity_id IN (
                    SELECT identity_id FROM person_identities WHERE person_id = ?1
                )
             OR m.conversation_id IN (
                    SELECT cp.conversation_id
                    FROM conversation_participants cp
                    JOIN person_identities pi ON pi.identity_id = cp.identity_id
                    WHERE pi.person_id = ?1
                )
              )
           {group_sql}
         GROUP BY c.id, c.title, c.platform, c.kind
         ORDER BY MAX(m.sent_at) IS NULL, MAX(m.sent_at) DESC, c.id"
    );
    let mut stmt = archive.conn.prepare(&sql)?;
    let rows = stmt.query_map([person_id], |r| {
        Ok(PersonConversation {
            id: r.get(0)?,
            title: r.get(1)?,
            platform: r.get(2)?,
            kind: r.get(3)?,
            last_at: r.get(4)?,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}
