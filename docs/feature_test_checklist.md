# ZezEdit 2.0 — Feature & Verification Checklist

This checklist tracks concrete verification criteria per milestone. Items may only be checked `[x]` after running actual tests or live verification against running processes.

---

## Milestone 1 — Architecture Redesign & Safe Project Foundation
- [x] `D:\ZezEdit` exists as an independent workspace.
- [x] Git repository initialized strictly inside `D:\ZezEdit` (verified no unintended modifications outside `D:\ZezEdit`).
- [x] `.gitignore` excludes `storage/`, `*.db*`, `node_modules/`, `.venv/`, and temporary build outputs.
- [x] `README.md` opens with exact Windows prerequisites, installation commands, setup steps, and PowerShell run commands (using `npm`).
- [x] All 11 required architecture and requirements documents present in `docs/` and `docs/architecture/`.
- [x] Python `.venv` environment created inside `backend/.venv` and dependencies install cleanly.
- [x] SQLite initializes via versioned SQL migrations (`migrations/0001_initial_schema.sql` tracked in `schema_migrations`).
- [x] Re-running migrations is idempotent (applied migrations are skipped, checksum/tracking preserved).
- [x] Path confinement helper rejects path traversal (`..\`, `C:\Windows`, symlink escape, root `D:\`) and blocks recursive deletion of `ZEZEDIT_STORAGE_ROOT`.
- [x] FastAPI server boots on `127.0.0.1:8000` and `/api/v1/health` returns JSON including DB, storage, FFmpeg/FFprobe, and Ollama probe status.
- [x] Frontend `npm run build` (`tsc && vite build`) compiles with zero TypeScript or bundler errors.

---

## Milestone 2 — Core Backend, Database & Persistent Project Management
- [x] Numbered migration `0002_core_management.sql` upgrades schema without dropping data.
- [x] Automatic pre-migration snapshot created in `storage/backups/` before applying schema upgrades.
- [x] SQLite foreign keys enforced (`PRAGMA foreign_keys = ON`).
- [x] Project management service supports create, get, list, update, archive, restore, and explicit confirmation-protected deletion.
- [x] Persistent `project_events` activity ledger records project creation, updates, and media registrations.
- [x] Media metadata service supports external media references, metadata extraction updates, `missing` status detection, and relinking.
- [x] Single authoritative job orchestrator enforces valid state transitions and rejects illegal transitions (e.g. running to queued).
- [x] Cancellation request on running job transitions to `cancelling` until worker acknowledgment.
- [x] Startup recovery detects jobs left `running`/`cancelling` from an unclean process termination and transitions them to `interrupted`.
- [x] Retry rules enforce maximum attempt counts.
- [x] Application settings persist in SQLite with automatic secret redaction (`[REDACTED]`).
- [x] Storage service inspects directory accessibility, total/free disk space, and per-category folder byte counts.
- [x] Online SQLite backup (`BackupService`) creates verified snapshots using `sqlite3.backup()` and performs restore validation.
- [x] REST endpoints registered under `/api/v1/*` (`/projects`, `/media`, `/jobs`, `/settings`, `/system/backups`, `/storage/inspect`, `/system/capabilities`).
- [x] Frontend project workspace (`ProjectsView.tsx`) allows creating, viewing, archiving, restoring, and deleting projects via `/api/v1`.
- [x] Automated pytest suite passes 12/12 tests with 100% pass rate.
