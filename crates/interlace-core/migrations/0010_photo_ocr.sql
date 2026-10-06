-- Additive photo OCR text. schema_epoch stays 1.
ALTER TABLE attachments ADD COLUMN ocr_text TEXT;
