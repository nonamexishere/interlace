//! Security-scoped app bookmark create/resolve. macOS only; no-op elsewhere.
//! No URL fetch — local `NSURL` file bookmarks only.

use std::path::{Path, PathBuf};

/// Create a security-scoped app bookmark for `path`.
/// On `tauri:dev` (unsandboxed) this often fails — caller logs and ignores.
pub fn create_security_scoped_bookmark(path: &Path) -> Result<Vec<u8>, String> {
    #[cfg(target_os = "macos")]
    {
        macos::create(path)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = path;
        Err("security-scoped bookmarks are macOS-only".into())
    }
}

/// Resolve bookmark bytes with security scope and start accessing.
/// Stale or unreadable → `Err` (caller must not pretend the old path string works).
pub fn resolve_security_scoped_bookmark(bytes: &[u8]) -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        macos::resolve(bytes)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = bytes;
        Err("security-scoped bookmarks are macOS-only".into())
    }
}

#[cfg(target_os = "macos")]
mod macos {
    use std::path::{Path, PathBuf};
    use std::sync::Mutex;

    use objc2::rc::Retained;
    use objc2::runtime::Bool;
    use objc2_foundation::{
        NSData, NSString, NSURLBookmarkCreationOptions, NSURLBookmarkResolutionOptions, NSURL,
    };

    /// Kept alive so `startAccessingSecurityScopedResource` stays valid.
    static ACTIVE: Mutex<Option<Retained<NSURL>>> = Mutex::new(None);

    fn hold_access(url: Retained<NSURL>) {
        let mut slot = match ACTIVE.lock() {
            Ok(g) => g,
            Err(p) => p.into_inner(),
        };
        if let Some(old) = slot.take() {
            unsafe {
                old.stopAccessingSecurityScopedResource();
            }
        }
        *slot = Some(url);
    }

    pub fn create(path: &Path) -> Result<Vec<u8>, String> {
        let s = NSString::from_str(&path.to_string_lossy());
        let url = NSURL::fileURLWithPath_isDirectory(&s, true);
        let data = url
            .bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error(
                NSURLBookmarkCreationOptions::WithSecurityScope,
                None,
                None,
            )
            .map_err(|e| e.to_string())?;
        Ok(data.to_vec())
    }

    pub fn resolve(bytes: &[u8]) -> Result<PathBuf, String> {
        if bytes.is_empty() {
            return Err("empty bookmark".into());
        }
        let data = NSData::with_bytes(bytes);
        let mut stale = Bool::NO;
        let url = unsafe {
            NSURL::URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error(
                &data,
                NSURLBookmarkResolutionOptions::WithSecurityScope,
                None,
                &mut stale,
            )
        }
        .map_err(|e| e.to_string())?;
        if stale.as_bool() {
            return Err("stale bookmark".into());
        }
        let ok = unsafe { url.startAccessingSecurityScopedResource() };
        if !ok {
            return Err("startAccessingSecurityScopedResource failed".into());
        }
        let ns_path = url
            .path()
            .ok_or_else(|| "bookmark URL has no path".to_string())?;
        let path = PathBuf::from(ns_path.to_string());
        hold_access(url);
        Ok(path)
    }
}
