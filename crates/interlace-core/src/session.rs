//! Last-archive-path pointer + owner `init` (shared by CLI and Tauri).

use std::fs;
use std::path::{Path, PathBuf};

use crate::db::{init_archive, Archive};
use crate::import::{normalize_email, parse_phone};
use crate::model::CoreError;

pub fn config_dir() -> PathBuf {
    if let Ok(p) = std::env::var("INTERLACE_CONFIG_DIR") {
        return PathBuf::from(p);
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join("Library/Application Support/Interlace")
}

pub fn write_last_path(path: &Path) -> Result<(), CoreError> {
    let dir = config_dir();
    fs::create_dir_all(&dir)?;
    let abs = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    let body = format!(
        "last_archive_path = {}\n",
        toml::Value::String(abs.display().to_string())
    );
    fs::write(dir.join("config.toml"), body)?;
    Ok(())
}

pub fn read_last_path() -> Option<PathBuf> {
    let p = config_dir().join("config.toml");
    let text = fs::read_to_string(p).ok()?;
    let v: toml::Value = toml::from_str(&text).ok()?;
    v.get("last_archive_path")
        .and_then(|x| x.as_str())
        .map(PathBuf::from)
}

pub fn validate_phone_region(cc: &str) -> Result<String, CoreError> {
    let region = cc.trim().to_ascii_uppercase();
    if region.len() != 2 || !region.chars().all(|c| c.is_ascii_alphabetic()) {
        return Err(CoreError::Config(
            "phone-region must be ISO 3166-1 alpha-2 (e.g. TR, US)".into(),
        ));
    }
    Ok(region)
}

/// Create a new archive and declare the owner (D20 region required).
pub fn init_owner_archive(
    path: &Path,
    phone_region: &str,
    name: Option<String>,
    emails: Vec<String>,
    phones: Vec<String>,
) -> Result<Archive, CoreError> {
    let region = validate_phone_region(phone_region)?;
    if path.join("INTERLACE.toml").is_file() {
        return Err(CoreError::Config(format!(
            "already an archive: {}",
            path.display()
        )));
    }
    let arch = init_archive(path)?;
    arch.conn.execute(
        "INSERT INTO settings(key, value) VALUES ('default_phone_region', ?1)",
        [&region],
    )?;
    let display = name.clone().unwrap_or_else(|| "Me".into());
    if let Some(ref n) = name {
        arch.conn.execute(
            "UPDATE archive_meta SET owner_display_name = ?1 WHERE id = 1",
            [n],
        )?;
    }
    arch.conn.execute(
        "INSERT INTO persons(display_name, is_self) VALUES (?1, 1)",
        [&display],
    )?;
    let person_id = arch.conn.last_insert_rowid();
    for e in emails {
        let e = e.trim();
        if e.is_empty() {
            continue;
        }
        let Some(norm) = normalize_email(e) else {
            return Err(CoreError::Config(format!("invalid email {e}")));
        };
        arch.conn.execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('owner', 'email', ?1, ?2, ?3)",
            rusqlite::params![e, norm, &display],
        )?;
        let iid = arch.conn.last_insert_rowid();
        arch.conn.execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'self_declared', 1.0, 'user')",
            rusqlite::params![person_id, iid],
        )?;
        arch.conn.execute(
            "INSERT INTO self_identities(identity_id) VALUES (?1)",
            [iid],
        )?;
    }
    for p in phones {
        let p = p.trim();
        if p.is_empty() {
            continue;
        }
        let Some(e164) = parse_phone(p, Some(&region)) else {
            return Err(CoreError::Config(format!(
                "invalid phone {p} (need E.164 or national for {region})"
            )));
        };
        arch.conn.execute(
            "INSERT INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES ('owner', 'phone', ?1, ?2, ?3)",
            rusqlite::params![p, e164, &display],
        )?;
        let iid = arch.conn.last_insert_rowid();
        arch.conn.execute(
            "INSERT INTO person_identities(person_id, identity_id, link_reason, confidence, created_by)
             VALUES (?1, ?2, 'self_declared', 1.0, 'user')",
            rusqlite::params![person_id, iid],
        )?;
        arch.conn.execute(
            "INSERT INTO self_identities(identity_id) VALUES (?1)",
            [iid],
        )?;
    }
    write_last_path(path)?;
    Ok(arch)
}

pub fn cloud_warning(root: &Path) -> Option<String> {
    let s = root.to_string_lossy();
    if s.contains("Mobile Documents")
        || s.contains("iCloud Drive")
        || s.contains("Dropbox")
        || s.contains("Google Drive")
    {
        Some("archive looks like it sits on iCloud/Dropbox; see docs/user/backup.md".into())
    } else {
        None
    }
}
