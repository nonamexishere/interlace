-- Additive membership intervals. schema_epoch stays 1.
-- NULL joined_at / left_at means that bound is unknown. Do not invent it.
CREATE TABLE group_membership (
    id               INTEGER PRIMARY KEY,
    conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
    identity_id      INTEGER NOT NULL REFERENCES identities(id),
    joined_at        TEXT,
    left_at          TEXT
);

CREATE INDEX idx_group_membership_conv_ident
    ON group_membership(conversation_id, identity_id);
