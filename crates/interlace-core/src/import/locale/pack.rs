//! Five shipped WhatsApp locale packs.

use crate::model::CoreError;

pub const PACK_IDS: &[&str] = &["en-US", "en-GB", "tr-TR", "de-DE", "pt-BR"];

#[derive(Debug, Clone)]
pub struct LocalePack {
    pub id: String,
    pub family_hints: Vec<String>,
    pub you_tokens: Vec<String>,
    pub date_time_patterns: Vec<String>,
    pub media_omitted: Vec<String>,
    pub file_attached_pattern: String,
    pub file_attached_alt: Vec<String>,
    pub forwarded_tokens: Vec<String>,
    pub title_prefixes_dm: Vec<String>,
    pub title_prefixes_group: Vec<String>,
    pub system_created_group: Vec<String>,
    pub system_added: Vec<String>,
    pub system_subject: Vec<String>,
    pub system_encryption: Vec<String>,
    pub encryption_banner_startswith: String,
}

pub fn load_pack(id: &str) -> Result<LocalePack, CoreError> {
    let raw = match id {
        "en-US" => include_str!("../../../locale/en-US.toml"),
        "en-GB" => include_str!("../../../locale/en-GB.toml"),
        "tr-TR" => include_str!("../../../locale/tr-TR.toml"),
        "de-DE" => include_str!("../../../locale/de-DE.toml"),
        "pt-BR" => include_str!("../../../locale/pt-BR.toml"),
        other => {
            return Err(CoreError::Config(format!(
                "unknown locale pack {other}; pass --locale as one of {}",
                PACK_IDS.join(", ")
            )))
        }
    };
    parse_pack_toml(id, raw)
}

pub fn all_packs() -> Result<Vec<LocalePack>, CoreError> {
    PACK_IDS.iter().map(|id| load_pack(id)).collect()
}

fn parse_pack_toml(id: &str, raw: &str) -> Result<LocalePack, CoreError> {
    let v: toml::Value =
        toml::from_str(raw).map_err(|e| CoreError::Config(format!("locale {id}: {e}")))?;
    let table = v
        .as_table()
        .ok_or_else(|| CoreError::Config(format!("locale {id}: not a table")))?;
    Ok(LocalePack {
        id: req_str(table, "id")?,
        family_hints: req_str_vec(table, "family_hints")?,
        you_tokens: req_str_vec(table, "you_tokens")?,
        date_time_patterns: req_str_vec(table, "date_time_patterns")?,
        media_omitted: req_str_vec(table, "media_omitted")?,
        file_attached_pattern: req_str(table, "file_attached_pattern")?,
        file_attached_alt: req_str_vec(table, "file_attached_alt")?,
        forwarded_tokens: req_str_vec(table, "forwarded_tokens")?,
        title_prefixes_dm: req_str_vec(table, "title_prefixes_dm")?,
        title_prefixes_group: req_str_vec(table, "title_prefixes_group")?,
        system_created_group: req_str_vec(table, "system_created_group")?,
        system_added: req_str_vec(table, "system_added")?,
        system_subject: req_str_vec(table, "system_subject")?,
        system_encryption: req_str_vec(table, "system_encryption")?,
        encryption_banner_startswith: req_str(table, "encryption_banner_startswith")?,
    })
}

fn req_str(t: &toml::map::Map<String, toml::Value>, k: &str) -> Result<String, CoreError> {
    t.get(k)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| CoreError::Config(format!("locale missing string {k}")))
}

fn req_str_vec(t: &toml::map::Map<String, toml::Value>, k: &str) -> Result<Vec<String>, CoreError> {
    let arr = t
        .get(k)
        .and_then(|v| v.as_array())
        .ok_or_else(|| CoreError::Config(format!("locale missing array {k}")))?;
    Ok(arr
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.to_string()))
        .collect())
}
