//! SQLite archive open, migrate, flock.

mod lock;
mod migrate;
mod open;

pub use lock::LockMode;
pub use migrate::migrate;
pub use open::{init_archive, open_archive, open_with_options, Archive};

use crate::model::CoreError;

pub type Result<T> = std::result::Result<T, CoreError>;
