//! Persist parsed WhatsApp messages, senders, and attachments.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use super::parse::{body_without_media_token, conversation_title, parse_chat, sender_matches_self};
use super::zip::{
    attach_kind_from_name, basename, decode_chat, find_chat_entry, list_zip, mime_from_name,
    read_zip_entry, read_zip_entry_capped,
};
use super::WhatsappImporter;
use crate::cas::validate_zip_entry_name;
use crate::import::locale::{
    is_encryption_banner, is_you_token, load_pack, looks_like_group_system, name_fold_join,
    parse_phone, strip_cf, strip_title_prefix, title_has_group_prefix, title_looks_like_dm,
    vote_locale, HeaderFamily, LocalePack, MediaMatch,
};
use crate::import::ImportContext;
use crate::model::*;

const MEDIA_ENTRY_CAP: u64 = 512 * 1024 * 1024;
const ENTRY_COUNT_CAP: usize = 2_000_000;

pub(super) fn import(
    importer: &WhatsappImporter,
    path: &Path,
    ctx: &mut dyn ImportContext,
) -> Result<ImportStats, CoreError> {
    // Do not call probe() again: that re-opens the ZIP and re-hashes it.
    let listed = list_zip(path, importer.opts.cancel.as_ref())?;
    let (chat_name, ios) = find_chat_entry(&listed)?;
    let family = if ios {
        HeaderFamily::Ios
    } else {
        HeaderFamily::Android
    };
    if listed.len() > ENTRY_COUNT_CAP {
        return Err(CoreError::Fatal(format!(
            "zip entry count {} exceeds 2M cap",
            listed.len()
        )));
    }
    let chat_bytes = read_zip_entry(
        path,
        &chat_name,
        importer.opts.max_bytes,
        importer.opts.cancel.as_ref(),
    )?;
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

    let locale_id = if let Some(ref loc) = importer.opts.locale {
        load_pack(loc)?;
        loc.clone()
    } else {
        let lines: Vec<&str> = text.lines().collect();
        vote_locale(&lines, Some(family), importer.opts.phone_region.as_deref())?
    };
    let pack = load_pack(&locale_id)?;

    let raw_title = conversation_title(&importer.opts, path, &chat_name, &pack);
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

    let parsed = parse_chat(
        &text,
        &pack,
        family,
        &chat_name,
        ctx,
        importer.opts.cancel.as_ref(),
    )?;
    let self_folds = ctx.owner_self_folds()?;

    let mut humans: HashSet<String> = HashSet::new();
    let mut non_self: HashSet<String> = HashSet::new();
    let group_prefix = title_has_group_prefix(&pack, &raw_title);
    let mut group_system = false;
    let mut group = group_prefix;
    let mut join_cutoff = false;
    for (i, m) in parsed.iter().enumerate() {
        if m.kind == MessageKind::System {
            if looks_like_group_system(&pack, &m.rest_raw) {
                group_system = true;
                group = true;
                if i == 0 || (i == 1 && parsed.first().map(|x| x.kind) == Some(MessageKind::System))
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
            humans.insert(s.clone());
            if !is_you_token(&pack, s) {
                non_self.insert(s.clone());
            }
        }
    }
    if non_self.len() >= 2 {
        group = true;
    }
    // D18-C: iOS 1:1 with owner display name (not you_token) stays DM.
    let zip_stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
    let chat_stem = Path::new(&chat_name)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("");
    let dm_shaped = title_looks_like_dm(&pack, &[zip_stem, chat_stem, raw_title.as_str()]);
    let owner_named: Vec<String> = humans
        .iter()
        .filter(|s| !is_you_token(&pack, s) && sender_matches_self(s, &self_folds))
        .cloned()
        .collect();
    let mut owner_self_token: Option<String> = None;
    if group
        && !group_system
        && !group_prefix
        && dm_shaped
        && humans.len() == 2
        && owner_named.len() == 1
    {
        group = false;
        owner_self_token = owner_named.into_iter().next();
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

        let sender_is_me = m
            .sender_raw
            .as_deref()
            .is_some_and(|s| is_you_token(&pack, s) || owner_self_token.as_deref() == Some(s));
        let sender_id = if let Some(ref s) = m.sender_raw {
            let id = persist_sender(
                ctx,
                &pack,
                s,
                conv_kind,
                dm_phone.as_deref(),
                region,
                &mut ident_cache,
            )?;
            if owner_self_token.as_deref() == Some(s.as_str()) {
                ctx.link_identity_to_self_person(id)?;
            }
            Some(id)
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
        if sender_is_me {
            if let Some(sid) = sender_id {
                ctx.set_participant_role(conv_id, sid, "me")?;
            }
        }

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
                    match read_zip_entry_capped(
                        path,
                        &entry,
                        MEDIA_ENTRY_CAP,
                        importer.opts.cancel.as_ref(),
                    ) {
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
                            if matches!(e, CoreError::Cancelled) {
                                return Err(e);
                            }
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
            detail: "export has ≥40000 messages; WhatsApp may have truncated older history".into(),
            raw_excerpt: None,
        })?;
    }

    Ok(ImportStats::default())
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
