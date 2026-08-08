//! Five shipped locale packs. No other ids in 0.1.0.

use serde::Deserialize;

pub const PACK_IDS: &[&str] = &["en-US", "en-GB", "tr-TR", "de-DE", "pt-BR"];

#[derive(Debug, Clone, Deserialize)]
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

pub fn load_pack(id: &str) -> Result<LocalePack, String> {
    let raw = match id {
        "en-US" => include_str!("../locale/en-US.toml"),
        "en-GB" => include_str!("../locale/en-GB.toml"),
        "tr-TR" => include_str!("../locale/tr-TR.toml"),
        "de-DE" => include_str!("../locale/de-DE.toml"),
        "pt-BR" => include_str!("../locale/pt-BR.toml"),
        other => return Err(format!("unknown locale pack {other}")),
    };
    toml::from_str(raw).map_err(|e| format!("parse {id}: {e}"))
}
