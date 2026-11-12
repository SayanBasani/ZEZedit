# Graph Report - ZezEdit  (2026-11-12)

## Corpus Check
- 184 files · ~271,507 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .xml 3, .example 1, (none) 1)

## Summary
- 3006 nodes · 8019 edges · 152 communities (115 shown, 37 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 915 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b590253`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- apiClient.ts
- App.tsx
- get_settings
- AppError
- projects.ts
- BackupService
- highlights.py
- AppError
- Button
- test_milestone24_timeline_operations_coverage.py
- config.py
- JobOrchestrator
- HighlightDiscoveryEngine
- CharacterCandidate
- NotFoundError
- subprocess
- ProjectService
- core.py
- v1/timeline.py
- v1/health.py
- sqlite_session
- CharacterService
- subprocess
- TimelineCommandService
- ExportStudio.tsx
- typing
- FramingEngine
- projects.ts
- ExportService
- get_health
- TimelineCommandService
- test_workflow_state_evaluation_lifecycle
- test_milestone9_timeline.py
- CharacterStudio.tsx
- NotFoundError
- ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification
- get
- ExportStudio.tsx
- Settings
- ProviderHealth
- create_app
- OllamaVisionAnalyzer
- SettingsManager.tsx
- characters.py
- ValidationError
- CharacterCandidate
- CaptionConfig
- character_service.py
- ZezEdit 2.0 — Local-First AI Video Editor
- characters.py
- test_candidate_human_review_workflow
- ZezEdit 2.0 — Feature Status Tracker
- VideoAnalysisPipeline
- ZezEdit 2.0 — Media Storage & Processing Pipeline
- error_envelope.schema.json
- 3. Core Functional Modules (A–J)
- ZezEdit — Pre-Deletion Baseline Reconstruction (November 11, 2026)
- ReframingService
- Unslop
- test_milestone2_core.py
- reframing_renderer.py
- .analyze_and_create_plan
- Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)
- test_character_library_and_export
- test_candidate_human_review_workflow
- Tokens
- ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library
- Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)
- pytest
- Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)
- WorkflowStateMachine
- README.md
- 6. Multiple Shorts Batch Export Engine
- Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)
- ZezEdit 2.0 — Milestone 13 Completion Report: ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan
- core.py
- .__init__
- VideoAnalysisPipeline
- entities.py
- OutputValidator
- v1/timeline.py
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- 3. Detailed Milestone Breakdown
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- character_service.py
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- ExportService
- character.py
- export.py
- run_migrations
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Authoritative Job Orchestration Design
- ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)
- compilerOptions
- ZezEdit 2.0 — Security & Data Safety Architecture
- 3. Sub-Workspace Breakdown
- Effects
- exports.py
- ZezEdit 2.0 — Security & Data Safety Architecture
- F. Test Evidence Summary
- 3. Detailed Specification by Domain
- BackupService
- JobOrchestrator
- .execute_render_job
- base.py
- character_env
- timeline_env
- delete_transcript_correction
- duration_sec
- height
- kind
- playhead_sec
- app/__init__.py
- v1/reframing.py
- ZezEdit 2.0 — Master Requirements Specification

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 181 edges
2. `request()` - 118 edges
3. `Settings` - 109 edges
4. `JobOrchestrator` - 79 edges
5. `StorageLayout` - 79 edges
6. `NotFoundError` - 78 edges
7. `get_settings()` - 70 edges
8. `AppError` - 68 edges
9. `TimelineCommandService` - 63 edges
10. `TimelineService` - 58 edges

## Surprising Connections (you probably didn't know these)
- `H. Frontend Restoration` --references--> `getSceneThumbnailUrl()`  [INFERRED]
  docs/reports/milestone_15_analysis_restoration_report.md → frontend/src/services/apiClient.ts
- `Milestone 2 — Core Backend, Database & Persistent Project Management` --references--> `BackupService`  [INFERRED]
  docs/feature_test_checklist.md → backend/app/services/backup_service.py
- `1. Core Mandate: One Single Job System` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/JOB_ORCHESTRATION.md → backend/app/services/jobs.py
- `Components` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/MEDIA_PIPELINE.md → backend/app/services/jobs.py
- `Domain G: Shorts Generation & FFmpeg Rendering` --references--> `JobOrchestrator`  [INFERRED]
  docs/reconstruction/FEATURE_PARITY_MATRIX.md → backend/app/services/jobs.py

## Import Cycles
- None detected.

## Communities (152 total, 37 thin omitted)

### Community 0 - "apiClient.ts"
Cohesion: 0.05
Nodes (93): CharacterStudio(), TimelineEditor(), addTimelineTextOverlay(), addTimelineTrack(), ApiClientError, approveAIPlan(), checkAssetIntegrity(), confirmCharacterCandidate() (+85 more)

### Community 1 - "App.tsx"
Cohesion: 0.08
Nodes (37): App(), NavSection, SidebarNavButton(), SidebarNavButtonProps, defaultToastValue, ToastAction, ToastCard(), ToastCardProps (+29 more)

### Community 2 - "get_settings"
Cohesion: 0.07
Nodes (24): get_settings_service(), get_analysis_pipeline(), get_db_path(), get_backup_service(), _check_storage_writable(), get_health(), get_system_diagnostics(), get_system_info() (+16 more)

### Community 3 - "AppError"
Cohesion: 0.09
Nodes (13): AppError, calculate_aspect_ratio(), MediaProbeResult, MediaStreamInfo, parse_fraction(), probe_media_file(), generate_proxy(), generate_thumbnail() (+5 more)

### Community 4 - "projects.ts"
Cohesion: 0.10
Nodes (24): `ZEZ-005`: Post-Import Guided Ingestion Flow, AnalysisWorkspaceProps, CharacterStudioProps, DashboardViewProps, ExportStudioProps, HighlightsWorkspaceProps, MediaLibraryViewProps, PostImportModalProps (+16 more)

### Community 5 - "BackupService"
Cohesion: 0.10
Nodes (6): create_backup(), restore_backup(), BackupService, storage_jobs_env(), test_sqlite_foreign_key_and_integrity_check(), test_sqlite_online_backup_generation()

### Community 6 - "highlights.py"
Cohesion: 0.09
Nodes (24): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, DiscoverHighlightsRequest, generate_more_highlights(), get_candidate_alternatives(), get_candidate_details() (+16 more)

### Community 7 - "AppError"
Cohesion: 0.05
Nodes (32): check_project_media_integrity(), delete_media(), generate_proxy_endpoint(), get_asset_integrity(), get_media(), get_media_global(), get_media_proxy_global(), get_media_stats() (+24 more)

### Community 8 - "Button"
Cohesion: 0.13
Nodes (37): Milestone 3 — Frontend Application Shell, Dashboard & Design System, Badge(), BadgeProps, Button(), ButtonProps, Card(), CardProps, ConfirmDialog() (+29 more)

### Community 9 - "test_milestone24_timeline_operations_coverage.py"
Cohesion: 0.11
Nodes (10): ValidationError, TrimClipRequest, UpdateClipPropsRequest, test_timeline_consecutive_undo_redo_stack(), test_timeline_duplicate_clip_naming_and_props(), test_timeline_new_command_clears_redo_history(), test_timeline_redo_empty_stack_validation(), test_timeline_trim_clip_bounds_and_duration() (+2 more)

### Community 10 - "config.py"
Cohesion: 0.08
Nodes (34): BatchExportModal(), BatchExportModalProps, HighlightsWorkspace(), approveCandidate(), bulkReviewCandidates(), discoverHighlights(), fetchCandidateAlternatives(), fetchProjectHighlights() (+26 more)

### Community 11 - "JobOrchestrator"
Cohesion: 0.08
Nodes (41): ResourceInspector(), DocumentationView(), AIProviderManager(), formatDuration(), StatusFilter, WorkingQueueView(), cancelJob(), fetchAIProviders() (+33 more)

### Community 12 - "HighlightDiscoveryEngine"
Cohesion: 0.08
Nodes (13): format_timestamp(), GeneratedCandidate, HighlightDiscoveryEngine, _now_utc(), QualityGateResult, ScoreBreakdown, main(), test_highlight_discovery_engine() (+5 more)

### Community 13 - "CharacterCandidate"
Cohesion: 0.14
Nodes (6): detach_observation(), list_candidates(), reject_candidate(), rename_candidate(), CharacterCandidate, CharacterObservation

### Community 14 - "NotFoundError"
Cohesion: 0.14
Nodes (21): AIConversation, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType, ContentProps, CreateTimelineRequest (+13 more)

### Community 15 - "subprocess"
Cohesion: 0.05
Nodes (39): ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream(), sample_analysis_frames(), SampledFrame (+31 more)

### Community 16 - "ProjectService"
Cohesion: 0.10
Nodes (14): archive_project(), create_project(), delete_project(), get_project(), get_project_events(), list_projects(), restore_project(), update_project() (+6 more)

### Community 17 - "core.py"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 18 - "v1/timeline.py"
Cohesion: 0.07
Nodes (15): add_text_overlay(), approve_plan(), create_timeline(), get_active_timeline(), get_ai_editor_service(), get_command_service(), get_timeline_service(), insert_clip() (+7 more)

### Community 19 - "v1/health.py"
Cohesion: 0.15
Nodes (8): DatabaseHealth, DependencyCheck, DiagnosticItem, HealthResponse, OllamaHealth, StorageHealth, SystemDiagnosticsResponse, SystemInfoResponse

### Community 20 - "sqlite_session"
Cohesion: 0.07
Nodes (18): BoundaryViolationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory(), validate_storage_root_path(), StorageLayout (+10 more)

### Community 21 - "CharacterService"
Cohesion: 0.13
Nodes (6): get_extraction_job(), run_character_extraction(), ExtractionJobConfig, ExtractionJobStatus, CharacterService, test_character_extraction_and_observations()

### Community 22 - "subprocess"
Cohesion: 0.06
Nodes (37): dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49 (+29 more)

### Community 23 - "TimelineCommandService"
Cohesion: 0.10
Nodes (6): delete_clip(), duplicate_clip(), get_history(), redo(), TimelineCommandService, test_timeline_split_clip_boundary_constraints()

### Community 24 - "ExportStudio.tsx"
Cohesion: 0.09
Nodes (7): get_ai_conversation(), get_plan(), list_plans(), reject_plan(), send_ai_message(), AIEditingPlan, AIEditorService

### Community 25 - "typing"
Cohesion: 0.06
Nodes (16): CropKeyframe, hex_to_ass_color(), build_crop_filter_expression(), ReframingRenderer, _simplify_keyframes(), test_export_delete_endpoint(), test_export_render_submission_and_query(), test_export_rest_api_list_presets() (+8 more)

### Community 26 - "FramingEngine"
Cohesion: 0.14
Nodes (5): FramingEngine, test_portrait_crop_geometry_and_bounds(), test_trajectory_smoothing_and_scene_cut_isolation(), `ZEZ-044`: Boundary Safety Containment (13M.12), 4. Features Already Restored in ZezEdit 2.0

### Community 27 - "projects.ts"
Cohesion: 0.16
Nodes (19): ReframingReviewModal(), ReframingWorkspace(), analyzeReframing(), fetchCropPreview(), fetchReframingRevisions(), getRenderedVideoUrl(), renderReframingRevision(), restoreReframingRevision() (+11 more)

### Community 28 - "ExportService"
Cohesion: 0.09
Nodes (46): 4. Post-Import Action Flow, AnalysisWorkspace(), AspectRatioOption, CREATIVE_DIRECTION_LABELS, CreativeDirectionOption, SingleVideoStudio(), STAGE_LABELS, VideoWorkspace() (+38 more)

### Community 29 - "get_health"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 30 - "TimelineCommandService"
Cohesion: 0.22
Nodes (5): get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 31 - "test_workflow_state_evaluation_lifecycle"
Cohesion: 0.23
Nodes (7): seed_analysis_run(), seed_candidate(), seed_export(), test_batch_export_endpoint_success(), test_batch_export_validation_and_skipped(), test_multi_video_data_isolation(), test_workflow_state_evaluation_lifecycle()

### Community 32 - "test_milestone9_timeline.py"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 33 - "CharacterStudio.tsx"
Cohesion: 0.07
Nodes (30): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+22 more)

### Community 34 - "NotFoundError"
Cohesion: 0.10
Nodes (13): add_track(), delete_track(), get_timeline(), update_timeline_settings(), NotFoundError, CreateTrackRequest, TimelineRecord, UpdateTimelineSettingsRequest (+5 more)

### Community 35 - "ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification"
Cohesion: 0.09
Nodes (21): A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, D. Audio and Transcription, Database Migration: `0010_transcript_corrections_and_audio.sql`, E. Scene Detection, F. Visual Understanding, Files Created, G. Temporal Context Aggregation (+13 more)

### Community 36 - "get"
Cohesion: 0.06
Nodes (33): AnalysisRunResponse, AudioAnalysisItem, create_or_update_transcript_correction(), delete_transcript_correction(), _format_run_response(), get_analysis_run(), get_audio_analysis(), get_context() (+25 more)

### Community 37 - "ExportStudio.tsx"
Cohesion: 0.18
Nodes (17): 7. Video Workspace Implementation, DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), cancelExportRender(), deleteExport(), fetchExportPresets(), getExportVideoUrl() (+9 more)

### Community 38 - "Settings"
Cohesion: 0.09
Nodes (5): Settings, WorkflowStage, client(), test_media_workflow_api_endpoint(), session4_env()

### Community 39 - "ProviderHealth"
Cohesion: 0.07
Nodes (23): ProviderHealth, SpeechToTextProvider, StructuredPlanResult, TextLLMProvider, VisionLanguageProvider, 1. Overview & Guiding Principles, 2. High-Level System Architecture, 3. Frontend Module Boundaries (`frontend/src/`) (+15 more)

### Community 40 - "create_app"
Cohesion: 0.05
Nodes (17): configure_logging(), create_app(), lifespan(), client(), test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint() (+9 more)

### Community 41 - "OllamaVisionAnalyzer"
Cohesion: 0.06
Nodes (27): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback(), 1. Backend Pytest Suite, 1. Character Extraction Studio & Character Library (Milestone 10), 2. Frontend Vitest Suite, 3. TypeScript Type Checking (+19 more)

### Community 42 - "SettingsManager.tsx"
Cohesion: 0.09
Nodes (28): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, ErrorBoundary, DEFAULT_THEME_CONTEXT, ThemeContext, ThemeContextType, ThemeMode (+20 more)

### Community 43 - "characters.py"
Cohesion: 0.16
Nodes (6): get_character_service(), get_library_character(), list_library_characters(), update_library_character(), CharacterProfile, UpdateProfileRequest

### Community 44 - "ValidationError"
Cohesion: 0.14
Nodes (9): AddTextOverlayRequest, InsertClipRequest, test_timeline_duration_auto_calculation(), test_timeline_text_overlay_creation_and_auto_track(), timeline_env(), test_ai_video_editor_assistant(), test_clip_operations_and_validation(), test_persistent_undo_and_redo() (+1 more)

### Community 45 - "CharacterCandidate"
Cohesion: 0.10
Nodes (20): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+12 more)

### Community 46 - "CaptionConfig"
Cohesion: 0.14
Nodes (6): CaptionEngine, format_ass_timestamp(), test_caption_engine_ass_file_generation_and_styling(), test_caption_engine_empty_segments(), test_format_ass_timestamp_precision(), test_caption_engine_ass_generation()

### Community 48 - "character_service.py"
Cohesion: 0.16
Nodes (6): export_character(), BoundingBox, CharacterExportPayload, DetectionType, RenameCandidateRequest, ReviewStatus

### Community 49 - "ZezEdit 2.0 — Local-First AI Video Editor"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 50 - "characters.py"
Cohesion: 0.11
Nodes (19): 1. Prerequisites, 2. Installation commands, 3. Environment and setup steps, 4. Exact Windows PowerShell backend startup commands, 5. Exact Windows PowerShell frontend startup commands, 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12 & 13), AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Architecture & Documentation (+11 more)

### Community 51 - "test_candidate_human_review_workflow"
Cohesion: 0.23
Nodes (5): merge_candidates(), split_candidate(), MergeCandidatesRequest, SplitCandidateRequest, test_candidate_human_review_workflow()

### Community 52 - "ZezEdit 2.0 — Feature Status Tracker"
Cohesion: 0.11
Nodes (18): ShortsCandidateRecord, AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Character Extraction Studio, Character Library & System Integration (Milestone 10), Core Backend, Database & Project Management (Milestone 2), Core Foundation & Architecture (Milestone 1), Core Product Workflow, Working Queue & Desktop Operations (Milestone 17), Frontend Application Shell, Dashboard & Design System (Milestone 3), Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11) (+10 more)

### Community 53 - "VideoAnalysisPipeline"
Cohesion: 0.08
Nodes (12): cancel_analysis(), get_analysis_cache(), get_analysis_telemetry(), retry_analysis(), _run_analysis_task(), start_analysis(), compute_source_signature(), _now_utc() (+4 more)

### Community 54 - "ZezEdit 2.0 — Media Storage & Processing Pipeline"
Cohesion: 0.11
Nodes (17): 1. Storage Separation & Source Immutability, 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First), 3. Smart Reframing & Portrait Rendering Architecture, 5. Milestone 4 Implementation Details: Media Ingestion & Proxies, 5. Video Analysis Engine (Milestone 5), 6. Smart Reframing & Dynamic Crop Renderer (Milestone 7), 7. Rendering Engine & Export Pipeline (Milestone 8), Authoritative Crop Math & Preview Parity (+9 more)

### Community 55 - "error_envelope.schema.json"
Cohesion: 0.11
Nodes (17): type, type, properties, required, type, type, properties, code (+9 more)

### Community 56 - "3. Core Functional Modules (A–J)"
Cohesion: 0.18
Nodes (5): _error_payload(), register_exception_handlers(), handle_app_error(), handle_unexpected_error(), handle_validation_error()

### Community 57 - "ZezEdit — Pre-Deletion Baseline Reconstruction (November 11, 2026)"
Cohesion: 0.14
Nodes (6): DetectedSubject, SubjectTrack, _compute_iou(), SubjectTracker, test_framing_strategies_single_two_person_and_group(), 2. Smart Reframing & Subject Tracking (Milestone 7)

### Community 58 - "ReframingService"
Cohesion: 0.14
Nodes (5): get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), preview_crop_geometry(), ReframingService

### Community 59 - "Unslop"
Cohesion: 0.12
Nodes (16): 1. Executive Summary & Historical Context, 2. Surviving Evidence Sources & Provenance, 3. Pre-Deletion Architecture & Data Flows, 4. Reconstructed Pre-Deletion Feature Inventory (20 Application Areas), 5. Milestone 13M.12 Deep-Dive Investigation, 6. Milestone 13M.13 Deep-Dive Investigation, 7. Historical UI Reconstruction, 8. Summary of Reconstructed Pre-Deletion Baseline (+8 more)

### Community 60 - "test_milestone2_core.py"
Cohesion: 0.12
Nodes (17): type, type, properties, type, type, type, type, clips (+9 more)

### Community 61 - "reframing_renderer.py"
Cohesion: 0.12
Nodes (16): 1. Spacing, 2. Color, 3. Icons, 4. Copy, 5. Type, 6. Layout, 7. Details, 8. Visuals (+8 more)

### Community 63 - "Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)"
Cohesion: 0.12
Nodes (16): type, exclusiveMinimum, type, type, properties, aspect_ratio, fps, project_id (+8 more)

### Community 64 - "test_character_library_and_export"
Cohesion: 0.32
Nodes (3): confirm_candidate(), ConfirmCandidateRequest, test_character_library_and_export()

### Community 65 - "test_candidate_human_review_workflow"
Cohesion: 0.12
Nodes (14): Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12), `ZEZ-049`: UI Tracking Status Pill (13M.12) (+6 more)

### Community 66 - "Tokens"
Cohesion: 0.14
Nodes (14): Accent, App layout, Buttons, Dark, Depth, Icons, Light, Motion (+6 more)

### Community 67 - "ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library"
Cohesion: 0.15
Nodes (6): 1. Overview & Principles, 2. Database Schema (Migration `0009_character_studio.sql`), 3. Human Review Operations, 4. Documented JSON Export Schema, Fundamental Constraints & Transparency Principles, ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library

### Community 68 - "Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)"
Cohesion: 0.18
Nodes (11): Domain J: System Infrastructure, Diagnostics & Reliability (`ZEZ-091` – `ZEZ-100`), `ZEZ-091`: Forward-Only Versioned SQLite Migrations, `ZEZ-092`: Pre-Migration Automatic Database Snapshot, `ZEZ-093`: Path Traversal & Anti-Root Recursive Deletion Guard, `ZEZ-094`: Single Authoritative Job Orchestrator & State Machine, `ZEZ-095`: Unclean Shutdown Recovery of Interrupted Jobs, `ZEZ-096`: Comprehensive Health & Diagnostics Probe (`/api/v1/health`), `ZEZ-097`: Graphify Knowledge Graph Auto-Maintenance (+3 more)

### Community 69 - "pytest"
Cohesion: 0.14
Nodes (14): Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`), `ZEZ-056`: Piecewise-Linear Dynamic FFmpeg Crop Filtergraph (13M.12), `ZEZ-057`: Burned-in Subtitles & Karaoke Word-Level ASS Styling, `ZEZ-058`: Professional Audio Processing & EBU R128 Loudness Normalization, `ZEZ-059`: Export Presets & Aspect Ratio Conversion, `ZEZ-060`: Strict Multi-Point Output Validation Gate, `ZEZ-061`: Poster Frame Cover Thumbnail Extraction, `ZEZ-062`: Render Progress Monitoring via FFmpeg `-progress` Pipe (+6 more)

### Community 70 - "Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)"
Cohesion: 0.14
Nodes (13): 10. Test and Acceptance Criteria, 11. Current Verified Restoration Coverage, 12. Recommended Next Implementation Milestone, 1. ZezEdit 1.0 Feature Inventory, 2. Historical Evidence References, 3. Exact Parity Requirements Identified, 5. Missing Functionality (Parity Gap), 6. Features That Cannot Be Recovered With Available Evidence (+5 more)

### Community 71 - "WorkflowStateMachine"
Cohesion: 0.16
Nodes (6): VideoWorkflowStateResponse, WorkflowStateMachine, Milestone 18: Unified Video-to-Shorts Production Pipeline Checklist, 1. Executive Summary, 23. Graphify Knowledge Graph & Topological Codebase Health, 4. Authoritative Workflow Lifecycle State Machine

### Community 72 - "README.md"
Cohesion: 0.20
Nodes (10): Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`), `ZEZ-021`: Automated Audio Extraction for ASR, `ZEZ-022`: Faster-Whisper Local Speech Transcription, `ZEZ-023`: Word-Level Timestamp Alignment, `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer, `ZEZ-026`: FFmpeg Visual Scene Cut Detection, `ZEZ-027`: Keyframe Visual Lightbox & Filmstrip, `ZEZ-028`: Interval Frame Sampling for Visual Understanding (+2 more)

### Community 73 - "6. Multiple Shorts Batch Export Engine"
Cohesion: 0.50
Nodes (4): 6. Multiple Shorts Batch Export Engine, Batch Export Request Payload:, Batch Export Response Payload:, Output File Organization:

### Community 74 - "Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)"
Cohesion: 0.15
Nodes (12): 1. Parity Metrics & Scorecard Summary, 2. Complete 100-Requirement Parity Matrix, Domain A: Application Shell, Dashboard & Navigation, Domain B: Media Management, Proxies & Storage, Domain C: Video Analysis & Speech Understanding, Domain D & E: AI Multimodal Understanding & Highlight Discovery, Domain F: Smart Reframing & Subject Tracking (13M.12/13M.13), Domain G: Shorts Generation & FFmpeg Rendering (+4 more)

### Community 75 - "ZezEdit 2.0 — Milestone 13 Completion Report: ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan"
Cohesion: 0.15
Nodes (13): Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`), `ZEZ-069`: Multi-Track Timeline NLE Canvas, `ZEZ-070`: Non-Destructive Clip Trimming & Splitting, `ZEZ-071`: Ripple Delete & Gap Closing, `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing, `ZEZ-073`: Persistent Timeline Undo & Redo History, `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration, `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`) (+5 more)

### Community 76 - "core.py"
Cohesion: 0.07
Nodes (33): list_ai_providers(), test_ai_provider(), update_ai_provider(), get_doc_article(), list_doc_articles(), list_doc_categories(), AIProviderCapability, AIProviderDTO (+25 more)

### Community 78 - ".__init__"
Cohesion: 0.17
Nodes (12): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 15: Video Analysis, AI Understanding & Temporal Context Restoration Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification (+4 more)

### Community 79 - "VideoAnalysisPipeline"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 80 - "entities.py"
Cohesion: 0.16
Nodes (10): AnalysisRunRecord, CandidateGenerationRunRecord, MediaGeneratedClipHistoryRecord, ProjectEventRecord, SampledFrameRecord, SpeechTurnRecord, TranscriptSegmentRecord, VideoSceneRecord (+2 more)

### Community 81 - "OutputValidator"
Cohesion: 0.15
Nodes (7): ValidationDetails, OutputValidator, test_output_validator_success_and_tampered_metadata(), test_output_validator_gate(), AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), Milestone 9: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing Checklist, AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

### Community 82 - "v1/timeline.py"
Cohesion: 0.08
Nodes (14): get_timeline_renderer(), render_timeline(), _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models, 2. `timeline_tracks` Table (+6 more)

### Community 83 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.18
Nodes (10): 1. Executive Summary, 2. Unslop Visual & Interaction Audit, 3. Product Workflow Gap Analysis, 4. Feature Recovery Matrix, 5. Unslop Design Direction for ZezEdit 2.0, A. Surfaces and Colors, B. Typography & Copy, Current Broken Workflow: (+2 more)

### Community 84 - "3. Detailed Milestone Breakdown"
Cohesion: 0.18
Nodes (11): 3. Core Functional Modules (A–J), Module A — Dashboard & Project Management, Module B — Media Library, Module C — Video Analysis, Module D — Highlight Discovery, Module E — Smart Reframing, Module F — Multi-Track Timeline Editor, Module G — AI Video Editor (+3 more)

### Community 85 - "Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)"
Cohesion: 0.18
Nodes (10): 1. Roadmap Architecture & Execution Principles, 2. Master Implementation Milestone Schedule, 3. Detailed Milestone Breakdown, Milestone 13: Exact Parity Specification & Pre-Deletion Architecture, Milestone 14: Interactive Reframing Review, Draggable Canvas & Keyframe Diamonds, Milestone 15: Video Analysis, AI Understanding & Temporal Context Restoration, Milestone 16: Multi-Track Timeline Audio Waveforms, Ducking & Word-Level Karaoke, Milestone 17: Core Product Workflow, Working Queue & Desktop Operations (+2 more)

### Community 86 - "Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)"
Cohesion: 0.20
Nodes (10): Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`), `ZEZ-001`: Studio Application Shell & Responsive Drawer, `ZEZ-002`: Studio Dashboard View, `ZEZ-003`: Project Management & Lifecycle Operations, `ZEZ-004`: Unified Video Workspace Navigation, `ZEZ-006`: System Monitor & Hardware Resource Widget, `ZEZ-007`: Studio Light / Dark Theme Synchronization, `ZEZ-008`: Notification Center & Job Completion Toasts (+2 more)

### Community 87 - "Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)"
Cohesion: 0.18
Nodes (11): Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`), `ZEZ-011`: Video Drag-and-Drop & File Picker Ingestion, `ZEZ-012`: Automated FFprobe Container & Stream Dissection, `ZEZ-013`: Fast Edit Proxy Generation (480p), `ZEZ-014`: Poster Frame & Thumbnail Strip Generation, `ZEZ-015`: Audio File Ingestion & Waveform Prep, `ZEZ-016`: Image File Ingestion for Overlays & Watermarks, `ZEZ-017`: Safe Isolated Storage Layout (+3 more)

### Community 88 - "character_service.py"
Cohesion: 0.18
Nodes (11): Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`), `ZEZ-031`: Local Multimodal Vision Integration (Ollama), `ZEZ-032`: Multimodal Context Aggregator, `ZEZ-033`: Explainable 9-Factor Highlight Scoring Engine, `ZEZ-034`: Narrative Setup and Payoff Boundary Preservation, `ZEZ-035`: Categorized Shorts Candidate Ranking, `ZEZ-036`: Hook Rationale & Explanation Card, `ZEZ-037`: Candidate Review & Approval Workflow (+3 more)

### Community 89 - "._generate_thumbnail"
Cohesion: 0.18
Nodes (11): Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`), `ZEZ-081`: Evidence-Based Character Extraction Pipeline (Non-3D), `ZEZ-082`: Spatial-Temporal Candidate Clustering (DBSCAN), `ZEZ-083`: Character Observation Gallery & Thumbnails, `ZEZ-084`: Screen-Time Transparency Analytics, `ZEZ-085`: Unverified Dialogue Correlation with Disclaimer, `ZEZ-086`: Human Review Controls: Inline Renaming, `ZEZ-087`: Human Review Controls: Confirm to Persistent Character Library (+3 more)

### Community 90 - "ZezEdit 2.0 — API Design & Conventions"
Cohesion: 0.20
Nodes (9): 1. API Versioning & Base Prefix, 2. Resource Naming & HTTP Method Conventions, 3. Standard Request & Response Conventions, 4. Implemented vs Planned Endpoint Inventory, Centralized Error Response Contract, Implemented in Milestones 1–6, Planned Endpoints (Milestones 10–12), Success Envelopes (+1 more)

### Community 91 - "ExportService"
Cohesion: 0.09
Nodes (10): delete_export(), get_export_details(), get_export_service(), list_export_presets(), list_exports(), stream_export_video(), ExportPreset, ExportRecord (+2 more)

### Community 93 - "character.py"
Cohesion: 0.22
Nodes (8): 1. Engine & Pragmas, 2. Versioned Migration Strategy (Historical Lesson Applied), 3. Planned Domain Entity Relationship Diagram, 4. Schema Breakdown: Implemented vs Planned, 5. Limitations & Alternatives Considered, Implemented Tables (Migrations 0001–0005), Planned Tables for Subsequent Milestones (Schema Blueprint), ZezEdit 2.0 — Database Design & Migration Strategy

### Community 94 - "export.py"
Cohesion: 0.22
Nodes (8): 1. Core Mandate: One Single Job System, 2. Job States & Lifecycle Transitions, 3. Canonical Job Types & Concurrency Policy, 4. Worker Ownership & Child Process PID Registry, 5. Restart Recovery Rules, 6. Retry Rules & Per-Job Logs, 7. Alternatives Considered & Limitations, ZezEdit 2.0 — Authoritative Job Orchestration Design

### Community 95 - "run_migrations"
Cohesion: 0.04
Nodes (19): MigrationError, _backup_before_upgrade(), _file_sha256(), MigrationResult, _parse_version_and_name(), run_migrations(), character_env(), test_character_api_routes() (+11 more)

### Community 96 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.22
Nodes (8): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, strict, include

### Community 98 - "ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)"
Cohesion: 0.29
Nodes (7): Dithering, Duotone, Effects, Glyphs, Halftone dots, Implementation, Performance

### Community 99 - "compilerOptions"
Cohesion: 0.29
Nodes (7): Decide what the visual is, Generate it, Objects for moments, Prompt recipe, Put it on the page, Styles that work, Visuals

### Community 102 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.29
Nodes (6): 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction, 4. Export Overwrite & Confirmation Rules, 5. AI Video Editor Security Boundary, 6. Backup & Restore Strategy, ZezEdit 2.0 — Security & Data Safety Architecture

### Community 103 - "3. Sub-Workspace Breakdown"
Cohesion: 0.12
Nodes (15): 1. Overview, 1. Overview Tab, 2. Analysis Tab, 2. Context & State Flow, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Scenes Tab, 5. AI Highlights Tab (+7 more)

### Community 104 - "Effects"
Cohesion: 0.29
Nodes (6): 1. Product Vision & Mission Statement, 2. Requirement Taxonomy & Numbering, 3. Detailed Specification by Domain, 4. Summary Parity Ledger, Core Architecture Axioms, ZezEdit 1.0 — Exact Product Parity Specification

### Community 105 - "exports.py"
Cohesion: 0.13
Nodes (10): BatchExportItem, BatchExportRequest, BatchExportResponse, cancel_export(), create_batch_export_jobs(), create_export_preview(), create_export_render_job(), CaptionConfig (+2 more)

### Community 106 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 107 - "F. Test Evidence Summary"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 108 - "3. Detailed Specification by Domain"
Cohesion: 0.40
Nodes (5): required, type, tracks, items, type

### Community 109 - "BackupService"
Cohesion: 0.06
Nodes (19): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, create_backup_endpoint(), execute_cleanup_endpoint(), get_capabilities_endpoint(), get_db_integrity_endpoint(), get_recovery_status_endpoint() (+11 more)

### Community 110 - "JobOrchestrator"
Cohesion: 0.06
Nodes (25): cancel_job(), create_job(), get_job(), get_job_checkpoint(), get_job_logs(), get_queue_stats(), list_jobs(), retry_job() (+17 more)

### Community 112 - ".execute_render_job"
Cohesion: 0.16
Nodes (5): AudioConfig, AudioPipeline, test_audio_pipeline_loudnorm_and_volume_filter_chains(), test_audio_pipeline_filters(), test_full_export_render_and_validation()

### Community 114 - "base.py"
Cohesion: 0.67
Nodes (3): minimum, type, duration_sec

### Community 115 - "character_env"
Cohesion: 0.67
Nodes (3): minimum, type, height

### Community 116 - "timeline_env"
Cohesion: 0.67
Nodes (3): enum, type, kind

### Community 117 - "delete_transcript_correction"
Cohesion: 0.67
Nodes (3): minimum, type, playhead_sec

### Community 118 - "duration_sec"
Cohesion: 0.67
Nodes (3): schema_version, const, type

### Community 119 - "height"
Cohesion: 0.67
Nodes (3): source_kind, enum, type

### Community 120 - "kind"
Cohesion: 0.67
Nodes (3): width, minimum, type

### Community 121 - "playhead_sec"
Cohesion: 0.67
Nodes (3): zoom_px_per_sec, minimum, type

### Community 135 - "v1/reframing.py"
Cohesion: 0.19
Nodes (7): create_reframing_plan(), CreateReframingPlanRequest, render_reframed_video(), RenderRevisionRequest, restore_reframing_revision(), save_manual_overrides(), SaveOverridesRequest

### Community 139 - "ZezEdit 2.0 — Master Requirements Specification"
Cohesion: 0.33
Nodes (5): 1. Mission & Product Vision, 2. Hardware & Resource Constraints (Mandatory), 4. Mandatory Data Protection & Reliability Rules, 5. Planned Milestone Sequence, ZezEdit 2.0 — Master Requirements Specification

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1367 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `JobOrchestrator` to `get_settings`, `AppError`, `BackupService`, `highlights.py`, `AppError`, `HighlightDiscoveryEngine`, `NotFoundError`, `subprocess`, `v1/health.py`, `sqlite_session`, `typing`, `Settings`, `ProviderHealth`, `create_app`, `OllamaVisionAnalyzer`, `VideoAnalysisPipeline`, `ZezEdit 2.0 — Media Storage & Processing Pipeline`, `Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)`, `pytest`, `Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)`, `entities.py`, `v1/timeline.py`, `ExportService`, `export.py`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `apiClient.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.050475635798874006 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `pytest` to `ExportStudio.tsx`, `JobOrchestrator`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `cancel_job()`) actually correct?**
  _`JobOrchestrator` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.08080808080808081 - nodes in this community are weakly interconnected._