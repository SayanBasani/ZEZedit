-- ZezEdit 2.0 Milestone 15 Schema Migration: Non-Destructive Transcript Corrections & Audio Analysis

-- 1. Transcript Corrections Table (ZEZ-025)
CREATE TABLE IF NOT EXISTS transcript_corrections (
    id TEXT PRIMARY KEY,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    segment_id TEXT REFERENCES transcript_segments(id) ON DELETE SET NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transcript_corrections_asset
    ON transcript_corrections (media_asset_id, start_time);

CREATE INDEX IF NOT EXISTS idx_transcript_corrections_segment
    ON transcript_corrections (segment_id);

-- 2. Audio Analysis Metadata Table (ZEZ-021)
CREATE TABLE IF NOT EXISTS audio_analysis (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    has_audio INTEGER NOT NULL DEFAULT 1,
    sample_rate INTEGER,
    channels INTEGER,
    codec_name TEXT,
    bit_rate INTEGER,
    duration_seconds REAL,
    speech_density REAL NOT NULL DEFAULT 0.0,
    silence_intervals_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audio_analysis_run
    ON audio_analysis (analysis_run_id);

CREATE INDEX IF NOT EXISTS idx_audio_analysis_asset
    ON audio_analysis (media_asset_id);
