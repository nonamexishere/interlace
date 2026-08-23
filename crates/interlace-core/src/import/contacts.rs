//! vCard + Google/Outlook CSV contacts (C1).

use std::fs;
use std::path::Path;

use data_encoding::BASE64;

use super::locale::{normalize_email, parse_phone, strip_cf};
use super::{ImportContext, SourceImporter};
use crate::model::*;

#[derive(Default)]
pub struct ContactsImporter {
    pub opts: ImportOpts,
    pub kind: Option<SourceKind>,
}

impl SourceImporter for ContactsImporter {
    fn id(&self) -> SourceKind {
        self.kind.unwrap_or(SourceKind::ContactsVcf)
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        if !path.is_file() {
            return Err(CoreError::Probe(format!(
                "not a contacts file: {}",
                path.display()
            )));
        }
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        let kind = match ext.as_str() {
            "vcf" | "vcard" => SourceKind::ContactsVcf,
            "csv" => SourceKind::ContactsCsv,
            _ => return Err(CoreError::Probe("expected .vcf or .csv".into())),
        };
        if kind == SourceKind::ContactsCsv {
            let head = fs::read_to_string(path).unwrap_or_default();
            let first = head.lines().next().unwrap_or("");
            if !(first.contains("E-mail")
                || first.contains("Email")
                || first.contains("First Name"))
            {
                return Err(CoreError::Probe(
                    "CSV header is not a contacts export".into(),
                ));
            }
        }
        Ok(ProbeResult {
            kind,
            label: path
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("contacts")
                .to_string(),
            bytes: fs::metadata(path).ok().map(|m| m.len()),
            file_blake3: super::optional_file_hash(path, self.opts.cancel.as_ref())?,
            locale_guess: None,
            notes: vec![],
        })
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        let kind = self.probe(path)?.kind;
        match kind {
            SourceKind::ContactsVcf => import_vcf_file(ctx, path)?,
            SourceKind::ContactsCsv => import_csv_file(ctx, path)?,
            _ => {
                return Err(CoreError::Probe(
                    "contacts importer got a non-contacts path".into(),
                ))
            }
        }
        Ok(ImportStats::default())
    }
}

pub fn import_vcf_file(ctx: &mut dyn ImportContext, path: &Path) -> Result<(), CoreError> {
    let text = fs::read_to_string(path)
        .or_else(|_| fs::read(path).map(|b| String::from_utf8_lossy(&b).into_owned()))?;
    import_vcf_text(ctx, &text)
}

pub fn import_vcf_text(ctx: &mut dyn ImportContext, text: &str) -> Result<(), CoreError> {
    let ckpt = ctx
        .load_checkpoint("vcf_index")?
        .and_then(|c| c.cursor_value.get("index").and_then(|v| v.as_u64()))
        .unwrap_or(0);
    let cards = split_vcards(&unfold(text));
    for (i, card) in cards.iter().enumerate() {
        if (i as u64) < ckpt {
            continue;
        }
        let rec = parse_vcard(card)?;
        if rec
            .fn_
            .as_ref()
            .map(|s| s.trim().is_empty())
            .unwrap_or(true)
            && rec.n_family.is_none()
            && rec.n_given.is_none()
        {
            ctx.warn(Warning {
                severity: Severity::Warn,
                locator: format!("vcf:{}", i),
                kind: "empty_fn".into(),
                detail: "vCard missing FN and N".into(),
                raw_excerpt: rec.raw_excerpt.clone(),
            })?;
        }
        ctx.persist_contact(rec)?;
        ctx.checkpoint(Checkpoint {
            cursor_kind: "vcf_index".into(),
            cursor_value: serde_json::json!({"index": i + 1}),
        })?;
        ctx.maybe_commit()?;
    }
    Ok(())
}

pub fn import_csv_file(ctx: &mut dyn ImportContext, path: &Path) -> Result<(), CoreError> {
    let text = fs::read_to_string(path)?;
    let mut lines = text.lines();
    let header = lines.next().unwrap_or("");
    let cols: Vec<String> = split_csv_line(header);
    let idx = |names: &[&str]| {
        cols.iter()
            .position(|c| names.iter().any(|n| c.eq_ignore_ascii_case(n)))
    };
    let i_first = idx(&["First Name", "First"]);
    let i_mid = idx(&["Middle Name", "Middle"]);
    let i_last = idx(&["Last Name", "Last"]);
    let i_email = idx(&[
        "E-mail 1 - Value",
        "Email 1 - Value",
        "E-mail Address",
        "Email",
    ]);
    let i_phone = idx(&["Phone 1 - Value", "Mobile Phone", "Primary Phone", "Phone"]);

    let ckpt = ctx
        .load_checkpoint("vcf_index")?
        .and_then(|c| c.cursor_value.get("index").and_then(|v| v.as_u64()))
        .unwrap_or(0);

    for (row_i, line) in lines.enumerate() {
        let index = (row_i as u64) + 1;
        if index <= ckpt {
            continue;
        }
        if line.trim().is_empty() {
            continue;
        }
        let cells = split_csv_line(line);
        let get = |i: Option<usize>| {
            i.and_then(|j| cells.get(j).cloned())
                .filter(|s| !s.is_empty())
        };
        let first = get(i_first);
        let mid = get(i_mid);
        let last = get(i_last);
        let fn_ = [first.clone(), mid, last.clone()]
            .into_iter()
            .flatten()
            .collect::<Vec<_>>()
            .join(" ");
        let fn_ = if fn_.trim().is_empty() {
            None
        } else {
            Some(fn_)
        };
        let mut channels = Vec::new();
        if let Some(e) = get(i_email) {
            if let Some(norm) = normalize_email(&e) {
                channels.push(ContactChannelIn {
                    kind: IdentityKind::Email,
                    value_raw: e,
                    value_normalized: norm,
                    pref: true,
                });
            }
        }
        if let Some(p) = get(i_phone) {
            if let Some(e164) = parse_phone(&p, None) {
                channels.push(ContactChannelIn {
                    kind: IdentityKind::Phone,
                    value_raw: p,
                    value_normalized: e164,
                    pref: true,
                });
            }
        }
        let uid = syn_uid(fn_.as_deref(), &channels);
        ctx.persist_contact(NewContact {
            uid,
            fn_,
            n_family: last,
            n_given: first,
            org: None,
            photo_bytes: None,
            channels,
            raw_excerpt: Some(line.chars().take(200).collect()),
        })?;
        ctx.checkpoint(Checkpoint {
            cursor_kind: "vcf_index".into(),
            cursor_value: serde_json::json!({"index": index}),
        })?;
        ctx.maybe_commit()?;
    }
    Ok(())
}

fn unfold(text: &str) -> String {
    let mut out = String::new();
    for line in text.lines() {
        if let Some(rest) = line.strip_prefix(' ').or_else(|| line.strip_prefix('\t')) {
            out.push_str(rest);
        } else {
            if !out.is_empty() {
                out.push('\n');
            }
            out.push_str(line);
        }
    }
    out
}

fn split_vcards(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut in_card = false;
    for line in text.lines() {
        let u = line.to_ascii_uppercase();
        if u.starts_with("BEGIN:VCARD") {
            in_card = true;
            cur.clear();
            cur.push_str(line);
            cur.push('\n');
            continue;
        }
        if !in_card {
            continue;
        }
        cur.push_str(line);
        cur.push('\n');
        if u.starts_with("END:VCARD") {
            out.push(std::mem::take(&mut cur));
            in_card = false;
        }
    }
    out
}

fn parse_vcard(card: &str) -> Result<NewContact, CoreError> {
    let mut fn_ = None;
    let mut n_family = None;
    let mut n_given = None;
    let mut org = None;
    let mut uid = None;
    let mut photo = None;
    let mut channels = Vec::new();
    for line in card.lines() {
        if line.is_empty() {
            continue;
        }
        let Some((name_params, value)) = split_prop(line) else {
            continue;
        };
        let name = name_params
            .split(';')
            .next()
            .unwrap_or("")
            .to_ascii_uppercase();
        match name.as_str() {
            "FN" => fn_ = Some(unescape_vcard(value)),
            "N" => {
                let mut it = value.split(';');
                n_family = it.next().map(unescape_vcard).filter(|s| !s.is_empty());
                n_given = it.next().map(unescape_vcard).filter(|s| !s.is_empty());
            }
            "ORG" => org = Some(unescape_vcard(value.split(';').next().unwrap_or(value))),
            "UID" => uid = Some(unescape_vcard(value)),
            "TEL" => {
                let raw = unescape_vcard(value);
                if let Some(e164) = parse_phone(&raw, None) {
                    channels.push(ContactChannelIn {
                        kind: IdentityKind::Phone,
                        value_raw: raw,
                        value_normalized: e164,
                        pref: name_params.to_ascii_uppercase().contains("PREF"),
                    });
                }
            }
            "EMAIL" => {
                let raw = unescape_vcard(value);
                if let Some(norm) = normalize_email(&raw) {
                    channels.push(ContactChannelIn {
                        kind: IdentityKind::Email,
                        value_raw: raw,
                        value_normalized: norm,
                        pref: name_params.to_ascii_uppercase().contains("PREF"),
                    });
                }
            }
            "PHOTO" => {
                let up = name_params.to_ascii_uppercase();
                if up.contains("ENCODING=B") || up.contains("ENCODING=BASE64") {
                    photo = decode_b64(value);
                }
            }
            _ => {}
        }
    }
    let uid = uid.unwrap_or_else(|| syn_uid(fn_.as_deref(), &channels));
    Ok(NewContact {
        uid,
        fn_,
        n_family,
        n_given,
        org,
        photo_bytes: photo,
        channels,
        raw_excerpt: Some(card.chars().take(8 * 1024).collect()),
    })
}

fn split_prop(line: &str) -> Option<(&str, &str)> {
    let colon = line.find(':')?;
    Some((&line[..colon], &line[colon + 1..]))
}

fn unescape_vcard(s: &str) -> String {
    strip_cf(s)
        .replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
}

fn syn_uid(fn_: Option<&str>, channels: &[ContactChannelIn]) -> String {
    let mut h = blake3::Hasher::new();
    h.update(fn_.unwrap_or("").as_bytes());
    h.update(&[0]);
    let mut ch: Vec<String> = channels
        .iter()
        .map(|c| format!("{:?}:{}", c.kind, c.value_normalized))
        .collect();
    ch.sort();
    for c in ch {
        h.update(c.as_bytes());
        h.update(&[0]);
    }
    format!("syn:{}", h.finalize().to_hex())
}

fn decode_b64(s: &str) -> Option<Vec<u8>> {
    let clean: String = s.chars().filter(|c| !c.is_whitespace()).collect();
    BASE64.decode(clean.as_bytes()).ok().or_else(|| {
        let t = clean.trim_end_matches('=');
        data_encoding::BASE64_NOPAD.decode(t.as_bytes()).ok()
    })
}

fn split_csv_line(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut in_q = false;
    let mut chars = line.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '"' if in_q && chars.peek() == Some(&'"') => {
                chars.next();
                cur.push('"');
            }
            '"' => in_q = !in_q,
            ',' if !in_q => {
                out.push(std::mem::take(&mut cur));
            }
            _ => cur.push(c),
        }
    }
    out.push(cur);
    out
}
