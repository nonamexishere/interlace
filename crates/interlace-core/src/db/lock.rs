use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::unix::io::AsRawFd;
use std::path::Path;

use super::{DbError, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LockMode {
    Shared,
    Exclusive,
}

pub struct ArchiveLock {
    /// Held for process lifetime so flock is released on drop.
    #[allow(dead_code)]
    file: File,
}

impl ArchiveLock {
    pub fn acquire(lock_path: &Path, mode: LockMode) -> Result<Self> {
        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(lock_path)?;

        let op = match mode {
            LockMode::Exclusive => libc::LOCK_EX | libc::LOCK_NB,
            LockMode::Shared => libc::LOCK_SH | libc::LOCK_NB,
        };
        let rc = unsafe { libc::flock(file.as_raw_fd(), op) };
        if rc != 0 {
            let (pid, cmd) = read_holder(&mut file);
            return Err(DbError::Lock { pid, cmd });
        }
        if matches!(mode, LockMode::Exclusive) {
            file.set_len(0)?;
            file.seek(SeekFrom::Start(0))?;
            let pid = std::process::id();
            let cmd = std::env::args()
                .next()
                .unwrap_or_else(|| "interlace".into());
            writeln!(file, "{pid} {cmd}")?;
            file.flush()?;
        }
        Ok(Self { file })
    }
}

fn read_holder(file: &mut File) -> (u32, String) {
    let _ = file.seek(SeekFrom::Start(0));
    let mut buf = String::new();
    let _ = file.read_to_string(&mut buf);
    let mut parts = buf.split_whitespace();
    let pid = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let cmd = parts.collect::<Vec<_>>().join(" ");
    let cmd = if cmd.is_empty() {
        "unknown".into()
    } else {
        cmd
    };
    (pid, cmd)
}
