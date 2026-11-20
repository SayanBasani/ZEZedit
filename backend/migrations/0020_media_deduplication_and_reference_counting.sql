-- Migration 0020: Media Deduplication & Reference Counting (P1.8)
-- Forward-only migration establishing physical media file deduplication and reference tracking.

-- 1. Create stored_media_files table representing canonical physical media files on disk
CREATE TABLE IF NOT EXISTS stored_media_files (
    id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    storage_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT,
    container_format TEXT,
    duration_seconds REAL,
    width INTEGER,
    height INTEGER,
    fps REAL,
    video_codec TEXT,
    audio_codec TEXT,
    is_external INTEGER NOT NULL DEFAULT 0,
    reference_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_verified_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_stored_media_files_sha256 ON stored_media_files(sha256);
CREATE INDEX IF NOT EXISTS idx_stored_media_files_storage_path ON stored_media_files(storage_path);
CREATE INDEX IF NOT EXISTS idx_stored_media_files_ref_count ON stored_media_files(reference_count);

-- 2. Add stored_file_id column to media_assets linking logical asset to stored physical file
ALTER TABLE media_assets ADD COLUMN stored_file_id TEXT DEFAULT NULL REFERENCES stored_media_files(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_media_assets_stored_file_id ON media_assets(stored_file_id);

-- 3. Safely backfill stored_media_files for existing media_assets records with known sha256
-- Groups existing records by sha256, selects canonical storage_path, and computes authoritative reference_count
INSERT OR IGNORE INTO stored_media_files (
    id,
    sha256,
    storage_path,
    file_size_bytes,
    mime_type,
    duration_seconds,
    width,
    height,
    fps,
    video_codec,
    audio_codec,
    is_external,
    reference_count,
    created_at,
    updated_at
)
SELECT
    'smf_' || substr(sha256, 1, 16) AS id,
    sha256,
    min(storage_path) AS storage_path,
    max(file_size_bytes) AS file_size_bytes,
    mime_type,
    duration_seconds,
    width,
    height,
    fps,
    video_codec,
    audio_codec,
    min(is_external) AS is_external,
    count(*) AS reference_count,
    min(created_at) AS created_at,
    max(updated_at) AS updated_at
FROM media_assets
WHERE sha256 IS NOT NULL AND sha256 != ''
GROUP BY sha256;

-- 4. Link media_assets.stored_file_id to backfilled stored_media_files
UPDATE media_assets
SET stored_file_id = (
    SELECT smf.id
    FROM stored_media_files smf
    WHERE smf.sha256 = media_assets.sha256
)
WHERE sha256 IS NOT NULL AND sha256 != '';
