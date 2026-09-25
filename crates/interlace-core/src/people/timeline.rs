use rusqlite::OptionalExtension;
use serde::Serialize;

use crate::db::Archive;
use crate::model::CoreError;

use super::attach::{
    attach_attachments, attach_labels, attach_recipients, enrich_from_body_tokens,
};
use super::{PersonConversation, PersonMediaRow, TimelineRow};

const TIMELINE_DEFAULT: u32 = 100;
const TIMELINE_MAX: u32 = 200;

/// EXISTS predicate for optional attach-kind (`None` / All = no extra clause).
fn attach_kind_sql(attach_kind: Option<&str>) -> &'static str {
    const PHOTOS: &str = "AND EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id AND (\
         a.kind IN ('image','sticker')\
      OR (a.kind IN ('inline','file') AND a.mime LIKE 'image/%')))";
    const VIDEO: &str = "AND EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id AND (\
         a.kind = 'video'\
      OR (a.kind IN ('inline','file') AND a.mime LIKE 'video/%')))";
    const VOICE: &str = "AND EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id AND (\
         a.kind = 'voice'\
      OR (a.kind IN ('inline','file') AND a.mime LIKE 'audio/%')))";
    // NULL/empty mime is not image/video/audio (same as client isFilesAttach).
    const FILES: &str = "AND EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id AND \
         a.kind IN ('file','vcf')\
     AND IFNULL(a.mime,'') NOT LIKE 'image/%'\
     AND IFNULL(a.mime,'') NOT LIKE 'video/%'\
     AND IFNULL(a.mime,'') NOT LIKE 'audio/%')";
    match attach_kind {
        None | Some("") | Some("all") => "",
        Some("photos") => PHOTOS,
        Some("video") => VIDEO,
        Some("voice") => VOICE,
        Some("files") => FILES,
        Some(_) => "AND 1=0",
    }
}

/// D18 timeline with optional `before` sent_at cursor (exclusive, descending).
pub fn person_timeline_rows(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
) -> Result<Vec<TimelineRow>, CoreError> {
    person_timeline_rows_for(
        archive,
        person_id,
        include_groups,
        limit,
        before,
        None,
        None,
        None,
        None,
        None,
    )
}

/// D18 timeline; `conversation_id = None` is All (merged stream).
/// `attach_kind = None` / All omits the attachments EXISTS filter.
/// `after` set (and `before` unset) is the newer page: oldest-first limit,
/// then reversed so callers still `toReversed()` under the hit.
/// `after_id` Some keeps the rest of that `sent_at` (`id` greater than it).
/// `after_id` None keeps strict `sent_at > :after`.
/// `before_id` Some (with `before`) keeps the rest of that `sent_at`
/// (`id` less than it). `before_id` None keeps strict `sent_at < :before`,
/// including the `sentAt~` cursor. Both cursors on one call is an error.
#[allow(clippy::too_many_arguments)]
pub fn person_timeline_rows_for(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
    conversation_id: Option<i64>,
    attach_kind: Option<&str>,
    after: Option<&str>,
    after_id: Option<i64>,
    before_id: Option<i64>,
) -> Result<Vec<TimelineRow>, CoreError> {
    if before.is_some() && after.is_some() {
        return Err(CoreError::Fatal(
            "person timeline accepts before or after, not both".into(),
        ));
    }
    let limit = limit.clamp(1, TIMELINE_MAX);
    let limit = if limit == 0 { TIMELINE_DEFAULT } else { limit };
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let cursor_sql = if after.is_some() && after_id.is_some() {
        "AND m.sent_at IS NOT NULL AND (m.sent_at > :after OR (m.sent_at = :after AND m.id > :after_id))"
    } else if after.is_some() {
        "AND m.sent_at IS NOT NULL AND m.sent_at > :after"
    } else if before.is_some() && before_id.is_some() {
        "AND m.sent_at IS NOT NULL AND (m.sent_at < :before OR (m.sent_at = :before AND m.id < :before_id))"
    } else if before.is_some() {
        "AND m.sent_at IS NOT NULL AND m.sent_at < :before"
    } else {
        ""
    };
    let order_sql = if after.is_some() {
        "ORDER BY m.sent_at ASC, m.id ASC"
    } else {
        "ORDER BY m.sent_at IS NULL, m.sent_at DESC, m.id DESC"
    };
    let conv_sql = if conversation_id.is_some() {
        "AND m.conversation_id = :conv"
    } else {
        ""
    };
    let attach_sql = attach_kind_sql(attach_kind);
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
                ) THEN 1 ELSE 0 END,
                m.raw_cas_hash
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE (
                m.sender_identity_id IN (
                    SELECT identity_id FROM person_identities WHERE person_id = :pid
                )
             OR m.conversation_id IN (
                    SELECT cp.conversation_id
                    FROM conversation_participants cp
                    JOIN person_identities pi ON pi.identity_id = cp.identity_id
                    WHERE pi.person_id = :pid
                )
              )
           {group_sql}
           {cursor_sql}
           {conv_sql}
           {attach_sql}
         {order_sql}
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
            labels: Vec::new(),
            raw_cas_hash: r.get(10)?,
            recipients: Default::default(),
        })
    };
    let lim = limit as i64;
    let rows = match (before, before_id, after, after_id, conversation_id) {
        (Some(_), _, Some(_), _, _) => {
            return Err(CoreError::Fatal(
                "person timeline accepts before or after, not both".into(),
            ));
        }
        (Some(b), Some(bid), None, _, Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b, ":before_id": bid, ":conv": cid },
            map_row,
        )?,
        (Some(b), Some(bid), None, _, None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b, ":before_id": bid },
            map_row,
        )?,
        (Some(b), None, None, _, Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b, ":conv": cid },
            map_row,
        )?,
        (Some(b), None, None, _, None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b },
            map_row,
        )?,
        (None, _, Some(a), Some(aid), Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":after": a, ":after_id": aid, ":conv": cid },
            map_row,
        )?,
        (None, _, Some(a), Some(aid), None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":after": a, ":after_id": aid },
            map_row,
        )?,
        (None, _, Some(a), None, Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":after": a, ":conv": cid },
            map_row,
        )?,
        (None, _, Some(a), None, None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":after": a },
            map_row,
        )?,
        (None, _, None, _, Some(cid)) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":conv": cid },
            map_row,
        )?,
        (None, _, None, _, None) => stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim },
            map_row,
        )?,
    };
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    if after.is_some() {
        out.reverse();
    }
    attach_attachments(archive, &mut out)?;
    attach_labels(archive, &mut out)?;
    attach_recipients(archive, &mut out)?;
    enrich_from_body_tokens(archive, &mut out)?;
    Ok(out)
}

/// Counts-only year buckets. `count` is stored `message_count`.
/// No rows is an empty vec. No live scan.
#[derive(Debug, Clone, Serialize)]
pub struct PersonYearCount {
    pub year: i64,
    pub count: i64,
    pub first_local_day: String,
}

pub fn person_year_counts(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
) -> Result<Vec<PersonYearCount>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT year, message_count, first_local_day \
         FROM person_year_index \
         WHERE person_id = :pid AND include_groups = :include_groups \
         ORDER BY year DESC",
    )?;
    let flag = if include_groups { 1i64 } else { 0 };
    let rows = stmt.query_map(
        rusqlite::named_params! { ":pid": person_id, ":include_groups": flag },
        |r| {
            Ok(PersonYearCount {
                year: r.get(0)?,
                count: r.get(1)?,
                first_local_day: r.get(2)?,
            })
        },
    )?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

/// Full replace of stored year rows. `None` replaces every person.
/// One flag is `dm` / `email_thread` only; the other includes groups.
/// A person or year with no dated messages stores no row.
/// Messages whose `import_run_id` is not a `done` run are ignored.
pub fn rebuild_activity_years(archive: &Archive, person_id: Option<i64>) -> Result<(), CoreError> {
    let ids: Vec<i64> = if let Some(id) = person_id {
        vec![id]
    } else {
        archive.conn.execute("DELETE FROM person_year_index", [])?;
        let mut stmt = archive.conn.prepare("SELECT id FROM persons")?;
        let rows = stmt.query_map([], |r| r.get(0))?;
        rows.collect::<Result<Vec<_>, _>>()?
    };
    for id in ids {
        if person_id.is_some() {
            archive
                .conn
                .execute("DELETE FROM person_year_index WHERE person_id = ?1", [id])?;
        }
        for include_groups in [false, true] {
            let mut sql = String::from(
                "INSERT INTO person_year_index( \
                    person_id, include_groups, year, message_count, first_local_day \
                 ) \
                 SELECT :pid, :include_groups, year, count, first_local_day FROM ( \
                   SELECT CAST(substr(day, 1, 4) AS INTEGER) AS year, \
                          COUNT(*) AS count, \
                          MIN(day) AS first_local_day \
                   FROM ( \
                     SELECT CASE \
                       WHEN c.platform IS NULL \
                         OR trim(c.platform) = '' \
                         OR lower(c.platform) = 'whatsapp' \
                       THEN CASE \
                         WHEN substr(m.sent_at, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' \
                         THEN substr(m.sent_at, 1, 10) \
                         ELSE NULL \
                       END \
                       ELSE strftime('%Y-%m-%d', m.sent_at, 'localtime') \
                     END AS day \
                     FROM messages m \
                     JOIN conversations c ON c.id = m.conversation_id \
                     JOIN import_runs ir ON ir.id = m.import_run_id AND ir.status = 'done' \
                     WHERE ( \
                            m.sender_identity_id IN ( \
                                SELECT identity_id FROM person_identities WHERE person_id = :pid \
                            ) \
                         OR m.conversation_id IN ( \
                                SELECT cp.conversation_id \
                                FROM conversation_participants cp \
                                JOIN person_identities pi ON pi.identity_id = cp.identity_id \
                                WHERE pi.person_id = :pid \
                            ) \
                          )",
            );
            if !include_groups {
                sql.push_str(" AND c.kind IN ('dm', 'email_thread')");
            }
            sql.push_str(
                " ) dated WHERE day IS NOT NULL GROUP BY substr(day, 1, 4) ORDER BY year DESC)",
            );
            let flag = if include_groups { 1i64 } else { 0 };
            archive.conn.execute(
                &sql,
                rusqlite::named_params! { ":pid": id, ":include_groups": flag },
            )?;
        }
    }
    Ok(())
}

/// Earliest message on one local day (lowest `sent_at`, then lowest id).
/// Same calendar and membership as `person_year_counts`. No message bodies.
/// A missing day or unknown person is `None`.
pub fn person_day_message(
    archive: &Archive,
    person_id: i64,
    day: &str,
    include_groups: bool,
) -> Result<Option<(i64, String)>, CoreError> {
    let mut sql = String::from(
        "SELECT m.id, m.sent_at \
         FROM messages m \
         JOIN conversations c ON c.id = m.conversation_id \
         WHERE ( \
                m.sender_identity_id IN ( \
                    SELECT identity_id FROM person_identities WHERE person_id = :pid \
                ) \
             OR m.conversation_id IN ( \
                    SELECT cp.conversation_id \
                    FROM conversation_participants cp \
                    JOIN person_identities pi ON pi.identity_id = cp.identity_id \
                    WHERE pi.person_id = :pid \
                ) \
              ) \
           AND (CASE \
             WHEN c.platform IS NULL \
               OR trim(c.platform) = '' \
               OR lower(c.platform) = 'whatsapp' \
             THEN CASE \
               WHEN substr(m.sent_at, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' \
               THEN substr(m.sent_at, 1, 10) \
               ELSE NULL \
             END \
             ELSE strftime('%Y-%m-%d', m.sent_at, 'localtime') \
           END) = :day",
    );
    if !include_groups {
        sql.push_str(" AND c.kind IN ('dm', 'email_thread')");
    }
    sql.push_str(" ORDER BY m.sent_at ASC, m.id ASC LIMIT 1");
    let mut stmt = archive.conn.prepare(&sql)?;
    let row = stmt
        .query_row(
            rusqlite::named_params! { ":pid": person_id, ":day": day },
            |r| {
                let id: i64 = r.get(0)?;
                let sent_at: Option<String> = r.get(1)?;
                Ok(sent_at.map(|sent| (id, sent)))
            },
        )
        .optional()?;
    Ok(row.flatten())
}

/// Stored CAS image / video / sticker rows for one person (same membership
/// as `person_timeline_rows_for` with `conversation_id = None`).
pub fn person_media_rows_for(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
    before: Option<&str>,
) -> Result<Vec<PersonMediaRow>, CoreError> {
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
    let sql = format!(
        "SELECT a.id, m.id, m.sent_at, c.kind, a.cas_hash, a.filename, a.mime, a.kind
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         JOIN attachments a ON a.message_id = m.id
         WHERE (
                m.sender_identity_id IN (
                    SELECT identity_id FROM person_identities WHERE person_id = :pid
                )
             OR m.conversation_id IN (
                    SELECT cp.conversation_id
                    FROM conversation_participants cp
                    JOIN person_identities pi ON pi.identity_id = cp.identity_id
                    WHERE pi.person_id = :pid
                )
              )
           AND a.cas_hash IS NOT NULL
           AND a.omitted = 0
           AND a.missing = 0
           AND (
                a.kind IN ('image','video','sticker')
             OR (a.kind = 'inline' AND (a.mime LIKE 'image/%' OR a.mime LIKE 'video/%'))
           )
           {group_sql}
           {cursor_sql}
         ORDER BY m.sent_at IS NULL, m.sent_at DESC, a.id DESC
         LIMIT :lim"
    );
    let mut stmt = archive.conn.prepare(&sql)?;
    let map_row = |r: &rusqlite::Row<'_>| {
        Ok(PersonMediaRow {
            attachment_id: r.get(0)?,
            message_id: r.get(1)?,
            sent_at: r.get(2)?,
            conversation_kind: r.get(3)?,
            cas_hash: r.get(4)?,
            filename: r.get(5)?,
            mime: r.get(6)?,
            kind: r.get(7)?,
        })
    };
    let lim = limit as i64;
    let rows = if let Some(b) = before {
        stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim, ":before": b },
            map_row,
        )?
    } else {
        stmt.query_map(
            rusqlite::named_params! { ":pid": person_id, ":lim": lim },
            map_row,
        )?
    };
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
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
