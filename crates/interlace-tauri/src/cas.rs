//! CAS protocol + in-window preview + Finder reveal. Hash only from the webview.

use std::fs;
use std::path::PathBuf;

use data_encoding::BASE64;
use tauri::http::{header, StatusCode};

use crate::{err, AppState};

pub(crate) fn sniff_mime(bytes: &[u8]) -> &'static str {
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
    if bytes.starts_with(b"%PDF") {
        return "application/pdf";
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

pub(crate) fn cas_response(
    root: Option<PathBuf>,
    uri_path: &str,
) -> tauri::http::Response<Vec<u8>> {
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

/// Inline preview for the webview (Vite `http://localhost` cannot load `cas://`).
#[tauri::command]
pub(crate) fn cas_data_url(state: tauri::State<AppState>, hash: String) -> Result<String, String> {
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

/// Reveal a local CAS blob in Finder. Hash only — never a path from the webview.
#[tauri::command]
pub(crate) fn reveal_cas(state: tauri::State<AppState>, hash: String) -> Result<(), String> {
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
    let status = std::process::Command::new("/usr/bin/open")
        .arg("-R")
        .arg(&canon)
        .status()
        .map_err(err)?;
    if !status.success() {
        return Err("could not reveal in Finder".into());
    }
    Ok(())
}

/// Reveal the open archive folder in Finder. Root from app state — never a path from the webview.
#[tauri::command]
pub(crate) fn reveal_archive(state: tauri::State<AppState>) -> Result<(), String> {
    let root = state
        .archive_root
        .lock()
        .map_err(err)?
        .clone()
        .ok_or_else(|| "no archive open".to_string())?;
    let canon = root.canonicalize().map_err(err)?;
    let status = std::process::Command::new("/usr/bin/open")
        .arg("-R")
        .arg(&canon)
        .status()
        .map_err(err)?;
    if !status.success() {
        return Err("could not reveal in Finder".into());
    }
    Ok(())
}
