//! UI1 session + UI3 person timeline + UI2/4/5 search, review, import.
//! No URL fetch. Paths via rfd.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::thread;

use interlace_core::people::{
    person_display_name, person_identities, person_list, person_timeline_rows, recent_link_events,
};
use interlace_core::session::{init_owner_archive, read_last_path, write_last_path};
use interlace_core::{
    open_archive, person_merge, person_undo, person_unlink, review_list, review_resolve,
    review_show, search, Archive, ImportOpts, ImporterRegistry, LockMode, PersonMergeOpts,
    Platform, SearchQuery, SourceKind,
};
use tauri::AppHandle;

#[derive(Clone, Default, serde::Serialize)]
struct ImportProgress {
    status: String,
    path: Option<String>,
    kind: Option<String>,
    error: Option<String>,
    stats: Option<interlace_core::ImportStats>,
}

struct AppState {
    archive: Arc<Mutex<Option<Archive>>>,
    import: Arc<Mutex<ImportProgress>>,
}

fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

fn hold(state: &AppState, arch: Archive) -> Result<serde_json::Value, String> {
    let st = arch.status().map_err(err)?;
    *state.archive.lock().map_err(err)? = Some(arch);
    Ok(st)
}

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

fn parse_platform(s: &str) -> Result<Option<Platform>, String> {
    match s.trim().to_ascii_lowercase().as_str() {
        "" | "any" => Ok(None),
        "whatsapp" => Ok(Some(Platform::Whatsapp)),
        "gmail" => Ok(Some(Platform::Gmail)),
        "contacts" => Ok(Some(Platform::Contacts)),
        other => Err(format!("unknown platform {other}")),
    }
}

#[tauri::command]
fn remembered_path() -> Option<String> {
    read_last_path().map(|p| p.display().to_string())
}

#[tauri::command]
fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let picked = rfd::FileDialog::new()
            .set_title("Interlace archive folder")
            .pick_folder();
        let _ = tx.send(picked);
    })
    .map_err(err)?;
    let picked = rx.recv().map_err(err)?;
    Ok(picked.map(|p| p.to_string_lossy().into_owned()))
}

#[tauri::command]
fn pick_import_path(app: AppHandle, folder: bool) -> Result<Option<String>, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let picked = if folder {
            rfd::FileDialog::new()
                .set_title("Takeout folder")
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
fn init(
    state: tauri::State<AppState>,
    path: String,
    phone_region: String,
    name: Option<String>,
    emails: Vec<String>,
    phones: Vec<String>,
) -> Result<serde_json::Value, String> {
    *state.archive.lock().map_err(err)? = None;
    let p = PathBuf::from(path);
    if p.as_os_str().is_empty() {
        return Err("init requires a folder".into());
    }
    let arch = init_owner_archive(&p, &phone_region, name, emails, phones).map_err(err)?;
    hold(&state, arch)
}

#[tauri::command]
fn open(state: tauri::State<AppState>, path: String) -> Result<serde_json::Value, String> {
    *state.archive.lock().map_err(err)? = None;
    let p = PathBuf::from(path);
    if !p.join("INTERLACE.toml").is_file() {
        return Err(format!(
            "not an Interlace archive (missing INTERLACE.toml): {}",
            p.display()
        ));
    }
    let arch = open_archive(&p, LockMode::Exclusive).map_err(err)?;
    write_last_path(&p).map_err(err)?;
    hold(&state, arch)
}

#[tauri::command]
fn status(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    let guard = state.archive.lock().map_err(err)?;
    let Some(arch) = guard.as_ref() else {
        return Err("no archive open".into());
    };
    arch.status().map_err(err)
}

fn with_arch<T>(
    state: &AppState,
    f: impl FnOnce(&Archive) -> Result<T, String>,
) -> Result<T, String> {
    let guard = state.archive.lock().map_err(err)?;
    let Some(arch) = guard.as_ref() else {
        return Err("no archive open".into());
    };
    f(arch)
}

fn with_arch_mut<T>(
    state: &AppState,
    f: impl FnOnce(&mut Archive) -> Result<T, String>,
) -> Result<T, String> {
    let mut guard = state.archive.lock().map_err(err)?;
    let Some(arch) = guard.as_mut() else {
        return Err("no archive open".into());
    };
    f(arch)
}

#[tauri::command]
fn people(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(person_list(arch).map_err(err)?).map_err(err)
    })
}

#[tauri::command]
fn person_show(state: tauri::State<AppState>, id: i64) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let name = person_display_name(arch, id).map_err(err)?;
        let identities = person_identities(arch, id).map_err(err)?;
        Ok(serde_json::json!({
            "id": id,
            "display_name": name,
            "identities": identities,
        }))
    })
}

#[tauri::command]
fn person_timeline(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
    limit: Option<u32>,
    before: Option<String>,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let rows = person_timeline_rows(
            arch,
            id,
            include_groups,
            limit.unwrap_or(80),
            before.as_deref(),
        )
        .map_err(err)?;
        serde_json::to_value(rows).map_err(err)
    })
}

#[tauri::command]
fn person_merge_cmd(
    state: tauri::State<AppState>,
    a: i64,
    b: i64,
    keep: Option<i64>,
) -> Result<serde_json::Value, String> {
    with_arch_mut(&state, |arch| {
        let survivor = person_merge(arch, a, b, PersonMergeOpts { keep }).map_err(err)?;
        let ev: i64 = arch
            .conn
            .query_row(
                "SELECT id FROM identity_link_events WHERE op='merge_persons' ORDER BY id DESC LIMIT 1",
                [],
                |r| r.get(0),
            )
            .map_err(err)?;
        Ok(serde_json::json!({"survivor": survivor, "event_id": ev}))
    })
}

#[tauri::command]
fn person_unlink_cmd(state: tauri::State<AppState>, identity_id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| person_unlink(arch, identity_id).map_err(err))
}

#[tauri::command]
fn person_undo_cmd(state: tauri::State<AppState>, event_id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| person_undo(arch, event_id).map_err(err))
}

#[tauri::command]
fn link_events(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(recent_link_events(arch, 8).map_err(err)?).map_err(err)
    })
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct SearchArgs {
    q: String,
    person_id: Option<i64>,
    from: Option<String>,
    to: Option<String>,
    platform: Option<String>,
    include_groups: bool,
    limit: Option<u32>,
}

#[tauri::command]
fn search_cmd(
    state: tauri::State<AppState>,
    args: SearchArgs,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let query = SearchQuery {
            q: args.q,
            person_id: args.person_id,
            from: args.from,
            to: args.to,
            platform: parse_platform(args.platform.as_deref().unwrap_or(""))?,
            conversation_id: None,
            include_groups: args.include_groups,
            limit: args.limit.unwrap_or(50),
        };
        let hits = search(arch, &query).map_err(err)?;
        let mut out = Vec::new();
        for h in hits {
            let meta: (String, String, Option<String>, Option<i64>, Option<String>) = arch
                .conn
                .query_row(
                    "SELECT c.platform, c.kind, c.title,
                            (SELECT p.id FROM person_identities pi
                             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
                             WHERE pi.identity_id = m.sender_identity_id LIMIT 1),
                            (SELECT p.display_name FROM person_identities pi
                             JOIN persons p ON p.id = pi.person_id AND p.tombstoned_at IS NULL
                             WHERE pi.identity_id = m.sender_identity_id LIMIT 1)
                     FROM messages m
                     JOIN conversations c ON c.id = m.conversation_id
                     WHERE m.id = ?1",
                    [h.message_id],
                    |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
                )
                .unwrap_or_else(|_| ("unknown".into(), "dm".into(), None, None, None));
            out.push(serde_json::json!({
                "message_id": h.message_id,
                "sent_at": h.sent_at,
                "conversation_id": h.conversation_id,
                "subject": h.subject,
                "snippet": h.snippet,
                "score": h.score,
                "platform": meta.0,
                "conversation_kind": meta.1,
                "conversation_title": meta.2,
                "person_id": meta.3,
                "person_name": meta.4,
            }));
        }
        Ok(serde_json::Value::Array(out))
    })
}

#[tauri::command]
fn search_body(state: tauri::State<AppState>, message_id: i64) -> Result<String, String> {
    with_arch(&state, |arch| {
        arch.conn
            .query_row(
                "SELECT COALESCE(body_text, '') FROM messages WHERE id = ?1",
                [message_id],
                |r| r.get(0),
            )
            .map_err(err)
    })
}

#[tauri::command]
fn review_list_cmd(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(review_list(arch).map_err(err)?).map_err(err)
    })
}

#[tauri::command]
fn review_show_cmd(state: tauri::State<AppState>, id: i64) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| review_show(arch, id).map_err(err))
}

#[tauri::command]
fn review_accept_cmd(state: tauri::State<AppState>, id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| review_resolve(arch, id, true).map_err(err))
}

#[tauri::command]
fn review_reject_cmd(state: tauri::State<AppState>, id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| review_resolve(arch, id, false).map_err(err))
}

#[tauri::command]
fn import_progress(state: tauri::State<AppState>) -> Result<ImportProgress, String> {
    Ok(state.import.lock().map_err(err)?.clone())
}

#[tauri::command]
fn import_start(
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
    let kind_e = parse_kind(kind.as_deref().unwrap_or("auto"), &pth)?;
    let kind_label = format!("{kind_e:?}");
    let mut slot = state.archive.lock().map_err(err)?;
    let Some(arch) = slot.take() else {
        return Err("no archive open".into());
    };
    drop(slot);
    *state.import.lock().map_err(err)? = ImportProgress {
        status: "running".into(),
        path: Some(path.clone()),
        kind: Some(kind_label.clone()),
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
            ..ImportOpts::default()
        };
        let mut arch = arch;
        let res = arch.run_import(kind_e, &pth, &opts);
        {
            let mut p = progress.lock().unwrap_or_else(|e| e.into_inner());
            match res {
                Ok(stats) => {
                    p.status = "done".into();
                    p.stats = Some(stats);
                    p.error = None;
                }
                Err(e) => {
                    p.status = "failed".into();
                    p.error = Some(e.to_string());
                }
            }
        }
        *archives.lock().unwrap_or_else(|e| e.into_inner()) = Some(arch);
    });
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            archive: Arc::new(Mutex::new(None)),
            import: Arc::new(Mutex::new(ImportProgress {
                status: "idle".into(),
                ..ImportProgress::default()
            })),
        })
        .invoke_handler(tauri::generate_handler![
            remembered_path,
            pick_folder,
            pick_import_path,
            init,
            open,
            status,
            people,
            person_show,
            person_timeline,
            person_merge_cmd,
            person_unlink_cmd,
            person_undo_cmd,
            link_events,
            search_cmd,
            search_body,
            review_list_cmd,
            review_show_cmd,
            review_accept_cmd,
            review_reject_cmd,
            import_start,
            import_progress
        ])
        .run(tauri::generate_context!())
        .expect("failed to start Interlace");
}
