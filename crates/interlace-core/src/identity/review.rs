//! Review queue resolve / list / show.

use crate::db::Archive;
use crate::import::name_fold_join;
use crate::model::CoreError;

use super::helpers::{
    live_person_of, live_right_person, person_display_name, person_identity_ids,
    person_is_contacts_or_vcard, person_is_live, person_platform_rank, review_pair_fold,
    review_queued_fold, review_side_panel,
};
use super::merge::{link_identity, merge_persons};

pub fn review_resolve(
    archive: &mut Archive,
    review_id: i64,
    accept: bool,
) -> Result<(), CoreError> {
    review_resolve_selected(archive, review_id, accept, None)
}

/// Accept only `selected` person ids (must be in the exact-fold cluster).
/// `None` means every live person in the cluster. Fewer than two selected
/// ids on accept is an error.
pub fn review_resolve_selected(
    archive: &mut Archive,
    review_id: i64,
    accept: bool,
    selected: Option<&[i64]>,
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
        let queued_right_person = row.2;
        let left_pid = live_person_of(archive, left)?;
        let right_pid = live_right_person(archive, queued_right_person, row.3)?;
        let cluster = review_cluster_person_ids(archive, left, left_pid, right_pid)?;
        let chosen: Vec<i64> = match selected {
            None => cluster.clone(),
            Some(ids) => cluster
                .iter()
                .copied()
                .filter(|pid| ids.contains(pid))
                .collect(),
        };
        let survivor = if chosen.len() >= 2 {
            let survivor = pick_cluster_survivor(archive, queued_right_person, &chosen)?;
            for pid in &chosen {
                if *pid != survivor {
                    merge_persons(
                        archive,
                        *pid,
                        survivor,
                        Some(survivor),
                        "user",
                        "manual",
                        1.0,
                    )?;
                }
            }
            Some(survivor)
        } else if live_person_of(archive, left)?.is_none() {
            // I3 / name-only: link the unlinked left identity onto the
            // suggested person. Not a person-person merge.
            match pick_cluster_survivor(archive, queued_right_person, &chosen)
                .ok()
                .or(right_pid)
            {
                Some(pid) => Some(pid),
                None => {
                    return Err(CoreError::Config("review has no right side".into()));
                }
            }
        } else {
            return Err(CoreError::Config(
                "select at least two people to merge".into(),
            ));
        };
        if let Some(survivor) = survivor {
            if live_person_of(archive, left)?.is_none() {
                link_identity(archive, survivor, left, "review_accepted", 0.90, "user")?;
            }
        }
        archive.conn.execute(
            "UPDATE merge_review_queue SET status = 'accepted',
                    resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                    resolved_by = 'user'
             WHERE id = ?1",
            [review_id],
        )?;
        close_sibling_fold_reviews(archive, review_id, left, left_pid, right_pid, "accepted")?;
    } else {
        archive.conn.execute(
            "UPDATE merge_review_queue SET status = 'rejected',
                    resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                    resolved_by = 'user'
             WHERE id = ?1",
            [review_id],
        )?;
        let left = row.1;
        let left_pid = live_person_of(archive, left)?;
        let right_pid = live_right_person(archive, row.2, row.3)?;
        close_sibling_fold_reviews(archive, review_id, left, left_pid, right_pid, "rejected")?;
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
    let left_pid = live_person_of(archive, left_id)?;
    let left_ids = if let Some(pid) = left_pid {
        person_identity_ids(archive, pid)?
    } else {
        vec![left_id]
    };
    let left = review_side_panel(archive, left_pid, &left_ids, review["left_name"].clone())?;
    let right = if let Some(pid) = review["right_person_id"].as_i64() {
        let right_ids = person_identity_ids(archive, pid)?;
        review_side_panel(archive, Some(pid), &right_ids, review["right_name"].clone())?
    } else {
        serde_json::json!({
            "person_id": null,
            "display_name": review["right_name"],
            "platforms": [],
            "identifiers": [],
            "message_count": 0,
            "samples": [],
        })
    };
    let right_pid = live_right_person(
        archive,
        review["right_person_id"].as_i64(),
        review["right_identity_id"].as_i64(),
    )?;
    let sides = review_side_panels(archive, left_id, left_pid, right_pid, &left, &right)?;
    Ok(serde_json::json!({
        "review": review,
        "evidence": evidence,
        "left": left,
        "right": right,
        "sides": sides,
    }))
}

fn close_sibling_fold_reviews(
    archive: &Archive,
    keep_review_id: i64,
    left: i64,
    left_pid: Option<i64>,
    right_pid: Option<i64>,
    status: &str,
) -> Result<(), CoreError> {
    let fold = match review_pair_fold(archive, left, left_pid, right_pid)? {
        Some(f) => f,
        None => match review_queued_fold(archive, left, right_pid, None)? {
            Some(f) => f,
            None => return Ok(()),
        },
    };
    let open: Vec<(i64, i64, Option<i64>, Option<i64>)> = {
        let mut stmt = archive.conn.prepare(
            "SELECT id, left_identity_id, right_person_id, right_identity_id
             FROM merge_review_queue WHERE status = 'open' AND id != ?1",
        )?;
        let it = stmt.query_map([keep_review_id], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
        })?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (oid, oleft, oright_person, oright_ident) in open {
        if review_queued_fold(archive, oleft, oright_person, oright_ident)?.as_deref()
            == Some(fold.as_str())
        {
            archive.conn.execute(
                "UPDATE merge_review_queue SET status = ?1,
                        resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                        resolved_by = 'user'
                 WHERE id = ?2",
                rusqlite::params![status, oid],
            )?;
        }
    }
    Ok(())
}

/// Exact-fold cluster for Review: live non-self persons sharing the pair's
/// `name_fold_join`. Different or empty folds → just the queued pair.
fn review_cluster_person_ids(
    archive: &Archive,
    left_identity_id: i64,
    left_pid: Option<i64>,
    right_pid: Option<i64>,
) -> Result<Vec<i64>, CoreError> {
    let mut ids = Vec::new();
    if let Some(fold) = review_pair_fold(archive, left_identity_id, left_pid, right_pid)? {
        let persons: Vec<(i64, String)> = {
            let mut stmt = archive.conn.prepare(
                "SELECT id, display_name FROM persons
                 WHERE tombstoned_at IS NULL AND is_self = 0",
            )?;
            let it = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?;
            it.collect::<Result<Vec<_>, _>>()?
        };
        for (pid, name) in persons {
            let f = name_fold_join(&name);
            if f.is_empty() {
                continue;
            }
            if f == fold {
                ids.push(pid);
            }
        }
    }
    if let Some(pid) = left_pid {
        if person_is_live(archive, pid)? && !ids.contains(&pid) {
            ids.push(pid);
        }
    }
    if let Some(pid) = right_pid {
        if person_is_live(archive, pid)? && !ids.contains(&pid) {
            ids.push(pid);
        }
    }
    let mut ranked: Vec<(u8, i64)> = Vec::with_capacity(ids.len());
    for pid in ids {
        ranked.push((person_platform_rank(archive, pid)?, pid));
    }
    ranked.sort_unstable();
    Ok(ranked.into_iter().map(|(_, pid)| pid).collect())
}

fn review_side_panels(
    archive: &Archive,
    left_identity_id: i64,
    left_pid: Option<i64>,
    right_pid: Option<i64>,
    left: &serde_json::Value,
    right: &serde_json::Value,
) -> Result<Vec<serde_json::Value>, CoreError> {
    // Fuzzy name_similarity or empty fold: sides is just the queued pair.
    if review_pair_fold(archive, left_identity_id, left_pid, right_pid)?.is_none() {
        return Ok(vec![left.clone(), right.clone()]);
    }
    let cluster = review_cluster_person_ids(archive, left_identity_id, left_pid, right_pid)?;
    if cluster.is_empty() {
        return Ok(vec![left.clone(), right.clone()]);
    }
    let mut sides = Vec::with_capacity(cluster.len() + 1);
    // Unlinked left identity is not a person; keep its panel (samples / name).
    if left_pid.is_none() {
        sides.push(left.clone());
    }
    for pid in cluster {
        if Some(pid) == left_pid {
            sides.push(left.clone());
        } else if Some(pid) == right_pid {
            sides.push(right.clone());
        } else {
            let ids = person_identity_ids(archive, pid)?;
            let name = person_display_name(archive, pid)?;
            sides.push(review_side_panel(
                archive,
                Some(pid),
                &ids,
                serde_json::Value::String(name),
            )?);
        }
    }
    Ok(sides)
}

fn pick_cluster_survivor(
    archive: &Archive,
    queued_right_person: Option<i64>,
    cluster: &[i64],
) -> Result<i64, CoreError> {
    if let Some(pid) = queued_right_person {
        if cluster.contains(&pid) && person_is_live(archive, pid)? {
            return Ok(pid);
        }
    }
    let mut contacts = Vec::new();
    for pid in cluster {
        if person_is_contacts_or_vcard(archive, *pid)? {
            contacts.push(*pid);
        }
    }
    if contacts.len() == 1 {
        return Ok(contacts[0]);
    }
    cluster
        .iter()
        .copied()
        .min()
        .ok_or_else(|| CoreError::Config("review has no right side".into()))
}
