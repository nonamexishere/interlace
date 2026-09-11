//! #342 review census: count-only measure; names never auto-merge.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//! Matrix IDs (gate grep):
//!
//! Public `review_census(&Archive) -> Result<ReviewCensus, CoreError>`.
//! Integer keys only. Ada exact-fold → cluster 1, open 1, never-enqueued 0,
//! 2 live persons, 0 auto-merge. Ada vs Cemre Yıldız → exact-fold 0,
//! pairs/best under 0.40 ≥ 1. Rejected Ada → rejected ≥ 1, still 2 live.
//! Measure does not insert `merge_review_queue` or change `person_identities`.
//! `serde_json` of the report must not contain `Ada` or `Cemre`.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::{name_fold_join, normalize_email};
use interlace_core::{resolve_run, review_census, review_resolve, ReviewCensus};

static SEQ: AtomicU64 = AtomicU64::new(0);

const CENSUS_KEYS: &[&str] = &[
    "identities",
    "persons_live",
    "review_open",
    "name_only_wa_exact_fold_contacts",
    "name_only_wa_no_phone_email",
    "name_score_pairs_under_040",
    "name_score_best_under_040",
    "exact_fold_clusters_rejected",
    "exact_fold_clusters_never_enqueued",
];

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-rc-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn ensure_source(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('contacts_vcf', 't', '/t.vcf')",
            [],
        )
        .ok();
    arch.conn
        .query_row("SELECT id FROM sources LIMIT 1", [], |r| r.get(0))
        .unwrap()
}

fn insert_ident(
    arch: &interlace_core::db::Archive,
    platform: &str,
    kind: &str,
    raw: &str,
    norm: &str,
    display: Option<&str>,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![platform, kind, raw, norm, display],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn persist_card(
    arch: &mut interlace_core::db::Archive,
    uid: &str,
    fn_: &str,
    phone: Option<&str>,
    email: Option<&str>,
) {
    let source = ensure_source(arch);
    arch.conn
        .execute(
            "INSERT INTO contacts_raw(source_id, uid, fn) VALUES (?1, ?2, ?3)",
            rusqlite::params![source, uid, fn_],
        )
        .unwrap();
    let cid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [fn_],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    let mut chans: Vec<(String, String, String)> = Vec::new();
    if let Some(p) = phone {
        chans.push(("phone".into(), p.into(), p.into()));
    }
    if let Some(e) = email {
        let norm = normalize_email(e).unwrap_or_else(|| e.to_lowercase());
        chans.push(("email".into(), e.into(), norm));
    }
    for (kind, raw, norm) in chans {
        arch.conn
            .execute(
                "INSERT OR IGNORE INTO identities(platform, kind, value_raw, value_normalized, display_name)
                 VALUES ('contacts', ?1, ?2, ?3, ?4)",
                rusqlite::params![&kind, &raw, &norm, fn_],
            )
            .unwrap();
        let iid: i64 = arch
            .conn
            .query_row(
                "SELECT id FROM identities WHERE platform='contacts' AND kind=?1 AND value_normalized=?2",
                rusqlite::params![&kind, &norm],
                |r| r.get(0),
            )
            .unwrap();
        arch.conn
            .execute(
                "INSERT INTO contact_channels(contact_id, kind, value_raw, value_normalized, pref, identity_id)
                 VALUES (?1, ?2, ?3, ?4, 0, ?5)",
                rusqlite::params![cid, &kind, &raw, &norm, iid],
            )
            .unwrap();
        arch.conn
            .execute(
                "INSERT OR IGNORE INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
                 VALUES (?1, ?2, 'takeout_vcard', 1.0, 'system')",
                rusqlite::params![pid, iid],
            )
            .unwrap();
    }
}

/// Already-linked WhatsApp `display_name` person (no parser).
fn persist_wa_display_person(
    arch: &interlace_core::db::Archive,
    display: &str,
    norm: &str,
) -> (i64, i64) {
    let iid = insert_ident(
        arch,
        "whatsapp",
        "display_name",
        display,
        norm,
        Some(display),
    );
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [display],
        )
        .unwrap();
    let pid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![pid, iid],
        )
        .unwrap();
    (pid, iid)
}

fn live_non_self(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND is_self = 0",
    )
}

fn open_reviews(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'",
    )
}

fn open_review_id(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM merge_review_queue WHERE status='open' ORDER BY id LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap()
}

fn person_identity_rows(arch: &interlace_core::db::Archive) -> Vec<(i64, i64, String)> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT person_id, identity_id, link_reason
             FROM person_identities
             ORDER BY person_id, identity_id",
        )
        .unwrap();
    stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn queue_rows(arch: &interlace_core::db::Archive) -> Vec<(i64, String)> {
    let mut stmt = arch
        .conn
        .prepare("SELECT id, status FROM merge_review_queue ORDER BY id")
        .unwrap();
    stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn sql_identities(arch: &interlace_core::db::Archive) -> i64 {
    count(arch, "SELECT COUNT(*) FROM identities")
}

fn sql_persons_live(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
    )
}

fn json_int(v: &serde_json::Value, key: &str) -> i64 {
    if let Some(n) = v.get(key).and_then(|x| x.as_i64()) {
        return n;
    }
    if let Some(obj) = v.as_object() {
        for child in obj.values() {
            if child.is_object() {
                if let Some(n) = child.get(key).and_then(|x| x.as_i64()) {
                    return n;
                }
            }
        }
    }
    panic!("census JSON missing integer key {key}: {v}");
}

fn assert_census_json_integers_no_names(census: &ReviewCensus) {
    let v = serde_json::to_value(census).unwrap();
    let dumped = serde_json::to_string(census).unwrap();
    assert!(
        !dumped.contains("Ada"),
        "census JSON must not contain planted Ada: {dumped}"
    );
    assert!(
        !dumped.contains("Cemre"),
        "census JSON must not contain planted Cemre Yıldız: {dumped}"
    );
    for key in CENSUS_KEYS {
        let _ = json_int(&v, key);
    }
    walk_integers_only(&v);
}

fn walk_integers_only(node: &serde_json::Value) {
    match node {
        serde_json::Value::Object(map) => {
            for child in map.values() {
                walk_integers_only(child);
            }
        }
        serde_json::Value::Array(arr) => {
            for child in arr {
                walk_integers_only(child);
            }
        }
        serde_json::Value::Number(n) => {
            assert!(
                n.is_i64() || n.as_u64().is_some(),
                "census values must be integers: {n}"
            );
        }
        serde_json::Value::Null => {}
        other => panic!("census JSON must be integers only, got {other}"),
    }
}

fn assert_context_matches_sql(arch: &interlace_core::db::Archive, census: &ReviewCensus) {
    assert_eq!(census.identities, sql_identities(arch));
    assert_eq!(census.persons_live, sql_persons_live(arch));
    assert_eq!(census.review_open, open_reviews(arch));
    let st = arch.status().unwrap();
    assert_eq!(census.identities, st["identities"].as_i64().unwrap());
    assert_eq!(census.persons_live, st["persons_live"].as_i64().unwrap());
    assert_eq!(census.review_open, st["review_open"].as_i64().unwrap());
    for key in [
        "name_only_wa_exact_fold_contacts",
        "name_only_wa_no_phone_email",
        "name_score_pairs_under_040",
        "name_score_best_under_040",
        "exact_fold_clusters_rejected",
        "exact_fold_clusters_never_enqueued",
    ] {
        assert!(
            st.get(key).is_none(),
            "Archive::status must not grow census key {key}"
        );
    }
}

#[test]
fn review_census_ada_exact_fold_one_open_never_enqueued_zero() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(stats.auto_person_merges, 0, "never auto-merge on name");
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(open_reviews(&arch), 1);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 2);
    assert_eq!(census.review_open, 1);
    assert_eq!(census.name_only_wa_exact_fold_contacts, 1);
    assert_eq!(census.name_only_wa_no_phone_email, 1);
    assert_eq!(census.name_score_pairs_under_040, 0);
    assert_eq!(census.name_score_best_under_040, 0);
    assert_eq!(census.exact_fold_clusters_rejected, 0);
    assert_eq!(census.exact_fold_clusters_never_enqueued, 0);
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_ada_vs_cemre_yildiz_under_040() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110200"), None);
    persist_wa_display_person(&arch, "Cemre Yıldız", &name_fold_join("Cemre Yıldız"));
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(stats.auto_person_merges, 0);
    assert_eq!(stats.review_enqueued, 0);
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(open_reviews(&arch), 0);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 2);
    assert_eq!(census.review_open, 0);
    assert_eq!(census.name_only_wa_exact_fold_contacts, 0);
    assert_eq!(census.name_only_wa_no_phone_email, 1);
    assert!(
        census.name_score_pairs_under_040 >= 1,
        "Ada vs Cemre Yıldız must count as a name_score pair under 0.40, got {}",
        census.name_score_pairs_under_040
    );
    assert!(
        census.name_score_best_under_040 >= 1,
        "Cemre Yıldız best Contacts match must be under 0.40, got {}",
        census.name_score_best_under_040
    );
    assert_eq!(census.exact_fold_clusters_rejected, 0);
    assert_eq!(census.exact_fold_clusters_never_enqueued, 0);
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_rejected_ada_still_two_live() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    resolve_run(&mut arch, 0).unwrap();
    let rid = open_review_id(&arch);
    review_resolve(&mut arch, rid, false).unwrap();
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(open_reviews(&arch), 0);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 2);
    assert_eq!(census.review_open, 0);
    assert!(
        census.exact_fold_clusters_rejected >= 1,
        "rejected Ada exact-fold cluster must count, got {}",
        census.exact_fold_clusters_rejected
    );
    assert_eq!(census.exact_fold_clusters_never_enqueued, 0);
    assert_eq!(census.name_only_wa_exact_fold_contacts, 1);
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_never_enqueued_without_resolve() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(open_reviews(&arch), 0);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM merge_review_queue"), 0);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 2);
    assert_eq!(census.review_open, 0);
    assert_eq!(census.name_only_wa_exact_fold_contacts, 1);
    assert!(
        census.exact_fold_clusters_never_enqueued >= 1,
        "live Ada exact-fold with no queue row must count as never-enqueued, got {}",
        census.exact_fold_clusters_never_enqueued
    );
    assert_eq!(census.exact_fold_clusters_rejected, 0);
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_leftover_wa_beside_merged_survivor_is_never_enqueued() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    let survivor: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM persons WHERE display_name = 'Ada' AND tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let survivor_wa = insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ada",
        &name_fold_join("Ada"),
        Some("Ada"),
    );
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![survivor, survivor_wa],
        )
        .unwrap();
    let leftover_iid = insert_ident(
        &arch,
        "whatsapp",
        "display_name",
        "Ada leftover",
        "ada leftover",
        Some("Ada"),
    );
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES ('Ada', 0)",
            [],
        )
        .unwrap();
    let leftover_pid = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![leftover_pid, leftover_iid],
        )
        .unwrap();
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM merge_review_queue"), 0);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 2);
    assert_eq!(census.review_open, 0);
    assert!(
        census.name_only_wa_exact_fold_contacts >= 1,
        "leftover WA Ada vs Contacts Ada is still an exact-fold person hit, got {}",
        census.name_only_wa_exact_fold_contacts
    );
    assert!(
        census.exact_fold_clusters_never_enqueued >= 1,
        "leftover same-fold WA beside a merged survivor must count as never-enqueued, got {}",
        census.exact_fold_clusters_never_enqueued
    );
    assert_eq!(census.exact_fold_clusters_rejected, 0);
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_accepted_cluster_not_resurrected() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    resolve_run(&mut arch, 0).unwrap();
    let rid = open_review_id(&arch);
    review_resolve(&mut arch, rid, true).unwrap();
    assert_eq!(live_non_self(&arch), 1, "Accept folds the Ada cluster");
    assert_eq!(open_reviews(&arch), 0);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.persons_live, 1);
    assert_eq!(census.review_open, 0);
    assert_eq!(
        census.exact_fold_clusters_never_enqueued, 0,
        "accepted/merged cluster must not count as never-enqueued"
    );
    assert_eq!(
        census.name_only_wa_exact_fold_contacts, 0,
        "merged cluster is no longer two live persons"
    );
    assert_context_matches_sql(&arch, &census);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_wa_with_phone_is_not_name_only() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    let (wa_pid, _) = persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let phone_iid = insert_ident(
        &arch,
        "whatsapp",
        "phone",
        "+905321110199",
        "+905321110199",
        Some("Ada"),
    );
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'manual', 1.0, 'user')",
            rusqlite::params![wa_pid, phone_iid],
        )
        .unwrap();
    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(stats.auto_person_merges, 0);
    assert_eq!(live_non_self(&arch), 2);

    let census = review_census(&arch).unwrap();
    assert_eq!(census.name_only_wa_exact_fold_contacts, 1);
    assert_eq!(
        census.name_only_wa_no_phone_email, 0,
        "WA Ada that also has a phone identity is not name-only"
    );
    assert_eq!(census.exact_fold_clusters_never_enqueued, 0);
    assert_census_json_integers_no_names(&census);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_census_does_not_enqueue_or_change_links() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    persist_card(&mut arch, "card-ada", "Ada", Some("+905321110100"), None);
    persist_wa_display_person(&arch, "Ada", &name_fold_join("Ada"));
    let queue_before = queue_rows(&arch);
    let links_before = person_identity_rows(&arch);
    let persons_before = count(&arch, "SELECT COUNT(*) FROM persons");
    let identities_before = sql_identities(&arch);

    let first = review_census(&arch).unwrap();
    let second = review_census(&arch).unwrap();

    assert_eq!(queue_rows(&arch), queue_before);
    assert_eq!(person_identity_rows(&arch), links_before);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM persons"), persons_before);
    assert_eq!(sql_identities(&arch), identities_before);
    assert_eq!(live_non_self(&arch), 2);
    assert_eq!(first.review_open, 0);
    assert_eq!(second.review_open, 0);
    assert!(first.exact_fold_clusters_never_enqueued >= 1);
    assert_eq!(
        first.exact_fold_clusters_never_enqueued,
        second.exact_fold_clusters_never_enqueued
    );
    assert_census_json_integers_no_names(&first);
    let _ = std::fs::remove_dir_all(&root);
}
