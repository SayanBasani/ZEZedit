# ZezEdit 2.0 — Feature Status Tracker

**Last Updated:** 2026-11-11  
**Active Milestone:** Milestone 1 — Architecture Redesign, Technical Blueprint & Safe Project Foundation

Status legend:
- **Implemented:** Code exists, integrated end-to-end, and verified with tests / runtime execution.
- **Partial:** Core scaffolding or partial layer exists; remaining workflow scheduled for later milestones.
- **Planned:** Designed in architecture specs; implementation scheduled in an upcoming milestone.
- **Not Started:** Future backlog item.
- **Blocked:** External dependency or unresolved blocker prevents verification.

---

## Core Foundation (Milestone 1)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| FND-01 | Versioned Architecture & Design Blueprint (11 docs + README) | Docs | Implemented | `docs/architecture/` | Covers all 18 required architectural decisions |
| FND-02 | Configurable Storage Root & Directory Layout | Core / Storage | Implemented | `backend/app/core/storage.py` | Separates media, proxies, thumbnails, analysis, exports, temp, backups, db |
| FND-03 | Path Confinement & Anti-Root Recursive Deletion Guard | Core / Security | Implemented | `backend/app/core/security.py` | Blocks traversal, root deletion, and storage escapes |
| FND-04 | Structured Logging & Centralized Error Handling | Core / API | Implemented | `backend/app/core/logging.py`, `backend/app/core/errors.py` | Standard JSON-friendly logs and uniform error envelopes |
| FND-05 | SQLite WAL Connection & Forward-Only SQL Migration Runner | DB / Migrations | Implemented | `backend/app/db/migrator.py`, `backend/migrations/0001_initial_schema.sql` | Initializes baseline metadata tables cleanly |
| FND-06 | FastAPI App Entry Point & `/api/v1/health` Endpoint | Backend API | Implemented | `backend/app/main.py`, `backend/app/api/v1/health.py` | Probes SQLite, storage root, FFmpeg, FFprobe, and Ollama |
| FND-07 | Minimal Bounded React/Vite/Tailwind Shell & Backend Connectivity Check | Frontend | Implemented | `frontend/src/app/App.tsx`, `frontend/src/services/apiClient.ts` | Stationary sidebar + scrollable main container (`BUG-08A-1/2` fix baked in) |

---

## Product Modules (Scheduled for Milestones 2–10)

| ID | Feature / Capability | Module | Status | Planned Milestone | Architecture Spec |
|---|---|---|---|---|---|
| MOD-A1 | Project Creation, Listing & Recent Projects UI | A: Dashboard | Planned | Milestone 2 | `SYSTEM_ARCHITECTURE.md`, `API_DESIGN.md` |
| MOD-B1 | Streaming Media Import, Metadata (FFprobe), Thumbnails & Proxies | B: Media Library | Planned | Milestone 2 | `MEDIA_PIPELINE.md`, `SECURITY_AND_DATA_SAFETY.md` |
| MOD-B2 | Missing vs Deleted Media State Detection & Relinking | B: Media Library | Planned | Milestone 2 | `DATABASE_DESIGN.md`, `SECURITY_AND_DATA_SAFETY.md` |
| MOD-J1 | Authoritative Single Job Orchestrator, PID Tracking & Startup Recovery | Core / Workers | Planned | Milestone 3 | `JOB_ORCHESTRATION.md` |
| MOD-J2 | Settings, Authoritative Ollama Model Inventory & Async Model Pull | J: Settings | Planned | Milestone 4 | `SYSTEM_ARCHITECTURE.md`, `TECHNOLOGY_DECISIONS.md` |
| MOD-C1 | Scene Cut Detection, Faster-Whisper Transcription & Visual Frame Sampling | C: Video Analysis | Planned | Milestone 5 | `MEDIA_PIPELINE.md` |
| MOD-D1 | Context-Aware Highlight Discovery & Candidate Ranking | D: Highlights | Planned | Milestone 5 | `MASTER_REQUIREMENTS.md` |
| MOD-E1 | Dynamic Subject Tracking, Portrait Crop Math Parity & Manual Revisions | E: Reframing | Planned | Milestone 6 | `MEDIA_PIPELINE.md` |
| MOD-F1 | Multi-Track Timeline Editor, Keyframes, Snap, Undo/Redo & Autosave | F: Timeline | Planned | Milestone 7 | `TIMELINE_MODEL.md` |
| MOD-G1 | Conversational AI Video Editor & Schema-Validated EditPlan Executor | G: AI Editor | Planned | Milestone 8 | `SECURITY_AND_DATA_SAFETY.md` |
| MOD-H1 | Independent Character Extraction Studio & Persistent Character Library | H: Characters | Planned | Milestone 9 | `DATABASE_DESIGN.md` |
| MOD-I1 | Multi-Format Rendering, Output Validation, Captions & Backup/Restore | I: Export | Planned | Milestone 10 | `MEDIA_PIPELINE.md`, `SECURITY_AND_DATA_SAFETY.md` |
