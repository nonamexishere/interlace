//! Empty Phase 2 shell (UI0). No archive commands, no URL fetch.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to start Interlace");
}
