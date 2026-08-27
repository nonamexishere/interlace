//! SQLite-backed `ImportContext`.

use std::path::Path;

use super::ImportContext;
use crate::cas::cas_put;
use crate::db::Archive;
use crate::model::*;

mod persist;
mod sql;

#[allow(unused_imports)]
pub use sql::{
    attach_kind_sql, conv_kind_sql, identity_kind_sql, msg_kind_sql, platform_sql, precision_sql,
    recipient_sql, severity_sql, source_kind_sql,
};

const COMMIT_EVERY_MSGS: u64 = 1000;
const COMMIT_EVERY_CAS: u64 = 8 * 1024 * 1024;

pub struct DbImportContext<'a> {
    pub archive: &'a mut Archive,
    run_id: i64,
    source_id: i64,
    pub stats: ImportStats,
    msgs_since: u64,
    cas_since: u64,
    in_tx: bool,
    cancel: Option<ImportCancel>,
}

impl<'a> DbImportContext<'a> {
    pub fn new(
        archive: &'a mut Archive,
        run_id: i64,
        source_id: i64,
        cancel: Option<ImportCancel>,
    ) -> Result<Self, CoreError> {
        let mut ctx = Self {
            archive,
            run_id,
            source_id,
            stats: ImportStats::default(),
            msgs_since: 0,
            cas_since: 0,
            in_tx: false,
            cancel,
        };
        ctx.begin()?;
        Ok(ctx)
    }

    fn check_cancel(&self) -> Result<(), CoreError> {
        if self.cancel.as_ref().is_some_and(|c| c.is_cancelled()) {
            Err(CoreError::Cancelled)
        } else {
            Ok(())
        }
    }

    fn begin(&mut self) -> Result<(), CoreError> {
        if !self.in_tx {
            self.archive.conn.execute_batch("BEGIN IMMEDIATE")?;
            self.in_tx = true;
        }
        Ok(())
    }

    pub fn commit(&mut self) -> Result<(), CoreError> {
        if self.in_tx {
            self.archive.conn.execute_batch("COMMIT")?;
            self.in_tx = false;
        }
        Ok(())
    }

    pub fn rollback(&mut self) {
        if self.in_tx {
            let _ = self.archive.conn.execute_batch("ROLLBACK");
            self.in_tx = false;
        }
    }

    fn setting(&self, key: &str) -> Result<Option<String>, CoreError> {
        let mut stmt = self
            .archive
            .conn
            .prepare("SELECT value FROM settings WHERE key = ?1")?;
        let mut rows = stmt.query([key])?;
        match rows.next()? {
            Some(r) => Ok(Some(r.get(0)?)),
            None => Ok(None),
        }
    }

    pub fn phone_region(&self) -> Result<Option<String>, CoreError> {
        self.setting("default_phone_region")
    }
}

impl ImportContext for DbImportContext<'_> {
    fn run_id(&self) -> i64 {
        self.run_id
    }
    fn source_id(&self) -> i64 {
        self.source_id
    }
    fn archive_root(&self) -> &Path {
        &self.archive.root
    }

    fn persist_identity(&mut self, rec: NewIdentity) -> Result<i64, CoreError> {
        let plat = platform_sql(rec.platform);
        let kind = identity_kind_sql(rec.kind);
        let n = self.archive.conn.execute(
            "INSERT OR IGNORE INTO identities(platform, kind, value_raw, value_normalized, display_name)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![plat, kind, rec.value_raw, rec.value_normalized, rec.display_name],
        )?;
        if n == 1 {
            self.stats.inserted_identities += 1;
        } else if rec.display_name.is_some() {
            self.archive.conn.execute(
                "UPDATE identities SET display_name = COALESCE(display_name, ?1)
                 WHERE platform = ?2 AND kind = ?3 AND value_normalized = ?4",
                rusqlite::params![rec.display_name, plat, kind, rec.value_normalized],
            )?;
        }
        let id: i64 = self.archive.conn.query_row(
            "SELECT id FROM identities WHERE platform = ?1 AND kind = ?2 AND value_normalized = ?3",
            rusqlite::params![plat, kind, rec.value_normalized],
            |r| r.get(0),
        )?;
        Ok(id)
    }

    fn persist_conversation(&mut self, rec: NewConversation) -> Result<i64, CoreError> {
        let plat = platform_sql(rec.platform);
        let kind = conv_kind_sql(rec.kind);
        self.archive.conn.execute(
            "INSERT INTO conversations(platform, kind, source_id, native_id, title, extra_json)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)
             ON CONFLICT(platform, native_id) DO UPDATE SET
               kind = CASE WHEN excluded.kind = 'group' THEN 'group' ELSE conversations.kind END,
               title = COALESCE(excluded.title, conversations.title),
               extra_json = COALESCE(excluded.extra_json, conversations.extra_json),
               source_id = COALESCE(conversations.source_id, excluded.source_id)",
            rusqlite::params![
                plat,
                kind,
                self.source_id,
                rec.native_id,
                rec.title,
                rec.extra_json
            ],
        )?;
        let id: i64 = self.archive.conn.query_row(
            "SELECT id FROM conversations WHERE platform = ?1 AND native_id = ?2",
            rusqlite::params![plat, rec.native_id],
            |r| r.get(0),
        )?;
        Ok(id)
    }

    fn persist_message(&mut self, rec: NewMessage) -> Result<PersistOutcome, CoreError> {
        let prec = precision_sql(rec.sent_at_precision);
        let kind = msg_kind_sql(rec.kind);
        let n = self.archive.conn.execute(
            "INSERT OR IGNORE INTO messages(
                conversation_id, source_id, import_run_id, sender_identity_id,
                sent_at, sent_at_precision, kind, subject, body_text, body_html,
                native_id, idempotency_key, gm_thrid, in_reply_to, payload_json
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
            rusqlite::params![
                rec.conversation_id,
                self.source_id,
                self.run_id,
                rec.sender_identity_id,
                rec.sent_at,
                prec,
                kind,
                rec.subject,
                rec.body_text,
                rec.body_html,
                rec.native_id,
                rec.idempotency_key,
                rec.gm_thrid,
                rec.in_reply_to,
                rec.payload_json,
            ],
        )?;
        let message_id: i64 = self.archive.conn.query_row(
            "SELECT id FROM messages WHERE idempotency_key = ?1",
            [&rec.idempotency_key],
            |r| r.get(0),
        )?;
        if n == 0 {
            if !rec.labels.is_empty() {
                self.persist_labels(message_id, &rec.labels)?;
            }
            self.stats.skipped_dupes += 1;
            return Ok(PersistOutcome::Duplicate { message_id });
        }
        for (iid, role) in &rec.recipients {
            self.archive.conn.execute(
                "INSERT OR IGNORE INTO message_recipients(message_id, identity_id, role)
                 VALUES (?1, ?2, ?3)",
                rusqlite::params![message_id, iid, recipient_sql(*role)],
            )?;
        }
        if !rec.labels.is_empty() {
            self.persist_labels(message_id, &rec.labels)?;
        }
        if let Some(sid) = rec.sender_identity_id {
            self.archive.conn.execute(
                "INSERT OR IGNORE INTO conversation_participants(conversation_id, identity_id, role)
                 VALUES (?1, ?2, 'member')",
                rusqlite::params![rec.conversation_id, sid],
            )?;
        }
        if let Some(ref ts) = rec.sent_at {
            self.archive.conn.execute(
                "UPDATE conversations SET last_message_at = CASE
                    WHEN last_message_at IS NULL OR last_message_at < ?1 THEN ?1
                    ELSE last_message_at END
                 WHERE id = ?2",
                rusqlite::params![ts, rec.conversation_id],
            )?;
        }
        self.stats.inserted_messages += 1;
        self.msgs_since += 1;
        Ok(PersistOutcome::Inserted { message_id })
    }

    fn persist_labels(&mut self, message_id: i64, labels: &[String]) -> Result<(), CoreError> {
        for name in labels {
            self.archive.conn.execute(
                "INSERT OR IGNORE INTO labels(platform, name) VALUES ('gmail', ?1)",
                [name],
            )?;
            let lid: i64 = self.archive.conn.query_row(
                "SELECT id FROM labels WHERE platform = 'gmail' AND name = ?1",
                [name],
                |r| r.get(0),
            )?;
            self.archive.conn.execute(
                "INSERT OR IGNORE INTO message_labels(message_id, label_id) VALUES (?1, ?2)",
                rusqlite::params![message_id, lid],
            )?;
        }
        Ok(())
    }

    fn persist_attachment(
        &mut self,
        rec: NewAttachment,
        bytes: Option<&[u8]>,
    ) -> Result<(), CoreError> {
        persist::persist_attachment(self, rec, bytes)
    }

    fn persist_contact(&mut self, rec: NewContact) -> Result<i64, CoreError> {
        persist::persist_contact(self, rec)
    }

    fn warn(&mut self, w: Warning) -> Result<(), CoreError> {
        self.archive.conn.execute(
            "INSERT INTO import_warnings(import_run_id, severity, locator, kind, detail, raw_excerpt)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            rusqlite::params![
                self.run_id,
                severity_sql(w.severity),
                w.locator,
                w.kind,
                w.detail,
                w.raw_excerpt
            ],
        )?;
        self.stats.warnings += 1;
        if matches!(w.severity, Severity::Reject) {
            self.stats.rejected += 1;
        }
        Ok(())
    }

    fn checkpoint(&mut self, c: Checkpoint) -> Result<(), CoreError> {
        let val = serde_json::to_string(&c.cursor_value)
            .map_err(|e| CoreError::Fatal(format!("checkpoint json: {e}")))?;
        self.archive.conn.execute(
            "INSERT INTO import_checkpoints(import_run_id, cursor_kind, cursor_value)
             VALUES (?1, ?2, ?3)
             ON CONFLICT(import_run_id, cursor_kind) DO UPDATE SET
               cursor_value = excluded.cursor_value,
               updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            rusqlite::params![self.run_id, c.cursor_kind, val],
        )?;
        Ok(())
    }

    fn load_checkpoint(&self, cursor_kind: &str) -> Result<Option<Checkpoint>, CoreError> {
        let mut stmt = self.archive.conn.prepare(
            "SELECT cursor_value FROM import_checkpoints
             WHERE import_run_id = ?1 AND cursor_kind = ?2",
        )?;
        let mut rows = stmt.query(rusqlite::params![self.run_id, cursor_kind])?;
        match rows.next()? {
            None => Ok(None),
            Some(r) => {
                let raw: String = r.get(0)?;
                let cursor_value: serde_json::Value = serde_json::from_str(&raw)
                    .map_err(|e| CoreError::Parse(format!("checkpoint: {e}")))?;
                Ok(Some(Checkpoint {
                    cursor_kind: cursor_kind.to_string(),
                    cursor_value,
                }))
            }
        }
    }

    fn heartbeat(&mut self) -> Result<(), CoreError> {
        self.check_cancel()?;
        self.archive.conn.execute(
            "UPDATE import_runs SET heartbeat_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE id = ?1",
            [self.run_id],
        )?;
        Ok(())
    }

    fn maybe_commit(&mut self) -> Result<(), CoreError> {
        self.check_cancel()?;
        if self.msgs_since >= COMMIT_EVERY_MSGS || self.cas_since >= COMMIT_EVERY_CAS {
            self.heartbeat()?;
            self.commit()?;
            self.begin()?;
            self.msgs_since = 0;
            self.cas_since = 0;
        }
        Ok(())
    }

    fn owner_self_folds(&self) -> Result<Vec<String>, CoreError> {
        persist::owner_self_folds(self)
    }

    fn link_identity_to_self_person(&mut self, identity_id: i64) -> Result<(), CoreError> {
        persist::link_identity_to_self_person(self, identity_id)
    }

    fn set_participant_role(
        &mut self,
        conversation_id: i64,
        identity_id: i64,
        role: &str,
    ) -> Result<(), CoreError> {
        self.archive.conn.execute(
            "UPDATE conversation_participants SET role = ?3
             WHERE conversation_id = ?1 AND identity_id = ?2",
            rusqlite::params![conversation_id, identity_id, role],
        )?;
        Ok(())
    }

    fn cas_put(&mut self, bytes: &[u8], mime_hint: Option<&str>) -> Result<String, CoreError> {
        let h = cas_put(self.archive, bytes, mime_hint)?;
        self.cas_since += bytes.len() as u64;
        Ok(h)
    }
}
