//! Core library for Interlace. Import, identity, search, and CAS live here.

pub mod cas;
pub mod db;
pub mod identity;
pub mod import;
pub mod model;
pub mod search;

pub use db::{init_archive, migrate, open_archive, open_with_options, Archive, LockMode};
pub use identity::{person_merge, person_undo, person_unlink, resolve_run, review_resolve};
pub use import::{
    ContactsImporter, GmailMboxImporter, ImportContext, ImporterRegistry, SourceImporter,
    TakeoutImporter, WhatsappImporter,
};
pub use model::*;
pub use search::{person_timeline, search};

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
