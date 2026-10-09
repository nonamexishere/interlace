//! Read-only repair list and one transactional apply.
//! Does not call `doctor`, `doctor_issues`, or `doctor_issues_quick`.

use std::collections::HashSet;
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};

use crate::cas::{cas_blob_path, cas_reference_count};
use crate::db::{Archive, Result};
use crate::model::{CoreError, DoctorPlan};

struct ListedFile {
    name: String,
    path: PathBuf,
    size: i64,
}

struct Reattach {
    hash: String,
    source: PathBuf,
    size: i64,
}

struct Reclaim {
    hash: String,
    paths: Vec<PathBuf>,
}

struct ApplyWork {
    rebuild: bool,
    reattach: Vec<Reattach>,
    reclaim: Vec<Reclaim>,
}

impl ApplyWork {
    fn is_empty(&self) -> bool {
        !self.rebuild && self.reattach.is_empty() && self.reclaim.is_empty()
    }
}

fn plan_refuse(detail: &str) -> CoreError {
    CoreError::Fatal(format!("doctor plan {detail}"))
}

fn is_hex64(name: &str) -> bool {
    name.len() == 64 && name.bytes().all(|b| b.is_ascii_hexdigit())
}

fn normalize_hash(hash: &str) -> std::result::Result<String, CoreError> {
    let hash = hash.to_ascii_lowercase();
    if is_hex64(&hash) {
        Ok(hash)
    } else {
        Err(plan_refuse("hash is not 64 hex"))
    }
}

fn skipped_name(path: &Path) -> bool {
    matches!(
        path.file_name().and_then(|s| s.to_str()),
        Some("snapshots" | "tmp")
    )
}

/// `cas/<dir>/<dir>/<file>` names only. Does not read file bytes.
/// Non-hex names, `snapshots/`, and `tmp/` are skipped.
fn list_cas_files(root: &Path) -> Result<Vec<ListedFile>> {
    let mut out = Vec::new();
    let l1 = match fs::read_dir(root.join("cas")) {
        Ok(dir) => dir,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(out),
        Err(e) => return Err(e.into()),
    };
    for a in l1 {
        let a = a?.path();
        if !a.is_dir() || skipped_name(&a) {
            continue;
        }
        for b in fs::read_dir(&a)? {
            let b = b?.path();
            if !b.is_dir() || skipped_name(&b) {
                continue;
            }
            for f in fs::read_dir(&b)? {
                let f = f?.path();
                if !f.is_file() || skipped_name(&f) {
                    continue;
                }
                let Some(raw) = f.file_name().and_then(|s| s.to_str()) else {
                    continue;
                };
                let name = raw.to_ascii_lowercase();
                if !is_hex64(&name) {
                    continue;
                }
                let size = f.metadata()?.len() as i64;
                out.push(ListedFile {
                    name,
                    path: f,
                    size,
                });
            }
        }
    }
    out.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(out)
}

fn file_digest(path: &Path) -> Result<String> {
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

/// Every hash stored in the four CAS columns, lowercased.
fn referenced_hashes(archive: &Archive) -> Result<HashSet<String>> {
    let mut set = HashSet::new();
    let mut stmt = archive.conn.prepare(
        "SELECT cas_hash FROM attachments WHERE cas_hash IS NOT NULL
         UNION
         SELECT derivative_cas_hash FROM attachments WHERE derivative_cas_hash IS NOT NULL
         UNION
         SELECT photo_cas_hash FROM contacts_raw WHERE photo_cas_hash IS NOT NULL
         UNION
         SELECT raw_cas_hash FROM messages WHERE raw_cas_hash IS NOT NULL",
    )?;
    let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
    for row in rows {
        set.insert(row?.to_ascii_lowercase());
    }
    Ok(set)
}

/// External-content FTS matches `search_doc` only when `rank` is 1.
/// Roll the savepoint back. `RELEASE` of the outermost savepoint would commit.
fn fts_integrity_fails(conn: &rusqlite::Connection) -> Result<bool> {
    let nested = !conn.is_autocommit();
    conn.execute_batch("SAVEPOINT doctor_plan_fts")?;
    let failed = conn
        .execute(
            "INSERT INTO messages_fts(messages_fts, rank) VALUES ('integrity-check', 1)",
            [],
        )
        .is_err();
    if let Err(e) = conn.execute_batch("ROLLBACK TO doctor_plan_fts") {
        let _ = conn.execute_batch("ROLLBACK");
        return Err(e.into());
    }
    let end = if nested {
        conn.execute_batch("RELEASE doctor_plan_fts")
    } else {
        conn.execute_batch("ROLLBACK")
    };
    if let Err(e) = end {
        let _ = conn.execute_batch("ROLLBACK");
        return Err(e.into());
    }
    Ok(failed)
}

fn referenced(archive: &Archive, hash: &str) -> Result<bool> {
    Ok(cas_reference_count(archive, hash)? > 0)
}

fn blob_row_exists(archive: &Archive, hash: &str) -> Result<bool> {
    let n: i64 = archive.conn.query_row(
        "SELECT COUNT(*) FROM cas_blobs WHERE hash = ?1",
        [hash],
        |row| row.get(0),
    )?;
    Ok(n > 0)
}

/// A file already at `cas/ab/cd/<name>` whose name is still referenced is not a misplaced blob.
fn is_settled(root: &Path, file: &ListedFile, referenced: &HashSet<String>) -> Result<bool> {
    Ok(referenced.contains(&file.name) && cas_blob_path(root, &file.name)? == file.path)
}

fn find_reattach_source(
    root: &Path,
    files: &[ListedFile],
    referenced: &HashSet<String>,
    hash: &str,
    dest: &Path,
) -> Result<Option<(PathBuf, i64)>> {
    for file in files {
        if file.path == dest || is_settled(root, file, referenced)? {
            continue;
        }
        if file_digest(&file.path)? == hash {
            return Ok(Some((file.path.clone(), file.size)));
        }
    }
    Ok(None)
}

/// Every walked `cas/<dir>/<dir>/<hash>`, including shards that are not `hash[0..2]/hash[2..4]`.
fn paths_named(files: &[ListedFile], hash: &str) -> Vec<PathBuf> {
    files
        .iter()
        .filter(|file| file.name == hash)
        .map(|file| file.path.clone())
        .collect()
}

fn classify(archive: &Archive, plan: &DoctorPlan) -> Result<ApplyWork> {
    let files = list_cas_files(&archive.root)?;
    let mut work = ApplyWork {
        rebuild: false,
        reattach: Vec::new(),
        reclaim: Vec::new(),
    };
    if plan.rebuild_search && fts_integrity_fails(&archive.conn)? {
        work.rebuild = true;
    }
    for hash in &plan.reattach {
        let hash = normalize_hash(hash)?;
        let dest = cas_blob_path(&archive.root, &hash)?;
        if dest.is_file() {
            let bytes = fs::read(&dest)?;
            let digest = blake3::hash(&bytes).to_hex().to_string();
            if digest != hash {
                return Err(plan_refuse(&format!(
                    "reattach {hash} canonical bytes differ"
                )));
            }
            continue;
        }
        if !referenced(archive, &hash)? {
            return Err(plan_refuse(&format!("reattach {hash} is no longer stored")));
        }
        let referenced_set = referenced_hashes(archive)?;
        let Some((source, size)) =
            find_reattach_source(&archive.root, &files, &referenced_set, &hash, &dest)?
        else {
            return Err(plan_refuse(&format!(
                "reattach {hash} is not a rename of stored bytes"
            )));
        };
        work.reattach.push(Reattach { hash, source, size });
    }
    for hash in &plan.reclaim {
        let hash = normalize_hash(hash)?;
        if referenced(archive, &hash)? {
            return Err(plan_refuse(&format!("reclaim {hash} is referenced")));
        }
        let paths = paths_named(&files, &hash);
        if paths.is_empty() && !blob_row_exists(archive, &hash)? {
            continue;
        }
        work.reclaim.push(Reclaim { hash, paths });
    }
    Ok(work)
}

fn unlink_blob(path: &Path) -> Result<()> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e.into()),
    }
}

impl Archive {
    pub fn doctor_plan(&self) -> Result<DoctorPlan> {
        let referenced = referenced_hashes(self)?;
        let files = list_cas_files(&self.root)?;
        let mut missing = HashSet::new();
        for hash in &referenced {
            if !cas_blob_path(&self.root, hash)?.is_file() {
                missing.insert(hash.clone());
            }
        }
        let mut reattach = Vec::new();
        let mut reclaim = Vec::new();
        for file in &files {
            // Hash only a file that could be the bytes of a missing canonical blob.
            // A settled file is already that blob. Reading every byte of cas/ here
            // took seconds in a debug build and froze the Doctor window.
            if !missing.is_empty() && !is_settled(&self.root, file, &referenced)? {
                let digest = file_digest(&file.path)?;
                if missing.contains(&digest) {
                    if !reattach.contains(&digest) {
                        reattach.push(digest);
                    }
                    continue;
                }
            }
            if !referenced.contains(&file.name) {
                reclaim.push(file.name.clone());
            }
        }
        reattach.sort();
        reclaim.sort();
        reclaim.dedup();
        Ok(DoctorPlan {
            rebuild_search: fts_integrity_fails(&self.conn)?,
            reattach,
            reclaim,
        })
    }

    pub fn doctor_apply(&self, plan: &DoctorPlan) -> Result<()> {
        let work = classify(self, plan)?;
        if work.is_empty() {
            return Ok(());
        }
        self.conn.execute_batch("BEGIN IMMEDIATE")?;
        let wrote = (|| -> Result<Option<ApplyWork>> {
            let work = classify(self, plan)?;
            if work.is_empty() {
                return Ok(None);
            }
            if work.rebuild {
                self.conn.execute(
                    "INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')",
                    [],
                )?;
            }
            for item in &work.reclaim {
                self.conn
                    .execute("DELETE FROM cas_blobs WHERE hash = ?1", [&item.hash])?;
            }
            for item in &work.reattach {
                self.conn.execute(
                    "INSERT INTO cas_blobs(hash, size, mime_hint, refcount)
                     VALUES (?1, ?2, NULL, 0)
                     ON CONFLICT(hash) DO NOTHING",
                    rusqlite::params![item.hash, item.size],
                )?;
            }
            Ok(Some(work))
        })();
        let work = match wrote {
            Ok(Some(work)) => work,
            Ok(None) => {
                let _ = self.conn.execute_batch("ROLLBACK");
                return Ok(());
            }
            Err(e) => {
                let _ = self.conn.execute_batch("ROLLBACK");
                return Err(e);
            }
        };
        if let Err(e) = self.conn.execute_batch("COMMIT") {
            let _ = self.conn.execute_batch("ROLLBACK");
            return Err(e.into());
        }
        let mut moved = Vec::new();
        for item in &work.reattach {
            let dest = cas_blob_path(&self.root, &item.hash)?;
            if let Some(parent) = dest.parent() {
                fs::create_dir_all(parent)?;
            }
            if item.source != dest {
                fs::rename(&item.source, &dest)?;
            }
            moved.push(dest);
        }
        for item in &work.reclaim {
            for path in &item.paths {
                if moved.iter().any(|dest| dest == path) {
                    continue;
                }
                unlink_blob(path)?;
            }
        }
        Ok(())
    }
}
