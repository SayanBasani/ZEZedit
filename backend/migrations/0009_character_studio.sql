-- ZezEdit 2.0 Milestone 10 Schema Migration: Character Extraction Studio, Character Library & Review System

-- 1. Character Extraction Jobs
CREATE TABLE IF NOT EXISTS character_extraction_jobs (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    sample_interval_sec REAL NOT NULL DEFAULT 1.0,
    detector_model TEXT NOT NULL DEFAULT 'opencv_haar_cpu',
    frames_sampled INTEGER NOT NULL DEFAULT 0,
    detections_count INTEGER NOT NULL DEFAULT 0,
    candidates_count INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_jobs_project
    ON character_extraction_jobs (project_id, status);

-- 2. Character Profiles (Persistent Character Library)
CREATE TABLE IF NOT EXISTS character_profiles (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    avatar_path TEXT,
    biography TEXT DEFAULT '',
    appearance_tags TEXT NOT NULL DEFAULT '[]', -- JSON string array
    total_appearances INTEGER NOT NULL DEFAULT 0,
    total_screen_time_seconds REAL NOT NULL DEFAULT 0.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_profiles_project
    ON character_profiles (project_id, name);

-- 3. Character Candidates (Provisional visual clusters)
CREATE TABLE IF NOT EXISTS character_candidates (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES character_extraction_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'provisional', -- 'provisional', 'confirmed', 'rejected', 'merged', 'split'
    confirmed_character_id TEXT REFERENCES character_profiles(id) ON DELETE SET NULL,
    observation_count INTEGER NOT NULL DEFAULT 0,
    sampled_screen_time_seconds REAL NOT NULL DEFAULT 0.0,
    estimated_screen_time_seconds REAL NOT NULL DEFAULT 0.0,
    representative_thumbnail_path TEXT,
    detection_methodology TEXT NOT NULL DEFAULT 'opencv_haar_spatial_temporal',
    clustering_confidence REAL NOT NULL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_candidates_job
    ON character_candidates (job_id, review_status);

CREATE INDEX IF NOT EXISTS idx_char_candidates_project
    ON character_candidates (project_id, review_status);

-- 4. Character Observations (Individual frame detections)
CREATE TABLE IF NOT EXISTS character_observations (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES character_candidates(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES character_extraction_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    timestamp REAL NOT NULL,
    frame_path TEXT,
    thumbnail_path TEXT NOT NULL,
    bounding_box TEXT NOT NULL, -- JSON { x, y, width, height }
    detection_type TEXT NOT NULL DEFAULT 'face', -- 'face', 'person'
    confidence REAL NOT NULL DEFAULT 0.8,
    detection_method TEXT NOT NULL DEFAULT 'opencv_haar',
    unverified_dialogue TEXT,
    is_detached BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_obs_candidate
    ON character_observations (candidate_id, is_detached);

CREATE INDEX IF NOT EXISTS idx_char_obs_job
    ON character_observations (job_id);

-- 5. Character Review Events (Audit Log)
CREATE TABLE IF NOT EXISTS character_review_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id TEXT,
    action_type TEXT NOT NULL, -- 'rename', 'confirm', 'merge', 'split', 'reject', 'detach_observation'
    payload_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_review_project
    ON character_review_events (project_id, created_at DESC);
