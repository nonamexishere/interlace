//! WhatsApp header family, datetime parse, and locale vote.

use super::{all_packs, split_sender_body, strip_cf, LocalePack};
use crate::model::{CoreError, SentAtPrecision};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HeaderFamily {
    Ios,
    Android,
}

#[derive(Debug, Clone)]
pub struct ParsedHeader {
    pub dt_raw: String,
    pub rest: String,
    pub family: HeaderFamily,
}

#[derive(Debug, Clone)]
pub struct ParsedDt {
    pub rfc3339: String,
    pub precision: SentAtPrecision,
}

pub fn parse_header_line(line: &str) -> Option<ParsedHeader> {
    let line = strip_cf(line.trim_end());
    if let Some(inner) = line.strip_prefix('[') {
        if let Some(end) = inner.find(']') {
            let dt = inner[..end].trim().to_string();
            let rest = inner[end + 1..].trim_start().to_string();
            if dt.chars().any(|c| c.is_ascii_digit()) {
                return Some(ParsedHeader {
                    dt_raw: dt,
                    rest,
                    family: HeaderFamily::Ios,
                });
            }
        }
    }
    if let Some(idx) = line.find(" - ") {
        let dt = line[..idx].trim().to_string();
        let rest = line[idx + 3..].to_string();
        if dt.chars().any(|c| c.is_ascii_digit()) {
            return Some(ParsedHeader {
                dt_raw: dt,
                rest,
                family: HeaderFamily::Android,
            });
        }
    }
    None
}

pub fn parse_dt_with_pack(pack: &LocalePack, dt: &str) -> Option<ParsedDt> {
    for pat in &pack.date_time_patterns {
        if let Some(p) = parse_strftime(pat, dt.trim()) {
            return Some(p);
        }
    }
    None
}

fn parse_strftime(pat: &str, s: &str) -> Option<ParsedDt> {
    let mut ci = s.chars().peekable();
    let mut pi = pat.chars().peekable();
    let mut y: i32 = 0;
    let mut mo: u32 = 1;
    let mut d: u32 = 1;
    let mut h: u32 = 0;
    let mut mi: u32 = 0;
    let mut sec: u32 = 0;
    let mut precision = SentAtPrecision::Minute;
    let mut hour12 = false;
    let mut pm = false;
    while let Some(pc) = pi.next() {
        if pc != '%' {
            let sc = ci.next()?;
            if sc != pc {
                return None;
            }
            continue;
        }
        let unpadded = if pi.peek() == Some(&'-') {
            pi.next();
            true
        } else {
            false
        };
        match pi.next()? {
            'Y' => y = take_digits(&mut ci, 4, 4)? as i32,
            'y' => {
                let yy = take_digits(&mut ci, 2, 2)? as i32;
                y = 2000 + yy;
            }
            'm' => {
                mo = if unpadded {
                    take_digits(&mut ci, 1, 2)?
                } else {
                    take_digits(&mut ci, 2, 2)?
                };
            }
            'd' => {
                d = if unpadded {
                    take_digits(&mut ci, 1, 2)?
                } else {
                    take_digits(&mut ci, 2, 2)?
                };
            }
            'H' => h = take_digits(&mut ci, 2, 2)?,
            'I' => {
                hour12 = true;
                h = if unpadded {
                    take_digits(&mut ci, 1, 2)?
                } else {
                    take_digits(&mut ci, 2, 2)?
                };
            }
            'M' => mi = take_digits(&mut ci, 2, 2)?,
            'S' => {
                sec = take_digits(&mut ci, 2, 2)?;
                precision = SentAtPrecision::Second;
            }
            'p' => {
                let a = ci.next()?.to_ascii_uppercase();
                let b = ci.next()?.to_ascii_uppercase();
                match (a, b) {
                    ('P', 'M') => pm = true,
                    ('A', 'M') => pm = false,
                    _ => return None,
                }
            }
            _ => return None,
        }
    }
    if ci.next().is_some() {
        return None;
    }
    if hour12 {
        h = match (h, pm) {
            (12, false) => 0,
            (12, true) => 12,
            (n, true) => n + 12,
            (n, false) => n,
        };
    }
    if !(1..=12).contains(&mo) || !(1..=31).contains(&d) || h > 23 || mi > 59 || sec > 59 {
        return None;
    }
    Some(ParsedDt {
        rfc3339: format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{sec:02}Z"),
        precision,
    })
}

fn take_digits(
    chars: &mut std::iter::Peekable<impl Iterator<Item = char>>,
    min: usize,
    max: usize,
) -> Option<u32> {
    let mut s = String::new();
    while s.len() < max {
        match chars.peek() {
            Some(c) if c.is_ascii_digit() => {
                s.push(chars.next().unwrap());
            }
            _ => break,
        }
    }
    if s.len() < min {
        return None;
    }
    s.parse().ok()
}

pub fn vote_locale(
    lines: &[&str],
    family: Option<HeaderFamily>,
    phone_region: Option<&str>,
) -> Result<String, CoreError> {
    let packs = all_packs()?;
    let mut scores = vec![0u32; packs.len()];
    let mut sampled: Vec<ParsedHeader> = Vec::new();
    for line in lines {
        if sampled.len() >= 50 {
            break;
        }
        let Some(h) = parse_header_line(line) else {
            continue;
        };
        if let Some(f) = family {
            if h.family != f {
                continue;
            }
        }
        sampled.push(h);
    }
    if sampled.is_empty() {
        return Err(CoreError::Probe(
            "no dated WhatsApp headers in first lines; pass --locale".into(),
        ));
    }
    for h in &sampled {
        for (i, p) in packs.iter().enumerate() {
            if let Some(pos) = p
                .date_time_patterns
                .iter()
                .position(|pat| parse_strftime(pat, h.dt_raw.trim()).is_some())
            {
                // Prefer a pack's first (native) pattern so de-DE comma-time
                // beats tr-TR's secondary comma pattern and vice versa.
                scores[i] += 16u32.saturating_sub(pos as u32);
            }
        }
    }
    let max = *scores.iter().max().unwrap_or(&0);
    if max == 0 {
        return Err(CoreError::Probe(
            "no locale pack matched datetimes; pass --locale en-US|en-GB|tr-TR|de-DE|pt-BR".into(),
        ));
    }
    let tied: Vec<usize> = scores
        .iter()
        .enumerate()
        .filter(|(_, s)| **s == max)
        .map(|(i, _)| i)
        .collect();
    if tied.len() == 1 {
        return Ok(packs[tied[0]].id.clone());
    }
    // Datetime tie (typical: tr-TR vs de-DE on `d.mm.yyyy, HH:MM:SS`).
    // Score pack-unique language tokens on header rests *and* raw lines
    // (undated encryption banners).
    let mut lang = vec![0u32; packs.len()];
    for h in &sampled {
        for &i in &tied {
            lang[i] += lang_hits(&packs[i], &h.rest);
        }
    }
    for line in lines.iter().take(80) {
        let raw = strip_cf(line);
        if parse_header_line(&raw).is_some() {
            continue;
        }
        for &i in &tied {
            lang[i] += lang_hits(&packs[i], &raw);
        }
    }
    let lang_max = tied.iter().map(|&i| lang[i]).max().unwrap_or(0);
    let lang_winners: Vec<usize> = tied
        .iter()
        .copied()
        .filter(|&i| lang[i] == lang_max && lang_max > 0)
        .collect();
    if lang_winners.len() == 1 {
        return Ok(packs[lang_winners[0]].id.clone());
    }
    if let Some(want) = pack_id_for_region(phone_region) {
        if let Some(&i) = tied.iter().find(|&&i| packs[i].id == want) {
            return Ok(packs[i].id.clone());
        }
    }
    let names: Vec<&str> = tied.iter().map(|&i| packs[i].id.as_str()).collect();
    Err(CoreError::Probe(format!(
        "locale vote tied between {}; pass --locale",
        names.join(", ")
    )))
}

fn pack_id_for_region(region: Option<&str>) -> Option<&'static str> {
    match region?.trim().to_ascii_uppercase().as_str() {
        "TR" => Some("tr-TR"),
        "DE" => Some("de-DE"),
        "GB" => Some("en-GB"),
        "US" => Some("en-US"),
        "BR" => Some("pt-BR"),
        _ => None,
    }
}

/// Hits on *pack-unique* strings only. Shared English fallbacks (`You`,
/// `<Media omitted>`, `created group`, English encryption copy on tr-TR)
/// must not break a de-DE/tr-TR datetime tie toward Turkish.
fn lang_hits(pack: &LocalePack, rest: &str) -> u32 {
    let r = strip_cf(rest.trim());
    if r.is_empty() {
        return 0;
    }
    let mut s = 0u32;
    if !pack.encryption_banner_startswith.is_empty()
        && r.starts_with(&pack.encryption_banner_startswith)
    {
        s += 8;
    }
    for t in &pack.media_omitted {
        if t.eq_ignore_ascii_case("<Media omitted>") {
            continue;
        }
        if r.eq_ignore_ascii_case(t) || r.contains(t.as_str()) {
            s += 4;
            break;
        }
    }
    if let Some((sender, _)) = split_sender_body(&r) {
        if pack.you_tokens.iter().any(|t| t == &sender && t != "You") {
            s += 4;
        }
    }
    let low = r.to_lowercase();
    let skip = [
        "created group",
        "added",
        "was added",
        "changed the subject",
        "messages and calls are end-to-end encrypted",
        "<media omitted>",
        "forwarded",
    ];
    for t in pack
        .system_encryption
        .iter()
        .chain(pack.system_created_group.iter())
        .chain(pack.system_added.iter())
        .chain(pack.system_subject.iter())
        .chain(pack.forwarded_tokens.iter())
    {
        let tl = t.to_lowercase();
        if t.is_empty() || skip.iter().any(|x| tl == *x) {
            continue;
        }
        if low.contains(&tl) {
            s += 2;
            break;
        }
    }
    s
}
