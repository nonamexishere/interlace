//! Process entry for `interlace` and `interlace-cli` (same surface).
//! Lives in the published `interlace-core` crate so bins do not depend on an
//! unpublished package at `cargo publish` time.

use std::fs;
use std::io::{self, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::error::ErrorKind;
use clap::{Parser, Subcommand, ValueEnum};

use crate::db::{open_archive, LockMode};
use crate::import::ImporterRegistry;
use crate::session::{init_owner_archive, read_last_path, write_last_path};
use crate::{
    person_list, person_merge, person_timeline, person_undo, person_unlink, review_resolve,
    review_show, search, ConversationKind, CoreError, ImportOpts, ImportStats, PersonMergeOpts,
    Platform, SearchQuery, SourceKind,
};

/// Local-first archive that unifies conversations across platforms.
/// Offline. No account. No sync. Back up the archive directory.
#[derive(Parser, Debug)]
#[command(
    name = "interlace",
    version,
    about = "Local-first archive that unifies conversations across platforms",
    long_about = "Interlace is an offline, single-user archive. Import WhatsApp ZIPs and Google Takeout (Contacts + Gmail mbox), resolve people, and search locally.\n\nThe archive folder is the backup unit. Phase 1 is not encrypted at rest."
)]
struct Cli {
    /// Override last-archive-path pointer
    #[arg(long = "path", global = true, value_name = "DIR")]
    archive: Option<PathBuf>,
    /// JSON on commands that support it
    #[arg(long, global = true)]
    json: bool,
    /// Full bodies in JSON + debug logs
    #[arg(long, global = true)]
    verbose: bool,
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Create a new archive directory (mode 0700)
    Init {
        /// ISO 3166-1 alpha-2 (required; no default)
        #[arg(long = "phone-region")]
        phone_region: String,
        /// Owner display name
        #[arg(long)]
        name: Option<String>,
        /// Owner email (repeatable)
        #[arg(long = "email")]
        emails: Vec<String>,
        /// Owner phone (repeatable)
        #[arg(long = "phone")]
        phones: Vec<String>,
    },
    /// Set last-archive-path pointer (shared lock)
    Open,
    /// Counts, last import, open review rows
    Status,
    /// Import a platform export
    Import {
        #[command(subcommand)]
        source: ImportCmd,
    },
    /// Full-text search
    Search {
        query: String,
        #[arg(long)]
        person: Option<i64>,
        #[arg(long = "from")]
        from: Option<String>,
        #[arg(long = "to")]
        to: Option<String>,
        #[arg(long)]
        platform: Option<PlatArg>,
        /// Conversation kind: dm | group | email_thread (empty = any)
        #[arg(long = "kind", value_enum)]
        kind: Option<KindArg>,
        #[arg(long = "include-groups")]
        include_groups: bool,
        #[arg(long, default_value_t = 50)]
        limit: u32,
    },
    /// People graph
    Person {
        #[command(subcommand)]
        cmd: PersonCmd,
    },
    /// Merge review queue
    Review {
        #[command(subcommand)]
        cmd: ReviewCmd,
    },
    /// Integrity, FTS rebuild, CAS gc
    Doctor {
        #[arg(long = "rebuild-fts")]
        rebuild_fts: bool,
        #[arg(long = "gc-cas")]
        gc_cas: bool,
        #[arg(long)]
        integrity: bool,
    },
    /// Print logs/interlace.jsonl
    Log {
        #[arg(long)]
        tail: bool,
    },
}

#[derive(Subcommand, Debug)]
enum ImportCmd {
    /// WhatsApp Android/iOS ZIP
    Whatsapp {
        /// Export ZIP
        file: PathBuf,
        #[arg(long)]
        locale: Option<String>,
        #[arg(long)]
        resume: Option<i64>,
        #[arg(long = "conversation-name")]
        conversation_name: Option<String>,
        #[arg(long = "max-bytes", default_value_t = 60 * 1024 * 1024 * 1024)]
        max_bytes: u64,
    },
    /// Takeout directory or independent zip
    Takeout {
        /// Takeout directory or zip
        file: PathBuf,
        #[arg(long)]
        resume: Option<i64>,
        #[arg(long = "max-bytes", default_value_t = 60 * 1024 * 1024 * 1024)]
        max_bytes: u64,
    },
    /// Standalone Gmail mbox
    Gmail {
        /// Standalone .mbox
        file: PathBuf,
        #[arg(long)]
        resume: Option<i64>,
        #[arg(long = "max-bytes", default_value_t = 60 * 1024 * 1024 * 1024)]
        max_bytes: u64,
    },
    /// Contacts vCard or CSV
    Contacts {
        /// .vcf or .csv
        file: PathBuf,
    },
}

#[derive(Subcommand, Debug)]
enum PersonCmd {
    List,
    Show {
        id: i64,
        #[arg(long = "include-groups")]
        include_groups: bool,
    },
    Merge {
        a: i64,
        b: i64,
        #[arg(long)]
        keep: Option<i64>,
    },
    Unlink {
        identity: i64,
    },
    Undo {
        event: i64,
    },
}

#[derive(Subcommand, Debug)]
enum ReviewCmd {
    List,
    Show { id: i64 },
    Accept { id: i64 },
    Reject { id: i64 },
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum PlatArg {
    Whatsapp,
    Gmail,
    Contacts,
    Owner,
}

impl From<PlatArg> for Platform {
    fn from(p: PlatArg) -> Self {
        match p {
            PlatArg::Whatsapp => Platform::Whatsapp,
            PlatArg::Gmail => Platform::Gmail,
            PlatArg::Contacts => Platform::Contacts,
            PlatArg::Owner => Platform::Owner,
        }
    }
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum KindArg {
    Dm,
    Group,
    #[value(name = "email_thread")]
    EmailThread,
}

impl From<KindArg> for ConversationKind {
    fn from(k: KindArg) -> Self {
        match k {
            KindArg::Dm => ConversationKind::Dm,
            KindArg::Group => ConversationKind::Group,
            KindArg::EmailThread => ConversationKind::EmailThread,
        }
    }
}

/// Run the CLI. Both bins must stay identical (no stderr nag).
pub fn run() -> ExitCode {
    match Cli::try_parse() {
        Ok(cli) => match dispatch(cli) {
            Ok(()) => ExitCode::SUCCESS,
            Err(e) => {
                eprintln!("{e}");
                ExitCode::from(e.code())
            }
        },
        Err(e) => {
            let _ = e.print();
            match e.kind() {
                ErrorKind::DisplayHelp | ErrorKind::DisplayVersion => ExitCode::SUCCESS,
                _ => ExitCode::from(1),
            }
        }
    }
}

struct CliError {
    msg: String,
    code: u8,
}

impl CliError {
    fn user(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 1,
        }
    }
    fn fatal(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 2,
        }
    }
    fn doctor(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 3,
        }
    }
    fn code(&self) -> u8 {
        self.code
    }
}

impl std::fmt::Display for CliError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.msg)
    }
}

impl From<CoreError> for CliError {
    fn from(e: CoreError) -> Self {
        match e {
            CoreError::Lock { .. }
            | CoreError::Config(_)
            | CoreError::Probe(_)
            | CoreError::TakeoutLayout(_)
            | CoreError::Parse(_) => Self::user(e.to_string()),
            _ => Self::fatal(e.to_string()),
        }
    }
}

impl From<std::io::Error> for CliError {
    fn from(e: std::io::Error) -> Self {
        Self::fatal(e.to_string())
    }
}

impl From<rusqlite::Error> for CliError {
    fn from(e: rusqlite::Error) -> Self {
        Self::fatal(e.to_string())
    }
}

fn dispatch(cli: Cli) -> Result<(), CliError> {
    match cli.cmd {
        Commands::Init {
            phone_region,
            name,
            emails,
            phones,
        } => {
            let path = cli
                .archive
                .clone()
                .ok_or_else(|| CliError::user("init requires --path DIR"))?;
            cmd_init(path, phone_region, name, emails, phones)
        }
        Commands::Open => {
            let path = cli
                .archive
                .clone()
                .ok_or_else(|| CliError::user("open requires --path DIR"))?;
            cmd_open(path)
        }
        Commands::Status => cmd_status(cli.archive, cli.json),
        Commands::Import { source } => cmd_import(cli.archive, source),
        Commands::Search {
            query,
            person,
            from,
            to,
            platform,
            kind,
            include_groups,
            limit,
        } => cmd_search(
            cli.archive,
            cli.json,
            cli.verbose,
            query,
            person,
            from,
            to,
            platform,
            kind,
            include_groups,
            limit,
        ),
        Commands::Person { cmd } => cmd_person(cli.archive, cli.json, cli.verbose, cmd),
        Commands::Review { cmd } => cmd_review(cli.archive, cli.json, cmd),
        Commands::Doctor {
            rebuild_fts,
            gc_cas,
            integrity,
        } => cmd_doctor(cli.archive, rebuild_fts, gc_cas, integrity),
        Commands::Log { tail } => cmd_log(cli.archive, tail),
    }
}

fn cmd_init(
    path: PathBuf,
    phone_region: String,
    name: Option<String>,
    emails: Vec<String>,
    phones: Vec<String>,
) -> Result<(), CliError> {
    let arch = init_owner_archive(&path, &phone_region, name, emails, phones)?;
    let person_id: i64 = arch
        .conn
        .query_row(
            "SELECT id FROM persons WHERE is_self = 1 ORDER BY id LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap_or(1);
    println!("created archive {} (mode 0700)", path.display());
    println!("backup unit: this entire directory");
    println!("self person id={person_id}");
    println!("there is no separate `interlace backup` command in Phase 1");
    Ok(())
}

fn cmd_open(path: PathBuf) -> Result<(), CliError> {
    let arch = open_archive(&path, LockMode::Shared)?;
    warn_mode(&arch.root);
    warn_cloud(&arch.root);
    write_last_path(&path)?;
    println!("opened {}", path.display());
    Ok(())
}

fn cmd_status(path: Option<PathBuf>, json: bool) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Shared)?;
    warn_mode(&arch.root);
    let st = arch.status()?;
    if json {
        println!("{}", serde_json::to_string_pretty(&st).unwrap());
    } else {
        println!(
            "archive {}  messages={} identities={} persons_live={} review_open={}",
            st["path"].as_str().unwrap_or(""),
            st["messages"],
            st["identities"],
            st["persons_live"],
            st["review_open"]
        );
        if let Some(li) = st.get("last_import") {
            if !li.is_null() {
                println!(
                    "last import id={} status={}",
                    li["id"],
                    li["status"].as_str().unwrap_or("?")
                );
            }
        }
    }
    Ok(())
}

fn cmd_import(path: Option<PathBuf>, source: ImportCmd) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let mut arch = open_archive(&root, LockMode::Exclusive)?;
    warn_mode(&arch.root);
    let (kind, file, opts) = match source {
        ImportCmd::Whatsapp {
            file,
            locale,
            resume,
            conversation_name,
            max_bytes,
        } => {
            let probed = ImporterRegistry::detect(&file).unwrap_or(SourceKind::WhatsappAndroidZip);
            let kind = match probed {
                SourceKind::WhatsappIosZip => SourceKind::WhatsappIosZip,
                _ => SourceKind::WhatsappAndroidZip,
            };
            (
                kind,
                file,
                ImportOpts {
                    locale,
                    resume_run_id: resume,
                    conversation_name,
                    max_bytes,
                    ..ImportOpts::default()
                },
            )
        }
        ImportCmd::Takeout {
            file,
            resume,
            max_bytes,
        } => {
            let kind = if file.is_dir() {
                SourceKind::TakeoutDir
            } else {
                SourceKind::TakeoutZip
            };
            (
                kind,
                file,
                ImportOpts {
                    resume_run_id: resume,
                    max_bytes,
                    ..ImportOpts::default()
                },
            )
        }
        ImportCmd::Gmail {
            file,
            resume,
            max_bytes,
        } => (
            SourceKind::GmailMbox,
            file,
            ImportOpts {
                resume_run_id: resume,
                max_bytes,
                ..ImportOpts::default()
            },
        ),
        ImportCmd::Contacts { file } => {
            let kind = match file
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_ascii_lowercase()
                .as_str()
            {
                "csv" => SourceKind::ContactsCsv,
                _ => SourceKind::ContactsVcf,
            };
            (kind, file, ImportOpts::default())
        }
    };
    println!("probing… {kind:?}");
    let stats = arch.run_import(kind, &file, &opts)?;
    print_stats(&stats);
    if matches!(kind, SourceKind::TakeoutDir | SourceKind::TakeoutZip) {
        eprintln!(
            "warning: Phase 1 stores decoded text + attachments only. Keep your Takeout \
dump if you want bit-perfect rfc822. Deleting it cannot be undone.\n\
(--preserve-raw arrives in Phase 2, default off.)"
        );
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn cmd_search(
    path: Option<PathBuf>,
    json: bool,
    verbose: bool,
    query: String,
    person: Option<i64>,
    from: Option<String>,
    to: Option<String>,
    platform: Option<PlatArg>,
    kind: Option<KindArg>,
    include_groups: bool,
    limit: u32,
) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Shared)?;
    let q = SearchQuery {
        q: query,
        person_id: person,
        from,
        to,
        platform: platform.map(Into::into),
        conversation_id: None,
        conversation_kind: kind.map(Into::into),
        include_groups,
        limit,
    };
    let hits = search(&arch, &q)?;
    if json {
        let mut arr = Vec::new();
        for h in hits {
            let snippet = if verbose {
                h.snippet.clone()
            } else {
                "[redacted]".into()
            };
            arr.push(serde_json::json!({
                "message_id": h.message_id,
                "sent_at": h.sent_at,
                "conversation_id": h.conversation_id,
                "subject": h.subject,
                "snippet": snippet,
                "score": h.score,
            }));
        }
        println!("{}", serde_json::to_string(&arr).unwrap());
    } else {
        for h in hits {
            println!(
                "{}  conv={}  {}",
                h.message_id,
                h.conversation_id,
                h.snippet.replace('\n', " ")
            );
        }
    }
    Ok(())
}

fn cmd_person(
    path: Option<PathBuf>,
    json: bool,
    verbose: bool,
    cmd: PersonCmd,
) -> Result<(), CliError> {
    match cmd {
        PersonCmd::List => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let rows = person_list(&arch)?;
            if json {
                println!("{}", serde_json::to_string(&rows).unwrap());
            } else {
                for p in rows {
                    let act = p.last_activity_at.as_deref().unwrap_or("-");
                    let self_mark = if p.is_self { "  (self)" } else { "" };
                    println!("{}\t{}{}\t{}", p.id, p.display_name, self_mark, act);
                }
            }
        }
        PersonCmd::Show { id, include_groups } => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let name: String = arch.conn.query_row(
                "SELECT display_name FROM persons WHERE id=?1 AND tombstoned_at IS NULL",
                [id],
                |r| r.get(0),
            )?;
            let mut stmt = arch.conn.prepare(
                "SELECT i.id, i.platform, i.kind, i.value_normalized, i.display_name
                 FROM person_identities pi JOIN identities i ON i.id = pi.identity_id
                 WHERE pi.person_id = ?1",
            )?;
            let idents: Vec<serde_json::Value> = stmt
                .query_map([id], |r| {
                    Ok(serde_json::json!({
                        "id": r.get::<_, i64>(0)?,
                        "platform": r.get::<_, String>(1)?,
                        "kind": r.get::<_, String>(2)?,
                        "value": r.get::<_, String>(3)?,
                        "display_name": r.get::<_, Option<String>>(4)?,
                    }))
                })?
                .collect::<Result<Vec<_>, _>>()?;
            let tl = person_timeline(&arch, id, include_groups, 20)?;
            if json {
                let mut hits = Vec::new();
                for h in &tl {
                    hits.push(serde_json::json!({
                        "message_id": h.message_id,
                        "sent_at": h.sent_at,
                        "snippet": if verbose { &h.snippet } else { "[redacted]" },
                    }));
                }
                println!(
                    "{}",
                    serde_json::json!({
                        "id": id,
                        "display_name": name,
                        "identities": idents,
                        "timeline": hits,
                    })
                );
            } else {
                println!("person {id}  {name}");
                println!("identities: {idents:?}");
                for h in tl {
                    println!("  msg {}  {}", h.message_id, h.snippet.replace('\n', " "));
                }
            }
        }
        PersonCmd::Merge { a, b, keep } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            let survivor = person_merge(&mut arch, a, b, PersonMergeOpts { keep })?;
            let ev: i64 = arch.conn.query_row(
                "SELECT id FROM identity_link_events WHERE op='merge_persons' ORDER BY id DESC LIMIT 1",
                [],
                |r| r.get(0),
            )?;
            println!("merged → {survivor} event_id={ev}");
        }
        PersonCmd::Unlink { identity } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            person_unlink(&mut arch, identity)?;
            println!("unlinked identity {identity}");
        }
        PersonCmd::Undo { event } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            person_undo(&mut arch, event)?;
            println!("undo event {event}");
        }
    }
    Ok(())
}

fn platform_label(p: &str) -> &str {
    match p {
        "whatsapp" => "WhatsApp",
        "gmail" => "Gmail",
        "contacts" => "Contacts",
        "owner" => "Me",
        other => other,
    }
}

fn print_review_panel(label: &str, panel: &serde_json::Value) {
    let name = panel["display_name"].as_str().unwrap_or("—");
    let plats: Vec<&str> = panel["platforms"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(platform_label))
                .collect()
        })
        .unwrap_or_default();
    let title = if plats.is_empty() {
        name.to_string()
    } else {
        format!("{name} ({})", plats.join(", "))
    };
    let count = panel["message_count"].as_i64().unwrap_or(0);
    println!("{label}: {title}");
    println!(
        "  {} {}",
        count,
        if count == 1 { "message" } else { "messages" }
    );
    let samples = panel["samples"].as_array();
    if samples.map(|s| s.is_empty()).unwrap_or(true) {
        println!("  No messages on this side");
        return;
    }
    for s in samples.unwrap() {
        let at = s["sent_at"].as_str().unwrap_or("no date");
        let body = s["body_text"].as_str().unwrap_or("");
        println!("  {at} · {body}");
    }
}

fn print_review_show(out: &serde_json::Value) {
    let rev = &out["review"];
    println!(
        "id={} status={} score={} {}",
        rev["id"],
        rev["status"].as_str().unwrap_or(""),
        rev["score"],
        rev["reason"].as_str().unwrap_or("")
    );
    if let Some(ev) = out["evidence"].as_array() {
        for e in ev {
            println!(
                "  {} · {} · {}",
                e["type"].as_str().unwrap_or(""),
                e["score"],
                e["detail"].as_str().unwrap_or("")
            );
        }
    }
    let sides = out["sides"].as_array().filter(|a| !a.is_empty());
    if let Some(sides) = sides {
        for (i, panel) in sides.iter().enumerate() {
            print_review_panel(&format!("side {}", i + 1), panel);
        }
    } else {
        print_review_panel("left", &out["left"]);
        print_review_panel("right", &out["right"]);
    }
}

fn cmd_review(path: Option<PathBuf>, json: bool, cmd: ReviewCmd) -> Result<(), CliError> {
    match cmd {
        ReviewCmd::List => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let mut stmt = arch.conn.prepare(
                "SELECT id, suggested_score, reason_summary, left_identity_id, right_person_id
                 FROM merge_review_queue WHERE status='open' ORDER BY suggested_score DESC, id",
            )?;
            let rows: Vec<serde_json::Value> = stmt
                .query_map([], |r| {
                    Ok(serde_json::json!({
                        "id": r.get::<_, i64>(0)?,
                        "score": r.get::<_, f64>(1)?,
                        "reason": r.get::<_, String>(2)?,
                        "left_identity_id": r.get::<_, i64>(3)?,
                        "right_person_id": r.get::<_, Option<i64>>(4)?,
                    }))
                })?
                .collect::<Result<Vec<_>, _>>()?;
            if json {
                println!("{}", serde_json::to_string(&rows).unwrap());
            } else {
                for r in rows {
                    println!(
                        "id={} score={} {}  identity:{}  person:{:?}",
                        r["id"],
                        r["score"],
                        r["reason"].as_str().unwrap_or(""),
                        r["left_identity_id"],
                        r["right_person_id"]
                    );
                }
            }
        }
        ReviewCmd::Show { id } => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let out = review_show(&arch, id)?;
            if json {
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                print_review_show(&out);
            }
        }
        ReviewCmd::Accept { id } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            review_resolve(&mut arch, id, true)?;
            println!("accepted review {id}");
        }
        ReviewCmd::Reject { id } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            review_resolve(&mut arch, id, false)?;
            println!("status=rejected; matcher will skip this pair");
        }
    }
    Ok(())
}

fn cmd_doctor(
    path: Option<PathBuf>,
    rebuild_fts: bool,
    gc_cas: bool,
    integrity: bool,
) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Exclusive)?;
    let integrity = integrity || (!rebuild_fts && !gc_cas);
    let issues = arch.doctor_issues()?;
    arch.doctor(rebuild_fts, gc_cas, integrity)?;
    if !issues.is_empty() {
        for i in &issues {
            eprintln!("doctor: {i}");
        }
        return Err(CliError::doctor("doctor found problems"));
    }
    println!("ok");
    Ok(())
}

fn cmd_log(path: Option<PathBuf>, tail: bool) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let _arch = open_archive(&root, LockMode::Shared)?;
    let logp = root.join("logs/interlace.jsonl");
    if !logp.is_file() {
        return Ok(());
    }
    let text = fs::read_to_string(&logp)?;
    let lines: Vec<&str> = text.lines().collect();
    let slice = if tail && lines.len() > 50 {
        &lines[lines.len() - 50..]
    } else {
        &lines[..]
    };
    for l in slice {
        println!("{l}");
    }
    Ok(())
}

fn resolve_path(explicit: Option<PathBuf>) -> Result<PathBuf, CliError> {
    if let Some(p) = explicit {
        return Ok(p);
    }
    read_last_path().ok_or_else(|| {
        CliError::user("run `interlace init --path DIR --phone-region CC` or pass --path")
    })
}

fn warn_mode(root: &Path) {
    #[cfg(unix)]
    if let Ok(meta) = fs::metadata(root) {
        let mode = meta.permissions().mode() & 0o777;
        if mode & 0o077 != 0 {
            eprintln!(
                "warning: archive mode {:o} is wider than 0700; chmod 700 {}",
                mode,
                root.display()
            );
        }
    }
}

fn warn_cloud(root: &Path) {
    if let Some(w) = crate::session::cloud_warning(root) {
        eprintln!("warning: {w}");
    }
}

fn print_stats(s: &ImportStats) {
    println!(
        "inserted={} skipped_dupes={} upgraded_attachments={} identities={} attachments_stored={} warnings={} rejected={} auto_person_merges={} review_enqueued={}",
        s.inserted_messages,
        s.skipped_dupes,
        s.upgraded_attachments,
        s.inserted_identities,
        s.attachments_stored,
        s.warnings,
        s.rejected,
        s.auto_person_merges,
        s.review_enqueued
    );
}

// keep rustc happy if stdout macros need Write in some cfgs
#[allow(dead_code)]
fn _flush() {
    let _ = io::stdout().flush();
}
