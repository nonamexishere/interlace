//! FTS search and person timeline. Bodies land in PR9.

use crate::db::Archive;
use crate::model::{CoreError, SearchHit, SearchQuery};

pub fn search(_archive: &Archive, _q: &SearchQuery) -> Result<Vec<SearchHit>, CoreError> {
    unimplemented!("search lands in PR9")
}

pub fn person_timeline(
    _archive: &Archive,
    _person_id: i64,
    _include_groups: bool,
    _limit: u32,
) -> Result<Vec<SearchHit>, CoreError> {
    unimplemented!("person_timeline lands in PR9")
}
