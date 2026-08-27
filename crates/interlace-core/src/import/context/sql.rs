//! SQL enum encodings for persist.

use crate::model::*;

pub fn platform_sql(p: Platform) -> &'static str {
    match p {
        Platform::Whatsapp => "whatsapp",
        Platform::Gmail => "gmail",
        Platform::Contacts => "contacts",
        Platform::Owner => "owner",
    }
}

pub fn identity_kind_sql(k: IdentityKind) -> &'static str {
    match k {
        IdentityKind::Phone => "phone",
        IdentityKind::Email => "email",
        IdentityKind::WhatsappJid => "whatsapp_jid",
        IdentityKind::DisplayName => "display_name",
        IdentityKind::GoogleContactUid => "google_contact_uid",
        IdentityKind::Username => "username",
    }
}

pub fn conv_kind_sql(k: ConversationKind) -> &'static str {
    match k {
        ConversationKind::Dm => "dm",
        ConversationKind::Group => "group",
        ConversationKind::EmailThread => "email_thread",
    }
}

pub fn msg_kind_sql(k: MessageKind) -> &'static str {
    match k {
        MessageKind::Text => "text",
        MessageKind::Media => "media",
        MessageKind::Mixed => "mixed",
        MessageKind::System => "system",
        MessageKind::Email => "email",
        MessageKind::Unknown => "unknown",
        MessageKind::Tombstone => "tombstone",
    }
}

pub fn precision_sql(p: SentAtPrecision) -> &'static str {
    match p {
        SentAtPrecision::Second => "second",
        SentAtPrecision::Minute => "minute",
        SentAtPrecision::Unknown => "unknown",
    }
}

pub fn attach_kind_sql(k: AttachmentKind) -> &'static str {
    match k {
        AttachmentKind::File => "file",
        AttachmentKind::Inline => "inline",
        AttachmentKind::Voice => "voice",
        AttachmentKind::Image => "image",
        AttachmentKind::Video => "video",
        AttachmentKind::Sticker => "sticker",
        AttachmentKind::Vcf => "vcf",
    }
}

pub fn recipient_sql(r: RecipientRole) -> &'static str {
    match r {
        RecipientRole::To => "to",
        RecipientRole::Cc => "cc",
        RecipientRole::Bcc => "bcc",
    }
}

pub fn severity_sql(s: Severity) -> &'static str {
    match s {
        Severity::Warn => "warn",
        Severity::Reject => "reject",
        Severity::UnknownRow => "unknown_row",
    }
}

pub fn source_kind_sql(k: SourceKind) -> &'static str {
    match k {
        SourceKind::WhatsappAndroidZip => "whatsapp_android_zip",
        SourceKind::WhatsappIosZip => "whatsapp_ios_zip",
        SourceKind::TakeoutZip => "takeout_zip",
        SourceKind::TakeoutDir => "takeout_dir",
        SourceKind::GmailMbox => "gmail_mbox",
        SourceKind::ContactsVcf => "contacts_vcf",
        SourceKind::ContactsCsv => "contacts_csv",
    }
}
