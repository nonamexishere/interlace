-- Content hash for two WhatsApp exports of one chat. schema_epoch stays 1.
CREATE TABLE wa_message_content (
    message_id   INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    content_hash TEXT    NOT NULL,
    minute       TEXT    NOT NULL,
    sender_canon TEXT    NOT NULL
);
CREATE INDEX idx_wa_message_content_hash ON wa_message_content(content_hash);
CREATE INDEX idx_wa_message_content_near ON wa_message_content(minute, sender_canon);
