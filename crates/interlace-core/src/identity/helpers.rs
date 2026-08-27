//! Shared person / identity / review-queue lookups.

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::import::name_fold_join;
use crate::model::{CoreError, ImportStats};

/// Shared fold of the queued pair, if both sides have the same non-empty
/// `name_fold_join`. Fuzzy / empty → `None` (cluster is just the pair).
pub(super) fn review_pair_fold(
    archive: &Archive,
    left_identity_id: i64,
    left_pid: Option<i64>,
    right_pid: Option<i64>,
) -> Result<Option<String>, CoreError> {
    let left_fold = if let Some(pid) = left_pid {
        person_name_fold(archive, pid)?
    } else {
        identity_name_fold(archive, left_identity_id)?
    };
    let right_fold = match right_pid {
        Some(pid) => person_name_fold(archive, pid)?,
        None => String::new(),
    };
    if left_fold.is_empty() || left_fold != right_fold {
        Ok(None)
    } else {
        Ok(Some(left_fold))
    }
}

/// Fold of a queued pair from stored ids (works after a person is tombstoned).
pub(super) fn review_queued_fold(
    archive: &Archive,
    left_identity_id: i64,
    right_person: Option<i64>,
    right_ident: Option<i64>,
) -> Result<Option<String>, CoreError> {
    let left_fold = identity_name_fold(archive, left_identity_id)?;
    let right_fold = if let Some(pid) = right_person {
        person_name_fold(archive, pid)?
    } else if let Some(rid) = right_ident {
        identity_name_fold(archive, rid)?
    } else {
        String::new()
    };
    if left_fold.is_empty() || left_fold != right_fold {
        Ok(None)
    } else {
        Ok(Some(left_fold))
    }
}

pub(super) fn fold_review_suppressed(archive: &Archive, fold: &str) -> Result<bool, CoreError> {
    if fold.is_empty() {
        return Ok(false);
    }
    let rows: Vec<(i64, Option<i64>, Option<i64>)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT left_identity_id, right_person_id, right_identity_id
             FROM merge_review_queue WHERE status IN ('open', 'rejected')",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (left, right_person, right_ident) in rows {
        if review_queued_fold(archive, left, right_person, right_ident)?.as_deref() == Some(fold) {
            return Ok(true);
        }
    }
    Ok(false)
}

pub(super) fn live_right_person(
    archive: &Archive,
    queued_right_person: Option<i64>,
    queued_right_ident: Option<i64>,
) -> Result<Option<i64>, CoreError> {
    if let Some(pid) = queued_right_person {
        if person_is_live(archive, pid)? {
            return Ok(Some(pid));
        }
    }
    if let Some(rid) = queued_right_ident {
        return live_person_of(archive, rid);
    }
    Ok(None)
}

pub(super) fn person_is_live(archive: &Archive, person_id: i64) -> Result<bool, CoreError> {
    let tombstoned: Option<Option<String>> = archive
        .conn
        .query_row(
            "SELECT tombstoned_at FROM persons WHERE id = ?1",
            [person_id],
            |r| r.get(0),
        )
        .optional()?;
    Ok(matches!(tombstoned, Some(None)))
}

pub(super) fn person_display_name(archive: &Archive, person_id: i64) -> Result<String, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT display_name FROM persons WHERE id = ?1",
            [person_id],
            |r| r.get(0),
        )
        .map_err(Into::into)
}

fn person_name_fold(archive: &Archive, person_id: i64) -> Result<String, CoreError> {
    Ok(name_fold_join(&person_display_name(archive, person_id)?))
}

fn identity_name_fold(archive: &Archive, identity_id: i64) -> Result<String, CoreError> {
    let name: String = archive.conn.query_row(
        "SELECT COALESCE(display_name, value_raw) FROM identities WHERE id = ?1",
        [identity_id],
        |r| r.get(0),
    )?;
    Ok(name_fold_join(&name))
}

pub(super) fn person_is_contacts_or_vcard(
    archive: &Archive,
    person_id: i64,
) -> Result<bool, CoreError> {
    let n: i64 = archive.conn.query_row(
        "SELECT COUNT(*) FROM person_identities pi
         LEFT JOIN identities i ON i.id = pi.identity_id
         WHERE pi.person_id = ?1
           AND (i.platform = 'contacts' OR pi.link_reason = 'takeout_vcard')",
        [person_id],
        |r| r.get(0),
    )?;
    Ok(n > 0)
}

pub(super) fn person_platform_rank(archive: &Archive, person_id: i64) -> Result<u8, CoreError> {
    if person_is_contacts_or_vcard(archive, person_id)? {
        return Ok(0);
    }
    let ids = person_identity_ids(archive, person_id)?;
    let plats = side_platforms(archive, &ids)?;
    if plats.iter().any(|p| p == "whatsapp") {
        Ok(1)
    } else if plats.iter().any(|p| p == "gmail") {
        Ok(2)
    } else {
        Ok(3)
    }
}

pub(super) fn person_identity_ids(
    archive: &Archive,
    person_id: i64,
) -> Result<Vec<i64>, CoreError> {
    let mut stmt = archive
        .conn
        .prepare("SELECT identity_id FROM person_identities WHERE person_id = ?1")?;
    let rows = stmt.query_map([person_id], |r| r.get(0))?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}

/// Review samples: sent by a side identity (including group sends), or a
/// `dm` / `email_thread` where a side identity is a participant. Received-only
/// group chatter does not count. People-list D18 is unchanged.
pub(super) fn review_side_panel(
    archive: &Archive,
    person_id: Option<i64>,
    identity_ids: &[i64],
    display_name: serde_json::Value,
) -> Result<serde_json::Value, CoreError> {
    let platforms = side_platforms(archive, identity_ids)?;
    let identifiers = side_identifiers(archive, identity_ids)?;
    if identity_ids.is_empty() {
        return Ok(serde_json::json!({
            "person_id": person_id,
            "display_name": display_name,
            "platforms": platforms,
            "identifiers": identifiers,
            "message_count": 0,
            "samples": [],
        }));
    }
    let placeholders = identity_ids
        .iter()
        .map(|_| "?")
        .collect::<Vec<_>>()
        .join(",");
    // Sent-by (any kind, including group) or participant of dm/email_thread.
    // Received-only group chatter stays out; people-list D18 is unchanged.
    let filter = format!(
        "m.sender_identity_id IN ({placeholders})
         OR (
                c.kind IN ('dm', 'email_thread')
            AND EXISTS (
                    SELECT 1 FROM conversation_participants cp
                    WHERE cp.conversation_id = m.conversation_id
                      AND cp.identity_id IN ({placeholders})
                )
         )"
    );
    let mut binds = Vec::with_capacity(identity_ids.len() * 2);
    binds.extend_from_slice(identity_ids);
    binds.extend_from_slice(identity_ids);
    let message_count: i64 = archive.conn.query_row(
        &format!(
            "SELECT COUNT(*)
             FROM messages m
             JOIN conversations c ON c.id = m.conversation_id
             WHERE {filter}"
        ),
        rusqlite::params_from_iter(&binds),
        |r| r.get(0),
    )?;
    let mut sample_stmt = archive.conn.prepare(&format!(
        "SELECT sent_at, COALESCE(substr(body_text, 1, 240), '')
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE {filter}
         ORDER BY m.sent_at IS NULL, m.sent_at DESC
         LIMIT 3"
    ))?;
    let samples: Vec<serde_json::Value> = sample_stmt
        .query_map(rusqlite::params_from_iter(&binds), |r| {
            Ok(serde_json::json!({
                "sent_at": r.get::<_, Option<String>>(0)?,
                "body_text": r.get::<_, String>(1)?,
            }))
        })?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(serde_json::json!({
        "person_id": person_id,
        "display_name": display_name,
        "platforms": platforms,
        "identifiers": identifiers,
        "message_count": message_count,
        "samples": samples,
    }))
}

/// Kind + normalized value for each identity on a review side (#128).
/// Stable order: platform rank, then kind, then value_normalized.
fn side_identifiers(
    archive: &Archive,
    identity_ids: &[i64],
) -> Result<Vec<serde_json::Value>, CoreError> {
    if identity_ids.is_empty() {
        return Ok(Vec::new());
    }
    let placeholders = identity_ids
        .iter()
        .map(|_| "?")
        .collect::<Vec<_>>()
        .join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT kind, value_normalized, platform FROM identities
         WHERE id IN ({placeholders})
         ORDER BY CASE platform
            WHEN 'whatsapp' THEN 0
            WHEN 'gmail' THEN 1
            WHEN 'contacts' THEN 2
            WHEN 'owner' THEN 3
            ELSE 4
         END, platform, kind, value_normalized"
    ))?;
    let rows = stmt.query_map(rusqlite::params_from_iter(identity_ids), |r| {
        Ok(serde_json::json!({
            "kind": r.get::<_, String>(0)?,
            "value_normalized": r.get::<_, String>(1)?,
            "platform": r.get::<_, String>(2)?,
        }))
    })?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}

fn side_platforms(archive: &Archive, identity_ids: &[i64]) -> Result<Vec<String>, CoreError> {
    if identity_ids.is_empty() {
        return Ok(Vec::new());
    }
    let placeholders = identity_ids
        .iter()
        .map(|_| "?")
        .collect::<Vec<_>>()
        .join(",");
    let mut stmt = archive.conn.prepare(&format!(
        "SELECT DISTINCT platform FROM identities WHERE id IN ({placeholders})
         ORDER BY CASE platform
            WHEN 'whatsapp' THEN 0
            WHEN 'gmail' THEN 1
            WHEN 'contacts' THEN 2
            WHEN 'owner' THEN 3
            ELSE 4
         END, platform"
    ))?;
    let rows = stmt.query_map(rusqlite::params_from_iter(identity_ids), |r| r.get(0))?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}

pub(super) fn live_person_of(
    archive: &Archive,
    identity_id: i64,
) -> Result<Option<i64>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT p.id FROM person_identities pi
             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
             WHERE pi.identity_id = ?1",
            [identity_id],
            |r| r.get(0),
        )
        .optional()
        .map_err(Into::into)
}

#[allow(clippy::too_many_arguments)]
pub(super) fn enqueue_review(
    archive: &Archive,
    stats: &mut ImportStats,
    left: i64,
    right_person: Option<i64>,
    right_ident: Option<i64>,
    score: f64,
    summary: &str,
    evidence: &str,
    detail: serde_json::Value,
) -> Result<(), CoreError> {
    if review_suppressed(archive, left, right_person, right_ident)? {
        return Ok(());
    }
    let n = archive.conn.execute(
        "INSERT INTO merge_review_queue(
            status, left_identity_id, right_person_id, right_identity_id,
            suggested_score, reason_summary
         ) VALUES ('open', ?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![left, right_person, right_ident, score, summary],
    );
    match n {
        Ok(0) => Ok(()),
        Ok(_) => {
            let rid = archive.conn.last_insert_rowid();
            let dj = serde_json::to_string(&detail)
                .map_err(|e| CoreError::Fatal(format!("evidence json: {e}")))?;
            archive.conn.execute(
                "INSERT INTO merge_evidence(review_id, evidence_type, score, detail_json)
                 VALUES (?1, ?2, ?3, ?4)",
                rusqlite::params![rid, evidence, score, dj],
            )?;
            stats.review_enqueued += 1;
            Ok(())
        }
        Err(e) if e.to_string().contains("UNIQUE") => Ok(()),
        Err(e) => Err(e.into()),
    }
}

fn review_suppressed(
    archive: &Archive,
    left: i64,
    right_person: Option<i64>,
    right_ident: Option<i64>,
) -> Result<bool, CoreError> {
    let n: i64 = if let Some(ri) = right_ident {
        archive.conn.query_row(
            "SELECT COUNT(*) FROM merge_review_queue
             WHERE left_identity_id = ?1 AND right_identity_id = ?2
               AND status IN ('open', 'rejected')",
            rusqlite::params![left, ri],
            |r| r.get(0),
        )?
    } else if let Some(rp) = right_person {
        archive.conn.query_row(
            "SELECT COUNT(*) FROM merge_review_queue
             WHERE left_identity_id = ?1 AND right_person_id = ?2
               AND status IN ('open', 'rejected')",
            rusqlite::params![left, rp],
            |r| r.get(0),
        )?
    } else {
        archive.conn.query_row(
            "SELECT COUNT(*) FROM merge_review_queue
             WHERE left_identity_id = ?1 AND right_person_id IS NULL
               AND right_identity_id IS NULL AND status IN ('open', 'rejected')",
            [left],
            |r| r.get(0),
        )?
    };
    Ok(n > 0)
}
