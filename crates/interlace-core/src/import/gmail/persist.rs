//! Persist one RFC822 record from an mbox.

use mailparse::MailHeaderMap;

use super::mbox::{header_block_len, split_from_line, unescape_mboxrd};
use super::parse::{
    parse_fromline_date, parse_labels, parse_mailbox, parse_rfc2822_date, split_addr_list,
};
use super::HEADER_CAP;
use crate::import::locale::{normalize_email, parse_phone};
use crate::import::ImportContext;
use crate::model::*;

pub(super) fn persist_rfc822(
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
        let norm = crate::import::locale::name_fold_join(&n);
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
