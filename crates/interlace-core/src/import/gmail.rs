//! Gmail mboxrd importer (M1–M3).

use std::fs;
use std::path::Path;

use super::{ImportContext, SourceImporter};
use crate::model::*;

mod mbox;
mod parse;
mod persist;

pub(crate) const HEADER_CAP: usize = 1024 * 1024;

#[derive(Default)]
pub struct GmailMboxImporter {
    pub opts: ImportOpts,
}

impl SourceImporter for GmailMboxImporter {
    fn id(&self) -> SourceKind {
        SourceKind::GmailMbox
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        if !path.is_file() {
            return Err(CoreError::Probe(format!(
                "not an mbox file: {}",
                path.display()
            )));
        }
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if ext != "mbox" {
            return Err(CoreError::Probe("expected .mbox".into()));
        }
        let bytes = fs::metadata(path)?.len();
        let head = mbox::read_prefix(path, 256)?;
        if !head.starts_with(b"From ") && !head.windows(6).any(|w| w == b"\nFrom ") {
            return Err(CoreError::Probe("mbox missing From_ separator".into()));
        }
        Ok(ProbeResult {
            kind: SourceKind::GmailMbox,
            label: path
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("mail.mbox")
                .to_string(),
            bytes: Some(bytes),
            file_blake3: super::optional_file_hash(path, self.opts.cancel.as_ref())?,
            locale_guess: None,
            notes: vec!["mboxrd".into()],
        })
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        import_mbox_file(ctx, path, &path.display().to_string(), self.opts.max_bytes)?;
        Ok(ImportStats::default())
    }
}

pub fn import_mbox_file(
    ctx: &mut dyn ImportContext,
    path: &Path,
    locator: &str,
    max_bytes: u64,
) -> Result<(), CoreError> {
    let meta = fs::metadata(path)?;
    if meta.len() > max_bytes {
        return Err(CoreError::Fatal(format!(
            "mbox {} exceeds --max-bytes {}",
            path.display(),
            max_bytes
        )));
    }
    let bytes = fs::read(path)?;
    import_mbox_bytes(ctx, &bytes, locator)
}

pub fn import_mbox_bytes(
    ctx: &mut dyn ImportContext,
    bytes: &[u8],
    locator: &str,
) -> Result<(), CoreError> {
    let ckpt = ctx.load_checkpoint("mbox_file_offset")?;
    let resume_off = ckpt
        .as_ref()
        .and_then(|c| {
            let same = c
                .cursor_value
                .get("path")
                .and_then(|v| v.as_str())
                .map(|p| p == locator)
                .unwrap_or(true);
            if same {
                c.cursor_value.get("byte_offset").and_then(|v| v.as_u64())
            } else {
                None
            }
        })
        .unwrap_or(0);

    let recs = mbox::split_mboxrd(bytes);
    for rec in recs {
        if (rec.start as u64) < resume_off {
            continue;
        }
        match persist::persist_rfc822(ctx, rec.raw, locator, rec.start) {
            Ok(()) => {}
            Err(CoreError::Parse(e)) => {
                ctx.warn(Warning {
                    severity: Severity::Reject,
                    locator: format!("{locator}:{}", rec.start),
                    kind: "mbox_corrupt".into(),
                    detail: e,
                    raw_excerpt: Some(mbox::excerpt(rec.raw)),
                })?;
            }
            Err(e) => return Err(e),
        }
        ctx.checkpoint(Checkpoint {
            cursor_kind: "mbox_file_offset".into(),
            cursor_value: serde_json::json!({
                "path": locator,
                "byte_offset": rec.end,
            }),
        })?;
        ctx.maybe_commit()?;
    }
    Ok(())
}
