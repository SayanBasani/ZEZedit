# ZezEdit 2.0 — Feature Status Tracker

**Last Updated:** 2026-11-12  
**Active Milestone:** Milestone 6 Completed — AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking

Status legend:
- **Implemented:** Code exists, integrated end-to-end, and verified with tests / runtime execution.
- **Partial:** Core scaffolding or partial layer exists; remaining workflow scheduled for later milestones.
- **Planned:** Designed in architecture specs; implementation scheduled in an upcoming milestone.
- **Not Started:** Future backlog item.
- **Blocked:** External dependency or unresolved blocker prevents verification.

---

## Core Foundation & Architecture (Milestone 1)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| FND-01 | Versioned Architecture & Design Blueprint (11 docs + README) | Docs | Implemented | `docs/architecture/` | Covers all 18 required architectural decisions |
| FND-02 | Configurable Storage Root & Directory Layout | Core / Storage | Implemented | `backend/app/core/storage.py` | Separates media, proxies, thumbnails, analysis, exports, temp, backups, db |
| FND-03 | Path Confinement & Anti-Root Recursive Deletion Guard | Core / Security | Implemented | `backend/app/core/security.py` | Blocks traversal, root deletion, and storage escapes |
| FND-04 | Structured Logging & Centralized Error Handling | Core / API | Implemented | `backend/app/core/logging.py`, `backend/app/core/errors.py` | Standard JSON-friendly logs and uniform error envelopes |
| FND-05 | SQLite WAL Connection & Forward-Only SQL Migration Runner | DB / Migrations | Implemented | `backend/app/db/migrator.py`, `backend/migrations/0001_initial_schema.sql` | Baseline metadata schema |
| FND-06 | FastAPI App Entry Point & `/api/v1/health` Endpoint | Backend API | Implemented | `backend/app/main.py`, `backend/app/api/v1/health.py` | Probes SQLite, storage root, FFmpeg, FFprobe, and Ollama |
| FND-07 | Minimal Bounded React/Vite/Tailwind Shell & Backend Connectivity Check | Frontend | Implemented | `frontend/src/app/App.tsx`, `frontend/src/services/apiClient.ts` | Stationary sidebar + scrollable main container (`BUG-08A-1/2` fix baked in) |

---

## Core Backend, Database & Project Management (Milestone 2)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M2-01 | Database Migration `0002_core_management.sql` | DB / Migrations | Implemented | `backend/migrations/0002_core_management.sql` | Upgrades projects & jobs, creates `media_assets` and `project_events` |
| M2-02 | Project Management Lifecycle & Events Service | Core Services | Implemented | `backend/app/services/projects.py` | Create, get, list, update, archive, restore, protected delete, events |
| M2-03 | Media Metadata & External Relinking Service | Core Services | Implemented | `backend/app/services/media.py` | Register external/stored media, metadata updates, mark missing, relinking |
| M2-04 | Persistent Job Orchestration & State Machine | Core Services | Implemented | `backend/app/services/jobs.py` | Strict transitions, cancellation, retries, startup recovery of interrupted jobs |
| M2-05 | Application Settings & Secret Redaction | Core Services | Implemented | `backend/app/services/settings_service.py` | SQLite JSON persistence, secret redaction (`[REDACTED]`) |
| M2-06 | Storage Inspection & Space Management | Core Services | Implemented | `backend/app/services/storage.py` | Real disk usage, category sizes, boundary checks |
| M2-07 | Online SQLite Backup & Restore Verification | Core Services | Implemented | `backend/app/services/backup_service.py` | Uses `sqlite3.backup()`, integrity check verification, safety snapshots |
| M2-08 | Versioned REST Endpoints (`/api/v1/*`) | Backend API | Implemented | `backend/app/api/v1/` | `projects`, `media`, `jobs`, `settings`, `backups`, `capabilities` |
| M2-09 | Frontend Project Workspace & Centralized Client | Frontend | Implemented | `frontend/src/features/projects/ProjectsView.tsx` | Create, list, archive/restore, delete projects, typed API client |
| M2-10 | Full Pytest Suite (12 unit + integration tests) | Testing | Implemented | `backend/tests/test_milestone2_core.py` | 100% pass covering migrations, state machine, relinking, backups |

---

## Frontend Application Shell, Dashboard & Design System (Milestone 3)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M3-01 | Design System Tokens & Unified Styling | UI Design System | Implemented | `frontend/tailwind.config.js`, `frontend/src/styles/index.css` | Canvas, surface, borders, text tiers, semantic accents |
| M3-02 | Dark / Light / System Mode & Theme Provider | UI Context | Implemented | `frontend/src/context/ThemeContext.tsx` | Instant sync, zero flicker, localStorage persistence |
| M3-03 | Component Library (Buttons, Inputs, Badges, Cards, Modals, States) | UI Components | Implemented | `frontend/src/components/ui/` | Fully accessible, typed with variants and animations |
| M3-04 | Responsive Studio Application Shell | UI Shell | Implemented | `frontend/src/app/App.tsx` | Fixed-height desktop sidebar + mobile drawer, active task badges |
| M3-05 | Studio Dashboard View | Features / Dashboard | Implemented | `frontend/src/features/dashboard/DashboardView.tsx` | Live metrics, recent projects, real-time background job monitor |
| M3-06 | Projects Management Interface | Features / Projects | Implemented | `frontend/src/features/projects/ProjectsManager.tsx` | Grid/list view modes, status filters, search, archive, delete modal |
| M3-07 | Settings Interface | Features / Settings | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | Hardware CPU limits, proxy scrub resolution, export presets, Ollama status |
| M3-08 | Frontend Vitest Test Suite (17 tests) | Testing | Implemented | `frontend/src/test/` | 100% pass covering components, contexts, and feature views |
| M3-09 | Production Bundle Verification | Build | Implemented | `dist/` | Production build clean in 1.86s, 60 kB gzip bundle |

---

## Media Ingestion, Import & Media Library (Milestone 4)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M4-01 | Database Migration `0003_media_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0003_media_pipeline.sql` | Adds `proxy_status` column and indexing to `media_assets` |
| M4-02 | FFprobe Technical Metadata Extraction Service | Media Services | Implemented | `backend/app/services/media_probe.py` | Robust parsing of video, audio, image streams, fps, DAR, orientation |
| M4-03 | FFmpeg Deterministic Thumbnail Generation | Media Services | Implemented | `backend/app/services/media_thumbnail.py` | Representative video frame seeks, downscaled JPEGs, artwork extraction |
| M4-04 | FFmpeg Proxy Transcode Engine (360p, 480p, 720p) | Media Services | Implemented | `backend/app/services/media_proxy.py` | CPU-bounded H.264 transcoding, fast-start atoms, thread confinement |
| M4-05 | Streaming Media Import Pipeline | Media Services | Implemented | `backend/app/services/media_pipeline.py` | Supports reference mode, copy mode, chunked streaming, disk space check |
| M4-06 | Versioned Media REST Endpoints | Backend API | Implemented | `backend/app/api/v1/media.py` | Import, streaming upload, thumbnail serving, proxy stream, stats, relink |
| M4-07 | Frontend Media Library View | Features / Media | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Grid/list view, metrics cards, search/filter/sort, details drawer, import modal |
| M4-08 | Backend Media Integration Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone4_media.py` | Real FFmpeg/FFprobe tests, synthetic video/audio, proxies, 100% pass |
| M4-09 | Frontend Media Vitest Suite (6 tests) | Testing | Implemented | `frontend/src/test/mediaLibrary.test.tsx` | Covers grid/list toggle, type/status filtering, search, import dialog |

---

## Video Analysis Engine, Transcription & Visual Understanding (Milestone 5)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M5-01 | Database Migration `0004_video_analysis.sql` | DB / Migrations | Implemented | `backend/migrations/0004_video_analysis.sql` | Schema for analysis runs, transcript segments, turns, scenes, frames, observations |
| M5-02 | 16kHz Mono Audio Extractor | Analysis Services | Implemented | `backend/app/services/audio_extractor.py` | FFmpeg extraction to ephemeral WAV scratch |
| M5-03 | Faster-Whisper CPU Speech Transcriber | Analysis Services | Implemented | `backend/app/services/transcription.py` | CPU-first Faster-Whisper (`int8`), segment timestamps, word tokens, PyAV 14+ compat |
| M5-04 | Dialogue & Speech Turn Segmentation | Analysis Services | Implemented | `backend/app/services/speech_segmentation.py` | Conversational pause thresholding, turn grouping, statement/question/exclamation |
| M5-05 | FFmpeg Visual Scene Cut Detection | Analysis Services | Implemented | `backend/app/services/scene_detector.py` | Cut extraction via FFmpeg scene filter, timestamps, midpoint representative frames |
| M5-06 | Controlled Downscaled Frame Sampling | Analysis Services | Implemented | `backend/app/services/frame_sampler.py` | Keyframe extraction downscaled to 640px max dimension, capped per profile |
| M5-07 | Visual Understanding via Local Ollama | Analysis Services | Implemented | `backend/app/services/visual_understanding.py` | Queries `qwen3-vl:4b-instruct` with conservative language; deterministic heuristic fallback |
| M5-08 | Multimodal Temporal Context Aggregator | Analysis Services | Implemented | `backend/app/services/temporal_aggregator.py` | Unifies scenes, speech turns, transcript segments, and vision at any timestamp |
| M5-09 | Analysis Pipeline Coordinator & REST API | Backend API | Implemented | `backend/app/services/analysis_pipeline.py`, `backend/app/api/v1/analysis.py` | 8-stage coordinator, async background execution, cancellation, REST endpoints |
| M5-10 | Interactive Frontend Analysis Workspace | Features / Analysis | Implemented | `frontend/src/features/analysis/AnalysisWorkspace.tsx` | Synchronized player, scrub bar, searchable transcript, scene cuts, vision tags, context inspector |
| M5-11 | Backend Analysis Test Suite (7 tests) | Testing | Implemented | `backend/tests/test_milestone5_analysis.py` | Audio extraction, scenes, speech turns, frames, fallback, aggregator, API flow (100% pass) |
| M5-12 | Frontend Analysis Vitest Suite (3 tests) | Testing | Implemented | `frontend/src/test/analysis.test.tsx` | Workspace rendering, transcript, speech turns, tab switching, context inspector (100% pass) |

---

## AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M6-01 | Database Migration `0005_highlight_candidates.sql` | DB / Migrations | Implemented | `backend/migrations/0005_highlight_candidates.sql` | Schema for `shorts_candidates`, versioned scoring, gate results, overlap groups |
| M6-02 | Candidate Dataclass Entity | Backend Models | Implemented | `backend/app/models/entities.py` | `ShortsCandidateRecord` dataclass mapping |
| M6-03 | Context-Aware Boundary Snapping & Lead Buffers | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Snapping to scene cuts (±0.6s), sentence boundaries, 0.3s lead-in, 0.5s lead-out |
| M6-04 | 9-Component Explainable Scoring Engine (`2.0.0-m6`) | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Semantic, narrative, conversation, visual, audio, opening, ending, duration, context penalty |
| M6-05 | Three-Tier Quality Gate Enforcement | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Categorizes into `recommended`, `needs_review`, `rejected` with failure reasons |
| M6-06 | Temporal Overlap Clustering & Deduplication | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Groups clips with $\text{IoU} \ge 0.65$ into alternative cuts under `overlap_group_id` |
| M6-07 | Ollama AI Content Explanation & Deterministic Fallback | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Generates hook, why_it_works, strengths, risks with local LLM or heuristic fallback |
| M6-08 | Shorts Candidates REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/highlights.py` | Discover, overview counts, candidate detail, boundary patch, approve, reject, restore, bulk review, render queue |
| M6-09 | Frontend Highlights & Shorts Studio Workspace | Features / Highlights | Implemented | `frontend/src/features/highlights/HighlightsWorkspace.tsx` | Metrics, filter tabs, candidate cards, boundary slider inspector, score breakdown, alternative cuts |
| M6-10 | Backend Automated Pytest Suite (3 tests) | Testing | Implemented | `backend/tests/test_milestone6_highlights.py` | Engine generation, quality gates, full REST lifecycle (100% pass) |
| M6-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/highlights.test.tsx` | Studio rendering, status tabs, boundary fine-tuning, approve/reject, queue toggle (100% pass) |

---

## Upcoming Milestones Roadmap (Not Started)

| ID | Feature / Capability | Module | Status | Planned Milestone |
|---|---|---|---|---|
| MOD-E1 | Dynamic Subject Tracking, Portrait Crop Math Parity & Manual Revisions | E: Reframing | Planned | Milestone 7 |
| MOD-F1 | Multi-Track Timeline Editor, Keyframes, Snap, Undo/Redo & Autosave | F: Timeline | Planned | Milestone 8 |
| MOD-G1 | Conversational AI Video Editor & Schema-Validated EditPlan Executor | G: AI Editor | Planned | Milestone 9 |
| MOD-H1 | Independent Character Extraction Studio & Persistent Character Library | H: Characters | Planned | Milestone 10 |
| MOD-I1 | Multi-Format Rendering, Output Validation, Captions & Export Manager | I: Export | Planned | Milestone 11 |
