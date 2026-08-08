//! Thin re-export of [`interlace_core::cli`]. Unpublished (`publish = false`).
//! Published bins call `interlace_core::cli::run` directly so crates.io
//! packages do not depend on this crate.

pub fn run() -> std::process::ExitCode {
    interlace_core::cli::run()
}
