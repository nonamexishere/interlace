-- Interlace schema v1
-- Apply via interlace_core::db::migrate. Never edit once shipped; add 0002_*.sql.

CREATE TABLE schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE archive_meta (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    archive_id          TEXT    NOT NULL,          -- UUID from INTERLACE.toml
    created_at          TEXT    NOT NULL,
    schema_epoch        INTEGER NOT NULL DEFAULT 1,
    owner_display_name  TEXT,                      -- optional, user-provided
    notes               TEXT
);

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sources (
    id              INTEGER PRIMARY KEY,
    kind            TEXT    NOT NULL
        CHECK (kind IN (
            'whatsapp_android_zip',
            'whatsapp_ios_zip',
            'takeout_zip',
            'takeout_dir',
            'gmail_mbox',
            'contacts_vcf',
            'contacts_csv'
        )),
    label           TEXT    NOT NULL,             -- user-visible, default = filename
    origin_path     TEXT    NOT NULL,             -- path as given at import time (may vanish)
    bytes           INTEGER,
    file_blake3     TEXT,                         -- hash of the import root file if regular file
    status          TEXT    NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','retired')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Source upsert key (application-enforced; SQLite UNIQUE cannot express
-- "blake3 OR path"):
--   if regular file: (kind, file_blake3)
--   else (dir / vanished file): (kind, canonical origin_path)
-- Re-import of the same bytes reuses the sources row; a new import_runs row is created.

CREATE TABLE import_runs (
    id              INTEGER PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    finished_at     TEXT,
    heartbeat_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    status          TEXT    NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','done','failed','interrupted')),
    stats_json      TEXT,                         -- counts: inserted, skipped_dup, warnings, rejected
    error           TEXT
);

CREATE TABLE import_checkpoints (
    import_run_id   INTEGER NOT NULL REFERENCES import_runs(id) ON DELETE CASCADE,
    cursor_kind     TEXT    NOT NULL,             -- 'wa_line' | 'mbox_file_offset' | 'zip_done_entries' | 'vcf_index' | 'spill_path'
    cursor_value    TEXT    NOT NULL,             -- JSON; see Checkpoint section (no seek-inside-DEFLATE)
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (import_run_id, cursor_kind)
);

CREATE TABLE import_warnings (
    id              INTEGER PRIMARY KEY,
    import_run_id   INTEGER NOT NULL REFERENCES import_runs(id) ON DELETE CASCADE,
    severity        TEXT    NOT NULL CHECK (severity IN ('warn','reject','unknown_row')),
    locator         TEXT    NOT NULL,             -- file:offset or zip entry:line
    kind            TEXT    NOT NULL,             -- 'parse','zip_slip','missing_media','mbox_corrupt',...
    detail          TEXT    NOT NULL,             -- human + machine
    raw_excerpt     TEXT                          -- truncated original line/headers, never huge blobs
);

-- Identities -----------------------------------------------------------------
-- value_normalized is the merge key within (platform, kind).
-- kind is closed for v1; new sources add kinds via 000N migration + CHECK replace.

CREATE TABLE identities (
    id                  INTEGER PRIMARY KEY,
    platform            TEXT    NOT NULL
        CHECK (platform IN ('whatsapp','gmail','contacts','owner')),
    kind                TEXT    NOT NULL
        CHECK (kind IN (
            'phone','email','whatsapp_jid','display_name',
            'google_contact_uid','username'
        )),
        -- whatsapp_jid is RESERVED unused in v1 (ZIP transcripts have no JIDs).
        -- Importers MUST NOT insert this kind until a future msgstore source.
    value_raw           TEXT    NOT NULL,
    value_normalized    TEXT    NOT NULL,
    display_name        TEXT,
    first_seen_at       TEXT,
    last_seen_at        TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (platform, kind, value_normalized)
);

CREATE TABLE self_identities (
    identity_id INTEGER PRIMARY KEY REFERENCES identities(id)
);

CREATE TABLE persons (
    id              INTEGER PRIMARY KEY,
    display_name    TEXT    NOT NULL,
    notes           TEXT,
    is_self         INTEGER NOT NULL DEFAULT 0 CHECK (is_self IN (0,1)),
    tombstoned_at   TEXT,                         -- set when merged into another person
    merged_into     INTEGER REFERENCES persons(id),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE person_identities (
    person_id       INTEGER NOT NULL REFERENCES persons(id),
    identity_id     INTEGER NOT NULL REFERENCES identities(id),
    link_reason     TEXT    NOT NULL
        CHECK (link_reason IN (
            'takeout_vcard','auto_phone','auto_email','auto_person_merge',
            'manual','review_accepted','self_declared'
        )),
    confidence      REAL    NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by      TEXT    NOT NULL CHECK (created_by IN ('system','user')),
    PRIMARY KEY (identity_id)                     -- an identity belongs to at most one live person
);

CREATE TABLE identity_link_events (
    id              INTEGER PRIMARY KEY,
    ts              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    actor           TEXT    NOT NULL CHECK (actor IN ('system','user')),
    op              TEXT    NOT NULL
        CHECK (op IN ('link','unlink','merge_persons','split_person','tombstone')),
    payload_json    TEXT    NOT NULL              -- enough to invert the op
);

CREATE TABLE merge_review_queue (
    id                  INTEGER PRIMARY KEY,
    status              TEXT    NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','accepted','rejected','expired')),
    left_identity_id    INTEGER NOT NULL REFERENCES identities(id),
    right_person_id     INTEGER REFERENCES persons(id),
    right_identity_id   INTEGER REFERENCES identities(id),
    suggested_score     REAL    NOT NULL,
    reason_summary      TEXT    NOT NULL,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    resolved_at         TEXT,
    resolved_by         TEXT,
    CHECK (
        (right_person_id IS NOT NULL AND right_identity_id IS NULL)
        OR (right_person_id IS NULL AND right_identity_id IS NOT NULL)
        OR (right_person_id IS NOT NULL AND right_identity_id IS NOT NULL)
    )
);

-- One open suggestion per identity pair (NULL-safe via coalesced sentinels in app
-- + partial unique indexes):
CREATE UNIQUE INDEX idx_review_open_ii ON merge_review_queue(left_identity_id, right_identity_id)
    WHERE status = 'open' AND right_identity_id IS NOT NULL;
CREATE UNIQUE INDEX idx_review_open_ip ON merge_review_queue(left_identity_id, right_person_id)
    WHERE status = 'open' AND right_person_id IS NOT NULL AND right_identity_id IS NULL;

CREATE TABLE merge_evidence (
    id              INTEGER PRIMARY KEY,
    review_id       INTEGER NOT NULL REFERENCES merge_review_queue(id) ON DELETE CASCADE,
    evidence_type   TEXT    NOT NULL
        CHECK (evidence_type IN (
            'phone_e164','email_exact','takeout_vcard_group',
            'name_similarity','photo_phash','username_pattern',
            'behavioral_echo'
        )),
    score           REAL    NOT NULL,
    detail_json     TEXT    NOT NULL
);

CREATE TABLE contacts_raw (
    id              INTEGER PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    uid             TEXT    NOT NULL,             -- vCard UID, else synthetic 'syn:'||blake3(fn||sorted channels)
    fn              TEXT,
    n_family        TEXT,
    n_given         TEXT,
    org             TEXT,
    photo_cas_hash  TEXT,
    photo_dhash     INTEGER,                      -- 64-bit dHash; NULL in Phase 1 (not computed)
    raw_excerpt     TEXT,                         -- first 8 KiB of vCard for debug
    UNIQUE (source_id, uid)
);

CREATE TABLE contact_channels (
    id              INTEGER PRIMARY KEY,
    contact_id      INTEGER NOT NULL REFERENCES contacts_raw(id) ON DELETE CASCADE,
    kind            TEXT    NOT NULL CHECK (kind IN ('phone','email')),
    value_raw       TEXT    NOT NULL,
    value_normalized TEXT   NOT NULL,
    pref            INTEGER NOT NULL DEFAULT 0,
    identity_id     INTEGER REFERENCES identities(id)
);

-- Conversations / messages ---------------------------------------------------

CREATE TABLE conversations (
    id              INTEGER PRIMARY KEY,
    platform        TEXT    NOT NULL CHECK (platform IN ('whatsapp','gmail')),
    kind            TEXT    NOT NULL
        CHECK (kind IN ('dm','group','email_thread')),
    source_id       INTEGER REFERENCES sources(id),
    native_id       TEXT    NOT NULL,             -- see idempotency section
    title           TEXT,
    -- kind='group' is the only group flag; do not add a parallel is_group column
    created_at      TEXT,
    last_message_at TEXT,
    extra_json      TEXT,                         -- e.g. {"join_cutoff":true}
    UNIQUE (platform, native_id)
);

CREATE TABLE conversation_participants (
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    identity_id     INTEGER NOT NULL REFERENCES identities(id),
    role            TEXT    NOT NULL DEFAULT 'member'
        CHECK (role IN ('member','owner','me')),
    PRIMARY KEY (conversation_id, identity_id)
);

CREATE TABLE messages (
    id                      INTEGER PRIMARY KEY,
    conversation_id         INTEGER NOT NULL REFERENCES conversations(id),
    source_id               INTEGER NOT NULL REFERENCES sources(id),
    import_run_id           INTEGER NOT NULL REFERENCES import_runs(id),
    sender_identity_id      INTEGER REFERENCES identities(id),   -- NULL = system/unknown
    sent_at                 TEXT,                                -- RFC3339 UTC; NULL iff precision='unknown'
    sent_at_precision       TEXT    NOT NULL DEFAULT 'second'
        CHECK (sent_at_precision IN ('second','minute','unknown')),
    imported_at             TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    kind                    TEXT    NOT NULL DEFAULT 'text'
        CHECK (kind IN (
            'text','media','mixed','system','email','unknown','tombstone'
        )),
    subject                 TEXT,                                -- email only
    body_text               TEXT,                                -- plain display text
    body_html               TEXT,                                -- email HTML if present
    native_id               TEXT,                                -- Message-ID or wa fingerprint aux
    idempotency_key         TEXT    NOT NULL,                    -- global unique
    thread_parent_id        INTEGER REFERENCES messages(id),     -- in-reply-to message if resolved
    gm_thrid                TEXT,                                -- X-GM-THRID decimal string
    in_reply_to             TEXT,
    edit_state              TEXT    NOT NULL DEFAULT 'original'
        CHECK (edit_state IN ('original','edited','deleted')),
    tombstone               INTEGER NOT NULL DEFAULT 0,
    payload_json            TEXT,                                -- platform extras (labels copy, forwarded flag)
    UNIQUE (idempotency_key),
    CHECK (
        (sent_at_precision = 'unknown' AND sent_at IS NULL)
        OR (sent_at_precision <> 'unknown' AND sent_at IS NOT NULL)
    )
);

CREATE TABLE message_recipients (
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    identity_id     INTEGER NOT NULL REFERENCES identities(id),
    role            TEXT    NOT NULL CHECK (role IN ('to','cc','bcc')),
    PRIMARY KEY (message_id, identity_id, role)
);

CREATE TABLE message_revisions (
    id              INTEGER PRIMARY KEY,
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    rev_no          INTEGER NOT NULL,
    body_text       TEXT,
    edited_at       TEXT,
    UNIQUE (message_id, rev_no)
);

CREATE TABLE message_reactions (
    id              INTEGER PRIMARY KEY,
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    actor_identity_id INTEGER NOT NULL REFERENCES identities(id),
    emoji           TEXT    NOT NULL,
    reacted_at      TEXT,
    UNIQUE (message_id, actor_identity_id, emoji)
);

CREATE TABLE labels (
    id              INTEGER PRIMARY KEY,
    platform        TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    UNIQUE (platform, name)
);

CREATE TABLE message_labels (
    message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    label_id    INTEGER NOT NULL REFERENCES labels(id),
    PRIMARY KEY (message_id, label_id)
);

-- Attachments + CAS ----------------------------------------------------------

CREATE TABLE cas_blobs (
    hash            TEXT PRIMARY KEY,            -- blake3 hex lowercase 64
    size            INTEGER NOT NULL,
    mime_hint       TEXT,
    -- refcount is a cache only. CASCADE delete of attachments does NOT maintain it.
    -- Application inc/dec on cas_put / unlink. doctor --gc-cas treats filesystem
    -- + `NOT EXISTS (SELECT 1 FROM attachments WHERE cas_hash=…)` as source of truth
    -- and repairs refcount. Do not GC from refcount==0 alone.
    refcount        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE attachments (
    id              INTEGER PRIMARY KEY,
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    cas_hash        TEXT REFERENCES cas_blobs(hash),   -- NULL if omitted/missing
    filename        TEXT,
    mime            TEXT,
    size            INTEGER,
    kind            TEXT NOT NULL DEFAULT 'file'
        CHECK (kind IN ('file','inline','voice','image','video','sticker','vcf')),
    content_id      TEXT,                        -- MIME Content-ID
    part_index      INTEGER,                     -- MIME part order
    omitted         INTEGER NOT NULL DEFAULT 0,  -- WhatsApp <Media omitted>
    missing         INTEGER NOT NULL DEFAULT 0   -- referenced but not in ZIP
);

-- Search ---------------------------------------------------------------------

CREATE TABLE search_doc (
    message_id      INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    sent_at         TEXT,                        -- NULL if message.sent_at is NULL
    platform        TEXT    NOT NULL,
    conversation_id INTEGER NOT NULL,
    sender_identity_id INTEGER,
    search_text     TEXT    NOT NULL             -- Turkish-folded + subject + filenames
);

CREATE VIRTUAL TABLE messages_fts USING fts5 (
    search_text,
    content='search_doc',
    content_rowid='message_id',
    tokenize = "unicode61 remove_diacritics 2",
    prefix = '2 3'
);

-- FTS sync policy (D17):
-- * Triggers stay INSTALLED always. Never DROP them (not crash-safe; DB-global).
-- * Import writes messages/attachments only. After the run commits:
--     INSERT INTO search_doc (message_id, sent_at, platform, conversation_id,
--                             sender_identity_id, search_text)
--       SELECT m.id, m.sent_at, c.platform, m.conversation_id, m.sender_identity_id, ...
--       FROM messages m JOIN conversations c ON c.id = m.conversation_id
--       WHERE m.import_run_id = ?;
--     INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
--   The bulk search_doc INSERT will fire search_doc_ai per row; for 10 M that is
--   still cheaper than mixing FTS with message+CAS txns. If Spike 1 shows the
--   bulk insert+trigger is too slow, wrap THAT insert by temporarily dropping
--   search_doc_ai INSIDE the same transaction and recreating it before COMMIT,
--   then rebuild — but open_archive must still CREATE TRIGGER IF NOT EXISTS.
-- * open_archive / migrate / doctor --rebuild-fts: CREATE TRIGGER IF NOT EXISTS
--   for ai/ad/au (idempotent), then rebuild if doctor asked.
-- * Do NOT incrementally insert into messages_fts from importer code.

CREATE TRIGGER search_doc_ai AFTER INSERT ON search_doc BEGIN
    INSERT INTO messages_fts(rowid, search_text) VALUES (new.message_id, new.search_text);
END;
CREATE TRIGGER search_doc_ad AFTER DELETE ON search_doc BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, search_text)
        VALUES ('delete', old.message_id, old.search_text);
END;
CREATE TRIGGER search_doc_au AFTER UPDATE ON search_doc BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, search_text)
        VALUES ('delete', old.message_id, old.search_text);
    INSERT INTO messages_fts(rowid, search_text) VALUES (new.message_id, new.search_text);
END;

-- Indexes --------------------------------------------------------------------

CREATE INDEX idx_identities_norm ON identities(kind, value_normalized);
CREATE INDEX idx_identities_platform_kind ON identities(platform, kind);
CREATE INDEX idx_person_identities_person ON person_identities(person_id);
CREATE INDEX idx_review_open ON merge_review_queue(status, suggested_score DESC);
CREATE INDEX idx_messages_conv_sent ON messages(conversation_id, sent_at);
CREATE INDEX idx_messages_sent ON messages(sent_at);
CREATE INDEX idx_messages_sender_sent ON messages(sender_identity_id, sent_at);
CREATE INDEX idx_messages_source ON messages(source_id);
CREATE INDEX idx_messages_native ON messages(native_id);
CREATE INDEX idx_messages_gm_thrid ON messages(gm_thrid);
CREATE INDEX idx_attachments_hash ON attachments(cas_hash);
CREATE INDEX idx_attachments_msg ON attachments(message_id);
CREATE INDEX idx_search_doc_sent ON search_doc(sent_at);
CREATE INDEX idx_search_doc_platform ON search_doc(platform, sent_at);
CREATE INDEX idx_search_doc_conv ON search_doc(conversation_id, sent_at);
CREATE INDEX idx_search_doc_sender ON search_doc(sender_identity_id, sent_at);
CREATE INDEX idx_conv_last ON conversations(last_message_at);
CREATE INDEX idx_contact_channels_norm ON contact_channels(kind, value_normalized);
CREATE INDEX idx_warnings_run ON import_warnings(import_run_id, severity);
CREATE INDEX idx_import_runs_heartbeat ON import_runs(status, heartbeat_at);
CREATE INDEX idx_sources_blake3 ON sources(kind, file_blake3);
CREATE INDEX idx_sources_path ON sources(kind, origin_path);

-- Bootstrap FTS rank
INSERT INTO messages_fts(messages_fts, rank) VALUES('rank', 'bm25(10.0)');
