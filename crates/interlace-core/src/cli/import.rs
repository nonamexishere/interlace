use std::path::PathBuf;

use crate::db::{open_archive, LockMode};
use crate::import::ImporterRegistry;
use crate::model::{ImportOpts, ImportStats, SourceKind};

use super::common::{resolve_path, warn_mode, CliError};
use super::ImportCmd;

pub(super) fn cmd_import(path: Option<PathBuf>, source: ImportCmd) -> Result<(), CliError> {
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
