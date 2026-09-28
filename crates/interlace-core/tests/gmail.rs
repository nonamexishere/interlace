//! Gmail mbox + Contacts must-pass matrix.
//!
//! Matrix IDs (gate grep): M1 M2 M3 C1
//! GM424-SCHEMA GM424-CHAIN GM424-NO-HEADERS GM424-SAME-SUBJECT
//! GM424-MISSING-PARENT GM424-IRT-WINS GM424-NO-CYCLE
//! GM424-LATER-PARENT GM424-WA-PARENTLESS

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

fn has_column(arch: &interlace_core::db::Archive, table: &str, col: &str) -> bool {
    let sql = format!("SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name = ?1");
    let n: i64 = arch.conn.query_row(&sql, [col], |r| r.get(0)).unwrap();
    n > 0
}

fn schema_epoch(arch: &interlace_core::db::Archive) -> i64 {
    arch.conn
        .query_row("SELECT schema_epoch FROM archive_meta", [], |r| r.get(0))
        .unwrap()
}

fn count_params(
    arch: &interlace_core::db::Archive,
    sql: &str,
    params: impl rusqlite::Params,
) -> i64 {
    arch.conn.query_row(sql, params, |r| r.get(0)).unwrap()
}

fn write_mbox_records(path: &std::path::Path, records: &[&str]) {
    let mut out = String::new();
    for (i, rec) in records.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        out.push_str(rec);
        if !rec.ends_with('\n') {
            out.push('\n');
        }
    }
    std::fs::write(path, out).unwrap();
}

fn import_gmail(
    arch: &mut interlace_core::db::Archive,
    mbox: &std::path::Path,
) -> interlace_core::ImportStats {
    arch.run_import(SourceKind::GmailMbox, mbox, &ImportOpts::default())
        .unwrap()
}

fn id_by_subject(arch: &interlace_core::db::Archive, subject: &str) -> i64 {
    let n = count_params(
        arch,
        "SELECT COUNT(*) FROM messages WHERE subject = ?1",
        [subject],
    );
    assert_eq!(n, 1, "one row for subject {subject}, got {n}");
    arch.conn
        .query_row(
            "SELECT id FROM messages WHERE subject = ?1",
            [subject],
            |r| r.get(0),
        )
        .unwrap()
}

fn parent_of(arch: &interlace_core::db::Archive, subject: &str) -> Option<i64> {
    arch.conn
        .query_row(
            "SELECT thread_parent_id FROM messages WHERE subject = ?1",
            [subject],
            |r| r.get(0),
        )
        .unwrap()
}

/// Stored rows in parent-then-replies order: sent_at, then id.
fn ordered_subjects(arch: &interlace_core::db::Archive) -> Vec<String> {
    let mut stmt = arch
        .conn
        .prepare("SELECT COALESCE(subject, '') FROM messages ORDER BY sent_at, id")
        .unwrap();
    let mut rows = stmt.query([]).unwrap();
    let mut out = Vec::new();
    while let Some(r) = rows.next().unwrap() {
        out.push(r.get(0).unwrap());
    }
    out
}

fn sender_blob(arch: &interlace_core::db::Archive, subject: &str) -> String {
    arch.conn
        .query_row(
            "SELECT COALESCE(i.display_name, '') || '|' || COALESCE(i.value_raw, '') \
             || '|' || COALESCE(i.value_normalized, '') \
             FROM messages m \
             JOIN identities i ON i.id = m.sender_identity_id \
             WHERE m.subject = ?1",
            [subject],
            |r| r.get(0),
        )
        .unwrap_or_else(|e| panic!("sender for {subject}: {e}"))
}

/// GM424-SCHEMA: additive References column; schema_epoch stays 1.
#[test]
fn gmail_thread_schema_references_epoch_stays_1() {
    let root = tmp_root();
    let arch = init_archive(&root.join("arch")).unwrap();
    assert_eq!(schema_epoch(&arch), 1, "GM424-SCHEMA: schema_epoch stays 1");
    assert!(
        has_column(&arch, "messages", "references"),
        "GM424-SCHEMA: messages.references must store the raw References header"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-CHAIN: root, reply, reply-to-reply. Parents point at the prior row.
#[test]
fn gmail_thread_three_message_chain() {
    let root = tmp_root();
    let mbox = root.join("chain.mbox");
    write_mbox_records(
        &mbox,
        &[
            "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: root
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <root@example.com>

root
",
            "\
From berk@example.com Sat Jan 01 00:00:01 2024
From: Berk <berk@example.com>
To: Ada <ada@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <reply-one@example.com>
In-Reply-To: <root@example.com>
References: <root@example.com>

reply one
",
            "\
From ada@example.com Sat Jan 01 00:00:02 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: reply two
Date: Sat, 1 Jan 2024 00:00:02 +0000
Message-ID: <reply-two@example.com>
In-Reply-To: <reply-one@example.com>
References: <root@example.com> <reply-one@example.com>

reply two
",
        ],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(stats.inserted_messages, 3, "GM424-CHAIN: three messages");
    let order = ordered_subjects(&arch);
    assert_eq!(
        order,
        vec![
            "root".to_string(),
            "reply one".to_string(),
            "reply two".to_string()
        ],
        "GM424-CHAIN: stored order is parent then replies, got {order:?}"
    );
    let root_id = id_by_subject(&arch, "root");
    let reply_one = id_by_subject(&arch, "reply one");
    let reply_two = id_by_subject(&arch, "reply two");
    assert_eq!(
        parent_of(&arch, "root"),
        None,
        "GM424-CHAIN: root has no parent"
    );
    assert_eq!(
        parent_of(&arch, "reply one"),
        Some(root_id),
        "GM424-CHAIN: reply one thread_parent_id must be the root row"
    );
    assert_eq!(
        parent_of(&arch, "reply two"),
        Some(reply_one),
        "GM424-CHAIN: reply two thread_parent_id must be reply one"
    );
    assert_ne!(reply_two, root_id);
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-NO-HEADERS: no In-Reply-To and no References stays unthreaded.
#[test]
fn gmail_thread_no_headers_stays_null() {
    let root = tmp_root();
    let mbox = root.join("flat.mbox");
    write_mbox_records(
        &mbox,
        &["\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: root
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <flat@example.com>

root
"],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(stats.inserted_messages, 1, "GM424-NO-HEADERS: one message");
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "GM424-NO-HEADERS: no extra row"
    );
    assert_eq!(
        parent_of(&arch, "root"),
        None,
        "GM424-NO-HEADERS: thread_parent_id stays NULL"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-SAME-SUBJECT: a shared subject is not a thread.
#[test]
fn gmail_thread_same_subject_does_not_parent() {
    let root = tmp_root();
    let mbox = root.join("subject.mbox");
    write_mbox_records(
        &mbox,
        &[
            "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: same subject
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <same-a@example.com>

root
",
            "\
From berk@example.com Sat Jan 01 00:00:01 2024
From: Berk <berk@example.com>
To: Ada <ada@example.com>
Subject: same subject
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <same-b@example.com>

reply one
",
        ],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(
        stats.inserted_messages, 2,
        "GM424-SAME-SUBJECT: two messages"
    );
    let parents: i64 = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE subject = 'same subject' AND thread_parent_id IS NOT NULL",
    );
    assert_eq!(
        parents, 0,
        "GM424-SAME-SUBJECT: same subject must not set thread_parent_id, got {parents}"
    );
    assert_eq!(
        count(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE subject = 'same subject'",
        ),
        2,
        "GM424-SAME-SUBJECT: both rows stay"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-MISSING-PARENT: an unknown In-Reply-To does not invent a row.
#[test]
fn gmail_thread_missing_parent_stays_null() {
    let root = tmp_root();
    let mbox = root.join("missing.mbox");
    write_mbox_records(
        &mbox,
        &["\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <orphan@example.com>
In-Reply-To: <not-in-archive@example.com>
References: <not-in-archive@example.com>

reply one
"],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(
        stats.inserted_messages, 1,
        "GM424-MISSING-PARENT: one insert"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        1,
        "GM424-MISSING-PARENT: no placeholder parent row"
    );
    assert_eq!(
        parent_of(&arch, "reply one"),
        None,
        "GM424-MISSING-PARENT: thread_parent_id stays NULL"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-IRT-WINS: In-Reply-To beats the last References id.
#[test]
fn gmail_thread_in_reply_to_beats_references() {
    let root = tmp_root();
    let mbox = root.join("disagree.mbox");
    write_mbox_records(
        &mbox,
        &[
            "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: root
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <irt-parent@example.com>

root
",
            "\
From berk@example.com Sat Jan 01 00:00:01 2024
From: Berk <berk@example.com>
To: Ada <ada@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <refs-last@example.com>

reply one
",
            "\
From ada@example.com Sat Jan 01 00:00:02 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: reply two
Date: Sat, 1 Jan 2024 00:00:02 +0000
Message-ID: <child@example.com>
In-Reply-To: <irt-parent@example.com>
References: <irt-parent@example.com> <refs-last@example.com>

reply two
",
        ],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(stats.inserted_messages, 3, "GM424-IRT-WINS: three messages");
    let irt = id_by_subject(&arch, "root");
    let refs_last = id_by_subject(&arch, "reply one");
    assert_ne!(irt, refs_last);
    assert_eq!(
        parent_of(&arch, "reply two"),
        Some(irt),
        "GM424-IRT-WINS: parent is the In-Reply-To message, not the last References id"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-NO-CYCLE: a self-parent and the edge that would close a cycle stay NULL.
#[test]
fn gmail_thread_self_parent_and_cycle_stay_null() {
    let root = tmp_root();
    let mbox = root.join("cycle.mbox");
    write_mbox_records(
        &mbox,
        &[
            "\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: root
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <self-loop@example.com>
In-Reply-To: <self-loop@example.com>
References: <self-loop@example.com>

root
",
            "\
From ada@example.com Sat Jan 01 00:00:01 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <cycle-a@example.com>
In-Reply-To: <cycle-b@example.com>
References: <cycle-b@example.com>

reply one
",
            "\
From berk@example.com Sat Jan 01 00:00:02 2024
From: Berk <berk@example.com>
To: Ada <ada@example.com>
Subject: reply two
Date: Sat, 1 Jan 2024 00:00:02 +0000
Message-ID: <cycle-b@example.com>
In-Reply-To: <cycle-a@example.com>
References: <cycle-a@example.com>

reply two
",
        ],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let stats = import_gmail(&mut arch, &mbox);
    assert_eq!(stats.inserted_messages, 3, "GM424-NO-CYCLE: three messages");
    assert_eq!(
        parent_of(&arch, "root"),
        None,
        "GM424-NO-CYCLE: self-parent stays NULL"
    );
    let a = id_by_subject(&arch, "reply one");
    let b = id_by_subject(&arch, "reply two");
    let parent_a = parent_of(&arch, "reply one");
    let parent_b = parent_of(&arch, "reply two");
    let cycle = parent_a == Some(b) && parent_b == Some(a);
    assert!(
        !cycle,
        "GM424-NO-CYCLE: a two-message cycle must not be stored"
    );
    let closing = match (parent_a, parent_b) {
        (Some(p), _) if p == b => parent_b,
        (_, Some(p)) if p == a => parent_a,
        _ => None,
    };
    assert_eq!(
        closing, None,
        "GM424-NO-CYCLE: the edge that would cycle stays NULL (a -> {parent_a:?}, b -> {parent_b:?})"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-LATER-PARENT: a later parent fills a NULL child. Reimport does not duplicate or retarget From.
#[test]
fn gmail_thread_later_parent_fills_null_child() {
    let root = tmp_root();
    let child = root.join("child.mbox");
    let parent = root.join("parent.mbox");
    let again = root.join("child-again.mbox");
    write_mbox_records(
        &child,
        &["\
From ada@example.com Sat Jan 01 00:00:01 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <later-child@example.com>
In-Reply-To: <later-root@example.com>
References: <later-root@example.com>

reply one
"],
    );
    write_mbox_records(
        &parent,
        &["\
From ada@example.com Sat Jan 01 00:00:00 2024
From: Ada <ada@example.com>
To: Berk <berk@example.com>
Subject: root
Date: Sat, 1 Jan 2024 00:00:00 +0000
Message-ID: <later-root@example.com>

root
"],
    );
    write_mbox_records(
        &again,
        &["\
From berk@example.com Sat Jan 01 00:00:01 2024
From: Berk <berk@example.com>
To: Ada <ada@example.com>
Subject: reply one
Date: Sat, 1 Jan 2024 00:00:01 +0000
Message-ID: <later-child@example.com>
In-Reply-To: <later-root@example.com>
References: <later-root@example.com>

changed body
"],
    );
    let mut arch = init_archive(&root.join("arch")).unwrap();
    let first = import_gmail(&mut arch, &child);
    assert_eq!(
        first.inserted_messages, 1,
        "GM424-LATER-PARENT: child inserts"
    );
    assert_eq!(
        parent_of(&arch, "reply one"),
        None,
        "GM424-LATER-PARENT: child stays NULL until the parent exists"
    );
    let second = import_gmail(&mut arch, &parent);
    assert_eq!(
        second.inserted_messages, 1,
        "GM424-LATER-PARENT: parent inserts"
    );
    let third = import_gmail(&mut arch, &again);
    assert_eq!(
        third.inserted_messages, 0,
        "GM424-LATER-PARENT: reimport inserts no second row"
    );
    assert_eq!(
        count(&arch, "SELECT COUNT(*) FROM messages"),
        2,
        "GM424-LATER-PARENT: still parent plus one child"
    );
    assert_eq!(
        count_params(
            &arch,
            "SELECT COUNT(*) FROM messages WHERE subject = ?1",
            ["reply one"],
        ),
        1,
        "GM424-LATER-PARENT: the child Message-ID stays one row"
    );
    let from = sender_blob(&arch, "reply one");
    let from_l = from.to_ascii_lowercase();
    assert!(
        from_l.contains("ada"),
        "GM424-LATER-PARENT: first From stays Ada, got {from}"
    );
    assert!(
        !from_l.contains("berk"),
        "GM424-LATER-PARENT: reimport must not change the first From, got {from}"
    );
    let root_id = id_by_subject(&arch, "root");
    assert_eq!(
        parent_of(&arch, "reply one"),
        Some(root_id),
        "GM424-LATER-PARENT: inserting the missing parent fills thread_parent_id on the NULL child"
    );
    let _ = std::fs::remove_dir_all(&root);
}

/// GM424-WA-PARENTLESS: this pass does not parent WhatsApp rows.
#[test]
fn gmail_thread_whatsapp_stays_parentless() {
    let root = tmp_root();
    let zip = interlace_fixtures::write_whatsapp_zip(
        &root.join("zips"),
        &interlace_fixtures::WaGenConfig {
            locale: "en-US",
            ios: true,
            with_media: false,
            n_messages: 4,
            n_participants: 2,
            corrupt_line_every: None,
            missing_media_every: None,
            multiline_ratio: 0.0,
            system_every: None,
            seed: 424,
        },
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
    assert!(
        stats.inserted_messages >= 1,
        "GM424-WA-PARENTLESS: whatsapp import inserts"
    );
    let linked = count(
        &arch,
        "SELECT COUNT(*) FROM messages WHERE thread_parent_id IS NOT NULL",
    );
    assert_eq!(
        linked, 0,
        "GM424-WA-PARENTLESS: WhatsApp rows stay parentless, got {linked}"
    );
    let _ = std::fs::remove_dir_all(&root);
}
