//! Review card: both sides' message counts and samples (#149).
//! Identifiers on each side panel (#128): kind + value_normalized.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//! Matrix IDs (gate grep):
//!
//! `review_show` must return `left` / `right` panels, not a single top-level
//! `samples` array. Sent group messages count; received-only group chatter
//! does not. Each panel lists `platforms`. Do not assume which panel is
//! WhatsApp vs Contacts — classify from `review.left_identity_id` /
//! `review.right_person_id`.
//!
//! #128: each side panel (left / right, and every entry of `sides` when present)
//! exposes `identifiers: [{ kind, value_normalized, platform? }, …]` so a
//! name_similarity card is decidable without CLI `review show`. Samples stay
//! plain `body_text` (no body_html). Score / evidence chrome unchanged.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::{name_fold_join, normalize_email};
use interlace_core::{resolve_run, review_show};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-rs-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn live_non_self(arch: &interlace_core::db::Archive) -> i64 {
    count(
        arch,
        "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL AND is_self = 0",
    )
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

struct AdaPair {
    contacts_iid: i64,
    wa_iid: i64,
}

fn plant_ada_pair(arch: &mut interlace_core::db::Archive) -> AdaPair {
    persist_card(arch, "card-ada", "Ada", Some("+905321110100"), None);
    let (wa_pid, wa_iid) = persist_wa_display_person(arch, "Ada", &name_fold_join("Ada"));
    let contacts_iid: i64 = arch
        .conn
        .query_row(
            "SELECT i.id FROM identities i
             WHERE i.platform = 'contacts' AND i.kind = 'phone'
               AND i.value_normalized = '+905321110100'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let contacts_pid: i64 = arch
        .conn
        .query_row(
            "SELECT p.id FROM persons p
             JOIN person_identities pi ON pi.person_id = p.id
             WHERE pi.identity_id = ?1 AND p.tombstoned_at IS NULL",
            [contacts_iid],
            |r| r.get(0),
        )
        .unwrap();
    assert_ne!(
        wa_pid, contacts_pid,
        "plant must start with two Ada persons"
    );
    AdaPair {
        contacts_iid,
        wa_iid,
    }
}

struct MsgInfra {
    source_id: i64,
    run_id: i64,
}

fn ensure_msg_infra(arch: &interlace_core::db::Archive) -> MsgInfra {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_ios_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let source_id = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [source_id],
        )
        .unwrap();
    MsgInfra {
        source_id,
        run_id: arch.conn.last_insert_rowid(),
    }
}

fn insert_conv(
    arch: &interlace_core::db::Archive,
    platform: &str,
    kind: &str,
    native_id: &str,
    title: &str,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![platform, kind, native_id, title],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn add_participant(arch: &interlace_core::db::Archive, conv: i64, iid: i64) {
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, 'member')",
            rusqlite::params![conv, iid],
        )
        .unwrap();
}

fn insert_msg(
    arch: &interlace_core::db::Archive,
    infra: &MsgInfra,
    conv: i64,
    sender: i64,
    sent_at: &str,
    body: &str,
    key: &str,
) {
    insert_msg_html(arch, infra, conv, sender, sent_at, body, None, key);
}

fn insert_msg_html(
    arch: &interlace_core::db::Archive,
    infra: &MsgInfra,
    conv: i64,
    sender: i64,
    sent_at: &str,
    body: &str,
    body_html: Option<&str>,
    key: &str,
) {
    arch.conn
        .execute(
            "INSERT INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, body_html, idempotency_key
             ) VALUES (?1, ?2, ?3, ?4, ?5, 'second', 'text', ?6, ?7, ?8)",
            rusqlite::params![
                conv,
                infra.source_id,
                infra.run_id,
                sender,
                sent_at,
                body,
                body_html,
                key
            ],
        )
        .unwrap();
}

fn plant_dm_from(
    arch: &interlace_core::db::Archive,
    infra: &MsgInfra,
    sender: i64,
    native_id: &str,
    sent_at: &str,
    body: &str,
    key: &str,
) {
    let conv = insert_conv(arch, "whatsapp", "dm", native_id, "Ada");
    add_participant(arch, conv, sender);
    insert_msg(arch, infra, conv, sender, sent_at, body, key);
}

fn open_review_id(arch: &interlace_core::db::Archive) -> i64 {
    let n = count(
        arch,
        "SELECT COUNT(*) FROM merge_review_queue WHERE status='open'",
    );
    assert_eq!(n, 1, "expected exactly one open review, got {n}");
    arch.conn
        .query_row(
            "SELECT id FROM merge_review_queue WHERE status='open'",
            [],
            |r| r.get(0),
        )
        .unwrap()
}

fn show(arch: &interlace_core::db::Archive) -> serde_json::Value {
    review_show(arch, open_review_id(arch)).unwrap()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Side {
    Whatsapp,
    Contacts,
}

fn identity_platform(arch: &interlace_core::db::Archive, iid: i64) -> String {
    arch.conn
        .query_row(
            "SELECT platform FROM identities WHERE id = ?1",
            [iid],
            |r| r.get(0),
        )
        .unwrap()
}

fn person_platforms(arch: &interlace_core::db::Archive, pid: i64) -> Vec<String> {
    let mut stmt = arch
        .conn
        .prepare(
            "SELECT DISTINCT i.platform
             FROM person_identities pi
             JOIN identities i ON i.id = pi.identity_id
             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
             WHERE pi.person_id = ?1",
        )
        .unwrap();
    stmt.query_map([pid], |r| r.get::<_, String>(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

fn side_from_platforms(plats: &[String]) -> Side {
    let has_wa = plats.iter().any(|p| p == "whatsapp");
    let has_ct = plats.iter().any(|p| p == "contacts");
    match (has_wa, has_ct) {
        (true, false) => Side::Whatsapp,
        (false, true) => Side::Contacts,
        _ => panic!("cannot classify side from platforms {plats:?}"),
    }
}

fn assert_panel_shell(shown: &serde_json::Value) {
    assert!(
        shown.get("review").is_some(),
        "review object must be kept: {shown}"
    );
    assert!(
        shown.get("evidence").and_then(|e| e.as_array()).is_some(),
        "evidence array must be kept: {shown}"
    );
    assert!(
        shown.get("left").map(|v| v.is_object()).unwrap_or(false),
        "expected left panel object, got {shown}"
    );
    assert!(
        shown.get("right").map(|v| v.is_object()).unwrap_or(false),
        "expected right panel object, got {shown}"
    );
    assert_eq!(
        shown["left"]["display_name"], shown["review"]["left_name"],
        "left.display_name must match review.left_name"
    );
    assert_eq!(
        shown["right"]["display_name"], shown["review"]["right_name"],
        "right.display_name must match review.right_name"
    );
    assert!(
        shown["left"]["platforms"].as_array().is_some(),
        "left.platforms must be an array: {shown}"
    );
    assert!(
        shown["right"]["platforms"].as_array().is_some(),
        "right.platforms must be an array: {shown}"
    );
}

fn platforms_of(panel: &serde_json::Value) -> Vec<String> {
    panel["platforms"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|v| v.as_str().unwrap_or("").to_string())
                .collect()
        })
        .unwrap_or_default()
}

struct Panels<'a> {
    wa: &'a serde_json::Value,
    contacts: &'a serde_json::Value,
}

fn both_panels<'a>(arch: &interlace_core::db::Archive, shown: &'a serde_json::Value) -> Panels<'a> {
    assert_panel_shell(shown);
    let left_iid = shown["review"]["left_identity_id"]
        .as_i64()
        .expect("review.left_identity_id");
    let right_pid = shown["review"]["right_person_id"]
        .as_i64()
        .expect("review.right_person_id (same-name review has a right person)");
    let left_side = side_from_platforms(&[identity_platform(arch, left_iid)]);
    let right_side = side_from_platforms(&person_platforms(arch, right_pid));
    match (left_side, right_side) {
        (Side::Whatsapp, Side::Contacts) => Panels {
            wa: &shown["left"],
            contacts: &shown["right"],
        },
        (Side::Contacts, Side::Whatsapp) => Panels {
            wa: &shown["right"],
            contacts: &shown["left"],
        },
        other => panic!(
            "expected one WhatsApp panel and one Contacts panel, got {other:?} shown={shown}"
        ),
    }
}

fn json_count(v: &serde_json::Value) -> i64 {
    v.as_i64()
        .or_else(|| v.as_u64().map(|n| i64::try_from(n).unwrap()))
        .unwrap_or_else(|| panic!("expected number, got {v}"))
}

fn samples_of(panel: &serde_json::Value) -> &[serde_json::Value] {
    panel["samples"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_else(|| panic!("samples must be an array, got {panel}"))
}

fn sample_bodies(panel: &serde_json::Value) -> Vec<String> {
    samples_of(panel)
        .iter()
        .map(|s| {
            assert!(
                s.get("body_html").is_none(),
                "samples must not return body_html: {s}"
            );
            let body = s["body_text"]
                .as_str()
                .unwrap_or_else(|| panic!("body_text must be a string: {s}"));
            assert!(
                body.chars().count() <= 240,
                "body_text longer than 240 chars: {}",
                body.chars().count()
            );
            body.to_string()
        })
        .collect()
}

fn bodies_contain(panel: &serde_json::Value, needle: &str) -> bool {
    sample_bodies(panel).iter().any(|b| b.contains(needle))
}

fn assert_empty_side(panel: &serde_json::Value, label: &str) {
    assert_eq!(
        json_count(&panel["message_count"]),
        0,
        "{label} message_count"
    );
    assert!(
        samples_of(panel).is_empty(),
        "{label} samples must be empty, got {:?}",
        sample_bodies(panel)
    );
}

/// #128 — panel identifiers: kind + value_normalized (platform optional).
fn identifiers_of(panel: &serde_json::Value) -> &[serde_json::Value] {
    panel["identifiers"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_else(|| {
            panic!(
                "panel.identifiers must be an array (kind + value_normalized per entry), got {panel}"
            )
        })
}

fn assert_identifier_shape(entry: &serde_json::Value, label: &str) {
    let kind = entry
        .get("kind")
        .and_then(|v| v.as_str())
        .unwrap_or_else(|| panic!("{label}: identifier.kind must be a non-empty string: {entry}"));
    assert!(
        !kind.is_empty(),
        "{label}: identifier.kind must be non-empty: {entry}"
    );
    let norm = entry
        .get("value_normalized")
        .and_then(|v| v.as_str())
        .unwrap_or_else(|| {
            panic!("{label}: identifier.value_normalized must be a non-empty string: {entry}")
        });
    assert!(
        !norm.is_empty(),
        "{label}: identifier.value_normalized must be non-empty: {entry}"
    );
    if let Some(plat) = entry.get("platform") {
        if !plat.is_null() {
            let p = plat.as_str().unwrap_or_else(|| {
                panic!("{label}: identifier.platform must be a string when present: {entry}")
            });
            assert!(
                !p.is_empty(),
                "{label}: identifier.platform must be non-empty when present: {entry}"
            );
        }
    }
}

fn assert_panel_identifiers(panel: &serde_json::Value, label: &str) {
    let ids = identifiers_of(panel);
    assert!(
        !ids.is_empty(),
        "{label}: identifiers must list at least one kind+value_normalized: {panel}"
    );
    for (i, entry) in ids.iter().enumerate() {
        assert_identifier_shape(entry, &format!("{label}.identifiers[{i}]"));
    }
}

fn panel_has_ident(panel: &serde_json::Value, kind: &str, value_normalized: &str) -> bool {
    identifiers_of(panel).iter().any(|e| {
        e["kind"].as_str() == Some(kind)
            && e["value_normalized"].as_str() == Some(value_normalized)
    })
}

fn review_panels_for_idents<'a>(shown: &'a serde_json::Value) -> Vec<&'a serde_json::Value> {
    if let Some(sides) = shown.get("sides").and_then(|v| v.as_array()) {
        if !sides.is_empty() {
            return sides.iter().collect();
        }
    }
    vec![&shown["left"], &shown["right"]]
}

#[test]
fn review_show_empty_contacts_plus_wa_dm() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let pair = plant_ada_pair(&mut arch);
    let infra = ensure_msg_infra(&arch);
    plant_dm_from(
        &arch,
        &infra,
        pair.wa_iid,
        "whatsapp:ada-dm",
        "2024-03-01T10:00:00Z",
        "Ada dm hi",
        "k-ada-dm",
    );

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        live_non_self(&arch),
        2,
        "I2 remains: names never auto-merge"
    );
    assert!(
        stats.review_enqueued >= 1,
        "same-name Ada pair must enqueue review"
    );

    let shown = show(&arch);
    let panels = both_panels(&arch, &shown);
    assert_eq!(json_count(&panels.wa["message_count"]), 1);
    assert!(
        bodies_contain(panels.wa, "Ada dm hi"),
        "WA samples missing Ada dm hi: {:?}",
        sample_bodies(panels.wa)
    );
    assert!(
        platforms_of(panels.wa).iter().any(|p| p == "whatsapp"),
        "WA platforms: {:?}",
        platforms_of(panels.wa)
    );
    assert!(
        platforms_of(panels.contacts)
            .iter()
            .any(|p| p == "contacts"),
        "Contacts platforms: {:?}",
        platforms_of(panels.contacts)
    );
    assert_empty_side(panels.contacts, "Contacts");
    assert_eq!(live_non_self(&arch), 2);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_show_both_sides_have_d18() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let pair = plant_ada_pair(&mut arch);
    let infra = ensure_msg_infra(&arch);
    plant_dm_from(
        &arch,
        &infra,
        pair.wa_iid,
        "whatsapp:ada-wa",
        "2024-03-02T10:00:00Z",
        "Ada wa note",
        "k-ada-wa",
    );
    let mail = insert_conv(&arch, "gmail", "email_thread", "gmail:ada-mail", "Ada mail");
    add_participant(&arch, mail, pair.contacts_iid);
    insert_msg(
        &arch,
        &infra,
        mail,
        pair.contacts_iid,
        "2024-03-02T11:00:00Z",
        "Ada mail note",
        "k-ada-mail",
    );

    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);

    let shown = show(&arch);
    let panels = both_panels(&arch, &shown);
    assert!(
        json_count(&panels.wa["message_count"]) >= 1,
        "WA count: {}",
        panels.wa["message_count"]
    );
    assert!(
        json_count(&panels.contacts["message_count"]) >= 1,
        "Contacts count: {}",
        panels.contacts["message_count"]
    );
    assert!(
        bodies_contain(panels.wa, "Ada wa note"),
        "WA samples: {:?}",
        sample_bodies(panels.wa)
    );
    assert!(
        !bodies_contain(panels.wa, "Ada mail note"),
        "WA samples leaked Contacts body: {:?}",
        sample_bodies(panels.wa)
    );
    assert!(
        bodies_contain(panels.contacts, "Ada mail note"),
        "Contacts samples: {:?}",
        sample_bodies(panels.contacts)
    );
    assert!(
        !bodies_contain(panels.contacts, "Ada wa note"),
        "Contacts samples leaked WA body: {:?}",
        sample_bodies(panels.contacts)
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_show_sent_group_messages_count() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let pair = plant_ada_pair(&mut arch);
    let infra = ensure_msg_infra(&arch);
    let grp = insert_conv(&arch, "whatsapp", "group", "whatsapp:project", "Project");
    add_participant(&arch, grp, pair.wa_iid);
    insert_msg(
        &arch,
        &infra,
        grp,
        pair.wa_iid,
        "2024-03-03T10:00:00Z",
        "Ada group only",
        "k-ada-group",
    );

    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);

    let shown = show(&arch);
    let panels = both_panels(&arch, &shown);
    assert_eq!(
        json_count(&panels.wa["message_count"]),
        1,
        "sent group messages must count on Review"
    );
    assert!(
        bodies_contain(panels.wa, "Ada group only"),
        "WA samples missing group send: {:?}",
        sample_bodies(panels.wa)
    );
    assert_empty_side(panels.contacts, "Contacts");

    plant_dm_from(
        &arch,
        &infra,
        pair.wa_iid,
        "whatsapp:ada-later",
        "2024-03-03T12:00:00Z",
        "Ada later dm",
        "k-ada-later",
    );

    let shown = show(&arch);
    let panels = both_panels(&arch, &shown);
    assert_eq!(json_count(&panels.wa["message_count"]), 2);
    assert!(
        bodies_contain(panels.wa, "Ada later dm"),
        "later DM must count: {:?}",
        sample_bodies(panels.wa)
    );
    assert!(
        bodies_contain(panels.wa, "Ada group only"),
        "group send must still count: {:?}",
        sample_bodies(panels.wa)
    );
    assert_empty_side(panels.contacts, "Contacts after later DM");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn review_show_caps_samples_at_three_count_is_full() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let pair = plant_ada_pair(&mut arch);
    let infra = ensure_msg_infra(&arch);
    let conv = insert_conv(&arch, "whatsapp", "dm", "whatsapp:ada-cap", "Ada");
    add_participant(&arch, conv, pair.wa_iid);
    let newest = format!("Ada cap 5 {}", "x".repeat(300));
    let bodies = [
        ("2024-03-04T00:00:01Z", "Ada cap 1", "k-cap-1", None),
        ("2024-03-04T00:00:02Z", "Ada cap 2", "k-cap-2", None),
        ("2024-03-04T00:00:03Z", "Ada cap 3", "k-cap-3", None),
        ("2024-03-04T00:00:04Z", "Ada cap 4", "k-cap-4", None),
    ];
    for (at, body, key, html) in bodies {
        insert_msg_html(&arch, &infra, conv, pair.wa_iid, at, body, html, key);
    }
    insert_msg_html(
        &arch,
        &infra,
        conv,
        pair.wa_iid,
        "2024-03-04T00:00:05Z",
        &newest,
        Some("<p>Ada cap 5 html</p>"),
        "k-cap-5",
    );

    resolve_run(&mut arch, 0).unwrap();
    assert_eq!(live_non_self(&arch), 2);

    let shown = show(&arch);
    let panels = both_panels(&arch, &shown);
    assert_eq!(json_count(&panels.wa["message_count"]), 5);
    let samples = samples_of(panels.wa);
    assert_eq!(samples.len(), 3, "samples capped at 3");
    let got = sample_bodies(panels.wa);
    let want_newest: String = newest.chars().take(240).collect();
    assert_eq!(got[0], want_newest, "first sample is the newest body");
    assert_eq!(got[0].chars().count(), 240);
    assert_eq!(samples[0]["sent_at"].as_str(), Some("2024-03-04T00:00:05Z"));
    assert_eq!(got[1], "Ada cap 4");
    assert_eq!(got[2], "Ada cap 3");
    assert!(!got.iter().any(|b| b.contains("Ada cap 1")));
    assert!(!got.iter().any(|b| b.contains("Ada cap 2")));
    assert!(!got.iter().any(|b| b.contains("Ada cap 5 html")));
    assert_empty_side(panels.contacts, "Contacts");
    let _ = std::fs::remove_dir_all(&root);
}

/// #128: name_similarity card exposes kind+value_normalized on every panel.
///
/// Plant: Contacts Ada (phone) + WhatsApp Ada (display_name). User must see
/// identifiers (not only display_name / platforms) so Accept is decidable
/// without CLI `review show`. Samples stay body_text; score/evidence kept.
#[test]
fn review_show_panels_include_identifiers() {
    let root = tmp_root();
    let mut arch = init_archive(&root).unwrap();
    let pair = plant_ada_pair(&mut arch);
    let infra = ensure_msg_infra(&arch);
    plant_dm_from(
        &arch,
        &infra,
        pair.wa_iid,
        "whatsapp:ada-id-dm",
        "2024-03-05T10:00:00Z",
        "Ada id sample",
        "k-ada-id-dm",
    );

    let stats = resolve_run(&mut arch, 0).unwrap();
    assert_eq!(
        live_non_self(&arch),
        2,
        "I2 remains: names never auto-merge"
    );
    assert!(
        stats.review_enqueued >= 1,
        "same-name Ada pair must enqueue review"
    );

    let shown = show(&arch);
    assert_panel_shell(&shown);
    assert!(
        shown
            .get("evidence")
            .and_then(|e| e.as_array())
            .map(|a| !a.is_empty())
            .unwrap_or(false),
        "evidence list must stay: {shown}"
    );
    assert!(
        shown["review"].get("score").is_some()
            || shown["review"].get("suggested_score").is_some(),
        "score must stay on the review card: {shown}"
    );

    // left / right always carry identifiers (kind + value_normalized).
    assert_panel_identifiers(&shown["left"], "left");
    assert_panel_identifiers(&shown["right"], "right");

    // n-way sides[] (when present): same shape on every side.
    if let Some(sides) = shown.get("sides").and_then(|v| v.as_array()) {
        for (i, side) in sides.iter().enumerate() {
            assert_panel_identifiers(side, &format!("sides[{i}]"));
        }
    }

    let panels = both_panels(&arch, &shown);
    let ada_fold = name_fold_join("Ada");
    assert!(
        panel_has_ident(panels.wa, "display_name", &ada_fold),
        "WA panel must expose the display_name identity (kind=display_name, \
         value_normalized={ada_fold:?}): identifiers={:?}",
        identifiers_of(panels.wa)
    );
    assert!(
        panel_has_ident(panels.contacts, "phone", "+905321110100"),
        "Contacts panel must expose the linked phone (kind=phone, \
         value_normalized=+905321110100): identifiers={:?}",
        identifiers_of(panels.contacts)
    );

    // Samples remain text nodes (body_text only; no body_html dump).
    assert!(
        bodies_contain(panels.wa, "Ada id sample"),
        "WA samples must still show the planted body: {:?}",
        sample_bodies(panels.wa)
    );
    for panel in review_panels_for_idents(&shown) {
        let _ = sample_bodies(panel); // panics if body_html / non-text
    }

    // Platform on an identifier entry is optional; when present it is a string.
    for panel in review_panels_for_idents(&shown) {
        for entry in identifiers_of(panel) {
            if let Some(p) = entry.get("platform") {
                if !p.is_null() {
                    assert!(
                        p.as_str().map(|s| !s.is_empty()).unwrap_or(false),
                        "platform when present must be a non-empty string: {entry}"
                    );
                }
            }
        }
    }

    assert_eq!(live_non_self(&arch), 2);
    let _ = std::fs::remove_dir_all(&root);
}
