//! FTS5 search + person timeline (D17, D18). Dual Turkish/ASCII fold.

use crate::db::Archive;
use crate::model::{CoreError, Platform, SearchHit, SearchQuery};

const DEFAULT_LIMIT: u32 = 50;
const MAX_LIMIT: u32 = 200;
const TIMELINE_DEFAULT: u32 = 100;

/// Index-time Turkish fold: İ→i, I→ı, then Unicode lower.
pub fn turkish_fold(s: &str) -> String {
    strip_cf(s)
        .replace('İ', "i")
        .replace('I', "ı")
        .to_lowercase()
}

/// Unicode lower *without* the Turkish I map (English I→i).
pub fn extra_ascii_fold(s: &str) -> String {
    strip_cf(s).to_lowercase()
}

pub fn build_search_text(
    subject: Option<&str>,
    body: Option<&str>,
    filenames: &[String],
) -> String {
    let sub = subject.unwrap_or("");
    let body = body.unwrap_or("");
    let files = filenames.join(" ");
    format!(
        "{} {} {} {}",
        turkish_fold(sub),
        turkish_fold(body),
        turkish_fold(&files),
        extra_ascii_fold(body)
    )
    .split_whitespace()
    .collect::<Vec<_>>()
    .join(" ")
}

/// Wrap bare tokens with OR of {raw, turkish_fold, unicode_lower}.
pub fn expand_query(user: &str) -> String {
    let mut out = Vec::new();
    for tok in user.split_whitespace() {
        let up = tok.to_ascii_uppercase();
        if matches!(up.as_str(), "AND" | "OR" | "NOT" | "NEAR") {
            out.push(up);
            continue;
        }
        if tok.starts_with('"') && tok.ends_with('"') && tok.len() >= 2 {
            let inner = &tok[1..tok.len() - 1];
            out.push(format!("\"{}\"", turkish_fold(inner)));
            continue;
        }
        let cleaned: String = tok
            .chars()
            .filter(|c| c.is_alphanumeric() || *c == '*' || c.is_alphabetic())
            .collect();
        if cleaned.is_empty() {
            continue;
        }
        let mut vars = vec![
            cleaned.clone(),
            turkish_fold(&cleaned),
            extra_ascii_fold(&cleaned),
        ];
        vars.sort();
        vars.dedup();
        vars.retain(|v| !v.is_empty());
        if vars.len() == 1 {
            out.push(vars.pop().unwrap());
        } else {
            out.push(format!("({})", vars.join(" OR ")));
        }
    }
    out.join(" ")
}

pub fn search(archive: &Archive, q: &SearchQuery) -> Result<Vec<SearchHit>, CoreError> {
    let limit = clamp_limit(q.limit, DEFAULT_LIMIT);
    if q.q.trim().is_empty() {
        return Ok(Vec::new());
    }
    let match_q = expand_query(&q.q);
    if match_q.is_empty() {
        return Ok(Vec::new());
    }
    let include_groups = if q.include_groups { 1i64 } else { 0 };
    let plat = q.platform.map(platform_sql);
    let mut sql = String::from(
        "SELECT
            m.id,
            m.sent_at,
            m.conversation_id,
            m.subject,
            snippet(messages_fts, 0, '«', '»', '…', 12) AS snip,
            bm25(messages_fts) AS score
         FROM messages_fts
         JOIN search_doc d ON d.message_id = messages_fts.rowid
         JOIN messages m ON m.id = d.message_id
         JOIN conversations c ON c.id = m.conversation_id
         WHERE messages_fts MATCH ?",
    );
    if q.from.is_some() {
        sql.push_str(" AND (d.sent_at IS NULL OR d.sent_at >= ?)");
    }
    if q.to.is_some() {
        sql.push_str(" AND (d.sent_at IS NULL OR d.sent_at <= ?)");
    }
    if plat.is_some() {
        sql.push_str(" AND d.platform = ?");
    }
    if q.conversation_id.is_some() {
        sql.push_str(" AND d.conversation_id = ?");
    }
    if q.person_id.is_some() {
        sql.push_str(
            " AND (
                d.sender_identity_id IN (SELECT identity_id FROM person_identities WHERE person_id = ?)
             OR d.conversation_id IN (
                    SELECT cp.conversation_id
                    FROM conversation_participants cp
                    JOIN person_identities pi ON pi.identity_id = cp.identity_id
                    JOIN conversations c2 ON c2.id = cp.conversation_id
                    WHERE pi.person_id = ?
                      AND (? = 1 OR c2.kind IN ('dm','email_thread'))
                )
              )",
        );
    }
    sql.push_str(" ORDER BY score, m.sent_at IS NULL, m.sent_at DESC LIMIT ?");

    let mut stmt = archive.conn.prepare(&sql)?;
    let mut vals: Vec<rusqlite::types::Value> = vec![match_q.into()];
    if let Some(ref f) = q.from {
        vals.push(f.clone().into());
    }
    if let Some(ref t) = q.to {
        vals.push(t.clone().into());
    }
    if let Some(p) = plat {
        vals.push(p.to_string().into());
    }
    if let Some(cid) = q.conversation_id {
        vals.push(cid.into());
    }
    if let Some(pid) = q.person_id {
        vals.push(pid.into());
        vals.push(pid.into());
        vals.push(include_groups.into());
    }
    vals.push((limit as i64).into());

    let params: Vec<&dyn rusqlite::types::ToSql> = vals
        .iter()
        .map(|v| v as &dyn rusqlite::types::ToSql)
        .collect();
    let rows = stmt.query_map(params.as_slice(), |r| {
        Ok(SearchHit {
            message_id: r.get(0)?,
            sent_at: r.get(1)?,
            conversation_id: r.get(2)?,
            subject: r.get(3)?,
            snippet: r.get::<_, String>(4).unwrap_or_default(),
            score: r.get::<_, f64>(5).unwrap_or(0.0),
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

pub fn person_timeline(
    archive: &Archive,
    person_id: i64,
    include_groups: bool,
    limit: u32,
) -> Result<Vec<SearchHit>, CoreError> {
    let limit = clamp_limit(limit, TIMELINE_DEFAULT);
    let group_sql = if include_groups {
        ""
    } else {
        "AND c.kind IN ('dm','email_thread')"
    };
    let sql = format!(
        "SELECT m.id, m.sent_at, m.conversation_id, m.subject,
                COALESCE(substr(m.body_text, 1, 160), '')
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE (
                m.sender_identity_id IN (
                    SELECT identity_id FROM person_identities WHERE person_id = ?1
                )
             OR (
                    m.conversation_id IN (
                      SELECT cp.conversation_id
                      FROM conversation_participants cp
                      JOIN person_identities pi ON pi.identity_id = cp.identity_id
                      WHERE pi.person_id = ?1
                    )
                    {group_sql}
                )
              )
         ORDER BY m.sent_at IS NULL, m.sent_at DESC
         LIMIT ?2"
    );
    let mut stmt = archive.conn.prepare(&sql)?;
    let rows = stmt.query_map(rusqlite::params![person_id, limit as i64], |r| {
        Ok(SearchHit {
            message_id: r.get(0)?,
            sent_at: r.get(1)?,
            conversation_id: r.get(2)?,
            subject: r.get(3)?,
            snippet: r.get(4)?,
            score: 0.0,
        })
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

/// Bulk-index messages for one import run (D17). Does not DROP triggers.
type MsgRow = (
    i64,
    Option<String>,
    String,
    i64,
    Option<i64>,
    Option<String>,
    Option<String>,
);

pub fn index_import_run(archive: &Archive, run_id: i64) -> Result<(), CoreError> {
    let msgs: Vec<MsgRow> = {
        let mut stmt = archive.conn.prepare(
            "SELECT m.id, m.sent_at, c.platform, m.conversation_id, m.sender_identity_id,
                    m.subject, m.body_text
             FROM messages m
             JOIN conversations c ON c.id = m.conversation_id
             WHERE m.import_run_id = ?1
               AND NOT EXISTS (SELECT 1 FROM search_doc s WHERE s.message_id = m.id)",
        )?;
        let it = stmt.query_map([run_id], |r| {
            Ok((
                r.get(0)?,
                r.get(1)?,
                r.get(2)?,
                r.get(3)?,
                r.get(4)?,
                r.get(5)?,
                r.get(6)?,
            ))
        })?;
        it.collect::<Result<Vec<_>, _>>()?
    };
    for (id, sent_at, platform, conv, sender, subject, body) in msgs {
        let files = attachment_names(archive, id)?;
        let text = build_search_text(subject.as_deref(), body.as_deref(), &files);
        archive.conn.execute(
            "INSERT INTO search_doc(
                message_id, sent_at, platform, conversation_id, sender_identity_id, search_text
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            rusqlite::params![id, sent_at, platform, conv, sender, text],
        )?;
    }
    rebuild_fts(archive)
}

pub fn rebuild_fts(archive: &Archive) -> Result<(), CoreError> {
    archive.conn.execute(
        "INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')",
        [],
    )?;
    Ok(())
}

fn attachment_names(archive: &Archive, message_id: i64) -> Result<Vec<String>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT filename FROM attachments WHERE message_id = ?1 AND filename IS NOT NULL",
    )?;
    let it = stmt.query_map([message_id], |r| r.get::<_, String>(0))?;
    Ok(it.collect::<Result<Vec<_>, _>>()?)
}

fn clamp_limit(limit: u32, default: u32) -> u32 {
    if limit == 0 {
        default
    } else {
        limit.min(MAX_LIMIT)
    }
}

fn platform_sql(p: Platform) -> &'static str {
    match p {
        Platform::Whatsapp => "whatsapp",
        Platform::Gmail => "gmail",
        Platform::Contacts => "contacts",
        Platform::Owner => "owner",
    }
}

fn strip_cf(s: &str) -> String {
    s.chars()
        .filter(|c| {
            !matches!(
                *c,
                '\u{200e}'
                    | '\u{200f}'
                    | '\u{200b}'
                    | '\u{200c}'
                    | '\u{200d}'
                    | '\u{feff}'
                    | '\u{2060}'
            )
        })
        .collect()
}

impl Default for SearchQuery {
    fn default() -> Self {
        Self {
            q: String::new(),
            person_id: None,
            from: None,
            to: None,
            platform: None,
            conversation_id: None,
            include_groups: false,
            limit: DEFAULT_LIMIT,
        }
    }
}
