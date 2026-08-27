//! Person list / show / timeline rows for CLI and Tauri (D18).

mod attach;
mod list;
mod timeline;

use rusqlite::Connection;
use serde::Serialize;

use crate::db::Archive;
use crate::model::CoreError;

pub use attach::{attachments_for, complete_attachments, extract_attached_filenames};
pub use list::{merge_targets, person_display_name, person_identities};
pub use timeline::{person_conversations, person_timeline_rows, person_timeline_rows_for};

#[derive(Debug, Clone, Serialize)]
pub struct PersonSummary {
    pub id: i64,
    pub display_name: String,
    pub is_self: bool,
    pub last_activity_at: Option<String>,
    pub preview: Option<String>,
    /// Linked identities' `value_normalized` (phone/email) for client-side filter.
    pub identity_values: Vec<String>,
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

/// One conversation on a person's switcher. `last_at` is the latest D18
/// `sent_at` in that conversation for this person.
#[derive(Debug, Clone, Serialize)]
pub struct PersonConversation {
    pub id: i64,
    pub title: Option<String>,
    pub platform: String,
    pub kind: String,
    pub last_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LinkEvent {
    pub id: i64,
    pub ts: String,
    pub op: String,
    pub actor: String,
    /// Set on `split_person` rows: the event this undo reversed.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub undo_of: Option<i64>,
    /// Merge payload display name for the absorbed person (sidebar undo label).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loser_display_name: Option<String>,
    /// Link / unlink payload person (sidebar undo label via people list).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub person_id: Option<i64>,
    /// Merge payload survivor id.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub keep: Option<i64>,
    /// Merge payload absorbed person id.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loser: Option<i64>,
}

pub fn person_list(archive: &Archive) -> Result<Vec<PersonSummary>, CoreError> {
    person_list_on(&archive.conn)
}

/// Same contract as `person_list` (groups off) on a caller-owned connection.
/// Used for a second WAL snapshot so the primary `Archive` stays free (#265).
/// Does not flock and does not open an archive.
pub fn person_list_on(conn: &Connection) -> Result<Vec<PersonSummary>, CoreError> {
    person_list_on_with_groups(conn, false)
}

/// Live persons with last D18 activity + preview.
/// `include_groups = false` (the `person_list` default): sender, or participant
/// of `dm` / `email_thread`. Sort: self first, `sent_at` desc, nulls last, `id`.
pub fn person_list_with_groups(
    archive: &Archive,
    include_groups: bool,
) -> Result<Vec<PersonSummary>, CoreError> {
    person_list_on_with_groups(&archive.conn, include_groups)
}

fn person_list_on_with_groups(
    conn: &Connection,
    include_groups: bool,
) -> Result<Vec<PersonSummary>, CoreError> {
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let sql = format!(
        "SELECT p.id, p.display_name, p.is_self,
                act.sent_at, act.subject, act.body_text
         FROM persons p
         LEFT JOIN (
           SELECT person_id, sent_at, subject, body_text
           FROM (
             SELECT pi.person_id AS person_id,
                    m.sent_at AS sent_at,
                    m.subject AS subject,
                    COALESCE(m.body_text, '') AS body_text,
                    ROW_NUMBER() OVER (
                      PARTITION BY pi.person_id
                      ORDER BY m.sent_at IS NULL, m.sent_at DESC, m.id DESC
                    ) AS rn
             FROM messages m
             JOIN conversations c ON c.id = m.conversation_id
             JOIN person_identities pi ON (
                    pi.identity_id = m.sender_identity_id
                 OR (
                        m.conversation_id IN (
                          SELECT cp.conversation_id
                          FROM conversation_participants cp
                          WHERE cp.identity_id = pi.identity_id
                        )
                        {group_sql}
                    )
             )
           ) ranked
           WHERE rn = 1
         ) act ON act.person_id = p.id
         WHERE p.tombstoned_at IS NULL
         ORDER BY p.is_self DESC, act.sent_at IS NULL, act.sent_at DESC, p.id"
    );
    let tx = conn.unchecked_transaction()?;
    let mut stmt = conn.prepare(&sql)?;
    let rows = stmt.query_map([], |r| {
        let subject: Option<String> = r.get(4)?;
        let body: Option<String> = r.get(5)?;
        let preview = match (subject.as_deref(), body.as_deref()) {
            (None, None) => None,
            (s, b) => list::list_preview(s, b.unwrap_or("")),
        };
        Ok(PersonSummary {
            id: r.get(0)?,
            display_name: r.get(1)?,
            is_self: r.get::<_, i64>(2)? == 1,
            last_activity_at: r.get(3)?,
            preview,
            identity_values: Vec::new(),
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    list::attach_identity_values(conn, &mut out)?;
    tx.commit()?;
    Ok(out)
}

pub fn recent_link_events(archive: &Archive, limit: u32) -> Result<Vec<LinkEvent>, CoreError> {
    let limit = limit.clamp(1, 50);
    let mut stmt = archive.conn.prepare(
        "SELECT id, ts, op, actor, payload_json FROM identity_link_events
         ORDER BY id DESC LIMIT ?1",
    )?;
    let rows = stmt.query_map([limit as i64], |r| {
        let payload: String = r.get(4)?;
        let v = serde_json::from_str::<serde_json::Value>(&payload).ok();
        let undo_of = v
            .as_ref()
            .and_then(|v| v.get("undo_of").and_then(|x| x.as_i64()));
        let loser_display_name = v
            .as_ref()
            .and_then(|v| v.get("loser_display_name").and_then(|x| x.as_str()))
            .map(str::to_string);
        let person_id = v
            .as_ref()
            .and_then(|v| v.get("person_id").and_then(|x| x.as_i64()));
        let keep = v
            .as_ref()
            .and_then(|v| v.get("keep").and_then(|x| x.as_i64()));
        let loser = v
            .as_ref()
            .and_then(|v| v.get("loser").and_then(|x| x.as_i64()));
        Ok(LinkEvent {
            id: r.get(0)?,
            ts: r.get(1)?,
            op: r.get(2)?,
            actor: r.get(3)?,
            undo_of,
            loser_display_name,
            person_id,
            keep,
            loser,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}
