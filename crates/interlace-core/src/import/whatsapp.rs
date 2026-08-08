//! WhatsApp Android/iOS ZIP importer (D16, D18, D22, D23).

use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

use zip::ZipArchive;

use super::locale::{
    is_encryption_banner, is_you_token, load_pack, looks_like_group_system, match_media,
    name_fold_join, parse_dt_with_pack, parse_header_line, parse_phone, split_sender_body,
    strip_cf, strip_forwarded, strip_title_prefix, title_has_group_prefix, vote_locale,
    HeaderFamily, LocalePack, MediaMatch,
};
use super::{ImportContext, SourceImporter};
use crate::cas::validate_zip_entry_name;
use crate::model::*;

const MEDIA_ENTRY_CAP: u64 = 512 * 1024 * 1024;
const ENTRY_COUNT_CAP: usize = 2_000_000;

#[derive(Default)]
pub struct WhatsappImporter {
    pub opts: ImportOpts,
}

impl SourceImporter for WhatsappImporter {
    fn id(&self) -> SourceKind {
        SourceKind::WhatsappAndroidZip
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        let listed = list_zip(path)?;
        let (chat_name, ios) = find_chat_entry(&listed)?;
        validate_zip_entry_name(&chat_name)?;
        let kind = if ios {
            SourceKind::WhatsappIosZip
        } else {
            SourceKind::WhatsappAndroidZip
        };
        let bytes = std::fs::metadata(path).ok().map(|m| m.len());
        let file_blake3 = hash_file(path).ok();
        let chat = read_zip_entry(path, &chat_name, self.opts.max_bytes)?;
        let (text, mut notes) = decode_chat(&chat);
        let family = if ios {
            HeaderFamily::Ios
        } else {
            HeaderFamily::Android
        };
        let lines: Vec<&str> = text.lines().collect();
        let locale_guess = if let Some(ref loc) = self.opts.locale {
            let _ = load_pack(loc)?;
            Some(loc.clone())
        } else {
            match vote_locale(&lines, Some(family)) {
                Ok(id) => Some(id),
                Err(e) => {
                    notes.push(e.to_string());
                    None
                }
            }
        };
        if listed.iter().any(|n| looks_like_media_name(n)) {
            notes.push("media entries present".into());
        }
        let label = path
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("whatsapp.zip")
            .to_string();
        Ok(ProbeResult {
            kind,
            label,
            bytes,
            file_blake3,
            locale_guess,
            notes,
        })
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        let probe = self.probe(path)?;
        let family = match probe.kind {
            SourceKind::WhatsappIosZip => HeaderFamily::Ios,
            SourceKind::WhatsappAndroidZip => HeaderFamily::Android,
            _ => return Err(CoreError::Probe("not a WhatsApp zip after probe".into())),
        };
        let listed = list_zip(path)?;
        if listed.len() > ENTRY_COUNT_CAP {
            return Err(CoreError::Fatal(format!(
                "zip entry count {} exceeds 2M cap",
                listed.len()
            )));
        }
        let (chat_name, _) = find_chat_entry(&listed)?;
        let chat_bytes = read_zip_entry(path, &chat_name, self.opts.max_bytes)?;
        let (text, decode_notes) = decode_chat(&chat_bytes);
        for n in decode_notes {
            ctx.warn(Warning {
                severity: Severity::Warn,
                locator: chat_name.clone(),
                kind: "decode".into(),
                detail: n,
                raw_excerpt: None,
            })?;
        }

        let locale_id = if let Some(ref loc) = self.opts.locale {
            load_pack(loc)?;
            loc.clone()
        } else if let Some(ref g) = probe.locale_guess {
            g.clone()
        } else {
            let lines: Vec<&str> = text.lines().collect();
            vote_locale(&lines, Some(family))?
        };
        let pack = load_pack(&locale_id)?;

        let raw_title = conversation_title(&self.opts, path, &chat_name, &pack);
        let title = strip_title_prefix(&pack, &raw_title);
        let folded_title = name_fold_join(&title);
        let native_id = format!(
            "whatsapp:{}",
            if folded_title.is_empty() {
                "chat".into()
            } else {
                folded_title
            }
        );

        let parsed = parse_chat(&text, &pack, family, &chat_name, ctx)?;

        let mut non_self: HashSet<String> = HashSet::new();
        let mut group = title_has_group_prefix(&pack, &raw_title);
        let mut join_cutoff = false;
        for (i, m) in parsed.iter().enumerate() {
            if m.kind == MessageKind::System {
                if looks_like_group_system(&pack, &m.rest_raw) {
                    group = true;
                    if i == 0
                        || (i == 1 && parsed.first().map(|x| x.kind) == Some(MessageKind::System))
                    {
                        // first real event after optional encryption banner
                        if i == 0 || is_encryption_banner(&pack, &parsed[0].rest_raw) {
                            join_cutoff = looks_like_group_system(&pack, &m.rest_raw);
                        }
                    }
                }
                continue;
            }
            if let Some(ref s) = m.sender_raw {
                if !is_you_token(&pack, s) {
                    non_self.insert(s.clone());
                }
            }
        }
        if non_self.len() >= 2 {
            group = true;
        }
        let conv_kind = if group {
            ConversationKind::Group
        } else {
            ConversationKind::Dm
        };
        let extra = if join_cutoff {
            Some(r#"{"join_cutoff":true}"#.to_string())
        } else {
            None
        };

        let conv_id = ctx.persist_conversation(NewConversation {
            platform: Platform::Whatsapp,
            kind: conv_kind,
            native_id: native_id.clone(),
            title: Some(title.clone()),
            extra_json: extra,
        })?;

        let region = None; // archive setting is applied in run_import via identity persist; D16 uses title/token
        let dm_phone = if !group {
            parse_phone(&title, region)
        } else {
            None
        };

        let ckpt_line = ctx
            .load_checkpoint("wa_line")?
            .and_then(|c| c.cursor_value.get("line_no").and_then(|v| v.as_u64()))
            .unwrap_or(0);

        let mut seq_map: HashMap<(String, String, String), u64> = HashMap::new();
        let mut ident_cache: HashMap<(IdentityKind, String), i64> = HashMap::new();

        let zip_names: HashSet<String> = listed.iter().map(|n| basename(n)).collect();
        // also keep full names for lookup
        let name_index: HashMap<String, String> =
            listed.iter().map(|n| (basename(n), n.clone())).collect();

        for m in &parsed {
            let sender_norm = match m.sender_raw.as_deref() {
                Some(s) if is_you_token(&pack, s) => name_fold_join(s),
                Some(s) => {
                    if let Some(e164) = parse_phone(s, region) {
                        e164
                    } else if let Some(ref e164) = dm_phone {
                        e164.clone()
                    } else {
                        name_fold_join(s)
                    }
                }
                None => String::new(),
            };
            let body_stripped = body_without_media_token(&pack, &m.body);
            let sent_key = m.sent_at.clone().unwrap_or_default();
            let seq_key = (sent_key.clone(), sender_norm.clone(), body_stripped.clone());
            let seq = {
                let e = seq_map.entry(seq_key).or_insert(0);
                let cur = *e;
                *e += 1;
                cur
            };

            if m.line_no as u64 <= ckpt_line {
                continue;
            }

            let sender_id = if let Some(ref s) = m.sender_raw {
                Some(persist_sender(
                    ctx,
                    &pack,
                    s,
                    conv_kind,
                    dm_phone.as_deref(),
                    region,
                    &mut ident_cache,
                )?)
            } else {
                None
            };

            let idem = wa_idempotency(&native_id, &sent_key, &sender_norm, &body_stripped, seq);
            let kind = m.kind;
            let outcome = ctx.persist_message(NewMessage {
                conversation_id: conv_id,
                sender_identity_id: sender_id,
                sent_at: m.sent_at.clone(),
                sent_at_precision: m.precision,
                kind,
                subject: None,
                body_text: Some(m.body.clone()),
                body_html: None,
                native_id: Some(format!("wa-line:{}", m.line_no)),
                idempotency_key: idem,
                gm_thrid: None,
                in_reply_to: None,
                payload_json: m.payload_json.clone(),
                recipients: Vec::new(),
                labels: Vec::new(),
            })?;
            let message_id = match outcome {
                PersistOutcome::Inserted { message_id } => message_id,
                PersistOutcome::Duplicate { message_id } => message_id,
            };

            match &m.media {
                MediaMatch::None => {}
                MediaMatch::Omitted => {
                    ctx.persist_attachment(
                        NewAttachment {
                            message_id,
                            filename: None,
                            mime: None,
                            size: None,
                            kind: AttachmentKind::File,
                            content_id: None,
                            part_index: None,
                            omitted: true,
                            missing: false,
                        },
                        None,
                    )?;
                }
                MediaMatch::File(fname) => {
                    let safe = basename(fname);
                    if validate_zip_entry_name(fname).is_err()
                        || validate_zip_entry_name(&safe).is_err()
                    {
                        ctx.warn(Warning {
                            severity: Severity::Reject,
                            locator: format!("{}:{}", chat_name, m.line_no),
                            kind: "zip_slip".into(),
                            detail: format!("media path rejected: {fname}"),
                            raw_excerpt: Some(fname.clone()),
                        })?;
                    } else if !zip_names.contains(&safe) {
                        ctx.warn(Warning {
                            severity: Severity::Warn,
                            locator: format!("{}:{}", chat_name, m.line_no),
                            kind: "missing_media".into(),
                            detail: format!("referenced media not in zip: {safe}"),
                            raw_excerpt: Some(safe.clone()),
                        })?;
                        ctx.persist_attachment(
                            NewAttachment {
                                message_id,
                                filename: Some(safe),
                                mime: mime_from_name(fname),
                                size: None,
                                kind: attach_kind_from_name(fname),
                                content_id: None,
                                part_index: None,
                                omitted: false,
                                missing: true,
                            },
                            None,
                        )?;
                    } else {
                        let entry = name_index
                            .get(&safe)
                            .cloned()
                            .unwrap_or_else(|| fname.clone());
                        match read_zip_entry_capped(path, &entry, MEDIA_ENTRY_CAP) {
                            Ok(bytes) => {
                                let size = bytes.len() as i64;
                                ctx.persist_attachment(
                                    NewAttachment {
                                        message_id,
                                        filename: Some(safe),
                                        mime: mime_from_name(fname),
                                        size: Some(size),
                                        kind: attach_kind_from_name(fname),
                                        content_id: None,
                                        part_index: None,
                                        omitted: false,
                                        missing: false,
                                    },
                                    Some(&bytes),
                                )?;
                            }
                            Err(e) => {
                                ctx.warn(Warning {
                                    severity: Severity::Reject,
                                    locator: format!("{}:{}", chat_name, m.line_no),
                                    kind: "media_read".into(),
                                    detail: e.to_string(),
                                    raw_excerpt: Some(fname.clone()),
                                })?;
                            }
                        }
                    }
                }
            }

            ctx.checkpoint(Checkpoint {
                cursor_kind: "wa_line".into(),
                cursor_value: serde_json::json!({
                    "entry": chat_name,
                    "line_no": m.line_no,
                    "seq_bucket": sent_key,
                    "seq": seq,
                }),
            })?;
            ctx.maybe_commit()?;
        }

        if parsed
            .iter()
            .filter(|m| m.kind != MessageKind::System)
            .count()
            >= 40_000
        {
            ctx.warn(Warning {
                severity: Severity::Warn,
                locator: chat_name,
                kind: "history_ceiling".into(),
                detail: "export has ≥40000 messages; WhatsApp may have truncated older history"
                    .into(),
                raw_excerpt: None,
            })?;
        }

        let _ = probe;
        Ok(ImportStats::default())
    }
}

struct ParsedLine {
    line_no: usize,
    sent_at: Option<String>,
    precision: SentAtPrecision,
    sender_raw: Option<String>,
    body: String,
    kind: MessageKind,
    media: MediaMatch,
    rest_raw: String,
    payload_json: Option<String>,
}

fn parse_chat(
    text: &str,
    pack: &LocalePack,
    family: HeaderFamily,
    chat_name: &str,
    ctx: &mut dyn ImportContext,
) -> Result<Vec<ParsedLine>, CoreError> {
    let mut out: Vec<ParsedLine> = Vec::new();
    for (idx, raw_line) in text.lines().enumerate() {
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
    Ok(out)
}

fn persist_sender(
    ctx: &mut dyn ImportContext,
    pack: &LocalePack,
    sender: &str,
    conv_kind: ConversationKind,
    dm_phone: Option<&str>,
    region: Option<&str>,
    cache: &mut HashMap<(IdentityKind, String), i64>,
) -> Result<i64, CoreError> {
    let token = strip_cf(sender.trim());
    if is_you_token(pack, &token) {
        let norm = name_fold_join(&token);
        return upsert(
            ctx,
            cache,
            IdentityKind::DisplayName,
            &token,
            &norm,
            Some(token.clone()),
        );
    }
    if let Some(e164) = parse_phone(&token, region) {
        return upsert(ctx, cache, IdentityKind::Phone, &token, &e164, None);
    }
    if conv_kind == ConversationKind::Dm {
        if let Some(e164) = dm_phone {
            return upsert(
                ctx,
                cache,
                IdentityKind::Phone,
                e164,
                e164,
                Some(token.clone()),
            );
        }
    }
    let norm = name_fold_join(&token);
    let norm = if norm.is_empty() {
        token.to_lowercase()
    } else {
        norm
    };
    upsert(
        ctx,
        cache,
        IdentityKind::DisplayName,
        &token,
        &norm,
        Some(token.clone()),
    )
}

fn upsert(
    ctx: &mut dyn ImportContext,
    cache: &mut HashMap<(IdentityKind, String), i64>,
    kind: IdentityKind,
    raw: &str,
    norm: &str,
    display_name: Option<String>,
) -> Result<i64, CoreError> {
    if let Some(id) = cache.get(&(kind, norm.to_string())) {
        return Ok(*id);
    }
    let id = ctx.persist_identity(NewIdentity {
        platform: Platform::Whatsapp,
        kind,
        value_raw: raw.to_string(),
        value_normalized: norm.to_string(),
        display_name,
    })?;
    cache.insert((kind, norm.to_string()), id);
    Ok(id)
}

fn wa_idempotency(
    native_conversation_id: &str,
    sent_at: &str,
    sender_normalized: &str,
    body_without_media: &str,
    seq: u64,
) -> String {
    let mut h = blake3::Hasher::new();
    h.update(b"wa-v1");
    h.update(native_conversation_id.as_bytes());
    h.update(&[0]);
    h.update(sent_at.as_bytes());
    h.update(&[0]);
    h.update(sender_normalized.as_bytes());
    h.update(&[0]);
    h.update(body_without_media.as_bytes());
    h.update(&[0]);
    h.update(seq.to_string().as_bytes());
    format!("wa:{}", h.finalize().to_hex())
}

fn body_without_media_token(pack: &LocalePack, body: &str) -> String {
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

fn conversation_title(
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

fn list_zip(path: &Path) -> Result<Vec<String>, CoreError> {
    let f = File::open(path)?;
    let mut zip = ZipArchive::new(f).map_err(|e| CoreError::Probe(format!("not a zip: {e}")))?;
    let mut names = Vec::with_capacity(zip.len());
    for i in 0..zip.len() {
        let e = zip
            .by_index(i)
            .map_err(|e| CoreError::Parse(format!("zip index {i}: {e}")))?;
        if e.is_dir() {
            continue;
        }
        names.push(e.name().replace('\\', "/"));
    }
    Ok(names)
}

fn find_chat_entry(names: &[String]) -> Result<(String, bool), CoreError> {
    let mut txts: Vec<String> = Vec::new();
    for n in names {
        if validate_zip_entry_name(n).is_err() {
            continue;
        }
        let file = basename(n);
        let depth = n
            .trim_matches('/')
            .split('/')
            .filter(|s| !s.is_empty())
            .count();
        if file.eq_ignore_ascii_case("_chat.txt") {
            return Ok((n.clone(), true));
        }
        if file.rsplit('.').next() == Some("txt") && depth <= 2 {
            txts.push(n.clone());
        }
    }
    match txts.len() {
        1 => Ok((txts.remove(0), false)),
        0 => Err(CoreError::Probe(
            "ZIP has no _chat.txt and no single *.txt chat".into(),
        )),
        _ => Err(CoreError::Probe(format!(
            "ambiguous WhatsApp txt entries: {}",
            txts.join(", ")
        ))),
    }
}

fn read_zip_entry(path: &Path, name: &str, max_bytes: u64) -> Result<Vec<u8>, CoreError> {
    read_zip_entry_capped(path, name, max_bytes)
}

fn read_zip_entry_capped(path: &Path, name: &str, max_bytes: u64) -> Result<Vec<u8>, CoreError> {
    validate_zip_entry_name(name)?;
    let f = File::open(path)?;
    let mut zip = ZipArchive::new(f).map_err(|e| CoreError::Parse(format!("zip: {e}")))?;
    let mut e = zip
        .by_name(name)
        .map_err(|err| CoreError::Parse(format!("zip entry {name}: {err}")))?;
    let sz = e.size();
    if sz > max_bytes {
        return Err(CoreError::Fatal(format!(
            "zip entry {name} uncompressed {sz} exceeds cap {max_bytes}"
        )));
    }
    let mut buf = Vec::with_capacity(sz as usize);
    e.read_to_end(&mut buf)?;
    if buf.len() as u64 > max_bytes {
        return Err(CoreError::Fatal(format!(
            "zip entry {name} read {} exceeds cap {max_bytes}",
            buf.len()
        )));
    }
    Ok(buf)
}

fn decode_chat(bytes: &[u8]) -> (String, Vec<String>) {
    let mut notes = Vec::new();
    if bytes.starts_with(&[0xFF, 0xFE]) {
        let u16s: Vec<u16> = bytes[2..]
            .chunks(2)
            .filter_map(|c| {
                if c.len() == 2 {
                    Some(u16::from_le_bytes([c[0], c[1]]))
                } else {
                    None
                }
            })
            .collect();
        return (String::from_utf16_lossy(&u16s), notes);
    }
    let start = if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
        3
    } else {
        0
    };
    match std::str::from_utf8(&bytes[start..]) {
        Ok(s) => (s.to_string(), notes),
        Err(_) => {
            let lossy = String::from_utf8_lossy(&bytes[start..]);
            let repl = lossy
                .chars()
                .filter(|c| *c == char::REPLACEMENT_CHARACTER)
                .count();
            let total = lossy.chars().count().max(1);
            if (repl as f64) / (total as f64) > 0.02 && bytes.len() % 2 == 0 {
                let u16s: Vec<u16> = bytes
                    .chunks(2)
                    .map(|c| u16::from_le_bytes([c[0], c[1]]))
                    .collect();
                notes.push("decoded chat as UTF-16LE after high UTF-8 replacement ratio".into());
                return (String::from_utf16_lossy(&u16s), notes);
            }
            notes.push("decoded chat as UTF-8 lossy".into());
            (lossy.into_owned(), notes)
        }
    }
}

fn hash_file(path: &Path) -> Result<String, CoreError> {
    let mut f = File::open(path)?;
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

fn basename(name: &str) -> String {
    name.replace('\\', "/")
        .rsplit('/')
        .next()
        .unwrap_or(name)
        .to_string()
}

fn looks_like_media_name(name: &str) -> bool {
    let b = basename(name);
    b.starts_with("IMG-")
        || b.starts_with("PTT-")
        || b.starts_with("VID-")
        || b.starts_with("AUD-")
        || b.starts_with("STK-")
}

fn attach_kind_from_name(name: &str) -> AttachmentKind {
    let b = basename(name);
    if b.starts_with("STK-") || b.to_ascii_lowercase().contains("sticker") {
        return AttachmentKind::Sticker;
    }
    if b.starts_with("PTT-") || b.starts_with("AUD-") {
        return AttachmentKind::Voice;
    }
    if b.starts_with("VID-") {
        return AttachmentKind::Video;
    }
    if b.starts_with("IMG-") {
        return AttachmentKind::Image;
    }
    let ext = PathBuf::from(&b)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    match ext.as_str() {
        "jpg" | "jpeg" | "png" | "gif" | "heic" | "webp" => AttachmentKind::Image,
        "mp4" | "mov" | "mkv" | "avi" => AttachmentKind::Video,
        "opus" | "ogg" | "mp3" | "m4a" | "wav" | "aac" => AttachmentKind::Voice,
        "vcf" | "vcard" => AttachmentKind::Vcf,
        _ => AttachmentKind::File,
    }
}

fn mime_from_name(name: &str) -> Option<String> {
    let ext = PathBuf::from(basename(name))
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    Some(
        match ext.as_str() {
            "jpg" | "jpeg" => "image/jpeg",
            "png" => "image/png",
            "gif" => "image/gif",
            "webp" => "image/webp",
            "mp4" => "video/mp4",
            "opus" => "audio/opus",
            "ogg" => "audio/ogg",
            "vcf" => "text/vcard",
            _ => return None,
        }
        .to_string(),
    )
}
