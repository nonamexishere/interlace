//! Process entry for `interlace` and `interlace-cli` (same surface).
//! Lives in the published `interlace-core` crate so bins do not depend on an
//! unpublished package at `cargo publish` time.

mod common;
mod import;
mod person;
mod review;
mod search;

use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::ExitCode;

use clap::error::ErrorKind;
use clap::{Parser, Subcommand, ValueEnum};

use crate::db::{open_archive, LockMode};
use crate::session::{init_owner_archive, write_last_path};
use crate::{AttachmentFilter, ConversationKind, Platform};

use common::{resolve_path, warn_cloud, warn_mode, CliError};
use import::cmd_import;
use person::cmd_person;
use review::cmd_review;
use search::cmd_search;

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
        /// Attachment presence: has_file | omitted | missing (empty = any)
        #[arg(long = "attachment", value_enum)]
        attachment: Option<AttachmentArg>,
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

#[derive(Clone, Copy, Debug, ValueEnum)]
enum AttachmentArg {
    #[value(name = "has_file")]
    HasFile,
    Omitted,
    Missing,
}

impl From<AttachmentArg> for AttachmentFilter {
    fn from(a: AttachmentArg) -> Self {
        match a {
            AttachmentArg::HasFile => AttachmentFilter::HasFile,
            AttachmentArg::Omitted => AttachmentFilter::Omitted,
            AttachmentArg::Missing => AttachmentFilter::Missing,
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
            attachment,
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
            attachment,
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

// keep rustc happy if stdout macros need Write in some cfgs
#[allow(dead_code)]
fn _flush() {
    let _ = io::stdout().flush();
}
