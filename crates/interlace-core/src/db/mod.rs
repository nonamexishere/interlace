//! SQLite archive open, migrate, flock.

mod lock;
mod migrate;
mod open;

pub use lock::LockMode;
pub use migrate::migrate;
pub use open::{init_archive, open_archive, Archive};

use thiserror::Error;

#[derive(Debug, Error)]
pub enum DbError {
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("sqlite: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("lock: archive in use by pid {pid} ({cmd})")]
    Lock { pid: u32, cmd: String },
    #[error("config: {0}")]
    Config(String),
}

pub type Result<T> = std::result::Result<T, DbError>;
