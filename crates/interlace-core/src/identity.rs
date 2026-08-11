//! Identity resolve / merge / undo / review (PR8).

use std::collections::HashSet;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::import::{name_fold, name_fold_join};
use crate::model::{CoreError, ImportStats, PersonMergeOpts};

/// Auto-link exact phone/email and auto person-merge (rules A/B). Display names
/// never attach onto an existing phone/email/contacts person (I2). After
/// name-similarity review is enqueued, leftover name-only identities get their
/// own person so WA-first archives have a people list. Then exact
/// `name_fold_join` Contacts vs WhatsApp `display_name` pairs enqueue review.
pub fn resolve_run(archive: &mut Archive, _run_id: i64) -> Result<ImportStats, CoreError> {
    let mut stats = ImportStats::default();
    attach_high_conf(archive, &mut stats)?;
    loop {
        let n = merge_duplicate_persons(archive, &mut stats)?;
        if n == 0 {
            break;
        }
    }
    enqueue_name_reviews(archive, &mut stats)?;
    promote_unlinked_names(archive)?;
    enqueue_exact_name_fold_reviews(archive, &mut stats)?;
    Ok(stats)
}

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

pub fn review_resolve(
    archive: &mut Archive,
    review_id: i64,
    accept: bool,
) -> Result<(), CoreError> {
    let row: (String, i64, Option<i64>, Option<i64>) = archive.conn.query_row(
        "SELECT status, left_identity_id, right_person_id, right_identity_id
         FROM merge_review_queue WHERE id = ?1",
        [review_id],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
    )?;
    if row.0 != "open" {
        return Err(CoreError::Config(format!(
            "review {review_id} is not open ({})",
            row.0
        )));
    }
    if accept {
        let left = row.1;
        let person_id = if let Some(pid) = row.2 {
            pid
        } else if let Some(rid) = row.3 {
            live_person_of(archive, rid)?
                .ok_or_else(|| CoreError::Config("review right identity has no person".into()))?
        } else {
            return Err(CoreError::Config("review has no right side".into()));
        };
        if live_person_of(archive, left)?.is_some() {
            // already linked; merge persons if different
            if let Some(lp) = live_person_of(archive, left)? {
                if lp != person_id {
                    merge_persons(
                        archive,
                        lp,
                        person_id,
                        Some(person_id.min(lp)),
                        "user",
                        "manual",
                        1.0,
                    )?;
                }
            }
        } else {
            link_identity(archive, person_id, left, "review_accepted", 0.90, "user")?;
        }
        archive.conn.execute(
            "UPDATE merge_review_queue SET status = 'accepted',
                    resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                    resolved_by = 'user'
             WHERE id = ?1",
            [review_id],
        )?;
    } else {
        archive.conn.execute(
            "UPDATE merge_review_queue SET status = 'rejected',
                    resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                    resolved_by = 'user'
             WHERE id = ?1",
            [review_id],
        )?;
    }
    Ok(())
}

pub fn review_list(archive: &Archive) -> Result<Vec<serde_json::Value>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT q.id, q.suggested_score, q.reason_summary, q.left_identity_id, q.right_person_id,
                q.right_identity_id,
                COALESCE(li.display_name, li.value_raw),
                rp.display_name
         FROM merge_review_queue q
         JOIN identities li ON li.id = q.left_identity_id
         LEFT JOIN persons rp ON rp.id = q.right_person_id
         WHERE q.status = 'open'
         ORDER BY q.suggested_score DESC, q.id",
    )?;
    let rows = stmt.query_map([], |r| {
        Ok(serde_json::json!({
            "id": r.get::<_, i64>(0)?,
            "score": r.get::<_, f64>(1)?,
            "reason": r.get::<_, String>(2)?,
            "left_identity_id": r.get::<_, i64>(3)?,
            "right_person_id": r.get::<_, Option<i64>>(4)?,
            "right_identity_id": r.get::<_, Option<i64>>(5)?,
            "left_name": r.get::<_, String>(6)?,
            "right_name": r.get::<_, Option<String>>(7)?,
        }))
    })?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}

pub fn review_show(archive: &Archive, id: i64) -> Result<serde_json::Value, CoreError> {
    let review: serde_json::Value = archive.conn.query_row(
        "SELECT q.id, q.status, q.suggested_score, q.reason_summary,
                q.left_identity_id, q.right_person_id, q.right_identity_id,
                COALESCE(li.display_name, li.value_raw),
                rp.display_name
         FROM merge_review_queue q
         JOIN identities li ON li.id = q.left_identity_id
         LEFT JOIN persons rp ON rp.id = q.right_person_id
         WHERE q.id = ?1",
        [id],
        |r| {
            Ok(serde_json::json!({
                "id": r.get::<_, i64>(0)?,
                "status": r.get::<_, String>(1)?,
                "score": r.get::<_, f64>(2)?,
                "reason": r.get::<_, String>(3)?,
                "left_identity_id": r.get::<_, i64>(4)?,
                "right_person_id": r.get::<_, Option<i64>>(5)?,
                "right_identity_id": r.get::<_, Option<i64>>(6)?,
                "left_name": r.get::<_, String>(7)?,
                "right_name": r.get::<_, Option<String>>(8)?,
            }))
        },
    )?;
    let mut ev = archive.conn.prepare(
        "SELECT evidence_type, score, detail_json FROM merge_evidence WHERE review_id=?1",
    )?;
    let evidence: Vec<serde_json::Value> = ev
        .query_map([id], |r| {
            Ok(serde_json::json!({
                "type": r.get::<_, String>(0)?,
                "score": r.get::<_, f64>(1)?,
                "detail": r.get::<_, String>(2)?,
            }))
        })?
        .collect::<Result<Vec<_>, _>>()?;
    let left_id = review["left_identity_id"].as_i64().unwrap_or(0);
    let left_ids = if let Some(pid) = live_person_of(archive, left_id)? {
        person_identity_ids(archive, pid)?
    } else {
        vec![left_id]
    };
    let left = review_side_panel(archive, &left_ids, review["left_name"].clone())?;
    let right = if let Some(pid) = review["right_person_id"].as_i64() {
        let right_ids = person_identity_ids(archive, pid)?;
        review_side_panel(archive, &right_ids, review["right_name"].clone())?
    } else {
        serde_json::json!({
            "display_name": review["right_name"],
            "message_count": 0,
            "samples": [],
        })
    };
    Ok(serde_json::json!({
        "review": review,
        "evidence": evidence,
        "left": left,
        "right": right,
    }))
}

fn person_identity_ids(archive: &Archive, person_id: i64) -> Result<Vec<i64>, CoreError> {
    let mut stmt = archive
        .conn
        .prepare("SELECT identity_id FROM person_identities WHERE person_id = ?1")?;
    let rows = stmt.query_map([person_id], |r| r.get(0))?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}

/// D18 membership with groups off: sent by a side identity, or a `dm` /
/// `email_thread` where a side identity is a participant. Groups never count.
fn review_side_panel(
    archive: &Archive,
    identity_ids: &[i64],
    display_name: serde_json::Value,
) -> Result<serde_json::Value, CoreError> {
    if identity_ids.is_empty() {
        return Ok(serde_json::json!({
            "display_name": display_name,
            "message_count": 0,
            "samples": [],
        }));
    }
    let placeholders = identity_ids
        .iter()
        .map(|_| "?")
        .collect::<Vec<_>>()
        .join(",");
    let filter = format!(
        "c.kind IN ('dm', 'email_thread')
         AND (
                m.sender_identity_id IN ({placeholders})
             OR EXISTS (
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
        "display_name": display_name,
        "message_count": message_count,
        "samples": samples,
    }))
}

fn attach_high_conf(archive: &Archive, stats: &mut ImportStats) -> Result<(), CoreError> {
    let rows: Vec<(i64, String, String, Option<String>)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT i.id, i.kind, i.value_normalized, i.display_name
             FROM identities i
             WHERE i.kind IN ('phone', 'email')
               AND NOT EXISTS (
                    SELECT 1 FROM person_identities pi WHERE pi.identity_id = i.id
               )",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (id, kind, norm, display) in rows {
        if !is_auto_key(&kind, &norm) {
            continue;
        }
        if identifier_conflict(archive, &kind, &norm)? {
            let other = first_channel_identity(archive, &kind, &norm)?;
            enqueue_review(
                archive,
                stats,
                id,
                None,
                other,
                0.50,
                "same identifier on two contact cards with incompatible names",
                if kind == "phone" {
                    "phone_e164"
                } else {
                    "email_exact"
                },
                serde_json::json!({"kind": kind, "value": norm}),
            )?;
            continue;
        }
        let mut persons = persons_with_key(archive, &kind, &norm)?;
        persons.sort_unstable();
        persons.dedup();
        if let Some(&pid) = persons.first() {
            let reason = if kind == "phone" {
                "auto_phone"
            } else {
                "auto_email"
            };
            link_identity(archive, pid, id, reason, 0.99, "system")?;
        } else {
            let name = display
                .as_deref()
                .filter(|s| !s.trim().is_empty())
                .unwrap_or(norm.as_str())
                .to_string();
            archive.conn.execute(
                "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
                [&name],
            )?;
            let pid = archive.conn.last_insert_rowid();
            let reason = if kind == "phone" {
                "auto_phone"
            } else {
                "auto_email"
            };
            link_identity(archive, pid, id, reason, 0.99, "system")?;
        }
    }
    Ok(())
}

fn merge_duplicate_persons(archive: &Archive, stats: &mut ImportStats) -> Result<u64, CoreError> {
    let pairs: Vec<(i64, i64, String, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT MIN(p1.id), MAX(p2.id), i1.kind, i1.value_normalized
             FROM person_identities pi1
             JOIN identities i1 ON i1.id = pi1.identity_id
             JOIN persons p1 ON p1.id = pi1.person_id AND p1.tombstoned_at IS NULL
             JOIN identities i2 ON i2.kind = i1.kind AND i2.value_normalized = i1.value_normalized
             JOIN person_identities pi2 ON pi2.identity_id = i2.id
             JOIN persons p2 ON p2.id = pi2.person_id AND p2.tombstoned_at IS NULL
             WHERE i1.kind IN ('phone', 'email') AND p1.id < p2.id
             GROUP BY i1.kind, i1.value_normalized, p1.id, p2.id",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    let mut n = 0u64;
    for (a, b, kind, norm) in pairs {
        if identifier_conflict(archive, &kind, &norm)? {
            if let Some(iid) = first_identity_of_person(archive, b)? {
                enqueue_review(
                    archive,
                    stats,
                    iid,
                    Some(a),
                    None,
                    0.50,
                    "person-merge blocked: same identifier, incompatible contact names",
                    if kind == "phone" {
                        "phone_e164"
                    } else {
                        "email_exact"
                    },
                    serde_json::json!({"kind": kind, "value": norm, "left": a, "right": b}),
                )?;
            }
            continue;
        }
        merge_persons(
            archive,
            a,
            b,
            Some(a.min(b)),
            "system",
            "auto_person_merge",
            0.99,
        )?;
        stats.auto_person_merges += 1;
        n += 1;
    }
    Ok(n)
}

fn enqueue_name_reviews(archive: &Archive, stats: &mut ImportStats) -> Result<(), CoreError> {
    let idents: Vec<(i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT i.id, COALESCE(i.display_name, i.value_raw)
             FROM identities i
             WHERE i.kind IN ('display_name', 'username')
               AND NOT EXISTS (
                    SELECT 1 FROM person_identities pi WHERE pi.identity_id = i.id
               )",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    let persons: Vec<(i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT id, display_name FROM persons WHERE tombstoned_at IS NULL AND is_self = 0",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (iid, iname) in idents {
        let mut best: Option<(i64, f64)> = None;
        for (pid, pname) in &persons {
            let mut s = name_score(&iname, pname);
            if let Some(other) = best_linked_name(archive, *pid)? {
                s = s.max(name_score(&iname, &other));
            }
            if s >= 0.40 && best.map(|(_, b)| s > b).unwrap_or(true) {
                best = Some((*pid, s));
            }
        }
        if let Some((pid, score)) = best {
            enqueue_review(
                archive,
                stats,
                iid,
                Some(pid),
                None,
                score,
                "name similarity only; not auto-merged",
                "name_similarity",
                serde_json::json!({"left": iname, "score": score}),
            )?;
        }
    }
    Ok(())
}

/// One new person per leftover `display_name` / `username`. Never link onto
/// an existing person (that is I2). Skip names that fold-equal a group title
/// (ZIP stem often becomes a participant identity).
fn promote_unlinked_names(archive: &Archive) -> Result<(), CoreError> {
    let group_folds: HashSet<String> = {
        let mut stmt = archive
            .conn
            .prepare("SELECT COALESCE(title, '') FROM conversations WHERE kind = 'group'")?;
        let rows = stmt.query_map([], |r| r.get::<_, String>(0))?;
        let mut set = HashSet::new();
        for t in rows {
            let f = name_fold_join(&t?);
            if !f.is_empty() {
                set.insert(f);
            }
        }
        set
    };
    let idents: Vec<(i64, String, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT i.id, COALESCE(NULLIF(trim(i.display_name), ''), i.value_raw), i.value_normalized
             FROM identities i
             WHERE i.kind IN ('display_name', 'username')
               AND NOT EXISTS (
                    SELECT 1 FROM person_identities pi WHERE pi.identity_id = i.id
               )",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (id, name, norm) in idents {
        let nf = name_fold_join(&name);
        if (!norm.is_empty() && group_folds.contains(&norm))
            || (!nf.is_empty() && group_folds.contains(&nf))
        {
            continue;
        }
        let label = if name.trim().is_empty() {
            norm.as_str()
        } else {
            name.as_str()
        };
        if label.trim().is_empty() {
            continue;
        }
        archive.conn.execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [label],
        )?;
        let pid = archive.conn.last_insert_rowid();
        // Existing CHECK has no name-only reason; `manual` + system = stub, not a user merge.
        link_identity(archive, pid, id, "manual", 1.0, "system")?;
    }
    Ok(())
}

/// I2: exact `name_fold_join` between a live Contacts/`takeout_vcard` person and
/// a live WhatsApp `display_name` person goes to review. Never auto-merge.
fn enqueue_exact_name_fold_reviews(
    archive: &Archive,
    stats: &mut ImportStats,
) -> Result<(), CoreError> {
    let contacts: Vec<(i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT DISTINCT p.id, p.display_name
             FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             LEFT JOIN identities i ON i.id = pi.identity_id
             WHERE p.tombstoned_at IS NULL AND p.is_self = 0
               AND (i.platform = 'contacts' OR pi.link_reason = 'takeout_vcard')",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    let wa: Vec<(i64, i64, String)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT p.id, MIN(i.id), p.display_name
             FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             JOIN identities i ON i.id = pi.identity_id
             WHERE p.tombstoned_at IS NULL AND p.is_self = 0
               AND i.platform = 'whatsapp' AND i.kind = 'display_name'
             GROUP BY p.id, p.display_name",
        )?;
        let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    let mut seen_pairs: HashSet<(i64, i64)> = HashSet::new();
    for (wa_pid, wa_iid, wa_name) in &wa {
        let wa_fold = name_fold_join(wa_name);
        if wa_fold.is_empty() {
            continue;
        }
        for (c_pid, c_name) in &contacts {
            if c_pid == wa_pid {
                continue;
            }
            if name_fold_join(c_name) != wa_fold {
                continue;
            }
            let key = (*wa_pid.min(c_pid), *wa_pid.max(c_pid));
            if !seen_pairs.insert(key) {
                continue;
            }
            enqueue_review(
                archive,
                stats,
                *wa_iid,
                Some(*c_pid),
                None,
                0.70,
                "exact_name_fold",
                "name_similarity",
                serde_json::json!({
                    "fold": wa_fold,
                    "left_person": wa_pid,
                    "right_person": c_pid,
                }),
            )?;
        }
    }
    Ok(())
}

fn merge_persons(
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

fn link_identity(
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

fn is_auto_key(kind: &str, norm: &str) -> bool {
    match kind {
        "phone" => {
            norm.starts_with('+')
                && norm.len() >= 9
                && norm[1..].bytes().all(|b| b.is_ascii_digit())
        }
        "email" => norm.contains('@') && norm.contains('.'),
        _ => false,
    }
}

fn identifier_conflict(archive: &Archive, kind: &str, norm: &str) -> Result<bool, CoreError> {
    let cards: Vec<(i64, Option<String>)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT DISTINCT cr.id, cr.fn
             FROM contacts_raw cr
             JOIN contact_channels cc ON cc.contact_id = cr.id
             LEFT JOIN person_identities pi ON pi.identity_id = cc.identity_id
             LEFT JOIN persons p ON p.id = pi.person_id
             WHERE cc.kind = ?1 AND cc.value_normalized = ?2
               AND (p.id IS NULL OR p.tombstoned_at IS NULL)",
        )?;
        let it = stmt.query_map(rusqlite::params![kind, norm], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    if cards.len() < 2 {
        return Ok(false);
    }
    for i in 0..cards.len() {
        for j in (i + 1)..cards.len() {
            let a = cards[i].1.as_deref().unwrap_or("");
            let b = cards[j].1.as_deref().unwrap_or("");
            if name_compat_ratio(a, b) < 0.85 {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

fn persons_with_key(archive: &Archive, kind: &str, norm: &str) -> Result<Vec<i64>, CoreError> {
    let mut ids = Vec::new();
    {
        let mut stmt = archive.conn.prepare(
            "SELECT DISTINCT p.id
             FROM identities i
             JOIN person_identities pi ON pi.identity_id = i.id
             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
             WHERE i.kind = ?1 AND i.value_normalized = ?2",
        )?;
        let it = stmt.query_map(rusqlite::params![kind, norm], |r| r.get(0))?;
        for x in it {
            ids.push(x?);
        }
    }
    {
        let mut stmt = archive.conn.prepare(
            "SELECT DISTINCT p.id
             FROM contact_channels cc
             JOIN person_identities pi ON pi.identity_id = cc.identity_id
             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
             WHERE cc.kind = ?1 AND cc.value_normalized = ?2",
        )?;
        let it = stmt.query_map(rusqlite::params![kind, norm], |r| r.get(0))?;
        for x in it {
            ids.push(x?);
        }
    }
    Ok(ids)
}

fn live_person_of(archive: &Archive, identity_id: i64) -> Result<Option<i64>, CoreError> {
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

fn first_channel_identity(
    archive: &Archive,
    kind: &str,
    norm: &str,
) -> Result<Option<i64>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT identity_id FROM contact_channels
             WHERE kind = ?1 AND value_normalized = ?2 AND identity_id IS NOT NULL
             LIMIT 1",
            rusqlite::params![kind, norm],
            |r| r.get(0),
        )
        .optional()
        .map_err(Into::into)
}

fn first_identity_of_person(archive: &Archive, person_id: i64) -> Result<Option<i64>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT identity_id FROM person_identities WHERE person_id = ?1 LIMIT 1",
            [person_id],
            |r| r.get(0),
        )
        .optional()
        .map_err(Into::into)
}

fn best_linked_name(archive: &Archive, person_id: i64) -> Result<Option<String>, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT COALESCE(i.display_name, i.value_raw) FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             WHERE pi.person_id = ?1
             LIMIT 1",
            [person_id],
            |r| r.get(0),
        )
        .optional()
        .map_err(Into::into)
}

#[allow(clippy::too_many_arguments)]
fn enqueue_review(
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

fn name_compat_ratio(a: &str, b: &str) -> f64 {
    let fa = name_fold(a);
    let fb = name_fold(b);
    if fa == fb && !fa.is_empty() {
        return 1.0;
    }
    let da: Vec<String> = fa.iter().map(|t| ascii_fold(t)).collect();
    let db: Vec<String> = fb.iter().map(|t| ascii_fold(t)).collect();
    if da == db && !da.is_empty() {
        return 0.90;
    }
    if da.is_empty() || db.is_empty() {
        return 0.0;
    }
    let set_a: std::collections::HashSet<_> = da.iter().collect();
    let set_b: std::collections::HashSet<_> = db.iter().collect();
    let inter = set_a.intersection(&set_b).count() as f64;
    let uni = set_a.union(&set_b).count() as f64;
    if uni == 0.0 {
        0.0
    } else {
        inter / uni
    }
}

/// DESIGN name_score. Never used as an auto-merge key.
pub fn name_score(a: &str, b: &str) -> f64 {
    let ta = name_fold(a);
    let tb = name_fold(b);
    if ta == tb && !ta.is_empty() {
        return 0.70;
    }
    let primary = score_tokens(&ta, &tb);
    let da: Vec<String> = ta.iter().map(|t| ascii_fold(t)).collect();
    let db: Vec<String> = tb.iter().map(|t| ascii_fold(t)).collect();
    let secondary = score_tokens(&da, &db).min(0.68);
    primary.max(secondary)
}

fn score_tokens(ta: &[String], tb: &[String]) -> f64 {
    if ta.is_empty() || tb.is_empty() {
        return 0.0;
    }
    if ta == tb {
        return 0.70;
    }
    let sa: std::collections::HashSet<_> = ta.iter().collect();
    let sb: std::collections::HashSet<_> = tb.iter().collect();
    if sa.is_subset(&sb) || sb.is_subset(&sa) {
        let min_len = ta.len().min(tb.len());
        let max_len = ta.len().max(tb.len());
        if min_len == 1 && max_len >= 2 {
            return 0.45;
        }
        return 0.60;
    }
    // Align tokens. Whole-string JW on the joined name was scoring ~0.41 for
    // two unrelated 2-token names (no shared given name or surname).
    token_align_score(ta, tb)
}

/// Strong pair: exact, or JW ≥ 0.92 with both tokens ≥ 4 letters (typo).
const STRONG_JW: f64 = 0.92;
const MIN_JW_CHARS: usize = 4;

fn token_sim(a: &str, b: &str) -> f64 {
    if a == b {
        1.0
    } else {
        jaro_winkler(a, b)
    }
}

fn is_strong_pair(a: &str, b: &str, sim: f64) -> bool {
    if a == b {
        return true;
    }
    let na = a.chars().count();
    let nb = b.chars().count();
    sim >= STRONG_JW && na >= MIN_JW_CHARS && nb >= MIN_JW_CHARS
}

fn token_align_score(ta: &[String], tb: &[String]) -> f64 {
    let (short, long) = if ta.len() <= tb.len() {
        (ta, tb)
    } else {
        (tb, ta)
    };
    let mut used = vec![false; long.len()];
    let mut strong = 0usize;
    let mut strong_sim_sum = 0.0;
    for s in short {
        let mut best: Option<(usize, f64)> = None;
        for (i, l) in long.iter().enumerate() {
            if used[i] {
                continue;
            }
            let sim = token_sim(s, l);
            if best.map(|(_, b)| sim > b).unwrap_or(true) {
                best = Some((i, sim));
            }
        }
        let Some((i, sim)) = best else {
            continue;
        };
        if is_strong_pair(s, &long[i], sim) {
            used[i] = true;
            strong += 1;
            strong_sim_sum += sim;
        }
    }
    if strong == 0 {
        return 0.0;
    }
    let unmatched_short = short.len() - strong;
    let unmatched_long = used.iter().filter(|u| !*u).count();
    // Shared surname, different given names (N10 John Smith / James Smith).
    if unmatched_short > 0 && unmatched_long > 0 {
        return 0.0;
    }
    if unmatched_short == 0 && unmatched_long == 0 {
        let mean = strong_sim_sum / strong as f64;
        return (mean * 0.70).clamp(0.60, 0.68);
    }
    // Fuzzy subset: every short token has a strong partner.
    if unmatched_short == 0 && unmatched_long > 0 {
        if short.len() == 1 && long.len() >= 2 {
            return 0.45;
        }
        return 0.60;
    }
    0.0
}

fn ascii_fold(s: &str) -> String {
    s.replace('ı', "i")
        .replace('ş', "s")
        .replace('ç', "c")
        .replace('ğ', "g")
        .replace('ö', "o")
        .replace('ü', "u")
        .replace('â', "a")
}

fn jaro_winkler(s1: &str, s2: &str) -> f64 {
    let a: Vec<char> = s1.chars().collect();
    let b: Vec<char> = s2.chars().collect();
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    if a == b {
        return 1.0;
    }
    let match_dist = (a.len().max(b.len()) / 2).saturating_sub(1);
    let mut a_match = vec![false; a.len()];
    let mut b_match = vec![false; b.len()];
    let mut matches = 0usize;
    for (i, ca) in a.iter().enumerate() {
        let lo = i.saturating_sub(match_dist);
        let hi = (i + match_dist + 1).min(b.len());
        for (j, cb) in b.iter().enumerate().take(hi).skip(lo) {
            if b_match[j] || ca != cb {
                continue;
            }
            a_match[i] = true;
            b_match[j] = true;
            matches += 1;
            break;
        }
    }
    if matches == 0 {
        return 0.0;
    }
    let mut k = 0usize;
    let mut trans = 0usize;
    for (i, m) in a_match.iter().enumerate() {
        if !m {
            continue;
        }
        while !b_match[k] {
            k += 1;
        }
        if a[i] != b[k] {
            trans += 1;
        }
        k += 1;
    }
    let m = matches as f64;
    let jaro = (m / a.len() as f64 + m / b.len() as f64 + (m - (trans as f64) / 2.0) / m) / 3.0;
    let mut prefix = 0usize;
    for (ca, cb) in a.iter().zip(b.iter()).take(4) {
        if ca == cb {
            prefix += 1;
        } else {
            break;
        }
    }
    jaro + prefix as f64 * 0.1 * (1.0 - jaro)
}

#[cfg(test)]
mod name_score_tests {
    use super::name_score;

    fn band(got: f64, lo: f64, hi: f64) {
        assert!(
            got + 1e-9 >= lo && got <= hi + 1e-9,
            "score {got} not in [{lo}, {hi}]"
        );
    }

    #[test]
    fn n_table_exact_and_subset() {
        assert!((name_score("Ahmet Yılmaz", "Yılmaz Ahmet") - 0.70).abs() < 1e-9);
        band(name_score("AHMET YILMAZ", "ahmet yilmaz"), 0.60, 0.68);
        assert!((name_score("İstanbul", "istanbul") - 0.70).abs() < 1e-9);
        assert!((name_score("ISLAK", "ıslak") - 0.70).abs() < 1e-9);
        assert!((name_score("Mehmet Ali", "Mhmt Ali") - 0.70).abs() < 1e-9);
        assert!((name_score("Sayın Dr. Ahmet Yılmaz", "Ahmet Yılmaz") - 0.70).abs() < 1e-9);
        assert!((name_score("\u{200e}Ahmet Yılmaz", "Ahmet Yılmaz") - 0.70).abs() < 1e-9);
        assert!((name_score("Ali", "Ali Veli Yılmaz") - 0.45).abs() < 1e-9);
        band(name_score("Ayşe", "Ayse"), 0.60, 0.68);
    }

    #[test]
    fn unrelated_two_token_names_below_review_floor() {
        // Concat-JW * 0.70 is ~0.41 on this pair; token align must not review.
        assert!(
            name_score("Cemre Yıldız", "Berk Özdemir") < 0.40,
            "got {}",
            name_score("Cemre Yıldız", "Berk Özdemir")
        );
        assert!(name_score("Can Yılmaz", "Cem Yılmaz") < 0.40);
        assert!(name_score("John Smith", "James Smith") < 0.40);
    }

    #[test]
    fn one_letter_surname_typo_still_reviews() {
        assert!(name_score("Ahmet Yılmaz", "Ahmet Yilmas") >= 0.40);
        assert!(name_score("Ada Yıldız", "Ada Yildiz") >= 0.40);
    }
}
