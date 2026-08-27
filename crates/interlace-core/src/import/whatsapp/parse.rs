//! Chat-line parse and title helpers.

use std::path::Path;

use super::super::locale::{
    match_media, name_fold_join, parse_dt_with_pack, parse_header_line, split_sender_body,
    strip_cf, strip_forwarded, strip_title_prefix, HeaderFamily, LocalePack, MediaMatch,
};
use super::super::ImportContext;
use crate::model::*;

pub(super) struct ParsedLine {
    pub line_no: usize,
    pub sent_at: Option<String>,
    pub precision: SentAtPrecision,
    pub sender_raw: Option<String>,
    pub body: String,
    pub kind: MessageKind,
    pub media: MediaMatch,
    pub rest_raw: String,
    pub payload_json: Option<String>,
}

pub(super) fn parse_chat(
    text: &str,
    pack: &LocalePack,
    family: HeaderFamily,
    chat_name: &str,
    ctx: &mut dyn ImportContext,
    cancel: Option<&ImportCancel>,
) -> Result<Vec<ParsedLine>, CoreError> {
    let mut out: Vec<ParsedLine> = Vec::new();
    for (idx, raw_line) in text.lines().enumerate() {
        if idx % 256 == 0 {
            if cancel.is_some_and(|c| c.is_cancelled()) {
                return Err(CoreError::Cancelled);
            }
            ctx.heartbeat()?;
        }
        let line_no = idx + 1;
        let line = strip_cf(raw_line.trim_end_matches('\r'));
        if line.is_empty() {
            if let Some(prev) = out.last_mut() {
                prev.body.push('\n');
            }
            continue;
        }
        if let Some(h) = parse_header_line(&line) {
            if h.family != family {
                if let Some(prev) = out.last_mut() {
                    prev.body.push('\n');
                    prev.body.push_str(&line);
                    continue;
                }
            }
            match parse_dt_with_pack(pack, &h.dt_raw) {
                Some(dt) => {
                    let (sender, body, kind) = if let Some((s, b)) = split_sender_body(&h.rest) {
                        let b = strip_forwarded(pack, &b);
                        (Some(s), b, MessageKind::Text)
                    } else {
                        (None, h.rest.clone(), MessageKind::System)
                    };
                    let media = if kind != MessageKind::System {
                        match_media(pack, &body)
                    } else {
                        MediaMatch::None
                    };
                    let kind = match (&media, kind) {
                        (_, MessageKind::System) => MessageKind::System,
                        (MediaMatch::None, k) => k,
                        (MediaMatch::Omitted | MediaMatch::File(_), _) => {
                            if body_without_media_token(pack, &body).is_empty() {
                                MessageKind::Media
                            } else {
                                MessageKind::Mixed
                            }
                        }
                    };
                    out.push(ParsedLine {
                        line_no,
                        sent_at: Some(dt.rfc3339),
                        precision: dt.precision,
                        sender_raw: sender,
                        body,
                        kind,
                        media,
                        rest_raw: h.rest,
                        payload_json: None,
                    });
                }
                None => {
                    // timestamp-shaped but pack failed
                    ctx.warn(Warning {
                        severity: Severity::UnknownRow,
                        locator: format!("{chat_name}:{line_no}"),
                        kind: "parse".into(),
                        detail: "header datetime did not match active locale pack".into(),
                        raw_excerpt: Some(line.chars().take(200).collect()),
                    })?;
                    out.push(ParsedLine {
                        line_no,
                        sent_at: None,
                        precision: SentAtPrecision::Unknown,
                        sender_raw: None,
                        body: line.clone(),
                        kind: MessageKind::Unknown,
                        media: MediaMatch::None,
                        rest_raw: h.rest,
                        payload_json: Some(serde_json::json!({"raw": line}).to_string()),
                    });
                }
            }
        } else if let Some(prev) = out.last_mut() {
            prev.body.push('\n');
            prev.body.push_str(&line);
        } else {
            ctx.warn(Warning {
                severity: Severity::Reject,
                locator: format!("{chat_name}:{line_no}"),
                kind: "parse".into(),
                detail: "line is not a header and no previous message".into(),
                raw_excerpt: Some(line.chars().take(200).collect()),
            })?;
        }
    }
    // Continuation lines may append `<attached: file>` after match_media ran
    // on the header-only body.
    for m in &mut out {
        if m.kind == MessageKind::System {
            continue;
        }
        if matches!(m.media, MediaMatch::None) {
            m.media = match_media(pack, &m.body);
        }
        match &m.media {
            MediaMatch::File(_) | MediaMatch::Omitted => {
                m.kind = if body_without_media_token(pack, &m.body).is_empty() {
                    MessageKind::Media
                } else {
                    MessageKind::Mixed
                };
            }
            MediaMatch::None => {}
        }
    }
    Ok(out)
}

pub(super) fn sender_matches_self(sender: &str, folds: &[String]) -> bool {
    let n = name_fold_join(sender);
    !n.is_empty() && folds.iter().any(|f| f == &n)
}

pub(super) fn body_without_media_token(pack: &LocalePack, body: &str) -> String {
    let t = strip_forwarded(pack, body);
    match match_media(pack, &t) {
        MediaMatch::None => t.trim().to_string(),
        MediaMatch::Omitted => String::new(),
        MediaMatch::File(_) => {
            // strip the attached token; leftover text (if any) remains
            let mut leftover = t.clone();
            for o in &pack.media_omitted {
                leftover = leftover.replace(o, "");
            }
            for alt in &pack.file_attached_alt {
                if let Some((pre, post)) = alt.split_once("{filename}") {
                    if leftover.contains(pre) {
                        if let Some(start) = leftover.find(pre) {
                            let after = &leftover[start + pre.len()..];
                            if let Some(end) = after.find(post) {
                                leftover = format!(
                                    "{}{}",
                                    leftover[..start].trim(),
                                    after[end + post.len()..].trim()
                                );
                            }
                        }
                    }
                }
            }
            leftover.trim().to_string()
        }
    }
}

pub(super) fn conversation_title(
    opts: &ImportOpts,
    zip_path: &Path,
    chat_name: &str,
    pack: &LocalePack,
) -> String {
    if let Some(ref n) = opts.conversation_name {
        return n.clone();
    }
    let base = Path::new(chat_name)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or(chat_name);
    if base != "_chat" && !base.is_empty() {
        return strip_title_prefix(pack, base);
    }
    zip_path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("chat")
        .to_string()
}
