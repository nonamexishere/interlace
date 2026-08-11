//! Gmail mbox + Contacts must-pass matrix.
//!
//! Matrix IDs (gate grep): M1 M2 M3 C1

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::import::ImporterRegistry;
use interlace_core::{ImportOpts, SourceKind};
use interlace_fixtures::{
    write_contacts_vcf, write_mbox, write_takeout_tree, ContactsGenConfig, MboxGenConfig,
    TakeoutGenConfig,
};

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-gm-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn count(arch: &interlace_core::db::Archive, sql: &str) -> i64 {
    arch.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

#[test]
fn gmail_m1_mboxrd_from_escaped() {
    let root = tmp_root();
    let mbox = root.join("mail.mbox");
    write_mbox(
        &mbox,
        &MboxGenConfig {
            n_messages: 5,
            seed: 1,
            missing_message_id_every: None,
            escape_from_in_body: true,
            mixed_charsets: false,
        },
    );
    assert_eq!(
        ImporterRegistry::detect(&mbox).unwrap(),
        SourceKind::GmailMbox
    );

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats.inserted_messages, 5, "M1 inserted");
    let bodies: String = arch
        .conn
        .query_row(
            "SELECT group_concat(body_text, '\n') FROM messages",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(
        bodies.contains("From someone quoted in the body"),
        "M1 must unescape mboxrd >From\n{bodies}"
    );
    assert!(
        !bodies.contains(">From someone quoted"),
        "M1 leftover >From\n{bodies}"
    );

    let stats2 = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats2.inserted_messages, 0);
    assert_eq!(stats2.skipped_dupes, 5);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn gmail_m2_missing_message_id() {
    let root = tmp_root();
    let mbox = root.join("noid.mbox");
    write_mbox(
        &mbox,
        &MboxGenConfig {
            n_messages: 6,
            seed: 2,
            missing_message_id_every: Some(2),
            escape_from_in_body: false,
            mixed_charsets: false,
        },
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(
        stats.inserted_messages, 6,
        "M2 all rows including no Message-ID"
    );
    let hashed = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE idempotency_key LIKE 'gmail-hash:%'",
    );
    assert!(hashed >= 3, "M2 expected gmail-hash keys, got {hashed}");
    let with_id = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE idempotency_key LIKE 'gmail:<%'",
    );
    assert!(with_id >= 1, "M2 expected Message-ID keys");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn gmail_m3_mixed_charsets() {
    let root = tmp_root();
    let mbox = root.join("mix.mbox");
    write_mbox(
        &mbox,
        &MboxGenConfig {
            n_messages: 6,
            seed: 3,
            missing_message_id_every: None,
            escape_from_in_body: false,
            mixed_charsets: true,
        },
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats.inserted_messages, 6, "M3 mixed charsets");
    for i in 0..6 {
        let n = count(
            &arch,
            &format!("SELECT COUNT(*) FROM messages WHERE body_text LIKE '%Hello body {i}%'"),
        );
        assert_eq!(n, 1, "M3 missing body {i}");
    }
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn gmail_c1_vcard_multi_tel_email_photo_uid() {
    let root = tmp_root();
    let vcf = root.join("c.vcf");
    write_contacts_vcf(
        &vcf,
        &ContactsGenConfig {
            n: 3,
            seed: 9,
            with_uid: true,
            with_photo: true,
            empty_fn: false,
        },
    );
    assert_eq!(
        ImporterRegistry::detect(&vcf).unwrap(),
        SourceKind::ContactsVcf
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default())
        .unwrap();
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM contacts_raw"), 3);
    assert!(
        count(&arch, "SELECT COUNT(*) FROM contact_channels") >= 6,
        "C1 TEL+EMAIL per card"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM contacts_raw WHERE photo_cas_hash IS NOT NULL"
        ),
        3
    );
    assert!(count(&arch, "SELECT COUNT(*) FROM cas_blobs") >= 1);
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM person_identities WHERE link_reason = 'takeout_vcard'"
        ),
        count(&arch, "SELECT COUNT(*) FROM contact_channels")
    );
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM persons"), 3);

    arch.run_import(SourceKind::ContactsVcf, &vcf, &ImportOpts::default())
        .unwrap();
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM contacts_raw"), 3);
    assert_eq!(count(&arch, "SELECT COUNT(*) FROM persons"), 3);

    let tree = write_takeout_tree(
        &root.join("to"),
        &TakeoutGenConfig {
            n_mail: 2,
            n_contacts: 2,
            seed: 7,
        },
    );
    assert_eq!(
        ImporterRegistry::detect(&tree).unwrap(),
        SourceKind::TakeoutDir
    );
    let stats = arch
        .run_import(SourceKind::TakeoutDir, &tree, &ImportOpts::default())
        .unwrap();
    assert!(stats.inserted_messages >= 2, "takeout mail");
    assert!(stats.warnings >= 1, "OQ5 raw-rfc822 warning");
    let _ = std::fs::remove_dir_all(&root);
}

/// Takeout All-mail uses `\nFrom ` at column 0 with no blank line between
/// records. `>From` in a body is not a fourth envelope.
#[test]
fn gmail_mbox_from_split_without_blank_line() {
    let root = tmp_root();
    let mbox = root.join("takeout-style.mbox");
    // Three messages joined only by newline+From (space, no colon). No blank
    // line before the next envelope. Body `>From` must not split.
    std::fs::write(
        &mbox,
        "\
From alice@example.com Sat Jan 01 00:00:00 2024
From: alice@example.com
To: bob@example.com
Subject: one
Message-ID: <one@example.com>

body one
From alice@example.com Sat Jan 01 00:00:01 2024
From: alice@example.com
To: bob@example.com
Subject: two
Message-ID: <two@example.com>

body two
>From someone quoted
From alice@example.com Sat Jan 01 00:00:02 2024
From: alice@example.com
To: bob@example.com
Subject: three
Message-ID: <three@example.com>

body three
",
    )
    .unwrap();

    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats.inserted_messages, 3, "newline+From must split three");
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        3,
        ">From in a body must not create a fourth message"
    );
    for subj in ["one", "two", "three"] {
        assert_eq!(
            count(
                &arch,
                &format!("SELECT COUNT(*) FROM messages WHERE subject = '{subj}'"),
            ),
            1,
            "subject {subj} must appear once"
        );
    }

    let stats2 = arch
        .run_import(SourceKind::GmailMbox, &mbox, &ImportOpts::default())
        .unwrap();
    assert_eq!(stats2.inserted_messages, 0);
    assert_eq!(stats2.skipped_dupes, 3);
    let _ = std::fs::remove_dir_all(&root);
}
