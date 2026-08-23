//! Importer plugin interface + WhatsApp / Gmail / Takeout / Contacts.

mod contacts;
mod context;
mod gmail;
mod locale;
mod takeout;
mod whatsapp;

use std::io::Read;
use std::path::Path;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::identity::resolve_run;
use crate::model::*;

pub use contacts::ContactsImporter;
pub use context::DbImportContext;
pub use gmail::GmailMboxImporter;
pub use locale::{load_pack, name_fold, name_fold_join, normalize_email, parse_phone, PACK_IDS};
pub use takeout::TakeoutImporter;
pub use whatsapp::WhatsappImporter;

use context::source_kind_sql;

pub trait ImportContext {
    fn run_id(&self) -> i64;
    fn source_id(&self) -> i64;
    fn archive_root(&self) -> &Path;

    fn persist_identity(&mut self, rec: NewIdentity) -> Result<i64, CoreError>;
    fn persist_conversation(&mut self, rec: NewConversation) -> Result<i64, CoreError>;
    fn persist_message(&mut self, rec: NewMessage) -> Result<PersistOutcome, CoreError>;
    fn persist_labels(&mut self, message_id: i64, labels: &[String]) -> Result<(), CoreError>;
    fn persist_attachment(
        &mut self,
        rec: NewAttachment,
        bytes: Option<&[u8]>,
    ) -> Result<(), CoreError>;
    fn persist_contact(&mut self, rec: NewContact) -> Result<i64, CoreError>;

    fn warn(&mut self, w: Warning) -> Result<(), CoreError>;
    fn checkpoint(&mut self, c: Checkpoint) -> Result<(), CoreError>;
    fn load_checkpoint(&self, cursor_kind: &str) -> Result<Option<Checkpoint>, CoreError>;
    fn heartbeat(&mut self) -> Result<(), CoreError>;
    fn maybe_commit(&mut self) -> Result<(), CoreError>;
    fn cas_put(&mut self, bytes: &[u8], mime_hint: Option<&str>) -> Result<String, CoreError>;

    /// Folded owner / self-identity names for D18-C. Default: none.
    fn owner_self_folds(&self) -> Result<Vec<String>, CoreError> {
        Ok(Vec::new())
    }

    /// Link a WhatsApp display_name identity onto `persons.is_self` (D18-C).
    fn link_identity_to_self_person(&mut self, _identity_id: i64) -> Result<(), CoreError> {
        Ok(())
    }

    /// Set `conversation_participants.role` (e.g. `me`).
    fn set_participant_role(
        &mut self,
        _conversation_id: i64,
        _identity_id: i64,
        _role: &str,
    ) -> Result<(), CoreError> {
        Ok(())
    }
}

pub trait SourceImporter: Send + Sync {
    fn id(&self) -> SourceKind;
    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError>;
    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError>;
}

pub struct ImporterRegistry;

impl ImporterRegistry {
    pub fn detect(path: &Path) -> Result<SourceKind, CoreError> {
        detect(path)
    }
}

pub fn detect(path: &Path) -> Result<SourceKind, CoreError> {
    takeout::check_spanned(path)?;
    if path.is_dir() {
        if takeout::is_takeout_tree(path) {
            return Ok(SourceKind::TakeoutDir);
        }
        // directory of independent takeout-*.zip
        if TakeoutImporter::default().probe(path).is_ok() {
            return Ok(SourceKind::TakeoutDir);
        }
        return Err(CoreError::Probe(format!(
            "directory is not a Takeout tree: {}",
            path.display()
        )));
    }
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    if ext == "mbox" {
        return Ok(SourceKind::GmailMbox);
    }
    if ext == "vcf" || ext == "vcard" {
        return Ok(SourceKind::ContactsVcf);
    }
    if ext == "csv" {
        return Ok(SourceKind::ContactsCsv);
    }
    if takeout::looks_like_takeout_zip(path)? {
        return Ok(SourceKind::TakeoutZip);
    }
    Ok(WhatsappImporter::default().probe(path)?.kind)
}

pub fn run_import(
    archive: &mut Archive,
    kind: SourceKind,
    path: &Path,
    opts: &ImportOpts,
) -> Result<ImportStats, CoreError> {
    if path.is_file() {
        let zip_len = std::fs::metadata(path)?.len();
        if zip_len > opts.max_bytes {
            return Err(CoreError::Fatal(format!(
                "file {} bytes exceeds --max-bytes {}",
                zip_len, opts.max_bytes
            )));
        }
    } else if !path.is_dir() {
        return Err(CoreError::Probe(format!(
            "import path is not a file or directory: {}",
            path.display()
        )));
    }

    let mut opts = opts.clone();
    if opts.phone_region.is_none() {
        opts.phone_region = archive
            .conn
            .query_row(
                "SELECT value FROM settings WHERE key = 'default_phone_region'",
                [],
                |r| r.get(0),
            )
            .optional()?;
    }
    let opts = &opts;

    if opts.cancel.as_ref().is_some_and(|c| c.is_cancelled()) {
        return abort_cancelled(archive, kind, path, opts);
    }

    let probe = match probe_kind(kind, path, opts) {
        Ok(p) => p,
        Err(CoreError::Cancelled) => return abort_cancelled(archive, kind, path, opts),
        Err(e) => return Err(e),
    };
    let kind = probe.kind;
    let kind_sql = source_kind_sql(kind);
    let origin = path
        .canonicalize()
        .unwrap_or_else(|_| path.to_path_buf())
        .to_string_lossy()
        .to_string();
    let label = probe.label.clone();
    let blake3 = probe.file_blake3.clone();

    let source_id = upsert_source(
        archive,
        kind_sql,
        &label,
        &origin,
        probe.bytes,
        blake3.as_deref(),
    )?;
    let run_id = open_run(archive, source_id, opts.resume_run_id)?;

    if opts.cancel.as_ref().is_some_and(|c| c.is_cancelled()) {
        let e = CoreError::Cancelled;
        mark_run(archive, run_id, "interrupted", None, Some(&e.to_string()))?;
        return Err(e);
    }

    let import_err;
    let mut stats = {
        let mut ctx = DbImportContext::new(archive, run_id, source_id, opts.cancel.clone())?;
        match dispatch_import(kind, path, opts, &mut ctx) {
            Ok(_) => {
                let s = ctx.stats.clone();
                if let Err(e) = ctx.commit() {
                    ctx.rollback();
                    import_err = Some(e);
                    ImportStats::default()
                } else {
                    import_err = None;
                    s
                }
            }
            Err(e) => {
                ctx.rollback();
                import_err = Some(e);
                ImportStats::default()
            }
        }
    };
    if let Some(e) = import_err {
        let status = if matches!(e, CoreError::Cancelled) {
            "interrupted"
        } else {
            "failed"
        };
        mark_run(archive, run_id, status, None, Some(&e.to_string()))?;
        return Err(e);
    }

    match resolve_run(archive, run_id) {
        Ok(id_stats) => {
            stats.auto_person_merges += id_stats.auto_person_merges;
            stats.review_enqueued += id_stats.review_enqueued;
        }
        Err(e) => {
            mark_run(
                archive,
                run_id,
                "failed",
                Some(&stats),
                Some(&e.to_string()),
            )?;
            return Err(e);
        }
    }

    if let Err(e) = crate::search::index_import_run(archive, run_id) {
        mark_run(
            archive,
            run_id,
            "failed",
            Some(&stats),
            Some(&e.to_string()),
        )?;
        return Err(e);
    }

    mark_run(archive, run_id, "done", Some(&stats), None)?;
    let spill = archive
        .root
        .join("imports")
        .join(run_id.to_string())
        .join("spill");
    let _ = std::fs::remove_dir_all(spill);
    Ok(stats)
}

/// BLAKE3 of a file. Checks `cancel` every 64 KiB so a multi-GB WhatsApp ZIP
/// does not block Cancel for the whole hash.
pub(crate) fn hash_file(path: &Path, cancel: Option<&ImportCancel>) -> Result<String, CoreError> {
    let mut f = std::fs::File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0u8; 65536];
    loop {
        if cancel.is_some_and(|c| c.is_cancelled()) {
            return Err(CoreError::Cancelled);
        }
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}

/// Like `hash_file`, but I/O errors become `None`. Cancel still fails.
pub(crate) fn optional_file_hash(
    path: &Path,
    cancel: Option<&ImportCancel>,
) -> Result<Option<String>, CoreError> {
    match hash_file(path, cancel) {
        Ok(h) => Ok(Some(h)),
        Err(CoreError::Cancelled) => Err(CoreError::Cancelled),
        Err(_) => Ok(None),
    }
}

fn abort_cancelled(
    archive: &Archive,
    kind: SourceKind,
    path: &Path,
    opts: &ImportOpts,
) -> Result<ImportStats, CoreError> {
    let e = CoreError::Cancelled;
    let origin = path
        .canonicalize()
        .unwrap_or_else(|_| path.to_path_buf())
        .to_string_lossy()
        .to_string();
    let label = path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("import")
        .to_string();
    let source_id = upsert_source(archive, source_kind_sql(kind), &label, &origin, None, None)?;
    let run_id = open_run(archive, source_id, opts.resume_run_id)?;
    mark_run(archive, run_id, "interrupted", None, Some(&e.to_string()))?;
    Err(e)
}

fn probe_kind(kind: SourceKind, path: &Path, opts: &ImportOpts) -> Result<ProbeResult, CoreError> {
    match kind {
        SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip => {
            WhatsappImporter { opts: opts.clone() }.probe(path)
        }
        SourceKind::GmailMbox => GmailMboxImporter { opts: opts.clone() }.probe(path),
        SourceKind::ContactsVcf | SourceKind::ContactsCsv => ContactsImporter {
            opts: opts.clone(),
            kind: Some(kind),
        }
        .probe(path),
        SourceKind::TakeoutZip | SourceKind::TakeoutDir => {
            TakeoutImporter { opts: opts.clone() }.probe(path)
        }
    }
}

fn dispatch_import(
    kind: SourceKind,
    path: &Path,
    opts: &ImportOpts,
    ctx: &mut dyn ImportContext,
) -> Result<ImportStats, CoreError> {
    match kind {
        SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip => {
            WhatsappImporter { opts: opts.clone() }.import(path, ctx)
        }
        SourceKind::GmailMbox => GmailMboxImporter { opts: opts.clone() }.import(path, ctx),
        SourceKind::ContactsVcf | SourceKind::ContactsCsv => ContactsImporter {
            opts: opts.clone(),
            kind: Some(kind),
        }
        .import(path, ctx),
        SourceKind::TakeoutZip | SourceKind::TakeoutDir => {
            TakeoutImporter { opts: opts.clone() }.import(path, ctx)
        }
    }
}

fn upsert_source(
    archive: &Archive,
    kind_sql: &str,
    label: &str,
    origin: &str,
    bytes: Option<u64>,
    blake3: Option<&str>,
) -> Result<i64, CoreError> {
    if let Some(h) = blake3 {
        let mut stmt = archive
            .conn
            .prepare("SELECT id FROM sources WHERE kind = ?1 AND file_blake3 = ?2 LIMIT 1")?;
        let mut rows = stmt.query(rusqlite::params![kind_sql, h])?;
        if let Some(r) = rows.next()? {
            return Ok(r.get(0)?);
        }
    } else {
        let mut stmt = archive
            .conn
            .prepare("SELECT id FROM sources WHERE kind = ?1 AND origin_path = ?2 LIMIT 1")?;
        let mut rows = stmt.query(rusqlite::params![kind_sql, origin])?;
        if let Some(r) = rows.next()? {
            return Ok(r.get(0)?);
        }
    }
    archive.conn.execute(
        "INSERT INTO sources(kind, label, origin_path, bytes, file_blake3)
         VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![kind_sql, label, origin, bytes.map(|b| b as i64), blake3],
    )?;
    Ok(archive.conn.last_insert_rowid())
}

fn open_run(archive: &Archive, source_id: i64, resume: Option<i64>) -> Result<i64, CoreError> {
    if let Some(rid) = resume {
        let (sid, _status): (i64, String) = archive.conn.query_row(
            "SELECT source_id, status FROM import_runs WHERE id = ?1",
            [rid],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;
        if sid != source_id {
            return Err(CoreError::Config(
                "resume run_id belongs to a different source".into(),
            ));
        }
        archive.conn.execute(
            "UPDATE import_runs SET status = 'running', error = NULL,
                    heartbeat_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE id = ?1",
            [rid],
        )?;
        return Ok(rid);
    }
    archive.conn.execute(
        "INSERT INTO import_runs(source_id, status) VALUES (?1, 'running')",
        [source_id],
    )?;
    Ok(archive.conn.last_insert_rowid())
}

fn mark_run(
    archive: &Archive,
    run_id: i64,
    status: &str,
    stats: Option<&ImportStats>,
    error: Option<&str>,
) -> Result<(), CoreError> {
    let stats_json = match stats {
        Some(s) => Some(
            serde_json::to_string(s).map_err(|e| CoreError::Fatal(format!("stats json: {e}")))?,
        ),
        None => None,
    };
    archive.conn.execute(
        "UPDATE import_runs SET status = ?1,
                finished_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                heartbeat_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                stats_json = COALESCE(?2, stats_json),
                error = ?3
         WHERE id = ?4",
        rusqlite::params![status, stats_json, error, run_id],
    )?;
    Ok(())
}

#[cfg(test)]
mod cancel_hash_tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn hash_file_returns_cancelled_without_reading_the_file() {
        let dir = std::env::temp_dir().join(format!("il-hash-c-{}", std::process::id()));
        let _ = std::fs::create_dir_all(&dir);
        let p = dir.join("big.bin");
        {
            let mut f = std::fs::File::create(&p).unwrap();
            let chunk = vec![0u8; 1024 * 1024];
            for _ in 0..16 {
                f.write_all(&chunk).unwrap();
            }
        }
        let token = ImportCancel::new();
        token.cancel();
        let t = std::time::Instant::now();
        let err = hash_file(&p, Some(&token)).unwrap_err();
        assert!(matches!(err, CoreError::Cancelled), "{err}");
        assert!(
            t.elapsed() < std::time::Duration::from_millis(500),
            "cancelled hash must not read 16 MiB, took {:?}",
            t.elapsed()
        );
        let _ = std::fs::remove_dir_all(&dir);
    }
}
