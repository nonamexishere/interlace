//! Archive open/init, doctor, search, review IPC.

use std::fs;
use std::path::{Path, PathBuf};

use interlace_core::people::{attachments_for, complete_attachments};
use interlace_core::session::{
    init_owner_archive, read_last_bookmark, read_last_path, record_recent, sandbox_denied_message,
    write_last_bookmark, write_last_path,
};
use interlace_core::{
    open_archive, review_list, review_resolve, review_resolve_selected, review_show, search,
    Archive, AttachmentFilter, ConversationKind, LockMode, Platform, SearchQuery,
};
use tauri::AppHandle;

use crate::{err, err_open, map_io, with_arch, with_arch_mut, AppState};

fn not_an_archive(p: &Path) -> String {
    format!(
        "not an Interlace archive (missing INTERLACE.toml): {}",
        p.display()
    )
}

/// Distinguish sandbox EPERM from a missing marker (`Path::is_file` swallows both).
fn ensure_archive_readable(p: &Path) -> Result<(), String> {
    if let Err(e) = fs::metadata(p) {
        if sandbox_denied_message(&e).is_some() {
            return Err(map_io(e));
        }
    }
    match fs::metadata(p.join("INTERLACE.toml")) {
        Ok(m) if m.is_file() => Ok(()),
        Err(e) => {
            if sandbox_denied_message(&e).is_some() {
                Err(map_io(e))
            } else {
                Err(not_an_archive(p))
            }
        }
        Ok(_) => Err(not_an_archive(p)),
    }
}

/// After a successful rfd pick / open we have access: store the bookmark.
/// Unsandboxed `tauri:dev` may fail create — path pointer is enough there.
fn persist_bookmark(app: &AppHandle, path: &Path) {
    let bytes = match crate::bookmark::create_security_scoped_bookmark(path) {
        Ok(bytes) => {
            if let Err(e) = write_last_bookmark(&bytes) {
                eprintln!("interlace: write_last_bookmark failed: {e}");
            }
            bytes
        }
        Err(e) => {
            eprintln!(
                "interlace: security-scoped bookmark not stored ({e}); path pointer is enough outside the sandbox"
            );
            Vec::new()
        }
    };
    if let Err(e) = record_recent(path, &bytes) {
        eprintln!("interlace: record_recent failed: {e}");
    }
    crate::menu::rebuild_menu(app);
}

fn hold(state: &AppState, arch: Archive) -> Result<serde_json::Value, String> {
    let st = arch.status().map_err(err)?;
    *state.archive_root.lock().map_err(err)? = Some(arch.root.clone());
    *state.archive.lock().map_err(err)? = Some(arch);
    Ok(st)
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

fn parse_conversation_kind(s: &str) -> Result<Option<ConversationKind>, String> {
    match s.trim().to_ascii_lowercase().as_str() {
        "" | "any" | "all" => Ok(None),
        "dm" => Ok(Some(ConversationKind::Dm)),
        "group" => Ok(Some(ConversationKind::Group)),
        "email_thread" => Ok(Some(ConversationKind::EmailThread)),
        other => Err(format!("unknown conversation kind {other}")),
    }
}

fn parse_attachment_filter(s: &str) -> Result<Option<AttachmentFilter>, String> {
    match s.trim().to_ascii_lowercase().as_str() {
        "" | "any" | "all" => Ok(None),
        "has_file" => Ok(Some(AttachmentFilter::HasFile)),
        "omitted" => Ok(Some(AttachmentFilter::Omitted)),
        "missing" => Ok(Some(AttachmentFilter::Missing)),
        other => Err(format!("unknown attachment filter {other}")),
    }
}

#[tauri::command]
pub(crate) fn remembered_path() -> Option<String> {
    if let Some(bytes) = read_last_bookmark() {
        return match crate::bookmark::resolve_security_scoped_bookmark(&bytes) {
            Ok(p) => Some(p.display().to_string()),
            Err(e) => {
                eprintln!("interlace: bookmark resolve failed ({e}); not using last_archive_path");
                None
            }
        };
    }
    // CLI-only leftover or unsandboxed dev: try the path pointer. Sandboxed .app will EPERM (#137).
    read_last_path().map(|p| p.display().to_string())
}

#[tauri::command]
pub(crate) fn pick_folder(app: AppHandle) -> Result<Option<String>, String> {
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
pub(crate) fn init(
    app: AppHandle,
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
    let arch = init_owner_archive(&p, &phone_region, name, emails, phones).map_err(err_open)?;
    let st = hold(&state, arch)?;
    persist_bookmark(&app, &p);
    Ok(st)
}

#[tauri::command]
pub(crate) fn open(
    app: AppHandle,
    state: tauri::State<AppState>,
    path: String,
) -> Result<serde_json::Value, String> {
    *state.archive.lock().map_err(err)? = None;
    let p = PathBuf::from(path);
    ensure_archive_readable(&p)?;
    let arch = open_archive(&p, LockMode::Exclusive).map_err(err_open)?;
    write_last_path(&p).map_err(err_open)?;
    let st = hold(&state, arch)?;
    persist_bookmark(&app, &p);
    Ok(st)
}

#[tauri::command]
pub(crate) fn close_archive(app: AppHandle, state: tauri::State<AppState>) -> Result<(), String> {
    let import_status = state.import.lock().map_err(err)?.status.clone();
    if import_status == "running" {
        return Err("import running".into());
    }
    *state.archive.lock().map_err(err)? = None;
    *state.archive_root.lock().map_err(err)? = None;
    crate::menu::rebuild_menu(&app);
    Ok(())
}

#[tauri::command]
pub(crate) fn status(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    let guard = state.archive.lock().map_err(err)?;
    let Some(arch) = guard.as_ref() else {
        return Err("no archive open".into());
    };
    arch.status().map_err(err)
}

#[tauri::command]
pub(crate) fn doctor_issues_cmd(state: tauri::State<AppState>) -> Result<Vec<String>, String> {
    with_arch(&state, |arch| arch.doctor_issues().map_err(err))
}

#[tauri::command]
pub(crate) fn doctor_issues_quick_cmd(
    state: tauri::State<AppState>,
) -> Result<Vec<String>, String> {
    with_arch(&state, |arch| arch.doctor_issues_quick().map_err(err))
}

#[tauri::command]
pub(crate) fn doctor_run_cmd(
    state: tauri::State<AppState>,
    integrity: bool,
    rebuild_fts: bool,
    gc_cas: bool,
) -> Result<Vec<String>, String> {
    if !integrity && !rebuild_fts && !gc_cas {
        return Err("pick integrity, rebuild FTS, or GC CAS".into());
    }
    with_arch(&state, |arch| {
        arch.doctor(rebuild_fts, gc_cas, integrity).map_err(err)?;
        arch.doctor_issues().map_err(err)
    })
}

/// Open an http(s) URL in the OS browser. Reject every other scheme.
#[tauri::command]
pub(crate) fn open_url(url: String) -> Result<(), String> {
    if !(url.starts_with("http://") || url.starts_with("https://")) {
        return Err("only http/https urls are allowed".into());
    }
    let status = std::process::Command::new("/usr/bin/open")
        .arg(&url)
        .status()
        .map_err(err)?;
    if !status.success() {
        return Err("could not open url".into());
    }
    Ok(())
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct SearchArgs {
    q: String,
    person_id: Option<i64>,
    from: Option<String>,
    to: Option<String>,
    platform: Option<String>,
    conversation_kind: Option<String>,
    attachment_filter: Option<String>,
    include_groups: bool,
    limit: Option<u32>,
}

#[tauri::command]
pub(crate) fn search_cmd(
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
            conversation_kind: parse_conversation_kind(
                args.conversation_kind.as_deref().unwrap_or(""),
            )?,
            attachment_filter: parse_attachment_filter(
                args.attachment_filter.as_deref().unwrap_or(""),
            )?,
            include_groups: args.include_groups,
            limit: args.limit.unwrap_or(50),
        };
        let hits = search(arch, &query).map_err(err)?;
        let ids: Vec<i64> = hits.iter().map(|h| h.message_id).collect();
        let atts = attachments_for(arch, &ids).map_err(err)?;
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
            let body: String = arch
                .conn
                .query_row(
                    "SELECT COALESCE(body_text, '') FROM messages WHERE id = ?1",
                    [h.message_id],
                    |r| r.get(0),
                )
                .unwrap_or_default();
            let attachments = complete_attachments(
                arch,
                h.message_id,
                &body,
                atts.get(&h.message_id).cloned().unwrap_or_default(),
            )
            .map_err(err)?;
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
                "attachments": attachments,
            }));
        }
        Ok(serde_json::Value::Array(out))
    })
}

#[tauri::command]
pub(crate) fn search_body(
    state: tauri::State<AppState>,
    message_id: i64,
) -> Result<String, String> {
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
pub(crate) fn review_list_cmd(state: tauri::State<AppState>) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| {
        serde_json::to_value(review_list(arch).map_err(err)?).map_err(err)
    })
}

#[tauri::command]
pub(crate) fn review_show_cmd(
    state: tauri::State<AppState>,
    id: i64,
) -> Result<serde_json::Value, String> {
    with_arch(&state, |arch| review_show(arch, id).map_err(err))
}

#[tauri::command]
pub(crate) fn review_accept_cmd(
    state: tauri::State<AppState>,
    id: i64,
    person_ids: Option<Vec<i64>>,
) -> Result<(), String> {
    with_arch_mut(&state, |arch| {
        match person_ids.as_deref() {
            None => review_resolve(arch, id, true),
            Some(ids) => review_resolve_selected(arch, id, true, Some(ids)),
        }
        .map_err(err)
    })
}

#[tauri::command]
pub(crate) fn review_reject_cmd(state: tauri::State<AppState>, id: i64) -> Result<(), String> {
    with_arch_mut(&state, |arch| review_resolve(arch, id, false).map_err(err))
}
