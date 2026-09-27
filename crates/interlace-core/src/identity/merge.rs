//! Person merge / unlink / undo.

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::{CoreError, PersonMergeOpts};

use super::helpers::reason_is_phone_replaced;

pub fn person_merge(
    archive: &mut Archive,
    a: i64,
    b: i64,
    opts: PersonMergeOpts,
) -> Result<i64, CoreError> {
    with_immediate(archive, || {
        let keep = merge_persons(archive, a, b, opts.keep, "user", "manual", 1.0)?;
        let loser = if keep == a { b } else { a };
        crate::people::rebuild_activity_years(archive, Some(keep))?;
        if loser != keep {
            crate::people::rebuild_activity_years(archive, Some(loser))?;
        }
        Ok(keep)
    })
}

pub fn person_unlink(archive: &mut Archive, identity_id: i64) -> Result<(), CoreError> {
    let row: Option<(i64, String, f64, String)> = archive
        .conn
        .query_row(
            "SELECT person_id, link_reason, confidence, created_by
             FROM person_identities WHERE identity_id = ?1",
            [identity_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
        )
        .optional()?;
    let Some((person_id, reason, conf, created_by)) = row else {
        return Ok(());
    };
    with_immediate(archive, || {
        archive.conn.execute(
            "DELETE FROM person_identities WHERE identity_id = ?1",
            [identity_id],
        )?;
        log_event(
            archive,
            "user",
            "unlink",
            serde_json::json!({
                "identity_id": identity_id,
                "person_id": person_id,
                "link_reason": reason,
                "confidence": conf,
                "created_by": created_by,
            }),
        )?;
        crate::people::rebuild_activity_years(archive, Some(person_id))?;
        Ok(())
    })
}

pub fn person_undo(archive: &mut Archive, event_id: i64) -> Result<(), CoreError> {
    let (op, payload_raw): (String, String) = archive.conn.query_row(
        "SELECT op, payload_json FROM identity_link_events WHERE id = ?1",
        [event_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )?;
    let p: serde_json::Value = serde_json::from_str(&payload_raw)
        .map_err(|e| CoreError::Parse(format!("undo payload: {e}")))?;
    with_immediate(archive, || {
        match op.as_str() {
            "merge_persons" => {
                let mut people = Vec::new();
                if let Some(prev) = p["prev"].as_object() {
                    for iid_s in prev.keys() {
                        let iid: i64 = iid_s.parse().map_err(|_| {
                            CoreError::Parse(format!("bad identity id in undo payload: {iid_s}"))
                        })?;
                        if let Some(holder) = current_holder(archive, iid)? {
                            queue_person(&mut people, holder);
                        }
                    }
                }
                undo_merge(archive, &p)?;
                let keep = p["keep"]
                    .as_i64()
                    .ok_or_else(|| CoreError::Parse("undo merge missing keep".into()))?;
                let loser = p["loser"]
                    .as_i64()
                    .ok_or_else(|| CoreError::Parse("undo merge missing loser".into()))?;
                queue_person(&mut people, keep);
                queue_person(&mut people, loser);
                rebuild_queued(archive, &people)?;
                reopen_phone_replaced(archive, keep, &p)?;
            }
            "link" => {
                let iid = p["identity_id"]
                    .as_i64()
                    .ok_or_else(|| CoreError::Parse("undo link missing identity_id".into()))?;
                let payload_pid = p["person_id"].as_i64();
                let holder = current_holder(archive, iid)?;
                archive.conn.execute(
                    "DELETE FROM person_identities WHERE identity_id = ?1",
                    [iid],
                )?;
                let mut people = Vec::new();
                if let Some(pid) = holder {
                    queue_person(&mut people, pid);
                }
                if let Some(pid) = payload_pid {
                    queue_person(&mut people, pid);
                } else if people.is_empty() {
                    return Err(CoreError::Parse("undo link missing person_id".into()));
                }
                rebuild_queued(archive, &people)?;
            }
            "unlink" => {
                let iid = p["identity_id"]
                    .as_i64()
                    .ok_or_else(|| CoreError::Parse("undo unlink missing identity_id".into()))?;
                let pid = p["person_id"]
                    .as_i64()
                    .ok_or_else(|| CoreError::Parse("undo unlink missing person_id".into()))?;
                let reason = p["link_reason"].as_str().unwrap_or("manual");
                let conf = p["confidence"].as_f64().unwrap_or(1.0);
                let by = p["created_by"].as_str().unwrap_or("user");
                archive.conn.execute(
                    "INSERT OR IGNORE INTO person_identities(
                        person_id, identity_id, link_reason, confidence, created_by
                     ) VALUES (?1, ?2, ?3, ?4, ?5)",
                    rusqlite::params![pid, iid, reason, conf, by],
                )?;
                crate::people::rebuild_activity_years(archive, Some(pid))?;
            }
            other => {
                return Err(CoreError::Config(format!(
                    "cannot undo identity event op={other}"
                )))
            }
        }
        log_event(
            archive,
            "user",
            "split_person",
            serde_json::json!({"undo_of": event_id, "op": op}),
        )?;
        Ok(())
    })
}

pub(crate) fn with_immediate<T>(
    archive: &Archive,
    body: impl FnOnce() -> Result<T, CoreError>,
) -> Result<T, CoreError> {
    archive.conn.execute_batch("BEGIN IMMEDIATE")?;
    match body() {
        Ok(value) => match archive.conn.execute_batch("COMMIT") {
            Ok(()) => Ok(value),
            Err(e) => {
                let _ = archive.conn.execute_batch("ROLLBACK");
                Err(e.into())
            }
        },
        Err(e) => {
            let _ = archive.conn.execute_batch("ROLLBACK");
            Err(e)
        }
    }
}

pub(super) fn merge_persons(
    archive: &Archive,
    a: i64,
    b: i64,
    keep: Option<i64>,
    actor: &str,
    reason: &str,
    conf: f64,
) -> Result<i64, CoreError> {
    if a == b {
        return Ok(a);
    }
    let keep_id = keep.unwrap_or(a.min(b));
    let loser = if keep_id == a { b } else { a };
    let keep_live: Option<String> = archive
        .conn
        .query_row(
            "SELECT tombstoned_at FROM persons WHERE id = ?1",
            [keep_id],
            |r| r.get(0),
        )
        .optional()?
        .flatten();
    if keep_live.is_some() {
        return Err(CoreError::Config(format!(
            "cannot merge into tombstoned person {keep_id}"
        )));
    }
    let loser_name: String = archive.conn.query_row(
        "SELECT display_name FROM persons WHERE id = ?1",
        [loser],
        |r| r.get(0),
    )?;
    let moved: Vec<(i64, String, f64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT identity_id, link_reason, confidence, created_by
             FROM person_identities WHERE person_id = ?1",
        )?;
        let it = stmt.query_map([loser], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
        })?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    let mut prev = serde_json::Map::new();
    for (iid, rsn, c, by) in &moved {
        prev.insert(
            iid.to_string(),
            serde_json::json!({"reason": rsn, "confidence": c, "created_by": by}),
        );
        archive.conn.execute(
            "UPDATE person_identities
             SET person_id = ?1, link_reason = ?2, confidence = ?3, created_by = ?4
             WHERE identity_id = ?5",
            rusqlite::params![keep_id, reason, conf, actor, iid],
        )?;
    }
    archive.conn.execute(
        "UPDATE persons SET tombstoned_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                merged_into = ?1,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id = ?2",
        rusqlite::params![keep_id, loser],
    )?;
    log_event(
        archive,
        actor,
        "merge_persons",
        serde_json::json!({
            "keep": keep_id,
            "loser": loser,
            "loser_display_name": loser_name,
            "moved_identity_ids": moved.iter().map(|m| m.0).collect::<Vec<_>>(),
            "prev": prev,
        }),
    )?;
    Ok(keep_id)
}

/// Accepting a replaced-phone suggestion merges two people. Undo puts that
/// suggestion back on the open list so Review shows it again.
fn reopen_phone_replaced(
    archive: &Archive,
    keep: i64,
    payload: &serde_json::Value,
) -> Result<(), CoreError> {
    let moved: Vec<i64> = payload["moved_identity_ids"]
        .as_array()
        .map(|ids| ids.iter().filter_map(|v| v.as_i64()).collect())
        .unwrap_or_default();
    if moved.is_empty() {
        return Ok(());
    }
    let rows: Vec<(i64, i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT id, left_identity_id, reason_summary
             FROM merge_review_queue
             WHERE status = 'accepted' AND right_person_id = ?1",
        )?;
        let it = stmt.query_map([keep], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (id, left_identity, reason) in rows {
        if !reason_is_phone_replaced(&reason) || !moved.contains(&left_identity) {
            continue;
        }
        archive.conn.execute(
            "UPDATE merge_review_queue
             SET status = 'open', resolved_at = NULL, resolved_by = NULL
             WHERE id = ?1",
            [id],
        )?;
    }
    Ok(())
}

fn current_holder(archive: &Archive, identity_id: i64) -> Result<Option<i64>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT person_id FROM person_identities WHERE identity_id = ?1",
            [identity_id],
            |r| r.get(0),
        )
        .optional()
        .map_err(CoreError::from)
}

fn queue_person(ids: &mut Vec<i64>, id: i64) {
    if !ids.contains(&id) {
        ids.push(id);
    }
}

fn rebuild_queued(archive: &Archive, ids: &[i64]) -> Result<(), CoreError> {
    for id in ids {
        crate::people::rebuild_activity_years(archive, Some(*id))?;
    }
    Ok(())
}

fn undo_merge(archive: &Archive, p: &serde_json::Value) -> Result<(), CoreError> {
    let keep = p["keep"]
        .as_i64()
        .ok_or_else(|| CoreError::Parse("undo merge missing keep".into()))?;
    let loser = p["loser"]
        .as_i64()
        .ok_or_else(|| CoreError::Parse("undo merge missing loser".into()))?;
    let name = p["loser_display_name"].as_str().unwrap_or("restored");
    // revive loser row (id reused)
    let exists: Option<i64> = archive
        .conn
        .query_row("SELECT id FROM persons WHERE id = ?1", [loser], |r| {
            r.get(0)
        })
        .optional()?;
    if exists.is_some() {
        archive.conn.execute(
            "UPDATE persons SET tombstoned_at = NULL, merged_into = NULL,
                    display_name = ?1,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE id = ?2",
            rusqlite::params![name, loser],
        )?;
    } else {
        archive.conn.execute(
            "INSERT INTO persons(id, display_name, is_self) VALUES (?1, ?2, 0)",
            rusqlite::params![loser, name],
        )?;
    }
    if let Some(prev) = p["prev"].as_object() {
        for (iid_s, meta) in prev {
            let iid: i64 = iid_s.parse().map_err(|_| {
                CoreError::Parse(format!("bad identity id in undo payload: {iid_s}"))
            })?;
            let reason = meta["reason"].as_str().unwrap_or("manual");
            let conf = meta["confidence"].as_f64().unwrap_or(1.0);
            let by = meta["created_by"].as_str().unwrap_or("system");
            archive.conn.execute(
                "UPDATE person_identities
                 SET person_id = ?1, link_reason = ?2, confidence = ?3, created_by = ?4
                 WHERE identity_id = ?5",
                rusqlite::params![loser, reason, conf, by, iid],
            )?;
        }
    }
    let _ = keep;
    Ok(())
}

pub(super) fn link_identity(
    archive: &Archive,
    person_id: i64,
    identity_id: i64,
    reason: &str,
    conf: f64,
    actor: &str,
) -> Result<(), CoreError> {
    let created_by = if actor == "user" { "user" } else { "system" };
    archive.conn.execute(
        "INSERT OR IGNORE INTO person_identities(
            person_id, identity_id, link_reason, confidence, created_by
         ) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![person_id, identity_id, reason, conf, created_by],
    )?;
    log_event(
        archive,
        actor,
        "link",
        serde_json::json!({
            "person_id": person_id,
            "identity_id": identity_id,
            "link_reason": reason,
            "confidence": conf,
        }),
    )?;
    Ok(())
}

fn log_event(
    archive: &Archive,
    actor: &str,
    op: &str,
    payload: serde_json::Value,
) -> Result<i64, CoreError> {
    let s = serde_json::to_string(&payload)
        .map_err(|e| CoreError::Fatal(format!("event json: {e}")))?;
    archive.conn.execute(
        "INSERT INTO identity_link_events(actor, op, payload_json) VALUES (?1, ?2, ?3)",
        rusqlite::params![actor, op, s],
    )?;
    Ok(archive.conn.last_insert_rowid())
}
