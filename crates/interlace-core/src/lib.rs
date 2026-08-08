//! Core library for Interlace. Import, identity, search, and CAS live here.

pub mod db;

pub use db::{init_archive, migrate, open_archive, Archive, LockMode};

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
