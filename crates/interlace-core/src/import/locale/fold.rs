//! Name fold, email fold, and phone parse.

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
