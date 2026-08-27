//! Media-omitted / file-attached templates and system / title tokens.

use super::{strip_cf, LocalePack};

pub fn split_sender_body(rest: &str) -> Option<(String, String)> {
    match rest.find(": ") {
        Some(i) => {
            let sender = strip_cf(rest[..i].trim());
            let body = rest[i + 2..].to_string();
            if sender.is_empty() {
                None
            } else {
                Some((sender, body))
            }
        }
        None => None,
    }
}

pub fn is_you_token(pack: &LocalePack, sender: &str) -> bool {
    let s = strip_cf(sender.trim());
    pack.you_tokens.iter().any(|t| t == &s)
}

pub fn looks_like_group_system(pack: &LocalePack, rest: &str) -> bool {
    let r = rest.to_lowercase();
    pack.system_created_group
        .iter()
        .chain(pack.system_added.iter())
        .chain(pack.system_subject.iter())
        .any(|t| !t.is_empty() && r.contains(&t.to_lowercase()))
}

pub fn is_encryption_banner(pack: &LocalePack, rest: &str) -> bool {
    let r = strip_cf(rest.trim());
    if !pack.encryption_banner_startswith.is_empty()
        && r.starts_with(&pack.encryption_banner_startswith)
    {
        return true;
    }
    pack.system_encryption
        .iter()
        .any(|t| r.contains(t.as_str()))
}

pub fn match_media(pack: &LocalePack, body: &str) -> MediaMatch {
    let t = strip_cf(body).trim().to_string();
    for o in &pack.media_omitted {
        if t.eq_ignore_ascii_case(o) {
            return MediaMatch::Omitted;
        }
    }
    for alt in &pack.file_attached_alt {
        if let Some(name) = match_template(alt, &t) {
            if !name.is_empty() {
                return MediaMatch::File(name);
            }
        }
        if let Some(name) = find_template(alt, &t) {
            if !name.is_empty() {
                return MediaMatch::File(name);
            }
        }
    }
    if let Some(name) = match_file_attached_pattern(&pack.file_attached_pattern, &t) {
        return MediaMatch::File(name);
    }
    MediaMatch::None
}

/// `<attached: file.jpg>` anywhere in a caption + attachment line.
fn find_template(tpl: &str, body: &str) -> Option<String> {
    let (pre, post) = tpl.split_once("{filename}")?;
    if pre.is_empty() {
        return None;
    }
    let start = body.find(pre)?;
    let after = &body[start + pre.len()..];
    let end = if post.is_empty() {
        after.len()
    } else {
        after.find(post)?
    };
    let name = after[..end].trim();
    if name.is_empty() || name.contains('<') || name.contains("..") {
        return None;
    }
    Some(name.to_string())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MediaMatch {
    None,
    Omitted,
    File(String),
}

fn match_template(tpl: &str, body: &str) -> Option<String> {
    let Some((pre, post)) = tpl.split_once("{filename}") else {
        return if tpl == body {
            Some(String::new())
        } else {
            None
        };
    };
    if let Some(rest) = body.strip_prefix(pre) {
        if post.is_empty() {
            return Some(rest.to_string());
        }
        if let Some(name) = rest.strip_suffix(post) {
            return Some(name.to_string());
        }
    }
    None
}

fn match_file_attached_pattern(pat: &str, body: &str) -> Option<String> {
    let rest = pat
        .strip_prefix("^(?P<filename>.+) ")
        .and_then(|s| s.strip_suffix("$"))?;
    let lit = rest
        .replace("\\(", "(")
        .replace("\\)", ")")
        .replace("\\.", ".");
    body.strip_suffix(&lit)
        .filter(|n| !n.is_empty())
        .map(|n| n.to_string())
}

pub fn strip_forwarded(pack: &LocalePack, body: &str) -> String {
    let mut t = strip_cf(body).trim().to_string();
    loop {
        let mut changed = false;
        for tok in &pack.forwarded_tokens {
            if let Some(rest) = t.strip_prefix(tok) {
                t = rest
                    .trim_start_matches([' ', '\n', '\u{200e}', '\u{200f}'])
                    .to_string();
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    t
}

pub fn strip_title_prefix(pack: &LocalePack, title: &str) -> String {
    let t = strip_cf(title.trim());
    for p in pack
        .title_prefixes_group
        .iter()
        .chain(pack.title_prefixes_dm.iter())
    {
        if let Some(rest) = t.strip_prefix(p.as_str()) {
            return rest.trim().to_string();
        }
    }
    t
}

pub fn title_has_group_prefix(pack: &LocalePack, title: &str) -> bool {
    let t = strip_cf(title.trim());
    pack.title_prefixes_group
        .iter()
        .any(|p| !p.is_empty() && t.starts_with(p.as_str()))
}

/// True if any candidate starts with a locale DM title prefix (incl. iOS
/// `WhatsApp Chat - `).
pub fn title_looks_like_dm(pack: &LocalePack, titles: &[&str]) -> bool {
    for title in titles {
        let t = strip_cf(title.trim());
        if t.is_empty() {
            continue;
        }
        if pack
            .title_prefixes_dm
            .iter()
            .any(|p| !p.is_empty() && t.starts_with(p.as_str()))
        {
            return true;
        }
    }
    false
}
