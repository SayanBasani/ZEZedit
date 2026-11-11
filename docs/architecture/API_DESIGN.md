# ZezEdit 2.0 — API Design & Conventions

## 1. API Versioning & Base Prefix

All backend endpoints live under a strict version prefix:
- Base path: `/api/v1`
- Frontend proxies `/api` to `http://127.0.0.1:8000` in development via Vite config, keeping browser requests same-origin (`http://localhost:5173/api/v1/...`).

Breaking response/schema changes require a new router prefix (`/api/v2`) rather than mutating existing `/api/v1` client contracts silently.

---

## 2. Resource Naming & HTTP Method Conventions

- Plural nouns for resource collections: `/api/v1/projects`, `/api/v1/jobs`, `/api/v1/exports`.
- Sub-resources scoped under parent entity:
  - `/api/v1/projects/{project_id}/media`
  - `/api/v1/projects/{project_id}/timeline`
  - `/api/v1/projects/{project_id}/candidates/{candidate_id}/reframing`
- Non-CRUD state transitions use explicit verb sub-paths with `POST`:
  - `/api/v1/jobs/{job_id}/cancel`
  - `/api/v1/jobs/{job_id}/retry`
  - `/api/v1/ai-editor/plans/{plan_id}/execute`
  - `/api/v1/providers/ollama/pull` (returns `202 Accepted` immediately; never blocks on long downloads — learned from `BUG-08A-8`).
- Long-running operations MUST NOT block HTTP request handlers; they enqueue a job record and return `202 Accepted` with `{ "job_id": "...", "status": "queued" }`.

---

## 3. Standard Request & Response Conventions

### Success Envelopes
- Single entity responses return typed Pydantic JSON directly (or wrapped with `data` for paginated lists):
  ```json
  {
    "items": [],
    "total": 0,
    "limit": 50,
    "offset": 0
  }
  ```
- Media streaming endpoints (`GET /.../video`, `/.../thumbnail`) support HTTP `206 Partial Content` Range headers so HTML5 `<video>` scrubbing works reliably in Chrome/Edge on Windows.

### Centralized Error Response Contract
All unhandled exceptions, Pydantic `RequestValidationError`s, and domain `AppError`s flow through `backend/app/core/errors.py` and emit a uniform JSON envelope:

```json
{
  "error": {
    "code": "PATH_OUTSIDE_BOUNDARY",
    "message": "Target path escapes permitted storage root.",
    "details": {
      "field": "source_path"
    },
    "request_id": "req_9f2a1c08"
  }
}
```

| HTTP Status | Meaning | Example `code` |
|---|---|---|
| `400` | Bad semantic request | `INVALID_TIME_RANGE`, `MEDIA_ALREADY_LINKED` |
| `403` | Security / boundary violation | `PATH_OUTSIDE_BOUNDARY`, `ROOT_DELETION_FORBIDDEN` |
| `404` | Missing record or asset | `PROJECT_NOT_FOUND`, `MEDIA_FILE_MISSING` |
| `409` | State conflict / confirmation required | `EXPORT_OVERWRITE_REQUIRES_CONFIRM`, `JOB_ALREADY_RUNNING` |
| `422` | Schema / AI validation error | `VALIDATION_ERROR`, `INVALID_AI_EDIT_PLAN` |
| `503` | Dependency unavailable (graceful degradation) | `OLLAMA_UNAVAILABLE`, `FFMPEG_MISSING` |

---

## 4. Implemented vs Planned Endpoint Inventory

### Implemented in Milestones 1–6
- `GET /api/v1/health` — Application health, SQLite status, storage writability, FFmpeg/FFprobe detection, Ollama status.
- `GET /api/v1/system/info` — Runtime info (OS, CPU count, Python version, app version).
- **Projects (M2):** `POST /api/v1/projects`, `GET /api/v1/projects`, `GET /api/v1/projects/{pid}`, `PATCH /api/v1/projects/{pid}`, `POST /api/v1/projects/{pid}/archive`, `POST /api/v1/projects/{pid}/restore`, `DELETE /api/v1/projects/{pid}`, `GET /api/v1/projects/{pid}/events`.
- **Media Pipeline (M2/M4):** `POST /api/v1/projects/{pid}/media/import-local`, `POST /api/v1/projects/{pid}/media/upload`, `GET /api/v1/projects/{pid}/media`, `GET /api/v1/projects/{pid}/media/{aid}`, `POST /api/v1/projects/{pid}/media/{aid}/relink`, `DELETE /api/v1/projects/{pid}/media/{aid}`, `GET /api/v1/projects/{pid}/media/{aid}/stream`, `GET /api/v1/projects/{pid}/media/{aid}/proxy-stream`, `GET /api/v1/projects/{pid}/media/{aid}/thumbnail`.
- **Jobs & Tasks (M2):** `GET /api/v1/jobs`, `GET /api/v1/jobs/{jid}`, `POST /api/v1/jobs/{jid}/cancel`, `POST /api/v1/jobs/{jid}/retry`.
- **Settings & Backups (M2):** `GET /api/v1/settings`, `PATCH /api/v1/settings`, `POST /api/v1/backups/create`, `GET /api/v1/backups`, `POST /api/v1/backups/restore`.
- **Video Analysis (M5):** `POST /api/v1/projects/{pid}/media/{aid}/analysis`, `GET /api/v1/projects/{pid}/media/{aid}/analysis`, `GET /api/v1/projects/{pid}/media/{aid}/analysis/{rid}/transcript`, `GET /api/v1/projects/{pid}/media/{aid}/analysis/{rid}/scenes`, `GET /api/v1/projects/{pid}/media/{aid}/analysis/{rid}/visual-observations`, `GET /api/v1/projects/{pid}/media/{aid}/analysis/{rid}/context`, `POST /api/v1/projects/{pid}/media/{aid}/analysis/{rid}/cancel`.
- **AI Highlight Discovery & Shorts Candidates (M6):**
  - `POST /api/v1/projects/{pid}/media/{aid}/highlights/discover` — Trigger candidate discovery with duration bounds, target count, and AI explanations.
  - `GET /api/v1/projects/{pid}/highlights` — Project highlights overview with total, recommended, needs_review, approved, and rejected counts.
  - `GET /api/v1/projects/{pid}/media/{aid}/highlights` — Candidates for a specific media asset.
  - `GET /api/v1/projects/{pid}/highlights/{cid}` — Detailed candidate record with score breakdown, quality gates, and citations.
  - `PATCH /api/v1/projects/{pid}/highlights/{cid}` — Fine-tune boundaries (`start_time`, `end_time`) and metadata with audit trail (`is_user_modified=True`).
  - `POST /api/v1/projects/{pid}/highlights/{cid}/approve` — Approve candidate.
  - `POST /api/v1/projects/{pid}/highlights/{cid}/reject` — Reject candidate with reason.
  - `POST /api/v1/projects/{pid}/highlights/{cid}/restore` — Restore candidate from approved/rejected state.
  - `POST /api/v1/projects/{pid}/highlights/{cid}/queue-render` — Toggle candidate inclusion in Shorts render queue.
  - `POST /api/v1/projects/{pid}/highlights/bulk-review` — Perform bulk approval, rejection, or restoration across candidate IDs.
  - `GET /api/v1/projects/{pid}/highlights/{cid}/alternatives` — Retrieve alternative temporal cuts (IoU $\ge 0.65$) sharing `overlap_group_id`.
- **Smart Reframing & Dynamic Crop (M7):**
  - `POST /api/v1/projects/{pid}/media/{aid}/reframing/analyze` — Run OpenCV subject tracking and generate authoritative reframing plan (`9:16`, `1:1`, `16:9`).
  - `GET /api/v1/projects/{pid}/reframing/{plan_id}` — Retrieve active reframing plan, keyframes, smoothing config, and active revision ID.
  - `GET /api/v1/projects/{pid}/reframing/{plan_id}/preview?timestamp={t}` — Live mathematical preview crop geometry and active subjects at timestamp $t$.
  - `POST /api/v1/projects/{pid}/reframing/{plan_id}/overrides` — Save manual pan offset, zoom, and headroom adjustments; creates new versioned revision in `reframing_revisions`.
  - `GET /api/v1/projects/{pid}/reframing/{plan_id}/revisions` — List all immutable historical revisions for this plan.
  - `POST /api/v1/projects/{pid}/reframing/{plan_id}/revisions/{rev_id}/restore` — Restore prior revision keyframes and parameters.
  - `POST /api/v1/projects/{pid}/reframing/{plan_id}/render` — Execute real FFmpeg filtergraph render producing vertical MP4 in `storage/shorts/`.
  - `GET /api/v1/projects/{pid}/reframing/{plan_id}/video` — Stream rendered reframed vertical video with HTTP 206 byte-range support.
- **Rendering Engine, Export Pipeline & Automatic Shorts (M8):**
  - `GET /api/v1/projects/{pid}/exports/presets` — Return standard export presets (`shorts_reels_9_16`, `landscape_16_9`, `square_1_1`).
  - `POST /api/v1/projects/{pid}/exports/render` — Submit an export render job with candidate, preset, caption styling, and audio settings.
  - `POST /api/v1/projects/{pid}/exports/preview` — Generate low-resolution fast 480p preview clip for interactive preview.
  - `GET /api/v1/projects/{pid}/exports` — List all exported videos for a project with status, validation results, and duration.
  - `GET /api/v1/projects/{pid}/exports/{export_id}` — Get detailed export record and FFprobe validation details.
  - `POST /api/v1/projects/{pid}/exports/{export_id}/cancel` — Cancel active export render job and terminate subprocess tree safely.
  - `DELETE /api/v1/projects/{pid}/exports/{export_id}` — Safely delete an export file and database record.
  - `GET /api/v1/projects/{pid}/exports/{export_id}/video` — Stream rendered video file with HTTP 206 byte-range seeking support.

- **Timeline Editor, Non-Destructive Editing & AI Assistant (M9):**
  - `GET /api/v1/projects/{pid}/timeline` — Retrieve active project sequence or initialize default tracks.
  - `POST /api/v1/projects/{pid}/timelines` — Create a new timeline sequence.
  - `GET /api/v1/projects/{pid}/timelines/{tl_id}` — Get timeline with tracks, clips, and duration.
  - `PATCH /api/v1/projects/{pid}/timelines/{tl_id}/settings` — Update sequence name, fps, or canvas dimensions.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/tracks` — Add video, audio, or overlay track.
  - `PATCH /api/v1/projects/{pid}/timelines/{tl_id}/tracks/{tr_id}` — Update track mute, lock, visibility, or order.
  - `DELETE /api/v1/projects/{pid}/timelines/{tl_id}/tracks/{tr_id}` — Delete a track and all its clips.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/clips` — Insert clip onto track with boundary checks.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/clips/move` — Move clip to new timeline start time or track.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/clips/trim` — Trim clip in/out boundaries.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/clips/split` — Split clip at playhead time into two adjacent clips.
  - `DELETE /api/v1/projects/{pid}/timelines/{tl_id}/clips/{clip_id}` — Delete clip (reversible via Undo).
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/clips/{clip_id}/duplicate` — Duplicate clip.
  - `PATCH /api/v1/projects/{pid}/timelines/{tl_id}/clips/{clip_id}` — Update volume, speed, transform, or content properties.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/overlays/text` — Add text overlay clip with color and size.
  - `GET /api/v1/projects/{pid}/timelines/{tl_id}/history` — Get history log and undo/redo availability.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/history/undo` — Revert most recent operation.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/history/redo` — Reapply next undone operation.
  - `GET /api/v1/projects/{pid}/timelines/{tl_id}/ai/conversation` — Retrieve active AI conversation.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/ai/messages` — Send natural language instruction, get reply or proposed plan.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/ai/plans/{plan_id}/approve` — Approve and execute AI editing plan.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/ai/plans/{plan_id}/reject` — Reject proposed plan.
  - `POST /api/v1/projects/{pid}/timelines/{tl_id}/render` — Render multi-track timeline using Milestone 8 export engine.

### Planned Endpoints (Milestones 10–12)
- **Conversational AI Prompt Editing (M10):** Natural language edit refinement.
- **Character Extraction (M11):** `/api/v1/character-extraction/jobs`, `/api/v1/character-extraction/entities/{id}`, `/api/v1/character-extraction/profiles`
- **Packaging & Archiving (M12):** `/api/v1/projects/{id}/archive-package`, `/api/v1/system/backups`
