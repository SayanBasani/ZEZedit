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

### Implemented in Milestone 1
- `GET /api/v1/health` — Returns application status, SQLite migration state, `ZEZEDIT_STORAGE_ROOT` writability, FFmpeg/FFprobe detection, and non-blocking Ollama daemon reachability.
- `GET /api/v1/system/info` — Minimal runtime info (OS, CPU count, Python version, app version) verifying API routing and CORS/proxy setup.

### Planned Endpoints (Milestones 2–10)
- **Projects & Media (M2):** `/api/v1/projects`, `/api/v1/projects/{id}/media/import`, `/api/v1/projects/{id}/media/{asset_id}/relink`
- **Jobs (M3):** `/api/v1/jobs`, `/api/v1/jobs/{id}`, `/api/v1/jobs/{id}/cancel`, `/api/v1/jobs/{id}/retry`, `/api/v1/jobs/{id}/logs`
- **Providers & Settings (M4):** `/api/v1/settings`, `/api/v1/providers/ollama/models`, `/api/v1/providers/ollama/pull`, `/api/v1/diagnostics`
- **Analysis & Highlights (M5):** `/api/v1/projects/{id}/analyze`, `/api/v1/projects/{id}/transcript`, `/api/v1/projects/{id}/candidates`
- **Smart Reframing (M6):** `/api/v1/projects/{id}/shorts/{short_id}/reframing`, `/api/v1/projects/{id}/reframing/preview-frame`, `/api/v1/projects/{id}/shorts/{short_id}/revisions`
- **Timeline Editor (M7):** `/api/v1/projects/{id}/timeline`, `/api/v1/projects/{id}/timeline/operations`, `/api/v1/projects/{id}/timeline/undo`, `/api/v1/projects/{id}/timeline/redo`
- **AI Video Editor (M8):** `/api/v1/projects/{id}/ai-editor/chat`, `/api/v1/projects/{id}/ai-editor/plans/{plan_id}/execute`
- **Character Extraction (M9):** `/api/v1/character-extraction/jobs`, `/api/v1/character-extraction/entities/{id}`, `/api/v1/character-extraction/profiles`
- **Exports & Backups (M10):** `/api/v1/projects/{id}/exports`, `/api/v1/system/backups`
