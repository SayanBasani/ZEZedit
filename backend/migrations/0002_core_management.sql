-- ZezEdit 2.0 Milestone 2 Schema Migration: Core Project Management & Assets

-- 1. Upgrade projects table with configuration and last opened tracking
ALTER TABLE projects ADD COLUMN project_config_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE projects ADD COLUMN last_opened_at TEXT;

-- 2. Media Assets Table
CREATE TABLE IF NOT EXISTS media_assets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    is_external INTEGER NOT NULL DEFAULT 0,
    media_type TEXT NOT NULL DEFAULT 'video',
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT,
    duration_seconds REAL,
    width INTEGER,
    height INTEGER,
    fps REAL,
    video_codec TEXT,
    audio_codec TEXT,
    availability_status TEXT NOT NULL DEFAULT 'present',
    proxy_reference_path TEXT,
    thumbnail_reference_path TEXT,
    metadata_status TEXT NOT NULL DEFAULT 'unextracted',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_assets_project_avail
    ON media_assets (project_id, availability_status);

-- 3. Upgrade jobs table with worker_id, retry_count, cancellation fields and align column names
ALTER TABLE jobs ADD COLUMN worker_id TEXT;
ALTER TABLE jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN input_config_json TEXT;
ALTER TABLE jobs ADD COLUMN result_metadata_json TEXT;
ALTER TABLE jobs ADD COLUMN cancellation_requested_at TEXT;
ALTER TABLE jobs ADD COLUMN cancelled_at TEXT;

-- 4. Project Activity / Event History Table
CREATE TABLE IF NOT EXISTS project_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_summary TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_events_proj_created
    ON project_events (project_id, created_at DESC);
