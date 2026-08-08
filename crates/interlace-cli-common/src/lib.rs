//! Shared process entry for `interlace` and `interlace-cli`.
//! Unpublished (`publish = false`); not a crates.io name.

/// Run the CLI. Phase 1 clap surface lands in PR10; both bins must stay identical.
pub fn run() {
    println!("Hello, world!");
}
