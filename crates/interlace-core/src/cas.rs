//! Content-addressed blob store: `cas/ab/cd/<64 hex blake3>`.

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Component, Path, PathBuf};

use crate::db::Archive;
use crate::model::CoreError;

const MAX_BLOB: usize = 512 * 1024 * 1024;

/// BLAKE3-256 hex of decoded bytes. Writes atomically via `tmp/` then rename.
pub fn cas_put(
    archive: &Archive,
    bytes: &[u8],
    mime_hint: Option<&str>,
) -> Result<String, CoreError> {
    if bytes.len() > MAX_BLOB {
        return Err(CoreError::Fatal(format!(
            "attachment exceeds 512 MiB ({} bytes)",
            bytes.len()
        )));
    }
    let hash = blake3::hash(bytes).to_hex().to_string();
    let dest = blob_path(&archive.root, &hash)?;
    if !dest.is_file() {
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent)?;
        }
        let tmp_dir = archive.root.join("tmp");
        fs::create_dir_all(&tmp_dir)?;
        let tmp = tmp_dir.join(format!("{hash}.part"));
        {
            let mut f = OpenOptions::new()
                .create(true)
                .write(true)
                .truncate(true)
                .open(&tmp)?;
            f.write_all(bytes)?;
            f.sync_all()?;
        }
        fs::rename(&tmp, &dest)?;
    }
    archive.conn.execute(
        "INSERT INTO cas_blobs(hash, size, mime_hint, refcount)
         VALUES (?1, ?2, ?3, 0)
         ON CONFLICT(hash) DO NOTHING",
        rusqlite::params![hash, bytes.len() as i64, mime_hint],
    )?;
    Ok(hash)
}

pub fn cas_get(archive: &Archive, hash: &str) -> Result<Vec<u8>, CoreError> {
    let path = blob_path(&archive.root, hash)?;
    fs::read(&path).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            CoreError::Fatal(format!("cas blob missing: {hash}"))
        } else {
            CoreError::Io(e)
        }
    })
}

/// Delete blobs not referenced by attachments.cas_hash or contacts_raw.photo_cas_hash.
/// Returns number of files removed. Repairs cas_blobs.refcount.
pub fn gc_cas(archive: &Archive) -> Result<u64, CoreError> {
    let cas_root = archive.root.join("cas");
    if !cas_root.is_dir() {
        return Ok(0);
    }
    let mut removed = 0u64;
    for entry in walk_blobs(&cas_root)? {
        let hash = match entry.file_name().and_then(|s| s.to_str()) {
            Some(h) => h.to_string(),
            None => continue,
        };
        if parse_hash(&hash).is_err() {
            continue;
        }
        let referenced: i64 = archive.conn.query_row(
            "SELECT
                (SELECT COUNT(*) FROM attachments WHERE cas_hash = ?1)
              + (SELECT COUNT(*) FROM contacts_raw WHERE photo_cas_hash = ?1)",
            [&hash],
            |r| r.get(0),
        )?;
        if referenced == 0 {
            let _ = fs::remove_file(&entry);
            archive
                .conn
                .execute("DELETE FROM cas_blobs WHERE hash = ?1", [&hash])?;
            removed += 1;
        } else {
            archive.conn.execute(
                "UPDATE cas_blobs SET refcount = ?1 WHERE hash = ?2",
                rusqlite::params![referenced, hash],
            )?;
        }
    }
    Ok(removed)
}

pub fn validate_zip_entry_name(name: &str) -> Result<(), CoreError> {
    let n = name.replace('\\', "/");
    if n.starts_with('/') || n.starts_with('~') {
        return Err(CoreError::ZipSlip(name.into()));
    }
    if n.len() >= 2 && n.as_bytes()[1] == b':' {
        return Err(CoreError::ZipSlip(name.into()));
    }
    let path = Path::new(&n);
    if path.is_absolute() {
        return Err(CoreError::ZipSlip(name.into()));
    }
    for c in path.components() {
        match c {
            Component::ParentDir | Component::Prefix(_) | Component::RootDir => {
                return Err(CoreError::ZipSlip(name.into()));
            }
            _ => {}
        }
    }
    Ok(())
}

fn parse_hash(hash: &str) -> Result<(), CoreError> {
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(CoreError::Fatal(format!("invalid cas hash: {hash}")));
    }
    Ok(())
}

/// `$ARCHIVE/cas/ab/cd/<64 hex>`. Rejects anything that is not a blake3 hex.
pub fn cas_blob_path(root: &Path, hash: &str) -> Result<PathBuf, CoreError> {
    blob_path(root, hash)
}

fn blob_path(root: &Path, hash: &str) -> Result<PathBuf, CoreError> {
    parse_hash(hash)?;
    let a = &hash[0..2];
    let b = &hash[2..4];
    Ok(root.join("cas").join(a).join(b).join(hash))
}

fn walk_blobs(cas_root: &Path) -> Result<Vec<PathBuf>, CoreError> {
    let mut out = Vec::new();
    let l1 = match fs::read_dir(cas_root) {
        Ok(d) => d,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(out),
        Err(e) => return Err(e.into()),
    };
    for a in l1 {
        let a = a?.path();
        if !a.is_dir() {
            continue;
        }
        for b in fs::read_dir(&a)? {
            let b = b?.path();
            if !b.is_dir() {
                continue;
            }
            for f in fs::read_dir(&b)? {
                let f = f?.path();
                if f.is_file() {
                    out.push(f);
                }
            }
        }
    }
    Ok(out)
}

impl Archive {
    pub fn cas_put(&self, bytes: &[u8], mime_hint: Option<&str>) -> Result<String, CoreError> {
        cas_put(self, bytes, mime_hint)
    }

    pub fn cas_get(&self, hash: &str) -> Result<Vec<u8>, CoreError> {
        cas_get(self, hash)
    }

    pub fn gc_cas(&self) -> Result<u64, CoreError> {
        gc_cas(self)
    }
}
