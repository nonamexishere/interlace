//! Search hit jump person (#402): from-me DM / email_thread → unique live peer.
//!
//! `search_hit_person` is the people helper `search_cmd` should call. Do not
//! rewrite FTS. Placeholders Ada / Berk / Self only.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::init_archive;
use interlace_core::people::search_hit_person;

static SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("il-sjp-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    std::fs::create_dir_all(&p).unwrap();
    p
}

struct Plant {
    self_id: i64,
    ada_id: i64,
    berk_id: i64,
    from_me_dm: i64,
    from_ada_dm: i64,
    self_only: i64,
    unlinked: i64,
    group_from_me: i64,
    many_peers: i64,
    email_from_me: i64,
}

fn ident(
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

fn person(arch: &interlace_core::db::Archive, name: &str, is_self: i64) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, ?2)",
            rusqlite::params![name, is_self],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn link(arch: &interlace_core::db::Archive, pid: i64, iid: i64, reason: &str) {
    arch.conn
        .execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, ?3, 0.99, 'system')",
            rusqlite::params![pid, iid, reason],
        )
        .unwrap();
}

fn conv(
    arch: &interlace_core::db::Archive,
    platform: &str,
    kind: &str,
    native: &str,
    title: &str,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![platform, kind, native, title],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn part(arch: &interlace_core::db::Archive, cid: i64, iid: i64, role: &str) {
    arch.conn
        .execute(
            "INSERT INTO conversation_participants(conversation_id, identity_id, role)
             VALUES (?1, ?2, ?3)",
            rusqlite::params![cid, iid, role],
        )
        .unwrap();
}

fn msg(
    arch: &interlace_core::db::Archive,
    cid: i64,
    src: i64,
    run: i64,
    sender: i64,
    sent_at: &str,
    key: &str,
    kind: &str,
) -> i64 {
    arch.conn
        .execute(
            "INSERT INTO messages(conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, body_text, idempotency_key)
             VALUES (?1, ?2, ?3, ?4, ?5, 'second', ?6, 'token', ?7)",
            rusqlite::params![cid, src, run, sender, sent_at, kind, key],
        )
        .unwrap();
    arch.conn.last_insert_rowid()
}

fn plant(arch: &interlace_core::db::Archive) -> Plant {
    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('whatsapp_android_zip', 't', '/t.zip')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();

    let self_wa = ident(
        arch,
        "whatsapp",
        "display_name",
        "Self",
        "self",
        Some("Self"),
    );
    let self_mail = ident(
        arch,
        "gmail",
        "email",
        "self@x.com",
        "self@x.com",
        Some("Self"),
    );
    let self_id = person(arch, "Self", 1);
    link(arch, self_id, self_wa, "self_declared");
    link(arch, self_id, self_mail, "self_declared");
    arch.conn
        .execute(
            "INSERT INTO self_identities(identity_id) VALUES (?1)",
            [self_wa],
        )
        .unwrap();
    arch.conn
        .execute(
            "INSERT INTO self_identities(identity_id) VALUES (?1)",
            [self_mail],
        )
        .unwrap();

    let ada_wa = ident(arch, "whatsapp", "display_name", "Ada", "ada", Some("Ada"));
    let ada_mail = ident(
        arch,
        "gmail",
        "email",
        "ada@x.com",
        "ada@x.com",
        Some("Ada"),
    );
    let ada_id = person(arch, "Ada", 0);
    link(arch, ada_id, ada_wa, "auto_email");
    link(arch, ada_id, ada_mail, "auto_email");

    let berk_wa = ident(
        arch,
        "whatsapp",
        "display_name",
        "Berk",
        "berk",
        Some("Berk"),
    );
    let berk_id = person(arch, "Berk", 0);
    link(arch, berk_id, berk_wa, "auto_email");

    let unlinked = ident(
        arch,
        "whatsapp",
        "display_name",
        "x-unlinked",
        "x-unlinked",
        None,
    );

    let ada_dm = conv(arch, "whatsapp", "dm", "whatsapp:ada", "Ada");
    part(arch, ada_dm, self_wa, "me");
    part(arch, ada_dm, ada_wa, "member");

    let self_notes = conv(arch, "whatsapp", "dm", "whatsapp:self-notes", "Self");
    part(arch, self_notes, self_wa, "me");

    let unlinked_dm = conv(arch, "whatsapp", "dm", "whatsapp:unlinked", "Ada");
    part(arch, unlinked_dm, unlinked, "member");
    part(arch, unlinked_dm, ada_wa, "member");

    let grp = conv(arch, "whatsapp", "group", "whatsapp:g-ada", "Ada and Self");
    part(arch, grp, self_wa, "me");
    part(arch, grp, ada_wa, "member");

    let many = conv(arch, "whatsapp", "dm", "whatsapp:ada-berk", "Ada Berk");
    part(arch, many, self_wa, "me");
    part(arch, many, ada_wa, "member");
    part(arch, many, berk_wa, "member");

    let email = conv(arch, "gmail", "email_thread", "gmail:ada", "Ada");
    part(arch, email, self_mail, "me");
    part(arch, email, ada_mail, "member");

    Plant {
        self_id,
        ada_id,
        berk_id,
        from_me_dm: msg(
            arch,
            ada_dm,
            src,
            run,
            self_wa,
            "2024-03-20T10:00:00Z",
            "k-me-dm",
            "text",
        ),
        from_ada_dm: msg(
            arch,
            ada_dm,
            src,
            run,
            ada_wa,
            "2024-03-20T10:01:00Z",
            "k-ada-dm",
            "text",
        ),
        self_only: msg(
            arch,
            self_notes,
            src,
            run,
            self_wa,
            "2024-03-21T10:00:00Z",
            "k-self",
            "text",
        ),
        unlinked: msg(
            arch,
            unlinked_dm,
            src,
            run,
            unlinked,
            "2024-03-22T10:00:00Z",
            "k-un",
            "text",
        ),
        group_from_me: msg(
            arch,
            grp,
            src,
            run,
            self_wa,
            "2024-03-23T10:00:00Z",
            "k-grp",
            "text",
        ),
        many_peers: msg(
            arch,
            many,
            src,
            run,
            self_wa,
            "2024-03-24T10:00:00Z",
            "k-many",
            "text",
        ),
        email_from_me: msg(
            arch,
            email,
            src,
            run,
            self_mail,
            "2024-03-25T10:00:00Z",
            "k-em",
            "email",
        ),
    }
}

/// peer-from-me-dm / list-name-peer — fail today: sender Self.
#[test]
fn from_me_dm_opens_ada() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.from_me_dm).unwrap();
    assert_eq!(
        pid,
        Some(p.ada_id),
        "from-me DM person_id must be Ada, not Self (got {:?}, self={}, ada={})",
        pid,
        p.self_id,
        p.ada_id
    );
    assert_eq!(
        pname.as_deref(),
        Some("Ada"),
        "list-name is the peer display_name (Ada), not Self"
    );
    assert_ne!(pid, Some(p.self_id), "from-me DM must not open Self");
}

/// peer-from-them-dm — Ada sent still Ada.
#[test]
fn inbound_dm_stays_ada() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.from_ada_dm).unwrap();
    assert_eq!(pid, Some(p.ada_id), "inbound DM person_id stays Ada");
    assert_eq!(pname.as_deref(), Some("Ada"));
    assert_ne!(pid, Some(p.self_id), "do not remap inbound to Self");
}

/// self-only — no other live person stays Self.
#[test]
fn self_only_stays_self() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.self_only).unwrap();
    assert_eq!(pid, Some(p.self_id), "Self-only thread stays Self");
    assert_eq!(pname.as_deref(), Some("Self"));
}

/// jump-unlinked-no-person — sender has no live person → None (do not steal Ada).
#[test]
fn unlinked_sender_stays_none() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.unlinked).unwrap();
    assert_eq!(
        pid, None,
        "unlinked sender stays no person_id (do not invent Ada)"
    );
    assert_eq!(pname, None);
}

/// group-keep-sender — from-me group stays Self.
#[test]
fn group_from_me_stays_self() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, _) = search_hit_person(&arch, p.group_from_me).unwrap();
    assert_eq!(
        pid,
        Some(p.self_id),
        "group from-me stays Self (no member remap)"
    );
    assert_ne!(pid, Some(p.ada_id), "do not remap group person_id to Ada");
}

/// jump-many-peers-no-min — two live non-self persons keep sender (Self).
#[test]
fn many_peers_keeps_sender() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.many_peers).unwrap();
    assert_eq!(
        pid,
        Some(p.self_id),
        "many-peers from-me keeps sender Self (not first-live Ada/Berk)"
    );
    assert_eq!(pname.as_deref(), Some("Self"));
    assert_ne!(pid, Some(p.ada_id));
    assert_ne!(pid, Some(p.berk_id));
}

/// jump-email-thread-unique-peer — from-me email_thread with Ada → Ada.
#[test]
fn email_thread_from_me_opens_ada() {
    let root = tmp();
    let arch = init_archive(&root.join("a")).unwrap();
    let p = plant(&arch);
    let (pid, pname) = search_hit_person(&arch, p.email_from_me).unwrap();
    assert_eq!(
        pid,
        Some(p.ada_id),
        "from-me email_thread person_id must be Ada, not Self (got {:?}, self={})",
        pid,
        p.self_id
    );
    assert_eq!(pname.as_deref(), Some("Ada"));
}
