-- Two open wa_near rows may share an identity pair. schema_epoch stays 1.
-- Person-merge uniqueness for non-near rows stays on this index.
DROP INDEX IF EXISTS idx_review_open_ii;
CREATE UNIQUE INDEX idx_review_open_ii
    ON merge_review_queue(left_identity_id, right_identity_id)
    WHERE status = 'open'
      AND right_identity_id IS NOT NULL
      AND instr(reason_summary, '"wa_near":true') = 0;
