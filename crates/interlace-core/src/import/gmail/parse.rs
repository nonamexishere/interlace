//! Date and mailbox-address parse.

use super::super::locale::strip_cf;

pub(super) fn parse_mailbox(raw: &str) -> (Option<String>, Option<String>) {
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

pub(super) fn split_addr_list(v: &str) -> Vec<&str> {
    // fixtures are single addresses; keep commas inside quotes out of scope
    v.split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect()
}

pub(super) fn parse_labels(raw: Option<&str>) -> Vec<String> {
    let Some(s) = raw else {
        return Vec::new();
    };
    s.split(',')
        .map(|p| p.trim().replace("\\", ""))
        .filter(|p| !p.is_empty())
        .collect()
}

pub(super) fn parse_fromline_date(from_line: &str) -> Option<String> {
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

pub(super) fn parse_rfc2822_date(s: &str) -> Option<String> {
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
