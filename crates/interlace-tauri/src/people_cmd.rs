//! Person show / timeline / merge / undo IPC. `people` stays in main.rs (#265).

use interlace_core::people::{
    conversation_participant_names, person_conversations, person_media_rows_for,
    person_timeline_rows_for, recent_link_events,
};
use interlace_core::{
    person_merge, person_rename, person_set_notes, person_show as person_show_core, person_undo,
    person_unlink, PersonMergeOpts,
};

use crate::{err, with_arch, with_arch_mut, AppState};

#[tauri::command]
pub(crate) fn person_show(
    state: tauri::State<AppState>,
    id: i64,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let show = person_show_core(arch, id).map_err(err)?;
        Ok(serde_json::json!({
            "id": show.id,
            "display_name": show.display_name,
            "notes": show.notes,
            "identities": show.identities,
        }))
    })
}

#[tauri::command]
pub(crate) fn person_rename_cmd(
    state: tauri::State<AppState>,
    id: i64,
    name: String,
) -> Result<(), String> {
    with_arch_mut(&state, |arch| person_rename(arch, id, &name).map_err(err))
}

#[tauri::command]
pub(crate) fn person_set_notes_cmd(
    state: tauri::State<AppState>,
    id: i64,
    notes: String,
) -> Result<(), String> {
    with_arch_mut(&state, |arch| {
        person_set_notes(arch, id, &notes).map_err(err)
    })
}

#[allow(clippy::too_many_arguments)]
#[tauri::command]
pub(crate) fn person_timeline(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
    limit: Option<u32>,
    before: Option<String>,
    conversation_id: Option<i64>,
    attach_kind: Option<String>,
    after: Option<String>,
    after_id: Option<i64>,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let rows = person_timeline_rows_for(
            arch,
            id,
            include_groups,
            limit.unwrap_or(80),
            before.as_deref(),
            conversation_id,
            attach_kind.as_deref(),
            after.as_deref(),
            after_id,
        )
        .map_err(err)?;
        serde_json::to_value(rows).map_err(err)
    })
}

#[tauri::command]
pub(crate) fn person_year_counts(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let rows = interlace_core::person_year_counts(arch, id, include_groups).map_err(err)?;
        serde_json::to_value(rows).map_err(err)
    })
}

#[tauri::command]
pub(crate) fn person_media(
    state: tauri::State<AppState>,
    id: i64,
    include_groups: bool,
    limit: Option<u32>,
    before: Option<String>,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        let rows = person_media_rows_for(
            arch,
            id,
            include_groups,
            limit.unwrap_or(200),
            before.as_deref(),
        )
        .map_err(err)?;
        serde_json::to_value(rows).map_err(err)
    })
}

#[tauri::command]
pub(crate) fn conversation_participants_cmd(
    state: tauri::State<AppState>,
    conversation_id: i64,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(conversation_participant_names(arch, conversation_id).map_err(err)?)
            .map_err(err)
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
