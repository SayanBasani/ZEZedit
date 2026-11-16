# Graph Report - ZezEdit  (2026-11-16)

## Corpus Check
- 268 files · ~502,961 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .xml 3, .bat 2, .example 1)

## Summary
- 4044 nodes · 11714 edges · 159 communities (123 shown, 36 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1265 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ab2e73f5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Settings
- StorageLayout
- subprocess
- CharacterService
- pathlib
- Button
- SettingsManager.tsx
- create_app
- Button
- create_app
- core.py
- AppError
- analysis.py
- test_process_manager_lifecycle.py
- highlights.py
- test_p0_9_restart_and_persistence.py
- ProjectService
- VideoAnalysisPipeline
- test_milestone9_timeline.py
- ExportService
- HighlightDiscoveryEngine
- subprocess
- export_service.py
- v1/media.py
- test_milestone24_export_pipeline_coverage.py
- TimelineCommandService
- start_highlight_discovery
- FramingEngine
- settings.py
- core.py
- v1/media.py
- JobOrchestrator
- NotFoundError
- projects.ts
- post
- TimelineCommandService
- time
- .get_job
- settings.py
- sqlite_session
- ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration
- sqlite3
- test_foundation.py
- .claim_next_queued_job
- v1/projects.py
- ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report
- .import_uploaded_media
- test_milestone4_media.py
- OllamaProvider
- v1/timeline.py
- .__init__
- analysis.py
- TimelineRenderer
- test_p1_3_large_upload_streaming.py
- error_envelope.schema.json
- socket
- MediaPipelineService
- Unslop
- .get_database_diagnostics
- reframing_renderer.py
- test_p0_7_windows_launcher_reliability.py
- ZezEdit 2.0 — Milestone 11 Completion Report: Graphify Integration, Unslop UI Redesign, Video-Centric Workspace & Feature Recovery
- ReframingWorkspace.tsx
- test_candidate_human_review_workflow
- Tokens
- preview_user_data_cleanup_endpoint
- CDPBrowser
- ZezEdit 2.0 — System Architecture
- Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)
- MediaService
- Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)
- ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library
- error_envelope.schema.json
- ._terminate_pid_tree
- 2. Complete 100-Requirement Parity Matrix
- Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)
- README.md
- OllamaVisionAnalyzer
- 3. Sub-Workspace Breakdown
- ai_providers.py
- ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis
- m15_env
- run_p0_9_demos.py
- Tokens
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- sample_videos
- Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)
- character.py
- CDPBrowser
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Database Design & Migration Strategy
- 2. Complete 100-Requirement Parity Matrix
- Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)
- CDPBrowser
- SKILL.md
- test_session5_clip_editing.py
- README.md
- ZezEdit 2.0 — Security & Data Safety Architecture
- Signs of slop
- ZezEdit 2.0 — Master Requirements Specification
- ZezEdit 2.0 — Security & Data Safety Architecture
- F. Test Evidence Summary
- 3. Core Functional Modules (A–J)
- 3. Detailed Milestone Breakdown
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Any
- ReframingRenderer
- base.py
- test_milestone19_desktop_operations.py
- test_reconciliation_transaction_rollback_on_interruption
- test_download_filename_derived_from_content_title
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Authoritative Job Orchestration Design
- schema_version
- width
- zoom_px_per_sec
- api/__init__.py
- .cors_origin_list
- .ensure_directories
- tailwind.config.js
- Path
- zezedit-backend
- ProcessMemoryMonitor
- timeline_document.schema.json
- FastAPI
- postcss.config.js
- vite-env.d.ts
- run_migrations
- Settings
- zezedit-backend
- test_concurrent_reconciliation_requests
- duration_sec
- kind
- playhead_sec
- schema_version
- source_kind
- width
- zoom_px_per_sec
- api/__init__.py
- core/__init__.py
- Stop-ZEZEdit.ps1

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 280 edges
2. `Settings` - 200 edges
3. `JobOrchestrator` - 164 edges
4. `request()` - 132 edges
5. `create_app()` - 105 edges
6. `StorageLayout` - 103 edges
7. `run_migrations()` - 94 edges
8. `AppError` - 92 edges
9. `get_settings()` - 85 edges
10. `NotFoundError` - 77 edges

## Surprising Connections (you probably didn't know these)
- ``ZEZ-018`: External Media Relinking & Missing File Detection` --references--> `MediaPipelineService`  [INFERRED]
  docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md → backend/app/services/media_pipeline.py
- `H. Frontend Restoration` --references--> `getSceneThumbnailUrl()`  [INFERRED]
  docs/reports/milestone_15_analysis_restoration_report.md → frontend/src/services/apiClient.ts
- ``ZEZ-020`: Media Organization, Tags & Search` --references--> `MediaAssetItem`  [INFERRED]
  docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md → frontend/src/types/projects.ts
- `Domain B: Media Management, Proxies & Storage` --references--> `StorageLayout`  [INFERRED]
  docs/reconstruction/FEATURE_PARITY_MATRIX.md → backend/app/core/storage.py
- `Centralized Error Response Contract` --references--> `AppError`  [INFERRED]
  docs/architecture/API_DESIGN.md → backend/app/core/errors.py

## Import Cycles
- None detected.

## Communities (159 total, 36 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.03
Nodes (27): StorageLayout, WorkflowStage, test_media_workflow_api_endpoint(), test_temp_cache_cleanup_invalid_token_rejected(), test_diagnostics_endpoint_reporting(), test_foreign_key_enforcement_across_independent_connections(), test_foreign_key_enforcement_on_connection(), test_02_foreign_key_enforcement_after_restart() (+19 more)

### Community 1 - "StorageLayout"
Cohesion: 0.04
Nodes (40): ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream(), sample_analysis_frames(), _sample_one() (+32 more)

### Community 2 - "subprocess"
Cohesion: 0.10
Nodes (26): BinaryStatus, probe_media_binary(), create_synthetic_mp4(), create_synthetic_mp4(), run_demos(), create_synthetic_mp4(), run_demos(), create_synthetic_mp4() (+18 more)

### Community 3 - "CharacterService"
Cohesion: 0.04
Nodes (30): CropKeyframe, DetectedSubject, SubjectTrack, FramingEngine, build_crop_filter_expression(), _simplify_keyframes(), _compute_iou(), SubjectTracker (+22 more)

### Community 4 - "pathlib"
Cohesion: 0.05
Nodes (104): CharacterStudio(), ProjectsView(), TimelineEditor(), addTimelineTextOverlay(), addTimelineTrack(), approveAIPlan(), archiveProject(), buildMediaQueryParams() (+96 more)

### Community 5 - "Button"
Cohesion: 0.05
Nodes (33): confirm_candidate(), detach_observation(), export_character(), get_character_service(), get_extraction_job(), get_library_character(), list_candidates(), list_library_characters() (+25 more)

### Community 6 - "SettingsManager.tsx"
Cohesion: 0.10
Nodes (46): Milestone 3 — Frontend Application Shell, Dashboard & Design System, BadgeProps, Button(), ButtonProps, Card(), CardProps, ConfirmDialog(), ConfirmDialogProps (+38 more)

### Community 7 - "create_app"
Cohesion: 0.05
Nodes (18): configure_logging(), create_app(), client(), test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint(), client() (+10 more)

### Community 8 - "Button"
Cohesion: 0.05
Nodes (86): 4. Post-Import Action Flow, Badge(), AnalysisWorkspace(), BatchExportModal(), DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), ExportStudioProps (+78 more)

### Community 9 - "create_app"
Cohesion: 0.05
Nodes (60): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, App(), NavSection, SidebarNavButton(), SidebarNavButtonProps, defaultToastValue (+52 more)

### Community 10 - "core.py"
Cohesion: 0.13
Nodes (25): test_ai_provider(), AIProviderCapability, AIProviderDTO, AIProviderTestRequest, AIProviderTestResponse, AIProviderUpdateRequest, AppSettingsUpdateRequest, CapabilitiesResponse (+17 more)

### Community 11 - "AppError"
Cohesion: 0.05
Nodes (18): delete_media(), delete_media_global(), get_media_proxy_global(), get_media_thumbnail_global(), get_proxy_file(), get_thumbnail_file(), AppError, calculate_aspect_ratio() (+10 more)

### Community 12 - "analysis.py"
Cohesion: 0.08
Nodes (45): ResourceInspector(), DocumentationView(), AIProviderManager(), categorizeJobType(), CategoryFilter, formatDuration(), formatTimeOnly(), ProcessesManagerView (+37 more)

### Community 13 - "test_process_manager_lifecycle.py"
Cohesion: 0.06
Nodes (23): get_analysis_telemetry(), compute_source_signature(), _heartbeat_ticker(), _ticker(), _now_utc(), VideoAnalysisPipeline, on_transcribe_progress(), _worker() (+15 more)

### Community 14 - "highlights.py"
Cohesion: 0.05
Nodes (22): BatchExportItem, BatchExportRequest, BatchExportResponse, cancel_export(), create_batch_export_jobs(), create_export_preview(), create_export_render_job(), delete_export() (+14 more)

### Community 15 - "test_p0_9_restart_and_persistence.py"
Cohesion: 0.08
Nodes (26): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, CandidateResponse, delete_candidate(), DiscoverHighlightsRequest, generate_more_highlights() (+18 more)

### Community 16 - "ProjectService"
Cohesion: 0.03
Nodes (35): import_local_file_global(), upload_media_batch_global(), upload_media_file(), upload_media_file_global(), delete_project(), AnalysisRunRecord, CandidateClipEditRecord, MediaAssetRecord (+27 more)

### Community 17 - "VideoAnalysisPipeline"
Cohesion: 0.11
Nodes (14): BoundaryViolationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory(), validate_storage_root_path(), test_health_and_system_info_endpoints() (+6 more)

### Community 18 - "test_milestone9_timeline.py"
Cohesion: 0.07
Nodes (17): format_timestamp(), GeneratedCandidate, HighlightDiscoveryEngine, _now_utc(), QualityGateResult, ScoreBreakdown, main(), test_highlight_discovery_engine() (+9 more)

### Community 19 - "ExportService"
Cohesion: 0.06
Nodes (24): get_settings_service(), get_analysis_pipeline(), get_db_path(), get_backup_service(), get_clip_editing_service(), get_export_service(), get_db_path(), get_discovery_engine() (+16 more)

### Community 20 - "HighlightDiscoveryEngine"
Cohesion: 0.09
Nodes (16): add_track(), delete_track(), get_active_timeline(), update_timeline_settings(), update_track(), NotFoundError, CreateTimelineRequest, CreateTrackRequest (+8 more)

### Community 21 - "subprocess"
Cohesion: 0.07
Nodes (40): 7. Video Workspace Implementation, BatchExportModalProps, HighlightsWorkspace(), ASPECT_RATIO_OPTIONS, CandidateClipEditorModal(), CandidateClipEditorModalProps, formatTimecode(), approveCandidate() (+32 more)

### Community 22 - "export_service.py"
Cohesion: 0.04
Nodes (28): AudioConfig, ExportPreset, ExportRecord, ValidationDetails, AudioPipeline, CaptionEngine, format_ass_timestamp(), hex_to_ass_color() (+20 more)

### Community 23 - "v1/media.py"
Cohesion: 0.08
Nodes (25): check_project_media_integrity(), generate_proxy_endpoint(), get_asset_integrity(), get_media(), get_media_global(), get_media_stats(), import_local_file(), inspect_relink() (+17 more)

### Community 24 - "test_milestone24_export_pipeline_coverage.py"
Cohesion: 0.07
Nodes (18): add_text_overlay(), approve_plan(), create_timeline(), delete_clip(), duplicate_clip(), get_ai_editor_service(), get_command_service(), get_timeline() (+10 more)

### Community 25 - "TimelineCommandService"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 26 - "start_highlight_discovery"
Cohesion: 0.04
Nodes (27): sqlite_session(), get_temporal_context_at(), TemporalContext, test_migration_and_foreign_keys(), test_temporal_aggregator_query(), test_export_deletion_preserves_candidate_and_media(), test_invalid_out_of_root_path_rejection(), test_missing_export_file_behavior() (+19 more)

### Community 27 - "FramingEngine"
Cohesion: 0.06
Nodes (37): dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49 (+29 more)

### Community 28 - "settings.py"
Cohesion: 0.06
Nodes (24): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, clear_all_user_data_endpoint(), ClearAllDataRequest, create_backup_endpoint(), execute_cleanup_endpoint(), get_db_integrity_endpoint() (+16 more)

### Community 29 - "core.py"
Cohesion: 0.08
Nodes (6): get_ai_conversation(), get_history(), get_plan(), list_plans(), send_ai_message(), AIEditorService

### Community 30 - "v1/media.py"
Cohesion: 0.06
Nodes (28): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback(), 1. Backend Pytest Suite, 1. Character Extraction Studio & Character Library (Milestone 10), 2. Frontend Vitest Suite, 2. Smart Reframing & Subject Tracking (Milestone 7) (+20 more)

### Community 31 - "JobOrchestrator"
Cohesion: 0.06
Nodes (43): lifespan(), _queue_poller(), JobRecord, JobOrchestrator, run_all_demos(), run_phase_e(), run_phase_f(), test_job_retry_lifecycle_and_event_timeline() (+35 more)

### Community 32 - "NotFoundError"
Cohesion: 0.10
Nodes (15): _check_storage_writable(), get_health(), get_system_diagnostics(), get_system_info(), get_system_resources(), get_capabilities_endpoint(), OllamaProvider, DatabaseHealth (+7 more)

### Community 33 - "projects.ts"
Cohesion: 0.06
Nodes (45): `ZEZ-005`: Post-Import Guided Ingestion Flow, AnalysisWorkspaceProps, CharacterStudioProps, HighlightsWorkspaceProps, PostImportModalProps, ReframingReviewModalProps, ReframingWorkspaceProps, SingleVideoStudioProps (+37 more)

### Community 34 - "post"
Cohesion: 0.15
Nodes (17): AIConversation, AIEditingPlan, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType, ContentProps (+9 more)

### Community 36 - "TimelineCommandService"
Cohesion: 0.08
Nodes (16): insert_clip(), ValidationError, AddTextOverlayRequest, InsertClipRequest, MoveClipRequest, SplitClipRequest, TrimClipRequest, TimelineCommandService (+8 more)

### Community 37 - "time"
Cohesion: 0.11
Nodes (27): create_sqlite_connection(), compute_sha256(), http_get(), is_port_listening(), log_demo(), run_all(), run_phase_c(), run_phase_d() (+19 more)

### Community 38 - ".get_job"
Cohesion: 0.07
Nodes (27): CandidateEditSaveRequest, get_candidate_edit(), reset_candidate_edit(), save_candidate_edit(), track_candidate_subjects(), TrackCandidateRequest, ClipEditingService, _setup_test_env() (+19 more)

### Community 39 - "settings.py"
Cohesion: 0.05
Nodes (12): log_demo(), run_all_demos(), client_with_clean_storage(), media_env(), analysis_env(), highlights_env(), reframing_env(), isolated_env() (+4 more)

### Community 40 - "sqlite_session"
Cohesion: 0.12
Nodes (12): audit(), compute_sha256(), establish_baseline(), get_git_info(), _setup_test_orchestrator(), test_active_external_child_pid_never_marked_stalled_within_grace(), test_checkpoint_never_heals_failed_status(), test_complete_job_rejects_failed_status() (+4 more)

### Community 41 - "ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration"
Cohesion: 0.16
Nodes (6): create_backup(), restore_backup(), BackupService, test_sqlite_online_backup_generation(), test_05_backup_integrity(), test_06_restore_into_isolated_location()

### Community 42 - "sqlite3"
Cohesion: 0.11
Nodes (12): cancel_job(), create_job(), delete_job(), delete_jobs_history(), _enrich_job_response(), get_job(), get_job_checkpoint(), get_job_logs() (+4 more)

### Community 43 - "test_foundation.py"
Cohesion: 0.14
Nodes (8): ProviderHealth, SpeechToTextProvider, StructuredPlanResult, TextLLMProvider, VisionLanguageProvider, 4. Backend Module Boundaries (`backend/app/`), 5. AI Provider Abstraction Boundaries, ADR-05: Dynamic Authoritative AI Provider Abstraction

### Community 44 - ".claim_next_queued_job"
Cohesion: 0.12
Nodes (4): test_resource_aware_scheduler_and_priority(), test_10_duplicate_job_prevention(), test_atomic_job_claiming_guarantee(), worker_claim()

### Community 45 - "v1/projects.py"
Cohesion: 0.22
Nodes (12): archive_project(), create_project(), get_project(), get_project_events(), list_projects(), restore_project(), update_project(), ProjectCreateRequest (+4 more)

### Community 46 - "ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 47 - ".import_uploaded_media"
Cohesion: 0.10
Nodes (9): UpdateClipPropsRequest, test_timeline_consecutive_undo_redo_stack(), test_timeline_duplicate_clip_naming_and_props(), test_timeline_new_command_clears_redo_history(), test_timeline_redo_empty_stack_validation(), test_timeline_text_overlay_creation_and_auto_track(), test_timeline_track_deletion_and_clip_cascade(), test_timeline_undo_empty_stack_validation() (+1 more)

### Community 48 - "test_milestone4_media.py"
Cohesion: 0.14
Nodes (7): list_ai_providers(), update_ai_provider(), get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 49 - "OllamaProvider"
Cohesion: 0.09
Nodes (13): render_timeline(), _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models, 2. `timeline_tracks` Table, 3. Persistent Reversible Command System (Undo / Redo) (+5 more)

### Community 50 - "v1/timeline.py"
Cohesion: 0.07
Nodes (30): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+22 more)

### Community 51 - ".__init__"
Cohesion: 0.18
Nodes (5): _error_payload(), register_exception_handlers(), handle_app_error(), handle_unexpected_error(), handle_validation_error()

### Community 52 - "analysis.py"
Cohesion: 0.06
Nodes (30): AnalysisRunResponse, AudioAnalysisItem, cancel_analysis(), create_or_update_transcript_correction(), delete_transcript_correction(), _format_run_response(), get_analysis_cache(), get_analysis_run() (+22 more)

### Community 53 - "TimelineRenderer"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 54 - "test_p1_3_large_upload_streaming.py"
Cohesion: 0.08
Nodes (14): create_reframing_plan(), CreateReframingPlanRequest, get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), ManualOverrideItem, preview_crop_geometry(), render_reframed_video() (+6 more)

### Community 55 - "error_envelope.schema.json"
Cohesion: 0.23
Nodes (21): _setup_test_orchestrator(), test_01_valid_job_state_transitions(), test_02_invalid_terminal_state_transitions(), test_03_cancellation_before_execution_starts(), test_04_cancellation_during_running_python_task(), test_05_cancellation_during_ffmpeg_subprocess(), test_06_confirmation_canceled_child_processes_exit(), test_07_no_orphan_subprocesses_after_cancellation() (+13 more)

### Community 57 - "socket"
Cohesion: 0.27
Nodes (7): query_health(), run_all_demos(), run_command(), http_request(), is_port_listening(), run_all_demos(), run_command()

### Community 58 - "MediaPipelineService"
Cohesion: 0.10
Nodes (20): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+12 more)

### Community 59 - "Unslop"
Cohesion: 0.16
Nodes (20): ReframingReviewModal(), ReframingWorkspace(), analyzeReframing(), fetchCropPreview(), fetchReframingRevisions(), getProxyUrl(), getRenderedVideoUrl(), renderReframingRevision() (+12 more)

### Community 61 - "reframing_renderer.py"
Cohesion: 0.23
Nodes (7): seed_analysis_run(), seed_candidate(), seed_export(), test_batch_export_endpoint_success(), test_batch_export_validation_and_skipped(), test_multi_video_data_isolation(), test_workflow_state_evaluation_lifecycle()

### Community 62 - "test_p0_7_windows_launcher_reliability.py"
Cohesion: 0.15
Nodes (10): _run_ps_command(), test_01_launcher_scripts_exist_and_resolve_root(), test_02_invocation_from_different_working_directory(), test_03_duplicate_startup_prevention(), test_04_already_running_healthy_detection(), test_05_port_occupied_by_unrelated_process(), test_06_stale_pid_file_cleanup(), test_07_pid_reuse_protection() (+2 more)

### Community 63 - "ZezEdit 2.0 — Milestone 11 Completion Report: Graphify Integration, Unslop UI Redesign, Video-Centric Workspace & Feature Recovery"
Cohesion: 0.22
Nodes (18): test_incremental_sha256_matches_full_hash(), _setup_test_orchestrator(), test_case_01_normal_completion(), test_case_02_long_cpu_operation_heartbeat(), test_case_03_long_ffmpeg_child_process_alive(), test_case_04_slow_transcription_progress(), test_case_05_worker_thread_crash(), test_case_06_worker_process_crash() (+10 more)

### Community 64 - "ReframingWorkspace.tsx"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 65 - "test_candidate_human_review_workflow"
Cohesion: 0.15
Nodes (6): 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction, 4. Export Overwrite & Confirmation Rules, 5. AI Video Editor Security Boundary, 6. Backup & Restore Strategy, ZezEdit 2.0 — Security & Data Safety Architecture

### Community 66 - "Tokens"
Cohesion: 0.09
Nodes (21): A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, D. Audio and Transcription, Database Migration: `0010_transcript_corrections_and_audio.sql`, E. Scene Detection, F. Visual Understanding, Files Created, G. Temporal Context Aggregation (+13 more)

### Community 67 - "preview_user_data_cleanup_endpoint"
Cohesion: 0.11
Nodes (19): 1. Prerequisites, 2. Installation commands, 3. Environment and setup steps, 4. Exact Windows PowerShell backend startup commands, 5. Exact Windows PowerShell frontend startup commands, 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12 & 13), AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Architecture & Documentation (+11 more)

### Community 69 - "ZezEdit 2.0 — System Architecture"
Cohesion: 0.25
Nodes (7): 1. Overview & Guiding Principles, 2. High-Level System Architecture, 3. Frontend Module Boundaries (`frontend/src/`), 6. Windows 11 Startup & Shutdown Lifecycle, Graceful Shutdown Sequence, Startup Sequence, ZezEdit 2.0 — System Architecture

### Community 70 - "Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)"
Cohesion: 0.11
Nodes (18): ShortsCandidateRecord, AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Character Extraction Studio, Character Library & System Integration (Milestone 10), Core Backend, Database & Project Management (Milestone 2), Core Foundation & Architecture (Milestone 1), Core Product Workflow, Working Queue & Desktop Operations (Milestone 17), Frontend Application Shell, Dashboard & Design System (Milestone 3), Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11) (+10 more)

### Community 71 - "MediaService"
Cohesion: 0.05
Nodes (31): stream_media(), stream_media_global(), _stream_video_asset(), MediaService, MediaProbeResult, test_batch_upload_with_zero_delay(), test_upload_single_with_controlled_test_delay(), test_upload_single_with_zero_delay() (+23 more)

### Community 72 - "Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)"
Cohesion: 0.11
Nodes (17): 1. Storage Separation & Source Immutability, 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First), 3. Smart Reframing & Portrait Rendering Architecture, 5. Milestone 4 Implementation Details: Media Ingestion & Proxies, 5. Video Analysis Engine (Milestone 5), 6. Smart Reframing & Dynamic Crop Renderer (Milestone 7), 7. Rendering Engine & Export Pipeline (Milestone 8), Authoritative Crop Math & Preview Parity (+9 more)

### Community 73 - "ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library"
Cohesion: 0.29
Nodes (6): 1. Overview & Principles, 2. Database Schema (Migration `0009_character_studio.sql`), 3. Human Review Operations, 4. Documented JSON Export Schema, Fundamental Constraints & Transparency Principles, ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library

### Community 74 - "error_envelope.schema.json"
Cohesion: 0.11
Nodes (17): type, type, properties, required, type, type, properties, code (+9 more)

### Community 76 - "2. Complete 100-Requirement Parity Matrix"
Cohesion: 0.12
Nodes (16): 1. Executive Summary & Historical Context, 2. Surviving Evidence Sources & Provenance, 3. Pre-Deletion Architecture & Data Flows, 4. Reconstructed Pre-Deletion Feature Inventory (20 Application Areas), 5. Milestone 13M.12 Deep-Dive Investigation, 6. Milestone 13M.13 Deep-Dive Investigation, 7. Historical UI Reconstruction, 8. Summary of Reconstructed Pre-Deletion Baseline (+8 more)

### Community 77 - "Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)"
Cohesion: 0.12
Nodes (17): type, type, properties, type, type, type, type, clips (+9 more)

### Community 78 - "README.md"
Cohesion: 0.12
Nodes (16): 1. Spacing, 2. Color, 3. Icons, 4. Copy, 5. Type, 6. Layout, 7. Details, 8. Visuals (+8 more)

### Community 79 - "OllamaVisionAnalyzer"
Cohesion: 0.16
Nodes (6): VideoWorkflowStateResponse, WorkflowStateMachine, Milestone 18: Unified Video-to-Shorts Production Pipeline Checklist, 1. Executive Summary, 23. Graphify Knowledge Graph & Topological Codebase Health, 4. Authoritative Workflow Lifecycle State Machine

### Community 80 - "3. Sub-Workspace Breakdown"
Cohesion: 0.12
Nodes (15): 1. Overview, 1. Overview Tab, 2. Analysis Tab, 2. Context & State Flow, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Scenes Tab, 5. AI Highlights Tab (+7 more)

### Community 81 - "ai_providers.py"
Cohesion: 0.12
Nodes (16): type, exclusiveMinimum, type, type, properties, aspect_ratio, fps, project_id (+8 more)

### Community 82 - "ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis"
Cohesion: 0.14
Nodes (14): Accent, App layout, Buttons, Dark, Depth, Icons, Light, Motion (+6 more)

### Community 84 - "run_p0_9_demos.py"
Cohesion: 0.36
Nodes (11): _setup_orchestrator(), test_case_01_healthy_worker_long_operation_with_heartbeats(), test_case_02_worker_genuinely_blocked(), test_case_03_worker_crashed_external_process(), test_case_04_worker_raises_exception(), test_case_05_worker_completes_successfully(), test_case_06_worker_attempts_update_terminal_job(), test_case_07_worker_pid_is_local_string() (+3 more)

### Community 85 - "Tokens"
Cohesion: 0.13
Nodes (15): Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-044`: Boundary Safety Containment (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12) (+7 more)

### Community 86 - "Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)"
Cohesion: 0.14
Nodes (14): Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`), `ZEZ-056`: Piecewise-Linear Dynamic FFmpeg Crop Filtergraph (13M.12), `ZEZ-057`: Burned-in Subtitles & Karaoke Word-Level ASS Styling, `ZEZ-058`: Professional Audio Processing & EBU R128 Loudness Normalization, `ZEZ-059`: Export Presets & Aspect Ratio Conversion, `ZEZ-060`: Strict Multi-Point Output Validation Gate, `ZEZ-061`: Poster Frame Cover Thumbnail Extraction, `ZEZ-062`: Render Progress Monitoring via FFmpeg `-progress` Pipe (+6 more)

### Community 87 - "Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)"
Cohesion: 0.15
Nodes (4): LargeUploadPreflightMiddleware, test_preflight_middleware_rejects_insufficient_disk_space(), test_preflight_middleware_rejects_malformed_content_length(), test_preflight_middleware_rejects_oversized_content_length()

### Community 92 - "Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)"
Cohesion: 0.20
Nodes (10): Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`), `ZEZ-021`: Automated Audio Extraction for ASR, `ZEZ-022`: Faster-Whisper Local Speech Transcription, `ZEZ-023`: Word-Level Timestamp Alignment, `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer, `ZEZ-026`: FFmpeg Visual Scene Cut Detection, `ZEZ-027`: Keyframe Visual Lightbox & Filmstrip, `ZEZ-028`: Interval Frame Sampling for Visual Understanding (+2 more)

### Community 93 - "character.py"
Cohesion: 0.29
Nodes (7): _create_synthetic_mp4(), test_batch_upload_partial_failure(), test_filename_spaces_unicode_brackets(), test_multiple_video_batch_upload_all_valid(), test_path_traversal_rejection(), test_repeated_upload_non_destructive_collision(), test_single_video_upload_success()

### Community 94 - "CDPBrowser"
Cohesion: 0.15
Nodes (12): 1. Parity Metrics & Scorecard Summary, 2. Complete 100-Requirement Parity Matrix, Domain A: Application Shell, Dashboard & Navigation, Domain B: Media Management, Proxies & Storage, Domain C: Video Analysis & Speech Understanding, Domain D & E: AI Multimodal Understanding & Highlight Discovery, Domain F: Smart Reframing & Subject Tracking (13M.12/13M.13), Domain G: Shorts Generation & FFmpeg Rendering (+4 more)

### Community 95 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.15
Nodes (13): Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`), `ZEZ-069`: Multi-Track Timeline NLE Canvas, `ZEZ-070`: Non-Destructive Clip Trimming & Splitting, `ZEZ-071`: Ripple Delete & Gap Closing, `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing, `ZEZ-073`: Persistent Timeline Undo & Redo History, `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration, `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`) (+5 more)

### Community 97 - "2. Complete 100-Requirement Parity Matrix"
Cohesion: 0.20
Nodes (5): client(), create_synthetic_test_video(), test_batch_render_recovery_action(), test_failed_render_preserves_script_and_retry_works(), test_five_candidates_generate_five_exports_and_mp4s()

### Community 98 - "Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)"
Cohesion: 0.17
Nodes (12): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 15: Video Analysis, AI Understanding & Temporal Context Restoration Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification (+4 more)

### Community 99 - "CDPBrowser"
Cohesion: 0.14
Nodes (14): 10. Test and Acceptance Criteria, 11. Current Verified Restoration Coverage, 12. Recommended Next Implementation Milestone, 1. ZezEdit 1.0 Feature Inventory, 2. Historical Evidence References, 3. Exact Parity Requirements Identified, 4. Features Already Restored in ZezEdit 2.0, 5. Missing Functionality (Parity Gap) (+6 more)

### Community 100 - "SKILL.md"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 101 - "test_session5_clip_editing.py"
Cohesion: 0.21
Nodes (4): get_doc_article(), list_doc_articles(), list_doc_categories(), DocCategoryDTO

### Community 104 - "Signs of slop"
Cohesion: 0.18
Nodes (10): 1. Executive Summary, 2. Unslop Visual & Interaction Audit, 3. Product Workflow Gap Analysis, 4. Feature Recovery Matrix, 5. Unslop Design Direction for ZezEdit 2.0, A. Surfaces and Colors, B. Typography & Copy, Current Broken Workflow: (+2 more)

### Community 105 - "ZezEdit 2.0 — Master Requirements Specification"
Cohesion: 0.18
Nodes (11): 3. Core Functional Modules (A–J), Module A — Dashboard & Project Management, Module B — Media Library, Module C — Video Analysis, Module D — Highlight Discovery, Module E — Smart Reframing, Module F — Multi-Track Timeline Editor, Module G — AI Video Editor (+3 more)

### Community 106 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.18
Nodes (10): 1. Roadmap Architecture & Execution Principles, 2. Master Implementation Milestone Schedule, 3. Detailed Milestone Breakdown, Milestone 13: Exact Parity Specification & Pre-Deletion Architecture, Milestone 14: Interactive Reframing Review, Draggable Canvas & Keyframe Diamonds, Milestone 15: Video Analysis, AI Understanding & Temporal Context Restoration, Milestone 16: Multi-Track Timeline Audio Waveforms, Ducking & Word-Level Karaoke, Milestone 17: Core Product Workflow, Working Queue & Desktop Operations (+2 more)

### Community 107 - "F. Test Evidence Summary"
Cohesion: 0.18
Nodes (11): Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`), `ZEZ-011`: Video Drag-and-Drop & File Picker Ingestion, `ZEZ-012`: Automated FFprobe Container & Stream Dissection, `ZEZ-013`: Fast Edit Proxy Generation (480p), `ZEZ-014`: Poster Frame & Thumbnail Strip Generation, `ZEZ-015`: Audio File Ingestion & Waveform Prep, `ZEZ-016`: Image File Ingestion for Overlays & Watermarks, `ZEZ-017`: Safe Isolated Storage Layout (+3 more)

### Community 108 - "3. Core Functional Modules (A–J)"
Cohesion: 0.18
Nodes (11): Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`), `ZEZ-031`: Local Multimodal Vision Integration (Ollama), `ZEZ-032`: Multimodal Context Aggregator, `ZEZ-033`: Explainable 9-Factor Highlight Scoring Engine, `ZEZ-034`: Narrative Setup and Payoff Boundary Preservation, `ZEZ-035`: Categorized Shorts Candidate Ranking, `ZEZ-036`: Hook Rationale & Explanation Card, `ZEZ-037`: Candidate Review & Approval Workflow (+3 more)

### Community 109 - "3. Detailed Milestone Breakdown"
Cohesion: 0.18
Nodes (11): Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`), `ZEZ-081`: Evidence-Based Character Extraction Pipeline (Non-3D), `ZEZ-082`: Spatial-Temporal Candidate Clustering (DBSCAN), `ZEZ-083`: Character Observation Gallery & Thumbnails, `ZEZ-084`: Screen-Time Transparency Analytics, `ZEZ-085`: Unverified Dialogue Correlation with Disclaimer, `ZEZ-086`: Human Review Controls: Inline Renaming, `ZEZ-087`: Human Review Controls: Confirm to Persistent Character Library (+3 more)

### Community 110 - "Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)"
Cohesion: 0.18
Nodes (11): Domain J: System Infrastructure, Diagnostics & Reliability (`ZEZ-091` – `ZEZ-100`), `ZEZ-091`: Forward-Only Versioned SQLite Migrations, `ZEZ-092`: Pre-Migration Automatic Database Snapshot, `ZEZ-093`: Path Traversal & Anti-Root Recursive Deletion Guard, `ZEZ-094`: Single Authoritative Job Orchestrator & State Machine, `ZEZ-095`: Unclean Shutdown Recovery of Interrupted Jobs, `ZEZ-096`: Comprehensive Health & Diagnostics Probe (`/api/v1/health`), `ZEZ-097`: Graphify Knowledge Graph Auto-Maintenance (+3 more)

### Community 113 - "ReframingRenderer"
Cohesion: 0.20
Nodes (9): 1. API Versioning & Base Prefix, 2. Resource Naming & HTTP Method Conventions, 3. Standard Request & Response Conventions, 4. Implemented vs Planned Endpoint Inventory, Centralized Error Response Contract, Implemented in Milestones 1–6, Planned Endpoints (Milestones 10–12), Success Envelopes (+1 more)

### Community 114 - "base.py"
Cohesion: 0.20
Nodes (10): Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`), `ZEZ-001`: Studio Application Shell & Responsive Drawer, `ZEZ-002`: Studio Dashboard View, `ZEZ-003`: Project Management & Lifecycle Operations, `ZEZ-004`: Unified Video Workspace Navigation, `ZEZ-006`: System Monitor & Hardware Resource Widget, `ZEZ-007`: Studio Light / Dark Theme Synchronization, `ZEZ-008`: Notification Center & Job Completion Toasts (+2 more)

### Community 118 - "test_reconciliation_transaction_rollback_on_interruption"
Cohesion: 0.33
Nodes (3): client(), test_automatic_shorts_generation_enqueues_export_render(), test_candidate_script_deletion_and_re_rendering()

### Community 119 - "test_download_filename_derived_from_content_title"
Cohesion: 0.22
Nodes (8): 1. Engine & Pragmas, 2. Versioned Migration Strategy (Historical Lesson Applied), 3. Planned Domain Entity Relationship Diagram, 4. Schema Breakdown: Implemented vs Planned, 5. Limitations & Alternatives Considered, Implemented Tables (Migrations 0001–0005), Planned Tables for Subsequent Milestones (Schema Blueprint), ZezEdit 2.0 — Database Design & Migration Strategy

### Community 120 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.22
Nodes (8): 1. Core Mandate: One Single Job System, 2. Job States & Lifecycle Transitions, 3. Canonical Job Types & Concurrency Policy, 4. Worker Ownership & Child Process PID Registry, 5. Restart Recovery Rules, 6. Retry Rules & Per-Job Logs, 7. Alternatives Considered & Limitations, ZezEdit 2.0 — Authoritative Job Orchestration Design

### Community 121 - "ZezEdit 2.0 — Authoritative Job Orchestration Design"
Cohesion: 0.22
Nodes (8): ADR-01: Single Local Monolith (FastAPI + React) vs Microservices, ADR-02: CPU-First Local Processing & Streaming I/O, ADR-03: SQLite WAL + Forward-Only SQL Migrations, ADR-04: Centralized Error Handling & Structured Logging, ADR-06: Decoupled Evidence-Based Character Extraction (No 3D Studio), ADR-07: Testing Strategy (Multi-Layer Gate), ADR-08: Shared Contract Directory (`shared/contracts/`), ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)

### Community 122 - "schema_version"
Cohesion: 0.22
Nodes (8): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, strict, include

### Community 126 - "api/__init__.py"
Cohesion: 0.29
Nodes (7): Dithering, Duotone, Effects, Glyphs, Halftone dots, Implementation, Performance

### Community 127 - ".cors_origin_list"
Cohesion: 0.29
Nodes (7): Decide what the visual is, Generate it, Objects for moments, Prompt recipe, Put it on the page, Styles that work, Visuals

### Community 129 - ".ensure_directories"
Cohesion: 0.29
Nodes (6): 1. Product Vision & Mission Statement, 2. Requirement Taxonomy & Numbering, 3. Detailed Specification by Domain, 4. Summary Parity Ledger, Core Architecture Axioms, ZezEdit 1.0 — Exact Product Parity Specification

### Community 134 - "Path"
Cohesion: 0.33
Nodes (5): 1. Mission & Product Vision, 2. Hardware & Resource Constraints (Mandatory), 4. Mandatory Data Protection & Reliability Rules, 5. Planned Milestone Sequence, ZezEdit 2.0 — Master Requirements Specification

### Community 135 - "zezedit-backend"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 138 - "FastAPI"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 139 - "postcss.config.js"
Cohesion: 0.40
Nodes (5): required, type, tracks, items, type

### Community 141 - "run_migrations"
Cohesion: 0.05
Nodes (16): MigrationError, _backup_before_upgrade(), _file_sha256(), MigrationResult, _parse_version_and_name(), run_migrations(), test_sqlite_migrations_idempotency_backup_and_checksum(), character_env() (+8 more)

### Community 142 - "Settings"
Cohesion: 0.06
Nodes (9): Settings, app_and_client(), env(), timeline_env(), test_startup_purges_stale_partial_uploads(), prod_client(), test_health_check_reports_failed_on_unwritable_storage(), test_api_clip_edit_routes() (+1 more)

### Community 143 - "zezedit-backend"
Cohesion: 0.50
Nodes (4): 6. Multiple Shorts Batch Export Engine, Batch Export Request Payload:, Batch Export Response Payload:, Output File Organization:

### Community 147 - "kind"
Cohesion: 0.67
Nodes (3): minimum, type, duration_sec

### Community 148 - "playhead_sec"
Cohesion: 0.67
Nodes (3): minimum, type, height

### Community 149 - "schema_version"
Cohesion: 0.67
Nodes (3): enum, type, kind

### Community 150 - "source_kind"
Cohesion: 0.67
Nodes (3): minimum, type, playhead_sec

### Community 151 - "width"
Cohesion: 0.67
Nodes (3): schema_version, const, type

### Community 152 - "zoom_px_per_sec"
Cohesion: 0.67
Nodes (3): source_kind, enum, type

### Community 153 - "api/__init__.py"
Cohesion: 0.67
Nodes (3): width, minimum, type

### Community 154 - "core/__init__.py"
Cohesion: 0.67
Nodes (3): zoom_px_per_sec, minimum, type

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1754 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `JobOrchestrator` to `Settings`, `StorageLayout`, `subprocess`, `CharacterService`, `create_app`, `AppError`, `test_process_manager_lifecycle.py`, `highlights.py`, `test_p0_9_restart_and_persistence.py`, `Settings`, `ProjectService`, `test_milestone9_timeline.py`, `ExportService`, `run_migrations`, `export_service.py`, `v1/media.py`, `start_highlight_discovery`, `settings.py`, `v1/media.py`, `NotFoundError`, `post`, `time`, `.get_job`, `sqlite_session`, `sqlite3`, `test_foundation.py`, `.claim_next_queued_job`, `OllamaProvider`, `error_envelope.schema.json`, `test_p0_7_windows_launcher_reliability.py`, `ZezEdit 2.0 — Milestone 11 Completion Report: Graphify Integration, Unslop UI Redesign, Video-Centric Workspace & Feature Recovery`, `Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)`, `._terminate_pid_tree`, `run_p0_9_demos.py`, `Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)`, `CDPBrowser`, `Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)`, `ZezEdit 2.0 — Database Design & Migration Strategy`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 56 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.034525386313465786 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)` to `SettingsManager.tsx`, `JobOrchestrator`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Are the 49 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `_run_discovery_background()`) actually correct?**
  _`JobOrchestrator` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Should `StorageLayout` be split into smaller, more focused modules?**
  _Cohesion score 0.04269662921348315 - nodes in this community are weakly interconnected._