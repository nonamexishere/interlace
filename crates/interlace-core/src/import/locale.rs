//! Five shipped WhatsApp locale packs + datetime / name / phone helpers.

use crate::model::{CoreError, SentAtPrecision};

pub const PACK_IDS: &[&str] = &["en-US", "en-GB", "tr-TR", "de-DE", "pt-BR"];

#[derive(Debug, Clone)]
pub struct LocalePack {
    pub id: String,
    pub family_hints: Vec<String>,
    pub you_tokens: Vec<String>,
    pub date_time_patterns: Vec<String>,
    pub media_omitted: Vec<String>,
    pub file_attached_pattern: String,
    pub file_attached_alt: Vec<String>,
    pub forwarded_tokens: Vec<String>,
    pub title_prefixes_dm: Vec<String>,
    pub title_prefixes_group: Vec<String>,
    pub system_created_group: Vec<String>,
    pub system_added: Vec<String>,
    pub system_subject: Vec<String>,
    pub system_encryption: Vec<String>,
    pub encryption_banner_startswith: String,
}

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

pub fn load_pack(id: &str) -> Result<LocalePack, CoreError> {
    let raw = match id {
        "en-US" => include_str!("../../locale/en-US.toml"),
        "en-GB" => include_str!("../../locale/en-GB.toml"),
        "tr-TR" => include_str!("../../locale/tr-TR.toml"),
        "de-DE" => include_str!("../../locale/de-DE.toml"),
        "pt-BR" => include_str!("../../locale/pt-BR.toml"),
        other => {
            return Err(CoreError::Config(format!(
                "unknown locale pack {other}; pass --locale as one of {}",
                PACK_IDS.join(", ")
            )))
        }
    };
    parse_pack_toml(id, raw)
}

pub fn all_packs() -> Result<Vec<LocalePack>, CoreError> {
    PACK_IDS.iter().map(|id| load_pack(id)).collect()
}

fn parse_pack_toml(id: &str, raw: &str) -> Result<LocalePack, CoreError> {
    let v: toml::Value =
        toml::from_str(raw).map_err(|e| CoreError::Config(format!("locale {id}: {e}")))?;
    let table = v
        .as_table()
        .ok_or_else(|| CoreError::Config(format!("locale {id}: not a table")))?;
    Ok(LocalePack {
        id: req_str(table, "id")?,
        family_hints: req_str_vec(table, "family_hints")?,
        you_tokens: req_str_vec(table, "you_tokens")?,
        date_time_patterns: req_str_vec(table, "date_time_patterns")?,
        media_omitted: req_str_vec(table, "media_omitted")?,
        file_attached_pattern: req_str(table, "file_attached_pattern")?,
        file_attached_alt: req_str_vec(table, "file_attached_alt")?,
        forwarded_tokens: req_str_vec(table, "forwarded_tokens")?,
        title_prefixes_dm: req_str_vec(table, "title_prefixes_dm")?,
        title_prefixes_group: req_str_vec(table, "title_prefixes_group")?,
        system_created_group: req_str_vec(table, "system_created_group")?,
        system_added: req_str_vec(table, "system_added")?,
        system_subject: req_str_vec(table, "system_subject")?,
        system_encryption: req_str_vec(table, "system_encryption")?,
        encryption_banner_startswith: req_str(table, "encryption_banner_startswith")?,
    })
}

fn req_str(t: &toml::map::Map<String, toml::Value>, k: &str) -> Result<String, CoreError> {
    t.get(k)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| CoreError::Config(format!("locale missing string {k}")))
}

fn req_str_vec(t: &toml::map::Map<String, toml::Value>, k: &str) -> Result<Vec<String>, CoreError> {
    let arr = t
        .get(k)
        .and_then(|v| v.as_array())
        .ok_or_else(|| CoreError::Config(format!("locale missing array {k}")))?;
    Ok(arr
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.to_string()))
        .collect())
}

pub fn strip_cf(s: &str) -> String {
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

/// DESIGN name_fold (identity keying). Auto-merge never uses this.
pub fn name_fold(s: &str) -> Vec<String> {
    let t = strip_cf(s)
        .replace('İ', "i")
        .replace('I', "ı")
        .to_lowercase();
    let drop = [
        "tr",
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "sayın",
        "sn",
        "bey",
        "hanım",
        "hanim",
        "av",
        "mühendis",
        "muhendis",
    ];
    let mut tokens: Vec<String> = t
        .split_whitespace()
        .map(|tok| {
            tok.trim_matches(|c: char| c.is_ascii_punctuation() && c != '-')
                .to_string()
        })
        .filter(|x| x.chars().count() > 1 && !drop.contains(&x.as_str()))
        .map(|x| match x.as_str() {
            "mhmt" | "mehmed" => "mehmet".into(),
            "ahmt" => "ahmet".into(),
            "mstf" => "mustafa".into(),
            _ => x,
        })
        .collect();
    tokens.sort();
    tokens
}

pub fn name_fold_join(s: &str) -> String {
    name_fold(s).join(" ")
}

/// D25: Gmail/googlemail fold +tag and dots; other domains exact lowercase.
pub fn normalize_email(raw: &str) -> Option<String> {
    let t = strip_cf(raw).trim().to_lowercase();
    let (local, domain) = t.split_once('@')?;
    if local.is_empty() || domain.is_empty() || !domain.contains('.') {
        return None;
    }
    let domain = if domain == "googlemail.com" {
        "gmail.com"
    } else {
        domain
    };
    if domain == "gmail.com" {
        let local = local.split('+').next().unwrap_or(local).replace('.', "");
        if local.is_empty() {
            return None;
        }
        Some(format!("{local}@{domain}"))
    } else {
        Some(format!("{local}@{domain}"))
    }
}

/// E.164 with optional `default_phone_region`. None if unparseable (D20).
pub fn parse_phone(raw: &str, region: Option<&str>) -> Option<String> {
    let cleaned = strip_cf(raw);
    let digits: String = cleaned.chars().filter(|c| c.is_ascii_digit()).collect();
    if digits.len() < 8 || digits.len() > 15 {
        return None;
    }
    let has_plus = cleaned.trim().starts_with('+');
    if has_plus {
        return Some(format!("+{digits}"));
    }
    match region.map(|r| r.to_ascii_uppercase()) {
        Some(ref r) if r == "TR" && digits.len() == 10 && digits.starts_with('5') => {
            Some(format!("+90{digits}"))
        }
        Some(ref r) if r == "TR" && digits.len() == 12 && digits.starts_with("90") => {
            Some(format!("+{digits}"))
        }
        Some(ref r) if (r == "US" || r == "CA") && digits.len() == 10 => {
            Some(format!("+1{digits}"))
        }
        Some(ref r) if r == "DE" && (10..=13).contains(&digits.len()) => {
            Some(format!("+49{digits}"))
        }
        Some(ref r) if r == "GB" && (10..=11).contains(&digits.len()) => {
            Some(format!("+44{digits}"))
        }
        Some(ref r) if r == "BR" && (10..=11).contains(&digits.len()) => {
            Some(format!("+55{digits}"))
        }
        _ => {
            // Bare international without plus if 11–15 digits starting with country-ish.
            if digits.len() >= 11 {
                Some(format!("+{digits}"))
            } else {
                None
            }
        }
    }
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

pub fn vote_locale(lines: &[&str], family: Option<HeaderFamily>) -> Result<String, CoreError> {
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
    // Score pack-unique language tokens on the same sample.
    let mut lang = vec![0u32; packs.len()];
    for h in &sampled {
        for &i in &tied {
            lang[i] += lang_hits(&packs[i], &h.rest);
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
    let names: Vec<&str> = tied.iter().map(|&i| packs[i].id.as_str()).collect();
    Err(CoreError::Probe(format!(
        "locale vote tied between {}; pass --locale",
        names.join(", ")
    )))
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
    }
    if let Some(name) = match_file_attached_pattern(&pack.file_attached_pattern, &t) {
        return MediaMatch::File(name);
    }
    MediaMatch::None
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unpadded_day_matches_tr_and_de() {
        let tr = load_pack("tr-TR").unwrap();
        let de = load_pack("de-DE").unwrap();
        for dt in [
            "3.08.2025, 02:31:13",
            "26.03.2025, 10:24:07",
            "7.04.2025, 23:21:09",
        ] {
            assert!(parse_dt_with_pack(&tr, dt).is_some(), "tr-TR {dt}");
            assert!(parse_dt_with_pack(&de, dt).is_some(), "de-DE {dt}");
        }
    }

    #[test]
    fn vote_tr_banner_not_de_on_padded_comma() {
        let lines = [
            "[26.03.2025, 10:24:07] Mesajlar ve aramalar uçtan uca şifrelidir",
            "[26.03.2025, 10:24:15] Mustafa: merhaba",
            "[26.03.2025, 10:24:20] Alice: hi",
        ];
        let refs: Vec<&str> = lines.iter().copied().collect();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios)).unwrap(),
            "tr-TR"
        );
    }

    #[test]
    fn vote_de_banner_not_tr_on_padded_comma() {
        let lines = [
            "[26.03.2025, 10:24:07] Nachrichten und Anrufe sind Ende-zu-Ende-verschlüsselt",
            "[26.03.2025, 10:24:15] Mustafa: hallo",
            "[26.03.2025, 10:24:20] Alice: hi",
        ];
        let refs: Vec<&str> = lines.iter().copied().collect();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios)).unwrap(),
            "de-DE"
        );
    }

    #[test]
    fn vote_mixed_unpadded_tr_banner() {
        let lines = [
            "[3.08.2025, 02:31:13] Mesajlar ve aramalar uçtan uca şifrelidir",
            "[26.03.2025, 10:24:07] Mustafa: a",
            "[7.04.2025, 23:21:09] Alice: b",
        ];
        let refs: Vec<&str> = lines.iter().copied().collect();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios)).unwrap(),
            "tr-TR"
        );
    }
}
