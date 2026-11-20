# ZezEdit 2.0 — Feature Status Tracker

**Last Updated:** 2026-11-20  
**Active Milestone:** Priority 2 (P2.3 Verified & Accepted) — Smart Reframing, Subject Tracking & Portrait Composition (178/178 Frontend Tests across 35 files, 505/505 Backend Tests, 0 TS Errors, Clean Production Build, 11/11 Live Demonstrations Passed, 0 FK Violations, SQLite integrity ok)

Status legend:
- **Implemented:** Code exists, integrated end-to-end, and verified with tests / runtime execution.
- **Tested and Passed:** Automated or manual test verification executed with recorded exit code 0.
- **Tested and Failed:** Automated or manual test verification executed with failures recorded.
- **Partial:** Core scaffolding or partial layer exists; remaining workflow scheduled for later milestones.
- **Planned:** Designed in architecture specs; implementation scheduled in an upcoming milestone.
- **Not Started:** Future backlog item.
- **Blocked:** External dependency or unresolved blocker prevents verification.

---

## Priority 0 — Windows Release Hardening & Project Audit (P0)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| P0.1-01 | Complete Project Audit & Failure Inventory | Documentation & Audit | Tested and Passed | `docs/reports/priority_0/P0_1_PROJECT_AUDIT.md` | Rigorous evidence-based audit of Git state, launcher safety, test suites, database integrity, and media storage |
| P0.2-01 | Full Backend Pytest Suite Baseline (274 Tests) | Test Suite | Tested and Passed | `backend/tests/` | 274/274 tests passed in 584.05s (exit code 0); zero tests skipped, deleted, or weakened |
| P0.3-01 | Full Frontend Vitest Suite & Real Browser Demos | Frontend / SPA | Tested and Passed | `frontend/src/` | 120/120 tests passed; 10 browser demonstrations verified with 12 screenshots in `docs/reports/priority_0/p0_3_evidence/` |
| P0.3-R1 | Browser Evidence Reconciliation & Video Route Verification | Documentation & Verification | Tested and Passed | `docs/reports/priority_0/P0_3_R1_BROWSER_EVIDENCE_RECONCILIATION.md` | Reconciled PowerShell ephemeral subshell termination vs persistent daemon; re-verified HTTP 206 video streaming & download routes |
| P0.4-01 | TypeScript Correctness & Production Build Stability | Frontend Build / Typing | Tested and Passed | `frontend/dist/` | 120/120 tests passed, 0 TS compiler errors, production bundle built in 2.22s, 5/5 real browser demos verified |
| P0.5-01 | SQLite Integrity, FK Repair & Orphan Reconciliation | Storage / Database | Tested and Passed | `backend/app/services/backup_service.py` | 16 FK violations repaired to NULL (ON DELETE SET NULL); 5 missing exports marked failed/invalid with 0 rows deleted; verified via `POST /system/db-reconcile` |
| P0.5-02 | Path Traversal Defense on Video Endpoints | API / Security | Tested and Passed | `backend/app/api/v1/exports.py` | Strict `is_relative_to(storage_root)` check on streaming, downloading, and deletion; out-of-root access returns HTTP 403 Forbidden |
| P0.5-03 | Database & API Consistency Regression Suite | Test Suite | Tested and Passed | `backend/tests/test_p0_5_database_and_api_consistency.py` | 12/12 tests passed covering FK enforcement, partial content, 404 missing, 403 traversal, cascade safety, idempotency, rollback on interrupt, concurrent requests, active job writes |
| P0.5-R1 | Full Backend Suite Verification & Reconciliation Transactionality | Core & Pipeline | Tested and Passed | `docs/reports/priority_0/P0_5_R1_REGRESSION_AND_SAFETY_CLOSURE.md` | Authoritative 281/281 pytest passed in 362.83s (exit code 0); atomic BEGIN IMMEDIATE transaction; 4/4 live demos verified |
| P0.6-01 | Job State Transitions & Monotonic Progress Invariants | Job Orchestration | Tested and Passed | `backend/app/services/jobs.py` | Strict `VALID_TRANSITIONS` enforcement; monotonic non-decreasing progress; 99% execution cap; 100% on complete |
| P0.6-02 | Deterministic Cancellation & Subprocess Tree Termination | Process Management | Tested and Passed | `backend/app/services/export_service.py` | Clean child process killing (`_terminate_pid_tree`); stdout cancellation detection; scratch file unlinking |
| P0.6-03 | Watchdog Stall Detection & Restart Recovery | Fault Tolerance | Tested and Passed | `backend/app/services/jobs.py` | Stalled worker detection without fake progress tickers; `recover_interrupted_jobs` synchronizes linked tables |
| P0.6-04 | Job Queue & Cancellation Automated Regression Suite | Test Suite | Tested and Passed | `backend/tests/test_p0_6_job_queue_and_cancellation.py` | 20/20 tests passed covering state machine, cancellation, subprocess kill, stalls, retries, restart recovery |
| P0.6-05 | P0.6 Live Demonstrations & Output Review | Verification | Tested and Passed | `backend/scripts/run_p0_6_demos.py` | 8/8 live demonstrations passing with real output artifacts, process PID termination, and idempotency checks |
| P0.7-01 | Script Path Resolution & CWD Independence | Launcher Scripts | Tested and Passed | `Start-ZEZEdit.ps1`, `Stop-ZEZEdit.ps1` | Dynamically resolves workspace root from `$PSScriptRoot` or `$MyInvocation`; supports execution from any external directory |
| P0.7-02 | Structured Process Ownership Tracking | Backend / Lifecycle | Tested and Passed | `backend/app/main.py`, `storage/temp/zezedit_process.json` | Records JSON metadata with `pid`, `port`, `host`, `project_root`, `role`, `command_line`, `start_time`; cleans on exit |
| P0.7-03 | Port Conflict Defense & Unrelated Process Protection | Network / Safety | Tested and Passed | `Start-ZEZEdit.ps1` | Non-ZEZEdit listeners on port 8000/custom port are detected and preserved; yields actionable error and exits 1 |
| P0.7-04 | Stale PID Cleanup & PID Reuse Protection | Process Management | Tested and Passed | `Stop-ZEZEdit.ps1` | Verifies process command line via CIM before terminating; safely preserves unrelated processes reusing recorded PIDs |
| P0.7-05 | Proxy-Immune Readiness Health Polling | Launcher Scripts | Tested and Passed | `Start-ZEZEdit.ps1` | `Get-ZezEditHealth` uses basic parsing, localhost proxy bypass, and 5s timeout to eliminate WPAD latency and Ollama timeout false failures |
| P0.7-06 | Detached Background Process Spawning | Process Management | Tested and Passed | `Start-ZEZEdit.ps1` | Spawns uvicorn server via WMI `Win32_Process.Create` detached from parent job object limits and console handle locks |
| P0.7-07 | P0.7 Automated Regression Test Suite | Test Suite | Tested and Passed | `backend/tests/test_p0_7_windows_launcher_reliability.py` | 18/18 tests passed covering path resolution, duplicate guard, port conflicts, PID reuse, graceful stop, child cleanup |
| P0.7-08 | P0.7 Live Windows Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p0_7_demos.py` | 8/8 live demonstrations passing covering normal start, duplicate guard, external CWD, port conflict, stop, repeat stop, restart data access, PID reuse protection |
| P0.8-01 | Single-Port Production Serving & Route Evaluation Hierarchy | Backend / SPA | Tested and Passed | `backend/app/main.py` | FastAPI serves built Vite bundle on port 8000; REST API, `/health`, and `/docs` take absolute precedence over SPA catch-all |
| P0.8-02 | Missing Static Asset 404 Protection & Syntax Error Prevention | Backend / SPA | Tested and Passed | `backend/app/main.py` | Requests with static extensions or targeting `/assets/` return HTTP 404 JSON, preventing browser HTML syntax errors |
| P0.8-03 | SPA Client-Side Deep Link Routing & History Navigation | Frontend / SPA | Tested and Passed | `backend/app/main.py` | Valid client routes (`/videos`, `/videos/:id`, `/studio/:id`, `/settings`, `/processes`, etc.) return `index.html` with HTTP 200 |
| P0.8-04 | Path Traversal & Sensitive File Defense | API / Security | Tested and Passed | `backend/app/main.py` | Traversal tokens return HTTP 400 Bad Request; sensitive file probes (`.env`, `.db`, `.py`, `.log`, `.bak`, `storage/`) return HTTP 403 Forbidden |
| P0.8-05 | P0.8 Automated Regression Suite & Live Demonstrations | Test Suite & Verification | Tested and Passed | `backend/tests/test_p0_8_production_frontend_serving.py` | 15/15 unit tests and 6/6 live demonstration groups passed; zero Vite port 5173 runtime dependency |
| P0.8-R1 | Production Serving Evidence Reconciliation & Browser Acceptance | Verification & Audit | Tested and Passed | `docs/reports/priority_0/P0_8_R1_EVIDENCE_RECONCILIATION.md` | Diagnosed PowerShell parser error on DB audit; verified 0 FK violations, 93 jobs, 44 exports, 5 media, 34 MP4s; live Chromium browser verified with 4 screenshots |
| P0.9-01 | Baseline Media & Export SHA-256 Hash Immutability | Storage / Verification | Tested and Passed | `docs/reports/priority_0/p0_9_evidence/baseline_manifest.json` | 5 source media files and 34 export MP4s verified byte-for-byte and hash-identical across restarts |
| P0.9-02 | SQLite WAL Checkpoint, Crash Recovery & Integrity | Database / Persistence | Tested and Passed | `storage/db/zezedit.db` | Verified clean recovery from simulated SIGKILL, uncommitted WAL transactions, and PASSIVE/FULL WAL checkpoints; 0 FK violations |
| P0.9-03 | Job & Worker Restart Recovery State Invariants | Job Orchestration | Tested and Passed | `backend/app/services/jobs.py` | Stale running/cancelling jobs reconciled to interrupted on boot; worker processes claim queued jobs cleanly without duplicate execution |
| P0.9-04 | Partial Upload & Render Interruption Atomicity | Media / Pipeline | Tested and Passed | `backend/app/services/export_service.py` | Aborted uploads leave 0 zombie media records; cancelled/killed FFmpeg render scratch files safely purged; completed exports untouched |
| P0.9-05 | P0.9 Automated Regression Suite & 21 Demonstrations | Test Suite & Verification | Tested and Passed | `backend/tests/test_p0_9_restart_and_persistence.py` | 20/20 automated tests passed (1.98s); 21/21 live restart/recovery demonstrations passed (exit code 0) |
| P0.9-R1-01 | Genuine Isolated OS Process-Crash & WAL Recovery | Fault Tolerance | Tested and Passed | `backend/scripts/run_p0_9_r1_reconciliation.py` | Child Python processes (PIDs 54244, 19096) terminated via OS kill; SQLite uncommitted automatic rollback and committed WAL recovery verified |
| P0.9-R1-02 | Backup and Restore into Isolated Database | Storage / Backup | Tested and Passed | `storage/backups/` | Backup `backup_r1_audit_20261116T061626Z.db` created, SHA-256 hashed, restored into isolated DB, 100% table count match, production DB untouched |
| P0.9-R1-03 | Five Consecutive Real Windows Launcher Cycles | Launcher Scripts | Tested and Passed | `Start-ZEZEdit.ps1`, `Stop-ZEZEdit.ps1` | 5 real cycles executed (PIDs 25140, 48380, 45900, 46376, 46900); /health, SPA root, media, jobs, exports verified; external CWD launch verified |
| P0.9-R1-04 | Real Worker Interruption, Recovery & Output Validation | Job Orchestration | Tested and Passed | `backend/app/services/jobs.py` | Real child worker (PID 31968) killed; recovered to interrupted; progress preserved at 45%; retried to completion with validated artifact |
| P0.9-R1-05 | Interruption Safety & Hash Invariant Audit | Storage / Media | Tested and Passed | `docs/reports/priority_0/p0_9_evidence/reconciliation/` | 5 source media and 34 exports 100% hash invariant; partial upload purged; FFmpeg killed mid-render; overwrite protection verified |
| P0.1-02 | Windows Single-Port Production Serving | Backend / SPA | Implemented | `backend/app/main.py` | FastAPI serves built Vite bundle on port 8000; SPA routing and asset isolation verified |
| P0.1-03 | Windows One-Click Launcher & Stop Routines | Launcher Scripts | Implemented | `Start-ZEZEdit.*`, `Stop-ZEZEdit.*` | 6-stage boot and selective PID/port process validation scripts authored; uncommitted |
| P0.1-04 | Job State Machine Direct Cancellation | Job Orchestration | Tested and Passed | `backend/app/services/jobs.py` | Added cancelled transition for running jobs; verified by `test_cancellation_and_job_sync` |
| P0.1-05 | Release Git Commit & Synchronization | Repository Lifecycle | Blocked | Git root | Blocked by uncommitted working tree (`P0.1-GIT-001`) |
| P0.1-06 | Orphan Export Database Reconciliation | Storage / Database | Tested and Passed | `storage/db/zezedit.db` | Reconciled under P0.5: 5 orphan exports marked failed/invalid; 0 FK violations remain; integrity ok |

---

## Priority 1 — Video Ingestion & Processing Core (P1)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| P1.1-01 | Single Video Upload & Metadata Ingestion | Media Ingestion | Tested and Passed | `backend/app/api/v1/media.py`, `backend/app/services/media_pipeline.py` | Direct streaming upload with FFprobe metadata extraction, thumbnail generation, and database registration |
| P1.1-02 | Multiple Video Batch Upload Operation | Media Ingestion | Tested and Passed | `POST /api/v1/media/batch-upload` | Upload multiple videos in a single operation with per-file status reporting and non-blocking iteration |
| P1.1-03 | Partial Batch Failure Resilience | Error Handling | Tested and Passed | `backend/app/api/v1/media.py` | Valid videos succeed and persist while invalid files report structured error details without dropping the batch |
| P1.1-04 | Filename Safety & Path Traversal Rejection | Security & Storage | Tested and Passed | `backend/app/services/media_pipeline.py` | Directory traversal sequences rejected (`400 PATH_TRAVERSAL_DETECTED`); spaces, brackets, Unicode preserved |
| P1.1-05 | Non-Destructive File Collision Handling | Storage Management | Tested and Passed | `backend/app/services/media_pipeline.py` | Unique 8-char hex prefixes guarantee separate physical files and distinct DB records on duplicate uploads |
| P1.1-06 | Video Edit Dashboard Navigation | Frontend Routing | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Clickable cards and explicit button route to `/videos/:id` displaying technical specifications and action tabs |
| P1.1-07 | P1.1 Automated Regression Suite | Test Suite | Tested and Passed | `backend/tests/test_p1_1_upload.py` | 7/7 tests passed covering single/batch upload, partial failures, empty file, unicode, traversal, collisions |
| P1.1-08 | P1.1 Live Demonstrations & Evidence | Verification | Tested and Passed | `backend/scripts/run_p1_1_demos.py` | 5/5 live demonstrations passed: Demo A (single), Demo B (3-video batch), Demo C (mixed), Demo D (safety), Demo E (collision) |
| P1.1-R1-01 | Real Browser Single & Batch Upload Acceptance | Frontend / Browser UI | Tested and Passed | `backend/scripts/run_p1_1_r1_browser_demos.py` | 5/5 CDP real-browser demonstrations passed against live production server (`http://127.0.0.1:8000`) with 15 screenshots and structured JSON evidence |
| P1.1-R1-02 | Upload Buffering Mechanics & P1.3 Scope Boundary | Architecture / Documentation | Tested and Passed | `docs/reports/priority_1/P1_1_R1_BROWSER_UPLOAD_ACCEPTANCE.md` | Reconciled P1.1 standard multipart upload with Starlette spooling and 1 MB streaming copy vs P1.3 direct socket streaming (>1GB) without tempfile spooling |
| P1.2-01 | Accurate Byte-Based Transport Progress | API & Transport | Tested and Passed | `frontend/src/services/apiClient.ts` | Implemented `XMLHttpRequest.upload.onprogress` with strictly monotonic bytes, genuine calculation, and 100% cap |
| P1.2-02 | Processing State Separation | Frontend UI & State | Tested and Passed | `frontend/src/features/videos/UploadProgressPanel.tsx` | Visually separates wire transmission (0-100%) from server-side FFprobe / DB commit (`"Processing on server..."`) |
| P1.2-03 | User Transfer Cancellation & Abort | Transport & Error Handling | Tested and Passed | `frontend/src/services/apiClient.ts` | `AbortController.abort()` and `xhr.abort()` trigger immediate cancellation with 0 DB orphan records and 0 orphan files |
| P1.2-04 | Unslop Upload Progress Panel | Design System | Tested and Passed | `frontend/src/features/videos/UploadProgressPanel.tsx` | Quiet graphite canvas, subtle emerald/amber/red status pills, 4px grid rhythm, human-readable formatBytes |
| P1.2-05 | Controlled Backend Test Delay | Backend API | Tested and Passed | `backend/app/api/v1/media.py` | Added optional `test_delay_seconds` parameter defaulting to 0.0 for deterministic test validation |
| P1.2-06 | P1.2 Automated Unit & Integration Tests | Test Suite | Tested and Passed | `frontend/src/test/uploadProgress.test.tsx`, `backend/tests/test_p1_2_upload_progress.py` | 13/13 Vitest unit tests passed and 3/3 Pytest backend tests passed |
| P1.2-07 | P1.2 Real Browser Live Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_2_browser_demos.py` | 6/6 CDP real-browser demonstrations passed against Windows production server with 13 screenshots and JSON evidence |
| P1.3-01 | Incremental Chunked Streaming & On-the-Fly SHA-256 | Media Ingestion | Tested and Passed | `backend/app/services/media_pipeline.py` | 1 MB bounded chunk writes with concurrent `hasher.update(chunk)` and per-50MB disk capacity checks |
| P1.3-02 | Tier 1 Pre-Flight Upload Interception | API & Middleware | Tested and Passed | `backend/app/main.py` | Intercepts Content-Length before body read; returns 413 (>2.5 GB) or 507 (<500 MB disk headroom) |
| P1.3-03 | Strictly Bounded Memory Ingestion | System Performance | Tested and Passed | `backend/scripts/run_p1_3_demos.py` | Verified +1.25 MB RSS delta (0.10% ratio) during 1.21 GB upload (`Visionquest S01E08.mkv`) |
| P1.3-04 | Client Disconnect & Atomic Abort Cleanup | Error Handling & Safety | Tested and Passed | `backend/app/services/media_pipeline.py` | Incomplete transfers immediately close file handle and unlink destination; 0 orphan records in SQLite |
| P1.3-05 | Heavy Upload Concurrency Throttling | Resource Management | Tested and Passed | `backend/app/services/media_pipeline.py` | Process semaphore limits concurrent heavy transfers (default 2), rejecting excess with HTTP 429 |
| P1.3-06 | Startup Orphaned Upload Pruning | System Lifecycle | Tested and Passed | `backend/app/main.py` | Startup lifespan automatically sweeps stale partial uploads from `storage/temp/uploads/` |
| P1.3-07 | P1.3 Automated Suite & Live Process Demos | Test Suite & Verification | Tested and Passed | `backend/tests/test_p1_3_large_upload_streaming.py`, `backend/scripts/run_p1_3_demos.py` | 7/7 unit tests passed; 8/8 live demonstrations passed with 1 honest qualification (Demo D BLOCKED for missing ~2GB asset) |
| P1.3-R1-01 | Real 1.21 GB Browser Upload Transport Verification | Frontend / Browser UI | Tested and Passed | `backend/scripts/run_p1_3_r1_reconciliation.py` | Uploaded `Visionquest S01E08.mkv` (1.21 GB) via Chrome CDP browser UI in 9.61s (128.8 MB/s); SHA-256 100% match; HTTP 206 range verified; RSS delta +1.10 MB |
| P1.3-R1-02 | Large Video Browser UI Cancellation at Scale (~247 MB) | Frontend / Error Handling | Tested and Passed | `backend/scripts/run_p1_3_r1_reconciliation.py` | 247 MB file cancelled mid-stream after 15.7 MB transmitted; UI confirmed "Upload cancelled"; partial file unlinked; 0 DB records; subsequent upload succeeded |
| P1.3-R1-03 | Large Video TCP Client Disconnect at Scale (~247 MB) | Network & Storage Safety | Tested and Passed | `backend/scripts/run_p1_3_r1_reconciliation.py` | 247 MB file upload severed after 50 MB transmitted; server detected disconnect, unlinked partial file, created 0 DB records; subsequent upload succeeded |
| P1.3-R1-04 | Pre-Flight & In-Flight Insufficient Storage Guards (507) | API & Middleware | Tested and Passed | `backend/scripts/run_p1_3_r1_reconciliation.py` | Pre-flight 507 returns structured JSON before body read; in-flight guard halts stream and unlinks partial destination; server remains healthy |
| P1.3-R1-05 | Malformed Content-Length & Chunked Security Hardening | Security & Validation | Tested and Passed | `backend/app/main.py`, `backend/tests/test_p1_3_large_upload_streaming.py` | Negative and non-integer Content-Length return HTTP 400; chunked uploads strictly capped by in-flight byte counter |
| P1.4-01 | Upload State Machine & Attempt Tracking | Frontend State & Types | Tested and Passed | `frontend/src/types/projects.ts`, `frontend/src/services/apiClient.ts` | Formalized states (`queued`, `uploading`, `processing`, `completed`, `failed`, `cancelled`, `retrying`) tracking unique `attemptId` and `attemptCount` |
| P1.4-02 | Stale Callback Event Guarding | API & Transport | Tested and Passed | `frontend/src/services/apiClient.ts` | All XHR progress, load, error, abort, and timeout callbacks check captured `attemptId`; outdated events discarded |
| P1.4-03 | Deterministic Error Classification | Frontend Logic | Tested and Passed | `frontend/src/services/apiClient.ts`, `frontend/src/features/videos/UploadProgressPanel.tsx` | Classifies retryable errors (network, timeout, 408, 429, 500, cancel, DB fail) vs non-retryable terminal errors (400, 413, 415, corrupt, empty) |
| P1.4-04 | In-Memory Full-Restart Retry | Frontend Workflow | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx`, `frontend/src/features/media/MediaLibraryView.tsx` | Retries restart honestly from byte 0 using retained `File` instance; displays clear explanation if DOM `File` reference lost on page reload |
| P1.4-05 | Item-Level Selective Batch Retry | Batch Upload | Tested and Passed | `frontend/src/features/videos/UploadProgressPanel.tsx` | Failed or cancelled items in multi-file batch uploads can be independently retried without restarting succeeded items |
| P1.4-06 | Rapid Duplicate Submission Guard | UI Concurrency | Tested and Passed | `frontend/src/features/videos/UploadProgressPanel.tsx` | Retry buttons disabled and actions guarded while upload is in-flight to prevent duplicate uploads and duplicate DB rows |
| P1.4-07 | Atomic Part Writes & Exception Cleanup | Storage & Safety | Tested and Passed | `backend/app/services/media_pipeline.py` | Streams to `.uploading` part file before atomic rename; closes Windows file handles before unlinking on error with 0 DB orphan records |
| P1.4-08 | Automated Startup Partial Upload Sweep | System Lifecycle | Tested and Passed | `backend/app/main.py` | Lifespan startup handler automatically purges stale `.uploading` and `.part` files abandoned from prior interrupted runs |
| P1.4-09 | P1.4 Automated Test Suite | Test Suite | Tested and Passed | `backend/tests/test_p1_4_upload_retry_and_recovery.py`, `frontend/src/test/uploadRetry.test.tsx` | 6 Pytest unit tests and 8 Vitest unit tests passed (384 backend / 143 frontend total suites) |
| P1.4-10 | P1.4 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_4_demos.py` | 10/10 live demonstrations passed with 7 PNG screenshots and structured JSON evidence in `docs/reports/priority_1/p1_4_evidence/` |
| P1.5-01 | Upload Integrity Contract & Schema Migration | DB / Migrations | Tested and Passed | `backend/migrations/0017_upload_integrity_contract.sql` | Migration 0017 adds sha256, integrity_status, upload_attempt_id, integrity_details_json, last_integrity_check with indexes |
| P1.5-02 | Streaming Single-Pass Incremental SHA-256 | Media Ingestion | Tested and Passed | `backend/app/services/media_pipeline.py` | Computes cryptographic SHA-256 incrementally on-the-fly during upload chunks without second disk passes |
| P1.5-03 | Byte-Count & File-Size Verification | Security & Validation | Tested and Passed | `backend/app/services/media_pipeline.py` | Rejects byte count discrepancies between Content-Length / X-Expected-File-Size and received bytes with 400 BYTE_COUNT_MISMATCH |
| P1.5-04 | Pre-Publication Media Validation | Media Validation | Tested and Passed | `backend/app/services/media_pipeline.py` | Probes staged .uploading part file via FFprobe; rejects corrupt, truncated, text, and audio masquerading as video (400 NO_VIDEO_STREAM) |
| P1.5-05 | Multi-Stream Container Support | Media Formats | Tested and Passed | `backend/app/services/media_pipeline.py`, `backend/app/services/media_probe.py` | Full support for MKVs with multiple audio and subtitle streams; accurately registers stream counts and dimensions |
| P1.5-06 | Two-Phase Atomic Publication & Failure Rollback | Storage Safety | Tested and Passed | `backend/app/services/media_pipeline.py` | Performs os.replace() strictly after probe; automatically rolls back and unlinks files on publication or DB registration failures |
| P1.5-07 | P1.5 Automated Regression Suite | Test Suite | Tested and Passed | `backend/tests/test_p1_5_upload_integrity_and_validation.py` | 9/9 Pytest unit tests passed covering migration 0017, MP4 contract, byte mismatch, sha mismatch, corrupt probe, multi-stream MKV, rollback |
| P1.5-08 | P1.5 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_5_demos.py` | 12/12 demonstrations passed with 7 PNG screenshots and structured JSON evidence in `docs/reports/priority_1/p1_5_evidence/` |
| P1.6-01 | Media Library Performance Indexes (Migration 0018) | DB / Migrations | Tested and Passed | `backend/migrations/0018_media_library_indexes.sql` | Migration 0018 adds b-tree indexes on created_at, filename, file_size, duration, media_type, and width/height |
| P1.6-02 | Complete Source Discovery Without Exports Leakage | Media Management | Tested and Passed | `backend/app/services/media.py` | Pure source video discovery ensuring zero exports, candidate clips, or temporary upload files appear in media library |
| P1.6-03 | Rich Technical Metadata Badge Projection | UI / Unslop | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Enriched card badges displaying container format, video/audio codecs, resolution, duration, size, integrity status, analysis status |
| P1.6-04 | Debounced Search (Filename, ID, Unicode, Spaces) | Search & Discovery | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx`, `backend/app/services/media.py` | 300ms debounced search handling case-insensitivity, spaces, unicode characters, and asset ID prefixes |
| P1.6-05 | Multi-Criteria Filtering & Allowlisted SQL Sorting | Filtering & Sort | Tested and Passed | `backend/app/services/media.py`, `backend/app/api/v1/media.py` | Filtering by resolution, format, codec, analysis status; allowlisted sorting with case-insensitive filename and SQLi immunity |
| P1.6-06 | Server-Side Pagination Engine | API / Pagination | Tested and Passed | `backend/app/schemas/core.py`, `backend/app/services/media.py` | Bounded pagination responses with total_count, total_pages, and zero overlap between pages |
| P1.6-07 | Stream Topology & Provenance Inspection Modal | Inspection UI | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Detail modal displaying video/audio stream breakdowns, sample rates, channels, language tags, pixel format, and SHA-256 provenance |
| P1.6-08 | Chunked HTTP 206 Partial Content Video Seeking | Streaming Engine | Tested and Passed | `backend/app/api/v1/media.py` | High-performance video streaming with byte-range parsing, Accept-Ranges, 416 bounds checking, and path traversal defense |
| P1.6-09 | Explicit Metadata Refresh & Thumbnail Regeneration | Asset Maintenance | Tested and Passed | `backend/app/services/media.py`, `backend/app/services/media_pipeline.py` | POST endpoints for FFprobe metadata re-probing (preserving SHA-256) and on-demand timestamp thumbnail regeneration |
| P1.6-10 | Dependency-Safe Deletion with 409 Conflict Protection | Asset Safety | Tested and Passed | `backend/app/services/media.py` | Rejects deletion with 409 on active jobs or dependent exports; permits safe disk reclamation via force_with_exports=true |
| P1.6-11 | Responsive Mobile Reflow (375x812 Viewport) | Responsive Design | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Verified on 375x812 mobile viewport with exactly 0px horizontal overflow |
| P1.6-12 | P1.6 Automated Test Suites | Test Suite | Tested and Passed | `backend/tests/test_p1_6_media_library.py`, `frontend/src/test/mediaLibraryManagement.test.tsx` | 5 Pytest integration tests and 5 Vitest unit tests passed (398 backend / 148 frontend total suites) |
| P1.6-13 | P1.6 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_6_demos.py` | 14/14 demonstrations passed with 8 PNG screenshots and structured JSON evidence in `docs/reports/priority_1/p1_6_evidence/` |
| P1.7-01 | Dynamic Missing Media Detection Without DB Corruption | Media Service | Tested and Passed | `backend/app/services/media.py` | Physical media absence evaluated dynamically; records preserved; zero API or query crashes |
| P1.7-02 | Schema Migration 0019 (Recovery Metadata & Relinking Audit) | Database / Schema | Tested and Passed | `backend/migrations/0019_media_relinking_and_recovery.sql` | Added relinked_at, previous_storage_path, previous_sha256, relink_match_status, and index |
| P1.7-03 | Candidate Inspection & Security Defense | API / Security | Tested and Passed | `backend/app/services/media.py` | Traversal & system path block (HTTP 403); format check (HTTP 400); corrupt container check; 64 KB incremental SHA-256 |
| P1.7-04 | Duration & Resolution Discrepancy Protection (Force Flag) | Integrity & Safety | Tested and Passed | `backend/app/services/media.py` | Blocks mismatch relinking with HTTP 400 without force=true; records forced_mismatch audit trail |
| P1.7-05 | Streaming Bounded-Memory Replacement File Upload | Pipeline Service | Tested and Passed | `backend/app/services/media_pipeline.py` | Upload relinking via multipart form-data; 1 MB disk streaming buffer; on-the-fly SHA-256; atomic publish |
| P1.7-06 | External Drive Reconnection Availability Reconciliation | Asset Management | Tested and Passed | `backend/app/services/media.py`, `POST /api/v1/media/reconcile-availability` | Re-scans drive paths; flips disconnected drives to missing; auto-restores reconnected drives to present and verified |
| P1.7-07 | MediaRelinkModal UI with Unslop Design & Comparison | UI / Unslop | Tested and Passed | `frontend/src/features/media/MediaRelinkModal.tsx` | Two modes (path vs upload); comparison card; duration difference warning; forced relink confirmation checkbox |
| P1.7-08 | Media Library Missing File Badges & Drive Scanning | UI / Discovery | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Amber MISSING FILE badges; Relink File button; Check Drives scanner with toast notification |
| P1.7-09 | Video Edit Dashboard Source Guarding & Missing Card | UI / Dashboard | Tested and Passed | `frontend/src/features/videos/VideoEditDashboard.tsx` | Top missing file warning banner; Missing Source card replacing video player; source-dependent action gating |
| P1.7-10 | P1.7 Automated Regression Test Suites | Test Suite | Tested and Passed | `backend/tests/test_p1_7_media_relinking.py`, `frontend/src/test/mediaRelinking.test.tsx` | 9 Pytest integration tests (407 total) and 6 Vitest unit tests (154 total across 30 files) passing cleanly |
| P1.7-11 | P1.7 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_7_demos.py` | 5/5 scenarios passed with structured JSON evidence in `docs/reports/priority_1/p1_7_evidence/p1_7_evidence.json` |
| P1.8-01 | Media Deduplication Schema (Migration 0020) | DB / Migrations | Tested and Passed | `backend/migrations/0020_media_deduplication_and_reference_counting.sql` | Creates stored_media_files table, adds stored_file_id to media_assets with FK and indexes |
| P1.8-02 | Physical vs Logical Media Asset Separation | Core Architecture | Tested and Passed | `backend/app/models/entities.py`, `backend/app/schemas/core.py` | Distinguishes canonical physical stored files (stored_media_files) from logical project assets (media_assets) |
| P1.8-03 | Content-Based Streaming Deduplication Pipeline | Media Ingestion | Tested and Passed | `backend/app/services/media_pipeline.py` | Streaming 64 KB SHA-256; checks stored_media_files; unlinks .uploading part file on hit; 0 byte disk delta |
| P1.8-04 | Authoritative Transactional Reference Counting | Asset Management | Tested and Passed | `backend/app/services/media.py` | Scalar subquery counts active media_assets references; syncs stored_media_files.reference_count |
| P1.8-05 | Safe Deletion & Storage Reclamation | Storage Safety | Tested and Passed | `backend/app/services/media.py`, `backend/app/services/projects.py` | Decrements ref count on asset delete; unlinks file only when references reach 0; multi-project cascade safe |
| P1.8-06 | Relinking Isolation Across Shared References | Media Relinking | Tested and Passed | `backend/app/services/media.py` | Relinking a shared asset updates only that asset; other referencing assets preserve original file and count |
| P1.8-07 | Deduplication Stats & Reconciliation Endpoints | API / Management | Tested and Passed | `backend/app/api/v1/media.py` | Endpoints for deduplication stats, bytes saved, and reference count reconciliation |
| P1.8-08 | Frontend Shared Badges & Deletion Warnings | UI / Unslop | Tested and Passed | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx`, `MediaLibraryView.tsx` | Quiet Shared (N) badge; specs modal reference count; deletion dialog explaining file preservation |
| P1.8-09 | P1.8 Automated Regression Test Suites | Test Suite | Tested and Passed | `backend/tests/test_p1_8_media_deduplication.py`, `frontend/src/test/mediaDeduplication.test.tsx` | 15 Pytest tests (422 total) and 5 Vitest tests (159 total across 31 files) passing cleanly |
| P1.8-10 | P1.8 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_8_demos.py` | 8/8 demonstrations passed with structured JSON evidence in `docs/reports/priority_1/p1_8_evidence/p1_8_evidence.json` |
| P1.9-01 | Storage Quotas & Audit Migration 0021 | DB / Migrations | Tested and Passed | `backend/migrations/0021_storage_management_quotas_and_audit.sql` | Tables `storage_quotas` (default limits) and `storage_cleanup_audits` (history with JSON manifests and indexes) |
| P1.9-02 | Physical & Logical Storage Breakdown | Storage Accounting | Tested and Passed | `backend/app/services/storage.py`, `GET /api/v1/maintenance/breakdown` | Single-pass filesystem metrics across 12 categories; deduplication awareness; physical vs logical asset accounting |
| P1.9-03 | Two-Stage Non-Destructive Safe Cleanup | Storage Reclamation | Tested and Passed | `POST /api/v1/maintenance/cleanup-preview`, `POST /api/v1/maintenance/cleanup-execute` | Preview identifies disposable temporary artifacts; blocks active jobs (<60s mtime); execute revalidates under mutex lock |
| P1.9-04 | Path Traversal & Boundary Escape Defense | Storage Security | Tested and Passed | `backend/app/services/storage.py` | Canonical path containment prevents directory traversal (`../`) and symlink escapes from breaching `storage_root` |
| P1.9-05 | Persistent Storage Quotas & Preflight Enforcement | Quota Management | Tested and Passed | `backend/app/main.py`, `backend/app/services/storage.py` | Persistent quota limits; preflight middleware rejects uploads/renders with HTTP 507 (`QUOTA_EXCEEDED`) without deleting user media |
| P1.9-06 | Controlled Automatic Pruning | Background Maintenance | Tested and Passed | `POST /api/v1/maintenance/auto-prune` | Disabled by default (`auto_prune_enabled = 0`); prunes expired temp files strictly older than retention policy |
| P1.9-07 | Interrupted Upload & Crash Recovery | Fault Recovery | Tested and Passed | `POST /api/v1/maintenance/recover-stale-artifacts` | Sweeps stale in-flight `.uploading` and `.part` files as well as abandoned scratch folders from crashed render processes |
| P1.9-08 | Comprehensive Cleanup Audit Logging | Audit / Observability | Tested and Passed | `GET /api/v1/maintenance/cleanup-history` | Detailed immutable audit log of manual and automated cleanup executions with examined/deleted/skipped tallies |
| P1.9-09 | SettingsManager Storage & Quotas UI | Frontend UI | Tested and Passed | `frontend/src/features/settings/SettingsManager.tsx` | Disk overview, quota bars, category breakdown with deduplication badges, candidate preview cards, quota form, audit table |
| P1.9-10 | P1.9 Automated Test Suite (26 Cases) | Test Suite | Tested and Passed | `backend/tests/test_p1_9_storage_management.py`, `frontend/src/test/storageManagement.test.tsx` | 25 Pytest integration tests (447 total backend) and 6 Vitest unit tests (165 total across 32 files) passing cleanly |
| P1.9-11 | P1.9 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p1_9_demos.py` | 12/12 demonstrations (A-L) passed with structured JSON evidence in `docs/reports/priority_1/p1_9_evidence/p1_9_evidence.json` |

---

## Priority 2 — AI Video Analysis & Intelligence Foundation (P2)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| P2.1-01 | Schema Migration 0022 (Analysis Foundation & Shared Media) | DB / Migrations | Tested and Passed | `backend/migrations/0022_analysis_foundation_and_shared_media.sql` | Links `analysis_runs` to `stored_media_files(id)` with FK (ON DELETE SET NULL) and indexes `idx_analysis_runs_stored_file_id` and `idx_analysis_runs_status_sig` |
| P2.1-02 | Missing Media Protection (P1.7 Alignment) | Error Handling & Safety | Tested and Passed | `backend/app/services/analysis_pipeline.py`, `backend/app/api/v1/analysis.py` | Immediate rejection of analysis on missing/inaccessible media with HTTP 400 `MEDIA_FILE_MISSING`; graceful failure marking on orphaned jobs |
| P2.1-03 | Storage Quota Guard & Intermediate Temp Cleanup (P1.9 Alignment) | Quota Management | Tested and Passed | `backend/app/services/analysis_pipeline.py` | Enforces temporary storage quotas before/during analysis (HTTP 400 `STORAGE_QUOTA_EXCEEDED`); guaranteed temp directory reclamation in `finally` block |
| P2.1-04 | Canonical Shared Media Analysis Reuse (P1.8 Alignment) | Pipeline / Deduplication | Tested and Passed | `backend/app/services/analysis_pipeline.py` | Duplicate media assets sharing `stored_file_id` or SHA-256 clone existing analysis records in sub-50ms (<10ms in memory) without redundant compute |
| P2.1-05 | Direct Global Media Analysis Endpoints | Backend API | Tested and Passed | `backend/app/api/v1/analysis.py` | Mounts `/api/v1/media/{media_asset_id}/analysis...` mirroring all analysis operations without requiring `project_id` scoping |
| P2.1-06 | Modular Sequential Full-Video Analysis Pipeline | Analysis Core | Tested and Passed | `backend/app/services/analysis_pipeline.py` | 6 sequential stages across full video: validation, audio demuxing, faster-whisper speech transcription (int8 CPU), scene boundary detection, keyframe sampling, visual observations |
| P2.1-07 | Stage-Aware Caching & Invalidation via Source Signatures | Cache / Performance | Tested and Passed | `backend/app/services/analysis_pipeline.py` | Evaluates deterministic signature (size:mtime:duration) to bypass re-analysis on unchanged files, while force_reanalysis allows explicit reruns |
| P2.1-08 | Job Orchestrator Linkage & Granular Stage Telemetry | Job Orchestration | Tested and Passed | `backend/app/services/analysis_pipeline.py` | Full progress and stage synchronization (`queued`, `validating_source`, `extracting_audio`, `transcribing_speech`, `detecting_scenes`, `sampling_frames`, `generating_visual_observations`, `completed`) |
| P2.1-09 | Non-Destructive User Transcript Corrections | Persistence / ASR | Tested and Passed | `backend/app/services/analysis_pipeline.py`, `backend/app/api/v1/analysis.py` | Stores manual transcript edits in `transcript_corrections` table without corrupting raw Whisper segments |
| P2.1-10 | Frontend Client Integration & Type Safety | Frontend / Types | Tested and Passed | `frontend/src/services/apiClient.ts`, `frontend/src/types/analysis.ts` | Polymorphic `_analysisBase` supporting project and global paths; strict TypeScript models matching API schemas |
| P2.1-11 | P2.1 Automated Test Suite | Test Suite | Tested and Passed | `backend/tests/test_p2_1_video_analysis_foundation.py`, `frontend/src/test/videoAnalysisFoundation.test.tsx` | 12 Pytest tests (468 backend total) and 6 Vitest tests (171 frontend total across 33 files) passing cleanly |
| P2.1-12 | P2.1 Live Demonstrations & Structured Evidence | Verification | Tested and Passed | `backend/scripts/run_p2_1_demos.py` | 12/12 live demonstrations passed with structured JSON evidence saved to `docs/reports/priority_2/p2_1_evidence/p2_1_evidence.json` |
| P2.2-01 | Schema Migration 0023 (Highlight Discovery & Multimodal Ranking) | DB / Migrations | Tested and Passed | `backend/migrations/0023_highlight_discovery_and_multimodal_ranking.sql` | Adds `rank_position`, `evidence_coverage`, `signal_scores_json`, `generation_reason`, `transcript_excerpt` to `shorts_candidates` and creates `candidate_generation_runs` |
| P2.2-02 | 7-Dimension Multimodal Scoring Engine | Scoring Engine | Tested and Passed | `backend/app/services/highlight_discovery.py` | Computes bounded 0-100 scores for speech interest, emotional intensity, audio activity, visual interest, context completeness, narrative coherence, distinctiveness |
| P2.2-03 | Missing Modality Handling without Phantom Data | Robustness & Fairness | Tested and Passed | `backend/app/services/highlight_discovery.py` | Detects absent audio or transcript, reports evidence coverage, notes missing evidence, and renormalizes weights across present modalities |
| P2.2-04 | Natural Boundary Snapping & Context Completeness Scoring | Boundary Intelligence | Tested and Passed | `backend/app/services/highlight_discovery.py` | Word-level boundary snapping to natural speech pauses; detects and penalizes dangling pronouns and leading conjunctions |
| P2.2-05 | Configurable Creative Directions & Custom Signal Weights | Direction / Weights | Tested and Passed | `backend/app/services/highlight_discovery.py` | Normalized weight profiles for general, talking head, podcast, action, gaming, educational, plus user-specified custom weight vectors |
| P2.2-06 | Overlap Clustering & Alternative Temporal Cuts | Clustering | Tested and Passed | `backend/app/services/highlight_discovery.py` | Clusters high-overlap candidates into `overlap_group_id` with `alternative_of_candidate_id` assigned to tighter/extended alternative cuts |
| P2.2-07 | Deterministic Ranking & Reproducible Tie-Breaking | Ranking Core | Tested and Passed | `backend/app/services/highlight_discovery.py` | Strictly assigns `rank_position` 1..N using deterministic sort `(-quality_score, start_time, id)` for identical reproducibility |
| P2.2-08 | Zero-Redundancy Cache & Controlled Forced Rediscovery | Performance | Tested and Passed | `backend/app/services/highlight_discovery.py` | Instant (<2ms) retrieval on unchanged source with `force_rediscovery=False`; clean run creation and bypass with `force_rediscovery=True` |
| P2.2-09 | Rich Filtering, Pagination, and Rank Sorting API | Backend API | Tested and Passed | `backend/app/api/v1/highlights.py` | Adds query parameters for `limit`, `offset`, `min_score`, `min_duration`, `max_duration`, `category`, `sort_by=rank`, `order=asc/desc` |
| P2.2-10 | Direct Global Media Highlights & Recommendations Endpoints | Backend API | Tested and Passed | `backend/app/api/v1/highlights.py` | Mounts `/api/v1/media/{media_asset_id}/highlights/discover`, `/recommendations`, and `/highlights` without requiring `project_id` scoping |
| P2.2-11 | Frontend Highlights Workspace Multimodal Signals & Rank Badges | Frontend UI | Tested and Passed | `frontend/src/features/highlights/HighlightsWorkspace.tsx`, `frontend/src/services/apiClient.ts` | Displays rank badge, evidence coverage badge, transcript excerpt, 7-dimension breakdown, creative direction selector, force rediscovery toggle |
| P2.2-12 | P2.2 Automated Test Suite (25 Backend & 3 Frontend Tests) | Test Suite | Tested and Passed | `backend/tests/test_p2_2_multimodal_highlight_discovery.py`, `frontend/src/test/multimodalHighlightDiscovery.test.tsx` | 25/25 Pytest scenarios and 3/3 Vitest scenarios passing with 100% success |
| P2.2-13 | P2.2 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p2_2_demos.py` | 11/11 live demonstrations passed with structured JSON evidence saved to `docs/reports/priority_2/p2_2_evidence/p2_2_evidence.json` |
| P2.3-01 | Authoritative Portrait Geometry & Preview/Render Math Parity | Reframing Core | Tested and Passed | `backend/app/services/framing_engine.py`, `backend/app/services/reframing_renderer.py` | `FramingEngine.interpolate_crop_at` and `ReframingRenderer.build_crop_filter_expression` share exact piecewise crop math and dimensions |
| P2.3-02 | Scene-Cut Boundary Awareness & Instant Cut Transitions | Reframing Intelligence | Tested and Passed | `backend/app/services/framing_engine.py` | Moving average trajectory smoothing never interpolates pans across hard visual scene cuts; camera snaps instantly at cut boundaries |
| P2.3-03 | Multi-Strategy Framing Selection | Reframing Core | Tested and Passed | `backend/app/services/framing_engine.py` | Supports single-subject focus, two-person joint dialogue composition, group framing, central fallback, and pinned character/subject focus |
| P2.3-04 | Missing Media Protection (P1.7 Alignment) | Error Handling & Safety | Tested and Passed | `backend/app/services/reframing_service.py` | Immediate rejection of plan analysis and rendering on missing/inaccessible media with HTTP 400 `MEDIA_FILE_MISSING` |
| P2.3-05 | Storage Quota Preflight Enforcement (P1.9 Alignment) | Quota Management | Tested and Passed | `backend/app/services/reframing_service.py` | Preflight checks on temporary disk usage and generated video storage limits return HTTP 400 `STORAGE_QUOTA_EXCEEDED` before staging or rendering |
| P2.3-06 | Non-Destructive Manual Overrides & Revision Management | Revisions / History | Tested and Passed | `backend/app/services/reframing_service.py` | User crop keyframe adjustments generate new non-destructive revisions (`_rev2.mp4`); previous revisions restorable with zero data loss |
| P2.3-07 | Candidate Clip Integration & Boundary Trimming | Integration | Tested and Passed | `backend/app/services/reframing_service.py` | Directly consumes P2.2 `shorts_candidates` records, extracts candidate interval bounds, attaches `candidate_id`, and honors manual trim bounds |
| P2.3-08 | Direct Global Media Reframing REST Endpoints | Backend API | Tested and Passed | `backend/app/api/v1/reframing.py` | Exposes `/api/v1/media/{media_asset_id}/reframing/...` and `/api/v1/reframing/{plan_id}/...` for plan creation, listing, preview, overrides, and rendering |
| P2.3-09 | Project Isolation & Authorization Checks | Security & Projects | Tested and Passed | `backend/app/api/v1/reframing.py` | Mismatched project queries and unauthorized cross-project asset reframing return strict HTTP 404 |
| P2.3-10 | Security Containment & Path Traversal Prevention | Security Core | Tested and Passed | `backend/app/api/v1/reframing.py` | `resolve_contained_path` guards video serving endpoints; attempts to escape storage root are rejected with boundary errors |
| P2.3-11 | Real FFmpeg Portrait 9:16 Video Render Execution | Rendering Pipeline | Tested and Passed | `backend/app/services/reframing_renderer.py` | Generates verified vertical 9:16 MP4 video files with audio sync, exact crop filtergraph expressions, and 1080x1920 geometry |
| P2.3-12 | P2.3 Automated Test Suite (12 Backend & 4 Frontend Tests) | Test Suite | Tested and Passed | `backend/tests/test_p2_3_smart_reframing.py`, `frontend/src/test/smartReframingP23.test.tsx` | 12/12 Pytest scenarios and 4/4 Vitest scenarios passing with 100% success (505 backend, 178 frontend total) |
| P2.3-13 | P2.3 Live Acceptance Demonstrations | Verification | Tested and Passed | `backend/scripts/run_p2_3_demos.py` | 11/11 live demonstrations passed with structured JSON evidence saved to `docs/reports/priority_2/p2_3_evidence/p2_3_evidence.json` |



---

## Windows Production Mode, One-Click Launcher & Release Hardening (Session 24)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S24-01 | Single-Port Production Frontend Serving | FastAPI Backend | Implemented | `backend/app/main.py` | FastAPI serves built Vite distribution from `frontend/dist` on `http://127.0.0.1:8000` with SPA routing |
| S24-02 | One-Click Windows Launcher | Launcher Scripts | Implemented | `Start-ZEZEdit.bat`, `Start-ZEZEdit.ps1` | Comprehensive prerequisite checks, duplicate instance guard, background launch, health poll, and auto browser launch |
| S24-03 | Selective Graceful Stop Script | Stop Scripts | Implemented | `Stop-ZEZEdit.bat`, `Stop-ZEZEdit.ps1` | Safely stops only ZEZEdit via PID file and port 8000 validation without terminating unrelated processes |
| S24-04 | Multi-State Readiness Health Endpoint | Health API | Implemented | `backend/app/api/v1/health.py`, `/health` | Deep diagnostic check (process alive, DB integrity, storage writability, FFmpeg/FFprobe, Ollama, Whisper, dispatcher, frontend build) |
| S24-05 | Client Route Deep Link & SPA Fallback | Frontend Serving | Implemented | `backend/app/main.py` | Full React Router support for direct page refresh on `/videos/:id`, `/settings`, etc. without 404s |
| S24-06 | Session 24 Production Test Suite | Test Suite | Implemented | `backend/tests/test_session24_windows_production_and_launcher.py` | 6/6 tests passed covering SPA serving, multi-state health, storage failures, launcher safety, restart recovery, traversal prevention |

---

## Real-Media AI Quality Validation & Professional Video Acceptance (Session 23)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S23-01 | Honest Multi-Tier Visual Analysis Coverage Model | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Replaces naive 100% scene duration claims with multi-tier breakdown (scene detection, sampled frames, vision LLM, local CV, semantic span, density) |
| S23-02 | Coarse-to-Fine Keyframe Focus Sampling | Frame Sampler | Implemented | `backend/app/services/frame_sampler.py` | Automatically samples interior scene midpoints plus fine context frames around dialogue and high-motion moments |
| S23-03 | Visual Coverage & Engine Inventory UI View | Video Edit Dashboard UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Tab 8 displays full honest telemetry breakdown, engine inventory, and explicit documented limitations |
| S23-04 | Real Moving Subject Tracking (6 Scenarios) | Reframing & Subject Tracker | Implemented | `backend/app/services/subject_tracker.py` | Verified MIL + Haar/skin tracker across L->R, R->L, crossing people, pillar occlusion, scene cut, and re-entry with $\ge 85\%$ crop visibility |
| S23-05 | Multimodal Timeline Causal Consistency | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Enforces causal consistency linking Timestamp -> Scene -> Visual Observation -> Person -> Speech Turn |
| S23-06 | Session 23 Real-Media AI Quality Suite | Test Suite | Implemented | `backend/tests/test_session23_real_media_ai_quality.py` | 6/6 tests passed covering subject tracking, 9:16 visibility, multi-tier coverage, timeline consistency, and permanent novelty |

---

## End-to-End Generation Repair, Multimodal Acceptance & Real Video Export Verification (Session 22)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S22-01 | Automatic End-to-End Video Generation & Export | Highlights API & Export Service | Implemented | `backend/app/api/v1/highlights.py` | Generate Shorts guarantees discovering candidate scripts AND rendering playable 1080x1920 MP4 files |
| S22-02 | Accurate Real-Time Navigation Tab Status | Video Edit Dashboard UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Dynamic tab label shows active rendering counts `(N completed, M rendering)` instead of stuck `(0)` |
| S22-03 | 1-Click Missing Video Render Recovery | Video Edit Dashboard UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Surfaced "Render Missing Videos (N)" action to recover unrendered candidate scripts |
| S22-04 | Export Concurrency Lock & Result Metadata Enriched | Export Service | Implemented | `backend/app/services/export_service.py` | Prevents worker race condition, returns complete `output_path` and `result_metadata` for completed renders |
| S22-05 | Full Visual Timeline Coverage Metric | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Accurately calculates visual timeline coverage from detected scene spans across video duration ($\ge 80\%$) |
| S22-06 | Session 22 End-to-End Acceptance Test Suite | Test Suite | Implemented | `backend/tests/test_session22_end_to_end_generation.py` | 3/3 passed verifying 5 candidates -> 5 exports -> 5 valid 1080x1920 MP4 files verified via FFprobe |

---

## Multimodal Intelligence Completion, Real Subject Tracking & Permanent Novelty Verification (Session 21)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S21-01 | Real Moving Subject Tracking & Dynamic Framing | Reframing Engine | Implemented | `backend/app/services/subject_tracker.py` | TrackerMIL + motion differencing tracks moving subjects and compiles piecewise-linear FFmpeg crop pan filters |
| S21-02 | Permanent Novelty Ledger Survives Deletions | Novelty Management | Implemented | `backend/app/services/highlight_discovery.py` | Rejects previously used intervals even after exports and candidate scripts have been deleted |
| S21-03 | Temporal Multimodal Alignment Context | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Retrieves synchronized visual observation, scene, and transcript state at any timestamp |
| S21-04 | Multimodal Intelligence Acceptance Suite | Test Suite | Implemented | `backend/tests/test_session21_multimodal_intelligence_and_tracking.py` | 5/5 tests passed covering dynamic crop pan, permanent novelty, timeline coverage, and analysis reuse |

---

## Multimodal Video Intelligence, Automatic Short Generation & Permanent Novelty Management (Session 20)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S20-01 | Immediate Modal Dismissal & Non-Blocking Progress | Studio UI | Implemented | `frontend/src/features/videos/GenerateShortModal.tsx` | Fixed modal hanging on submit; dismisses instantly and shows non-blocking header progress banner |
| S20-02 | Automatic Export Rendering Pipeline | Highlights API & Export Service | Implemented | `backend/app/api/v1/highlights.py` | Automatically enqueues batch 9:16 export render jobs on candidate discovery, populating `Generated Videos` |
| S20-03 | Decoupled Script & Video Lifecycle | Highlights & Export APIs | Implemented | `backend/app/api/v1/` | Deleting an MP4 removes video while strictly preserving script and novelty history; re-renders from script anytime |
| S20-04 | Independent Script Deletion | Highlights API | Implemented | `backend/app/api/v1/highlights.py` | Added `DELETE /highlights/{candidate_id}`; deletes script while preserving rendered MP4 and novelty history |
| S20-05 | Content-Derived Download Filenames | Exports API | Implemented | `backend/app/api/v1/exports.py` | Generates sanitized filename from content title (e.g. `Elephant-Dance.mp4`) in `Content-Disposition` |
| S20-06 | Concurrent Export Worker Lock Guard | Export Service | Implemented | `backend/app/services/export_service.py` | Added `_ACTIVE_JOB_IDS` in-memory lock preventing concurrent execution race condition between queue poller and background tasks |
| S20-07 | Session 20 Acceptance Test Suite | Test Suite | Implemented | `backend/tests/test_session20_multimodal_workflow.py` | 4/4 tests passed covering auto-render, deletion preservation, re-render, and filename sanitization |

---

---

## Final Product Acceptance Audit & Remaining Work Inventory (Session 19)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S19-01 | Full-System Evidence-Based Product Audit | Product Architecture | Implemented | `docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md` | Audited all 8 workflow areas; derived exact completion percentage (100% active scope, 90% total historical scope) |
| S19-02 | Quality Gates Verification Suite (100% Pass Rate) | Test Suites | Implemented | `backend/tests/` & `frontend/src/test/` | Verified 250/250 backend tests pass (287.94s), 120/120 frontend vitests pass (18.49s), 0 TypeScript errors, clean production build (6.70s) |
| S19-03 | Interactive E2E Browser Acceptance Verification | Browser Testing | Implemented | `browser_sandbox/` | Verified 8 views on live app: Media Library, Video Edit Dashboard (Home, Shorts, Videos, Scripts, Frames, Transcript, Scenes), Generate Short modal, Processes, AI Providers, Settings |
| S19-04 | Finite Remaining-Work Implementation Plan | Release Roadmap | Implemented | `docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md` | Established finite remaining roadmap: exactly 1 session (Session 20) for FastAPI static bundle serving and Windows desktop launcher |
| S19-05 | Release Readiness Acceptance Criteria Definition | Governance | Implemented | `docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md` | Defined 5 strict objective release criteria; rendered verdict: NOT READY — LIMITED REMAINING WORK |

---

## Queue Architecture Repair, Regression Stabilization & Integration Acceptance (Session 18)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S18-01 | Full Dispatcher Lifecycle & True Worker Execution | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Verified deterministic execution across `media_analysis`, `candidate_generation`, and `export_render` with atomic FIFO dispatching, capacity management, and automatic worker release on completion |
| S18-02 | Startup Job & Orphan Reconciliation Repair | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Fixed startup orphan query in `recover_interrupted_jobs` to safely preserve legitimate queued analysis runs and queued exports whose jobs are active in SQLite |
| S18-03 | Self-Termination Cancellation Guard | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Overhauled `_terminate_pid_tree` to strictly safeguard `os.getpid()`, terminating only child worker processes (FFmpeg) and dedicated subprocesses without killing the host runner |
| S18-04 | Asynchronous Discovery Contract Unification | Highlights API | Implemented | `backend/app/api/v1/highlights.py` | Fixed missing `response` parameter in `generate_more_highlights`, unified `start_highlight_discovery` to emit `X-Job-Id`, and verified asynchronous background candidate discovery |
| S18-05 | Full Regression Stabilization (100% Pass Rate) | Test Suites | Implemented | `backend/tests/` & `frontend/src/test/` | Resolved all 5 failing backend tests and 2 failing frontend race conditions; full automated suites: 250/250 backend passed, 120/120 frontend passed, 0 errors in TypeScript |
| S18-06 | Real Multimodal Queue Integration | Export & Discovery Engines | Implemented | `backend/app/services/` | Executed real background candidate generation (`job_bedad53ef5d2`) and real 9:16 vertical render (`job_0af7b48be499`, 17.1 MB valid MP4 inspected via FFprobe) |

---

## Product Acceptance, Short-Form Quality & Workflow Completion (Session 16)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S16-01 | Automatic Queued Job Dispatcher & Atomic Claiming | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Implemented `claim_next_queued_job` with atomic SQL UPDATE preventing duplicate worker claims, background thread dispatching loop, and stale queue timeout cleanup |
| S16-02 | Stale Queued Job Timeout Reclamation | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Automatically reclaims jobs queued >1800s without worker pickup, marking them `failed` (`queue_timeout`) and keeping the Process Manager truthful |
| S16-03 | Dynamic Thumbnail Resolution & Serving | Media API | Implemented | `backend/app/api/v1/media.py` | Fixed 500 error on global media thumbnails; dynamically generates missing JPEG thumbnails and serves directly from storage |
| S16-04 | Persistent Script Editing Workflow | Highlights API & Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Added Edit Script modal on Generated Scripts tab; allows editing Title, Hook, and Dialogue; persists to SQLite via PATCH and survives full page refreshes |
| S16-05 | Truthful AI Capability Labeling | Frontend UI | Implemented | `frontend/src/features/videos/` | Replaced speculative marketing claims ("viral", "neural" for heuristics) with precise technical labels ("Local CPU execution (Neural & CV)") |
| S16-06 | Product Acceptance Regression Suite | Test Suite | Implemented | `backend/tests/test_session16_product_acceptance.py` | Verified atomic claiming under 5 concurrent threads, stale queue cleanup, persistent script updating, and thumbnail endpoints |

---

## Reliability, Rendering & Quality Acceptance (Session 14)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S14-01 | Strict Job State Invariant Enforcement | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Terminal states (`failed`, `cancelled`, `completed`) are strictly immutable; illegal transitions raise `INVALID_JOB_TRANSITION`; removed `is_stalled_heal` backdoor |
| S14-02 | Inactivity-Bounded Heartbeat Tickers | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Background tickers pulse every 10s during Whisper, scene detection, and frame sampling (`max_inactive_seconds=180.0`, `max_stage_seconds=1800.0`), preventing premature stall false-positives |
| S14-03 | 7-Creative-Direction Scoring Differentiation | Highlight Discovery | Implemented | `backend/app/services/highlight_discovery.py` | Integrated humor vocabulary scoring, dialogue Q&A velocity, and educational cues; verified up to 100% candidate differentiation across all 7 styles on `Visionquest S01E08.mkv` |
| S14-04 | 7-Scenario Video Rendering Matrix | Reframing & Export | Implemented | `backend/app/services/reframing_renderer.py` | Verified 9:16 portrait static, 9:16 moving pan, 9:16 subject tracking, 9:16 ASS captions + loudnorm audio, 1:1 square, 16:9 landscape, and 3-audio MKV transcode with 100% clean bitstream decode (`-f null -`) |
| S14-05 | 180s API Timeout & Zero-Alert Verification | Frontend API Client | Implemented | `frontend/src/services/apiClient.ts` | Discovers highlights on 69-minute MKV without client-side aborts; interactive live browser verification confirmed zero false alerts |
| S14-06 | Script & Video Deletion Isolation | Export Service & UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Deleting rendered MP4 exports preserves narrative scripts and candidate discovery intervals |
| S14-07 | 10-Case Job Lifecycle Acceptance Suite | Test Suite | Implemented | `backend/tests/test_session14_job_lifecycle_acceptance.py` | 10/10 acceptance tests verifying terminal state immutability, complete_job rejection, checkpoint isolation, and ticker bounds |

---

## Independent Acceptance Testing, Job Reliability Stress Testing & Defect Repair (Session 12)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S12-01 | Deadlock-Resistant Watchdog & PID Distinction | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Strictly distinguishes in-process threads from external child processes (`psutil.pid_exists`), capping progress to 99% on failure and preventing server-process PID masking |
| S12-02 | Inactivity-Bounded Heartbeat Ticker | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Automatically halts heartbeat pulse if worker thread freezes/deadlocks for >300s, ensuring frozen tasks fail cleanly |
| S12-03 | 16-Case Job Lifecycle Stress Suite | Test Suite | Implemented | `backend/tests/test_session12_job_lifecycle_stress.py` | 16 comprehensive edge cases verifying normal completion, slow operations, thread/process crashes, deadlocks, restart recovery, cancellation, and late race conditions |
| S12-04 | 1,000-Record Library Scalability Benchmark | Test Suite & Export Service | Implemented | `backend/tests/test_session12_large_library.py` | Verified sub-15ms server-side pagination, 98.8% payload size reduction (~10KB vs >850KB), 0 missing/duplicate items, and multi-criteria filters |
| S12-05 | Server-Side Scalable Exports API | Export API | Implemented | `backend/app/api/v1/exports.py` | Added query parameters (`search`, `status`, `aspect_ratio`, `sort_by`, `offset`, `limit`) and total count to `/projects/{id}/exports` |
| S12-06 | Non-Destructive Export Deletion | Export Service & UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Deleting rendered MP4 exports preserves narrative scripts and candidate discovery boundaries |
| S12-07 | End-to-End Browser Acceptance Verification | Browser Testing | Implemented | `docs/reports/session_12/SESSION_12_ACCEPTANCE_REPORT.md` | Full interactive verification on `Visionquest S01E08.mkv` confirming zero 15s timeout alerts and clean Process Manager state |

---

## Recurring Job Failure Repair, Video Dashboard Simplification & Inline Video Library (Session 11)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S11-01 | Stalled Job Watchdog Timeout & Race Hardening | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Raised default stall threshold from 60s to 600s, added OS PID liveness check via `psutil`, guarded completed/100% jobs from stall, and added self-healing on checkpoint save |
| S11-02 | Pipeline Heartbeat Ticker for Heavy CPU Stages | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Background async context manager pulses heartbeats every 8.0s during Whisper CPU transcription, FFmpeg scene detection, and frame sampling |
| S11-03 | Frontend Highlight Discovery Timeout Increase | API Client | Implemented | `frontend/src/services/apiClient.ts` | Extended highlight discovery request timeout from 15s to 180s to accommodate long multi-scene sliding window scoring |
| S11-04 | Simplified Video Dashboard Home Architecture | Video Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Removed obsolete duplicate generator tab; Home tab prominently displays video technical specs, Reusable Intelligence card, and clear primary CTAs |
| S11-05 | Unified Generate Short Modal | Video Studio UI | Implemented | `frontend/src/features/videos/GenerateShortModal.tsx` | Modal with explicit quantity selector (1, 3, 5, AI Auto, Custom), 7 creative directions, 3 aspect ratios, duration modes, and expandable advanced settings |
| S11-06 | Decoupled Generated Scripts & Video Archive | Video Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Scripts and exports managed independently; video deletion leaves narrative scripts intact; failed renders show Retry Render CTA |
| S11-07 | Inline Thumbnail Playback (Zero Scroll-to-Top) | Video Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Clicking card thumbnail flips that exact card into an inline HTML5 video player without scrolling to top; fullscreen and expand modal preview supported |
| S11-08 | Scalable Generated Videos Library | Video Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Fast client search, aspect ratio pills, status filter pills, multi-criteria sorting, and 12-item pagination with lazy image loading |
| S11-09 | End-to-End Automated Test Verification | Test Suites | Implemented | `backend/tests/test_job_lifecycle_stall_and_recovery.py` | 186/186 backend tests and 120/120 frontend tests pass with 100% pass rate |
| S11-10 | Session 11 Completion Report & Documentation | Documentation | Implemented | `docs/reports/session_11/SESSION_11_COMPLETION_REPORT.md` | Comprehensive session completion report detailing diagnosis, root causes, architecture changes, and verification evidence |

---

## Performance Diagnostics, Stuck Analysis Repair & Video Generation (Session 9)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S9-01 | AnyIO Worker Thread Offloading | Analysis API | Implemented | `backend/app/api/v1/analysis.py` | Offloads heavy CPU analysis tasks to AnyIO threadpool workers; reduced HTTP polling latency from timeout to 10.92ms average |
| S9-02 | Faster-Whisper Singleton Model Caching | Transcription | Implemented | `backend/app/services/transcription.py` | Thread-safe singleton model cache eliminates HuggingFace download/load overhead on recurring runs (0.00s warmup) |
| S9-03 | Whisper Streaming Progress & Non-VAD Primary Path | Pipeline & Transcription | Implemented | `backend/app/services/transcription.py` | Streaming segment callbacks with real work units (seconds transcribed), ETA calculation, and speech text ticker |
| S9-04 | Batched Keyframe Extraction Pass | Subject Tracker | Implemented | `backend/app/services/subject_tracker.py` | Replaced 91 sequential `ffmpeg.exe` subprocess calls with single batched pass; extraction speed improved 40.9x (2.23s) |
| S9-05 | Bounded Downscaled Subject Tracking | Subject Tracker | Implemented | `backend/app/services/subject_tracker.py` | 640px frame scaling, top-4 detection filter, and max-2 active TrackerMIL instances; reduced CPU tracking time from >100s to 11.5s |
| S9-06 | Stalled Job Process Exit Race Condition Fix | Job Orchestration | Implemented | `backend/app/services/jobs.py` | Added 15s grace period for terminated worker PIDs to prevent false-positive failures on clean FFmpeg exit |
| S9-07 | Real 5-Minute Video Analysis Live Execution | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Full live execution on `Ek Mota Hathi Ghumne Chala.mp4` (302.4s, 70MB) completed in 101.43s on CPU |
| S9-08 | Multi-Aspect Real MP4 Rendering & Output Verification | Export Pipeline | Implemented | `backend/app/services/export_service.py` | Verified 9:16 portrait (1080x1920), 1:1 square (1080x1080), 16:9 landscape (1920x1080); 100% clean decode with `-f null -` |
| S9-09 | Complete Parameter Matrix Validation | Highlights & Discovery | Implemented | `backend/app/services/highlight_discovery.py` | Validated all 7 creative directions, 4 quantity preferences, 5 duration modes, and zero-collision temporal novelty |
| S9-10 | Performance & Architecture Documentation | Documentation | Implemented | `docs/architecture/ANALYSIS_PERFORMANCE_AND_PROGRESS.md` | Formal root-cause audit, before/after benchmarks, and heartbeat protocol specifications |

---

## Real Object Tracking, Multi-Subject Intelligence & Temporal Novelty Correction (Session 8)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S8-01 | Temporal Novelty Correction & Containment Rejection | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Multi-layer overlap scoring with $R_{\min} = \frac{\text{Intersection}}{\min(\text{dur}_A, \text{dur}_B)}$; prevents containment duplicates (e.g. $[63.07, 87.31]$ vs $[63.07, 114.01]$) |
| S8-02 | Intra-Batch Overlap Deduplication & Alternative Cuts | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Validates every candidate against all candidates selected in current batch and clusters alternative cuts |
| S8-03 | CPU-Friendly Multi-Class Subject Detection | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | YCrCb skin segmentation for `person`/`face` and Sobel gradient saliency for `vehicle`/`object`/`animal` |
| S8-04 | Genuine Temporal Tracking via TrackerMIL | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | Persistent `TrackerMIL` instances maintain independent identities (`subject_1`, `subject_2`) across frames |
| S8-05 | Scene Cut Aware Track Termination | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | Tracks strictly terminate across scene transitions; never smooths or tracks across scene cuts |
| S8-06 | Multi-Subject Framing Strategies | Framing Engine | Implemented | `backend/app/services/framing_engine.py` | Supports `primary_subject`, `two_person`, `group`/`all_subjects`, `action_object`, and `pinned_subject_id` |
| S8-07 | Dynamic Tracking Render Pipeline Integration | Export Service | Implemented | `backend/app/services/export_service.py` | `_resolve_keyframes` runs `ReframingService` dynamically on demand and compiles piecewise-linear FFmpeg crop expressions |
| S8-08 | Speaker-Focused Framing Capability Audit | UI & Docs | Implemented | `frontend/src/features/studio/CandidateClipEditorModal.tsx` | Distinguishes Available (Face/Person, Object, Group) from Unsupported (Deep AV speaker diarization on CPU) |
| S8-09 | Comprehensive Automated Verification Tests | Testing | Implemented | `backend/tests/test_session8_tracking_and_novelty.py` | 12 new automated tests for overlap, containment, multi-subject tracking, and dynamic filtergraph generation |
| S8-10 | Architecture & Design Specifications | Documentation | Implemented | `docs/architecture/OBJECT_AND_MULTI_SUBJECT_TRACKING.md`, `docs/architecture/TEMPORAL_NOVELTY_DESIGN.md` | Formal specs for object tracking, multi-subject framing, and novelty design |

---

---

## Complete Product Integration & Real-World Validation (Session 7)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S7-01 | End-to-End Product Workflow Mapping | Architecture Docs | Implemented | `docs/architecture/END_TO_END_PRODUCT_FLOW.md` | Full system diagram and 14-stage component/API/service/record mapping |
| S7-02 | Long-Form Source Video Analysis & Persistence | Pipeline / DB | Implemented | `backend/app/services/analysis_pipeline.py` | Verified on 5.04-min 1080p video (`Ek Mota Hathi`): 37 scenes, 74 transcript segments, 41 frames, 12 observations |
| S7-03 | Simplified Generator Configuration Defaults | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | AI Recommended quantity, Best Overall direction, 9:16 aspect ratio, AI Best Duration; advanced settings collapsed |
| S7-04 | Candidate Quality & Persistent Novelty Ledger | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Batch 1 (3 clips) and Batch 2 Generate More (3 clips) produced 6 distinct non-overlapping candidates (0 common IDs) |
| S7-05 | Candidate Clip Editing & Reframing Resolution | Clip Editor / Export | Implemented | `backend/app/services/clip_editing_service.py` | Non-destructive trim (65.0s-85.0s), manual crop coordinates (50%, 50%), and zoom (1.1x) verified in rendered output |
| S7-06 | Multi-Aspect Real Video Rendering & Output Verification | FFmpeg Pipeline | Implemented | `backend/app/services/export_service.py` | Rendered 4 real shorts: Two 9:16 vertical (20.52s, 30.08s), One 1:1 square edited (20.00s), One 16:9 landscape (45.36s) |
| S7-07 | In-Browser HTML5 Video Playback & Byte-Range Streaming | Frontend / API | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Live playback verified via Browser Subagent on 1:1 square short with burned subtitles and audio |
| S7-08 | Central Process Manager Integration & Lineage | Process Center | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Tracked 10 tasks (export_render & media_analysis) with source video association and execution logs |
| S7-09 | Honest Tracking & Saliency Capability Audit | Tracking Services | Implemented | `backend/app/services/subject_tracker.py` | Comprehensive capability audit: Haar cascades for face/upper body, color saliency fallback; multi-subject/speaker tracking marked unsupported |
| S7-10 | Storage Reclamation & Disk Usage Verification | Storage Services | Implemented | `backend/app/services/storage.py` | Verified category sizes: media (70.4 MB), exports (40.6 MB), analysis (1.7 MB), backups (26.6 MB), db (4.2 MB) |

---

## Real Video Rendering, Clip Editing & Batch Export (Session 6C)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S6C-01 | Architecture Audit & 15-Stage Pipeline Design | Architecture Docs | Implemented | `docs/architecture/RENDERING_PIPELINE_AUDIT.md`, `VIDEO_RENDERING_DESIGN.md` | Answered 15 architectural questions, 15-stage filter chain specification |
| S6C-02 | Preset Catalog Extension for All Aspect Ratios | Export Models | Implemented | `backend/app/models/export.py` | Added `9:16`, `16:9`, `1:1`, `4:5`, `4:3`, `3:4` presets with strict dimensions |
| S6C-03 | Candidate Clip Editing Resolution & Custom Framing | Export Service | Implemented | `backend/app/services/export_service.py` | Seamlessly reads `candidate_clip_edits`, applies edited timestamps and manual/center crop expressions |
| S6C-04 | Process Manager Scoping for Render Jobs | Backend Services | Implemented | `backend/app/services/export_service.py` | Associates `media_asset_id` on job creation so jobs link to source video filename in Central Process Manager |
| S6C-05 | Direct MP4 Download & HTTP 206 Partial Content Streaming | Backend API | Implemented | `backend/app/api/v1/exports.py` | Added `/projects/{pid}/exports/{export_id}/download` and `/video` byte-range streaming |
| S6C-06 | Generated Short Videos Archive & In-Browser Player | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Dedicated Generated Videos tab with playable cards, HTML5 modal player, seek/controls, download, delete |
| S6C-07 | Multi-Candidate Batch Selection & Sticky Batch Bar | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Checkboxes, Select All, Clear Selection, and "Render Selected (N)" batch execution |
| S6C-08 | Post-Render Output Verification via OutputValidator | Export Pipeline | Implemented | `backend/app/services/export_service.py` | Mandates FFprobe stream inspection and FFmpeg null-sink decode verification before marking completed |
| S6C-09 | Comprehensive Automated Test Suites | Testing | Implemented | `backend/tests/test_session6c_rendering_and_batch_export.py`, `frontend/src/test/session6c_rendering.test.tsx` | 5 new backend tests, 3 new frontend tests; 169 backend & 120 frontend tests pass 100% |
| S6C-10 | Real Media Rendering & Browser Playback Verification | Verification | Implemented | `storage/exports/default/` | Rendered 9:16, 1:1, 16:9 MP4s and confirmed in-browser playback with Browser Subagent |

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

## Character Extraction Studio, Character Library & System Integration (Milestone 10)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M10-01 | Database Migration `0009_character_studio.sql` | DB / Migrations | Implemented | `backend/migrations/0009_character_studio.sql` | Schema for `character_extraction_jobs`, `character_profiles`, `character_candidates`, `character_observations`, `character_review_events` |
| M10-02 | Configurable Frame Sampling & Region Detection | Character Core | Implemented | `backend/app/services/character_service.py` | CPU-first OpenCV skin/saliency detection, non-saturating frame sampling, bounding box & confidence tracking |
| M10-03 | Spatial-Temporal Candidate Clustering | Character Core | Implemented | `backend/app/services/character_service.py` | Provisional visual candidate groupings without claiming biometric identity verification |
| M10-04 | Dialogue & Observation Association | Character Core | Implemented | `backend/app/services/character_service.py` | Cropped thumbnail generation, transcript temporal intersection, explicit unverified speaker association disclaimer |
| M10-05 | Human-in-the-Loop Review Controls | Character Core | Implemented | `backend/app/services/character_service.py` | Rename candidate, confirm to library, merge candidate groups, split observations, reject, non-destructive detach |
| M10-06 | Persistent Character Library & Documented JSON Export | Character Core | Implemented | `backend/app/services/character_service.py` | Project-wide character repository, bio/tag management, appearance totals, versioned JSON export payload |
| M10-07 | Character Studio REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/characters.py` | 12 REST endpoints covering extraction jobs, candidate listing/patching, review actions, library queries, and export |
| M10-08 | Frontend Character Studio Workspace | Features / Characters | Implemented | `frontend/src/features/characters/CharacterStudio.tsx` | Two tabs (Candidate Review & Character Library), extraction controls, observation gallery, review modals, JSON viewer |
| M10-09 | Full End-to-End System Integration & Reliability | System | Implemented | `frontend/src/app/App.tsx`, `backend/app/main.py` | All 10 modules seamlessly connected; startup recovery, zero regressions across 51 backend + 52 frontend tests |
| M10-10 | Backend Automated Test Suite (4 tests) | Testing | Implemented | `backend/tests/test_milestone10_character.py` | Extraction & observations, review workflow (rename, detach, split, merge, confirm), library & export, REST API (100% pass) |
| M10-11 | Frontend Vitest Test Suite (6 tests) | Testing | Implemented | `frontend/src/test/characters.test.tsx` | Studio rendering, observation inspector, inline rename, confirm modal, library tab, JSON export download (100% pass) |

---

## Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M11-01 | Full System Architecture Audit | Documentation | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Exhaustive verification of all 10 milestones, identifying real processing vs heuristics vs fallbacks |
| M11-02 | Implementation Classification & Honesty Audit | Audit | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Explicit breakdown distinguishing deep neural models, CV algorithms, rule-based heuristics, and offline fallbacks |
| M11-03 | Critical Technical Debt & Defect Registry | Audit / Quality | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Catalog of 10 ranked defects (DEF-01 through DEF-10) with reproduction steps, impacts, and corrective paths |
| M11-04 | React Error Boundary & Startup Crash Protection | Frontend Shell | Implemented | `frontend/src/components/ui/ErrorBoundary.tsx` | Catches unhandled render errors, presents user recovery action, eliminates blank-screen failure modes |
| M11-05 | Dark Mode Form Controls & Dropdown Unslop | UI Design System | Implemented | `frontend/src/styles/index.css`, `frontend/src/components/ui/Input.tsx` | Enforces `color-scheme: dark` and explicit background/text styling across all native select and option controls |
| M11-06 | Controlled Automated Test Verification | Testing | Implemented | `backend/tests/`, `frontend/src/test/` | 51/51 Pytest passing (100%), 52/52 Vitest passing (100%), 0 TypeScript errors, 2.29s Vite production build |
| M11-07 | SQLite WAL Integrity & FK Conformance | DB / Storage | Implemented | `storage/db/zezedit.db` | Verified 0 FK errors, database integrity check `ok`, all 9 migrations accounted for |
| M11-08 | Unslop Design System Installation & Redline Polish | Design / Shell | Implemented | `.agents/skills/unslop/`, `frontend/src/` | Applied Unslop 9-pass redline review, removed visual slop, quiet chrome, 4px grid |
| M11-09 | Graphify Knowledge Graph Build & Navigation | Tooling / Architecture | Implemented | `graphify-out/`, `.agents/rules/graphify.md` | Extracted 2,074 nodes, 5,772 edges across 113 communities; shortest path & explain verified |
| M11-10 | Unified Video Workspace Hub | Frontend Architecture | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | 9 integrated sub-workspaces for the active video asset preserving project and media context |
| M11-11 | Intelligent Post-Import Action Screen | Media Ingestion | Implemented | `frontend/src/features/media/PostImportModal.tsx` | Instant post-import action dialog with 4 distinct paths and live persistent job progress tracking |
| M11-12 | Full End-to-End User Journey Verification | Quality / E2E | Implemented | `docs/reports/milestone_11/` | Real browser verification across all 12 application views with live captured screenshot evidence |

---

## Pre-Deletion Baseline Reconstruction & Feature Parity Specification (Milestone 12)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M12-01 | Pre-Deletion Historical Baseline Specification | Reconstruction | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Authoritative recovery of historical state before Nov 11 deletion across all 20 application areas |
| M12-02 | Forensic Evidence Extraction (13M.12 & 13M.13) | Forensics | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Rigorous evidence extraction from surviving transcripts, 13M.12 report, and VS Code history |
| M12-03 | Feature Parity Matrix & Historical Gap Analysis | Specification | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Feature-by-feature parity analysis comparing pre-deletion capabilities against current ZezEdit 2.0 |
| M12-04 | Prioritized Restoration Roadmap | Architecture | Implemented | `docs/reconstruction/RESTORATION_ROADMAP.md` | 10-tier dependency-ordered implementation roadmap establishing exact sequence to achieve full parity |
| M12-05 | 13M.12 Mathematical Model & Test Recovery | CV / Tracking | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Verified 10/10 tracking tests, 113 backend pytest suite, 81 frontend vitest suite, and 3 contact sheets |
| M12-06 | 13M.13 Implementation & Partial Status Classification | UI / Revisions | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Documented 42 KB `ReframingReviewModal.tsx`, revision DB schema, and interrupted test status |
| M12-07 | Milestone 12 Comprehensive Reconstruction Report | Documentation | Implemented | `docs/reports/milestone_12_reconstruction_report.md` | 14-section formal milestone reconstruction and feature parity report |

---

## ZezEdit 1.0 Exact Feature Parity Specification (Milestone 13)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M13-01 | Immutable ZezEdit 1.0 Parity Specification | Specification | Implemented | `docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md` | 100 discrete requirements (`ZEZ-001` to `ZEZ-100`) covering all 10 product domains |
| M13-02 | Standardized Parity Scorecard Matrix | Tracking | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Authoritative measurement: 89 RESTORED (89%), 11 VERIFIED_PARTIAL (11%), 0 BLOCKED/UNRECOVERABLE |
| M13-03 | Parity Restoration Implementation Roadmap | Architecture | Implemented | `docs/reconstruction/RESTORATION_ROADMAP.md` | 5-phase dependency-ordered execution plan leading directly to complete feature parity |
| M13-04 | Milestone 13 Parity Restoration Plan Report | Documentation | Implemented | `docs/reports/milestone_13_parity_restoration_plan.md` | 12-section formal report detailing feature inventory, evidence paths, and next milestone |

---

## Video Analysis, AI Understanding & Temporal Context Restoration (Milestone 15)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M15-01 | Database Migration `0010_transcript_corrections_and_audio.sql` | DB / Migrations | Implemented | `backend/migrations/0010_transcript_corrections_and_audio.sql` | Adds `transcript_corrections` and `audio_analysis` tables with indexes |
| M15-02 | Audio Stream Inspection & Robust Silence Detection | Analysis Services | Implemented | `backend/app/services/audio_extractor.py` | FFprobe inspection, multi-channel handling, silent video fallback, and FFmpeg `silencedetect` |
| M15-03 | Real Scene Thumbnail Extraction & Serving | Analysis Services | Implemented | `backend/app/services/scene_detector.py`, `backend/app/api/v1/analysis.py` | Extracts scene representative JPEG thumbnails on disk; `/scene-thumbnail/{scene_id}` streaming endpoint |
| M15-04 | Non-Destructive Transcript Corrections (`ZEZ-025`) | Analysis / Captions | Implemented | `backend/app/api/v1/analysis.py`, `backend/app/services/export_service.py` | Full CRUD REST API; dynamically overlays raw Whisper text and applies to ASS export captions |
| M15-05 | Stage-Aware Analysis Caching & Fingerprinting (`ZEZ-029`) | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Checksum/mtime caching avoids re-running Whisper on unchanged media; supports `force_reanalysis` |
| M15-06 | Analysis Run History Selector (`ZEZ-030`) | Backend / Frontend | Implemented | `backend/app/api/v1/analysis.py`, `frontend/src/features/analysis/AnalysisWorkspace.tsx` | All runs preserved; dropdown selector allows historical inspection and comparison |
| M15-07 | Studio Dark UI Restoration & Lightbox (`ZEZ-027`, `ZEZ-098`) | Frontend UI | Implemented | `frontend/src/features/analysis/AnalysisWorkspace.tsx` | Unslop design compliance; Audio analysis panel, real thumbnails grid, lightbox modal, and inline editor |
| M15-08 | Backend Automated Parity Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone15_analysis_parity.py` | Stream inspection, silent video, scene thumbnails, caching, transcript corrections, temporal context (100% pass) |

---

## Core Product Workflow, Working Queue & Desktop Operations (Milestone 17)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M17-01 | Continuous Main Video to Shorts Pipeline | Workflow | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Full continuous workflow from import to analysis, highlight discovery, trimming, reframing, and export |
| M17-02 | Next Video Edit Workflow & Transition Modal | Workspace | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Dedicated Next Video button, auto-saving workspace state, and video switching dialog |
| M17-03 | Hardware Resource Inspector (`ZEZ-006`) | Monitoring | Implemented | `backend/app/api/v1/health.py`, `frontend/src/components/system/ResourceInspector.tsx` | Real-time CPU, RAM, process RSS, worker concurrency, and floating hover window |
| M17-04 | Working Queue & Job Orchestration (`ZEZ-094`, `ZEZ-095`) | Queue / Ops | Implemented | `backend/app/api/v1/jobs.py`, `frontend/src/features/queue/WorkingQueueView.tsx` | Full queue status tabs, queue distribution chart, job execution timeline logs |
| M17-05 | AI Provider Manager & Live Test Probe | AI Providers | Implemented | `backend/app/api/v1/ai_providers.py`, `frontend/src/features/providers/AIProviderManager.tsx` | Ollama, Faster-Whisper, and deterministic heuristic fallback cards, with live ping and model discovery |
| M17-06 | In-App Studio Documentation Center (`ZEZ-009`)| Docs / Help | Implemented | `backend/app/api/v1/docs_center.py`, `frontend/src/features/docs/DocumentationView.tsx` | Searchable categories, article listings, markdown renderer with 13 comprehensive guides |
| M17-07 | Scope Adjustment: Character Studio Deferred | Governance | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Character Studio deferred out of active priorities per M17 directive; preserved in DB and code |
| M17-08 | Regression Test Suite Expansion | Testing | Implemented | `backend/tests/test_milestone17_core_operations.py`, `frontend/src/test/milestone17_operations.test.tsx` | 61/61 backend pytest (100% pass), 56/56 frontend vitest (100% pass) |

---

## Unified Video-to-Shorts Production Pipeline (Milestone 18)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M18-01 | Authoritative Lifecycle State Machine | Pipeline Core | Implemented | `backend/app/services/workflow_state.py` | 18 explicit workflow lifecycle stages; self-healing dynamic derivation from SQLite tables and in-flight jobs |
| M18-02 | Workflow Telemetry & Next-Actions API | Backend API | Implemented | `backend/app/api/v1/media.py` | `GET /projects/{project_id}/media/{asset_id}/workflow` returning stage, stepper, counters, and available next actions |
| M18-03 | Multiple Shorts Batch Export Endpoint | Backend API | Implemented | `backend/app/api/v1/exports.py` | `POST /projects/{project_id}/exports/batch` enqueuing parallel independent render jobs with skipped candidate validation |
| M18-04 | Batch Export Multiple Shorts Modal | Frontend Studio | Implemented | `frontend/src/features/exports/BatchExportModal.tsx` | 9:16 / 1:1 / 16:9 aspect ratios, animated word captions, audio loudness normalization, multi-selection |
| M18-05 | Workflow Stage Header Banner & Progress Stepper | Frontend Studio | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Pipeline badge, 5-stage stepper (Ingest → Analysis → Highlights → Review → Export), telemetry counters |
| M18-06 | Dynamic Primary Next-Action Execution Dispatch | Workflow | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Context-aware 1-click action button dispatching Start Analysis, Discover Highlights, Review, Batch Export, Next Video |
| M18-07 | Per-Video State Persistence & Auto-save | Workspace Core | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Restores active tab and video state from `localStorage`; real-time "✓ Auto-saved" visual confirmation |
| M18-08 | Multi-Video Strict Cross-Project Data Isolation | Architecture | Implemented | `backend/app/services/workflow_state.py` | Zero cross-project or cross-media state leakage; verified by automated multi-tenant test suites |
| M18-09 | Automated Backend Integration Test Suite | Testing | Implemented | `backend/tests/test_milestone18_unified_pipeline.py` | 5 comprehensive integration tests covering lifecycle, API, batch export, skipped candidates, data isolation (100% pass) |
| M18-10 | Automated Frontend Vitest Test Suite | Testing | Implemented | `frontend/src/test/milestone18_pipeline.test.tsx` | 3 vitest tests covering modal rendering, candidate selection, aspect ratio options, and API dispatch (100% pass) |

---

## Desktop Operations Center, Working Queue, Resource Inspector and AI Provider Manager (Milestone 19)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M19-01 | Real Working Queue & Cancellation / Retry Engine | Job Queue | Implemented | `backend/app/services/jobs.py`, `backend/app/api/v1/jobs.py` | Cancels active worker states; retries failed jobs without duplicate renders; logs `job_retried` timeline events |
| M19-02 | Queue Chart & Task Type Distribution Breakdown | Operations UI | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Visual queue bar, live counts (running/pending/completed/failed/cancelled), task type pills, duration column |
| M19-03 | Hardware Resource Inspector & Accessibility Controls | System Monitoring | Implemented | `frontend/src/components/system/ResourceInspector.tsx` | Hover activation with grace buffer, click-to-pin, Escape key dismiss, outside click dismiss, accessibility roles |
| M19-04 | AI Provider Manager & Studio Task Engine Routing | AI Providers | Implemented | `frontend/src/features/providers/AIProviderManager.tsx` | Ollama, Faster-Whisper, and heuristic cards, 4-task engine routing grid, live ping probe, and secret token masking |
| M19-05 | In-App Documentation Center Expansion | Docs / Help | Implemented | `backend/app/api/v1/docs_center.py`, `frontend/src/features/docs/DocumentationView.tsx` | 16 articles across 5 categories, including troubleshooting, keyboard shortcuts, and storage layout guides |
| M19-06 | Subsystem Diagnostics Probe API | Health / System | Implemented | `backend/app/api/v1/health.py`, `frontend/src/features/dashboard/FoundationOverview.tsx` | `GET /api/v1/system/diagnostics` probing SQLite WAL, storage buckets, FFmpeg/FFprobe binaries, Ollama, Whisper, host CPU/RAM |
| M19-07 | Automated Operations Backend Test Suite | Testing | Implemented | `backend/tests/test_milestone19_desktop_operations.py` | 6 integration tests covering diagnostics, cancellation, retries, stats, provider resiliency, and docs search (100% pass) |
| M19-08 | Automated Operations Frontend Vitest Suite | Testing | Implemented | `frontend/src/test/milestone19_desktop_operations.test.tsx` | 4 tests covering ResourceInspector, WorkingQueueView, AIProviderManager, and DocumentationView (100% pass) |

---

## Production Hardening, Long-Video Performance, Storage Management & Recovery (Milestone 20)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M20-01 | Large Video Streaming Import & Media Integrity | Media Pipeline | Implemented | `backend/app/services/media_pipeline.py`, `backend/app/services/media.py` | 64KB bounded chunk streaming import; FFprobe metadata persistence; source media integrity scanner (`online`, `missing`, `corrupted`) |
| M20-02 | Safe Media Relinking with Candidate Verification | Media / Relink | Implemented | `backend/app/services/media.py`, `backend/app/api/v1/media.py` | Candidate duration, resolution, size comparison with discrepancy warnings; force relink protection; preserves analysis and candidate history |
| M20-03 | Memory-Aware Video Processing & Disk Caching | Video / Frames | Implemented | `backend/app/services/frame_sampler.py`, `backend/app/services/audio_extractor.py` | Timestamp seeking (`-ss` before `-i`); downscaling to 640px; disk frame caching; bounded 16kHz mono audio chunk extraction |
| M20-04 | Resource-Aware Worker Management & Priority Scheduling | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Single queue architecture; configurable concurrency; host CPU/RAM pressure guard; strict priority dispatch (200 > 150 > 100 > 50) |
| M20-05 | Granular Job Checkpoints & Crash Recovery | Recovery Core | Implemented | `backend/app/services/jobs.py`, `backend/migrations/0011_*.sql` | Persists completed units and intermediate artifacts; restart recovery preserves checkpoints for idempotent resume without work duplication |
| M20-06 | Categorized Storage Breakdown & Low-Storage Guard | Storage Service | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Real filesystem measurement across 9 categories; low storage threshold (< 5GB) warning |
| M20-07 | Safe Disposable Cache Cleanup Preview & Execution | Storage Ops | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Scans strictly disposable `temp/` buffers; cryptographic confirmation token; guarantees source media, projects, and exports are never deleted |
| M20-08 | Database Diagnostics & PRAGMA Verification | Database Ops | Implemented | `backend/app/services/backup_service.py`, `backend/app/api/v1/settings.py` | Live `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, WAL mode confirmation, table row counts, orphaned record detection |
| M20-09 | Online Database Backups & Pre-Restore Safety Copy | Backups Core | Implemented | `backend/app/services/backup_service.py`, `backend/app/api/v1/settings.py` | Verified SQLite online backups; pre-restore automatic safety snapshots; recovery readiness status reporting |
| M20-10 | Multi-Tab Studio Settings Manager | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | 6 dedicated tabs: General, Processing & Performance, Storage Management, Backups & Recovery, AI Providers, Diagnostics |
| M20-11 | Media Library Integrity & Relink Dialog | Media UI | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Batch project media integrity check button; missing file relink dialog with candidate comparison preview and force override |
| M20-12 | Comprehensive Automated Test Suites | Testing / QA | Implemented | `backend/tests/test_milestone20_production_reliability.py`, `frontend/src/test/milestone20_production_hardening.test.tsx` | 7 backend pytest tests (100% pass); 5 frontend vitest tests (100% pass); 68/68 total vitest tests passing |

---

## Editorial & Notification Refinements (Milestone 23)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M23-01 | AI Assistant Plan Version History & Restore API | Timeline API | Implemented | `backend/app/api/v1/timeline.py`, `backend/app/services/ai_editor_service.py` | `GET /timelines/{id}/ai/plans` listing version history; `POST /timelines/{id}/ai/plans/{plan_id}/restore` rolling back / applying plan operations |
| M23-02 | Interactive Plan Version History Drawer (`ZEZ-080`) | Timeline UI | Implemented | `frontend/src/features/timeline/TimelineEditor.tsx` | Slide-over drawer in AI tab with dynamic version counter badge, timestamps, status badges (`executed`, `proposed`, `rejected`), operations diff breakdown, and 1-click restore |
| M23-03 | Global Floating Toast Notification System (`ZEZ-008`) | System UI | Implemented | `frontend/src/components/system/ToastNotificationCenter.tsx`, `frontend/src/main.tsx`, `frontend/src/app/App.tsx` | Fixed bottom-right container, 4-second self-dismiss timers, pause on hover, action button hooks, and background job transition alerts (`running` -> `completed`/`failed`) |
| M23-04 | Automated Test Suites for Plan History & Toasts | Testing / QA | Implemented | `backend/tests/test_milestone9_timeline.py`, `frontend/src/test/notifications.test.tsx`, `frontend/src/test/timeline.test.tsx` | 80/80 backend pytest tests passing; 73/73 frontend vitest tests passing; verified via live browser verification with screenshot evidence |

---

---

## Unified Single-Video Studio Evolution (Sessions 0–3)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S0-01 | Architectural Audit, Multi-Session Blueprint & Schema Design | Architecture | Implemented | `docs/architecture/SESSION_0_AUDIT_REPORT.md`, `docs/architecture/UNIFIED_VIDEO_STUDIO_DESIGN.md` | Single-video workflow roadmap, database & API migration specs, and unified studio design blueprint |
| S1-01 | Navigation Simplification & Sidebar Streamlining | App Shell | Implemented | `frontend/src/app/App.tsx`, `frontend/src/components/layout/Sidebar.tsx` | Removed disconnected standalone tools (Video Analysis, Highlights, Reframing, Shorts Export); streamlined sidebar to Media Library |
| S1-02 | Unslopped Media Library with Dedicated "Open Video Studio" Action | Media Library | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Removed all emojis; single unified primary action on video cards to enter Dedicated Studio |
| S2-01 | Dedicated `/studio/:assetId` Route & Synchronized History | Routing / Navigation | Implemented | `frontend/src/app/App.tsx`, `frontend/src/features/studio/SingleVideoStudio.tsx` | Pure React state URL synchronization with `window.history.pushState` and `popstate` support; direct URL hydration |
| S2-02 | Global Analysis Progress Bar with Stage & Percentage Telemetry | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Real-time measurable progress bar with stage status, percentage, elapsed time, and cancellation trigger |
| S2-03 | Upfront Generation Configuration Bar | Studio Controls | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Upfront aspect ratio selection (9:16, 1:1, 16:9, 4:5), clip count (5, 6, 10, 15, 20), creative direction (Best Overall, Dramatic, Action, Emotional/Sad, Dialogue, Funny) |
| S2-04 | Framed Video Preview Player with Dynamic Ratio Adaptation | Video Studio | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Aspect-ratio constrained preview container, scrub bar, transport controls, and direct candidate seek |
| S2-05 | Generated Shorts Showcase with Direct Export Triggers | Studio Showcase | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Candidate shorts cards with virality scores, duration badges, category pills, seeking triggers, and 1-click MP4 export |
| S2-06 | Collapsible Deep Intelligence Drawers | Studio Intelligence | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Collapsible drawers for Timestamped Transcript, Detected Scene Cuts, and Detailed Media Metadata |
| S2-07 | Comprehensive Vitest Automated Test Suite | Testing / QA | Implemented | `frontend/src/test/singleVideoStudio.test.tsx` | 6 comprehensive tests covering loading, upfront controls, discovery trigger, export submission, and drawers (19/19 test files, 94/94 tests pass) |
| S3-01 | Database Migration `0012_unified_analysis_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0012_unified_analysis_pipeline.sql` | Added `job_id`, `source_signature`, `stage_details_json`, `checkpoint_data_json` to `analysis_runs` |
| S3-02 | Bounded Memory Streaming Pipeline for 1–2 GB Movies | Analysis Core | Implemented | `backend/app/services/analysis_pipeline.py` | Out-of-process streaming FFmpeg demuxing, scene detection, and frame sampling without loading full video into RAM |
| S3-03 | Sub-Millisecond Source Signature Calculation & Invalidation | Analysis Core | Implemented | `backend/app/services/analysis_pipeline.py` | Hybrid `size:mtime:hash64k` signature; instant cache invalidation upon file change |
| S3-04 | Faster-Whisper Automatic VAD Fallback | Speech AI | Implemented | `backend/app/services/transcription.py` | Automatic fallback to `vad_filter=False` when VAD classifies dialogue over music as silence; verified on Hindi rhymes |
| S3-05 | Persistent JobOrchestrator Linkage & Checkpoint Sync | Jobs / Pipeline | Implemented | `backend/app/services/analysis_pipeline.py`, `backend/app/services/jobs.py` | Synchronized `media_analysis` jobs, priority 150, stage progress, and non-clamping completion checkpoints |
| S3-06 | Granular Stage Telemetry & Cache Inspection APIs | Backend API | Implemented | `backend/app/api/v1/analysis.py` | `GET /analysis/{id}/telemetry` and `GET /analysis/{id}/cache` exposing stage, pct, timings, warnings, and component breakdown |
| S3-07 | Analysis Cancellation & Retry State Transitions | Backend API | Implemented | `backend/app/api/v1/analysis.py` | `POST /analysis/{id}/cancel` and `POST /analysis/{id}/retry` synchronized with JobOrchestrator state machines |
| S3-08 | Single-Video Studio Real Progress Banner & Telemetry UI | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Live stage telemetry polling (1.5s), elapsed time, cancel/retry action buttons, cache info badge, and distinct stage milestones |
| S3-09 | Automated Test Suite for Session 3 Unified Analysis | Testing / QA | Implemented | `backend/tests/test_session3_unified_analysis.py` | 7 comprehensive tests covering signatures, job linkage, telemetry, caching, cancel, retry, and audio-less video (100% pass) |
| S4-01 | Multimodal Candidate Discovery Engine | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Multi-signal discovery analyzing transcript dialogue, speech turns, scene cuts, keyframe visual semantics, and audio energy with explainable scoring |
| S4-02 | Natural Boundary Snapping & Breathing Room | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Speech closure on terminal punctuation (`.`, `!`, `?`), 0.15s lead-in margin, and scene cut snapping preventing flash frames and mid-sentence cuts |
| S4-03 | 7 Creative Direction Profiles & Adaptive Weighting | Intelligence Core | Implemented | `backend/app/services/highlight_discovery.py` | Distinct multimodal weighting profiles for Best Overall, Viral & Punchy, Dramatic, Action & Motion, Emotional / Sad, Engaging Dialogue, and Humorous |
| S4-04 | Persistent Novelty & Non-Repetition Engine | Novelty Core | Implemented | `backend/app/services/highlight_discovery.py` | tIoU $\ge 0.50$ and OverlapRatio $\ge 0.60$ novelty exclusion checks against historical intervals; verified $<0.38$ max overlap on real media |
| S4-05 | Database Migration `0013_candidate_discovery_novelty.sql` | DB / Migrations | Implemented | `backend/migrations/0013_candidate_discovery_novelty.sql` | Schema migration for `candidate_generation_runs`, `media_generated_clips_history`, and candidate boundary confidence columns |
| S4-06 | REST Endpoints for Discovery, Runs & Novelty History | Backend API | Implemented | `backend/app/api/v1/highlights.py` | `POST /highlights/generate-more`, `GET /highlights/runs`, `GET /highlights/runs/{id}`, and `GET /highlights/history` |
| S4-07 | Single-Video Studio Candidate Cards with Multimodal Score Popovers | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Candidate cards with Attractiveness estimate, Natural Cut confidence badge, creative direction pill, and expandable 6-signal breakdown grid |
| S4-08 | Candidate Batches Drawer & Novelty Tracking Ledger UI | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Drawer tab for candidate discovery runs, batch filtering, requested vs selected counts, and novelty exclusions |
| S4-09 | Comprehensive Test Suites for Candidate Discovery & Novelty | Testing / QA | Implemented | `backend/tests/test_session4_candidate_discovery.py`, `frontend/src/test/session4_candidate_discovery.test.tsx` | 5/5 backend tests and 4/4 frontend tests passing (100% pass across 28 backend tests and 98 frontend tests) |
| S5-01 | Database Migration `0014_candidate_clip_edits.sql` | DB / Migrations | Implemented | `backend/migrations/0014_candidate_clip_edits.sql` | Dedicated candidate clip edits schema preserving original candidate discovery data and novelty records |
| S5-02 | Candidate Clip Editing & Persistence Service | Core Services | Implemented | `backend/app/services/clip_editing_service.py` | Isolated edit state management: timestamp bounds validation, duration computation, aspect ratio framing, manual crop offsets, and reset-to-original |
| S5-03 | Candidate Clip Editing REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/clip_edits.py` | `GET/PUT /media/{mid}/candidates/{cid}/edit`, `POST .../edit/reset`, `POST .../edit/track` |
| S5-04 | Interval-Bounded Smart Subject Tracking | Reframing Core | Implemented | `backend/app/services/reframing_service.py`, `backend/app/services/subject_tracker.py` | Supports explicit interval `start_time` and `end_time` tracking via OpenCV Haar cascades and central saliency fallback without full video decode |
| S5-05 | Interactive Candidate Clip Editor Modal | Studio UI | Implemented | `frontend/src/features/studio/CandidateClipEditorModal.tsx` | Bounded clip loop player, dynamic aspect ratio crop box overlay, timeline trimming handles with +/-0.5s adjusters, aspect ratio buttons (9:16, 1:1, 16:9, 4:5), and framing mode tabs |
| S5-06 | Single-Video Studio Candidate Card "Edit Clip" Integration | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | "Edit Clip" button on discovered candidate cards launching the focused clip editor modal |
| S5-07 | Automated Unit & Integration Test Suites | Testing / QA | Implemented | `backend/tests/test_session5_clip_editing.py`, `frontend/src/test/session5_clip_editing.test.tsx` | 4/4 backend tests and 4/4 frontend tests passing (100% pass across 11 unified pipeline tests and 102 frontend tests) |
| PR-01 | Single-Button Clear All Application Data API | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | `POST /storage/clear-all-data` with explicit `DELETE` confirmation; sweeps all managed storage subdirectories and database tables while preserving migrations and app settings |
| PR-02 | Clear All Data Unit Test Suite | Testing / QA | Implemented | `backend/tests/test_storage_clear_all_data.py` | 2/2 tests verifying token validation, file deletion across managed directories, SQLite database truncation, and default workspace re-creation |
| PR-03 | Direct Video Ingestion & Short Video Generator Library | Library UI | Implemented | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Direct drag & drop / file picker with video type validation, auto-title derivation, and card grid with "Open Video Dashboard" CTA |
| PR-04 | Dedicated Video Edit Dashboard (`/videos/:assetId`) | Dashboard UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Centralized video workspace with top persistent header, real-time stage progress bar & ETA, and 8 dedicated horizontal tabs |
| PR-05 | 8 Dedicated Video Inspection & Generation Tabs | Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | 1. Home (Player + Specs), 2. Short Generator (18 directions, presets, tracking), 3. Generated Shorts (Cards, Edit Modal, Export), 4. Generated Scripts (Cards, Regenerate Video), 5. Analyzed Frames, 6. Voice & Transcript, 7. Scene Analysis, 8. Video Details |
| PR-06 | Clear All Application Data Confirmation Modal | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | High-impact warning card and dialog requiring typing `DELETE` to execute total wipeout |
| PR-07 | Video-Centric Frontend Automated Tests | Testing / QA | Implemented | `frontend/src/test/productRestructure.test.tsx` | 2/2 tests verifying ShortVideoGeneratorLibrary and VideoEditDashboard tabs (104 frontend tests pass) |
| S6A-01 | Reusable Video Intelligence Engine & Sub-Second Cache Validation | Intelligence Core | Implemented | `backend/app/services/highlight_discovery.py` | Full video analysis executed once; all subsequent short generations reuse stored audio, scenes, transcripts, and frames in ~0.12s |
| S6A-02 | Simplified 4-Option Default Generator UI & Graphite Unslopped Layout | UI / Dashboard | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Clean, calm default form: Option 1 AI Recommended clip count, Option 2 Best Overall / Varied, Option 3 9:16 Vertical, Option 4 AI Selects Best Duration |
| S6A-03 | Collapsible Advanced Settings & Per-Video Persistence | Studio Controls | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Collapsed by default; 7 active supported creative directions, 11 disabled "Coming Soon", tracking modes, scene focus, novelty policy, localStorage config persistence |
| S6A-04 | Multi-Layer Persistent Novelty & Temporal Overlap Engine | Novelty Core | Implemented | `backend/app/services/highlight_discovery.py` | Exact interval matching (<2.5s tolerance), strict temporal IoU / asymmetric overlap guards, transcript token similarity checks |
| S6A-05 | Aspect-Ratio Independent Rejection & Honest Exhaustion Handling | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Changing aspect ratios tests against all recorded moments; detects exhaustion honestly with `is_novelty_exhausted` and warning banner |
| S6A-06 | Database Migration `0015_reusable_intelligence_and_generate_more.sql` | DB / Migrations | Implemented | `backend/migrations/0015_reusable_intelligence_and_generate_more.sql` | Added `generation_type`, `reused_analysis_run_id`, `duration_preference`, and `is_novelty_exhausted` to `candidate_generation_runs` |
| S6A-07 | Real Video Verification on 73.3MB Media File | Testing / QA | Implemented | `backend/scripts/verify_session6a_real_video.py` | Verified on `Ek Mota Hathi Ghumne Chala.mp4` (0.127s discovery time, 0 duplicates generated, novelty exhaustion recorded) |
| S6A-08 | Comprehensive Automated Test Suites | Testing / QA | Implemented | `backend/tests/test_session6a_reusable_intelligence_and_generate_more.py` | 6/6 dedicated session tests passing (152/152 backend tests, 106/106 frontend tests passing) |
| S6B-01 | Database Migration `0016_process_manager_and_storage_reclamation.sql` | DB / Migrations | Implemented | `backend/migrations/0016_process_manager_and_storage_reclamation.sql` | Adds `media_asset_id` and `parent_job_id` columns with indexes to `jobs` table |
| S6B-02 | Central Process Manager Dashboard & Subprocess Lineage | Core Services | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx`, `backend/app/services/jobs.py` | Unified table of background tasks across all videos, Category & Status filters, video picker, search, retry attempt lineage, and subprocess tree cancellation via `psutil` |
| S6B-03 | Process Details Drawer with Live Logs & Elapsed/ETA Timers | Dashboard UI | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Slide-over drawer with process metadata, progress bar, duration counters, retry tree, and raw execution logs |
| S6B-04 | Process Manager API Parity across `/processes` and `/jobs` | Backend API | Implemented | `backend/app/api/v1/jobs.py`, `backend/app/api/v1/__init__.py` | Full route parity for listing, getting, cancelling, retrying, and deleting jobs |
| S6B-05 | Stale Process Crash Recovery on Startup | Jobs / Core | Implemented | `backend/app/services/jobs.py` | Auto-detects interrupted running/cancelling jobs on server startup and flags them as `interrupted` |
| S6B-06 | Single Video Deletion Storage Reclamation | Media Core | Implemented | `backend/app/services/media.py` | Deletes associated physical files (`media/`, `proxies/`, `thumbnails/`, `analysis/`) and marks active jobs cancelled on single video delete |
| S6B-07 | Complete User Data Cleanup & Physical Storage Reclamation | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Sweeps all managed storage directories, terminates active jobs, empties user DB tables, compacts SQLite physical file with double WAL checkpoints, and re-creates default project |
| S6B-08 | Storage Cleanup Preview API & Reclaimed Byte Telemetry | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Computes item counts (videos, clips, frames, temp files), estimated reclaimable bytes, and pre/post physical disk delta |
| S6B-09 | Settings Storage Manager UI Integration | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | "Refresh Storage Usage" button, dynamic cleanup preview breakdown, active jobs warnings, and `DELETE ALL USER DATA` confirmation modal |
| S6B-10 | Automated Test Suites for Process Manager & Storage Reclamation | Testing / QA | Implemented | `backend/tests/test_process_manager_lifecycle.py`, `backend/tests/test_storage_reclamation_e2e.py`, `frontend/src/test/processesManager.test.tsx`, `frontend/src/test/storageReclamation.test.tsx` | 8/8 backend lifecycle tests, 4/4 backend storage tests, 9/9 frontend process manager tests, 2/2 frontend storage tests (100% pass) |
| S10-01 | Safe Website Data Reset & Storage Reclamation | Storage Core | Implemented | `backend/app/services/storage.py`, `scratch/safe_reset.py` | Full pre-reset inventory, timestamped safety backup, safe purge of 634 user files (1.77GB reclaimed) and 31 tables while preserving schema, migrations, settings, and default workspace |
| S10-02 | Concurrent Scene Thumbnail & Frame Extraction Optimization | Analysis Core | Implemented | `backend/app/services/scene_detector.py`, `backend/app/services/frame_sampler.py` | ThreadPoolExecutor parallelization across 6 workers reducing scene and frame thumbnail extraction runtime by ~5x on long-form media |
| S10-03 | Real Video End-to-End Pipeline Validation (`BLACK TORCH S01E02.mkv`) | Pipeline / Export | Implemented | `backend/scripts/`, `scratch/render_and_validate.py` | Validated full workflow on 24-minute Matroska video: HTTP upload, 17-stage analysis in 498.9s, candidate discovery across all creative directions/ratios, strict novelty Generate More, and clean renders (9:16, 1:1, 16:9) |
| S15-01 | Long-Video Endurance & Resilient Heartbeat Ticker Architecture | Intelligence Core | Implemented | `backend/app/services/analysis_pipeline.py` | Active progress callbacks bypass hard stage ceiling; speech transcription silence timeout increased to 600s; scene & frame extraction deadlines scaled proportionally to duration |
| S15-02 | Verified Job Completion Evidence Enforcement | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Raises `COMPLETION_EVIDENCE_MISSING` if output file does not physically exist or is 0 bytes |
| S15-03 | Cross-Table State Machine Synchronization | Jobs / Pipeline | Implemented | `backend/app/services/jobs.py` | Full synchronization of `analysis_runs` and `exports` upon job cancellation, failure, watchdog stall, or crash recovery |
| S15-04 | Duplicate Request Idempotency Guards | API / Services | Implemented | `backend/app/services/analysis_pipeline.py`, `backend/app/services/export_service.py`, `backend/app/api/v1/highlights.py` | Reuses existing active runs, renders, and candidate discovery jobs |
| S15-05 | Long-Operation Request Timeout Hardening | Frontend Client | Implemented | `frontend/src/services/apiClient.ts` | Increased highlight discovery timeouts to 300,000ms (5 minutes) |
| S15-06 | Comprehensive Endurance & Failure Recovery Test Suite | Testing / QA | Implemented | `backend/tests/test_session15_endurance_and_recovery.py` | 10/10 lifecycle scenarios passing (234 backend tests and 120 frontend tests pass) |

| ID | Feature / Capability | Module | Status | Planned Milestone |
|---|---|---|---|---|
| M14 | Interactive Reframing Review, Draggable Crop Canvas & Keyframe Diamonds (`ZEZ-050`–`054`) | Reframing Core | Planned | Milestone 14 |
| M15 | System Alerts, Resource Monitoring, In-App Documentation & AI Version Drawer | Shell / UI | Planned | Milestone 15 |
| M16 | Timeline Advanced Multi-Track Audio Mixing, Ducking & Karaoke Captions | Timeline Core | Planned | Milestone 16 |
| M17 | Full Regression Test Parity ($\ge 120$ Backend Tests, $\ge 85$ Frontend Tests) | Testing / QA | Planned | Milestone 17 |
| M18 | Real Vision & Face Detection Engine (YuNet ONNX / MobileFaceNet CPU Re-ID) | Vision Core | Planned | Milestone 18 |
| M19 | Performance Optimization & Hardware Acceleration (QuickSync / NVENC Presets) | Performance | Planned | Milestone 19 |
| M20 | Production Desktop Packaging & Offline Installer (Electron / Tauri Distribution) | Packaging | Planned | Milestone 20 |
