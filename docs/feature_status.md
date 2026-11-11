# ZezEdit 2.0 — Feature Status Tracker

**Last Updated:** 2026-11-12  
**Active Milestone:** Milestone 9 Completed — AI Video Editor, Multi-Track Timeline & Non-Destructive Editing

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

## Smart Reframing, Subject Tracking & Portrait Composition (Milestone 7)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M7-01 | Database Migration `0006_smart_reframing.sql` | DB / Migrations | Implemented | `backend/migrations/0006_smart_reframing.sql` | Schema for `reframing_plans` and `reframing_revisions` with range indexing |
| M7-02 | Subject Detection & Tracking Service | Reframing Engine | Implemented | `backend/app/services/subject_tracker.py` | CPU-first OpenCV Haar Cascades (frontal/profile face, upper body), saliency fallback, IoU/centroid association, 1.2s gap bridging |
| M7-03 | Framing Engine & Geometry Resolution | Reframing Engine | Implemented | `backend/app/services/framing_engine.py` | Aspect ratios (9:16, 1:1, 16:9), even integer dimension clamping, single/two-person/group strategies, headroom factor |
| M7-04 | Velocity-Constrained Dynamic Crop Smoothing | Reframing Engine | Implemented | `backend/app/services/framing_engine.py` | Window-weighted smoothing with `max_pan_velocity` limits, strict scene-cut isolation (instant step, zero blurring across cuts) |
| M7-05 | Preview / Renderer Mathematical Parity | Reframing Engine | Implemented | `backend/app/services/framing_engine.py`, `backend/app/services/reframing_renderer.py` | Consumes identical piecewise linear interpolation formula `interpolate_crop_at(t)` and filter expressions |
| M7-06 | Dynamic FFmpeg Filtergraph Renderer | Reframing Engine | Implemented | `backend/app/services/reframing_renderer.py` | Piecewise-linear time-varying crop filter (`crop=w:h:x:y`), scale to target (1080x1920), libx264, yuv420p, audio sync |
| M7-07 | Non-Destructive Revision History Ledger | Reframing Services | Implemented | `backend/app/services/reframing_service.py` | Versioned plan revisions, manual override retention, restore revision, render dispatch |
| M7-08 | Smart Reframing REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/reframing.py` | Analyze plan, preview crop, manual override patch, revisions list, restore revision, render revision, video stream |
| M7-09 | Reframing Review Workspace Frontend | Features / Reframing | Implemented | `frontend/src/features/reframing/ReframingWorkspace.tsx` | Dual viewports (source landscape overlay & true 9:16 portrait viewport), manual crop sliders, zoom/headroom, revisions modal, render trigger |
| M7-10 | Backend Automated Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone7_reframing.py` | Geometry, strategies, smoothing, expression parity, real FFmpeg rendering, API lifecycle & revisions (100% pass) |
| M7-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/reframing.test.tsx` | Dual viewports, manual adjustment, revision drawer, restore revision, render action (100% pass) |

---

## Rendering Engine, Export Pipeline & Automatic Shorts Generation (Milestone 8)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M8-01 | Database Migration `0007_export_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0007_export_pipeline.sql` | Schema for `exports` table with preset, configuration JSON, validation details, and indexes |
| M8-02 | Standard Export Presets Catalog | Export Services | Implemented | `backend/app/models/export.py` | YouTube Shorts / Reels (9:16), Landscape (16:9), Square Social (1:1) with CRF and codec defaults |
| M8-03 | Configurable Caption & Subtitle Engine | Export Services | Implemented | `backend/app/services/caption_engine.py` | ASS subtitle generator supporting word-highlight, phrase bursts, sentences, styling, and safe margins |
| M8-04 | Audio Processing & Fallback Synthesis | Export Services | Implemented | `backend/app/services/audio_pipeline.py` | Volume controls, fade in/out, EBU R128 loudness normalization, resample 48kHz, silent audio fallback |
| M8-05 | 15-Stage Modular Rendering Pipeline | Export Services | Implemented | `backend/app/services/export_service.py` | End-to-end coordinator integrating smart reframing keyframes, scaling, ASS burn-in, audio, and publishing |
| M8-06 | Subprocess Tracking & Real Process Cancellation | Export Services | Implemented | `backend/app/services/export_service.py` | Popen process registration, real-time progress parsing (`out_time_us`), and graceful process termination |
| M8-07 | Post-Render Output Validation Gate | Export Services | Implemented | `backend/app/services/output_validator.py` | Rigorous FFprobe stream inspection (dimensions, duration tolerance, codecs) + test frame decoding |
| M8-08 | Export REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/exports.py` | Presets, submit render, fast preview, list exports, export details, cancel, delete, HTTP 206 video stream |
| M8-09 | Frontend Shorts Export Studio Workspace | Features / Exports | Implemented | `frontend/src/features/exports/ExportStudio.tsx` | Preset selector, caption customization, audio sliders, live progress monitor, video player, export history |
| M8-10 | Backend Automated Pytest Suite (7 tests) | Testing | Implemented | `backend/tests/test_milestone8_export.py` | Presets, captions, audio filters, validation gate, full render, API lifecycle, cancellation (100% pass) |
| M8-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/exports.test.tsx` | Studio rendering, tab switching, caption styling, render job monitor, export history (100% pass) |

---

## AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M9-01 | Database Migration `0008_timeline_editor.sql` | DB / Migrations | Implemented | `backend/migrations/0008_timeline_editor.sql` | Tables for `timelines`, `timeline_tracks`, `timeline_clips`, `timeline_commands`, `ai_conversations`, `ai_editing_plans`, `ai_messages` |
| M9-02 | Authoritative Timeline & Multi-Track Service | Timeline Core | Implemented | `backend/app/services/timeline_service.py` | Timeline CRUD, default tracks initialization (V2, V1, A1, A2), track mute/lock/visibility, duration recalculation |
| M9-03 | Validated Reversible Editing Commands Layer | Timeline Core | Implemented | `backend/app/services/timeline_command_service.py` | `InsertClip`, `MoveClip`, `TrimClip`, `SplitClip`, `DeleteClip`, `DuplicateClip`, `UpdateClipProps`, `AddTextOverlay` |
| M9-04 | Persistent Undo & Redo History Engine | Timeline Core | Implemented | `backend/app/services/timeline_command_service.py` | Transactional forward/inverse payloads surviving app restarts and crashes |
| M9-05 | AI Video Editor Assistant Service | AI Assistant | Implemented | `backend/app/services/ai_editor_service.py` | Context aggregation (media, transcripts, highlights, timeline state), query answering, structured plan generation with warnings |
| M9-06 | User Approval Gate & Safe Execution Engine | AI Assistant | Implemented | `backend/app/services/ai_editor_service.py` | Plan review card, user approval execution mapping safely into command layer; no silent or destructive execution |
| M9-07 | Multi-Track Timeline FFmpeg Rendering Pipeline | Timeline Core | Implemented | `backend/app/services/timeline_renderer.py` | Video layering, libass text overlays, multi-track audio mixing (`amix`), loudness normalization, Milestone 8 `OutputValidator` gate |
| M9-08 | Timeline & AI REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/timeline.py` | 23 REST endpoints covering timeline CRUD, tracks, clips, undo/redo, AI conversation, plans, and render |
| M9-09 | Frontend Timeline & AI Editor Workspace | Features / Timeline | Implemented | `frontend/src/features/timeline/TimelineEditor.tsx` | Toolbar, preview monitor, Inspector properties panel, AI assistant chat with plan review card, multi-track lanes and playhead |
| M9-10 | Backend Automated Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone9_timeline.py` | Timeline CRUD, clip operations/validation, persistent undo/redo, AI assistant, multi-track render, API lifecycle (100% pass) |
| M9-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/timeline.test.tsx` | Sequence rendering, clip inspection, undo/redo, AI plan approval, render trigger (100% pass) |

---

## Upcoming Milestones Roadmap (Not Started)

| ID | Feature / Capability | Module | Status | Planned Milestone |
|---|---|---|---|---|
| MOD-G2 | Conversational AI Prompt-to-Cut Advanced Fine-Tuning | G: AI Editor | Planned | Milestone 10 |
| MOD-H1 | Independent Character Extraction Studio & Persistent Character Library | H: Characters | Planned | Milestone 11 |
| MOD-I1 | Final Packaging, Multi-Format Archiving & Project Backup | I: Export | Planned | Milestone 12 |
