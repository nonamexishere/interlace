//! Importer plugin interface. Implementations land in later PRs.

use std::path::Path;

use crate::model::*;

pub trait ImportContext {
    fn run_id(&self) -> i64;
    fn source_id(&self) -> i64;
    fn archive_root(&self) -> &Path;

    fn persist_identity(&mut self, rec: NewIdentity) -> Result<i64, CoreError>;
    fn persist_conversation(&mut self, rec: NewConversation) -> Result<i64, CoreError>;
    fn persist_message(&mut self, rec: NewMessage) -> Result<PersistOutcome, CoreError>;
    fn persist_labels(&mut self, message_id: i64, labels: &[String]) -> Result<(), CoreError>;
    fn persist_attachment(
        &mut self,
        rec: NewAttachment,
        bytes: Option<&[u8]>,
    ) -> Result<(), CoreError>;
    fn persist_contact(&mut self, rec: NewContact) -> Result<i64, CoreError>;

    fn warn(&mut self, w: Warning) -> Result<(), CoreError>;
    fn checkpoint(&mut self, c: Checkpoint) -> Result<(), CoreError>;
    fn load_checkpoint(&self, cursor_kind: &str) -> Result<Option<Checkpoint>, CoreError>;
    fn heartbeat(&mut self) -> Result<(), CoreError>;
    fn maybe_commit(&mut self) -> Result<(), CoreError>;
    fn cas_put(&mut self, bytes: &[u8], mime_hint: Option<&str>) -> Result<String, CoreError>;
}

pub trait SourceImporter: Send + Sync {
    fn id(&self) -> SourceKind;
    fn probe(&self, path: &Path) -> Result<ProbeResult, CoreError>;
    fn import(&self, path: &Path, ctx: &mut dyn ImportContext) -> Result<ImportStats, CoreError>;
}

pub struct ImporterRegistry;

impl ImporterRegistry {
    pub fn detect(_path: &Path) -> Result<SourceKind, CoreError> {
        unimplemented!("importer registry lands in PR6/PR7")
    }
}
