//! Auto-link phone/email, enqueue name reviews. Names never auto-merge.

use std::collections::HashSet;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::import::name_fold_join;
use crate::model::{CoreError, ImportStats};

use super::helpers::{enqueue_review, fold_review_suppressed};
use super::merge::{link_identity, merge_persons};
use super::score::{name_compat_ratio, name_score};

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
    let mut seen_folds: HashSet<String> = HashSet::new();
    for (wa_pid, wa_iid, wa_name) in &wa {
        let wa_fold = name_fold_join(wa_name);
        if wa_fold.is_empty() {
            continue;
        }
        if !seen_folds.insert(wa_fold.clone()) {
            continue;
        }
        if fold_review_suppressed(archive, &wa_fold)? {
            continue;
        }
        let Some((c_pid, _)) = contacts
            .iter()
            .find(|(c_pid, c_name)| *c_pid != *wa_pid && name_fold_join(c_name) == wa_fold)
        else {
            continue;
        };
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
    Ok(())
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
