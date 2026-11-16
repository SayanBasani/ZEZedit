-- Migration 0018: Media Library Query & Sorting Indexes
-- Optimizes server-side pagination, search, and filtering across large media collections

CREATE INDEX IF NOT EXISTS idx_media_assets_created_at ON media_assets(created_at);
CREATE INDEX IF NOT EXISTS idx_media_assets_filename ON media_assets(original_filename);
CREATE INDEX IF NOT EXISTS idx_media_assets_file_size ON media_assets(file_size_bytes);
CREATE INDEX IF NOT EXISTS idx_media_assets_duration ON media_assets(duration_seconds);
CREATE INDEX IF NOT EXISTS idx_media_assets_media_type ON media_assets(media_type);
CREATE INDEX IF NOT EXISTS idx_media_assets_width_height ON media_assets(width, height);
