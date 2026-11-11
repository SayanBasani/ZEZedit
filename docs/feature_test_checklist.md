# ZezEdit 2.0 — Feature & Verification Checklist

This checklist tracks concrete verification criteria per milestone. Items may only be checked `[x]` after running actual tests or live verification against running processes.

---

## Milestone 1 — Architecture Redesign & Safe Project Foundation

### 1. Project Hygiene & Git Safety
- [ ] `D:\ZezEdit` exists as an independent workspace.
- [ ] Git repository initialized strictly inside `D:\ZezEdit` (verified no unintended modifications outside `D:\ZezEdit`).
- [ ] `.gitignore` excludes `storage/`, `*.db*`, `node_modules/`, `.venv/`, and temporary build outputs.

### 2. Documentation Deliverables
- [ ] `README.md` opens with exact Windows prerequisites, installation commands, setup steps, and PowerShell run commands (using `npm`).
- [ ] All 11 required architecture and requirements documents present in `docs/` and `docs/architecture/`.

### 3. Backend Core, Database Migrations & Security Boundaries
- [ ] Python `.venv` environment created inside `backend/.venv` and dependencies install cleanly.
- [ ] SQLite initializes via versioned SQL migrations (`migrations/0001_initial_schema.sql` tracked in `schema_migrations`).
- [ ] Re-running migrations is idempotent (applied migrations are skipped, checksum/tracking preserved).
- [ ] Path confinement helper rejects path traversal (`..\`, `C:\Windows`, symlink escape, root `D:\`) and blocks recursive deletion of `ZEZEDIT_STORAGE_ROOT`.
- [ ] FastAPI server boots on `127.0.0.1:8000` and `/api/v1/health` returns JSON including DB, storage, FFmpeg/FFprobe, and Ollama probe status.
- [ ] Automated backend pytest suite passes cleanly.

### 4. Frontend Foundation & Connectivity
- [ ] `npm install` succeeds cleanly in `frontend/`.
- [ ] `npm run build` (`tsc && vite build`) compiles cleanly with zero TypeScript or bundler errors.
- [ ] Frontend Vite dev server starts and loads cleanly without uncaught runtime errors.
- [ ] Frontend UI communicates live with `/api/v1/health` and accurately displays backend health, storage status, and environment probes.
- [ ] Bounded root layout (`h-screen max-h-screen overflow-hidden`) keeps sidebar stationary and allows independent workspace scrolling (`BUG-08A-1/2` prevention).

---

## Upcoming Milestones Verification Backlog (Not Started)

### Milestone 2 — Media Library & Storage Isolation
- [ ] Streaming file import copies/links 1–2 GB+ MP4 without exceeding bounded RAM ceiling.
- [ ] Imported original media file checksum matches before/after proxy & analysis tasks (immutability verified).
- [ ] Missing external media transitions state to `missing` without deleting project edits; relinking restores playback.

### Milestone 3 — Single Authoritative Job Orchestrator
- [ ] Simulated process crash leaves orphaned `running` job cleanly recovered on backend restart.
- [ ] Cancelling an active job terminates registered child PIDs cleanly and isolates temp cleanup to owned temp directory.

### Milestone 4 — AI Provider Abstraction & Settings
- [ ] Ollama inventory reflects `http://127.0.0.1:11434/api/tags` dynamically (`qwen3-vl:4b-instruct`).
- [ ] Unreachable Ollama or missing Faster-Whisper degrades gracefully without HTTP 500 or wiping UI state.

### Milestones 5–10 — Analysis, Reframing, Timeline, AI Editor, Characters, Export
- [ ] Dynamic reframing crop preview pixels equal FFmpeg render filter crop coordinates.
- [ ] Timeline undo/redo stack and autosave survive page reload.
- [ ] AI Editor rejects unvalidated plans and blocks any direct OS/shell execution attempts.
- [ ] Character Extraction keeps face/HSV grouping honest without false identity/diarization claims.
- [ ] Final MP4 exports pass FFprobe structural validation and refuse accidental overwrite without confirmation.
