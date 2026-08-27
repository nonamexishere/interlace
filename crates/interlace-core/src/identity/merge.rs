//! Person merge / unlink / undo.

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::{CoreError, PersonMergeOpts};

pub fn person_merge(
    archive: &mut Archive,
    a: i64,
    b: i64,
    opts: PersonMergeOpts,
) -> Result<i64, CoreError> {
    merge_persons(archive, a, b, opts.keep, "user", "manual", 1.0)
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
    Ok(())
}

pub fn person_undo(archive: &mut Archive, event_id: i64) -> Result<(), CoreError> {
    let (op, payload_raw): (String, String) = archive.conn.query_row(
        "SELECT op, payload_json FROM identity_link_events WHERE id = ?1",
        [event_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )?;
    let p: serde_json::Value = serde_json::from_str(&payload_raw)
        .map_err(|e| CoreError::Parse(format!("undo payload: {e}")))?;
    match op.as_str() {
        "merge_persons" => undo_merge(archive, &p)?,
        "link" => {
            let iid = p["identity_id"]
                .as_i64()
                .ok_or_else(|| CoreError::Parse("undo link missing identity_id".into()))?;
            archive.conn.execute(
                "DELETE FROM person_identities WHERE identity_id = ?1",
                [iid],
            )?;
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
