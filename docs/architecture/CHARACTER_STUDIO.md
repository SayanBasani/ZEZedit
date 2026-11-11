# ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library

## 1. Overview & Principles

The Character Extraction Studio provides human-in-the-loop character and face discovery, appearance tracking, screen-time estimation, and a persistent Character Library.

### Fundamental Constraints & Transparency Principles

1. **Non-Mandatory & Decoupled:**
   Character extraction is an independent workflow. It is never required or coupled to AI highlight discovery, smart reframing, multi-track timeline editing, or video export.

2. **Explicit Transparency:**
   Automated detections and spatial-temporal groupings are explicitly designated as **provisional candidate clusters**. They do not constitute biometric facial recognition, identity verification, or automated person identification.

3. **Temporal Dialogue Association (Not Diarization):**
   Speech segments intersecting an observation timestamp are labeled as **unverified temporal dialogue associations**. They indicate that dialogue occurred during that time window, not that the detected face was confirmed to be speaking.

4. **Non-Destructive Human Review:**
   When a user detaches an observation (false positive) from a candidate, the observation record is flagged as `is_detached = 1`, but the cropped thumbnail and raw disk evidence are strictly preserved.

5. **CPU-First Architecture:**
   All image processing, color segmentation, contour analysis, and thumbnail generation run on standard CPU architectures (tested on Intel Core i3) without requiring CUDA, dedicated GPUs, or external network calls.

---

## 2. Database Schema (Migration `0009_character_studio.sql`)

```sql
-- 1. Extraction Jobs
CREATE TABLE character_extraction_jobs (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
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

-- 2. Character Profiles (Persistent Character Library)
CREATE TABLE character_profiles (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    avatar_path TEXT,
    biography TEXT DEFAULT '',
    appearance_tags TEXT NOT NULL DEFAULT '[]',
    total_appearances INTEGER NOT NULL DEFAULT 0,
    total_screen_time_seconds REAL NOT NULL DEFAULT 0.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. Character Candidates (Provisional visual clusters)
CREATE TABLE character_candidates (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES character_extraction_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'provisional',
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

-- 4. Character Observations (Individual frame detections)
CREATE TABLE character_observations (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES character_candidates(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES character_extraction_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    timestamp REAL NOT NULL,
    frame_path TEXT,
    thumbnail_path TEXT NOT NULL,
    bounding_box TEXT NOT NULL,
    detection_type TEXT NOT NULL DEFAULT 'face',
    confidence REAL NOT NULL DEFAULT 0.8,
    detection_method TEXT NOT NULL DEFAULT 'opencv_haar',
    unverified_dialogue TEXT,
    is_detached BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

-- 5. Character Review Events (Immutable Audit Log)
CREATE TABLE character_review_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id TEXT,
    action_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT,
    created_at TEXT NOT NULL
);
```

---

## 3. Human Review Operations

- **Rename:** Edits candidate label (e.g. "Candidate #1" $\to$ "Host Alex") and logs review event.
- **Confirm to Library:** Converts candidate to confirmed status, links to persistent `character_profiles` record, aggregates screen time and appearances, and logs review event.
- **Merge:** Consolidates multiple candidate clusters into a single target candidate, reassigning observations without data loss.
- **Split:** Moves selected observations into a new candidate cluster, recalculating screen time and observation counts for both.
- **Detach Observation:** Flags an observation as detached (`is_detached = 1`), subtracting it from active candidate metrics while preserving disk evidence.
- **Reject:** Marks candidate as rejected (e.g., inanimate object or false positive).

---

## 4. Documented JSON Export Schema

Exported character profiles include the full profile definition, associated candidate clusters, observation timestamps, detection bounding boxes, and formal transparency disclaimers:

```json
{
  "export_version": "2.0.0",
  "exported_at": "2026-11-12T01:39:21Z",
  "profile": {
    "id": "char_9631131006f1",
    "project_id": "proj_0f8238e5761d",
    "name": "Alex Mercer",
    "avatar_path": "D:\\ZezEdit\\storage\\characters\\proj_0f8238e5761d\\thumbs\\obs_47450c0e9f28.jpg",
    "biography": "Protagonist in the tech demo series",
    "appearance_tags": ["lead", "dark jacket", "host"],
    "total_appearances": 1,
    "total_screen_time_seconds": 5.0,
    "metadata_json": {},
    "created_at": "2026-11-12T01:39:21Z",
    "updated_at": "2026-11-12T01:39:21Z"
  },
  "associated_candidates": [
    {
      "candidate_id": "cand_d4e956a5e750",
      "label": "Protagonist Lead",
      "observation_count": 5,
      "sampled_screen_time_seconds": 5.0,
      "estimated_screen_time_seconds": 5.0,
      "observations": [
        {
          "id": "obs_47450c0e9f28",
          "timestamp": 1.0,
          "detection_type": "face",
          "confidence": 0.85,
          "unverified_dialogue": null
        }
      ]
    }
  ],
  "screen_time_summary": {
    "total_appearances": 1,
    "total_screen_time_seconds": 5.0,
    "candidate_clusters_count": 1
  },
  "disclaimer": "ZezEdit 2.0 Character Studio metadata. Identity grouping is provisional, user-verified, and does not constitute biometric facial recognition. Associated dialogue represents temporal transcript overlap, not confirmed speaker diarization."
}
```
