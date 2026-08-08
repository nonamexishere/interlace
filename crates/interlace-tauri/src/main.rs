//! UI1 session + UI3 person timeline. No URL fetch. Paths via rfd.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::sync::Mutex;

use interlace_core::people::{
    person_display_name, person_identities, person_list, person_timeline_rows, recent_link_events,
};
use interlace_core::session::{init_owner_archive, read_last_path, write_last_path};
use interlace_core::{
    open_archive, person_merge, person_undo, person_unlink, Archive, LockMode, PersonMergeOpts,
};
use tauri::AppHandle;

struct AppState {
    archive: Mutex<Option<Archive>>,
}

fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

fn hold(state: &AppState, arch: Archive) -> Result<serde_json::Value, String> {
    let st = arch.status().map_err(err)?;
    *state.archive.lock().map_err(err)? = Some(arch);
    Ok(st)
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

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            archive: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            remembered_path,
            pick_folder,
            init,
            open,
            status,
            people,
            person_show,
            person_timeline,
            person_merge_cmd,
            person_unlink_cmd,
            person_undo_cmd,
            link_events
        ])
        .run(tauri::generate_context!())
        .expect("failed to start Interlace");
}
