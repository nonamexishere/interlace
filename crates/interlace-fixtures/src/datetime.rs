//! Tiny strftime subset used by locale `date_time_patterns`.

pub fn format_pattern(pat: &str, y: i32, mo: u32, d: u32, h: u32, mi: u32, s: u32) -> String {
    let mut out = String::new();
    let mut chars = pat.chars().peekable();
    while let Some(c) = chars.next() {
        if c != '%' {
            out.push(c);
            continue;
        }
        let mut unpadded = false;
        if chars.peek() == Some(&'-') {
            chars.next();
            unpadded = true;
        }
        match chars.next() {
            Some('Y') => out.push_str(&format!("{y:04}")),
            Some('y') => out.push_str(&format!("{:02}", y % 100)),
            Some('m') if unpadded => out.push_str(&format!("{mo}")),
            Some('m') => out.push_str(&format!("{mo:02}")),
            Some('d') if unpadded => out.push_str(&format!("{d}")),
            Some('d') => out.push_str(&format!("{d:02}")),
            Some('H') => out.push_str(&format!("{h:02}")),
            Some('M') => out.push_str(&format!("{mi:02}")),
            Some('S') => out.push_str(&format!("{s:02}")),
            Some('I') => {
                let h12 = match h % 12 {
                    0 => 12,
                    n => n,
                };
                if unpadded {
                    out.push_str(&format!("{h12}"));
                } else {
                    out.push_str(&format!("{h12:02}"));
                }
            }
            Some('p') => out.push_str(if h >= 12 { "PM" } else { "AM" }),
            Some(other) => {
                out.push('%');
                if unpadded {
                    out.push('-');
                }
                out.push(other);
            }
            None => out.push('%'),
        }
    }
    out
}

/// Sequential timestamps starting 2024-03-15 14:32:00, +i seconds.
pub fn stamp(i: usize) -> (i32, u32, u32, u32, u32, u32) {
    let total = 15 * 24 * 3600 + 14 * 3600 + 32 * 60 + i as u32; // day-of-march-ish
    let s = total % 60;
    let mi = (total / 60) % 60;
    let h = (total / 3600) % 24;
    let day = 15 + (total / 86400);
    (2024, 3, day.min(28), h, mi, s)
}
