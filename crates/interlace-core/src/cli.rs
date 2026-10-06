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
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::OnceLock;

use clap::error::ErrorKind;
use clap::{Parser, Subcommand, ValueEnum};

use crate::db::{open_archive, LockMode};
use crate::model::CoreError;
use crate::session::{init_owner_archive, write_last_path};
use crate::{
    ocr_image_attachments, ocr_images_enabled, set_ocr_images_enabled,
    set_voice_transcribe_enabled, transcribe_voice_notes, voice_transcribe_enabled,
    AttachmentFilter, ConversationKind, Platform,
};

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
    /// Write voice-note text into local search
    Transcribe {
        /// Turn the setting on. Does not run a pass.
        #[arg(long, conflicts_with = "off")]
        on: bool,
        /// Turn the setting off. Does not run a pass.
        #[arg(long, conflicts_with = "on")]
        off: bool,
    },
    /// Write photo text into local search
    Ocr {
        /// Turn the setting on. Does not run a pass.
        #[arg(long, conflicts_with = "off")]
        on: bool,
        /// Turn the setting off. Does not run a pass.
        #[arg(long, conflicts_with = "on")]
        off: bool,
    },
    /// Integrity, FTS rebuild, CAS gc
    Doctor {
        #[arg(long = "rebuild-fts")]
        rebuild_fts: bool,
        /// Delete unreferenced CAS files (`interlace doctor --gc-cas`)
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
        /// Store unescaped rfc822 in CAS (default off). Raw mail can add several gigabytes of disk.
        #[arg(long = "preserve-raw")]
        preserve_raw: bool,
    },
    /// Standalone Gmail mbox
    Gmail {
        /// Standalone .mbox
        file: PathBuf,
        #[arg(long)]
        resume: Option<i64>,
        #[arg(long = "max-bytes", default_value_t = 60 * 1024 * 1024 * 1024)]
        max_bytes: u64,
        /// Store unescaped rfc822 in CAS (default off). Raw mail can add several gigabytes of disk.
        #[arg(long = "preserve-raw")]
        preserve_raw: bool,
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
    Show {
        id: i64,
    },
    Accept {
        id: i64,
    },
    Reject {
        id: i64,
    },
    /// Count-only matcher diagnostics (integers; no names)
    Census,
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
        Commands::Transcribe { on, off } => cmd_transcribe(cli.archive, on, off),
        Commands::Ocr { on, off } => cmd_ocr(cli.archive, on, off),
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

pub type VoiceDecoder = fn(&[u8], &Path) -> Result<Option<String>, CoreError>;

static VOICE_DECODER: OnceLock<VoiceDecoder> = OnceLock::new();

/// Register the on-device decoder. Bins call this before [`run`].
pub fn install_voice_decoder(decoder: VoiceDecoder) {
    let _ = VOICE_DECODER.set(decoder);
}

pub fn installed_voice_decoder() -> Option<VoiceDecoder> {
    VOICE_DECODER.get().copied()
}

/// `INTERLACE_WHISPER_WEIGHTS` wins, including when that path is missing.
pub fn resolve_whisper_weights() -> PathBuf {
    if let Some(path) = std::env::var_os("INTERLACE_WHISPER_WEIGHTS") {
        return PathBuf::from(path);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for candidate in [
                dir.join("../Resources/ggml-tiny.bin"),
                dir.join("../Resources/assets/ggml-tiny.bin"),
                dir.join("ggml-tiny.bin"),
            ] {
                if candidate.is_file() {
                    return candidate;
                }
            }
            if let Some(found) = walk_assets(dir) {
                return found;
            }
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        if let Some(found) = walk_assets(&cwd) {
            return found;
        }
    }
    PathBuf::from("assets/ggml-tiny.bin")
}

fn walk_assets(start: &Path) -> Option<PathBuf> {
    let mut cur = start.to_path_buf();
    for _ in 0..8 {
        let candidate = cur.join("assets/ggml-tiny.bin");
        if candidate.is_file() {
            return Some(candidate);
        }
        if !cur.pop() {
            break;
        }
    }
    None
}

fn cmd_transcribe(path: Option<PathBuf>, on: bool, off: bool) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Exclusive)?;
    if on {
        set_voice_transcribe_enabled(&arch, true)?;
        return Ok(());
    }
    if off {
        set_voice_transcribe_enabled(&arch, false)?;
        return Ok(());
    }
    if !voice_transcribe_enabled(&arch)? {
        return Ok(());
    }
    let weights = resolve_whisper_weights();
    if !weights.is_file() {
        println!("voice weights are missing");
        return Ok(());
    }
    let decode = installed_voice_decoder()
        .ok_or_else(|| CliError::fatal("voice decoder is not installed"))?;
    transcribe_voice_notes(&arch, &weights, |bytes| decode(bytes, &weights))?;
    Ok(())
}

pub type OcrDecoder = fn(&[u8], &Path) -> Result<Option<String>, CoreError>;

static OCR_DECODER: OnceLock<OcrDecoder> = OnceLock::new();

/// Register the on-device decoder. Bins call this before [`run`].
pub fn install_ocr_decoder(decoder: OcrDecoder) {
    let _ = OCR_DECODER.set(decoder);
}

pub fn installed_ocr_decoder() -> Option<OcrDecoder> {
    OCR_DECODER.get().copied()
}

/// `INTERLACE_OCR_WEIGHTS` wins, including when that path is missing.
pub fn resolve_ocr_weights() -> PathBuf {
    if let Some(path) = std::env::var_os("INTERLACE_OCR_WEIGHTS") {
        return PathBuf::from(path);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for candidate in [
                dir.join("../Resources/tur.traineddata"),
                dir.join("../Resources/assets/tur.traineddata"),
                dir.join("tur.traineddata"),
            ] {
                if candidate.is_file() {
                    return candidate;
                }
            }
            if let Some(found) = walk_ocr_assets(dir) {
                return found;
            }
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        if let Some(found) = walk_ocr_assets(&cwd) {
            return found;
        }
    }
    PathBuf::from("assets/tur.traineddata")
}

fn walk_ocr_assets(start: &Path) -> Option<PathBuf> {
    let mut cur = start.to_path_buf();
    for _ in 0..8 {
        let candidate = cur.join("assets/tur.traineddata");
        if candidate.is_file() {
            return Some(candidate);
        }
        if !cur.pop() {
            break;
        }
    }
    None
}

fn cmd_ocr(path: Option<PathBuf>, on: bool, off: bool) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Exclusive)?;
    if on {
        set_ocr_images_enabled(&arch, true)?;
        return Ok(());
    }
    if off {
        set_ocr_images_enabled(&arch, false)?;
        return Ok(());
    }
    if !ocr_images_enabled(&arch)? {
        return Ok(());
    }
    let weights = resolve_ocr_weights();
    if !weights.is_file() {
        println!("ocr weights are missing");
        return Ok(());
    }
    let decode =
        installed_ocr_decoder().ok_or_else(|| CliError::fatal("ocr decoder is not installed"))?;
    ocr_image_attachments(&arch, &weights, |bytes| decode(bytes, &weights))?;
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
