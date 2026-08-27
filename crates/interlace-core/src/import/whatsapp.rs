//! WhatsApp Android/iOS ZIP importer (D16, D18, D22, D23).

use std::fs::File;
use std::path::Path;

use ::zip::ZipArchive;

use super::locale::{load_pack, vote_locale, HeaderFamily};
use super::{ImportContext, SourceImporter};
use crate::cas::validate_zip_entry_name;
use crate::model::*;

mod parse;
mod persist;
mod zip;

#[derive(Default)]
pub struct WhatsappImporter {
    pub opts: ImportOpts,
}

impl SourceImporter for WhatsappImporter {
    fn id(&self) -> SourceKind {
        SourceKind::WhatsappAndroidZip
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        let listed = list_zip(path, self.opts.cancel.as_ref())?;
        let (chat_name, ios) = zip::find_chat_entry(&listed)?;
        validate_zip_entry_name(&chat_name)?;
        let kind = if ios {
            SourceKind::WhatsappIosZip
        } else {
            SourceKind::WhatsappAndroidZip
        };
        let bytes = std::fs::metadata(path).ok().map(|m| m.len());
        let file_blake3 = super::optional_file_hash(path, self.opts.cancel.as_ref())?;
        let chat = zip::read_zip_entry(
            path,
            &chat_name,
            self.opts.max_bytes,
            self.opts.cancel.as_ref(),
        )?;
        let (text, mut notes) = zip::decode_chat(&chat);
        let family = if ios {
            HeaderFamily::Ios
        } else {
            HeaderFamily::Android
        };
        let lines: Vec<&str> = text.lines().collect();
        let locale_guess = if let Some(ref loc) = self.opts.locale {
            let _ = load_pack(loc)?;
            Some(loc.clone())
        } else {
            match vote_locale(&lines, Some(family), self.opts.phone_region.as_deref()) {
                Ok(id) => Some(id),
                Err(e) => {
                    notes.push(e.to_string());
                    None
                }
            }
        };
        if listed.iter().any(|n| zip::looks_like_media_name(n)) {
            notes.push("media entries present".into());
        }
        let label = path
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("whatsapp.zip")
            .to_string();
        Ok(ProbeResult {
            kind,
            label,
            bytes,
            file_blake3,
            locale_guess,
            notes,
        })
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        persist::import(self, path, ctx)
    }
}

fn open_zip_cancellable(
    path: &Path,
    cancel: Option<&ImportCancel>,
) -> Result<ZipArchive<File>, CoreError> {
    if cancel.is_some_and(|c| c.is_cancelled()) {
        return Err(CoreError::Cancelled);
    }
    zip::open_zip_cancellable(path, cancel)
}

fn list_zip(path: &Path, cancel: Option<&ImportCancel>) -> Result<Vec<String>, CoreError> {
    if cancel.is_some_and(|c| c.is_cancelled()) {
        return Err(CoreError::Cancelled);
    }
    zip::list_zip(path, cancel)
}
