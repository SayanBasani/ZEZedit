# ZEZEDIT 2.0 — SESSION 5 IMPLEMENTATION AUDIT & ARCHITECTURAL SPECIFICATION
## Interactive Clip Preview, Editing, Smart Reframing & Subject Tracking

---

## 1. Executive Summary & Objective

In **Session 4**, we implemented the intelligent clip discovery pipeline, multimodal scoring, natural boundaries, and the persistent novelty ledger, enabling users to generate and review non-repetitive short-video candidates from long-form media.

**Session 5** establishes the dedicated interactive editing and framing environment for discovered candidates:
1. **Interactive Candidate Preview & Trimming:** Fine-grained adjustment of start and end timestamps, real-time duration recalculation, boundary constraint validation against media duration, and one-click "Reset to Original Boundaries".
2. **Aspect Ratio Support:** Selection between standard short-form and social aspect ratios (`9:16` vertical portrait, `1:1` square, `16:9` widescreen landscape, and `4:5` social feed portrait).
3. **Framing Modes:**
   - **Center Crop:** Symmetrical, predictable crop centered on the source footage.
   - **Manual Positioning:** User-controlled horizontal offset (0–100%), vertical offset (0–100%), and digital zoom (1.0x–2.5x).
   - **Smart Subject Tracking:** Intelligent framing driven by `SubjectTracker` (OpenCV Haar cascades and visual saliency) and `FramingEngine`, computing crop keyframes over the candidate interval without re-decoding the full video.
4. **Data Isolation & Novelty Integrity:**
   - Discovered candidate records in `shorts_candidates` remain **100% immutable**. Original timestamps and AI scores are never overwritten.
   - The persistent novelty ledger `media_generated_clips_history` is **never mutated** by user edits. Candidate generation history and non-repetition guarantees are preserved.
   - Edits are persisted in a dedicated schema `candidate_clip_edits` (Migration 0014).

---

## 2. Existing Codebase Audit & Reusability Assessment

| Component | Location | Status | Assessment / Role in Session 5 |
| :--- | :--- | :--- | :--- |
| **`SubjectTracker`** | `backend/app/services/subject_tracker.py` | Complete | Provides CPU-based OpenCV Haar cascade detection for frontal/profile faces, upper bodies, and visual saliency fallback. Implements `track_clip(media_path, start_time, end_time, ...)` which samples frames at `sample_fps` without decoding the entire video. Reused for smart tracking. |
| **`FramingEngine`** | `backend/app/services/framing_engine.py` | Complete | Computes crop geometry (`calculate_crop_dimensions`), handles zoom, headroom factor, smoothing windows, and bounds constraints for `9:16`, `1:1`, `16:9`, `4:5`. Reused for crop math. |
| **`ReframingService`** | `backend/app/services/reframing_service.py` | Complete | Orchestrates `SubjectTracker` + `FramingEngine`, creates `reframing_plans` and `reframing_revisions`. Reused when running smart tracking on candidate intervals. |
| **`shorts_candidates` table** | `backend/migrations/0005...` & `0013...` | Complete | Stores generated candidates, natural boundaries, and quality scores. Kept strictly immutable. |
| **`candidate_clip_edits` table** | `backend/migrations/0014...` | **Newly Created** | Stores candidate-specific editing state: edited timestamps, aspect ratio, framing mode, manual crop offsets, tracked subject ID, reframing plan linkage, and versioning. |
| **`SingleVideoStudio.tsx`** | `frontend/src/views/SingleVideoStudio.tsx` | Complete | Houses the video studio workspace. Hosts the new interactive `ClipEditorModal` for previewing and modifying candidate clips. |

---

## 3. Database Schema Design (Migration 0014)

```sql
CREATE TABLE IF NOT EXISTS candidate_clip_edits (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL,
    media_asset_id TEXT NOT NULL,
    original_start_time REAL NOT NULL,
    original_end_time REAL NOT NULL,
    edited_start_time REAL NOT NULL,
    edited_end_time REAL NOT NULL,
    edited_duration REAL NOT NULL,
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    framing_mode TEXT NOT NULL DEFAULT 'center',
    manual_crop_x_pct REAL DEFAULT 50.0,
    manual_crop_y_pct REAL DEFAULT 50.0,
    manual_crop_zoom REAL DEFAULT 1.0,
    tracked_subject_id TEXT,
    tracking_status TEXT DEFAULT 'none',
    reframing_plan_id TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES shorts_candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (media_asset_id) REFERENCES media_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (reframing_plan_id) REFERENCES reframing_plans(id) ON DELETE SET NULL
);
```

### Key Invariants:
1. **Uniqueness:** Each candidate has at most one active edit record (`candidate_id TEXT NOT NULL UNIQUE`).
2. **Cascade Deletion:** If a candidate, media asset, or project is deleted, edits are cleaned up automatically.
3. **Pristine Reference:** `original_start_time` and `original_end_time` are copied from the candidate upon edit creation and never mutated, allowing instant "Reset to Original" without querying older snapshots.

---

## 4. Backend Service & API Specification

### 4.1 Service: `ClipEditingService` (`backend/app/services/clip_editing_service.py`)
- `get_or_create_edit(candidate_id, project_id, media_asset_id)`: Fetches existing edit or initializes a new draft from candidate discovery boundaries.
- `save_edit(...)`: Validates timestamp bounds (`0 <= start < end <= asset_duration`, `min_duration >= 1.0s`), updates aspect ratio, framing mode, and manual crop parameters.
- `reset_to_original(candidate_id, project_id)`: Restores `edited_start_time = original_start_time`, `edited_end_time = original_end_time`, `aspect_ratio = '9:16'`, `framing_mode = 'center'`.
- `run_clip_tracking(candidate_id, project_id, target_aspect_ratio)`: Calls `ReframingService.analyze_and_create_plan` bounded to `[edited_start_time, edited_end_time]` and links the generated `reframing_plan_id`.

### 4.2 REST Endpoints
- `GET /api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit`
- `PUT /api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit`
- `POST /api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit/reset`
- `POST /api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit/track`

---

## 5. UI/UX Design & Unslop Guidelines

The Clip Editor follows the established **Unslop** design direction:
- **Character:** Precise, quiet, tool-grade video editing suite.
- **Palette:** Dark graphite surfaces (`#14171F`, `#1C202B`), subtle borders (`#2D3548`), high-contrast text (`#E2E8F0`, `#94A3B8`).
- **Typography & Details:** Clean monospace timecode displays (`00:14.50`), pill indicators with subtle border highlights, standard Lucide icons (no playful emojis).
- **Interactive Controls:**
  - Transport controls with bounded candidate loop playback.
  - Interactive Start/End timecode spinners and range scrubber.
  - Visual Crop Box overlay representing the selected aspect ratio and manual X/Y crop offsets.
  - Dedicated "Reset to Original" button with clear confirmation.
