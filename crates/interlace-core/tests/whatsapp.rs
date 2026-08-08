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
