//! UI1: archive session (init / open / status). No URL fetch. Paths via rfd.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::sync::Mutex;

use interlace_core::session::{init_owner_archive, read_last_path, write_last_path};
use interlace_core::{open_archive, Archive, LockMode};
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
            status
        ])
        .run(tauri::generate_context!())
        .expect("failed to start Interlace");
}
