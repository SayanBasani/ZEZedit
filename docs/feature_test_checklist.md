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

---

## Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification

- [x] SQLite migration `0004_video_analysis.sql` applies forward-only schema upgrade: `analysis_runs`, `transcript_segments`, `speech_turns`, `video_scenes`, `sampled_frames`, `visual_observations` with indexed ranges.
- [x] Automatic pre-migration database snapshot saved to `storage/backups/pre_migration_0004_*.db`.
- [x] Audio extraction service (`audio_extractor.py`) extracts 16kHz mono 16-bit PCM WAV tracks to ephemeral job scratch via FFmpeg.
- [x] Faster-Whisper CPU provider (`transcription.py`) runs speech recognition with segment boundaries, language detection, and word timestamps on CPU with `int8` compute type and PyAV 14+ compatibility patch.
- [x] Dialogue segmentation (`speech_segmentation.py`) groups transcript segments across conversational pauses (`> 0.8s`) into speech turns with statement/question/exclamation detection.
- [x] FFmpeg scene boundary detection (`scene_detector.py`) extracts visual scene cut timestamps and midpoint representative frames.
- [x] Controlled visual keyframe sampler (`frame_sampler.py`) extracts downscaled (max 640px) keyframes capped by analysis profile (`fast`, `balanced`, `detailed`).
- [x] Visual understanding service (`visual_understanding.py`) queries local Ollama (`qwen3-vl:4b-instruct`) for factual scene setting, subjects, and text observations with conservative language and deterministic heuristic fallback when Ollama is offline.
- [x] Temporal context aggregator (`temporal_aggregator.py`) resolves active scene, active speech turn, nearby dialogue, and visible observations at any query timestamp.
- [x] Video analysis pipeline coordinator (`analysis_pipeline.py`) coordinates multi-stage background execution with cancellation support.
- [x] Versioned REST API endpoints (`/api/v1/projects/{pid}/media/{aid}/analysis`) support run triggering, status polling, transcript querying, scenes list, visual observations, and temporal context inspection.
- [x] Interactive Analysis Workspace (`AnalysisWorkspace.tsx`) provides synchronized video player, interactive scrub bar, searchable transcript with seek-on-click, scene cuts strip, visual observation stream, and temporal context inspector.
- [x] Automated backend test suite passes 25/25 tests (`pytest tests/ -v`, including 7 tests in `test_milestone5_analysis.py`).
- [x] Automated frontend test suite passes 26/26 tests (`npm test -- --run`, including 3 tests in `analysis.test.tsx`).
- [x] Production build passes cleanly in 2.29s with 0 TypeScript errors.
- [x] Live end-to-end HTTP verification confirms real video generation, local import, synchronous analysis run execution (audio extraction -> whisper -> scene detection -> frame sampling -> observations -> persistence), transcript query, and temporal context query at 1.0s.

---

## Milestone 6: AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking Verification

- [x] SQLite migration `0005_highlight_candidates.sql` applies forward-only schema upgrade creating `shorts_candidates` table with range indexes, score breakdowns, gate results, overlap groups, and scoring version `2.0.0-m6`.
- [x] Automatic pre-migration snapshot saved to `storage/backups/pre_migration_0005_*.db`.
- [x] Highlight discovery engine (`highlight_discovery.py`) generates speech dialogue moments, scene visual moments, and question/answer dialogue pairings from analysis data.
- [x] Context-aware boundary snapping snaps candidate starts/ends to visual scene cuts within 0.6s and dialogue pause closures, applying 0.3s lead-in and 0.5s lead-out buffers to eliminate flash frames and premature cutoffs.
- [x] 9-component explainable scoring model (`2.0.0-m6`) evaluates Semantic Interest (0-20), Narrative Completeness (0-20), Conversation Structure (0-15), Visual Interest (0-15), Audio Evidence (0-10), Opening Clarity (0-10), Ending Completeness (0-10), Duration Suitability (-5 to +10), and Context Dependency Penalty (0 to -15).
- [x] Quality gates enforce minimum criteria and assign `recommended`, `needs_review`, or `rejected` review status with explainable failure reasons.
- [x] Temporal overlap clustering identifies candidate pairs with $\text{IoU} \ge 0.65$, linking secondary variations under `overlap_group_id` and demoting them so the primary candidate remains prominent.
- [x] Ollama AI content explanation queries `qwen3-vl:4b-instruct` for Hook, Why It Works, Target Audience, Strengths, and Risks, with deterministic heuristic fallback when offline.
- [x] Shorts candidate REST API (`/api/v1/projects/{pid}/highlights`) supports candidate discovery, project overview counts, candidate detail, boundary patch with audit trail (`is_user_modified=True`), approve, reject, restore, render queue toggle, and bulk review.
- [x] Interactive Highlights & Shorts Studio Workspace (`HighlightsWorkspace.tsx`) provides metric counter cards, search/filter toolbar, status tabs, candidate cards, boundary slider fine-tuning, 9-component score breakdown, and alternative cuts list.
- [x] Automated backend test suite passes 28/28 tests (`pytest tests/ -v`, including 3 tests in `test_milestone6_highlights.py`).
- [x] Automated frontend test suite passes 31/31 tests across 5 suites (`npm test -- --run`, including 5 tests in `highlights.test.tsx`).
- [x] Production build passes cleanly in 2.23s with 0 TypeScript errors.
- [x] Live end-to-end HTTP verification confirms project creation, media import, video analysis, highlight discovery, boundary modification (`is_user_modified=True`), candidate approval, and render queue toggling.
