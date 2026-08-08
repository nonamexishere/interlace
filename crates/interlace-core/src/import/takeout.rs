//! Takeout directory / independent ZIP importer (Spike 4).

use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use zip::ZipArchive;

use super::contacts::{import_csv_file, import_vcf_file, import_vcf_text};
use super::gmail::import_mbox_file;
use super::{ImportContext, SourceImporter};
use crate::cas::validate_zip_entry_name;
use crate::model::*;

#[derive(Default)]
pub struct TakeoutImporter {
    pub opts: ImportOpts,
}

impl SourceImporter for TakeoutImporter {
    fn id(&self) -> SourceKind {
        SourceKind::TakeoutDir
    }

    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError> {
        check_spanned(path)?;
        if path.is_dir() {
            if dir_has_takeout_zips(path)? {
                let zips = collect_takeout_zips(path)?;
                assert_disjoint_zips(&zips)?;
                return Ok(ProbeResult {
                    kind: SourceKind::TakeoutDir,
                    label: path
                        .file_name()
                        .and_then(|s| s.to_str())
                        .unwrap_or("takeout")
                        .to_string(),
                    bytes: None,
                    file_blake3: None,
                    locale_guess: None,
                    notes: vec![format!("{} independent zip(s)", zips.len())],
                });
            }
            if is_takeout_tree(path) {
                return Ok(ProbeResult {
                    kind: SourceKind::TakeoutDir,
                    label: path
                        .file_name()
                        .and_then(|s| s.to_str())
                        .unwrap_or("Takeout")
                        .to_string(),
                    bytes: None,
                    file_blake3: None,
                    locale_guess: None,
                    notes: vec!["extracted Takeout tree".into()],
                });
            }
            return Err(CoreError::Probe(format!(
                "directory is not a Takeout tree: {}",
                path.display()
            )));
        }
        if looks_like_takeout_zip(path)? {
            return Ok(ProbeResult {
                kind: SourceKind::TakeoutZip,
                label: path
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("takeout.zip")
                    .to_string(),
                bytes: fs::metadata(path).ok().map(|m| m.len()),
                file_blake3: hash_file(path).ok(),
                locale_guess: None,
                notes: vec![],
            });
        }
        Err(CoreError::Probe("not a Takeout zip or directory".into()))
    }

    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError> {
        check_spanned(path)?;
        if path.is_dir() {
            if dir_has_takeout_zips(path)? {
                let zips = collect_takeout_zips(path)?;
                assert_disjoint_zips(&zips)?;
                for z in zips {
                    import_takeout_zip(ctx, &z, self.opts.max_bytes)?;
                }
            } else {
                let root = if path.join("Takeout").is_dir() {
                    path.join("Takeout")
                } else {
                    path.to_path_buf()
                };
                import_takeout_tree(ctx, &root)?;
            }
        } else {
            import_takeout_zip(ctx, path, self.opts.max_bytes)?;
        }
        ctx.warn(Warning {
            severity: Severity::Warn,
            locator: path.display().to_string(),
            kind: "takeout_raw".into(),
            detail: "Phase 1 does not store raw rfc822 in CAS. Deleting the Takeout dump \
                     loses bit-perfect originals. --preserve-raw is Phase 2 (default off)."
                .into(),
            raw_excerpt: None,
        })?;
        Ok(ImportStats::default())
    }
}

pub fn is_takeout_tree(path: &Path) -> bool {
    if path.join("Takeout/Mail").is_dir() || path.join("Takeout/Contacts").exists() {
        return true;
    }
    path.join("Mail").is_dir() || path.join("Contacts").is_dir()
}

pub fn looks_like_takeout_zip(path: &Path) -> Result<bool, CoreError> {
    let f = File::open(path)?;
    let mut zip = match ZipArchive::new(f) {
        Ok(z) => z,
        Err(_) => return Ok(false),
    };
    for i in 0..zip.len().min(256) {
        if let Ok(e) = zip.by_index(i) {
            let n = e.name().replace('\\', "/");
            if n.contains("Takeout/Mail/")
                || n.contains("Takeout/Contacts/")
                || n.starts_with("Takeout/")
            {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

pub fn check_spanned(path: &Path) -> Result<(), CoreError> {
    if path.is_file() {
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if ext.starts_with('z') && ext.len() == 3 && ext[1..].chars().all(|c| c.is_ascii_digit()) {
            return Err(CoreError::TakeoutLayout(
                "spanned zip not supported; extract then pass the Takeout/ dir".into(),
            ));
        }
        if let Some(stem) = path.file_stem() {
            let sibling = path
                .parent()
                .unwrap_or_else(|| Path::new("."))
                .join(format!("{}.z01", stem.to_string_lossy()));
            if sibling.exists() {
                return Err(CoreError::TakeoutLayout(
                    "spanned zip not supported; extract then pass the Takeout/ dir".into(),
                ));
            }
        }
    } else if path.is_dir() {
        if let Ok(rd) = fs::read_dir(path) {
            for e in rd.flatten() {
                let n = e.file_name().to_string_lossy().to_ascii_lowercase();
                if n.ends_with(".z01") || n.ends_with(".z02") {
                    return Err(CoreError::TakeoutLayout(
                        "spanned zip not supported; extract then pass the Takeout/ dir".into(),
                    ));
                }
            }
        }
    }
    Ok(())
}

fn dir_has_takeout_zips(path: &Path) -> Result<bool, CoreError> {
    Ok(!collect_takeout_zips(path)?.is_empty() && !is_takeout_tree(path))
}

fn collect_takeout_zips(dir: &Path) -> Result<Vec<PathBuf>, CoreError> {
    let mut out = Vec::new();
    let rd = fs::read_dir(dir)?;
    for e in rd {
        let e = e?;
        let p = e.path();
        if p.extension()
            .and_then(|x| x.to_str())
            .map(|s| s.eq_ignore_ascii_case("zip"))
            != Some(true)
        {
            continue;
        }
        if looks_like_takeout_zip(&p)? {
            out.push(p);
        }
    }
    out.sort();
    Ok(out)
}

fn assert_disjoint_zips(zips: &[PathBuf]) -> Result<(), CoreError> {
    let mut seen: HashMap<String, PathBuf> = HashMap::new();
    for z in zips {
        for name in list_zip_names(z)? {
            let logical = logical_takeout_path(&name);
            if logical.is_empty() {
                continue;
            }
            if let Some(prev) = seen.get(&logical) {
                return Err(CoreError::TakeoutLayout(format!(
                    "same path {logical} in multiple zips ({} and {}); extract and merge directories, then import takeout <dir>",
                    prev.display(),
                    z.display()
                )));
            }
            seen.insert(logical, z.clone());
        }
    }
    Ok(())
}

fn list_zip_names(path: &Path) -> Result<Vec<String>, CoreError> {
    let f = File::open(path)?;
    let mut zip = ZipArchive::new(f).map_err(|e| CoreError::Parse(format!("zip: {e}")))?;
    let mut names = Vec::new();
    for i in 0..zip.len() {
        let e = zip
            .by_index(i)
            .map_err(|e| CoreError::Parse(format!("zip: {e}")))?;
        if e.is_dir() {
            continue;
        }
        names.push(e.name().replace('\\', "/"));
    }
    Ok(names)
}

fn logical_takeout_path(name: &str) -> String {
    let n = name.replace('\\', "/");
    if let Some(i) = n.find("Takeout/") {
        n[i..].to_string()
    } else {
        String::new()
    }
}

fn import_takeout_tree(ctx: &mut dyn ImportContext, root: &Path) -> Result<(), CoreError> {
    let mail = root.join("Mail");
    if mail.is_dir() {
        for e in fs::read_dir(&mail)? {
            let p = e?.path();
            if p.extension()
                .and_then(|x| x.to_str())
                .map(|s| s.eq_ignore_ascii_case("mbox"))
                == Some(true)
            {
                import_mbox_file(ctx, &p, &p.display().to_string(), 60 * 1024 * 1024 * 1024)?;
            }
        }
    }
    let contacts = root.join("Contacts");
    if contacts.is_dir() {
        walk_contacts(ctx, &contacts)?;
    }
    Ok(())
}

fn walk_contacts(ctx: &mut dyn ImportContext, dir: &Path) -> Result<(), CoreError> {
    for e in fs::read_dir(dir)? {
        let p = e?.path();
        if p.is_dir() {
            walk_contacts(ctx, &p)?;
            continue;
        }
        let ext = p
            .extension()
            .and_then(|x| x.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        match ext.as_str() {
            "vcf" | "vcard" => import_vcf_file(ctx, &p)?,
            "csv" => import_csv_file(ctx, &p)?,
            _ => {}
        }
    }
    Ok(())
}

fn import_takeout_zip(
    ctx: &mut dyn ImportContext,
    path: &Path,
    max_bytes: u64,
) -> Result<(), CoreError> {
    let names = list_zip_names(path)?;
    let mut seen: HashSet<String> = HashSet::new();
    for n in &names {
        if validate_zip_entry_name(n).is_err() {
            ctx.warn(Warning {
                severity: Severity::Reject,
                locator: n.clone(),
                kind: "zip_slip".into(),
                detail: format!("skipped zip-slip entry {n}"),
                raw_excerpt: None,
            })?;
            continue;
        }
        let logical = logical_takeout_path(n);
        if logical.is_empty() {
            continue;
        }
        if !seen.insert(logical.clone()) {
            return Err(CoreError::TakeoutLayout(format!(
                "duplicate path {logical} inside {}",
                path.display()
            )));
        }
        let lower = logical.to_ascii_lowercase();
        if lower.ends_with(".mbox") {
            let spill = spill_entry(ctx, path, n, max_bytes)?;
            import_mbox_file(ctx, &spill, &logical, max_bytes)?;
        } else if lower.ends_with(".vcf") || lower.ends_with(".vcard") {
            let bytes = read_zip_entry(path, n, max_bytes)?;
            let text = String::from_utf8_lossy(&bytes).into_owned();
            import_vcf_text(ctx, &text)?;
        } else if lower.ends_with(".csv") && lower.contains("contact") {
            let spill = spill_entry(ctx, path, n, max_bytes)?;
            import_csv_file(ctx, &spill)?;
        }
    }
    Ok(())
}

fn spill_entry(
    ctx: &mut dyn ImportContext,
    zip_path: &Path,
    name: &str,
    max_bytes: u64,
) -> Result<PathBuf, CoreError> {
    validate_zip_entry_name(name)?;
    let safe = Path::new(name)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("spill.bin");
    if safe.contains("..") {
        return Err(CoreError::ZipSlip(name.into()));
    }
    let dir = ctx
        .archive_root()
        .join("imports")
        .join(ctx.run_id().to_string())
        .join("spill");
    fs::create_dir_all(&dir)?;
    let dest = dir.join(safe);
    let bytes = read_zip_entry(zip_path, name, max_bytes)?;
    let mut f = File::create(&dest)?;
    f.write_all(&bytes)?;
    f.sync_all()?;
    Ok(dest)
}

fn read_zip_entry(path: &Path, name: &str, max_bytes: u64) -> Result<Vec<u8>, CoreError> {
    validate_zip_entry_name(name)?;
    let f = File::open(path)?;
    let mut zip = ZipArchive::new(f).map_err(|e| CoreError::Parse(format!("zip: {e}")))?;
    let mut e = zip
        .by_name(name)
        .map_err(|err| CoreError::Parse(format!("zip entry {name}: {err}")))?;
    if e.size() > max_bytes {
        return Err(CoreError::Fatal(format!(
            "zip entry {name} uncompressed {} exceeds cap {max_bytes}",
            e.size()
        )));
    }
    let mut buf = Vec::new();
    e.read_to_end(&mut buf)?;
    Ok(buf)
}

fn hash_file(path: &Path) -> Result<String, CoreError> {
    let mut f = File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0u8; 65536];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}
