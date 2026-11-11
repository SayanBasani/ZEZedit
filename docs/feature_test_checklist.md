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

---

## Milestone 3 — Frontend Application Shell, Dashboard & Design System
- [x] Unified design system variables and tokens configured in `tailwind.config.js` and `src/styles/index.css`.
- [x] Light / dark / system preference theme engine with persistent `localStorage` synchronization and zero-flicker HTML root attributes.
- [x] Reusable accessible UI components created: `Button` (5 variants, 3 sizes, loading spinners), `Input` & `SearchInput` (with clear button), `Badge` (semantic colors), `Card` (interactive hover), `Dialog` & `ConfirmDialog` (keyboard accessible, backdrop blur, action callbacks), `EmptyState`, and `Skeleton`.
- [x] Stationary responsive application shell with collapsible desktop sidebar, tooltip labels, active job pills, mobile slide-over drawer, and theme switch header.
- [x] Root layout enforces `h-screen max-h-screen overflow-hidden` with scroll strictly confined to `<main className="flex-1 min-h-0 min-w-0 overflow-y-auto overscroll-contain">` (`BUG-08A-1/2` scrollbar trap resolved).
- [x] Studio Dashboard (`DashboardView`) displaying real project counts, recent project cards, live background tasks status, and quick workspace navigation pills.
- [x] Projects Manager (`ProjectsManager`) with Grid/List layout toggle, search filtering, status filtering dropdown, creation modal, archive/restore, and confirmation-protected delete.
- [x] Studio Settings Manager (`SettingsManager`) with theme selection, CPU hardware limits, proxy scrub resolution, default export presets, protected storage boundary display, and Ollama provider health.
- [x] Vitest and React Testing Library setup installed with jsdom environment.
- [x] Automated frontend unit test suite passes 17/17 tests (`src/test/designSystem.test.tsx` and `src/test/features.test.tsx`).
- [x] Production build (`npm run build`) compiles cleanly in under 2 seconds with zero TypeScript errors.

---

## Milestone 4 — Media Ingestion, Import & Media Library
- [x] Forward migration `0003_media_pipeline.sql` adds `proxy_status` column and indexing non-destructively with pre-migration snapshot.
- [x] FFprobe inspection service (`media_probe.py`) extracts container, duration, file size, bitrate, width, height, fps, DAR, orientation, video/audio codecs, sample rate, and channels.
- [x] Corrupt and empty media files rejected with structured `CORRUPT_MEDIA` and `EMPTY_MEDIA_FILE` errors.
- [x] FFmpeg thumbnail generator (`media_thumbnail.py`) creates representative downscaled JPEG frames at deterministic paths (`storage/thumbnails/{asset_id}.jpg`).
- [x] FFmpeg proxy generator (`media_proxy.py`) creates lightweight H.264 scrub proxies with fast-start atoms (`storage/proxies/{asset_id}_proxy_{profile}.mp4`) bounded by CPU thread constraints.
- [x] Ingestion pipeline supports both **External Reference** mode (zero file duplication) and **Managed Copy** mode (stream copied to `storage/media/{project_subdir}/`).
- [x] Large file handling avoids full RAM buffering via bounded 1 MB streaming chunks and verifies disk free space ($>100\text{ MB}$ margin).
- [x] Streaming HTTP upload endpoint (`POST /projects/{pid}/media/upload`) accepts multipart uploads directly to disk without memory bloat.
- [x] Media assets deletion purges derivative thumbnails and proxies, and only deletes source media if explicitly confirmed and managed (external files strictly protected).
- [x] Frontend Media Library interface (`MediaLibraryView.tsx`) with Grid and List view modes, storage statistics cards, search filtering, media type tabs, availability/proxy status filters, and sorting.
- [x] Import Dialog with Local Path and File Upload tabs, storage copy toggle, and immediate proxy generation checkbox.
- [x] Technical Metadata Drawer displaying full FFprobe parameters, codecs, aspect ratios, and full storage paths.
- [x] Missing media indicators with one-click Relink dialog restoring access to moved files.
- [x] Automated backend test suite passes 18/18 tests (including 6 real FFmpeg/FFprobe tests in `test_milestone4_media.py`).
- [x] Automated frontend test suite passes 23/23 tests (including 6 tests in `mediaLibrary.test.tsx`).
- [x] Live end-to-end HTTP verification confirms real FFmpeg video generation, import, thumbnail serving, proxy generation, and stream serving.
