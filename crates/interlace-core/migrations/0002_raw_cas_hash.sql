-- Optional CAS pointer for opted-in raw rfc822.
ALTER TABLE messages ADD COLUMN raw_cas_hash TEXT REFERENCES cas_blobs(hash);
CREATE INDEX idx_messages_raw_cas_hash ON messages(raw_cas_hash)
    WHERE raw_cas_hash IS NOT NULL;
