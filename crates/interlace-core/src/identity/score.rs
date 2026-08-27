//! DESIGN name_score. Never used as an auto-merge key.

use crate::import::name_fold;

pub(super) fn name_compat_ratio(a: &str, b: &str) -> f64 {
    let fa = name_fold(a);
    let fb = name_fold(b);
    if fa == fb && !fa.is_empty() {
        return 1.0;
    }
    let da: Vec<String> = fa.iter().map(|t| ascii_fold(t)).collect();
    let db: Vec<String> = fb.iter().map(|t| ascii_fold(t)).collect();
    if da == db && !da.is_empty() {
        return 0.90;
    }
    if da.is_empty() || db.is_empty() {
        return 0.0;
    }
    let set_a: std::collections::HashSet<_> = da.iter().collect();
    let set_b: std::collections::HashSet<_> = db.iter().collect();
    let inter = set_a.intersection(&set_b).count() as f64;
    let uni = set_a.union(&set_b).count() as f64;
    if uni == 0.0 {
        0.0
    } else {
        inter / uni
    }
}

/// DESIGN name_score. Never used as an auto-merge key.
pub fn name_score(a: &str, b: &str) -> f64 {
    let ta = name_fold(a);
    let tb = name_fold(b);
    if ta == tb && !ta.is_empty() {
        return 0.70;
    }
    let primary = score_tokens(&ta, &tb);
    let da: Vec<String> = ta.iter().map(|t| ascii_fold(t)).collect();
    let db: Vec<String> = tb.iter().map(|t| ascii_fold(t)).collect();
    let secondary = score_tokens(&da, &db).min(0.68);
    primary.max(secondary)
}

fn score_tokens(ta: &[String], tb: &[String]) -> f64 {
    if ta.is_empty() || tb.is_empty() {
        return 0.0;
    }
    if ta == tb {
        return 0.70;
    }
    let sa: std::collections::HashSet<_> = ta.iter().collect();
    let sb: std::collections::HashSet<_> = tb.iter().collect();
    if sa.is_subset(&sb) || sb.is_subset(&sa) {
        let min_len = ta.len().min(tb.len());
        let max_len = ta.len().max(tb.len());
        if min_len == 1 && max_len >= 2 {
            return 0.45;
        }
        return 0.60;
    }
    // Align tokens. Whole-string JW on the joined name was scoring ~0.41 for
    // two unrelated 2-token names (no shared given name or surname).
    token_align_score(ta, tb)
}

/// Strong pair: exact, or JW ≥ 0.92 with both tokens ≥ 4 letters (typo).
const STRONG_JW: f64 = 0.92;
const MIN_JW_CHARS: usize = 4;

fn token_sim(a: &str, b: &str) -> f64 {
    if a == b {
        1.0
    } else {
        jaro_winkler(a, b)
    }
}

fn is_strong_pair(a: &str, b: &str, sim: f64) -> bool {
    if a == b {
        return true;
    }
    let na = a.chars().count();
    let nb = b.chars().count();
    sim >= STRONG_JW && na >= MIN_JW_CHARS && nb >= MIN_JW_CHARS
}

fn token_align_score(ta: &[String], tb: &[String]) -> f64 {
    let (short, long) = if ta.len() <= tb.len() {
        (ta, tb)
    } else {
        (tb, ta)
    };
    let mut used = vec![false; long.len()];
    let mut strong = 0usize;
    let mut strong_sim_sum = 0.0;
    for s in short {
        let mut best: Option<(usize, f64)> = None;
        for (i, l) in long.iter().enumerate() {
            if used[i] {
                continue;
            }
            let sim = token_sim(s, l);
            if best.map(|(_, b)| sim > b).unwrap_or(true) {
                best = Some((i, sim));
            }
        }
        let Some((i, sim)) = best else {
            continue;
        };
        if is_strong_pair(s, &long[i], sim) {
            used[i] = true;
            strong += 1;
            strong_sim_sum += sim;
        }
    }
    if strong == 0 {
        return 0.0;
    }
    let unmatched_short = short.len() - strong;
    let unmatched_long = used.iter().filter(|u| !*u).count();
    // Shared surname, different given names (N10 John Smith / James Smith).
    if unmatched_short > 0 && unmatched_long > 0 {
        return 0.0;
    }
    if unmatched_short == 0 && unmatched_long == 0 {
        let mean = strong_sim_sum / strong as f64;
        return (mean * 0.70).clamp(0.60, 0.68);
    }
    // Fuzzy subset: every short token has a strong partner.
    if unmatched_short == 0 && unmatched_long > 0 {
        if short.len() == 1 && long.len() >= 2 {
            return 0.45;
        }
        return 0.60;
    }
    0.0
}

fn ascii_fold(s: &str) -> String {
    s.replace('ı', "i")
        .replace('ş', "s")
        .replace('ç', "c")
        .replace('ğ', "g")
        .replace('ö', "o")
        .replace('ü', "u")
        .replace('â', "a")
}

fn jaro_winkler(s1: &str, s2: &str) -> f64 {
    let a: Vec<char> = s1.chars().collect();
    let b: Vec<char> = s2.chars().collect();
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    if a == b {
        return 1.0;
    }
    let match_dist = (a.len().max(b.len()) / 2).saturating_sub(1);
    let mut a_match = vec![false; a.len()];
    let mut b_match = vec![false; b.len()];
    let mut matches = 0usize;
    for (i, ca) in a.iter().enumerate() {
        let lo = i.saturating_sub(match_dist);
        let hi = (i + match_dist + 1).min(b.len());
        for (j, cb) in b.iter().enumerate().take(hi).skip(lo) {
            if b_match[j] || ca != cb {
                continue;
            }
            a_match[i] = true;
            b_match[j] = true;
            matches += 1;
            break;
        }
    }
    if matches == 0 {
        return 0.0;
    }
    let mut k = 0usize;
    let mut trans = 0usize;
    for (i, m) in a_match.iter().enumerate() {
        if !m {
            continue;
        }
        while !b_match[k] {
            k += 1;
        }
        if a[i] != b[k] {
            trans += 1;
        }
        k += 1;
    }
    let m = matches as f64;
    let jaro = (m / a.len() as f64 + m / b.len() as f64 + (m - (trans as f64) / 2.0) / m) / 3.0;
    let mut prefix = 0usize;
    for (ca, cb) in a.iter().zip(b.iter()).take(4) {
        if ca == cb {
            prefix += 1;
        } else {
            break;
        }
    }
    jaro + prefix as f64 * 0.1 * (1.0 - jaro)
}

#[cfg(test)]
mod name_score_tests {
    use super::name_score;

    fn band(got: f64, lo: f64, hi: f64) {
        assert!(
            got + 1e-9 >= lo && got <= hi + 1e-9,
            "score {got} not in [{lo}, {hi}]"
        );
    }

    #[test]
    fn n_table_exact_and_subset() {
        assert!((name_score("Ahmet Yılmaz", "Yılmaz Ahmet") - 0.70).abs() < 1e-9);
        band(name_score("AHMET YILMAZ", "ahmet yilmaz"), 0.60, 0.68);
        assert!((name_score("İstanbul", "istanbul") - 0.70).abs() < 1e-9);
        assert!((name_score("ISLAK", "ıslak") - 0.70).abs() < 1e-9);
        assert!((name_score("Mehmet Ali", "Mhmt Ali") - 0.70).abs() < 1e-9);
        assert!((name_score("Sayın Dr. Ahmet Yılmaz", "Ahmet Yılmaz") - 0.70).abs() < 1e-9);
        assert!((name_score("\u{200e}Ahmet Yılmaz", "Ahmet Yılmaz") - 0.70).abs() < 1e-9);
        assert!((name_score("Ali", "Ali Veli Yılmaz") - 0.45).abs() < 1e-9);
        band(name_score("Ayşe", "Ayse"), 0.60, 0.68);
    }

    #[test]
    fn unrelated_two_token_names_below_review_floor() {
        // Concat-JW * 0.70 is ~0.41 on this pair; token align must not review.
        assert!(
            name_score("Cemre Yıldız", "Berk Özdemir") < 0.40,
            "got {}",
            name_score("Cemre Yıldız", "Berk Özdemir")
        );
        assert!(name_score("Can Yılmaz", "Cem Yılmaz") < 0.40);
        assert!(name_score("John Smith", "James Smith") < 0.40);
    }

    #[test]
    fn one_letter_surname_typo_still_reviews() {
        assert!(name_score("Ahmet Yılmaz", "Ahmet Yilmas") >= 0.40);
        assert!(name_score("Ada Yıldız", "Ada Yildiz") >= 0.40);
    }
}
