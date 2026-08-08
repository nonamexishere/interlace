use std::fs::{self, OpenOptions};
use std::io::Write;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

use rusqlite::Connection;

use super::lock::{ArchiveLock, LockMode};
use super::migrate::migrate;
use super::{DbError, Result};

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
        "format = 1\narchive_id = \"{archive_id}\"\ncreated_at = \"{created_at}\"\napp_min_version = \"0.0.1\"\n"
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
        return Err(DbError::Config(format!(
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
    let mut opts = OpenOptions::new();
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
