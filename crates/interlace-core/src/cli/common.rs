use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

use crate::model::CoreError;
use crate::session::read_last_path;

pub(super) struct CliError {
    msg: String,
    code: u8,
}

impl CliError {
    pub(super) fn user(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 1,
        }
    }
    pub(super) fn fatal(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 2,
        }
    }
    pub(super) fn doctor(m: impl Into<String>) -> Self {
        Self {
            msg: m.into(),
            code: 3,
        }
    }
    pub(super) fn code(&self) -> u8 {
        self.code
    }
}

impl std::fmt::Display for CliError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.msg)
    }
}

impl From<CoreError> for CliError {
    fn from(e: CoreError) -> Self {
        match e {
            CoreError::Lock { .. }
            | CoreError::Config(_)
            | CoreError::Probe(_)
            | CoreError::TakeoutLayout(_)
            | CoreError::Parse(_) => Self::user(e.to_string()),
            _ => Self::fatal(e.to_string()),
        }
    }
}

impl From<std::io::Error> for CliError {
    fn from(e: std::io::Error) -> Self {
        Self::fatal(e.to_string())
    }
}

impl From<rusqlite::Error> for CliError {
    fn from(e: rusqlite::Error) -> Self {
        Self::fatal(e.to_string())
    }
}

pub(super) fn resolve_path(explicit: Option<PathBuf>) -> Result<PathBuf, CliError> {
    if let Some(p) = explicit {
        return Ok(p);
    }
    read_last_path().ok_or_else(|| {
        CliError::user("run `interlace init --path DIR --phone-region CC` or pass --path")
    })
}

pub(super) fn warn_mode(root: &Path) {
    #[cfg(unix)]
    if let Ok(meta) = fs::metadata(root) {
        let mode = meta.permissions().mode() & 0o777;
        if mode & 0o077 != 0 {
            eprintln!(
                "warning: archive mode {:o} is wider than 0700; chmod 700 {}",
                mode,
                root.display()
            );
        }
    }
}

pub(super) fn warn_cloud(root: &Path) {
    if let Some(w) = crate::session::cloud_warning(root) {
        eprintln!("warning: {w}");
    }
}
