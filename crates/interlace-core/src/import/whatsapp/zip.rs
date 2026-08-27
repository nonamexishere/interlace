//! ZIP listing / entry read / chat decode.

use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

use zip::ZipArchive;

use crate::cas::validate_zip_entry_name;
use crate::model::*;

pub(super) fn open_zip_cancellable(
    path: &Path,
    cancel: Option<&ImportCancel>,
) -> Result<ZipArchive<File>, CoreError> {
    if cancel.is_some_and(|c| c.is_cancelled()) {
        return Err(CoreError::Cancelled);
    }
    let Some(cancel) = cancel else {
        let f = File::open(path)?;
        return ZipArchive::new(f).map_err(|e| CoreError::Probe(format!("not a zip: {e}")));
    };
    let (tx, rx) = std::sync::mpsc::sync_channel(1);
    let path = path.to_path_buf();
    std::thread::Builder::new()
        .name("il-zip-open".into())
        .spawn(move || {
            let sent = (|| {
                let f = File::open(&path)?;
                ZipArchive::new(f).map_err(|e| CoreError::Probe(format!("not a zip: {e}")))
            })();
            let _ = tx.send(sent);
        })
        .map_err(CoreError::from)?;
    loop {
        if cancel.is_cancelled() {
            return Err(CoreError::Cancelled);
        }
        match rx.recv_timeout(std::time::Duration::from_millis(50)) {
            Ok(r) => return r,
            Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {}
            Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => {
                return Err(CoreError::Probe("zip open failed".into()));
            }
        }
    }
}

pub(super) fn list_zip(
    path: &Path,
    cancel: Option<&ImportCancel>,
) -> Result<Vec<String>, CoreError> {
    let mut zip = super::open_zip_cancellable(path, cancel)?;
    let mut names = Vec::with_capacity(zip.len());
    for i in 0..zip.len() {
        if i % 64 == 0 && cancel.is_some_and(|c| c.is_cancelled()) {
            return Err(CoreError::Cancelled);
        }
        let e = zip
            .by_index(i)
            .map_err(|e| CoreError::Parse(format!("zip index {i}: {e}")))?;
        if e.is_dir() {
            continue;
        }
        names.push(e.name().replace('\\', "/"));
    }
    Ok(names)
}

pub(super) fn find_chat_entry(names: &[String]) -> Result<(String, bool), CoreError> {
    let mut txts: Vec<String> = Vec::new();
    for n in names {
        if validate_zip_entry_name(n).is_err() {
            continue;
        }
        let file = basename(n);
        let depth = n
            .trim_matches('/')
            .split('/')
            .filter(|s| !s.is_empty())
            .count();
        if file.eq_ignore_ascii_case("_chat.txt") {
            return Ok((n.clone(), true));
        }
        if file.rsplit('.').next() == Some("txt") && depth <= 2 {
            txts.push(n.clone());
        }
    }
    match txts.len() {
        1 => Ok((txts.remove(0), false)),
        0 => Err(CoreError::Probe(
            "ZIP has no _chat.txt and no single *.txt chat".into(),
        )),
        _ => Err(CoreError::Probe(format!(
            "ambiguous WhatsApp txt entries: {}",
            txts.join(", ")
        ))),
    }
}

pub(super) fn read_zip_entry(
    path: &Path,
    name: &str,
    max_bytes: u64,
    cancel: Option<&ImportCancel>,
) -> Result<Vec<u8>, CoreError> {
    read_zip_entry_capped(path, name, max_bytes, cancel)
}

pub(super) fn read_zip_entry_capped(
    path: &Path,
    name: &str,
    max_bytes: u64,
    cancel: Option<&ImportCancel>,
) -> Result<Vec<u8>, CoreError> {
    validate_zip_entry_name(name)?;
    let mut zip = super::open_zip_cancellable(path, cancel)?;
    let mut e = zip
        .by_name(name)
        .map_err(|err| CoreError::Parse(format!("zip entry {name}: {err}")))?;
    let sz = e.size();
    if sz > max_bytes {
        return Err(CoreError::Fatal(format!(
            "zip entry {name} uncompressed {sz} exceeds cap {max_bytes}"
        )));
    }
    let mut buf = Vec::with_capacity(sz.min(max_bytes) as usize);
    let mut tmp = [0u8; 65536];
    loop {
        if cancel.is_some_and(|c| c.is_cancelled()) {
            return Err(CoreError::Cancelled);
        }
        let n = e.read(&mut tmp)?;
        if n == 0 {
            break;
        }
        if buf.len() as u64 + n as u64 > max_bytes {
            return Err(CoreError::Fatal(format!(
                "zip entry {name} read exceeds cap {max_bytes}"
            )));
        }
        buf.extend_from_slice(&tmp[..n]);
    }
    Ok(buf)
}

pub(super) fn decode_chat(bytes: &[u8]) -> (String, Vec<String>) {
    let mut notes = Vec::new();
    if bytes.starts_with(&[0xFF, 0xFE]) {
        let u16s: Vec<u16> = bytes[2..]
            .chunks(2)
            .filter_map(|c| {
                if c.len() == 2 {
                    Some(u16::from_le_bytes([c[0], c[1]]))
                } else {
                    None
                }
            })
            .collect();
        return (String::from_utf16_lossy(&u16s), notes);
    }
    let start = if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
        3
    } else {
        0
    };
    match std::str::from_utf8(&bytes[start..]) {
        Ok(s) => (s.to_string(), notes),
        Err(_) => {
            let lossy = String::from_utf8_lossy(&bytes[start..]);
            let repl = lossy
                .chars()
                .filter(|c| *c == char::REPLACEMENT_CHARACTER)
                .count();
            let total = lossy.chars().count().max(1);
            if (repl as f64) / (total as f64) > 0.02 && bytes.len() % 2 == 0 {
                let u16s: Vec<u16> = bytes
                    .chunks(2)
                    .map(|c| u16::from_le_bytes([c[0], c[1]]))
                    .collect();
                notes.push("decoded chat as UTF-16LE after high UTF-8 replacement ratio".into());
                return (String::from_utf16_lossy(&u16s), notes);
            }
            notes.push("decoded chat as UTF-8 lossy".into());
            (lossy.into_owned(), notes)
        }
    }
}

pub(super) fn basename(name: &str) -> String {
    name.replace('\\', "/")
        .rsplit('/')
        .next()
        .unwrap_or(name)
        .to_string()
}

pub(super) fn looks_like_media_name(name: &str) -> bool {
    let b = basename(name);
    b.starts_with("IMG-")
        || b.starts_with("PTT-")
        || b.starts_with("VID-")
        || b.starts_with("AUD-")
        || b.starts_with("STK-")
}

pub(super) fn attach_kind_from_name(name: &str) -> AttachmentKind {
    let b = basename(name);
    if b.starts_with("STK-") || b.to_ascii_lowercase().contains("sticker") {
        return AttachmentKind::Sticker;
    }
    if b.starts_with("PTT-") || b.starts_with("AUD-") {
        return AttachmentKind::Voice;
    }
    if b.starts_with("VID-") {
        return AttachmentKind::Video;
    }
    if b.starts_with("IMG-") {
        return AttachmentKind::Image;
    }
    let ext = PathBuf::from(&b)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    match ext.as_str() {
        "jpg" | "jpeg" | "png" | "gif" | "heic" | "webp" => AttachmentKind::Image,
        "mp4" | "mov" | "mkv" | "avi" => AttachmentKind::Video,
        "opus" | "ogg" | "mp3" | "m4a" | "wav" | "aac" => AttachmentKind::Voice,
        "vcf" | "vcard" => AttachmentKind::Vcf,
        _ => AttachmentKind::File,
    }
}

pub(super) fn mime_from_name(name: &str) -> Option<String> {
    let ext = PathBuf::from(basename(name))
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    Some(
        match ext.as_str() {
            "jpg" | "jpeg" => "image/jpeg",
            "png" => "image/png",
            "gif" => "image/gif",
            "webp" => "image/webp",
            "mp4" => "video/mp4",
            "opus" => "audio/opus",
            "ogg" => "audio/ogg",
            "vcf" => "text/vcard",
            _ => return None,
        }
        .to_string(),
    )
}
