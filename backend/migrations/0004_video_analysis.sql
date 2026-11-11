-- ZezEdit 2.0 Milestone 5 Schema Migration: Video Analysis Engine, Transcription & Visual Understanding

-- 1. Analysis Runs Table
CREATE TABLE IF NOT EXISTS analysis_runs (
    id TEXT PRIMARY KEY,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    profile TEXT NOT NULL DEFAULT 'balanced', -- fast, balanced, detailed
    config_json TEXT NOT NULL DEFAULT '{}',
    progress_pct REAL NOT NULL DEFAULT 0.0,
    current_stage TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_asset
    ON analysis_runs (media_asset_id, status);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_project
    ON analysis_runs (project_id, created_at DESC);

-- 2. Transcript Segments Table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    language TEXT,
    confidence REAL,
    words_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transcript_segments_range
    ON transcript_segments (analysis_run_id, start_time, end_time);

-- 3. Speech Turns Table
CREATE TABLE IF NOT EXISTS speech_turns (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    speaker_label TEXT NOT NULL DEFAULT 'Speaker 1',
    text TEXT NOT NULL,
    segment_ids_json TEXT NOT NULL DEFAULT '[]',
    turn_type TEXT NOT NULL DEFAULT 'statement', -- statement, question, exclamation, pause_gap
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_speech_turns_range
    ON speech_turns (analysis_run_id, start_time, end_time);

-- 4. Video Scenes Table
CREATE TABLE IF NOT EXISTS video_scenes (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    scene_index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    representative_timestamp REAL NOT NULL,
    thumbnail_path TEXT,
    change_score REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_video_scenes_range
    ON video_scenes (analysis_run_id, start_time, end_time);

-- 5. Sampled Frames Table
CREATE TABLE IF NOT EXISTS sampled_frames (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    timestamp REAL NOT NULL,
    frame_path TEXT NOT NULL,
    scene_id TEXT REFERENCES video_scenes(id) ON DELETE SET NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sampled_frames_time
    ON sampled_frames (analysis_run_id, timestamp);

-- 6. Visual Observations Table
CREATE TABLE IF NOT EXISTS visual_observations (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    timestamp REAL NOT NULL,
    frame_id TEXT REFERENCES sampled_frames(id) ON DELETE CASCADE,
    category TEXT NOT NULL, -- scene_setting, subjects, activity, on_screen_text, aesthetic_note
    description TEXT NOT NULL,
    provider_model TEXT NOT NULL, -- e.g. 'qwen3-vl:4b-instruct' or 'heuristic_fallback'
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_visual_observations_time
    ON visual_observations (analysis_run_id, timestamp);
