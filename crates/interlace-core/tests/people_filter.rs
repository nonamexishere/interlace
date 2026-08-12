//! People sidebar `/` filter (#138): match linked identity values, not only name.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//!
//! Contract for impl (client-side on the loaded list — no per-keystroke IPC):
//! - `person_list` / `PersonSummary` JSON must carry identity material so the
//!   UI can match phone last-4 / full E.164 / email local part without calling
//!   `person_identities` per keystroke.
//! - Accepted payload shapes (any one is enough):
//!   - `identity_values: string[]` — each linked `value_normalized`
//!   - `filter_haystack: string` — prejoined search text including identities
//!   - `identities: { value | value_normalized | display_name }[]`
//! - Match rule (casefold substring): `display_name`, plus `" self"` when
//!   `is_self`, plus identity material. Empty/whitespace query matches all.
//!
//! Placeholders only: Cemre Yıldız / Ada / Ali; phone +905321234567.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::people::{person_identities, person_list, PersonSummary};

static SEQ: AtomicU64 = AtomicU64::new(0);

const CEMRE_NAME: &str = "Cemre Yıldız";
const CEMRE_PHONE: &str = "+905321234567";
const ADA_NAME: &str = "Ada";
const ADA_EMAIL: &str = "contact.ada@example.com";
const ALI_NAME: &str = "Ali";
const ALI_EMAIL: &str = "ali@example.com";

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-ppl-f-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

struct FilterPlant {
    cemre_id: i64,
    ada_id: i64,
    ali_id: i64,
}

/// Cemre (WA phone, name without digits) + Ada (email local part ≠ name) + Ali.
fn plant_filter_roster(arch: &interlace_core::db::Archive) -> FilterPlant {
    let link = |arch: &interlace_core::db::Archive,
                name: &str,
                platform: &str,
                kind: &str,
                raw: &str,
                norm: &str|
     -> i64 {
        arch.conn
            .execute(
                "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                rusqlite::params![platform, kind, raw, norm, name],
            )
            .unwrap();
        let iid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
                [name],
            )
            .unwrap();
        let pid = arch.conn.last_insert_rowid();
        arch.conn
            .execute(
                "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
                 VALUES (?1, ?2, 'auto_phone', 0.99, 'system')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
        pid
    };

    let cemre_id = link(
        arch,
        CEMRE_NAME,
        "whatsapp",
        "phone",
        CEMRE_PHONE,
        CEMRE_PHONE,
    );
    let ada_id = link(arch, ADA_NAME, "gmail", "email", ADA_EMAIL, ADA_EMAIL);
    let ali_id = link(arch, ALI_NAME, "gmail", "email", ALI_EMAIL, ALI_EMAIL);

    FilterPlant {
        cemre_id,
        ada_id,
        ali_id,
    }
}

/// Identity search material exposed on the list payload (not display_name).
fn identity_material(p: &PersonSummary) -> String {
    let v = serde_json::to_value(p).expect("PersonSummary serializes");
    let mut out = String::new();
    if let Some(arr) = v.get("identity_values").and_then(|x| x.as_array()) {
        for item in arr {
            if let Some(s) = item.as_str() {
                out.push_str(s);
                out.push(' ');
            }
        }
    }
    if let Some(s) = v.get("filter_haystack").and_then(|x| x.as_str()) {
        out.push_str(s);
        out.push(' ');
    }
    if let Some(arr) = v.get("identities").and_then(|x| x.as_array()) {
        for item in arr {
            for key in ["value", "value_normalized", "display_name"] {
                if let Some(s) = item.get(key).and_then(|x| x.as_str()) {
                    out.push_str(s);
                    out.push(' ');
                }
            }
        }
    }
    out
}

/// Client-side people filter rules (#138), reading identity material from list JSON.
fn matches_people_filter(p: &PersonSummary, query: &str) -> bool {
    let q = query.trim().to_lowercase();
    if q.is_empty() {
        return true;
    }
    let mut hay = p.display_name.to_lowercase();
    if p.is_self {
        hay.push_str(" self");
    }
    hay.push(' ');
    hay.push_str(&identity_material(p).to_lowercase());
    hay.contains(&q)
}

fn find<'a>(list: &'a [PersonSummary], id: i64) -> &'a PersonSummary {
    list.iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("person {id} missing from list"))
}

#[test]
fn list_payload_carries_linked_identity_material() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);

    // Control: identity is linked and readable via person_identities.
    let cemre_ids = person_identities(&arch, planted.cemre_id).unwrap();
    assert!(
        cemre_ids.iter().any(|i| i.value == CEMRE_PHONE),
        "control: Cemre must have linked WA phone {CEMRE_PHONE}; got {cemre_ids:?}"
    );

    let list = person_list(&arch).unwrap();
    let cemre = find(&list, planted.cemre_id);
    let material = identity_material(cemre);
    assert!(
        !material.is_empty(),
        "PersonSummary list payload must expose identity material \
         (identity_values / filter_haystack / identities) so the UI can filter \
         without per-keystroke person_identities; got {}",
        serde_json::to_string(cemre).unwrap()
    );
    assert!(
        material.contains(CEMRE_PHONE) || material.contains("532"),
        "identity material must include phone {CEMRE_PHONE} (or a haystack that \
         contains it); material={material:?} payload={}",
        serde_json::to_string(cemre).unwrap()
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn filter_phone_last4_finds_person_not_by_display_name() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);
    let list = person_list(&arch).unwrap();

    let cemre = find(&list, planted.cemre_id);
    assert_eq!(cemre.display_name, CEMRE_NAME);
    assert!(
        !cemre.display_name.to_lowercase().contains("532"),
        "fixture: display_name must not already contain 532"
    );

    assert!(
        matches_people_filter(cemre, "532"),
        "typing 532 must find {CEMRE_NAME} via WA phone {CEMRE_PHONE}; payload={}",
        serde_json::to_string(cemre).unwrap()
    );
    assert!(
        !matches_people_filter(find(&list, planted.ali_id), "532"),
        "Ali must not match phone last-4 532"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn filter_full_e164_finds_person() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);
    let list = person_list(&arch).unwrap();

    let cemre = find(&list, planted.cemre_id);
    assert!(
        matches_people_filter(cemre, CEMRE_PHONE),
        "full E.164 {CEMRE_PHONE} must match; payload={}",
        serde_json::to_string(cemre).unwrap()
    );
    assert!(
        matches_people_filter(cemre, "+905321234567"),
        "full E.164 must be casefold-substring match"
    );
    assert!(
        !matches_people_filter(find(&list, planted.ada_id), CEMRE_PHONE),
        "Ada must not match Cemre's E.164"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn filter_email_local_part_finds_person() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);
    let list = person_list(&arch).unwrap();

    let ada = find(&list, planted.ada_id);
    assert_eq!(ada.display_name, ADA_NAME);
    // Local part is contact.ada — not a substring of display_name "Ada" alone
    // when we query the full local part.
    let local = ADA_EMAIL.split('@').next().unwrap();
    assert_eq!(local, "contact.ada");
    assert!(
        !ada.display_name.to_lowercase().contains(local),
        "fixture: display_name must not contain email local part {local}"
    );

    let ada_ids = person_identities(&arch, planted.ada_id).unwrap();
    assert!(
        ada_ids.iter().any(|i| i.value == ADA_EMAIL),
        "control: Ada must have linked email {ADA_EMAIL}"
    );

    assert!(
        matches_people_filter(ada, local),
        "email local part {local} must find {ADA_NAME}; payload={}",
        serde_json::to_string(ada).unwrap()
    );
    assert!(
        matches_people_filter(ada, ADA_EMAIL),
        "full email must also match; payload={}",
        serde_json::to_string(ada).unwrap()
    );
    assert!(
        !matches_people_filter(find(&list, planted.cemre_id), local),
        "Cemre must not match Ada's email local part"
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn filter_still_matches_display_name() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);
    let list = person_list(&arch).unwrap();

    assert!(matches_people_filter(
        find(&list, planted.cemre_id),
        "cemre"
    ));
    // Same Unicode letters as display_name (ASCII "YILDIZ" ≠ Turkish "Yıldız").
    assert!(matches_people_filter(
        find(&list, planted.cemre_id),
        "yıldız"
    ));
    assert!(matches_people_filter(find(&list, planted.ada_id), "ADA"));
    assert!(matches_people_filter(find(&list, planted.ali_id), "ali"));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn filter_empty_matches_all() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let planted = plant_filter_roster(&arch);
    let list = person_list(&arch).unwrap();

    for id in [planted.cemre_id, planted.ada_id, planted.ali_id] {
        assert!(
            matches_people_filter(find(&list, id), ""),
            "empty query must keep person {id}"
        );
        assert!(
            matches_people_filter(find(&list, id), "   "),
            "whitespace query must keep person {id}"
        );
    }
    let _ = std::fs::remove_dir_all(&root);
}
