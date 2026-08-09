//! Core library for Interlace, a local-first offline archive.
//!
//! Message → Identity → Person. No network client. See `docs/design/DESIGN.md`.

pub mod cas;
pub mod cli;
pub mod db;
pub mod identity;
pub mod import;
pub mod model;
pub mod people;
pub mod search;
pub mod session;

pub use db::{init_archive, migrate, open_archive, open_with_options, Archive, LockMode};
pub use identity::{
    person_merge, person_undo, person_unlink, resolve_run, review_list, review_resolve, review_show,
};
pub use import::{
    ContactsImporter, GmailMboxImporter, ImportContext, ImporterRegistry, SourceImporter,
    TakeoutImporter, WhatsappImporter,
};
pub use model::*;
pub use people::{
    attachments_for, person_display_name, person_identities, person_list, person_timeline_rows,
    recent_link_events, AttachmentRef, LinkEvent, PersonIdentity, PersonSummary, TimelineRow,
};
pub use search::{
    build_search_text, expand_query, extra_ascii_fold, index_import_run, person_timeline,
    rebuild_fts, search, turkish_fold,
};
pub use session::{
    cloud_warning, init_owner_archive, read_last_path, validate_phone_region, write_last_path,
};

/// Placeholder kept from the 0.0.1 name-squat so existing tests stay green.
pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        assert_eq!(add(2, 2), 4);
    }
}
