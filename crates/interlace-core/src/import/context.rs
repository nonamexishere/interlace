//! SQLite-backed `ImportContext`.

use std::path::Path;

use rusqlite::OptionalExtension;

use super::ImportContext;
use crate::cas::cas_put;
use crate::db::Archive;
use crate::model::*;

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
        let mut hash: Option<String> = None;
        if let Some(b) = bytes {
            if rec.omitted || rec.missing {
                // still store if caller passed bytes (upgrade path)
            }
            let h = self.cas_put(b, rec.mime.as_deref())?;
            hash = Some(h);
        }

        let existing: Option<(i64, Option<String>, i64, i64)> = {
            let mut stmt = self.archive.conn.prepare(
                "SELECT id, cas_hash, omitted, missing FROM attachments
                 WHERE message_id = ?1 AND (
                    (?2 IS NULL AND filename IS NULL) OR filename = ?2
                 ) LIMIT 1",
            )?;
            let mut rows = stmt.query(rusqlite::params![rec.message_id, rec.filename])?;
            match rows.next()? {
                Some(r) => Some((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
                None => None,
            }
        };

        if let Some((aid, old_hash, omitted, _missing)) = existing {
            if let Some(ref h) = hash {
                let needs = old_hash.is_none() || omitted != 0;
                if needs {
                    self.archive.conn.execute(
                        "UPDATE attachments SET cas_hash = ?1, omitted = 0, missing = 0,
                                size = COALESCE(?2, size), mime = COALESCE(?3, mime),
                                kind = ?4
                         WHERE id = ?5",
                        rusqlite::params![h, rec.size, rec.mime, attach_kind_sql(rec.kind), aid],
                    )?;
                    self.archive.conn.execute(
                        "UPDATE cas_blobs SET refcount = refcount + 1 WHERE hash = ?1",
                        [h],
                    )?;
                    self.stats.upgraded_attachments += 1;
                    self.stats.attachments_stored += 1;
                }
            }
            return Ok(());
        }

        self.archive.conn.execute(
            "INSERT INTO attachments(
                message_id, cas_hash, filename, mime, size, kind,
                content_id, part_index, omitted, missing
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            rusqlite::params![
                rec.message_id,
                hash,
                rec.filename,
                rec.mime,
                rec.size,
                attach_kind_sql(rec.kind),
                rec.content_id,
                rec.part_index,
                rec.omitted as i64,
                rec.missing as i64,
            ],
        )?;
        if let Some(ref h) = hash {
            self.archive.conn.execute(
                "UPDATE cas_blobs SET refcount = refcount + 1 WHERE hash = ?1",
                [h],
            )?;
            self.stats.attachments_stored += 1;
        } else if rec.omitted {
            self.stats.attachments_omitted += 1;
        } else if rec.missing {
            self.stats.attachments_missing += 1;
        }
        Ok(())
    }

    fn persist_contact(&mut self, rec: NewContact) -> Result<i64, CoreError> {
        let existing: Option<i64> = {
            let mut stmt = self
                .archive
                .conn
                .prepare("SELECT id FROM contacts_raw WHERE source_id = ?1 AND uid = ?2 LIMIT 1")?;
            let mut rows = stmt.query(rusqlite::params![self.source_id(), rec.uid])?;
            match rows.next()? {
                Some(r) => Some(r.get(0)?),
                None => None,
            }
        };
        if let Some(id) = existing {
            return Ok(id);
        }

        let photo_hash = match rec.photo_bytes.as_deref() {
            Some(b) if !b.is_empty() => Some(self.cas_put(b, Some("image/jpeg"))?),
            _ => None,
        };

        self.archive.conn.execute(
            "INSERT INTO contacts_raw(
                source_id, uid, fn, n_family, n_given, org, photo_cas_hash, raw_excerpt
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            rusqlite::params![
                self.source_id(),
                rec.uid,
                rec.fn_,
                rec.n_family,
                rec.n_given,
                rec.org,
                photo_hash,
                rec.raw_excerpt
            ],
        )?;
        let contact_id = self.archive.conn.last_insert_rowid();

        let display = rec
            .fn_
            .as_ref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .or_else(|| rec.channels.first().map(|c| c.value_raw.clone()))
            .unwrap_or_else(|| "Unnamed contact".into());

        self.archive.conn.execute(
            "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
            [&display],
        )?;
        let person_id = self.archive.conn.last_insert_rowid();

        for ch in &rec.channels {
            if !matches!(ch.kind, IdentityKind::Phone | IdentityKind::Email) {
                continue;
            }
            let iid = self.persist_identity(NewIdentity {
                platform: Platform::Contacts,
                kind: ch.kind,
                value_raw: ch.value_raw.clone(),
                value_normalized: ch.value_normalized.clone(),
                display_name: rec.fn_.clone(),
            })?;
            self.archive.conn.execute(
                "INSERT INTO contact_channels(
                    contact_id, kind, value_raw, value_normalized, pref, identity_id
                 ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                rusqlite::params![
                    contact_id,
                    identity_kind_sql(ch.kind),
                    ch.value_raw,
                    ch.value_normalized,
                    ch.pref as i64,
                    iid
                ],
            )?;
            self.archive.conn.execute(
                "INSERT OR IGNORE INTO person_identities(
                    person_id, identity_id, link_reason, confidence, created_by
                 ) VALUES (?1, ?2, 'takeout_vcard', 1.0, 'system')",
                rusqlite::params![person_id, iid],
            )?;
        }
        Ok(contact_id)
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
        use super::locale::name_fold_join;
        let mut out = Vec::new();
        let owner: Option<String> = self.archive.conn.query_row(
            "SELECT owner_display_name FROM archive_meta WHERE id = 1",
            [],
            |r| r.get(0),
        )?;
        if let Some(n) = owner {
            let f = name_fold_join(&n);
            if !f.is_empty() {
                out.push(f);
            }
        }
        let mut stmt = self.archive.conn.prepare(
            "SELECT COALESCE(i.display_name, ''), i.value_normalized, i.kind
             FROM self_identities s
             JOIN identities i ON i.id = s.identity_id",
        )?;
        let rows = stmt.query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, String>(2)?,
            ))
        })?;
        for row in rows {
            let (disp, norm, _kind) = row?;
            for cand in [disp.as_str(), norm.as_str()] {
                if cand.is_empty() {
                    continue;
                }
                let f = name_fold_join(cand);
                if !f.is_empty() && !out.contains(&f) {
                    out.push(f);
                }
            }
        }
        Ok(out)
    }

    fn link_identity_to_self_person(&mut self, identity_id: i64) -> Result<(), CoreError> {
        let pid: Option<i64> = self
            .archive
            .conn
            .query_row(
                "SELECT id FROM persons WHERE is_self = 1 AND tombstoned_at IS NULL LIMIT 1",
                [],
                |r| r.get(0),
            )
            .optional()?;
        let Some(pid) = pid else {
            return Ok(());
        };
        self.archive.conn.execute(
            "INSERT OR IGNORE INTO self_identities(identity_id) VALUES (?1)",
            [identity_id],
        )?;
        let n = self.archive.conn.execute(
            "INSERT OR IGNORE INTO person_identities(
                person_id, identity_id, link_reason, confidence, created_by
             ) VALUES (?1, ?2, 'self_declared', 1.0, 'system')",
            rusqlite::params![pid, identity_id],
        )?;
        if n == 1 {
            let payload = serde_json::json!({
                "person_id": pid,
                "identity_id": identity_id,
                "link_reason": "self_declared",
                "confidence": 1.0,
            })
            .to_string();
            self.archive.conn.execute(
                "INSERT INTO identity_link_events(actor, op, payload_json) VALUES ('system', 'link', ?1)",
                [payload],
            )?;
        }
        Ok(())
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

pub fn platform_sql(p: Platform) -> &'static str {
    match p {
        Platform::Whatsapp => "whatsapp",
        Platform::Gmail => "gmail",
        Platform::Contacts => "contacts",
        Platform::Owner => "owner",
    }
}

pub fn identity_kind_sql(k: IdentityKind) -> &'static str {
    match k {
        IdentityKind::Phone => "phone",
        IdentityKind::Email => "email",
        IdentityKind::WhatsappJid => "whatsapp_jid",
        IdentityKind::DisplayName => "display_name",
        IdentityKind::GoogleContactUid => "google_contact_uid",
        IdentityKind::Username => "username",
    }
}

pub fn conv_kind_sql(k: ConversationKind) -> &'static str {
    match k {
        ConversationKind::Dm => "dm",
        ConversationKind::Group => "group",
        ConversationKind::EmailThread => "email_thread",
    }
}

pub fn msg_kind_sql(k: MessageKind) -> &'static str {
    match k {
        MessageKind::Text => "text",
        MessageKind::Media => "media",
        MessageKind::Mixed => "mixed",
        MessageKind::System => "system",
        MessageKind::Email => "email",
        MessageKind::Unknown => "unknown",
        MessageKind::Tombstone => "tombstone",
    }
}

pub fn precision_sql(p: SentAtPrecision) -> &'static str {
    match p {
        SentAtPrecision::Second => "second",
        SentAtPrecision::Minute => "minute",
        SentAtPrecision::Unknown => "unknown",
    }
}

pub fn attach_kind_sql(k: AttachmentKind) -> &'static str {
    match k {
        AttachmentKind::File => "file",
        AttachmentKind::Inline => "inline",
        AttachmentKind::Voice => "voice",
        AttachmentKind::Image => "image",
        AttachmentKind::Video => "video",
        AttachmentKind::Sticker => "sticker",
        AttachmentKind::Vcf => "vcf",
    }
}

pub fn recipient_sql(r: RecipientRole) -> &'static str {
    match r {
        RecipientRole::To => "to",
        RecipientRole::Cc => "cc",
        RecipientRole::Bcc => "bcc",
    }
}

pub fn severity_sql(s: Severity) -> &'static str {
    match s {
        Severity::Warn => "warn",
        Severity::Reject => "reject",
        Severity::UnknownRow => "unknown_row",
    }
}

pub fn source_kind_sql(k: SourceKind) -> &'static str {
    match k {
        SourceKind::WhatsappAndroidZip => "whatsapp_android_zip",
        SourceKind::WhatsappIosZip => "whatsapp_ios_zip",
        SourceKind::TakeoutZip => "takeout_zip",
        SourceKind::TakeoutDir => "takeout_dir",
        SourceKind::GmailMbox => "gmail_mbox",
        SourceKind::ContactsVcf => "contacts_vcf",
        SourceKind::ContactsCsv => "contacts_csv",
    }
}
