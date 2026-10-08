//! Core library for Interlace, a local-first offline archive.
//!
//! Message → Identity → Person. No network client. See `docs/design/DESIGN.md`.

pub mod cas;
pub mod cli;
pub mod db;
mod derivative;
pub mod identity;
pub mod import;
pub mod model;
mod ocr;
pub mod people;
pub mod search;
pub mod session;
mod voice;

pub use db::{
    archive_on_file, init_archive, list_snapshots, migrate, open_archive, open_with_options,
    restore_snapshot, restore_snapshot_at, snapshot_archive, Archive, LockMode,
};
pub use identity::{
    person_merge, person_undo, person_unlink, resolve_run, review_census, review_list,
    review_resolve, review_resolve_selected, review_show, ReviewCensus,
};
pub use import::{
    ContactsImporter, GmailMboxImporter, ImportContext, ImporterRegistry, SourceImporter,
    TakeoutImporter, WhatsappImporter,
};
pub use model::*;
pub use ocr::{
    ocr_image_attachments, ocr_images_enabled, pending_ocr_rows, set_ocr_images_enabled,
    store_ocr_text,
};
pub use people::{
    attachments_for, complete_attachments, conversation_participant_names,
    conversation_participant_names_at, labels_list, merge_targets, person_conversations,
    person_day_message, person_display_name, person_identities, person_list, person_list_on,
    person_list_with_groups, person_media_rows_for, person_rename, person_set_notes, person_show,
    person_timeline_rows, person_timeline_rows_for, person_year_counts, rebuild_activity_years,
    recent_link_events, resolve_wa_quote, search_hit_person, AttachmentRef,
    ConversationParticipantName, LabelRef, LinkEvent, PersonConversation, PersonIdentity,
    PersonMediaRow, PersonShow, PersonSummary, PersonYearCount, TimelineRow, WaQuoteJump,
};
pub use search::{
    build_search_text, expand_query, extra_ascii_fold, index_import_run, person_timeline,
    rebuild_fts, search, turkish_fold, visible_message_body,
};
pub use session::{
    cloud_warning, init_owner_archive, read_last_bookmark, read_last_path, sandbox_denied_message,
    validate_phone_region, write_last_bookmark, write_last_path,
};
pub use voice::{
    pending_voice_note_rows, set_voice_transcribe_enabled, store_voice_transcript,
    transcribe_voice_notes, voice_transcribe_enabled,
};

/// Placeholder kept from the 0.0.1 name-squat so existing tests stay green.
pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        assert_eq!(add(2, 2), 4);
    }
}
