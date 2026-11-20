-- Migration 0019: Media Relinking, Missing File Recovery & External Media Handling (P1.7)
-- Adds explicit audit columns and recovery indexes to media_assets

ALTER TABLE media_assets ADD COLUMN relinked_at TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN previous_storage_path TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN previous_sha256 TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN relink_match_status TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_media_assets_relinked_at ON media_assets(relinked_at);
