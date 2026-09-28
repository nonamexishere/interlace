//! Read-time WhatsApp quote pointer. No new column and no write.

use serde::Serialize;

use crate::db::Archive;
use crate::import::{
    all_packs, is_you_token, parse_dt_with_pack, parse_header_line, split_sender_body, strip_cf,
    LocalePack,
};
use crate::model::CoreError;

/// A quote found in `body_text`. `message_id` is set only when exactly one row matches.
#[derive(Debug, Clone, Serialize)]
pub struct WaQuoteJump {
    pub before: String,
    pub span: String,
    pub after: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message_id: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sent_at: Option<String>,
}

struct QuoteSpan {
    sender: String,
    text: String,
    /// Parsed instants for a timestamped line. Empty when the line has no time.
    sent_at: Vec<String>,
    start: usize,
    end: usize,
}

/// First embedded export line in `body`, resolved inside `conversation_id` only.
/// `None` when the body has no quote shape. Never inserts.
pub fn resolve_wa_quote(
    archive: &Archive,
    conversation_id: i64,
    body: &str,
) -> Result<Option<WaQuoteJump>, CoreError> {
    let packs = all_packs()?;
    let Some(span) = find_quote(body, &packs) else {
        return Ok(None);
    };
    let want = blake3::hash(span.text.trim().as_bytes())
        .to_hex()
        .to_string();
    let you = packs.iter().any(|p| is_you_token(p, &span.sender));
    let mut hits: Vec<(i64, Option<String>)> = Vec::new();
    let mut stmt = archive.conn.prepare(
        "SELECT m.id, m.sent_at, COALESCE(m.body_text, ''),
                COALESCE(i.display_name, ''), COALESCE(i.value_raw, ''),
                COALESCE(p.display_name, ''),
                CASE WHEN p.is_self = 1 THEN 1 ELSE 0 END,
                CASE WHEN si.identity_id IS NOT NULL THEN 1 ELSE 0 END,
                COALESCE(cp.role, '')
         FROM messages m
         LEFT JOIN identities i ON i.id = m.sender_identity_id
         LEFT JOIN person_identities pi ON pi.identity_id = i.id
         LEFT JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
         LEFT JOIN self_identities si ON si.identity_id = i.id
         LEFT JOIN conversation_participants cp
           ON cp.conversation_id = m.conversation_id AND cp.identity_id = m.sender_identity_id
         WHERE m.conversation_id = ?1",
    )?;
    let rows = stmt.query_map([conversation_id], |r| {
        Ok((
            r.get::<_, i64>(0)?,
            r.get::<_, Option<String>>(1)?,
            r.get::<_, String>(2)?,
            r.get::<_, String>(3)?,
            r.get::<_, String>(4)?,
            r.get::<_, String>(5)?,
            r.get::<_, i64>(6)?,
            r.get::<_, i64>(7)?,
            r.get::<_, String>(8)?,
        ))
    })?;
    for row in rows {
        let (id, sent_at, body_text, id_display, value_raw, person_display, is_self, in_self, role) =
            row?;
        if blake3::hash(body_text.trim().as_bytes())
            .to_hex()
            .to_string()
            != want
        {
            continue;
        }
        if !span.sent_at.is_empty()
            && !sent_at
                .as_ref()
                .is_some_and(|at| span.sent_at.iter().any(|q| q == at))
        {
            continue;
        }
        let sender_ok = if you {
            is_self == 1
                || in_self == 1
                || role == "me"
                || packs
                    .iter()
                    .any(|p| is_you_token(p, &id_display) || is_you_token(p, &value_raw))
        } else {
            [&id_display, &value_raw, &person_display]
                .into_iter()
                .any(|n| !n.is_empty() && strip_cf(n.trim()) == span.sender)
        };
        if !sender_ok {
            continue;
        }
        if hits.iter().any(|(prev, _)| *prev == id) {
            continue;
        }
        hits.push((id, sent_at));
        if hits.len() > 1 {
            break;
        }
    }
    let (message_id, sent_at) = if hits.len() == 1 {
        let (id, at) = hits.pop().unwrap();
        (Some(id), at)
    } else {
        (None, None)
    };
    let before = body[..span.start].to_string();
    let quote = body[span.start..span.end].to_string();
    let after = body[span.end..].to_string();
    Ok(Some(WaQuoteJump {
        before,
        span: quote,
        after,
        message_id,
        sent_at,
    }))
}

fn find_quote(body: &str, packs: &[LocalePack]) -> Option<QuoteSpan> {
    let lines = line_bounds(body);
    for (start, end) in &lines {
        if let Some(span) = timestamped_in_line(&body[*start..*end], *start, packs) {
            return Some(span);
        }
    }
    for (start, end) in &lines {
        let line = &body[*start..*end];
        if parse_header_line(line).is_some() {
            continue;
        }
        let (rel_s, rel_e) = trim_bounds(line);
        if rel_s >= rel_e {
            continue;
        }
        let trimmed = &line[rel_s..rel_e];
        let Some((sender, text)) = split_sender_body(trimmed) else {
            continue;
        };
        return Some(QuoteSpan {
            sender,
            text,
            sent_at: Vec::new(),
            start: start + rel_s,
            end: start + rel_e,
        });
    }
    None
}

fn timestamped_in_line(line: &str, line_start: usize, packs: &[LocalePack]) -> Option<QuoteSpan> {
    let mut offsets = vec![0usize];
    for (i, c) in line.char_indices() {
        if c == '[' && i != 0 {
            offsets.push(i);
        }
    }
    for rel in offsets {
        let sub = &line[rel..];
        let Some(header) = parse_header_line(sub) else {
            continue;
        };
        let mut instants: Vec<String> = Vec::new();
        for pack in packs {
            if let Some(dt) = parse_dt_with_pack(pack, &header.dt_raw) {
                if !instants.iter().any(|s| s == &dt.rfc3339) {
                    instants.push(dt.rfc3339);
                }
            }
        }
        if instants.is_empty() {
            continue;
        }
        let Some((sender, text)) = split_sender_body(&header.rest) else {
            continue;
        };
        let (trim_s, trim_e) = trim_bounds(sub);
        if trim_s >= trim_e {
            continue;
        }
        return Some(QuoteSpan {
            sender,
            text,
            sent_at: instants,
            start: line_start + rel + trim_s,
            end: line_start + rel + trim_e,
        });
    }
    None
}

fn line_bounds(body: &str) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    let mut start = 0usize;
    for (i, c) in body.char_indices() {
        if c == '\n' {
            let mut end = i;
            if end > start && body.as_bytes()[end - 1] == b'\r' {
                end -= 1;
            }
            out.push((start, end));
            start = i + c.len_utf8();
        }
    }
    if start < body.len() || out.is_empty() {
        out.push((start, body.len()));
    }
    out
}

fn trim_bounds(s: &str) -> (usize, usize) {
    let lead = s.len() - s.trim_start().len();
    let end = s.trim_end().len();
    (lead, end)
}
