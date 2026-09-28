//! Fill `thread_parent_id` from headers already stored in this archive.

use std::collections::{HashMap, HashSet};

use crate::model::CoreError;

/// Trim, strip one pair of angle brackets, ASCII lowercase.
pub(super) fn normalize_message_id(raw: &str) -> String {
    let trimmed = raw.trim();
    let inner = if trimmed.len() >= 2 && trimmed.starts_with('<') && trimmed.ends_with('>') {
        &trimmed[1..trimmed.len() - 1]
    } else {
        trimmed
    };
    inner.to_ascii_lowercase()
}

fn header_ids(raw: &str) -> Vec<String> {
    raw.split_whitespace()
        .map(normalize_message_id)
        .filter(|id| !id.is_empty())
        .collect()
}

fn pick_parent(
    in_reply_to: Option<&str>,
    references: Option<&str>,
    by_mid: &HashMap<String, i64>,
) -> Option<i64> {
    if let Some(header) = in_reply_to {
        for id in header_ids(header) {
            if let Some(row) = by_mid.get(&id) {
                return Some(*row);
            }
        }
    }
    let mut last = None;
    if let Some(header) = references {
        for id in header_ids(header) {
            if let Some(row) = by_mid.get(&id) {
                last = Some(*row);
            }
        }
    }
    last
}

fn would_cycle(child: i64, parent: i64, parents: &HashMap<i64, i64>) -> bool {
    if child == parent {
        return true;
    }
    let mut seen = HashSet::new();
    let mut cur = parent;
    loop {
        if cur == child || !seen.insert(cur) {
            return true;
        }
        match parents.get(&cur) {
            Some(next) => cur = *next,
            None => return false,
        }
    }
}

/// After this import's messages exist: set NULL parents only.
/// First stored row for a Message-ID wins. Does not rewrite bodies or headers.
pub(crate) fn link_reply_parents(conn: &rusqlite::Connection) -> Result<(), CoreError> {
    let mut by_mid: HashMap<String, i64> = HashMap::new();
    let mut id_stmt = conn.prepare(
        "SELECT id, native_id FROM messages WHERE native_id IS NOT NULL ORDER BY id ASC",
    )?;
    let mut id_rows = id_stmt.query([])?;
    while let Some(row) = id_rows.next()? {
        let id: i64 = row.get(0)?;
        let native: String = row.get(1)?;
        let key = normalize_message_id(&native);
        if key.is_empty() {
            continue;
        }
        by_mid.entry(key).or_insert(id);
    }
    drop(id_rows);
    drop(id_stmt);

    let mut parents: HashMap<i64, i64> = HashMap::new();
    let mut parent_stmt = conn
        .prepare("SELECT id, thread_parent_id FROM messages WHERE thread_parent_id IS NOT NULL")?;
    let mut parent_rows = parent_stmt.query([])?;
    while let Some(row) = parent_rows.next()? {
        parents.insert(row.get(0)?, row.get(1)?);
    }
    drop(parent_rows);
    drop(parent_stmt);

    let mut open_stmt = conn.prepare(
        "SELECT id, in_reply_to, [references] FROM messages
         WHERE thread_parent_id IS NULL
           AND (in_reply_to IS NOT NULL OR [references] IS NOT NULL)
         ORDER BY id ASC",
    )?;
    let candidates: Vec<(i64, Option<String>, Option<String>)> = open_stmt
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))?
        .collect::<Result<Vec<_>, _>>()?;
    drop(open_stmt);

    for (id, in_reply_to, references) in candidates {
        let Some(parent) = pick_parent(in_reply_to.as_deref(), references.as_deref(), &by_mid)
        else {
            continue;
        };
        if would_cycle(id, parent, &parents) {
            continue;
        }
        let n = conn.execute(
            "UPDATE messages SET thread_parent_id = ?1 WHERE id = ?2 AND thread_parent_id IS NULL",
            rusqlite::params![parent, id],
        )?;
        if n == 1 {
            parents.insert(id, parent);
        }
    }
    Ok(())
}
