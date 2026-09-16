//! Live-row UPDATE of display_name / notes. Not a merge.

use serde::Serialize;

use crate::db::Archive;
use crate::model::CoreError;

use super::{person_display_name, person_identities, PersonIdentity};

#[derive(Debug, Clone, Serialize)]
pub struct PersonShow {
    pub id: i64,
    pub display_name: String,
    pub notes: Option<String>,
    pub identities: Vec<PersonIdentity>,
}

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
