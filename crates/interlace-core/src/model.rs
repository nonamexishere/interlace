//! Frozen public types. Field names are normative; do not rename.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SourceKind {
    WhatsappAndroidZip,
    WhatsappIosZip,
    TakeoutZip,
    TakeoutDir,
    GmailMbox,
    ContactsVcf,
    ContactsCsv,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum IdentityKind {
    Phone,
    Email,
    /// Reserved; v1 ZIP importers must not emit this.
    WhatsappJid,
    DisplayName,
    GoogleContactUid,
    Username,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Platform {
    Whatsapp,
    Gmail,
    Contacts,
    Owner,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConversationKind {
    Dm,
    Group,
    EmailThread,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MessageKind {
    Text,
    Media,
    Mixed,
    System,
    Email,
    Unknown,
    Tombstone,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SentAtPrecision {
    Second,
    Minute,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AttachmentKind {
    File,
    Inline,
    Voice,
    Image,
    Video,
    Sticker,
    Vcf,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecipientRole {
    To,
    Cc,
    Bcc,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Warn,
    Reject,
    UnknownRow,
}

#[derive(Debug, thiserror::Error)]
pub enum CoreError {
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("sqlite: {0}")]
    Sqlite(String),
    #[error("parse: {0}")]
    Parse(String),
    #[error("zip-slip: {0}")]
    ZipSlip(String),
    #[error("probe: {0}")]
    Probe(String),
    #[error("lock: archive in use by pid {pid} ({cmd})")]
    Lock { pid: u32, cmd: String },
    #[error("config: {0}")]
    Config(String),
    #[error("unsupported takeout layout: {0}")]
    TakeoutLayout(String),
    #[error("fatal: {0}")]
    Fatal(String),
}

impl From<rusqlite::Error> for CoreError {
    fn from(e: rusqlite::Error) -> Self {
        CoreError::Sqlite(e.to_string())
    }
}

#[derive(Debug, Clone)]
pub struct NewIdentity {
    pub platform: Platform,
    pub kind: IdentityKind,
    pub value_raw: String,
    pub value_normalized: String,
    pub display_name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct NewConversation {
    pub platform: Platform,
    pub kind: ConversationKind,
    pub native_id: String,
    pub title: Option<String>,
    pub extra_json: Option<String>,
}

#[derive(Debug, Clone)]
pub struct NewMessage {
    pub conversation_id: i64,
    pub sender_identity_id: Option<i64>,
    pub sent_at: Option<String>,
    pub sent_at_precision: SentAtPrecision,
    pub kind: MessageKind,
    pub subject: Option<String>,
    pub body_text: Option<String>,
    pub body_html: Option<String>,
    pub native_id: Option<String>,
    pub idempotency_key: String,
    pub gm_thrid: Option<String>,
    pub in_reply_to: Option<String>,
    pub payload_json: Option<String>,
    pub recipients: Vec<(i64, RecipientRole)>,
    pub labels: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct NewAttachment {
    pub message_id: i64,
    pub filename: Option<String>,
    pub mime: Option<String>,
    pub size: Option<i64>,
    pub kind: AttachmentKind,
    pub content_id: Option<String>,
    pub part_index: Option<i32>,
    pub omitted: bool,
    pub missing: bool,
}

#[derive(Debug, Clone)]
pub struct NewContact {
    pub uid: String,
    pub fn_: Option<String>,
    pub n_family: Option<String>,
    pub n_given: Option<String>,
    pub org: Option<String>,
    pub photo_bytes: Option<Vec<u8>>,
    pub channels: Vec<ContactChannelIn>,
    pub raw_excerpt: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ContactChannelIn {
    pub kind: IdentityKind,
    pub value_raw: String,
    pub value_normalized: String,
    pub pref: bool,
}

#[derive(Debug)]
pub enum PersistOutcome {
    Inserted { message_id: i64 },
    Duplicate { message_id: i64 },
}

#[derive(Debug, Clone)]
pub struct ProbeResult {
    pub kind: SourceKind,
    pub label: String,
    pub bytes: Option<u64>,
    pub file_blake3: Option<String>,
    pub locale_guess: Option<String>,
    pub notes: Vec<String>,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct ImportStats {
    pub inserted_messages: u64,
    pub skipped_dupes: u64,
    pub upgraded_attachments: u64,
    pub inserted_identities: u64,
    pub attachments_stored: u64,
    pub attachments_omitted: u64,
    pub attachments_missing: u64,
    pub warnings: u64,
    pub rejected: u64,
    pub auto_person_merges: u64,
    pub review_enqueued: u64,
}

#[derive(Debug, Clone)]
pub struct Checkpoint {
    pub cursor_kind: String,
    pub cursor_value: serde_json::Value,
}

#[derive(Debug, Clone)]
pub struct Warning {
    pub severity: Severity,
    pub locator: String,
    pub kind: String,
    pub detail: String,
    pub raw_excerpt: Option<String>,
}

#[derive(Debug, Clone)]
pub struct SearchQuery {
    pub q: String,
    pub person_id: Option<i64>,
    pub from: Option<String>,
    pub to: Option<String>,
    pub platform: Option<Platform>,
    pub conversation_id: Option<i64>,
    pub include_groups: bool,
    pub limit: u32,
}

#[derive(Debug, Clone)]
pub struct SearchHit {
    pub message_id: i64,
    pub sent_at: Option<String>,
    pub conversation_id: i64,
    pub subject: Option<String>,
    pub snippet: String,
    pub score: f64,
}

#[derive(Debug, Clone)]
pub struct OpenOptions {
    pub path: PathBuf,
    pub create: bool,
}

#[derive(Debug, Clone)]
pub struct ImportOpts {
    pub locale: Option<String>,
    pub resume_run_id: Option<i64>,
    pub conversation_name: Option<String>,
    pub max_bytes: u64,
    /// Archive `default_phone_region` (ISO 3166-1 alpha-2). Probe uses it to
    /// break a datetime locale tie (tr-TR vs de-DE). `--locale` still wins.
    pub phone_region: Option<String>,
}

impl Default for ImportOpts {
    fn default() -> Self {
        Self {
            locale: None,
            resume_run_id: None,
            conversation_name: None,
            max_bytes: 60 * 1024 * 1024 * 1024,
            phone_region: None,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct PersonMergeOpts {
    pub keep: Option<i64>,
}
