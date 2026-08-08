//! Identity resolve / merge / undo. Bodies land in PR8.

use crate::db::Archive;
use crate::model::{CoreError, ImportStats, PersonMergeOpts};

pub fn resolve_run(_archive: &mut Archive, _run_id: i64) -> Result<ImportStats, CoreError> {
    unimplemented!("identity resolver lands in PR8")
}

pub fn person_merge(
    _archive: &mut Archive,
    _a: i64,
    _b: i64,
    _opts: PersonMergeOpts,
) -> Result<i64, CoreError> {
    unimplemented!("person_merge lands in PR8")
}

pub fn person_unlink(_archive: &mut Archive, _identity_id: i64) -> Result<(), CoreError> {
    unimplemented!("person_unlink lands in PR8")
}

pub fn person_undo(_archive: &mut Archive, _event_id: i64) -> Result<(), CoreError> {
    unimplemented!("person_undo lands in PR8")
}

pub fn review_resolve(
    _archive: &mut Archive,
    _review_id: i64,
    _accept: bool,
) -> Result<(), CoreError> {
    unimplemented!("review_resolve lands in PR8")
}
