//! UI1 session + UI3 person timeline + UI2/4/5 search, review, import.
//! No URL fetch. Paths via rfd. Last folder via security-scoped bookmark (#109).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bookmark;

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::thread;

use data_encoding::BASE64;
use interlace_core::people::{
    attachments_for, complete_attachments, person_display_name, person_identities, person_list,
    person_timeline_rows, recent_link_events,
};
use interlace_core::session::{
    init_owner_archive, read_last_bookmark, read_last_path, sandbox_denied_message,
    write_last_bookmark, write_last_path,
};
use interlace_core::{
    open_archive, person_merge, person_undo, person_unlink, review_list, review_resolve,
    review_show, search, Archive, CoreError, ImportOpts, ImporterRegistry, LockMode,
    PersonMergeOpts, Platform, SearchQuery, SourceKind,
};
use tauri::http::{header, StatusCode};
use tauri::AppHandle;

#[derive(Clone, Default, serde::Serialize)]
struct ImportProgress {
    status: String,
    path: Option<String>,
    kind: Option<String>,
    detail: Option<String>,
    error: Option<String>,
    stats: Option<interlace_core::ImportStats>,
}

struct AppState {
    archive: Arc<Mutex<Option<Archive>>>,
    archive_root: Arc<Mutex<Option<PathBuf>>>,
    import: Arc<Mutex<ImportProgress>>,
}

fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

/// Permission denied → #137 sentence alone (no raw errno). Other errors unchanged.
fn err_open(e: CoreError) -> String {
    if let CoreError::Io(io) = &e {
        if let Some(msg) = sandbox_denied_message(io) {
            return msg.to_string();
        }
    }
    e.to_string()
}

fn map_io(e: std::io::Error) -> String {
    sandbox_denied_message(&e)
        .map(|s| s.to_string())
        .unwrap_or_else(|| e.to_string())
}

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
fn persist_bookmark(path: &Path) {
    match bookmark::create_security_scoped_bookmark(path) {
        Ok(bytes) => {
            if let Err(e) = write_last_bookmark(&bytes) {
                eprintln!("interlace: write_last_bookmark failed: {e}");
            }
        }
        Err(e) => {
            eprintln!(
                "interlace: security-scoped bookmark not stored ({e}); path pointer is enough outside the sandbox"
            );
        }
    }
}

fn hold(state: &AppState, arch: Archive) -> Result<serde_json::Value, String> {
    let st = arch.status().map_err(err)?;
    *state.archive_root.lock().map_err(err)? = Some(arch.root.clone());
    *state.archive.lock().map_err(err)? = Some(arch);
    Ok(st)
}

fn sniff_mime(bytes: &[u8]) -> &'static str {
    if bytes.len() >= 3 && bytes[0] == 0xff && bytes[1] == 0xd8 && bytes[2] == 0xff {
        return "image/jpeg";
    }
    if bytes.len() >= 8 && bytes.starts_with(&[0x89, b'P', b'N', b'G']) {
        return "image/png";
    }
    if bytes.len() >= 6 && (bytes.starts_with(b"GIF87a") || bytes.starts_with(b"GIF89a")) {
        return "image/gif";
    }
    if bytes.len() >= 12 && bytes.starts_with(b"RIFF") && &bytes[8..12] == b"WEBP" {
        return "image/webp";
    }
    if bytes.len() >= 12 && bytes[4..8] == *b"ftyp" {
        return "video/mp4";
    }
    if bytes.starts_with(b"ID3") {
        return "audio/mpeg";
    }
    if bytes.len() >= 2 && bytes[0] == 0xff && bytes[1] & 0xe0 == 0xe0 {
        return "audio/mpeg";
    }
    if bytes.len() >= 4 && bytes.starts_with(b"OggS") {
        return "audio/ogg";
    }
    "application/octet-stream"
}

fn cas_response(root: Option<PathBuf>, uri_path: &str) -> tauri::http::Response<Vec<u8>> {
    let deny = |status: StatusCode, msg: &str| {
        tauri::http::Response::builder()
            .status(status)
            .header(header::CONTENT_TYPE, "text/plain; charset=utf-8")
            .body(msg.as_bytes().to_vec())
            .unwrap()
    };
    let hash = uri_path
        .trim_start_matches('/')
        .split('?')
        .next()
        .unwrap_or("");
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return deny(StatusCode::BAD_REQUEST, "invalid cas hash");
    }
    let Some(root) = root else {
        return deny(StatusCode::NOT_FOUND, "no archive open");
    };
    let Ok(path) = interlace_core::cas::cas_blob_path(&root, hash) else {
        return deny(StatusCode::BAD_REQUEST, "invalid cas hash");
    };
    let Ok(cas_root) = root.join("cas").canonicalize() else {
        return deny(StatusCode::NOT_FOUND, "cas missing");
    };
    let Ok(canon) = path.canonicalize() else {
        return deny(StatusCode::NOT_FOUND, "blob missing");
    };
    if !canon.starts_with(&cas_root) {
        return deny(StatusCode::FORBIDDEN, "path outside cas");
    }
    match fs::read(&canon) {
        Ok(bytes) => tauri::http::Response::builder()
            .status(StatusCode::OK)
            .header(header::CONTENT_TYPE, sniff_mime(&bytes))
            .header(
                header::CACHE_CONTROL,
                "private, max-age=31536000, immutable",
            )
            .body(bytes)
            .unwrap(),
        Err(_) => deny(StatusCode::NOT_FOUND, "blob missing"),
    }
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

fn is_zip(path: &Path) -> bool {
    path.extension()
        .and_then(|s| s.to_str())
        .is_some_and(|s| s.eq_ignore_ascii_case("zip"))
}

fn list_whatsapp_zips(dir: &Path) -> Vec<PathBuf> {
    let Ok(rd) = fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for e in rd.flatten() {
        let p = e.path();
        if !p.is_file() || !is_zip(&p) {
            continue;
        }
        if let Ok(k) = ImporterRegistry::detect(&p) {
            if matches!(
                k,
                SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip
            ) {
                out.push(p);
            }
        }
    }
    out.sort();
    out
}

fn zip_kind(path: &Path) -> SourceKind {
    ImporterRegistry::detect(path).unwrap_or(SourceKind::WhatsappIosZip)
}

/// One or more (kind, path) jobs. A folder of WA ZIPs is the dogfood path.
fn plan_import(kind_s: &str, path: &Path) -> Result<Vec<(SourceKind, PathBuf)>, String> {
    let k = kind_s.trim().to_ascii_lowercase();
    if path.is_dir() {
        if matches!(k.as_str(), "gmail" | "contacts") {
            return Err("gmail/contacts need a file, not a folder".into());
        }
        if k == "takeout" {
            return Ok(vec![(SourceKind::TakeoutDir, path.to_path_buf())]);
        }
        if matches!(ImporterRegistry::detect(path), Ok(SourceKind::TakeoutDir))
            && matches!(k.as_str(), "" | "auto" | "takeout")
        {
            return Ok(vec![(SourceKind::TakeoutDir, path.to_path_buf())]);
        }
        let zips = list_whatsapp_zips(path);
        if !zips.is_empty() && matches!(k.as_str(), "" | "auto" | "whatsapp") {
            return Ok(zips.into_iter().map(|p| (zip_kind(&p), p)).collect());
        }
        return Err(format!(
            "folder is not a Google Takeout tree and has no WhatsApp ZIPs: {}",
            path.display()
        ));
    }
    Ok(vec![(parse_kind(&k, path)?, path.to_path_buf())])
}

fn add_stats(into: &mut interlace_core::ImportStats, add: &interlace_core::ImportStats) {
    into.inserted_messages += add.inserted_messages;
    into.skipped_dupes += add.skipped_dupes;
    into.upgraded_attachments += add.upgraded_attachments;
    into.inserted_identities += add.inserted_identities;
    into.attachments_stored += add.attachments_stored;
    into.attachments_omitted += add.attachments_omitted;
    into.attachments_missing += add.attachments_missing;
    into.warnings += add.warnings;
    into.rejected += add.rejected;
    into.auto_person_merges += add.auto_person_merges;
    into.review_enqueued += add.review_enqueued;
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
    if let Some(bytes) = read_last_bookmark() {
        return match bookmark::resolve_security_scoped_bookmark(&bytes) {
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
                .set_title("Import folder (Takeout or WhatsApp ZIPs)")
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
    let arch = init_owner_archive(&p, &phone_region, name, emails, phones).map_err(err_open)?;
    persist_bookmark(&p);
    hold(&state, arch)
}

#[tauri::command]
fn open(state: tauri::State<AppState>, path: String) -> Result<serde_json::Value, String> {
    *state.archive.lock().map_err(err)? = None;
    let p = PathBuf::from(path);
    ensure_archive_readable(&p)?;
    let arch = open_archive(&p, LockMode::Exclusive).map_err(err_open)?;
    write_last_path(&p).map_err(err_open)?;
    persist_bookmark(&p);
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

#[tauri::command]
fn doctor_issues_cmd(state: tauri::State<AppState>) -> Result<Vec<String>, String> {
    with_arch(&state, |arch| arch.doctor_issues().map_err(err))
}

#[tauri::command]
fn doctor_run_cmd(
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

/// Inline preview for the webview (Vite `http://localhost` cannot load `cas://`).
#[tauri::command]
fn cas_data_url(state: tauri::State<AppState>, hash: String) -> Result<String, String> {
    const MAX: usize = 12 * 1024 * 1024;
    let root = state
        .archive_root
        .lock()
        .map_err(err)?
        .clone()
        .ok_or_else(|| "no archive open".to_string())?;
    let path = interlace_core::cas::cas_blob_path(&root, &hash).map_err(err)?;
    let cas_root = root.join("cas").canonicalize().map_err(err)?;
    let canon = path.canonicalize().map_err(err)?;
    if !canon.starts_with(&cas_root) {
        return Err("path outside cas".into());
    }
    let bytes = fs::read(&canon).map_err(err)?;
    if bytes.len() > MAX {
        return Err("attachment too large to preview in-window".into());
    }
    let mime = sniff_mime(&bytes);
    Ok(format!("data:{mime};base64,{}", BASE64.encode(&bytes)))
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
    let jobs = plan_import(kind.as_deref().unwrap_or("auto"), &pth)?;
    if jobs.is_empty() {
        return Err("nothing to import".into());
    }
    let kind_label = if jobs.len() == 1 {
        format!("{:?}", jobs[0].0)
    } else {
        format!("{} WhatsApp ZIPs", jobs.len())
    };
    let mut slot = state.archive.lock().map_err(err)?;
    let Some(arch) = slot.take() else {
        return Err("no archive open".into());
    };
    drop(slot);
    *state.import.lock().map_err(err)? = ImportProgress {
        status: "running".into(),
        path: Some(path.clone()),
        kind: Some(kind_label.clone()),
        detail: Some(format!("0/{} starting", jobs.len())),
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
        let total = jobs.len();
        let mut acc = interlace_core::ImportStats::default();
        let mut failed: Option<String> = None;
        for (i, (kind_e, file)) in jobs.into_iter().enumerate() {
            {
                let mut p = progress.lock().unwrap_or_else(|e| e.into_inner());
                let name = file
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("import");
                p.detail = Some(format!("{}/{} {}", i + 1, total, name));
                p.path = Some(file.display().to_string());
            }
            match arch.run_import(kind_e, &file, &opts) {
                Ok(s) => add_stats(&mut acc, &s),
                Err(e) => {
                    failed = Some(format!("{}: {e}", file.display()));
                    break;
                }
            }
        }
        {
            let mut p = progress.lock().unwrap_or_else(|e| e.into_inner());
            if let Some(e) = failed {
                p.status = "failed".into();
                p.error = Some(e);
                p.stats = Some(acc);
            } else {
                p.status = "done".into();
                p.error = None;
                p.stats = Some(acc);
                p.detail = Some(format!("{total}/{total} done"));
            }
        }
        *archives.lock().unwrap_or_else(|e| e.into_inner()) = Some(arch);
    });
    Ok(())
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
            doctor_run_cmd,
            cas_data_url,
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
