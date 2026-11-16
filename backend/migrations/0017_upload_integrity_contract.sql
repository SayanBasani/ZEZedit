-- Forward-only migration 0017: Upload Integrity, Validation and Contract Tracking (P1.5)
-- Adds explicit integrity columns and indexes to media_assets

ALTER TABLE media_assets ADD COLUMN sha256 TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN integrity_status TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN upload_attempt_id TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_media_assets_sha256 ON media_assets(sha256);
CREATE INDEX IF NOT EXISTS idx_media_assets_integrity_status ON media_assets(integrity_status);
