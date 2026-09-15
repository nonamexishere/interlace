//! Live-row rename + notes. Not a merge; does not touch identities / senders.

use serde::Serialize;

use crate::db::Archive;
use crate::model::CoreError;

use super::{person_display_name, person_identities, PersonIdentity};

/// Inspector / IPC body for one live person. Notes ride here, not `PersonSummary`.
#[derive(Debug, Clone, Serialize)]
pub struct PersonShow {
    pub id: i64,
    pub display_name: String,
    pub notes: Option<String>,
    pub identities: Vec<PersonIdentity>,
}

/// Trim `name`; empty / whitespace → `Parse`. Live row only. Same name is Ok no-op.
pub fn person_rename(archive: &mut Archive, id: i64, name: &str) -> Result<(), CoreError> {
    let name = name.trim();
    if name.is_empty() {
        return Err(CoreError::Parse("empty person name".into()));
    }
    let current = person_display_name(archive, id)?;
    if current == name {
        return Ok(());
    }
    let n = archive.conn.execute(
        "UPDATE persons SET display_name = ?1, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id = ?2 AND tombstoned_at IS NULL",
        rusqlite::params![name, id],
    )?;
    if n == 0 {
        return Err(CoreError::Config(format!("no live person {id}")));
    }
    Ok(())
}

/// Live row only. Empty / whitespace stores NULL (clear). Else trimmed text.
pub fn person_set_notes(archive: &mut Archive, id: i64, notes: &str) -> Result<(), CoreError> {
    let _ = person_display_name(archive, id)?;
    let stored = {
        let t = notes.trim();
        if t.is_empty() {
            None
        } else {
            Some(t.to_string())
        }
    };
    let n = archive.conn.execute(
        "UPDATE persons SET notes = ?1, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id = ?2 AND tombstoned_at IS NULL",
        rusqlite::params![stored, id],
    )?;
    if n == 0 {
        return Err(CoreError::Config(format!("no live person {id}")));
    }
    Ok(())
}

/// Today's `person_show` IPC body plus `notes`. Live row only.
pub fn person_show(archive: &Archive, id: i64) -> Result<PersonShow, CoreError> {
    let (display_name, notes): (String, Option<String>) = archive
        .conn
        .query_row(
            "SELECT display_name, notes FROM persons WHERE id=?1 AND tombstoned_at IS NULL",
            [id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .map_err(|_| CoreError::Config(format!("no live person {id}")))?;
    Ok(PersonShow {
        id,
        display_name,
        notes,
        identities: person_identities(archive, id)?,
    })
}
