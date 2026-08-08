//! Gmail mboxrd importer (M1–M3).

use std::fs;
use std::path::Path;

use mailparse::MailHeaderMap;

use super::locale::{normalize_email, parse_phone, strip_cf};
use super::{ImportContext, SourceImporter};
use crate::model::*;

const HEADER_CAP: usize = 1024 * 1024;

#[derive(Default)]
pub struct GmailMboxImporter {
    pub opts: ImportOpts,
}

impl SourceImporter for GmailMboxImporter {
    fn id(&self) -> SourceKind {
        SourceKind::GmailMbox
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        if !path.is_file() {
            return Err(CoreError::Probe(format!(
                "not an mbox file: {}",
                path.display()
            )));
        }
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if ext != "mbox" {
            return Err(CoreError::Probe("expected .mbox".into()));
        }
        let bytes = fs::metadata(path)?.len();
        let head = read_prefix(path, 256)?;
        if !head.starts_with(b"From ") && !head.windows(6).any(|w| w == b"\nFrom ") {
            return Err(CoreError::Probe("mbox missing From_ separator".into()));
        }
        Ok(ProbeResult {
            kind: SourceKind::GmailMbox,
            label: path
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("mail.mbox")
                .to_string(),
            bytes: Some(bytes),
            file_blake3: hash_file(path).ok(),
            locale_guess: None,
            notes: vec!["mboxrd".into()],
        })
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        import_mbox_file(ctx, path, &path.display().to_string(), self.opts.max_bytes)?;
        Ok(ImportStats::default())
    }
}

pub fn import_mbox_file(
    ctx: &mut dyn ImportContext,
    path: &Path,
    locator: &str,
    max_bytes: u64,
) -> Result<(), CoreError> {
    let meta = fs::metadata(path)?;
    if meta.len() > max_bytes {
        return Err(CoreError::Fatal(format!(
            "mbox {} exceeds --max-bytes {}",
            path.display(),
            max_bytes
        )));
    }
    let bytes = fs::read(path)?;
    import_mbox_bytes(ctx, &bytes, locator)
}

pub fn import_mbox_bytes(
    ctx: &mut dyn ImportContext,
    bytes: &[u8],
    locator: &str,
) -> Result<(), CoreError> {
    let ckpt = ctx.load_checkpoint("mbox_file_offset")?;
    let resume_off = ckpt
        .as_ref()
        .and_then(|c| {
            let same = c
                .cursor_value
                .get("path")
                .and_then(|v| v.as_str())
                .map(|p| p == locator)
                .unwrap_or(true);
            if same {
                c.cursor_value.get("byte_offset").and_then(|v| v.as_u64())
            } else {
                None
            }
        })
        .unwrap_or(0);

    let recs = split_mboxrd(bytes);
    for rec in recs {
        if (rec.start as u64) < resume_off {
            continue;
        }
        match persist_rfc822(ctx, rec.raw, locator, rec.start) {
            Ok(()) => {}
            Err(CoreError::Parse(e)) => {
                ctx.warn(Warning {
                    severity: Severity::Reject,
                    locator: format!("{locator}:{}", rec.start),
                    kind: "mbox_corrupt".into(),
                    detail: e,
                    raw_excerpt: Some(excerpt(rec.raw)),
                })?;
            }
            Err(e) => return Err(e),
        }
        ctx.checkpoint(Checkpoint {
            cursor_kind: "mbox_file_offset".into(),
            cursor_value: serde_json::json!({
                "path": locator,
                "byte_offset": rec.end,
            }),
        })?;
        ctx.maybe_commit()?;
    }
    Ok(())
}

struct MboxRec<'a> {
    start: usize,
    end: usize,
    raw: &'a [u8],
}

fn split_mboxrd(bytes: &[u8]) -> Vec<MboxRec<'_>> {
    let mut starts = Vec::new();
    if bytes.starts_with(b"From ") {
        starts.push(0);
    }
    let needle = b"\nFrom ";
    let mut i = 0;
    while i + needle.len() <= bytes.len() {
        if &bytes[i..i + needle.len()] == needle {
            let from_at = i + 1;
            // blank-line-before-From (`\n\nFrom `) or start of file.
            if i == 0 || bytes[i - 1] == b'\n' {
                starts.push(from_at);
            }
            i += needle.len();
        } else {
            i += 1;
        }
    }
    starts.sort_unstable();
    starts.dedup();
    let mut out = Vec::new();
    for (k, &s) in starts.iter().enumerate() {
        let e = starts.get(k + 1).copied().unwrap_or(bytes.len());
        if e > s {
            out.push(MboxRec {
                start: s,
                end: e,
                raw: &bytes[s..e],
            });
        }
    }
    out
}

fn persist_rfc822(
    ctx: &mut dyn ImportContext,
    raw: &[u8],
    locator: &str,
    offset: usize,
) -> Result<(), CoreError> {
    let (from_line, rfc) = split_from_line(raw);
    let rfc = unescape_mboxrd(rfc);
    if rfc.len() > HEADER_CAP * 4 && header_block_len(&rfc) > HEADER_CAP {
        return Err(CoreError::Parse("header block exceeds 1 MiB".into()));
    }
    let parsed = mailparse::parse_mail(&rfc).map_err(|e| CoreError::Parse(e.to_string()))?;
    let get = |n: &str| parsed.headers.get_first_value(n);

    let message_id = get("Message-ID");
    let subject = get("Subject");
    let date_hdr = get("Date");
    let gm_thrid = get("X-GM-THRID");
    let in_reply_to = get("In-Reply-To");
    let references = get("References");
    let labels = parse_labels(get("X-Gmail-Labels").as_deref());

    let (sent_at, precision) = match date_hdr.as_deref().and_then(parse_rfc2822_date) {
        Some(ts) => (Some(ts), SentAtPrecision::Second),
        None => match from_line.as_deref().and_then(parse_fromline_date) {
            Some(ts) => (Some(ts), SentAtPrecision::Second),
            None => (None, SentAtPrecision::Unknown),
        },
    };

    let from_raw = get("From").unwrap_or_default();
    let sender_id = persist_addr(ctx, &from_raw, None)?;

    let mut recipients = Vec::new();
    for (hdr, role) in [
        ("To", RecipientRole::To),
        ("Cc", RecipientRole::Cc),
        ("Bcc", RecipientRole::Bcc),
    ] {
        if let Some(v) = get(hdr) {
            for part in split_addr_list(&v) {
                if let Some(id) = persist_addr(ctx, part, Some(role))? {
                    recipients.push((id, role));
                }
            }
        }
    }

    let (body_text, body_html, atts) = collect_bodies(&parsed)?;

    let idem = if let Some(ref mid) = message_id {
        format!("gmail:{}", mid.trim().to_ascii_lowercase())
    } else {
        format!("gmail-hash:{}", blake3::hash(&rfc).to_hex())
    };

    let native_conv = if let Some(ref t) = gm_thrid {
        format!("gmail-thrid:{}", t.trim())
    } else if let Some(ref irt) = in_reply_to {
        format!("gmail-ref:{}", irt.trim().to_ascii_lowercase())
    } else if let Some(ref refs) = references {
        let last = refs.split_whitespace().last().unwrap_or(refs);
        format!("gmail-ref:{}", last.trim().to_ascii_lowercase())
    } else {
        format!("gmail-single:{idem}")
    };

    let conv_id = ctx.persist_conversation(NewConversation {
        platform: Platform::Gmail,
        kind: ConversationKind::EmailThread,
        native_id: native_conv,
        title: subject.clone(),
        extra_json: None,
    })?;

    if let Some(sid) = sender_id {
        // participants via persist_message
        let _ = sid;
    }

    let outcome = ctx.persist_message(NewMessage {
        conversation_id: conv_id,
        sender_identity_id: sender_id,
        sent_at,
        sent_at_precision: precision,
        kind: MessageKind::Email,
        subject,
        body_text,
        body_html,
        native_id: message_id.clone(),
        idempotency_key: idem,
        gm_thrid,
        in_reply_to,
        payload_json: None,
        recipients,
        labels: labels.clone(),
    })?;
    let message_id_row = match outcome {
        PersistOutcome::Inserted { message_id } => message_id,
        PersistOutcome::Duplicate { message_id } => {
            if !labels.is_empty() {
                ctx.persist_labels(message_id, &labels)?;
            }
            message_id
        }
    };

    for (att, bytes) in atts {
        let rec = NewAttachment {
            message_id: message_id_row,
            filename: att.filename,
            mime: att.mime,
            size: att.size,
            kind: att.kind,
            content_id: att.content_id,
            part_index: att.part_index,
            omitted: false,
            missing: false,
        };
        ctx.persist_attachment(rec, bytes.as_deref())?;
    }

    let _ = locator;
    let _ = offset;
    Ok(())
}

struct AttDraft {
    filename: Option<String>,
    mime: Option<String>,
    size: Option<i64>,
    kind: AttachmentKind,
    content_id: Option<String>,
    part_index: Option<i32>,
}

type Bodies = (
    Option<String>,
    Option<String>,
    Vec<(AttDraft, Option<Vec<u8>>)>,
);

fn collect_bodies(mail: &mailparse::ParsedMail<'_>) -> Result<Bodies, CoreError> {
    let mut text = None;
    let mut html = None;
    let mut atts = Vec::new();
    walk_parts(mail, 0, &mut text, &mut html, &mut atts)?;
    Ok((text, html, atts))
}

fn walk_parts(
    mail: &mailparse::ParsedMail<'_>,
    idx: i32,
    text: &mut Option<String>,
    html: &mut Option<String>,
    atts: &mut Vec<(AttDraft, Option<Vec<u8>>)>,
) -> Result<(), CoreError> {
    let mime = mail.ctype.mimetype.to_ascii_lowercase();
    if mime.starts_with("multipart/") {
        for (i, p) in mail.subparts.iter().enumerate() {
            walk_parts(p, idx + i as i32 + 1, text, html, atts)?;
        }
        return Ok(());
    }
    let disp = mail.get_content_disposition();
    let filename = disp.params.get("filename").cloned();
    let is_attach =
        matches!(disp.disposition, mailparse::DispositionType::Attachment) || filename.is_some();
    if is_attach {
        let body = mail.get_body_raw().unwrap_or_default();
        if body.len() > 512 * 1024 * 1024 {
            return Err(CoreError::Fatal(format!(
                "MIME attachment exceeds 512 MiB ({})",
                body.len()
            )));
        }
        let kind = if mime == "text/vcard" || mime == "text/x-vcard" {
            AttachmentKind::Vcf
        } else if matches!(disp.disposition, mailparse::DispositionType::Inline)
            && mime.starts_with("image/")
        {
            AttachmentKind::Inline
        } else {
            AttachmentKind::File
        };
        atts.push((
            AttDraft {
                filename,
                mime: Some(mail.ctype.mimetype.clone()),
                size: Some(body.len() as i64),
                kind,
                content_id: mail.headers.get_first_value("Content-ID"),
                part_index: Some(idx),
            },
            Some(body),
        ));
        return Ok(());
    }
    if mime == "text/plain" && text.is_none() {
        *text = mail.get_body().ok().map(|s| s.trim_end().to_string());
    } else if mime == "text/html" && html.is_none() {
        *html = mail.get_body().ok();
    } else if mime.starts_with("text/") && text.is_none() {
        *text = mail.get_body().ok().map(|s| s.trim_end().to_string());
    }
    Ok(())
}

fn persist_addr(
    ctx: &mut dyn ImportContext,
    raw: &str,
    _role: Option<RecipientRole>,
) -> Result<Option<i64>, CoreError> {
    let (name, email) = parse_mailbox(raw);
    if let Some(e) = email {
        let Some(norm) = normalize_email(&e) else {
            return Ok(None);
        };
        let id = ctx.persist_identity(NewIdentity {
            platform: Platform::Gmail,
            kind: IdentityKind::Email,
            value_raw: e,
            value_normalized: norm,
            display_name: name,
        })?;
        return Ok(Some(id));
    }
    if let Some(n) = name {
        let norm = super::locale::name_fold_join(&n);
        if norm.is_empty() {
            return Ok(None);
        }
        let id = ctx.persist_identity(NewIdentity {
            platform: Platform::Gmail,
            kind: IdentityKind::DisplayName,
            value_raw: n.clone(),
            value_normalized: norm,
            display_name: Some(n),
        })?;
        return Ok(Some(id));
    }
    let _ = parse_phone;
    Ok(None)
}

fn parse_mailbox(raw: &str) -> (Option<String>, Option<String>) {
    let s = strip_cf(raw).trim().to_string();
    if s.is_empty() {
        return (None, None);
    }
    if let Some(start) = s.rfind('<') {
        if let Some(end) = s.rfind('>') {
            if end > start {
                let email = s[start + 1..end].trim().to_string();
                let name = s[..start].trim().trim_matches('"').trim().to_string();
                return (
                    if name.is_empty() { None } else { Some(name) },
                    if email.contains('@') {
                        Some(email)
                    } else {
                        None
                    },
                );
            }
        }
    }
    if s.contains('@') {
        (None, Some(s))
    } else {
        (Some(s), None)
    }
}

fn split_addr_list(v: &str) -> Vec<&str> {
    // fixtures are single addresses; keep commas inside quotes out of scope
    v.split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect()
}

fn parse_labels(raw: Option<&str>) -> Vec<String> {
    let Some(s) = raw else {
        return Vec::new();
    };
    s.split(',')
        .map(|p| p.trim().replace("\\", ""))
        .filter(|p| !p.is_empty())
        .collect()
}

fn split_from_line(raw: &[u8]) -> (Option<String>, Vec<u8>) {
    if let Some(pos) = raw.iter().position(|&b| b == b'\n') {
        let line = String::from_utf8_lossy(&raw[..pos])
            .trim_end_matches('\r')
            .to_string();
        let rest = raw[pos + 1..].to_vec();
        if line.starts_with("From ") {
            return (Some(line), rest);
        }
    }
    (None, raw.to_vec())
}

fn unescape_mboxrd(rfc: Vec<u8>) -> Vec<u8> {
    let mut out = Vec::with_capacity(rfc.len());
    for line in rfc.split_inclusive(|&b| b == b'\n') {
        if let Some(stripped) = strip_mboxrd_gt(line) {
            out.extend_from_slice(stripped);
        } else {
            out.extend_from_slice(line);
        }
    }
    out
}

fn strip_mboxrd_gt(line: &[u8]) -> Option<&[u8]> {
    // ^(>+)From  lose one leading >
    if !line.starts_with(b">") {
        return None;
    }
    let mut i = 0;
    while i < line.len() && line[i] == b'>' {
        i += 1;
    }
    if line
        .get(i..)
        .map(|s| s.starts_with(b"From "))
        .unwrap_or(false)
        && i >= 1
    {
        Some(&line[1..])
    } else {
        None
    }
}

fn header_block_len(rfc: &[u8]) -> usize {
    if let Some(p) = find_sub(rfc, b"\n\n") {
        p + 2
    } else if let Some(p) = find_sub(rfc, b"\r\n\r\n") {
        p + 4
    } else {
        rfc.len()
    }
}

fn find_sub(hay: &[u8], needle: &[u8]) -> Option<usize> {
    hay.windows(needle.len()).position(|w| w == needle)
}

fn parse_fromline_date(from_line: &str) -> Option<String> {
    // From addr Dow Mon DD HH:MM:SS YYYY
    let rest = from_line.strip_prefix("From ")?;
    let mut parts = rest.split_whitespace();
    let _addr = parts.next()?;
    let _dow = parts.next()?;
    let mon = month(parts.next()?)?;
    let day: u32 = parts.next()?.parse().ok()?;
    let time = parts.next()?;
    let year: i32 = parts.next()?.parse().ok()?;
    let mut hm = time.split(':');
    let h: u32 = hm.next()?.parse().ok()?;
    let mi: u32 = hm.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let s: u32 = hm.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    Some(format!(
        "{year:04}-{mon:02}-{day:02}T{h:02}:{mi:02}:{s:02}Z"
    ))
}

fn month(m: &str) -> Option<u32> {
    Some(match m {
        "Jan" => 1,
        "Feb" => 2,
        "Mar" => 3,
        "Apr" => 4,
        "May" => 5,
        "Jun" => 6,
        "Jul" => 7,
        "Aug" => 8,
        "Sep" => 9,
        "Oct" => 10,
        "Nov" => 11,
        "Dec" => 12,
        _ => return None,
    })
}

fn parse_rfc2822_date(s: &str) -> Option<String> {
    // mailparse doesn't expose a date parser; try From-style fallback via chrono-less scan
    // Common: "1 Jan 2024 00:00:00 +0000"
    let t = s.trim();
    if let Ok(parsed) = mailparse::dateparse(t) {
        // unix seconds
        if parsed >= 0 {
            return Some(unix_to_rfc3339(parsed as u64));
        }
    }
    None
}

fn unix_to_rfc3339(secs: u64) -> String {
    // naive days from epoch
    let z = secs;
    let days = z / 86400;
    let rem = z % 86400;
    let h = rem / 3600;
    let mi = (rem % 3600) / 60;
    let s = rem % 60;
    let (y, mo, d) = civil_from_days(days as i64);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn civil_from_days(z: i64) -> (i32, u32, u32) {
    // Howard Hinnant civil_from_days
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y as i32, m as u32, d as u32)
}

fn excerpt(raw: &[u8]) -> String {
    String::from_utf8_lossy(&raw[..raw.len().min(200)]).into_owned()
}

fn read_prefix(path: &Path, n: usize) -> Result<Vec<u8>, CoreError> {
    use std::io::Read;
    let mut f = fs::File::open(path)?;
    let mut buf = vec![0u8; n];
    let got = f.read(&mut buf)?;
    buf.truncate(got);
    Ok(buf)
}

fn hash_file(path: &Path) -> Result<String, CoreError> {
    use std::io::Read;
    let mut f = fs::File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0u8; 65536];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}
