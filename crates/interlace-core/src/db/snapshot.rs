//! Point-in-time copies under `snapshots/<id>/`. The live WAL is not checkpointed.

use std::fs;
use std::io::ErrorKind;
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use rusqlite::backup::{Backup, StepResult};
use rusqlite::{Connection, OpenFlags};

use super::lock::LockMode;
use super::open::{open_archive, Archive};
use super::Result;
use crate::model::CoreError;

static ID_SEQ: AtomicU64 = AtomicU64::new(1);
static STAGE_SEQ: AtomicU64 = AtomicU64::new(1);

const BUSY_TRIES: u32 = 80;

/// Copy committed pages, `INTERLACE.toml`, and `cas/` into `snapshots/<id>/`.
/// Returns the directory name, not a filesystem path.
pub fn snapshot_archive(archive: &Archive) -> Result<String> {
    let (id, dir) = allocate_snapshot_dir(&archive.root)?;
    let mut guard = DirGuard::arm(dir);
    write_snapshot(&archive.root, guard.path())?;
    guard.disarm();
    Ok(id)
}

/// Directory names under `snapshots/`, lexicographic descending. Missing dir is empty.
pub fn list_snapshots(root: &Path) -> Result<Vec<String>> {
    let dir = root.join("snapshots");
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut ids = Vec::new();
    for ent in fs::read_dir(&dir)? {
        let ent = ent?;
        if !ent.file_type()?.is_dir() {
            continue;
        }
        if let Ok(name) = ent.file_name().into_string() {
            ids.push(name);
        }
    }
    ids.sort_by(|a, b| b.cmp(a));
    Ok(ids)
}

/// Replace live toml, sqlite, and `cas/` with snapshot `id` on the held archive.
pub fn restore_snapshot(archive: &mut Archive, id: &str) -> Result<()> {
    if !snapshot_id_ok(id) {
        return Err(missing_err(id));
    }
    let snap = archive.root.join("snapshots").join(id);
    let snaps = archive.root.join("snapshots");
    match fs::symlink_metadata(&snap) {
        Ok(meta) if meta.is_dir() && snap.parent() == Some(snaps.as_path()) => {}
        _ => return Err(missing_err(id)),
    }
    verify_manifest(&snap)?;

    let stage = archive.root.join("tmp").join(format!(
        "snap-stage-{}-{}",
        std::process::id(),
        STAGE_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    let _stage_guard = DirGuard::arm(stage.clone());
    stage_from_snapshot(&snap, &stage)?;
    verify_manifest(&stage)?;

    let mut suspended = false;
    let installed = (|| -> Result<()> {
        archive.suspend_conn()?;
        suspended = true;
        install_staged(&archive.root, &stage)?;
        Ok(())
    })();
    if let Err(e) = installed {
        if suspended {
            // Resume must not replace the install error.
            let _ = archive.resume_conn();
        }
        return Err(e);
    }
    archive.resume_conn()
}

/// `open_archive` exclusive, then [`restore_snapshot`]. Lock failure renames nothing.
pub fn restore_snapshot_at(root: &Path, id: &str) -> Result<()> {
    let mut archive = open_archive(root, LockMode::Exclusive)?;
    restore_snapshot(&mut archive, id)
}

fn write_snapshot(root: &Path, dir: &Path) -> Result<()> {
    copy_database(&root.join("archive.sqlite"), &dir.join("archive.sqlite"))?;
    fs::copy(root.join("INTERLACE.toml"), dir.join("INTERLACE.toml"))?;
    mirror_tree(&root.join("cas"), &dir.join("cas"), true)?;
    remove_sidecars(&dir.join("archive.sqlite"))?;
    write_manifest(dir)?;
    Ok(())
}

fn copy_database(src: &Path, dst: &Path) -> Result<()> {
    if src == dst {
        return Err(CoreError::Fatal("snapshot backup: same path".into()));
    }
    match backup_once(src, dst, true) {
        Ok(()) => Ok(()),
        Err(_) => {
            remove_sqlite_family(dst);
            backup_once(src, dst, false)
        }
    }
}

fn backup_once(src_path: &Path, dst_path: &Path, query_only: bool) -> Result<()> {
    let src = Connection::open_with_flags(src_path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    // This connection must not auto-checkpoint the live WAL. The archive
    // connection stays open, so this close is not last-close either.
    let _ = src.set_db_config(
        rusqlite::config::DbConfig::SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,
        true,
    );
    src.pragma_update(None, "wal_autocheckpoint", 0i64)?;
    src.pragma_update(None, "busy_timeout", 5_000i64)?;
    if query_only {
        src.pragma_update(None, "query_only", "ON")?;
    }

    let mut dst = Connection::open(dst_path)?;
    {
        let backup = Backup::new(&src, &mut dst)?;
        let mut busy = 0u32;
        let mut more = 0u32;
        loop {
            // Busy and Locked are Ok variants. step(-1) copies every remaining page.
            match backup.step(-1)? {
                StepResult::Done => break,
                StepResult::More => {
                    more += 1;
                    if more > 10_000 {
                        return Err(CoreError::Fatal("snapshot backup did not finish".into()));
                    }
                }
                StepResult::Busy | StepResult::Locked => {
                    busy += 1;
                    if busy >= BUSY_TRIES {
                        return Err(CoreError::Fatal("snapshot backup busy".into()));
                    }
                    thread::sleep(Duration::from_millis(10));
                }
                _ => {
                    return Err(CoreError::Fatal("snapshot backup: unexpected step".into()));
                }
            }
        }
    }
    seal_destination(&dst)?;
    drop(dst);
    drop(src);
    remove_sidecars(dst_path)?;
    Ok(())
}

fn seal_destination(dst: &Connection) -> Result<()> {
    let _: i64 = dst.query_row("PRAGMA wal_checkpoint(TRUNCATE)", [], |row| row.get(0))?;
    let mode: String = dst.query_row("PRAGMA journal_mode=DELETE", [], |row| row.get(0))?;
    if !mode.eq_ignore_ascii_case("delete") {
        return Err(CoreError::Fatal(format!(
            "snapshot seal left journal_mode {mode}"
        )));
    }
    Ok(())
}

fn stage_from_snapshot(snap: &Path, stage: &Path) -> Result<()> {
    fs::create_dir_all(stage)?;
    fs::copy(snap.join("INTERLACE.toml"), stage.join("INTERLACE.toml"))?;
    fs::copy(snap.join("archive.sqlite"), stage.join("archive.sqlite"))?;
    mirror_tree(&snap.join("cas"), &stage.join("cas"), false)?;
    fs::copy(snap.join("MANIFEST.blake3"), stage.join("MANIFEST.blake3"))?;
    Ok(())
}

fn install_staged(root: &Path, stage: &Path) -> Result<()> {
    let aside = root.join("tmp").join(format!(
        "snap-aside-{}-{}",
        std::process::id(),
        STAGE_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&aside)?;
    let names = ["INTERLACE.toml", "archive.sqlite", "cas"];
    if let Err(e) = move_present(root, &aside, &names) {
        // A failed roll-back leaves the aside on disk.
        if move_present(&aside, root, &names).is_ok() {
            let _ = fs::remove_dir_all(&aside);
        }
        return Err(e);
    }
    // Sidecars are deleted while the live database name is absent, so the
    // snapshot is never published beside the previous wal.
    if let Err(e) = delete_live_sidecars(root) {
        if root.join("archive.sqlite-wal").exists() {
            remove_names(root, &names);
            if move_present(&aside, root, &names).is_ok() {
                let _ = fs::remove_dir_all(&aside);
            }
        }
        return Err(e);
    }
    if let Err(e) = move_required(stage, root, &names) {
        remove_names(root, &names);
        return Err(e);
    }
    let _ = fs::remove_dir_all(&aside);
    Ok(())
}

fn move_present(from_dir: &Path, to_dir: &Path, names: &[&str]) -> Result<()> {
    for name in names {
        let from = from_dir.join(name);
        if !from.exists() {
            continue;
        }
        let to = to_dir.join(name);
        if to.exists() {
            return Err(CoreError::Fatal(
                "snapshot restore: name still present".into(),
            ));
        }
        fs::rename(from, to)?;
    }
    Ok(())
}

fn move_required(from_dir: &Path, to_dir: &Path, names: &[&str]) -> Result<()> {
    for name in names {
        let from = from_dir.join(name);
        if !from.exists() {
            return Err(CoreError::Fatal(format!(
                "snapshot restore: staged {name} missing"
            )));
        }
        let to = to_dir.join(name);
        if to.exists() {
            return Err(CoreError::Fatal(
                "snapshot restore: name still present".into(),
            ));
        }
        fs::rename(from, to)?;
    }
    Ok(())
}

fn remove_names(dir: &Path, names: &[&str]) {
    for name in names {
        let path = dir.join(name);
        if path.is_dir() {
            let _ = fs::remove_dir_all(&path);
        } else {
            let _ = fs::remove_file(&path);
        }
    }
}

fn delete_live_sidecars(root: &Path) -> Result<()> {
    for name in [
        "archive.sqlite-wal",
        "archive.sqlite-shm",
        "archive.sqlite-journal",
    ] {
        remove_file_retry(&root.join(name))?;
    }
    Ok(())
}

fn remove_file_retry(path: &Path) -> Result<()> {
    for _ in 0..20 {
        match fs::remove_file(path) {
            Ok(()) => return Ok(()),
            Err(e) if e.kind() == ErrorKind::NotFound => return Ok(()),
            Err(_) => thread::sleep(Duration::from_millis(10)),
        }
    }
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e.into()),
    }
}

fn mirror_tree(src: &Path, dst: &Path, skip_partial: bool) -> Result<()> {
    fs::create_dir_all(dst)?;
    if !src.exists() {
        return Ok(());
    }
    mirror_dir(src, dst, skip_partial)
}

fn mirror_dir(src: &Path, dst: &Path, skip_partial: bool) -> Result<()> {
    fs::create_dir_all(dst)?;
    let mut entries = Vec::new();
    for ent in fs::read_dir(src)? {
        entries.push(ent?);
    }
    entries.sort_by_key(|ent| ent.file_name());
    for ent in entries {
        let name = ent.file_name();
        let label = name.to_string_lossy();
        if skip_partial && (label == "tmp" || label.ends_with(".part")) {
            continue;
        }
        let ty = ent.file_type()?;
        if ty.is_symlink() {
            continue;
        }
        let from = ent.path();
        let to = dst.join(&name);
        if ty.is_dir() {
            mirror_dir(&from, &to, skip_partial)?;
        } else if ty.is_file() {
            fs::copy(&from, &to)?;
        }
    }
    Ok(())
}

fn write_manifest(dir: &Path) -> Result<()> {
    let rels = snapshot_files(dir)?;
    if !rels.iter().any(|rel| rel == "INTERLACE.toml")
        || !rels.iter().any(|rel| rel == "archive.sqlite")
    {
        return Err(hash_err("missing file"));
    }
    let mut text = String::new();
    for rel in &rels {
        let bytes = fs::read(dir.join(rel))?;
        text.push_str(blake3::hash(&bytes).to_hex().as_str());
        text.push(' ');
        text.push_str(rel);
        text.push('\n');
    }
    fs::write(dir.join("MANIFEST.blake3"), text)?;
    Ok(())
}

fn verify_manifest(dir: &Path) -> Result<()> {
    let raw = match fs::read(dir.join("MANIFEST.blake3")) {
        Ok(bytes) => bytes,
        Err(e) if e.kind() == ErrorKind::NotFound => return Err(hash_err("missing manifest")),
        Err(e) => return Err(e.into()),
    };
    let text = String::from_utf8(raw).map_err(|_| hash_err("bad line"))?;
    if !text.ends_with('\n') || text.ends_with("\n\n") {
        return Err(hash_err("bad line"));
    }
    let body = &text[..text.len() - 1];
    if body.is_empty() || body.contains("\n\n") {
        return Err(hash_err("bad line"));
    }
    let mut listed = Vec::new();
    let mut prev = String::new();
    for line in body.split('\n') {
        if line.is_empty() {
            return Err(hash_err("bad line"));
        }
        let Some((hex, rel)) = line.split_once(' ') else {
            return Err(hash_err("bad line"));
        };
        if !hex_ok(hex) || !rel_ok(rel) {
            return Err(hash_err("bad line"));
        }
        if !prev.is_empty() && rel <= prev.as_str() {
            return Err(hash_err("bad line"));
        }
        prev = rel.to_string();
        let file = dir.join(rel);
        match fs::symlink_metadata(&file) {
            Ok(meta) if meta.file_type().is_file() => {}
            Ok(_) => return Err(hash_err("missing file")),
            Err(e) if e.kind() == ErrorKind::NotFound => return Err(hash_err("missing file")),
            Err(e) => return Err(e.into()),
        }
        let bytes = fs::read(&file)?;
        if blake3::hash(&bytes).to_hex().as_str() != hex {
            return Err(hash_err("digest mismatch"));
        }
        listed.push(rel.to_string());
    }
    if listed != snapshot_files(dir)? {
        return Err(hash_err("manifest set"));
    }
    Ok(())
}

fn snapshot_files(dir: &Path) -> Result<Vec<String>> {
    let mut files = Vec::new();
    for name in ["INTERLACE.toml", "archive.sqlite"] {
        if dir.join(name).is_file() {
            files.push(name.to_string());
        }
    }
    collect_files(&dir.join("cas"), dir, &mut files)?;
    files.sort();
    files.dedup();
    Ok(files)
}

fn collect_files(dir: &Path, root: &Path, out: &mut Vec<String>) -> Result<()> {
    if !dir.exists() {
        return Ok(());
    }
    let mut entries = Vec::new();
    for ent in fs::read_dir(dir)? {
        entries.push(ent?);
    }
    entries.sort_by_key(|ent| ent.file_name());
    for ent in entries {
        let ty = ent.file_type()?;
        if ty.is_symlink() {
            continue;
        }
        let path = ent.path();
        if ty.is_dir() {
            collect_files(&path, root, out)?;
        } else if ty.is_file() {
            out.push(rel_to_root(&path, root)?);
        }
    }
    Ok(())
}

fn rel_to_root(path: &Path, root: &Path) -> Result<String> {
    let rel = path.strip_prefix(root).map_err(|_| hash_err("bad line"))?;
    let mut parts = Vec::new();
    for comp in rel.components() {
        match comp {
            Component::Normal(part) => {
                let Some(part) = part.to_str() else {
                    return Err(hash_err("bad line"));
                };
                parts.push(part.to_string());
            }
            _ => return Err(hash_err("bad line")),
        }
    }
    Ok(parts.join("/"))
}

fn allocate_snapshot_dir(root: &Path) -> Result<(String, PathBuf)> {
    let snaps = root.join("snapshots");
    fs::create_dir_all(&snaps)?;
    for _ in 0..64 {
        let id = new_snapshot_id()?;
        let dir = snaps.join(&id);
        match fs::create_dir(&dir) {
            Ok(()) => return Ok((id, dir)),
            Err(e) if e.kind() == ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(e.into()),
        }
    }
    Err(missing_err("id collision"))
}

fn new_snapshot_id() -> Result<String> {
    let stamp = utc_compact()?;
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let pid = u64::from(std::process::id());
    let n = ID_SEQ.fetch_add(1, Ordering::Relaxed);
    let mut raw = Vec::with_capacity(32);
    raw.extend_from_slice(&nanos.to_le_bytes());
    raw.extend_from_slice(&pid.to_le_bytes());
    raw.extend_from_slice(&n.to_le_bytes());
    let digest = blake3::hash(&raw);
    let bytes = digest.as_bytes();
    let suffix = format!(
        "{b0:02x}{b1:02x}{b2:02x}",
        b0 = bytes[0],
        b1 = bytes[1],
        b2 = bytes[2]
    );
    Ok(format!("{stamp}-{suffix}"))
}

fn utc_compact() -> Result<String> {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let t = secs as libc::time_t;
    let mut tm: libc::tm = unsafe { std::mem::zeroed() };
    let ptr = unsafe { libc::gmtime_r(&t, &mut tm) };
    if ptr.is_null() {
        return Err(CoreError::Fatal("snapshot clock".into()));
    }
    Ok(format!(
        "{:04}{:02}{:02}T{:02}{:02}{:02}Z",
        tm.tm_year + 1900,
        tm.tm_mon + 1,
        tm.tm_mday,
        tm.tm_hour,
        tm.tm_min,
        tm.tm_sec
    ))
}

fn snapshot_id_ok(id: &str) -> bool {
    if id.is_empty() || id == "." || id == ".." || id.contains('\0') {
        return false;
    }
    if id.contains('/') || id.contains('\\') || id.contains("..") {
        return false;
    }
    let mut parts = Path::new(id).components();
    match (parts.next(), parts.next()) {
        (Some(Component::Normal(name)), None) => name.to_str() == Some(id),
        _ => false,
    }
}

fn hex_ok(hex: &str) -> bool {
    hex.len() == 64
        && hex
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}

fn rel_ok(rel: &str) -> bool {
    if rel.is_empty()
        || rel.starts_with('/')
        || rel.contains('\\')
        || rel.contains('\0')
        || rel == "MANIFEST.blake3"
    {
        return false;
    }
    rel.split('/')
        .all(|part| !part.is_empty() && part != "." && part != "..")
}

fn remove_sidecars(sqlite: &Path) -> Result<()> {
    for suffix in ["-wal", "-shm", "-journal"] {
        if let Some(path) = sqlite_sidecar(sqlite, suffix) {
            match fs::remove_file(path) {
                Ok(()) => {}
                Err(e) if e.kind() == ErrorKind::NotFound => {}
                Err(e) => return Err(e.into()),
            }
        }
    }
    Ok(())
}

fn remove_sqlite_family(sqlite: &Path) {
    let _ = fs::remove_file(sqlite);
    for suffix in ["-wal", "-shm", "-journal"] {
        if let Some(path) = sqlite_sidecar(sqlite, suffix) {
            let _ = fs::remove_file(path);
        }
    }
}

fn sqlite_sidecar(sqlite: &Path, suffix: &str) -> Option<PathBuf> {
    let name = sqlite.file_name()?;
    let mut owned = name.to_os_string();
    owned.push(suffix);
    Some(sqlite.with_file_name(owned))
}

fn hash_err(detail: &str) -> CoreError {
    CoreError::Fatal(format!("snapshot hash: {detail}"))
}

fn missing_err(detail: &str) -> CoreError {
    CoreError::Fatal(format!("snapshot missing: {detail}"))
}

struct DirGuard {
    path: PathBuf,
    armed: bool,
}

impl DirGuard {
    fn arm(path: PathBuf) -> Self {
        Self { path, armed: true }
    }

    fn path(&self) -> &Path {
        &self.path
    }

    fn disarm(&mut self) {
        self.armed = false;
    }
}

impl Drop for DirGuard {
    fn drop(&mut self) {
        if self.armed {
            let _ = fs::remove_dir_all(&self.path);
        }
    }
}
