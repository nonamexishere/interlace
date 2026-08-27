//! Attachment / contact / self-link persist helpers.

use rusqlite::OptionalExtension;

use super::sql::{attach_kind_sql, identity_kind_sql};
use super::DbImportContext;
use crate::import::ImportContext;
use crate::model::*;

pub(super) fn persist_attachment(
    ctx: &mut DbImportContext<'_>,
    rec: NewAttachment,
    bytes: Option<&[u8]>,
) -> Result<(), CoreError> {
    let mut hash: Option<String> = None;
    if let Some(b) = bytes {
        if rec.omitted || rec.missing {
            // still store if caller passed bytes (upgrade path)
        }
        let h = ctx.cas_put(b, rec.mime.as_deref())?;
        hash = Some(h);
    }

    let existing: Option<(i64, Option<String>, i64, i64)> = {
        let mut stmt = ctx.archive.conn.prepare(
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
                ctx.archive.conn.execute(
                    "UPDATE attachments SET cas_hash = ?1, omitted = 0, missing = 0,
                            size = COALESCE(?2, size), mime = COALESCE(?3, mime),
                            kind = ?4
                     WHERE id = ?5",
                    rusqlite::params![h, rec.size, rec.mime, attach_kind_sql(rec.kind), aid],
                )?;
                ctx.archive.conn.execute(
                    "UPDATE cas_blobs SET refcount = refcount + 1 WHERE hash = ?1",
                    [h],
                )?;
                ctx.stats.upgraded_attachments += 1;
                ctx.stats.attachments_stored += 1;
            }
        }
        return Ok(());
    }

    ctx.archive.conn.execute(
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
        ctx.archive.conn.execute(
            "UPDATE cas_blobs SET refcount = refcount + 1 WHERE hash = ?1",
            [h],
        )?;
        ctx.stats.attachments_stored += 1;
    } else if rec.omitted {
        ctx.stats.attachments_omitted += 1;
    } else if rec.missing {
        ctx.stats.attachments_missing += 1;
    }
    Ok(())
}

pub(super) fn persist_contact(
    ctx: &mut DbImportContext<'_>,
    rec: NewContact,
) -> Result<i64, CoreError> {
    let existing: Option<i64> = {
        let mut stmt = ctx
            .archive
            .conn
            .prepare("SELECT id FROM contacts_raw WHERE source_id = ?1 AND uid = ?2 LIMIT 1")?;
        let mut rows = stmt.query(rusqlite::params![ctx.source_id(), rec.uid])?;
        match rows.next()? {
            Some(r) => Some(r.get(0)?),
            None => None,
        }
    };
    if let Some(id) = existing {
        return Ok(id);
    }

    let photo_hash = match rec.photo_bytes.as_deref() {
        Some(b) if !b.is_empty() => Some(ctx.cas_put(b, Some("image/jpeg"))?),
        _ => None,
    };

    ctx.archive.conn.execute(
        "INSERT INTO contacts_raw(
            source_id, uid, fn, n_family, n_given, org, photo_cas_hash, raw_excerpt
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        rusqlite::params![
            ctx.source_id(),
            rec.uid,
            rec.fn_,
            rec.n_family,
            rec.n_given,
            rec.org,
            photo_hash,
            rec.raw_excerpt
        ],
    )?;
    let contact_id = ctx.archive.conn.last_insert_rowid();

    let display = rec
        .fn_
        .as_ref()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .or_else(|| rec.channels.first().map(|c| c.value_raw.clone()))
        .unwrap_or_else(|| "Unnamed contact".into());

    ctx.archive.conn.execute(
        "INSERT INTO persons(display_name, is_self) VALUES (?1, 0)",
        [&display],
    )?;
    let person_id = ctx.archive.conn.last_insert_rowid();

    for ch in &rec.channels {
        if !matches!(ch.kind, IdentityKind::Phone | IdentityKind::Email) {
            continue;
        }
        let iid = ctx.persist_identity(NewIdentity {
            platform: Platform::Contacts,
            kind: ch.kind,
            value_raw: ch.value_raw.clone(),
            value_normalized: ch.value_normalized.clone(),
            display_name: rec.fn_.clone(),
        })?;
        ctx.archive.conn.execute(
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
        ctx.archive.conn.execute(
            "INSERT OR IGNORE INTO person_identities(
                person_id, identity_id, link_reason, confidence, created_by
             ) VALUES (?1, ?2, 'takeout_vcard', 1.0, 'system')",
            rusqlite::params![person_id, iid],
        )?;
    }
    Ok(contact_id)
}

pub(super) fn owner_self_folds(ctx: &DbImportContext<'_>) -> Result<Vec<String>, CoreError> {
    use crate::import::locale::name_fold_join;
    let mut out = Vec::new();
    let owner: Option<String> = ctx.archive.conn.query_row(
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
    let mut stmt = ctx.archive.conn.prepare(
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

pub(super) fn link_identity_to_self_person(
    ctx: &mut DbImportContext<'_>,
    identity_id: i64,
) -> Result<(), CoreError> {
    let pid: Option<i64> = ctx
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
    ctx.archive.conn.execute(
        "INSERT OR IGNORE INTO self_identities(identity_id) VALUES (?1)",
        [identity_id],
    )?;
    let n = ctx.archive.conn.execute(
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
        ctx.archive.conn.execute(
            "INSERT INTO identity_link_events(actor, op, payload_json) VALUES ('system', 'link', ?1)",
            [payload],
        )?;
    }
    Ok(())
}
