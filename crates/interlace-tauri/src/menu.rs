//! Native application menu (About / File / View). No website URL.

use tauri::menu::{AboutMetadata, Menu, MenuBuilder, MenuItem, SubmenuBuilder};
use tauri::AppHandle;

/// About box copy: same honesty as Doctor / the cloud-path banner. No website URL.
const ABOUT_COPY: &str = "Offline. Not encrypted at rest — FileVault is your encryption.";

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
        .item(
            &SubmenuBuilder::new(app, "File")
                .item(&MenuItem::with_id(
                    app,
                    "open-archive",
                    "Open archive",
                    true,
                    Some("CmdOrCtrl+O"),
                )?)
                .text("menu-import", "Import")
                .build()?,
        )
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
