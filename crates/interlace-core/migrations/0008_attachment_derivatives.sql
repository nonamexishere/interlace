-- Additive still pointer. schema_epoch stays 1.
ALTER TABLE attachments ADD COLUMN derivative_cas_hash TEXT REFERENCES cas_blobs(hash);
