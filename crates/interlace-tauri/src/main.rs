//! UI1 session + UI3 person timeline + UI2/4/5 search, review, import.
//! No URL fetch. Paths via rfd. Last folder via security-scoped bookmark (#109).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bookmark;
mod cas;
mod import_cmd;
mod ipc;
mod menu;
mod people_cmd;
mod window_frame;

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use interlace_core::people::person_list_on;
use interlace_core::session::sandbox_denied_message;
use interlace_core::{Archive, CoreError, ImportCancel};
use rusqlite::{Connection, OpenFlags};
use tauri::{Emitter, Manager};

use crate::cas::{cas_data_url, cas_response, reveal_archive, reveal_cas};
use crate::import_cmd::{import_cancel, import_progress, import_start, pick_import_path};
use crate::ipc::{
    doctor_issues_cmd, doctor_issues_quick_cmd, doctor_run_cmd, init, open, open_url, pick_folder,
    remembered_path, review_accept_cmd, review_list_cmd, review_reject_cmd, review_show_cmd,
    search_body, search_cmd, status,
};
use crate::menu::native_menu;
use crate::people_cmd::{
    link_events, person_conversations_cmd, person_merge_cmd, person_show, person_timeline,
    person_undo_cmd, person_unlink_cmd,
};

#[derive(Clone, Default, serde::Serialize)]
pub(crate) struct ImportProgress {
    pub(crate) status: String,
    pub(crate) path: Option<String>,
    pub(crate) kind: Option<String>,
    pub(crate) detail: Option<String>,
    pub(crate) error: Option<String>,
    pub(crate) stats: Option<interlace_core::ImportStats>,
}

pub(crate) struct AppState {
    pub(crate) archive: Arc<Mutex<Option<Archive>>>,
    pub(crate) archive_root: Arc<Mutex<Option<PathBuf>>>,
    pub(crate) import: Arc<Mutex<ImportProgress>>,
    pub(crate) import_cancel: Arc<Mutex<Option<ImportCancel>>>,
}

pub(crate) fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

/// Permission denied → #137 sentence alone (no raw errno). Other errors unchanged.
pub(crate) fn err_open(e: CoreError) -> String {
    if let CoreError::Io(io) = &e {
        if let Some(msg) = sandbox_denied_message(io) {
            return msg.to_string();
        }
    }
    e.to_string()
}

pub(crate) fn map_io(e: std::io::Error) -> String {
    sandbox_denied_message(&e)
        .map(|s| s.to_string())
        .unwrap_or_else(|| e.to_string())
}

pub(crate) fn with_arch<T>(
    state: &AppState,
    f: impl FnOnce(&Archive) -> Result<T, String>,
) -> Result<T, String> {
    let guard = state.archive.lock().map_err(err)?;
    let Some(arch) = guard.as_ref() else {
        return Err("no archive open".into());
    };
    f(arch)
}

pub(crate) fn with_arch_mut<T>(
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
    // Drop the archive mutex before the heavy read; do not take() the Archive.
    let root = {
        let guard = state.archive.lock().map_err(err)?;
        let Some(arch) = guard.as_ref() else {
            return Err("no archive open".into());
        };
        arch.root.clone()
    };
    let snap = Connection::open_with_flags(
        root.join("archive.sqlite"),
        OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .map_err(err)?;
    snap.pragma_update(None, "query_only", "ON").map_err(err)?;
    snap.pragma_update(None, "temp_store", "MEMORY")
        .map_err(err)?;
    snap.pragma_update(None, "busy_timeout", 5_000i64)
        .map_err(err)?;
    let list = person_list_on(&snap).map_err(err)?;
    {
        let guard = state.archive.lock().map_err(err)?;
        let Some(arch) = guard.as_ref() else {
            return Err("no archive open".into());
        };
        if arch.root != root {
            return Err("archive changed".into());
        }
    }
    serde_json::to_value(list).map_err(err)
}

fn main() {
    let archive_root: Arc<Mutex<Option<PathBuf>>> = Arc::new(Mutex::new(None));
    let proto_root = Arc::clone(&archive_root);
    tauri::Builder::default()
        .manage(AppState {
            archive: Arc::new(Mutex::new(None)),
            archive_root: Arc::clone(&archive_root),
            import: Arc::new(Mutex::new(ImportProgress {
                status: "idle".into(),
                ..ImportProgress::default()
            })),
            import_cancel: Arc::new(Mutex::new(None)),
        })
        .menu(native_menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open-archive" => {
                let _ = app.emit("menu-open-archive", ());
            }
            "menu-import" => {
                let _ = app.emit("menu-import", ());
            }
            "view-people" => {
                let _ = app.emit("menu-view", "people");
            }
            "view-search" => {
                let _ = app.emit("menu-view", "search");
            }
            "view-review" => {
                let _ = app.emit("menu-view", "review");
            }
            "view-doctor" => {
                let _ = app.emit("menu-view", "doctor");
            }
            _ => {}
        })
        .setup(|app| {
            if let Some(win) = app.get_webview_window("main") {
                window_frame::restore_window_frame(&win);
            }
            Ok(())
        })
        .on_window_event(|window, event| match event {
            tauri::WindowEvent::Moved(_) | tauri::WindowEvent::Resized(_) => {
                window_frame::debounce_save_window_frame(window);
            }
            tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed => {
                window_frame::save_window_frame(window);
            }
            _ => {}
        })
        .register_uri_scheme_protocol("cas", move |_ctx, req| {
            let path = req.uri().path().to_string();
            let root = proto_root.lock().ok().and_then(|g| g.clone());
            cas_response(root, &path)
        })
        .invoke_handler(tauri::generate_handler![
            remembered_path,
            pick_folder,
            pick_import_path,
            init,
            open,
            status,
            doctor_issues_cmd,
            doctor_issues_quick_cmd,
            doctor_run_cmd,
            cas_data_url,
            reveal_cas,
            reveal_archive,
            open_url,
            people,
            person_show,
            person_timeline,
            person_conversations_cmd,
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
            import_progress,
            import_cancel
        ])
        .run(tauri::generate_context!())
        .expect("failed to start Interlace");
}
