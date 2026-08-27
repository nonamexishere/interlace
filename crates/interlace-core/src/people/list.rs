use std::collections::HashMap;

use rusqlite::Connection;

use crate::db::Archive;
use crate::model::CoreError;

use super::{PersonIdentity, PersonSummary};

const PREVIEW_MAX_CHARS: usize = 160;

/// One-line list preview: subject if the last D18 row has one, else truncated
/// `body_text` with HTML tags stripped. Empty / missing text → `None`.
pub(super) fn list_preview(subject: Option<&str>, body_text: &str) -> Option<String> {
    let subject = subject.map(str::trim).filter(|s| !s.is_empty());
    if let Some(s) = subject {
        let t = truncate_one_line(s, PREVIEW_MAX_CHARS);
        return if t.is_empty() { None } else { Some(t) };
    }
    let plain = strip_html_tags(body_text);
    let t = truncate_one_line(&plain, PREVIEW_MAX_CHARS);
    if t.is_empty() {
        None
    } else {
        Some(t)
    }
}

fn strip_html_tags(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut in_tag = false;
    for c in s.chars() {
        match c {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => out.push(c),
            _ => {}
        }
    }
    out
}

fn truncate_one_line(s: &str, max: usize) -> String {
    let line: String = s
        .chars()
        .map(|c| if c == '\n' || c == '\r' { ' ' } else { c })
        .take(max)
        .collect();
    line.trim().to_string()
}

/// Fill each person's linked `value_normalized` for client-side people filter (#138).
pub(super) fn attach_identity_values(
    conn: &Connection,
    people: &mut [PersonSummary],
) -> Result<(), CoreError> {
    if people.is_empty() {
        return Ok(());
    }
    let mut by_person: HashMap<i64, Vec<String>> = HashMap::new();
    let mut stmt = conn.prepare(
        "SELECT pi.person_id, i.value_normalized
         FROM person_identities pi
         JOIN identities i ON i.id = pi.identity_id
         ORDER BY pi.person_id, i.id",
    )?;
    let rows = stmt.query_map([], |r| {
        let pid: i64 = r.get(0)?;
        let value: String = r.get(1)?;
        Ok((pid, value))
    })?;
    for row in rows {
        let (pid, value) = row?;
        if !value.is_empty() {
            by_person.entry(pid).or_default().push(value);
        }
    }
    for p in people.iter_mut() {
        p.identity_values = by_person.remove(&p.id).unwrap_or_default();
    }
    Ok(())
}

/// People the UI may offer as merge targets for `selected_id`.
///
/// Drops the selected person and, unless `allow_self`, anyone with `is_self`.
/// `query` is a casefold substring of `display_name` only — a query that looks
/// like a numeric id matches nobody. Empty query keeps every remaining person.
pub fn merge_targets(
    people: &[PersonSummary],
    selected_id: i64,
    allow_self: bool,
    query: &str,
) -> Vec<PersonSummary> {
    let q = query.trim().to_lowercase();
    people
        .iter()
        .filter(|p| p.id != selected_id)
        .filter(|p| allow_self || !p.is_self)
        .filter(|p| q.is_empty() || p.display_name.to_lowercase().contains(&q))
        .cloned()
        .collect()
}

pub fn person_identities(
    archive: &Archive,
    person_id: i64,
) -> Result<Vec<PersonIdentity>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT i.id, i.platform, i.kind, i.value_normalized, i.display_name
         FROM person_identities pi
         JOIN identities i ON i.id = pi.identity_id
         WHERE pi.person_id = ?1
         ORDER BY i.id",
    )?;
    let rows = stmt.query_map([person_id], |r| {
        Ok(PersonIdentity {
            id: r.get(0)?,
            platform: r.get(1)?,
            kind: r.get(2)?,
            value: r.get(3)?,
            display_name: r.get(4)?,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

pub fn person_display_name(archive: &Archive, person_id: i64) -> Result<String, CoreError> {
    archive
        .conn
        .query_row(
            "SELECT display_name FROM persons WHERE id=?1 AND tombstoned_at IS NULL",
            [person_id],
            |r| r.get(0),
        )
        .map_err(|_| CoreError::Config(format!("no live person {person_id}")))
}
