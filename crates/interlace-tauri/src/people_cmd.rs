//! Person show / timeline / merge / undo IPC. `people` stays in main.rs (#265).

use interlace_core::people::{
    person_conversations, person_display_name, person_identities, person_timeline_rows_for,
    recent_link_events,
};
use interlace_core::{person_merge, person_undo, person_unlink, PersonMergeOpts};

use crate::{err, with_arch, with_arch_mut, AppState};

#[tauri::command]
pub(crate) fn person_show(
    state: tauri::State<AppState>,
    id: i64,
) -> Result<serde_json::Value, String> {
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
pub(crate) fn person_timeline(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
    limit: Option<u32>,
    before: Option<String>,
    conversation_id: Option<i64>,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let rows = person_timeline_rows_for(
            arch,
            id,
            include_groups,
            limit.unwrap_or(80),
            before.as_deref(),
            conversation_id,
        )
        .map_err(err)?;
        serde_json::to_value(rows).map_err(err)
    })
}

#[tauri::command]
pub(crate) fn person_conversations_cmd(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(person_conversations(arch, id, include_groups).map_err(err)?)
            .map_err(err)
    })
}

#[tauri::command]
pub(crate) fn person_merge_cmd(
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
pub(crate) fn person_unlink_cmd(
    state: tauri::State<AppState>,
    identity_id: i64,
) -> Result<(), String> {
    with_arch_mut(&state, |arch| person_unlink(arch, identity_id).map_err(err))
}

#[tauri::command]
pub(crate) fn person_undo_cmd(state: tauri::State<AppState>, event_id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| person_undo(arch, event_id).map_err(err))
}

#[tauri::command]
pub(crate) fn link_events(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(recent_link_events(arch, 8).map_err(err)?).map_err(err)
    })
}
