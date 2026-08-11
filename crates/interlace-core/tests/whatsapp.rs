//! WhatsApp must-pass matrix.
//!
//! Matrix IDs (gate grep): W1 W2 W3 W4

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::{ImporterRegistry, WhatsappImporter};
use interlace_core::{ImportOpts, SourceImporter, SourceKind};
use interlace_fixtures::{write_whatsapp_zip, WaGenConfig};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-wa-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

/// iOS en-US DM, no media — same seed + larger `n_messages` prefixes the smaller export.
fn wa_later_reexport_cfg(n_messages: usize) -> WaGenConfig {
    WaGenConfig {
        locale: "en-US",
        ios: true,
        with_media: false,
        n_messages,
        n_participants: 2,
        corrupt_line_every: None,
        missing_media_every: None,
        multiline_ratio: 0.0,
        system_every: None,
        seed: 100,
    }
}

fn user_message_id(arch: &interlace_core::db::Archive, i: usize) -> i64 {
    arch.conn
        .query_row(
            "SELECT id FROM messages WHERE body_text LIKE ?1",
            [format!("msg-{i} %")],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("expected user row msg-{i}: {e}"))
}

fn user_message_ids(arch: &interlace_core::db::Archive, last: usize) -> Vec<i64> {
    (1..=last).map(|i| user_message_id(arch, i)).collect()
}

fn assert_each_user_row_once(arch: &interlace_core::db::Archive, last: usize) {
    for i in 1..=last {
        let n: i64 = arch
            .conn
            .query_row(
                "SELECT COUNT(*) FROM messages WHERE body_text LIKE ?1",
                [format!("msg-{i} %")],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(n, 1, "user row msg-{i} should exist once, got {n}");
    }
}

#[test]
fn whatsapp_w1_ios_en_us_dm_no_media() {
    let root = tmp_root();
    let zip = write_whatsapp_zip(
        &root.join("zips"),
        &WaGenConfig {
            locale: "en-US",
            ios: true,
            with_media: false,
            n_messages: 200,
            n_participants: 2,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.0,
            system_every: None,
            seed: 1,
        },
    );
    let probe = WhatsappImporter::default().probe(&zip).unwrap();
    assert_eq!(probe.kind, SourceKind::WhatsappIosZip);
    assert_eq!(probe.locale_guess.as_deref(), Some("en-US"));
    assert_eq!(
        ImporterRegistry::detect(&zip).unwrap(),
        SourceKind::WhatsappIosZip
    );

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    // 200 user/system fixture lines + encryption banner
    assert!(
        stats.inserted_messages >= 200,
        "W1 inserted {}",
        stats.inserted_messages
    );
    assert_eq!(stats.skipped_dupes, 0);
    let n = count(&arch, "SELECT COUNT(*) FROM messages");
    assert!(n >= 200, "messages={n}");
    let kind: String = arch
        .conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap();
    assert_eq!(kind, "dm", "W1 must be a DM");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM attachments"), 0);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM identities WHERE kind = 'whatsapp_jid'"
        ),
        0
    );
    assert!(count(&arch, "SELECT COUNT(*) FROM identities") >= 2);

    let stats2 = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert_eq!(stats2.inserted_messages, 0);
    assert!(
        stats2.skipped_dupes >= 200,
        "W1 reimport dupes {}",
        stats2.skipped_dupes
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM messages"), n);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn whatsapp_w2_ios_tr_tr_group_media() {
    let root = tmp_root();
    let zip = write_whatsapp_zip(
        &root.join("zips"),
        &WaGenConfig {
            locale: "tr-TR",
            ios: true,
            with_media: true,
            n_messages: 500,
            n_participants: 8,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.0,
            system_every: Some(50),
            seed: 2,
        },
    );
    let probe = WhatsappImporter::default().probe(&zip).unwrap();
    assert_eq!(probe.kind, SourceKind::WhatsappIosZip);
    assert_eq!(probe.locale_guess.as_deref(), Some("tr-TR"));

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip,
            &ImportOpts {
                locale: Some("tr-TR".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert!(
        stats.inserted_messages >= 500,
        "W2 inserted {}",
        stats.inserted_messages
    );
    assert!(
        stats.attachments_stored > 0,
        "W2 should store media, stored={}",
        stats.attachments_stored
    );
    let kind: String = arch
        .conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap();
    assert_eq!(kind, "group", "W2 group 8 participants");
    assert!(
        count(
            &arch,
            "SELECT COUNT(*) FROM attachments WHERE cas_hash IS NOT NULL"
        ) > 0
    );
    assert!(count(&arch, "SELECT COUNT(*) FROM cas_blobs") > 0);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM identities WHERE kind = 'whatsapp_jid'"
        ),
        0
    );
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn whatsapp_w3_android_de_de_media() {
    let root = tmp_root();
    let zip = write_whatsapp_zip(
        &root.join("zips"),
        &WaGenConfig {
            locale: "de-DE",
            ios: false,
            with_media: true,
            n_messages: 200,
            n_participants: 2,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.0,
            system_every: None,
            seed: 3,
        },
    );
    let probe = WhatsappImporter::default().probe(&zip).unwrap();
    assert_eq!(probe.kind, SourceKind::WhatsappAndroidZip);
    assert_eq!(probe.locale_guess.as_deref(), Some("de-DE"));

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(
            SourceKind::WhatsappAndroidZip,
            &zip,
            &ImportOpts {
                locale: Some("de-DE".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert!(
        stats.inserted_messages >= 200,
        "W3 inserted {}",
        stats.inserted_messages
    );
    assert!(stats.attachments_stored > 0, "W3 media stored");
    let n_att = count(&arch, "SELECT COUNT(*) FROM attachments");
    assert!(n_att > 0, "W3 attachments={n_att}");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn whatsapp_w4_android_pt_br_multiline_system() {
    let root = tmp_root();
    let zip = write_whatsapp_zip(
        &root.join("zips"),
        &WaGenConfig {
            locale: "pt-BR",
            ios: false,
            with_media: false,
            n_messages: 80,
            n_participants: 3,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.5,
            system_every: Some(10),
            seed: 4,
        },
    );
    let probe = WhatsappImporter::default().probe(&zip).unwrap();
    assert_eq!(probe.kind, SourceKind::WhatsappAndroidZip);
    assert_eq!(probe.locale_guess.as_deref(), Some("pt-BR"));

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(
            SourceKind::WhatsappAndroidZip,
            &zip,
            &ImportOpts {
                locale: Some("pt-BR".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert!(
        stats.inserted_messages >= 80,
        "W4 inserted {}",
        stats.inserted_messages
    );
    let systems = count(&arch, "SELECT COUNT(*) FROM messages WHERE kind = 'system'");
    assert!(systems >= 1, "W4 expected system rows, got {systems}");
    let multi = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE body_text LIKE '%continuation line%'",
    );
    assert!(multi >= 1, "W4 expected multiline continuation");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM attachments"), 0);
    let _ = std::fs::remove_dir_all(&root);
}

fn write_named_ios_zip(dir: &std::path::Path, stem: &str, chat: &str) -> std::path::PathBuf {
    use std::io::Write;
    std::fs::create_dir_all(dir).unwrap();
    let p = dir.join(format!("{stem}.zip"));
    let f = std::fs::File::create(&p).unwrap();
    let mut z = zip::ZipWriter::new(f);
    z.start_file(
        "_chat.txt",
        zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
    )
    .unwrap();
    z.write_all(chat.as_bytes()).unwrap();
    z.finish().unwrap();
    p
}

fn archive_with_owner(root: &std::path::Path, name: &str) -> interlace_core::db::Archive {
    let arch = init_archive(root).unwrap();
    arch.conn
        .execute(
            "UPDATE archive_meta SET owner_display_name = ?1 WHERE id = 1",
            [name],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 1)",
            [name],
        )
        .unwrap();
    arch
}

fn conv_kind(arch: &interlace_core::db::Archive) -> String {
    arch.conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap()
}

/// D18-C: iOS 1:1, no you_token, owner display name + DM ZIP stem → dm + self link.
#[test]
fn whatsapp_d18c_ios_owner_name_is_dm() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Mustafa: hey alice
[2024-03-15, 14:32:20] Alice: hi
";
    let zip = write_named_ios_zip(&root.join("zips"), "WhatsApp Chat - Alice", chat);
    let mut arch = archive_with_owner(&root.join("arch"), "Mustafa");
    arch.run_import(
        SourceKind::WhatsappIosZip,
        &zip,
        &ImportOpts {
            locale: Some("en-US".into()),
            ..ImportOpts::default()
        },
    )
    .unwrap();
    assert_eq!(conv_kind(&arch), "dm");
    let me_role: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM conversation_participants cp
             JOIN identities i ON i.id = cp.identity_id
             WHERE cp.role = 'me' AND i.display_name = 'Mustafa'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(me_role, 1, "owner sender should be role=me");
    let linked: i64 = arch
        .conn
        .query_row(
            "SELECT COUNT(*) FROM person_identities pi
             JOIN persons p ON p.id = pi.person_id
             JOIN identities i ON i.id = pi.identity_id
             WHERE p.is_self = 1 AND i.display_name = 'Mustafa'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(linked, 1, "owner-named WA identity linked to self person");
    let _ = std::fs::remove_dir_all(&root);
}

/// D18-C negative: same two senders, ZIP stem not a DM prefix → stay group.
#[test]
fn whatsapp_d18c_no_dm_prefix_stays_group() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Mustafa: hey
[2024-03-15, 14:32:20] Alice: hi
";
    let zip = write_named_ios_zip(&root.join("zips"), "random-export", chat);
    let mut arch = archive_with_owner(&root.join("arch"), "Mustafa");
    arch.run_import(
        SourceKind::WhatsappIosZip,
        &zip,
        &ImportOpts {
            locale: Some("en-US".into()),
            ..ImportOpts::default()
        },
    )
    .unwrap();
    assert_eq!(conv_kind(&arch), "group");
    let _ = std::fs::remove_dir_all(&root);
}

/// D18-C negative: DM-shaped title but group system line → stay group.
#[test]
fn whatsapp_d18c_group_system_stays_group() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Alice created group
[2024-03-15, 14:32:20] Mustafa: hey
[2024-03-15, 14:32:21] Alice: hi
";
    let zip = write_named_ios_zip(&root.join("zips"), "WhatsApp Chat - Alice", chat);
    let mut arch = archive_with_owner(&root.join("arch"), "Mustafa");
    arch.run_import(
        SourceKind::WhatsappIosZip,
        &zip,
        &ImportOpts {
            locale: Some("en-US".into()),
            ..ImportOpts::default()
        },
    )
    .unwrap();
    assert_eq!(conv_kind(&arch), "group");
    let _ = std::fs::remove_dir_all(&root);
}

/// D18-C negative: three human senders even with owner name + DM stem → group.
#[test]
fn whatsapp_d18c_three_senders_stays_group() {
    let root = tmp_root();
    let chat = "\
[2024-03-15, 14:32:18] Messages and calls are end-to-end encrypted
[2024-03-15, 14:32:19] Mustafa: hey
[2024-03-15, 14:32:20] Alice: hi
[2024-03-15, 14:32:21] Bob: yo
";
    let zip = write_named_ios_zip(&root.join("zips"), "WhatsApp Chat - Book Club", chat);
    let mut arch = archive_with_owner(&root.join("arch"), "Mustafa");
    arch.run_import(
        SourceKind::WhatsappIosZip,
        &zip,
        &ImportOpts {
            locale: Some("en-US".into()),
            ..ImportOpts::default()
        },
    )
    .unwrap();
    assert_eq!(conv_kind(&arch), "group");
    let _ = std::fs::remove_dir_all(&root);
}

/// #32: iOS TR unpadded day + padded day; vote tr-TR; no unknown_row.
#[test]
fn whatsapp_unpadded_day_ios_tr_no_unknown() {
    let root = tmp_root();
    let chat = "\
[3.08.2025, 02:31:13] Mesajlar ve aramalar uçtan uca şifrelidir
[26.03.2025, 10:24:07] Mustafa: merhaba
[7.04.2025, 23:21:09] Alice: hi
[15.03.2024, 14:32:18] Mustafa: <Medya dahil edilmedi>
";
    let zip = write_named_ios_zip(&root.join("zips"), "WhatsApp Chat - Alice", chat);
    let probe = WhatsappImporter::default().probe(&zip).unwrap();
    assert_eq!(probe.kind, SourceKind::WhatsappIosZip);
    assert_eq!(probe.locale_guess.as_deref(), Some("tr-TR"));

    let mut arch = archive_with_owner(&root.join("arch"), "Mustafa");
    let stats = arch
        .run_import(SourceKind::WhatsappIosZip, &zip, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats.warnings, 0, "unpadded day must not unknown_row");
    let unknown = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE kind = 'unknown'",
    );
    assert_eq!(unknown, 0);
    let dated = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE sent_at IS NOT NULL",
    );
    assert_eq!(dated, count(&arch, "SELECT COUNT(*) FROM messages"));
    let _ = std::fs::remove_dir_all(&root);
}

/// #100: later re-export of the same chat must union — A then newer B.
/// Second import inserts only the M newer user rows; overlapping N keep the same `messages.id`.
#[test]
fn whatsapp_later_reexport_a_then_b_unions() {
    const N: usize = 40;
    const M: usize = 12;
    let root = tmp_root();
    // Generator uses a fixed zip filename; write the two archives in different dirs.
    let zip_a = write_whatsapp_zip(&root.join("zip-a"), &wa_later_reexport_cfg(N));
    let zip_b = write_whatsapp_zip(&root.join("zip-b"), &wa_later_reexport_cfg(N + M));

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats_a = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip_a,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    // N user fixture lines + encryption banner (W1-style)
    assert!(
        stats_a.inserted_messages >= N as u64,
        "A inserted {}",
        stats_a.inserted_messages
    );
    assert_eq!(stats_a.skipped_dupes, 0);
    let n_after_a = count(&arch, "SELECT COUNT(*) FROM messages");
    assert!(n_after_a >= N as i64, "messages after A={n_after_a}");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM conversations"), 1);
    let kind: String = arch
        .conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap();
    assert_eq!(kind, "dm", "#100 fixture must be a DM");
    let overlap_ids = user_message_ids(&arch, N);

    let stats_b = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip_b,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    // Banner already present from A; only the M newer user rows insert.
    assert_eq!(
        stats_b.inserted_messages, M as u64,
        "A-then-B must insert only the M newer user rows, inserted={}",
        stats_b.inserted_messages
    );
    assert!(
        stats_b.skipped_dupes >= N as u64,
        "A-then-B skipped_dupes {} < N={N}",
        stats_b.skipped_dupes
    );
    let n_after_b = count(&arch, "SELECT COUNT(*) FROM messages");
    assert_eq!(
        n_after_b,
        n_after_a + M as i64,
        "delta after B must be exactly M user messages"
    );
    assert!(
        n_after_b >= (N + M) as i64,
        "total messages after A-then-B={n_after_b}"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM conversations"), 1);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(DISTINCT conversation_id) FROM messages"
        ),
        1
    );
    assert_eq!(user_message_ids(&arch, N), overlap_ids);
    assert_each_user_row_once(&arch, N + M);
    let _ = std::fs::remove_dir_all(&root);
}

/// #100: later re-export of the same chat must union — newer B then older A.
/// Second import inserts nothing; A's rows are all dupes; ids stay put.
#[test]
fn whatsapp_later_reexport_b_then_a_skips() {
    const N: usize = 40;
    const M: usize = 12;
    let root = tmp_root();
    let zip_a = write_whatsapp_zip(&root.join("zip-a"), &wa_later_reexport_cfg(N));
    let zip_b = write_whatsapp_zip(&root.join("zip-b"), &wa_later_reexport_cfg(N + M));

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats_b = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip_b,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert!(
        stats_b.inserted_messages >= (N + M) as u64,
        "B inserted {}",
        stats_b.inserted_messages
    );
    assert_eq!(stats_b.skipped_dupes, 0);
    let n_after_b = count(&arch, "SELECT COUNT(*) FROM messages");
    assert!(n_after_b >= (N + M) as i64, "messages after B={n_after_b}");
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM conversations"), 1);
    let kind: String = arch
        .conn
        .query_row("SELECT kind FROM conversations LIMIT 1", [], |r| r.get(0))
        .unwrap();
    assert_eq!(kind, "dm", "#100 fixture must be a DM");
    let ids_after_b = user_message_ids(&arch, N + M);

    let stats_a = arch
        .run_import(
            SourceKind::WhatsappIosZip,
            &zip_a,
            &ImportOpts {
                locale: Some("en-US".into()),
                ..ImportOpts::default()
            },
        )
        .unwrap();
    assert_eq!(
        stats_a.inserted_messages, 0,
        "B-then-A must insert nothing, inserted={}",
        stats_a.inserted_messages
    );
    assert!(
        stats_a.skipped_dupes >= N as u64,
        "B-then-A skipped_dupes {} must cover A's N user rows",
        stats_a.skipped_dupes
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        n_after_b,
        "B-then-A must not add rows"
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM conversations"), 1);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(DISTINCT conversation_id) FROM messages"
        ),
        1
    );
    assert_eq!(user_message_ids(&arch, N + M), ids_after_b);
    assert_each_user_row_once(&arch, N + M);
    let _ = std::fs::remove_dir_all(&root);
}
