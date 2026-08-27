//! Import pick / plan / progress / cancel. Cooperative flag only — do not kill the thread.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread;

use interlace_core::{CoreError, ImportCancel, ImportOpts, ImporterRegistry, SourceKind};
use tauri::AppHandle;

use crate::{err, AppState, ImportProgress};

fn parse_kind(s: &str, path: &Path) -> Result<SourceKind, String> {
    match s.trim().to_ascii_lowercase().as_str() {
        "" | "auto" => ImporterRegistry::detect(path).map_err(err),
        "whatsapp" => {
            let k = ImporterRegistry::detect(path).map_err(err)?;
            if matches!(
                k,
                SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip
            ) {
                Ok(k)
            } else {
                Ok(SourceKind::WhatsappAndroidZip)
            }
        }
        "takeout" => {
            if path.is_dir() {
                Ok(SourceKind::TakeoutDir)
            } else {
                Ok(SourceKind::TakeoutZip)
            }
        }
        "gmail" => Ok(SourceKind::GmailMbox),
        "contacts" => {
            let ext = path
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_ascii_lowercase();
            if ext == "csv" {
                Ok(SourceKind::ContactsCsv)
            } else {
                Ok(SourceKind::ContactsVcf)
            }
        }
        other => Err(format!("unknown import kind {other}")),
    }
}

fn is_zip(path: &Path) -> bool {
    path.extension()
        .and_then(|s| s.to_str())
        .is_some_and(|s| s.eq_ignore_ascii_case("zip"))
}

fn list_whatsapp_zips(dir: &Path) -> Vec<PathBuf> {
    let Ok(rd) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for e in rd.flatten() {
        let p = e.path();
        if !p.is_file() || !is_zip(&p) {
            continue;
        }
        if let Ok(k) = ImporterRegistry::detect(&p) {
            if matches!(
                k,
                SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip
            ) {
                out.push(p);
            }
        }
    }
    out.sort();
    out
}

fn zip_kind(path: &Path) -> SourceKind {
    ImporterRegistry::detect(path).unwrap_or(SourceKind::WhatsappIosZip)
}

/// One or more (kind, path) jobs. A folder of WA ZIPs is the dogfood path.
fn plan_import(kind_s: &str, path: &Path) -> Result<Vec<(SourceKind, PathBuf)>, String> {
    let k = kind_s.trim().to_ascii_lowercase();
    if path.is_dir() {
        if matches!(k.as_str(), "gmail" | "contacts") {
            return Err("gmail/contacts need a file, not a folder".into());
        }
        if k == "takeout" {
            return Ok(vec![(SourceKind::TakeoutDir, path.to_path_buf())]);
        }
        if matches!(ImporterRegistry::detect(path), Ok(SourceKind::TakeoutDir))
            && matches!(k.as_str(), "" | "auto" | "takeout")
        {
            return Ok(vec![(SourceKind::TakeoutDir, path.to_path_buf())]);
        }
        let zips = list_whatsapp_zips(path);
        if !zips.is_empty() && matches!(k.as_str(), "" | "auto" | "whatsapp") {
            return Ok(zips.into_iter().map(|p| (zip_kind(&p), p)).collect());
        }
        return Err(format!(
            "folder is not a Google Takeout tree and has no WhatsApp ZIPs: {}",
            path.display()
        ));
    }
    Ok(vec![(parse_kind(&k, path)?, path.to_path_buf())])
}

fn add_stats(into: &mut interlace_core::ImportStats, add: &interlace_core::ImportStats) {
    into.inserted_messages += add.inserted_messages;
    into.skipped_dupes += add.skipped_dupes;
    into.upgraded_attachments += add.upgraded_attachments;
    into.inserted_identities += add.inserted_identities;
    into.attachments_stored += add.attachments_stored;
    into.attachments_omitted += add.attachments_omitted;
    into.attachments_missing += add.attachments_missing;
    into.warnings += add.warnings;
    into.rejected += add.rejected;
    into.auto_person_merges += add.auto_person_merges;
    into.review_enqueued += add.review_enqueued;
}

#[tauri::command]
pub(crate) fn pick_import_path(app: AppHandle, folder: bool) -> Result<Option<String>, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let picked = if folder {
            rfd::FileDialog::new()
                .set_title("Import folder (Takeout or WhatsApp ZIPs)")
                .pick_folder()
        } else {
            rfd::FileDialog::new()
                .set_title("Import file")
                .add_filter("WhatsApp / Takeout ZIP", &["zip"])
                .add_filter("Gmail mbox", &["mbox"])
                .add_filter("Contacts", &["vcf", "vcard", "csv"])
                .pick_file()
        };
        let _ = tx.send(picked);
    })
    .map_err(err)?;
    let picked = rx.recv().map_err(err)?;
    Ok(picked.map(|p| p.to_string_lossy().into_owned()))
}

#[tauri::command]
pub(crate) fn import_progress(state: tauri::State<AppState>) -> Result<ImportProgress, String> {
    Ok(state.import.lock().map_err(err)?.clone())
}

#[tauri::command]
pub(crate) fn import_cancel(state: tauri::State<AppState>) -> Result<(), String> {
    if let Some(token) = state.import_cancel.lock().map_err(err)?.as_ref() {
        token.cancel();
    }
    Ok(())
}

#[tauri::command]
pub(crate) fn import_start(
    state: tauri::State<AppState>,
    path: String,
    kind: Option<String>,
    locale: Option<String>,
) -> Result<(), String> {
    {
        let p = state.import.lock().map_err(err)?;
        if p.status == "running" {
            return Err("import already running".into());
        }
    }
    let pth = PathBuf::from(&path);
    if pth.as_os_str().is_empty() {
        return Err("import path required".into());
    }
    let jobs = plan_import(kind.as_deref().unwrap_or("auto"), &pth)?;
    if jobs.is_empty() {
        return Err("nothing to import".into());
    }
    let kind_label = if jobs.len() == 1 {
        format!("{:?}", jobs[0].0)
    } else {
        format!("{} WhatsApp ZIPs", jobs.len())
    };
    let mut slot = state.archive.lock().map_err(err)?;
    let Some(arch) = slot.take() else {
        return Err("no archive open".into());
    };
    drop(slot);
    let token = ImportCancel::new();
    *state.import_cancel.lock().map_err(err)? = Some(token.clone());
    *state.import.lock().map_err(err)? = ImportProgress {
        status: "running".into(),
        path: Some(path.clone()),
        kind: Some(kind_label.clone()),
        detail: Some(format!("0/{} starting", jobs.len())),
        error: None,
        stats: None,
    };
    let archives = Arc::clone(&state.archive);
    let progress = Arc::clone(&state.import);
    let locale = locale.and_then(|s| {
        let t = s.trim().to_string();
        if t.is_empty() {
            None
        } else {
            Some(t)
        }
    });
    thread::spawn(move || {
        let opts = ImportOpts {
            locale,
            cancel: Some(token.clone()),
            ..ImportOpts::default()
        };
        let mut arch = arch;
        let total = jobs.len();
        let mut acc = interlace_core::ImportStats::default();
        let mut failed: Option<String> = None;
        let mut interrupted = false;
        for (i, (kind_e, file)) in jobs.into_iter().enumerate() {
            if token.is_cancelled() {
                interrupted = true;
                break;
            }
            {
                let mut p = progress.lock().unwrap_or_else(|e| e.into_inner());
                let name = file
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("import");
                p.detail = Some(format!("{}/{} {}", i + 1, total, name));
                p.path = Some(file.display().to_string());
            }
            match arch.run_import(kind_e, &file, &opts) {
                Ok(s) => add_stats(&mut acc, &s),
                Err(e) => {
                    if matches!(e, CoreError::Cancelled) {
                        interrupted = true;
                    } else {
                        failed = Some(format!("{}: {e}", file.display()));
                    }
                    break;
                }
            }
        }
        {
            let mut p = progress.lock().unwrap_or_else(|e| e.into_inner());
            if interrupted {
                p.status = "interrupted".into();
                p.error = Some("import cancelled".into());
                p.stats = Some(acc);
            } else if let Some(e) = failed {
                p.status = "failed".into();
                p.error = Some(e);
                p.stats = Some(acc);
            } else {
                p.status = "done".into();
                p.error = None;
                p.stats = Some(acc);
                p.detail = Some(format!("{total}/{total} done"));
            }
        }
        *archives.lock().unwrap_or_else(|e| e.into_inner()) = Some(arch);
    });
    Ok(())
}
