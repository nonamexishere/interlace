//! Replaced-phone review. Shared chat, date overlap, and a quiet old number.
//! Display name, photo, and username are not evidence.

use std::collections::HashMap;

use crate::db::Archive;
use crate::model::{CoreError, ImportStats};

use super::helpers::reason_is_phone_replaced;

struct PhoneActivity {
    identity_id: i64,
    person_id: i64,
    value: String,
    first_ord: i64,
    last_ord: i64,
    last_at: String,
    convs: Vec<i64>,
}

struct PhoneHit {
    newer_id: i64,
    newer_value: String,
    older_id: i64,
    older_person: i64,
    older_value: String,
    conv: i64,
    gap_days: i64,
}

pub(super) fn enqueue_phone_replaced(
    archive: &Archive,
    stats: &mut ImportStats,
) -> Result<(), CoreError> {
    let phones = phone_activities(archive)?;
    let mut by_newer: HashMap<i64, Vec<PhoneHit>> = HashMap::new();
    for i in 0..phones.len() {
        for j in (i + 1)..phones.len() {
            if phones[i].person_id == phones[j].person_id {
                continue;
            }
            let Some(hit) = phone_hit(&phones[i], &phones[j]) else {
                continue;
            };
            by_newer.entry(hit.newer_id).or_default().push(hit);
        }
    }
    let mut newer_ids: Vec<i64> = by_newer.keys().copied().collect();
    newer_ids.sort_unstable();
    for newer_id in newer_ids {
        let Some(hits) = by_newer.get(&newer_id) else {
            continue;
        };
        // Two older numbers that both fit this newer number: queue nothing.
        if hits.len() != 1 {
            continue;
        }
        insert_phone_review(archive, stats, &hits[0])?;
    }
    Ok(())
}

fn phone_hit(a: &PhoneActivity, b: &PhoneActivity) -> Option<PhoneHit> {
    let (older, newer) = if a.last_at < b.last_at {
        (a, b)
    } else if b.last_at < a.last_at {
        (b, a)
    } else {
        return None;
    };
    if newer.last_at <= older.last_at {
        return None;
    }
    let conv = shared_conv(&older.convs, &newer.convs)?;
    if newer.first_ord > older.last_ord + 30 {
        return None;
    }
    if older.last_ord > newer.first_ord + 7 {
        return None;
    }
    Some(PhoneHit {
        newer_id: newer.identity_id,
        newer_value: newer.value.clone(),
        older_id: older.identity_id,
        older_person: older.person_id,
        older_value: older.value.clone(),
        conv,
        gap_days: newer.first_ord - older.last_ord,
    })
}

fn shared_conv(a: &[i64], b: &[i64]) -> Option<i64> {
    a.iter().copied().filter(|id| b.contains(id)).min()
}

fn phone_activities(archive: &Archive) -> Result<Vec<PhoneActivity>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT i.id, p.id, i.value_normalized, m.conversation_id, m.sent_at
         FROM identities i
         JOIN person_identities pi ON pi.identity_id = i.id
         JOIN persons p ON p.id = pi.person_id
           AND p.tombstoned_at IS NULL AND p.is_self = 0
         JOIN messages m ON m.sender_identity_id = i.id
         WHERE i.kind = 'phone'
           AND m.kind != 'system'
           AND m.sent_at IS NOT NULL",
    )?;
    let rows = stmt.query_map([], |r| {
        Ok((
            r.get::<_, i64>(0)?,
            r.get::<_, i64>(1)?,
            r.get::<_, String>(2)?,
            r.get::<_, i64>(3)?,
            r.get::<_, String>(4)?,
        ))
    })?;
    let mut acc: HashMap<i64, PhoneActivity> = HashMap::new();
    for row in rows {
        let (iid, pid, value, conv, sent_at) = row?;
        let Some(ord) = utc_date_ord(&sent_at) else {
            continue;
        };
        let entry = acc.entry(iid).or_insert_with(|| PhoneActivity {
            identity_id: iid,
            person_id: pid,
            value,
            first_ord: ord,
            last_ord: ord,
            last_at: sent_at.clone(),
            convs: Vec::new(),
        });
        if ord < entry.first_ord {
            entry.first_ord = ord;
        }
        if sent_at > entry.last_at {
            entry.last_at = sent_at;
            entry.last_ord = ord;
        }
        if !entry.convs.contains(&conv) {
            entry.convs.push(conv);
        }
    }
    let mut phones: Vec<PhoneActivity> = acc.into_values().collect();
    phones.sort_by_key(|p| p.identity_id);
    Ok(phones)
}

fn insert_phone_review(
    archive: &Archive,
    stats: &mut ImportStats,
    hit: &PhoneHit,
) -> Result<(), CoreError> {
    let open_or_rejected: i64 = archive.conn.query_row(
        "SELECT COUNT(*) FROM merge_review_queue
         WHERE left_identity_id = ?1 AND right_identity_id = ?2
           AND status IN ('open', 'rejected')",
        rusqlite::params![hit.newer_id, hit.older_id],
        |r| r.get(0),
    )?;
    if open_or_rejected > 0 {
        return Ok(());
    }
    let reason = serde_json::json!({
        "phone_replaced": true,
        "shared": true,
        "shared_conversation_id": hit.conv,
        "overlap": true,
        "gap_days": hit.gap_days,
        "quiet": true,
        "old_phone": hit.older_value,
        "new_phone": hit.newer_value,
    })
    .to_string();
    debug_assert!(reason_is_phone_replaced(&reason));
    let inserted = archive.conn.execute(
        "INSERT INTO merge_review_queue(
            status, left_identity_id, right_person_id, right_identity_id,
            suggested_score, reason_summary
         ) VALUES ('open', ?1, ?2, ?3, 0.60, ?4)",
        rusqlite::params![hit.newer_id, hit.older_person, hit.older_id, reason],
    );
    match inserted {
        Ok(0) => Ok(()),
        Ok(_) => {
            stats.review_enqueued += 1;
            Ok(())
        }
        Err(e) if e.to_string().contains("UNIQUE") => Ok(()),
        Err(e) => Err(e.into()),
    }
}

fn utc_date_ord(sent_at: &str) -> Option<i64> {
    let b = sent_at.as_bytes();
    if b.len() < 10 || b[4] != b'-' || b[7] != b'-' {
        return None;
    }
    let y: i32 = std::str::from_utf8(&b[0..4]).ok()?.parse().ok()?;
    let m: u32 = std::str::from_utf8(&b[5..7]).ok()?.parse().ok()?;
    let d: u32 = std::str::from_utf8(&b[8..10]).ok()?.parse().ok()?;
    if !(1..=12).contains(&m) || d == 0 || d > 31 {
        return None;
    }
    Some(civil_ord(y, m, d))
}

fn civil_ord(y: i32, m: u32, d: u32) -> i64 {
    let mdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut days = (y as i64 - 1) * 365;
    days += i64::from((y - 1) / 4 - (y - 1) / 100 + (y - 1) / 400);
    for month in 1..m {
        days += i64::from(mdays[month as usize]);
        if month == 2 && is_leap(y) {
            days += 1;
        }
    }
    days + i64::from(d)
}

fn is_leap(y: i32) -> bool {
    y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)
}
