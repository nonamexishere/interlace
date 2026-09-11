-- Additive: optional CAS pointer for opted-in raw rfc822. schema_epoch stays 1.
ALTER TABLE messages ADD COLUMN raw_cas_hash TEXT REFERENCES cas_blobs(hash);
