//! Native application menu (About / File / View). No website URL.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;

use interlace_core::session::{drop_recent, read_last_bookmark, read_recents};
use tauri::menu::{AboutMetadata, Menu, MenuBuilder, MenuItem, SubmenuBuilder};
use tauri::{AppHandle, Emitter};

/// About box copy: same honesty as Doctor / the cloud-path banner. No website URL.
const ABOUT_COPY: &str = "Offline. Not encrypted at rest — FileVault is your encryption.";

fn file_menu(app: &AppHandle) -> tauri::Result<tauri::menu::Submenu<tauri::Wry>> {
    let mut file = SubmenuBuilder::new(app, "File")
        .item(&MenuItem::with_id(
            app,
            "open-archive",
            "Open archive",
            true,
            Some("CmdOrCtrl+O"),
        )?)
        .text("menu-import", "Import");
    let recents = read_recents();
    if !recents.is_empty() {
        let mut recent = SubmenuBuilder::new(app, "Recent archives");
        for entry in recents.iter() {
            recent = recent.text(
                recent_menu_id(&entry.path),
                entry.display.replace('&', "&&"),
            );
        }
        file = file.separator().item(&recent.build()?);
    }
    file.build()
}

pub(crate) fn native_menu(app: &AppHandle) -> tauri::Result<Menu<tauri::Wry>> {
    let about = AboutMetadata {
        name: Some("Interlace".into()),
        copyright: Some(ABOUT_COPY.into()),
        credits: Some(ABOUT_COPY.into()),
        ..Default::default()
    };
    MenuBuilder::new(app)
        .item(
            &SubmenuBuilder::new(app, "Interlace")
                .about(Some(about))
                .separator()
                .quit()
                .build()?,
        )
        .item(&file_menu(app)?)
        .item(
            &SubmenuBuilder::new(app, "View")
                .text("view-people", "People")
                .text("view-search", "Search")
                .text("view-review", "Review")
                .text("view-doctor", "Doctor")
                .build()?,
        )
        .build()
}

pub(crate) fn rebuild_menu(app: &AppHandle) {
    if let Ok(menu) = native_menu(app) {
        let _ = app.set_menu(menu);
    }
}

fn recent_menu_id(path: &str) -> String {
    let mut hasher = DefaultHasher::new();
    path.hash(&mut hasher);
    format!("recent-{:016x}", hasher.finish())
}

/// Resolve that one bookmark and emit the path. Missing / fail: drop + rebuild.
pub(crate) fn open_recent(app: &AppHandle, id: &str) {
    let recents = read_recents();
    let Some(entry) = recents.iter().find(|e| recent_menu_id(&e.path) == id) else {
        return;
    };
    let resolved = if entry.bookmark.is_empty() {
        if entry.path.is_empty() {
            None
        } else {
            Some(PathBuf::from(&entry.path))
        }
    } else {
        crate::bookmark::resolve_security_scoped_bookmark(&entry.bookmark).ok()
    };
    let Some(path) = resolved.filter(|p| p.is_dir()) else {
        if let Some(bytes) = read_last_bookmark() {
            let _ = crate::bookmark::resolve_security_scoped_bookmark(&bytes);
        }
        let _ = drop_recent(&entry.path);
        rebuild_menu(app);
        return;
    };
    let _ = drop_recent(&entry.path);
    let _ = app.emit("menu-open-recent", path.to_string_lossy().into_owned());
}
