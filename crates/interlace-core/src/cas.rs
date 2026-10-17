//! Content-addressed blob store: `cas/ab/cd/<64 hex blake3>`.

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};

use rusqlite::{Connection, OptionalExtension};

use crate::db::Archive;
use crate::model::CoreError;

const MAX_BLOB: usize = 512 * 1024 * 1024;

/// Committed rename/unlink list. A settings value, not a user preference.
/// The value is a path list; it is never `work`, and the key has no `note`.
const PENDING_CAS_KEY: &str = "cas_pending_files";

pub(crate) enum PendingOp {
    Rename {
        hash: String,
        source: PathBuf,
        dest: PathBuf,
    },
    Unlink {
        hash: String,
        path: PathBuf,
    },
}

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
    let write_new = if dest.is_file() {
        match existing_blake3(&dest)? {
            Some(found) if found.eq_ignore_ascii_case(&hash) => false,
            Some(_) => {
                return Err(CoreError::Fatal(format!("cas blob bytes are not {hash}")));
            }
            None => true,
        }
    } else {
        true
    };
    if write_new {
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
    let bytes = match fs::read(&path) {
        Ok(bytes) => bytes,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Err(CoreError::Fatal(format!("cas blob missing: {hash}")));
        }
        Err(e) => return Err(CoreError::Io(e)),
    };
    if !cas_digest_matches(hash, &bytes) {
        return Err(CoreError::Fatal(format!("cas blob missing: {hash}")));
    }
    Ok(bytes)
}

pub fn cas_digest_matches(hash: &str, bytes: &[u8]) -> bool {
    blake3::hash(bytes)
        .to_hex()
        .as_str()
        .eq_ignore_ascii_case(hash)
}

pub fn cas_file_digest_matches(path: &Path, hash: &str) -> Result<bool, CoreError> {
    Ok(existing_blake3(path)?.is_some_and(|found| found.eq_ignore_ascii_case(hash)))
}

pub(crate) fn cas_reference_count(archive: &Archive, hash: &str) -> Result<i64, CoreError> {
    reference_count(&archive.conn, hash)
}

fn reference_count(conn: &Connection, hash: &str) -> Result<i64, CoreError> {
    Ok(conn.query_row(
        "SELECT
                (SELECT COUNT(*) FROM attachments WHERE cas_hash = ?1)
              + (SELECT COUNT(*) FROM attachments WHERE derivative_cas_hash = ?1)
              + (SELECT COUNT(*) FROM contacts_raw WHERE photo_cas_hash = ?1)
              + (SELECT COUNT(*) FROM messages WHERE raw_cas_hash = ?1)",
        [hash],
        |r| r.get(0),
    )?)
}

/// Delete blobs not referenced by `attachments.cas_hash`, `attachments.derivative_cas_hash`,
/// contact photos, or `messages.raw_cas_hash`.
/// Returns number of files removed. Repairs cas_blobs.refcount.
pub fn gc_cas(archive: &Archive) -> Result<u64, CoreError> {
    replay_cas_pending(&archive.conn, &archive.root)?;
    let cas_root = archive.root.join("cas");
    if !cas_root.is_dir() {
        return Ok(0);
    }
    let mut victims: Vec<(String, PathBuf)> = Vec::new();
    let mut keeps: Vec<(String, i64)> = Vec::new();
    for entry in walk_blobs(&cas_root)? {
        let hash = match entry.file_name().and_then(|s| s.to_str()) {
            Some(h) => h.to_string(),
            None => continue,
        };
        if parse_hash(&hash).is_err() {
            continue;
        }
        let referenced = cas_reference_count(archive, &hash)?;
        if referenced == 0 {
            victims.push((hash, entry));
        } else {
            keeps.push((hash, referenced));
        }
    }
    if victims.is_empty() && keeps.is_empty() {
        return Ok(0);
    }
    let ops: Vec<PendingOp> = victims
        .iter()
        .map(|(hash, path)| PendingOp::Unlink {
            hash: hash.clone(),
            path: path.clone(),
        })
        .collect();
    immediate(&archive.conn, || {
        if !ops.is_empty() {
            store_pending(&archive.conn, &archive.root, &ops)?;
            for (hash, _) in &victims {
                archive
                    .conn
                    .execute("DELETE FROM cas_blobs WHERE hash = ?1", [hash])?;
            }
        }
        for (hash, referenced) in &keeps {
            archive.conn.execute(
                "UPDATE cas_blobs SET refcount = ?1 WHERE hash = ?2",
                rusqlite::params![referenced, hash],
            )?;
        }
        Ok(())
    })?;
    if ops.is_empty() {
        return Ok(0);
    }
    replay_cas_pending(&archive.conn, &archive.root)?;
    Ok(victims.len() as u64)
}

/// Sum sizes of blobs not referenced by `attachments.cas_hash`, `attachments.derivative_cas_hash`,
/// contact photos, or raw rfc822.
/// Read-only: does not delete files or rewrite cas_blobs.
pub fn estimate_unreferenced_cas_bytes(archive: &Archive) -> Result<u64, CoreError> {
    let cas_root = archive.root.join("cas");
    if !cas_root.is_dir() {
        return Ok(0);
    }
    let mut bytes = 0u64;
    for path in walk_blobs(&cas_root)? {
        let hash = match path.file_name().and_then(|s| s.to_str()) {
            Some(h) => h.to_string(),
            None => continue,
        };
        if parse_hash(&hash).is_err() {
            continue;
        }
        let referenced = cas_reference_count(archive, &hash)?;
        if referenced == 0 {
            bytes += fs::metadata(&path)?.len();
        }
    }
    Ok(bytes)
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

fn hash_ok(hash: &str) -> bool {
    hash.len() == 64
        && hash
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}

fn canonical_rel(hash: &str) -> String {
    format!("cas/{}/{}/{}", &hash[0..2], &hash[2..4], hash)
}

fn file_blake3(path: &Path) -> Result<String, CoreError> {
    let mut file = File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}

fn existing_blake3(path: &Path) -> Result<Option<String>, CoreError> {
    match file_blake3(path) {
        Ok(hash) => Ok(Some(hash)),
        Err(CoreError::Io(e)) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e),
    }
}

fn immediate(
    conn: &Connection,
    body: impl FnOnce() -> Result<(), CoreError>,
) -> Result<(), CoreError> {
    conn.execute_batch("BEGIN IMMEDIATE")?;
    match body() {
        Ok(()) => match conn.execute_batch("COMMIT") {
            Ok(()) => Ok(()),
            Err(e) => {
                let _ = conn.execute_batch("ROLLBACK");
                Err(e.into())
            }
        },
        Err(e) => {
            let _ = conn.execute_batch("ROLLBACK");
            Err(e)
        }
    }
}

/// Relative path under `cas/`, lexical only. `..` and absolute paths are refused.
fn cas_rel(root: &Path, path: &Path) -> Result<String, CoreError> {
    let rel = path
        .strip_prefix(root)
        .map_err(|_| CoreError::Fatal("cas pending path is outside the archive".into()))?;
    let mut parts = Vec::new();
    for comp in rel.components() {
        match comp {
            Component::Normal(part) => {
                let part = part
                    .to_str()
                    .ok_or_else(|| CoreError::Fatal("cas pending path".into()))?;
                if part.is_empty()
                    || part == "."
                    || part == ".."
                    || part.contains('\t')
                    || part.contains('\n')
                    || part.contains('\r')
                {
                    return Err(CoreError::Fatal("cas pending path".into()));
                }
                parts.push(part.to_string());
            }
            _ => return Err(CoreError::Fatal("cas pending path".into())),
        }
    }
    if parts.first().map(String::as_str) != Some("cas") || parts.len() < 2 {
        return Err(CoreError::Fatal("cas pending path is outside cas".into()));
    }
    Ok(parts.join("/"))
}

fn file_name_is(rel: &str, hash: &str) -> bool {
    Path::new(rel)
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.eq_ignore_ascii_case(hash))
}

/// `None` when the path is not a real file under this archive's `cas/`.
fn resolved_cas_path(root: &Path, rel: &str) -> Option<PathBuf> {
    if rel.is_empty() || rel.contains('\0') || rel.contains('\\') {
        return None;
    }
    let rel_path = Path::new(rel);
    if rel_path.is_absolute() {
        return None;
    }
    let mut depth = 0usize;
    for comp in rel_path.components() {
        match comp {
            Component::Normal(part) => {
                let part = part.to_str()?;
                if part.is_empty() || part == "." || part == ".." {
                    return None;
                }
                if depth == 0 && part != "cas" {
                    return None;
                }
                depth += 1;
            }
            _ => return None,
        }
    }
    if depth < 2 {
        return None;
    }
    let full = root.join(rel_path);
    if !prefix_inside_cas(root, &full) {
        return None;
    }
    Some(full)
}

fn prefix_inside_cas(root: &Path, full: &Path) -> bool {
    let Ok(root_canon) = fs::canonicalize(root) else {
        return false;
    };
    let cas_lexical = root_canon.join("cas");
    let mut cursor = full.to_path_buf();
    loop {
        match fs::symlink_metadata(&cursor) {
            Ok(meta) => {
                if meta.file_type().is_symlink() {
                    return false;
                }
                let Ok(canon) = fs::canonicalize(&cursor) else {
                    return false;
                };
                if canon == root_canon {
                    return true;
                }
                return canon == cas_lexical || canon.starts_with(&cas_lexical);
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                if !cursor.pop() {
                    return false;
                }
            }
            Err(_) => return false,
        }
    }
}

pub(crate) fn store_pending(
    conn: &Connection,
    root: &Path,
    ops: &[PendingOp],
) -> Result<(), CoreError> {
    if ops.is_empty() {
        return Ok(());
    }
    let mut text = String::from("1\n");
    for op in ops {
        match op {
            PendingOp::Rename { hash, source, dest } => {
                let hash = hash.to_ascii_lowercase();
                if !hash_ok(&hash) {
                    return Err(CoreError::Fatal("cas pending hash".into()));
                }
                let source = cas_rel(root, source)?;
                let dest = cas_rel(root, dest)?;
                if dest != canonical_rel(&hash) {
                    return Err(CoreError::Fatal(
                        "cas pending rename dest is not canonical".into(),
                    ));
                }
                text.push_str(&format!("r\t{hash}\t{source}\t{dest}\n"));
            }
            PendingOp::Unlink { hash, path } => {
                let hash = hash.to_ascii_lowercase();
                if !hash_ok(&hash) {
                    return Err(CoreError::Fatal("cas pending hash".into()));
                }
                let rel = cas_rel(root, path)?;
                if !file_name_is(&rel, &hash) {
                    return Err(CoreError::Fatal(
                        "cas pending unlink name is not the hash".into(),
                    ));
                }
                text.push_str(&format!("u\t{hash}\t{rel}\n"));
            }
        }
    }
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        rusqlite::params![PENDING_CAS_KEY, text],
    )?;
    Ok(())
}

enum ParsedOp {
    Rename {
        hash: String,
        source: String,
        dest: String,
    },
    Unlink {
        hash: String,
        path: String,
    },
}

fn parse_pending(text: &str) -> Result<Vec<ParsedOp>, CoreError> {
    let mut lines = text.split('\n');
    if lines.next().unwrap_or("") != "1" {
        return Err(CoreError::Fatal(
            "cas pending record is not version 1".into(),
        ));
    }
    let mut ops = Vec::new();
    for line in lines {
        if line.is_empty() {
            continue;
        }
        let mut parts = line.split('\t');
        match parts.next() {
            Some("r") => {
                let hash = parts
                    .next()
                    .ok_or_else(|| CoreError::Fatal("cas pending record".into()))?
                    .to_string();
                let source = parts
                    .next()
                    .ok_or_else(|| CoreError::Fatal("cas pending record".into()))?
                    .to_string();
                let dest = parts
                    .next()
                    .ok_or_else(|| CoreError::Fatal("cas pending record".into()))?
                    .to_string();
                if parts.next().is_some() {
                    return Err(CoreError::Fatal("cas pending record".into()));
                }
                ops.push(ParsedOp::Rename { hash, source, dest });
            }
            Some("u") => {
                let hash = parts
                    .next()
                    .ok_or_else(|| CoreError::Fatal("cas pending record".into()))?
                    .to_string();
                let path = parts
                    .next()
                    .ok_or_else(|| CoreError::Fatal("cas pending record".into()))?
                    .to_string();
                if parts.next().is_some() {
                    return Err(CoreError::Fatal("cas pending record".into()));
                }
                ops.push(ParsedOp::Unlink { hash, path });
            }
            _ => return Err(CoreError::Fatal("cas pending record".into())),
        }
    }
    Ok(ops)
}

/// Finish a committed file list, then drop unreferenced `cas_blobs` rows whose
/// canonical file is already gone. Does not scan `cas/` for a substitute.
pub(crate) fn replay_cas_pending(conn: &Connection, root: &Path) -> Result<(), CoreError> {
    let value: Option<String> = conn
        .query_row(
            "SELECT value FROM settings WHERE key = ?1",
            [PENDING_CAS_KEY],
            |row| row.get(0),
        )
        .optional()?;
    if let Some(value) = value {
        if let Ok(ops) = parse_pending(&value) {
            let mut restores = Vec::new();
            let mut renamed = Vec::new();
            for op in ops {
                match op {
                    ParsedOp::Rename { hash, source, dest } => {
                        if !hash_ok(&hash) || dest != canonical_rel(&hash) {
                            continue;
                        }
                        let Some(source_path) = resolved_cas_path(root, &source) else {
                            continue;
                        };
                        let Some(dest_path) = resolved_cas_path(root, &dest) else {
                            continue;
                        };
                        finish_rename(&hash, &source_path, &dest_path)?;
                        renamed.push(dest_path);
                    }
                    ParsedOp::Unlink { hash, path } => {
                        if !hash_ok(&hash) || !file_name_is(&path, &hash) {
                            continue;
                        }
                        let Some(full) = resolved_cas_path(root, &path) else {
                            continue;
                        };
                        if renamed.iter().any(|dest| dest == &full) {
                            continue;
                        }
                        if let Some(row) = finish_unlink(&hash, &full)? {
                            restores.push(row);
                        }
                    }
                }
            }
            immediate(conn, || {
                for (hash, size) in &restores {
                    conn.execute(
                        "INSERT INTO cas_blobs(hash, size, mime_hint, refcount)
                         VALUES (?1, ?2, NULL, 0)
                         ON CONFLICT(hash) DO NOTHING",
                        rusqlite::params![hash, size],
                    )?;
                }
                conn.execute("DELETE FROM settings WHERE key = ?1", [PENDING_CAS_KEY])?;
                Ok(())
            })?;
        }
    }
    sweep_missing_unreferenced(conn, root)
}

fn finish_rename(hash: &str, source: &Path, dest: &Path) -> Result<(), CoreError> {
    if source == dest {
        return Ok(());
    }
    let dest_digest = existing_blake3(dest)?;
    if dest_digest.as_deref().is_some_and(|digest| digest != hash) {
        return Ok(());
    }
    let source_digest = existing_blake3(source)?;
    let dest_ok = dest_digest.is_none() || dest_digest.as_deref() == Some(hash);
    if source_digest.as_deref() == Some(hash) && dest_ok {
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent)?;
        }
        match fs::rename(source, dest) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(e.into()),
        }
    } else {
        Ok(())
    }
}

/// `Some` only when the unlink failed and the bytes still match `hash`.
fn finish_unlink(hash: &str, path: &Path) -> Result<Option<(String, i64)>, CoreError> {
    if !path.exists() {
        return Ok(None);
    }
    let digest = existing_blake3(path)?;
    match fs::remove_file(path) {
        Ok(()) => Ok(None),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => {
            if digest.as_deref() == Some(hash) {
                let size = path.metadata()?.len() as i64;
                Ok(Some((hash.to_string(), size)))
            } else {
                Err(e.into())
            }
        }
    }
}

fn sweep_missing_unreferenced(conn: &Connection, root: &Path) -> Result<(), CoreError> {
    let gone = {
        let mut stmt = conn.prepare("SELECT hash FROM cas_blobs")?;
        let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
        let mut gone = Vec::new();
        for row in rows {
            let hash = row?;
            if !hash_ok(&hash) {
                continue;
            }
            let path = blob_path(root, &hash)?;
            if path.is_file() {
                continue;
            }
            if reference_count(conn, &hash)? == 0 {
                gone.push(hash);
            }
        }
        gone
    };
    if gone.is_empty() {
        return Ok(());
    }
    immediate(conn, || {
        for hash in &gone {
            let path = blob_path(root, hash)?;
            if path.is_file() || reference_count(conn, hash)? != 0 {
                continue;
            }
            conn.execute("DELETE FROM cas_blobs WHERE hash = ?1", [hash])?;
        }
        Ok(())
    })
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

    pub fn estimate_unreferenced_cas_bytes(&self) -> Result<u64, CoreError> {
        estimate_unreferenced_cas_bytes(self)
    }
}
