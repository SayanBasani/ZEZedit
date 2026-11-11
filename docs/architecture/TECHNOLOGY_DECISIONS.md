# ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)

This ledger summarizes core architectural decisions, why each option was chosen over alternatives, and known limitations.

---

## ADR-01: Single Local Monolith (FastAPI + React) vs Microservices
- **Decision:** Run a single Python FastAPI backend communicating with a React + TypeScript + Vite SPA.
- **Reason:** ZezEdit targets single-user Windows 11 desktops. A monolith eliminates inter-service serialization overhead, port conflicts, service discovery boilerplate, and fragmented error handling.
- **Alternatives Considered:** Separate microservices (Node API + Python Worker + Electron wrapper) or Redis/Celery. Rejected due to installation complexity and higher RAM usage on 20 GB machines.
- **Limitation:** Does not horizontally scale across multiple servers; bound to a single workstation.

## ADR-02: CPU-First Local Processing & Streaming I/O
- **Decision:** Require all media, tracking, transcription, and LLM paths to run strictly on CPU (`i3-1220P` + 20 GB RAM) using streaming FFmpeg pipes, proxies, and sampled frames. Treat GPU acceleration as optional.
- **Reason:** Hardware lacks dedicated NVIDIA CUDA VRAM; 1–2 GB+ videos would exhaust RAM if decoded completely in memory.
- **Alternatives Considered:** PyTorch CUDA pipelines or mandatory cloud APIs. Rejected per local-first hardware mandates.
- **Limitation:** Long renders and heavy transcription take CPU minutes; UI must remain responsive via async job queues and bounded `-threads`.

## ADR-03: SQLite WAL + Forward-Only SQL Migrations
- **Decision:** Use SQLite 3 in `WAL` mode paired with numbered `.sql` files in `backend/migrations/` tracked via `schema_migrations`.
- **Reason:** Prevents the historical >55-table monolithic `db.py` drift and provides deterministic versioned upgrades with automatic pre-migration snapshots.
- **Alternatives Considered:** SQLAlchemy + Alembic ORM auto-generation. Kept direct `sqlite3` + SQL files to minimize dependency weight and avoid ORM session locking during multi-thread job tracking.
- **Limitation:** Developers write explicit parameterized SQL rather than ORM query builder chains.

## ADR-04: Centralized Error Handling & Structured Logging
- **Decision:** Route all exceptions through `backend/app/core/errors.py` (`AppError` subclasses + FastAPI exception handlers) and emit structured rotating logs via `backend/app/core/logging.py`.
- **Reason:** Guarantees every API failure yields a consistent JSON envelope (`error.code`, `error.message`, `error.details`, `error.request_id`) and attaches diagnostic context for per-job and application logs.
- **Alternatives Considered:** Ad-hoc `HTTPException` strings per endpoint (caused fragmented UI errors previously).
- **Limitation:** Requires discipline to raise typed `AppError` classes in new service modules.

## ADR-05: Dynamic Authoritative AI Provider Abstraction
- **Decision:** Discover local Ollama models dynamically from `http://127.0.0.1:11434/api/tags` with generous timeouts (8s), non-blocking pulls (`202 Accepted`), and clean interface traits (`TextLLMProvider`, `VisionLanguageProvider`, `SpeechToTextProvider`).
- **Reason:** Fixes historical bugs (`BUG-08A-7`, `BUG-08A-8`, Milestone 13M.8 stale hardcoded `all-minilm` entries) and isolates untrusted LLM JSON planning behind Pydantic validators.
- **Alternatives Considered:** Direct `httpx` calls scattered inside chat/highlight services.
- **Limitation:** Small 4B local models (`qwen3-vl:4b-instruct`) have limited reasoning depth; system must clearly caveat scores and validate schemas strictly.

## ADR-06: Decoupled Evidence-Based Character Extraction (No 3D Studio)
- **Decision:** Retain independent Character Extraction Studio (face + saliency sampling, conservative clustering, human confirmation) while permanently dropping historical 3D character mesh/rigging/GLB reconstruction tables.
- **Reason:** 3D mesh synthesis proved out-of-scope and unstable on CPU hardware in earlier milestones (removed in M13M.7/M13M.10) while fragmenting core video editing focus.
- **Alternatives Considered:** Rebuilding 3D avatar generation pipelines. Rejected for scope clarity and CPU feasibility.
- **Limitation:** Character Library manages 2D visual reference profiles and timeline appearances rather than 3D avatars.

## ADR-07: Testing Strategy (Multi-Layer Gate)
- **Decision:** Enforce three test tiers per milestone:
  1. **Backend Unit & Migration Tests (`pytest`):** Schema migrations, security path containment, deterministic math, API contracts using `FastAPI TestClient` and temp storage roots.
  2. **Frontend Build & Component Tests (`tsc && vite build` + `vitest`):** Static type safety, layout invariants, API client parsing.
  3. **Live Runtime & Real-Media Verification:** Running local FastAPI + Vite processes simultaneously, verifying `/api/v1/health`, and in media milestones inspecting actual FFprobe output and extracted JPEG contact sheets from real 1080p MP4s.
- **Reason:** Passing unit tests alone never caught scroll traps or shrunken portrait renders in historical builds.

## ADR-08: Shared Contract Directory (`shared/contracts/`)
- **Decision:** Keep canonical JSON schema specifications / documentation notes for critical cross-boundary objects (`timeline_document.schema.json`, `error_envelope.schema.json`) inside `shared/contracts/` alongside matching Pydantic & TypeScript definitions.
- **Reason:** Keeps frontend TypeScript types and backend Pydantic schemas aligned cleanly across milestones.
- **Limitation:** Kept lightweight (manual parity check in early milestones rather than complex codegen build scripts).
