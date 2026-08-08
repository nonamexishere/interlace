//! Core library for Interlace. Import, identity, search, and CAS live here.
//! Phase 1 public API is frozen in a later PR; this crate is a name-holding stub until then.

/// Placeholder kept from the 0.0.1 name-squat so `cargo test -p interlace-core` stays green.
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
