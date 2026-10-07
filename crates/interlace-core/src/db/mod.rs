//! SQLite archive open, migrate, flock.

mod lock;
mod migrate;
mod open;
mod snapshot;

pub use lock::LockMode;
pub use migrate::migrate;
pub use open::{archive_on_file, init_archive, open_archive, open_with_options, Archive};
pub use snapshot::{list_snapshots, restore_snapshot, restore_snapshot_at, snapshot_archive};

use crate::model::CoreError;

pub type Result<T> = std::result::Result<T, CoreError>;
