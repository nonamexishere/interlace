-- Membership intervals from export system lines. schema_epoch stays 1.
-- conversation_participants stays the undated current set.
CREATE TABLE group_membership (
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    identity_id     INTEGER NOT NULL REFERENCES identities(id),
    joined_at       TEXT,
    left_at         TEXT
);
