//! Importer plugin interface + WhatsApp (PR6). Gmail/Contacts land in PR7.

mod context;
mod locale;
mod whatsapp;

use std::fs::File;
use std::path::Path;

use zip::ZipArchive;

use crate::db::Archive;
use crate::identity::resolve_run;
use crate::model::*;

pub use context::DbImportContext;
pub use locale::{load_pack, name_fold, parse_phone, PACK_IDS};
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
    if path.is_dir() {
        if path.join("Takeout").is_dir()
            || path.join("Takeout/Mail").is_dir()
            || path.join("Takeout/Contacts").is_dir()
        {
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
    if looks_like_takeout_zip(path)? {
        return Ok(SourceKind::TakeoutZip);
    }
    Ok(WhatsappImporter::default().probe(path)?.kind)
}

fn looks_like_takeout_zip(path: &Path) -> Result<bool, CoreError> {
    let f = File::open(path)?;
    let mut zip = match ZipArchive::new(f) {
        Ok(z) => z,
        Err(_) => return Ok(false),
    };
    let n = zip.len().min(128);
    for i in 0..n {
        if let Ok(e) = zip.by_index(i) {
            let name = e.name().replace('\\', "/");
            if name.starts_with("Takeout/") || name.contains("/Takeout/") {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

pub fn run_import(
    archive: &mut Archive,
    kind: SourceKind,
    path: &Path,
    opts: &ImportOpts,
) -> Result<ImportStats, CoreError> {
    match kind {
        SourceKind::WhatsappAndroidZip | SourceKind::WhatsappIosZip => {}
        other => {
            return Err(CoreError::Fatal(format!(
                "{other:?} importer is not implemented in this PR"
            )))
        }
    }
    if !path.is_file() {
        return Err(CoreError::Probe(format!(
            "import path is not a file: {}",
            path.display()
        )));
    }
    let zip_len = std::fs::metadata(path)?.len();
    if zip_len > opts.max_bytes {
        return Err(CoreError::Fatal(format!(
            "file {} bytes exceeds --max-bytes {}",
            zip_len, opts.max_bytes
        )));
    }

    let importer = WhatsappImporter { opts: opts.clone() };
    let probe = importer.probe(path)?;
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

    let import_err;
    let mut stats = {
        let mut ctx = DbImportContext::new(archive, run_id, source_id)?;
        match importer.import(path, &mut ctx) {
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
        mark_run(archive, run_id, "failed", None, Some(&e.to_string()))?;
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

    if let Err(e) = bulk_search_doc(archive, run_id) {
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
    Ok(stats)
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

fn bulk_search_doc(archive: &Archive, run_id: i64) -> Result<(), CoreError> {
    archive.conn.execute(
        "INSERT INTO search_doc (message_id, sent_at, platform, conversation_id, sender_identity_id, search_text)
         SELECT m.id, m.sent_at, c.platform, m.conversation_id, m.sender_identity_id,
                trim(COALESCE(m.subject, '') || ' ' || COALESCE(m.body_text, ''))
         FROM messages m
         JOIN conversations c ON c.id = m.conversation_id
         WHERE m.import_run_id = ?1
           AND NOT EXISTS (SELECT 1 FROM search_doc s WHERE s.message_id = m.id)",
        [run_id],
    )?;
    archive.conn.execute(
        "INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')",
        [],
    )?;
    Ok(())
}
