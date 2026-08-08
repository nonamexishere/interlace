use std::fs::{self, OpenOptions as FsOpenOptions};
use std::io::Write;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

use rusqlite::{Connection, OptionalExtension};

use crate::model::{CoreError, ImportOpts, ImportStats, OpenOptions, SourceKind};

use super::lock::{ArchiveLock, LockMode};
use super::migrate::migrate;
use super::Result;

/// Open archive connection plus the held flock.
pub struct Archive {
    pub conn: Connection,
    pub root: PathBuf,
    _lock: ArchiveLock,
}

pub fn init_archive(root: &Path) -> Result<Archive> {
    fs::create_dir_all(root)?;
    #[cfg(unix)]
    {
        let mut perms = fs::metadata(root)?.permissions();
        perms.set_mode(0o700);
        fs::set_permissions(root, perms)?;
    }
    for sub in ["cas", "logs", "imports", "tmp", "exports"] {
        fs::create_dir_all(root.join(sub))?;
    }

    let archive_id = new_archive_id();
    let created_at = now_rfc3339();
    let toml = format!(
        "format = 1\narchive_id = \"{archive_id}\"\ncreated_at = \"{created_at}\"\napp_min_version = \"0.1.0\"\n"
    );
    write_mode_600(root.join("INTERLACE.toml"), toml.as_bytes())?;
    write_mode_600(root.join("INTERLACE.lock"), b"")?;

    let arch = open_archive(root, LockMode::Exclusive)?;
    arch.conn.execute(
        "INSERT INTO archive_meta(id, archive_id, created_at) VALUES (1, ?1, ?2)",
        rusqlite::params![archive_id, created_at],
    )?;
    Ok(arch)
}

pub fn open_archive(root: &Path, mode: LockMode) -> Result<Archive> {
    let marker = root.join("INTERLACE.toml");
    if !marker.is_file() {
        return Err(CoreError::Config(format!(
            "not an Interlace archive (missing INTERLACE.toml): {}",
            root.display()
        )));
    }
    let lock = ArchiveLock::acquire(&root.join("INTERLACE.lock"), mode)?;
    let db_path = root.join("archive.sqlite");
    let conn = Connection::open(&db_path)?;
    apply_pragmas(&conn)?;
    migrate(&conn)?;
    ensure_fts_triggers(&conn)?;
    Ok(Archive {
        conn,
        root: root.to_path_buf(),
        _lock: lock,
    })
}

/// DESIGN `OpenOptions` wrapper: `create` → init, else exclusive open.
pub fn open_with_options(opts: &OpenOptions) -> Result<Archive> {
    if opts.create {
        init_archive(&opts.path)
    } else {
        open_archive(&opts.path, LockMode::Exclusive)
    }
}

impl Archive {
    pub fn status(&self) -> Result<serde_json::Value> {
        let archive_id: String = self.conn.query_row(
            "SELECT archive_id FROM archive_meta WHERE id = 1",
            [],
            |r| r.get(0),
        )?;
        let messages: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM messages", [], |r| r.get(0))?;
        let identities: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM identities", [], |r| r.get(0))?;
        let persons_live: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM persons WHERE tombstoned_at IS NULL",
            [],
            |r| r.get(0),
        )?;
        let review_open: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM merge_review_queue WHERE status = 'open'",
            [],
            |r| r.get(0),
        )?;
        let last_import = self
            .conn
            .query_row(
                "SELECT id, status, finished_at, stats_json FROM import_runs ORDER BY id DESC LIMIT 1",
                [],
                |r| {
                    Ok(serde_json::json!({
                        "id": r.get::<_, i64>(0)?,
                        "status": r.get::<_, String>(1)?,
                        "finished_at": r.get::<_, Option<String>>(2)?,
                        "stats_json": r.get::<_, Option<String>>(3)?,
                    }))
                },
            )
            .optional()?;
        Ok(serde_json::json!({
            "archive_id": archive_id,
            "path": self.root,
            "messages": messages,
            "identities": identities,
            "persons_live": persons_live,
            "review_open": review_open,
            "last_import": last_import,
        }))
    }

    pub fn doctor(&self, rebuild_fts: bool, gc_cas: bool, integrity: bool) -> Result<()> {
        if gc_cas {
            crate::cas::gc_cas(self)?;
        }
        if integrity {
            let ok: String = self
                .conn
                .query_row("PRAGMA integrity_check", [], |r| r.get(0))?;
            if ok != "ok" {
                return Err(CoreError::Fatal(format!("integrity_check: {ok}")));
            }
        }
        if rebuild_fts {
            crate::search::rebuild_fts(self)?;
        }
        Ok(())
    }

    /// Non-mutating scan used by `interlace doctor`. Empty = healthy.
    pub fn doctor_issues(&self) -> Result<Vec<String>> {
        let mut issues = Vec::new();
        let ok: String = self
            .conn
            .query_row("PRAGMA integrity_check", [], |r| r.get(0))?;
        if ok != "ok" {
            issues.push(format!("integrity_check: {ok}"));
        }
        if let Err(e) = self.conn.execute(
            "INSERT INTO messages_fts(messages_fts) VALUES('integrity-check')",
            [],
        ) {
            issues.push(format!("fts integrity-check: {e}"));
        }
        let trig: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='search_doc_ai'",
            [],
            |r| r.get(0),
        )?;
        if trig == 0 {
            issues.push("missing search_doc_ai trigger".into());
        }
        let stale: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM import_runs
             WHERE status = 'running'
               AND heartbeat_at < strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')",
            [],
            |r| r.get(0),
        )?;
        if stale > 0 {
            issues.push(format!(
                "{stale} import run(s) running with heartbeat older than 15 minutes"
            ));
            let _ = self.conn.execute(
                "UPDATE import_runs SET status = 'interrupted'
                 WHERE status = 'running'
                   AND heartbeat_at < strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')",
                [],
            );
        }
        let mut stmt = self
            .conn
            .prepare("SELECT DISTINCT cas_hash FROM attachments WHERE cas_hash IS NOT NULL")?;
        let hashes = stmt.query_map([], |r| r.get::<_, String>(0))?;
        for h in hashes {
            let h = h?;
            if self.cas_get(&h).is_err() {
                issues.push(format!("CAS blob missing: {h}"));
            }
        }
        Ok(issues)
    }

    pub fn run_import(
        &mut self,
        kind: SourceKind,
        path: &std::path::Path,
        opts: &ImportOpts,
    ) -> Result<ImportStats> {
        crate::import::run_import(self, kind, path, opts)
    }
}

fn apply_pragmas(conn: &Connection) -> Result<()> {
    // journal_mode returns a row; use query_row, not execute.
    conn.pragma_update(None, "foreign_keys", "ON")?;
    let _: String = conn.query_row("PRAGMA journal_mode = WAL", [], |r| r.get(0))?;
    conn.pragma_update(None, "synchronous", "NORMAL")?;
    conn.pragma_update(None, "temp_store", "MEMORY")?;
    conn.pragma_update(None, "cache_size", -200_000i64)?;
    conn.pragma_update(None, "mmap_size", 1_073_741_824i64)?;
    conn.pragma_update(None, "busy_timeout", 5_000i64)?;
    conn.pragma_update(None, "wal_autocheckpoint", 1_000i64)?;
    Ok(())
}

fn ensure_fts_triggers(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        r#"
        CREATE TRIGGER IF NOT EXISTS search_doc_ai AFTER INSERT ON search_doc BEGIN
            INSERT INTO messages_fts(rowid, search_text) VALUES (new.message_id, new.search_text);
        END;
        CREATE TRIGGER IF NOT EXISTS search_doc_ad AFTER DELETE ON search_doc BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, search_text)
                VALUES ('delete', old.message_id, old.search_text);
        END;
        CREATE TRIGGER IF NOT EXISTS search_doc_au AFTER UPDATE ON search_doc BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, search_text)
                VALUES ('delete', old.message_id, old.search_text);
            INSERT INTO messages_fts(rowid, search_text) VALUES (new.message_id, new.search_text);
        END;
        "#,
    )?;
    Ok(())
}

fn write_mode_600(path: PathBuf, bytes: &[u8]) -> Result<()> {
    let mut opts = FsOpenOptions::new();
    opts.write(true).create(true).truncate(true);
    #[cfg(unix)]
    opts.mode(0o600);
    let mut f = opts.open(&path)?;
    f.write_all(bytes)?;
    Ok(())
}

fn new_archive_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{:032x}", nanos ^ u128::from(std::process::id()))
}

fn now_rfc3339() -> String {
    // SQLite-compatible UTC timestamp; enough for init until chrono lands.
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}
