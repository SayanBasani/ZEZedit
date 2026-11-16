# Graph Report - ZezEdit  (2026-11-15)

## Corpus Check
- 222 files · ~382,077 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .xml 3, .example 1, (none) 1)

## Summary
- 3487 nodes · 9865 edges · 143 communities (126 shown, 17 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1116 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0746ec1f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- subprocess
- config.py
- CharacterService
- JobOrchestrator
- config.py
- MediaService
- v1/timeline.py
- v1/reframing.py
- Button
- Settings
- AppError
- ExportService
- sqlite3
- system.ts
- .from_root
- Settings
- .from_root
- core.py
- ProjectService
- sqlite_session
- projects.ts
- ReframingWorkspace.tsx
- StorageLayout
- test_milestone5_analysis.py
- test_milestone24_timeline_operations_coverage.py
- StorageLayout
- start_highlight_discovery
- create_app
- ExportService
- get_health
- analysis.py
- TimelineService
- test_milestone9_timeline.py
- BackupService
- post
- TimelineCommandService
- SubjectTracker
- ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration
- HighlightDiscoveryEngine
- settings.py
- ZezEdit 2.0 — Milestone 17 Verification & Restoration Report
- CropKeyframe
- SettingsService
- get_settings
- base.py
- .approve_and_execute_plan
- ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report
- get_settings
- MediaPipelineService
- ZezEdit 2.0 — Local-First AI Video Editor
- characters.py
- test_session17_queue_and_workflow.py
- ZezEdit 2.0 — Feature Status Tracker
- test_session23_real_media_ai_quality.py
- ZezEdit 2.0 — Media Storage & Processing Pipeline
- error_envelope.schema.json
- CharacterStudio.tsx
- error_envelope.schema.json
- MediaPipelineService
- Unslop
- test_direct_upload_verification.py
- reframing_renderer.py
- properties
- Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)
- get
- test_candidate_human_review_workflow
- Tokens
- preview_user_data_cleanup_endpoint
- analysis.py
- pytest
- Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)
- WorkflowStateMachine
- README.md
- Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)
- .__init__
- ZezEdit 2.0 — Milestone 13 Completion Report: ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan
- 2. Complete 100-Requirement Parity Matrix
- Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)
- README.md
- VideoAnalysisPipeline
- Signs of slop
- ai_providers.py
- ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- README.md
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- test_milestone20_production_reliability.py
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- ZezEdit 2.0 — API Design & Conventions
- Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)
- character.py
- subprocess
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Database Design & Migration Strategy
- test_milestone5_analysis.py
- ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)
- compilerOptions
- SKILL.md
- Effects
- Visuals
- ZezEdit 2.0 — Security & Data Safety Architecture
- Effects
- ZezEdit 2.0 — Master Requirements Specification
- ZezEdit 2.0 — Security & Data Safety Architecture
- F. Test Evidence Summary
- test_session12_large_library.py
- test_session6c_rendering_and_batch_export.py
- OllamaProvider
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- 6. Multiple Shorts Batch Export Engine
- .validate_external_path
- base.py
- character_env
- timeline_env
- pytest
- test_milestone19_desktop_operations.py
- height
- test_session21_multimodal_intelligence_and_tracking.py
- test_creative_direction_aliases_and_educational
- schema_version
- source_kind
- width
- zoom_px_per_sec
- api/__init__.py
- .cors_origin_list
- core/__init__.py
- .ensure_directories
- zezedit-backend
- test_session15_endurance_and_recovery.py

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 241 edges
2. `Settings` - 146 edges
3. `JobOrchestrator` - 143 edges
4. `request()` - 130 edges
5. `StorageLayout` - 94 edges
6. `AppError` - 82 edges
7. `get_settings()` - 82 edges
8. `NotFoundError` - 77 edges
9. `create_app()` - 77 edges
10. `run_migrations()` - 71 edges

## Surprising Connections (you probably didn't know these)
- `Centralized Error Response Contract` --references--> `AppError`  [INFERRED]
  docs/architecture/API_DESIGN.md → backend/app/core/errors.py
- `ADR-04: Centralized Error Handling & Structured Logging` --references--> `AppError`  [INFERRED]
  docs/architecture/TECHNOLOGY_DECISIONS.md → backend/app/core/errors.py
- `Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration` --references--> `ExportService`  [INFERRED]
  docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md → backend/app/services/export_service.py
- `15. Multi-Track Timeline & Custom Clip Editing` --references--> `ExportService`  [INFERRED]
  docs/reports/milestone_18_unified_video_to_shorts_pipeline_report.md → backend/app/services/export_service.py
- `Domain B: Media Management, Proxies & Storage` --references--> `StorageLayout`  [INFERRED]
  docs/reconstruction/FEATURE_PARITY_MATRIX.md → backend/app/core/storage.py

## Import Cycles
- None detected.

## Communities (143 total, 17 thin omitted)

### Community 0 - "subprocess"
Cohesion: 0.07
Nodes (26): ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream(), sample_analysis_frames(), _sample_one() (+18 more)

### Community 1 - "config.py"
Cohesion: 0.07
Nodes (11): AppError, calculate_aspect_ratio(), MediaProbeResult, MediaStreamInfo, parse_fraction(), probe_media_file(), generate_proxy(), generate_thumbnail() (+3 more)

### Community 2 - "CharacterService"
Cohesion: 0.04
Nodes (117): FoundationOverview(), MODULE_ROADMAP, ProjectsView(), formatBytes(), SettingsManager(), SettingsTab, TimelineEditor(), addTimelineTextOverlay() (+109 more)

### Community 3 - "JobOrchestrator"
Cohesion: 0.05
Nodes (33): confirm_candidate(), detach_observation(), export_character(), get_character_service(), get_extraction_job(), get_library_character(), list_candidates(), list_library_characters() (+25 more)

### Community 4 - "config.py"
Cohesion: 0.06
Nodes (26): lifespan(), _queue_poller(), JobRecord, JobOrchestrator, test_job_retry_lifecycle_and_event_timeline(), test_queue_stats_aggregation(), test_job_checkpointing_and_recovery(), test_resource_aware_scheduler_and_priority() (+18 more)

### Community 5 - "MediaService"
Cohesion: 0.07
Nodes (9): delete_media_global(), get_asset_integrity(), get_proxy_file(), relink_media(), MediaAssetRecord, MediaService, test_media_assets_and_relinking(), test_media_pipeline_local_import_modes() (+1 more)

### Community 6 - "v1/timeline.py"
Cohesion: 0.08
Nodes (45): ResourceInspector(), DocumentationView(), AIProviderManager(), categorizeJobType(), CategoryFilter, formatDuration(), formatTimeOnly(), ProcessesManagerView (+37 more)

### Community 7 - "v1/reframing.py"
Cohesion: 0.11
Nodes (47): Milestone 3 — Frontend Application Shell, Dashboard & Design System, BadgeProps, Button(), ButtonProps, Card(), CardProps, ConfirmDialog(), ConfirmDialogProps (+39 more)

### Community 8 - "Button"
Cohesion: 0.07
Nodes (63): AnalysisWorkspace(), CandidateClipEditorModal(), AspectRatioOption, CREATIVE_DIRECTION_LABELS, CreativeDirectionOption, SingleVideoStudio(), STAGE_LABELS, GenerateShortModal() (+55 more)

### Community 9 - "Settings"
Cohesion: 0.05
Nodes (14): Settings, _format_bytes(), StorageService, main(), storage_jobs_env(), test_storage_breakdown_categories_accuracy(), test_temp_cache_cleanup_execute_with_valid_token(), test_temp_cache_cleanup_preview_no_file_deletion() (+6 more)

### Community 10 - "AppError"
Cohesion: 0.06
Nodes (35): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, App() (+27 more)

### Community 11 - "ExportService"
Cohesion: 0.06
Nodes (20): BatchExportItem, BatchExportRequest, BatchExportResponse, cancel_export(), create_batch_export_jobs(), create_export_preview(), create_export_render_job(), delete_export() (+12 more)

### Community 12 - "sqlite3"
Cohesion: 0.11
Nodes (11): _setup_test_orchestrator(), test_active_external_child_pid_never_marked_stalled_within_grace(), test_checkpoint_never_heals_failed_status(), test_complete_job_rejects_failed_status(), test_completed_or_100pct_job_never_marked_stalled(), test_dead_os_pid_marked_stalled_after_grace(), test_in_process_job_stalls_when_silent_beyond_timeout(), test_export_delete_endpoint() (+3 more)

### Community 13 - "system.ts"
Cohesion: 0.07
Nodes (16): add_text_overlay(), approve_plan(), create_timeline(), duplicate_clip(), get_ai_editor_service(), get_command_service(), get_timeline_renderer(), get_timeline_service() (+8 more)

### Community 14 - ".from_root"
Cohesion: 0.06
Nodes (19): AudioConfig, CaptionConfig, ExportPreset, ValidationDetails, AudioPipeline, CaptionEngine, format_ass_timestamp(), hex_to_ass_color() (+11 more)

### Community 15 - "Settings"
Cohesion: 0.18
Nodes (19): AIConversation, AIEditingPlan, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType, ContentProps (+11 more)

### Community 16 - ".from_root"
Cohesion: 0.08
Nodes (13): get_analysis_pipeline(), get_db_path(), get_backup_service(), get_clip_editing_service(), get_export_service(), get_discovery_engine(), get_job_orchestrator(), get_media_service() (+5 more)

### Community 17 - "core.py"
Cohesion: 0.07
Nodes (31): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, CandidateResponse, delete_candidate(), DiscoverHighlightsRequest, generate_more_highlights() (+23 more)

### Community 18 - "ProjectService"
Cohesion: 0.08
Nodes (24): check_project_media_integrity(), generate_proxy_endpoint(), get_media(), get_media_global(), get_media_proxy_global(), get_media_thumbnail_global(), get_thumbnail_file(), import_local_file() (+16 more)

### Community 19 - "sqlite_session"
Cohesion: 0.09
Nodes (41): 7. Video Workspace Implementation, Badge(), BatchExportModal(), BatchExportModalProps, DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), HighlightsWorkspace() (+33 more)

### Community 20 - "projects.ts"
Cohesion: 0.06
Nodes (39): AnalysisWorkspaceProps, CharacterStudioProps, DashboardViewProps, ExportStudioProps, HighlightsWorkspaceProps, MediaLibraryViewProps, PostImportModalProps, ProjectsManagerProps (+31 more)

### Community 21 - "ReframingWorkspace.tsx"
Cohesion: 0.16
Nodes (20): ReframingReviewModal(), ReframingWorkspace(), analyzeReframing(), fetchCropPreview(), fetchReframingRevisions(), getProxyUrl(), getRenderedVideoUrl(), renderReframingRevision() (+12 more)

### Community 22 - "StorageLayout"
Cohesion: 0.04
Nodes (21): MigrationError, StorageLayout, _backup_before_upgrade(), _file_sha256(), MigrationResult, _parse_version_and_name(), run_migrations(), m15_env() (+13 more)

### Community 23 - "test_milestone5_analysis.py"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 24 - "test_milestone24_timeline_operations_coverage.py"
Cohesion: 0.07
Nodes (16): ValidationError, SplitClipRequest, TimelineClip, TrimClipRequest, UpdateClipPropsRequest, test_timeline_consecutive_undo_redo_stack(), test_timeline_duplicate_clip_naming_and_props(), test_timeline_move_clip_cross_track() (+8 more)

### Community 25 - "StorageLayout"
Cohesion: 0.09
Nodes (11): DetectedSubject, FramingEngine, test_framing_strategies_single_two_person_and_group(), test_portrait_crop_geometry_and_bounds(), test_trajectory_smoothing_and_scene_cut_isolation(), test_framing_engine_center_and_speaker_strategies(), test_framing_engine_action_object_framing(), test_framing_engine_group_framing() (+3 more)

### Community 26 - "start_highlight_discovery"
Cohesion: 0.07
Nodes (32): devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49, tailwindcss@^3.4.16, @testing-library/jest-dom@^7.0.1, @testing-library/react@^16.3.3, @types/react@^18.3.12 (+24 more)

### Community 27 - "create_app"
Cohesion: 0.11
Nodes (23): create_app(), test_api_endpoints_end_to_end(), test_media_http_api_endpoints(), test_candidate_api_lifecycle(), test_reframing_api_lifecycle_and_revisions(), _setup_test_env(), test_api_parity_processes_and_jobs_routes(), test_delete_job_history() (+15 more)

### Community 28 - "ExportService"
Cohesion: 0.08
Nodes (16): get_analysis_cache(), get_analysis_telemetry(), compute_source_signature(), _ticker(), _now_utc(), VideoAnalysisPipeline, on_transcribe_progress(), run_real_video_verification() (+8 more)

### Community 29 - "get_health"
Cohesion: 0.09
Nodes (12): CreateReframingPlanRequest, get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), ManualOverrideItem, preview_crop_geometry(), render_reframed_video(), RenderRevisionRequest (+4 more)

### Community 30 - "analysis.py"
Cohesion: 0.08
Nodes (6): get_ai_conversation(), get_plan(), get_timeline(), list_plans(), send_ai_message(), AIEditorService

### Community 31 - "TimelineService"
Cohesion: 0.10
Nodes (12): add_track(), delete_track(), get_active_timeline(), update_timeline_settings(), update_track(), NotFoundError, TimelineRecord, TimelineTrack (+4 more)

### Community 32 - "test_milestone9_timeline.py"
Cohesion: 0.09
Nodes (30): get_doc_article(), list_doc_articles(), list_doc_categories(), AIProviderCapability, AIProviderDTO, AIProviderTestRequest, AIProviderTestResponse, AIProviderUpdateRequest (+22 more)

### Community 33 - "BackupService"
Cohesion: 0.07
Nodes (14): create_backup(), restore_backup(), create_backup_endpoint(), get_db_integrity_endpoint(), get_recovery_status_endpoint(), get_storage_breakdown_endpoint(), list_backups_endpoint(), preview_cleanup_endpoint() (+6 more)

### Community 34 - "post"
Cohesion: 0.11
Nodes (13): archive_project(), create_project(), delete_project(), get_project(), get_project_events(), get_project_service(), list_projects(), restore_project() (+5 more)

### Community 35 - "TimelineCommandService"
Cohesion: 0.10
Nodes (6): delete_clip(), get_history(), redo(), undo(), TimelineCommandService, test_persistent_undo_and_redo()

### Community 36 - "SubjectTracker"
Cohesion: 0.09
Nodes (21): A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, D. Audio and Transcription, Database Migration: `0010_transcript_corrections_and_audio.sql`, E. Scene Detection, F. Visual Understanding, Files Created, G. Temporal Context Aggregation (+13 more)

### Community 37 - "ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration"
Cohesion: 0.07
Nodes (30): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+22 more)

### Community 38 - "HighlightDiscoveryEngine"
Cohesion: 0.07
Nodes (16): format_timestamp(), GeneratedCandidate, HighlightDiscoveryEngine, _now_utc(), QualityGateResult, ScoreBreakdown, test_highlight_discovery_engine(), test_quality_gates_and_statuses() (+8 more)

### Community 39 - "settings.py"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 40 - "ZezEdit 2.0 — Milestone 17 Verification & Restoration Report"
Cohesion: 0.11
Nodes (12): cancel_job(), create_job(), delete_job(), delete_jobs_history(), _enrich_job_response(), get_job(), get_job_checkpoint(), get_job_logs() (+4 more)

### Community 41 - "CropKeyframe"
Cohesion: 0.15
Nodes (6): CropKeyframe, test_preview_and_renderer_expression_parity(), test_crop_filter_expression_constant_y_simplification(), test_crop_filter_expression_stationary_crop(), test_dynamic_crop_filter_expression_generation(), `ZEZ-055`: Authoritative Preview-to-Render Mathematical Parity (13M.12/13M.13)

### Community 42 - "SettingsService"
Cohesion: 0.12
Nodes (12): _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models, 2. `timeline_tracks` Table, 3. Persistent Reversible Command System (Undo / Redo), 3. `timeline_clips` Table (+4 more)

### Community 43 - "get_settings"
Cohesion: 0.13
Nodes (8): get_settings_service(), list_ai_providers(), update_ai_provider(), get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 44 - "base.py"
Cohesion: 0.13
Nodes (7): CandidateEditSaveRequest, get_candidate_edit(), reset_candidate_edit(), save_candidate_edit(), track_candidate_subjects(), TrackCandidateRequest, ClipEditingService

### Community 45 - ".approve_and_execute_plan"
Cohesion: 0.11
Nodes (8): AddTextOverlayRequest, InsertClipRequest, test_timeline_duration_auto_calculation(), test_timeline_text_overlay_creation_and_auto_track(), timeline_env(), test_ai_video_editor_assistant(), test_clip_operations_and_validation(), test_timeline_rendering_pipeline()

### Community 46 - "ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 47 - "get_settings"
Cohesion: 0.13
Nodes (14): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, clear_all_user_data_endpoint(), ClearAllDataRequest, execute_cleanup_endpoint(), get_backup_service(), get_capabilities_endpoint() (+6 more)

### Community 48 - "MediaPipelineService"
Cohesion: 0.19
Nodes (4): delete_media(), get_media_stats(), MediaStorageStatsResponse, MediaPipelineService

### Community 49 - "ZezEdit 2.0 — Local-First AI Video Editor"
Cohesion: 0.10
Nodes (15): ReframingRenderer, Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12) (+7 more)

### Community 50 - "characters.py"
Cohesion: 0.16
Nodes (8): ProviderHealth, SpeechToTextProvider, StructuredPlanResult, TextLLMProvider, VisionLanguageProvider, 4. Backend Module Boundaries (`backend/app/`), 5. AI Provider Abstraction Boundaries, ADR-05: Dynamic Authoritative AI Provider Abstraction

### Community 51 - "test_session17_queue_and_workflow.py"
Cohesion: 0.11
Nodes (12): _worker(), test_large_library_pagination_performance(), queue_env(), test_scenario_01_queued_analysis_job_executes(), test_scenario_02_queued_highlight_discovery_job_executes(), mock_discover(), test_scenario_03_queued_export_job_executes(), test_scenario_04_multiple_queued_jobs_priority_and_fifo_order() (+4 more)

### Community 52 - "ZezEdit 2.0 — Feature Status Tracker"
Cohesion: 0.09
Nodes (21): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+13 more)

### Community 53 - "test_session23_real_media_ai_quality.py"
Cohesion: 0.08
Nodes (11): SubjectTrack, _compute_iou(), SubjectTracker, create_scenario_video(), test_moving_subject_occlusion_and_scene_cut(), test_moving_subject_tracking_left_to_right_and_visibility(), test_moving_subject_two_crossing_separate_tracks(), test_permanent_novelty_on_multiple_batches() (+3 more)

### Community 54 - "ZezEdit 2.0 — Media Storage & Processing Pipeline"
Cohesion: 0.26
Nodes (17): _setup_test_orchestrator(), test_case_01_normal_completion(), test_case_02_long_cpu_operation_heartbeat(), test_case_03_long_ffmpeg_child_process_alive(), test_case_04_slow_transcription_progress(), test_case_05_worker_thread_crash(), test_case_06_worker_process_crash(), test_case_07_worker_deadlock_detected() (+9 more)

### Community 55 - "error_envelope.schema.json"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 56 - "CharacterStudio.tsx"
Cohesion: 0.13
Nodes (24): CharacterStudio(), confirmCharacterCandidate(), detachCharacterObservation(), exportCharacterJson(), getCharacterCandidates(), getCharacterLibrary(), mergeCharacterCandidates(), rejectCharacterCandidate() (+16 more)

### Community 57 - "error_envelope.schema.json"
Cohesion: 0.11
Nodes (13): _check_storage_writable(), get_health(), get_system_diagnostics(), get_system_info(), get_system_resources(), DatabaseHealth, DependencyCheck, DiagnosticItem (+5 more)

### Community 58 - "MediaPipelineService"
Cohesion: 0.11
Nodes (19): 1. Prerequisites, 2. Installation commands, 3. Environment and setup steps, 4. Exact Windows PowerShell backend startup commands, 5. Exact Windows PowerShell frontend startup commands, 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12 & 13), AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Architecture & Documentation (+11 more)

### Community 59 - "Unslop"
Cohesion: 0.11
Nodes (18): ShortsCandidateRecord, AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Character Extraction Studio, Character Library & System Integration (Milestone 10), Core Backend, Database & Project Management (Milestone 2), Core Foundation & Architecture (Milestone 1), Core Product Workflow, Working Queue & Desktop Operations (Milestone 17), Frontend Application Shell, Dashboard & Design System (Milestone 3), Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11) (+10 more)

### Community 61 - "reframing_renderer.py"
Cohesion: 0.11
Nodes (17): type, type, properties, required, type, type, properties, code (+9 more)

### Community 62 - "properties"
Cohesion: 0.18
Nodes (5): _error_payload(), register_exception_handlers(), handle_app_error(), handle_unexpected_error(), handle_validation_error()

### Community 63 - "Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)"
Cohesion: 0.16
Nodes (4): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback()

### Community 64 - "get"
Cohesion: 0.17
Nodes (10): WorkflowStage, client(), seed_analysis_run(), seed_candidate(), seed_export(), test_batch_export_endpoint_success(), test_batch_export_validation_and_skipped(), test_media_workflow_api_endpoint() (+2 more)

### Community 65 - "test_candidate_human_review_workflow"
Cohesion: 0.12
Nodes (16): 1. Executive Summary & Historical Context, 2. Surviving Evidence Sources & Provenance, 3. Pre-Deletion Architecture & Data Flows, 4. Reconstructed Pre-Deletion Feature Inventory (20 Application Areas), 5. Milestone 13M.12 Deep-Dive Investigation, 6. Milestone 13M.13 Deep-Dive Investigation, 7. Historical UI Reconstruction, 8. Summary of Reconstructed Pre-Deletion Baseline (+8 more)

### Community 66 - "Tokens"
Cohesion: 0.12
Nodes (17): type, type, properties, type, type, type, type, clips (+9 more)

### Community 67 - "preview_user_data_cleanup_endpoint"
Cohesion: 0.12
Nodes (16): 1. Spacing, 2. Color, 3. Icons, 4. Copy, 5. Type, 6. Layout, 7. Details, 8. Visuals (+8 more)

### Community 68 - "analysis.py"
Cohesion: 0.06
Nodes (30): AnalysisRunResponse, AudioAnalysisItem, cancel_analysis(), create_or_update_transcript_correction(), delete_transcript_correction(), _format_run_response(), get_analysis_run(), get_audio_analysis() (+22 more)

### Community 69 - "pytest"
Cohesion: 0.11
Nodes (17): 1. Storage Separation & Source Immutability, 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First), 3. Smart Reframing & Portrait Rendering Architecture, 5. Milestone 4 Implementation Details: Media Ingestion & Proxies, 5. Video Analysis Engine (Milestone 5), 6. Smart Reframing & Dynamic Crop Renderer (Milestone 7), 7. Rendering Engine & Export Pipeline (Milestone 8), Authoritative Crop Math & Preview Parity (+9 more)

### Community 70 - "Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)"
Cohesion: 0.12
Nodes (16): 1. Overview, 1. Overview Tab, 2. Analysis Tab, 2. Context & State Flow, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Post-Import Action Flow, 4. Scenes Tab (+8 more)

### Community 71 - "WorkflowStateMachine"
Cohesion: 0.12
Nodes (16): type, exclusiveMinimum, type, type, properties, aspect_ratio, fps, project_id (+8 more)

### Community 72 - "README.md"
Cohesion: 0.15
Nodes (3): create_reframing_plan(), ReframingPlanRecord, ReframingRevisionRecord

### Community 73 - "Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)"
Cohesion: 0.18
Nodes (10): 1. Roadmap Architecture & Execution Principles, 2. Master Implementation Milestone Schedule, 3. Detailed Milestone Breakdown, Milestone 13: Exact Parity Specification & Pre-Deletion Architecture, Milestone 14: Interactive Reframing Review, Draggable Canvas & Keyframe Diamonds, Milestone 15: Video Analysis, AI Understanding & Temporal Context Restoration, Milestone 16: Multi-Track Timeline Audio Waveforms, Ducking & Word-Level Karaoke, Milestone 17: Core Product Workflow, Working Queue & Desktop Operations (+2 more)

### Community 74 - ".__init__"
Cohesion: 0.14
Nodes (4): TranscriptionResult, WhisperTranscriber, C. Restored Analysis Pipeline, Execution Stages

### Community 75 - "ZezEdit 2.0 — Milestone 13 Completion Report: ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan"
Cohesion: 0.13
Nodes (14): 10. Test and Acceptance Criteria, 11. Current Verified Restoration Coverage, 12. Recommended Next Implementation Milestone, 1. ZezEdit 1.0 Feature Inventory, 2. Historical Evidence References, 3. Exact Parity Requirements Identified, 4. Features Already Restored in ZezEdit 2.0, 5. Missing Functionality (Parity Gap) (+6 more)

### Community 76 - "2. Complete 100-Requirement Parity Matrix"
Cohesion: 0.14
Nodes (14): Accent, App layout, Buttons, Dark, Depth, Icons, Light, Motion (+6 more)

### Community 77 - "Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)"
Cohesion: 0.36
Nodes (11): _setup_orchestrator(), test_case_01_healthy_worker_long_operation_with_heartbeats(), test_case_02_worker_genuinely_blocked(), test_case_03_worker_crashed_external_process(), test_case_04_worker_raises_exception(), test_case_05_worker_completes_successfully(), test_case_06_worker_attempts_update_terminal_job(), test_case_07_worker_pid_is_local_string() (+3 more)

### Community 78 - "README.md"
Cohesion: 0.14
Nodes (14): Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`), `ZEZ-056`: Piecewise-Linear Dynamic FFmpeg Crop Filtergraph (13M.12), `ZEZ-057`: Burned-in Subtitles & Karaoke Word-Level ASS Styling, `ZEZ-058`: Professional Audio Processing & EBU R128 Loudness Normalization, `ZEZ-059`: Export Presets & Aspect Ratio Conversion, `ZEZ-060`: Strict Multi-Point Output Validation Gate, `ZEZ-061`: Poster Frame Cover Thumbnail Extraction, `ZEZ-062`: Render Progress Monitoring via FFmpeg `-progress` Pipe (+6 more)

### Community 79 - "VideoAnalysisPipeline"
Cohesion: 0.16
Nodes (6): VideoWorkflowStateResponse, WorkflowStateMachine, Milestone 18: Unified Video-to-Shorts Production Pipeline Checklist, 1. Executive Summary, 23. Graphify Knowledge Graph & Topological Codebase Health, 4. Authoritative Workflow Lifecycle State Machine

### Community 80 - "Signs of slop"
Cohesion: 0.18
Nodes (6): OutputValidator, test_output_validator_success_and_tampered_metadata(), test_output_validator_gate(), AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), Milestone 9: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing Checklist, AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

### Community 81 - "ai_providers.py"
Cohesion: 0.20
Nodes (10): Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`), `ZEZ-021`: Automated Audio Extraction for ASR, `ZEZ-022`: Faster-Whisper Local Speech Transcription, `ZEZ-023`: Word-Level Timestamp Alignment, `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer, `ZEZ-026`: FFmpeg Visual Scene Cut Detection, `ZEZ-027`: Keyframe Visual Lightbox & Filmstrip, `ZEZ-028`: Interval Frame Sampling for Visual Understanding (+2 more)

### Community 82 - "ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis"
Cohesion: 0.15
Nodes (12): 1. Parity Metrics & Scorecard Summary, 2. Complete 100-Requirement Parity Matrix, Domain A: Application Shell, Dashboard & Navigation, Domain B: Media Management, Proxies & Storage, Domain C: Video Analysis & Speech Understanding, Domain D & E: AI Multimodal Understanding & Highlight Discovery, Domain F: Smart Reframing & Subject Tracking (13M.12/13M.13), Domain G: Shorts Generation & FFmpeg Rendering (+4 more)

### Community 83 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.15
Nodes (13): Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`), `ZEZ-069`: Multi-Track Timeline NLE Canvas, `ZEZ-070`: Non-Destructive Clip Trimming & Splitting, `ZEZ-071`: Ripple Delete & Gap Closing, `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing, `ZEZ-073`: Persistent Timeline Undo & Redo History, `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration, `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`) (+5 more)

### Community 84 - "README.md"
Cohesion: 0.11
Nodes (12): 1. Overview & Principles, 2. Database Schema (Migration `0009_character_studio.sql`), 3. Human Review Operations, 4. Documented JSON Export Schema, Fundamental Constraints & Transparency Principles, ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library, 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction (+4 more)

### Community 85 - "Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)"
Cohesion: 0.17
Nodes (11): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification, Milestone 6: AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking Verification (+3 more)

### Community 86 - "Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 87 - "Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)"
Cohesion: 0.18
Nodes (10): 1. Executive Summary, 2. Unslop Visual & Interaction Audit, 3. Product Workflow Gap Analysis, 4. Feature Recovery Matrix, 5. Unslop Design Direction for ZezEdit 2.0, A. Surfaces and Colors, B. Typography & Copy, Current Broken Workflow: (+2 more)

### Community 88 - "test_milestone20_production_reliability.py"
Cohesion: 0.11
Nodes (12): app_and_client(), create_test_video(), create_test_wav(), test_audio_extractor_bounded_chunk(), test_media_integrity_and_relinking(), client(), test_automatic_shorts_generation_enqueues_export_render(), test_candidate_script_deletion_and_re_rendering() (+4 more)

### Community 89 - "._generate_thumbnail"
Cohesion: 0.18
Nodes (11): 3. Core Functional Modules (A–J), Module A — Dashboard & Project Management, Module B — Media Library, Module C — Video Analysis, Module D — Highlight Discovery, Module E — Smart Reframing, Module F — Multi-Track Timeline Editor, Module G — AI Video Editor (+3 more)

### Community 90 - "ZezEdit 2.0 — API Design & Conventions"
Cohesion: 0.18
Nodes (11): Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`), `ZEZ-011`: Video Drag-and-Drop & File Picker Ingestion, `ZEZ-012`: Automated FFprobe Container & Stream Dissection, `ZEZ-013`: Fast Edit Proxy Generation (480p), `ZEZ-014`: Poster Frame & Thumbnail Strip Generation, `ZEZ-015`: Audio File Ingestion & Waveform Prep, `ZEZ-016`: Image File Ingestion for Overlays & Watermarks, `ZEZ-017`: Safe Isolated Storage Layout (+3 more)

### Community 91 - "ZezEdit 2.0 — API Design & Conventions"
Cohesion: 0.18
Nodes (11): Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`), `ZEZ-031`: Local Multimodal Vision Integration (Ollama), `ZEZ-032`: Multimodal Context Aggregator, `ZEZ-033`: Explainable 9-Factor Highlight Scoring Engine, `ZEZ-034`: Narrative Setup and Payoff Boundary Preservation, `ZEZ-035`: Categorized Shorts Candidate Ranking, `ZEZ-036`: Hook Rationale & Explanation Card, `ZEZ-037`: Candidate Review & Approval Workflow (+3 more)

### Community 92 - "Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)"
Cohesion: 0.18
Nodes (11): Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`), `ZEZ-081`: Evidence-Based Character Extraction Pipeline (Non-3D), `ZEZ-082`: Spatial-Temporal Candidate Clustering (DBSCAN), `ZEZ-083`: Character Observation Gallery & Thumbnails, `ZEZ-084`: Screen-Time Transparency Analytics, `ZEZ-085`: Unverified Dialogue Correlation with Disclaimer, `ZEZ-086`: Human Review Controls: Inline Renaming, `ZEZ-087`: Human Review Controls: Confirm to Persistent Character Library (+3 more)

### Community 93 - "character.py"
Cohesion: 0.18
Nodes (11): Domain J: System Infrastructure, Diagnostics & Reliability (`ZEZ-091` – `ZEZ-100`), `ZEZ-091`: Forward-Only Versioned SQLite Migrations, `ZEZ-092`: Pre-Migration Automatic Database Snapshot, `ZEZ-093`: Path Traversal & Anti-Root Recursive Deletion Guard, `ZEZ-094`: Single Authoritative Job Orchestrator & State Machine, `ZEZ-095`: Unclean Shutdown Recovery of Interrupted Jobs, `ZEZ-096`: Comprehensive Health & Diagnostics Probe (`/api/v1/health`), `ZEZ-097`: Graphify Knowledge Graph Auto-Maintenance (+3 more)

### Community 94 - "subprocess"
Cohesion: 0.07
Nodes (10): character_env(), export_env(), test_real_ffmpeg_reframing_render(), m8_env(), timeline_env(), client(), create_synthetic_test_video(), test_batch_render_recovery_action() (+2 more)

### Community 95 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.20
Nodes (9): 1. API Versioning & Base Prefix, 2. Resource Naming & HTTP Method Conventions, 3. Standard Request & Response Conventions, 4. Implemented vs Planned Endpoint Inventory, Centralized Error Response Contract, Implemented in Milestones 1–6, Planned Endpoints (Milestones 10–12), Success Envelopes (+1 more)

### Community 96 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.18
Nodes (11): Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`), `ZEZ-001`: Studio Application Shell & Responsive Drawer, `ZEZ-002`: Studio Dashboard View, `ZEZ-003`: Project Management & Lifecycle Operations, `ZEZ-004`: Unified Video Workspace Navigation, `ZEZ-005`: Post-Import Guided Ingestion Flow, `ZEZ-006`: System Monitor & Hardware Resource Widget, `ZEZ-007`: Studio Light / Dark Theme Synchronization (+3 more)

### Community 97 - "test_milestone5_analysis.py"
Cohesion: 0.23
Nodes (8): NormalizedSegment, segment_dialogue_turns(), SegmentWord, SpeechTurn, test_analysis_api_flow(), test_audio_extractor(), test_speech_segmentation(), test_temporal_aggregator_query()

### Community 98 - "ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)"
Cohesion: 0.18
Nodes (9): AnalysisRunRecord, CandidateClipEditRecord, ProjectEventRecord, SampledFrameRecord, SpeechTurnRecord, TranscriptSegmentRecord, VideoSceneRecord, VisualObservationRecord (+1 more)

### Community 99 - "compilerOptions"
Cohesion: 0.21
Nodes (5): client(), test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint()

### Community 100 - "SKILL.md"
Cohesion: 0.22
Nodes (8): 1. Engine & Pragmas, 2. Versioned Migration Strategy (Historical Lesson Applied), 3. Planned Domain Entity Relationship Diagram, 4. Schema Breakdown: Implemented vs Planned, 5. Limitations & Alternatives Considered, Implemented Tables (Migrations 0001–0005), Planned Tables for Subsequent Milestones (Schema Blueprint), ZezEdit 2.0 — Database Design & Migration Strategy

### Community 101 - "Effects"
Cohesion: 0.22
Nodes (8): 1. Core Mandate: One Single Job System, 2. Job States & Lifecycle Transitions, 3. Canonical Job Types & Concurrency Policy, 4. Worker Ownership & Child Process PID Registry, 5. Restart Recovery Rules, 6. Retry Rules & Per-Job Logs, 7. Alternatives Considered & Limitations, ZezEdit 2.0 — Authoritative Job Orchestration Design

### Community 102 - "Visuals"
Cohesion: 0.22
Nodes (8): ADR-01: Single Local Monolith (FastAPI + React) vs Microservices, ADR-02: CPU-First Local Processing & Streaming I/O, ADR-03: SQLite WAL + Forward-Only SQL Migrations, ADR-04: Centralized Error Handling & Structured Logging, ADR-06: Decoupled Evidence-Based Character Extraction (No 3D Studio), ADR-07: Testing Strategy (Multi-Layer Gate), ADR-08: Shared Contract Directory (`shared/contracts/`), ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)

### Community 103 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.22
Nodes (8): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, strict, include

### Community 104 - "Effects"
Cohesion: 0.25
Nodes (7): 1. Overview & Guiding Principles, 2. High-Level System Architecture, 3. Frontend Module Boundaries (`frontend/src/`), 6. Windows 11 Startup & Shutdown Lifecycle, Graceful Shutdown Sequence, Startup Sequence, ZezEdit 2.0 — System Architecture

### Community 106 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.29
Nodes (7): Dithering, Duotone, Effects, Glyphs, Halftone dots, Implementation, Performance

### Community 107 - "F. Test Evidence Summary"
Cohesion: 0.29
Nodes (7): Decide what the visual is, Generate it, Objects for moments, Prompt recipe, Put it on the page, Styles that work, Visuals

### Community 108 - "test_session12_large_library.py"
Cohesion: 0.09
Nodes (7): configure_logging(), large_library_service(), test_large_library_aspect_and_status_filters(), test_large_library_offset_limit_stability(), test_large_library_payload_size_comparison(), test_large_library_search_filter(), test_large_library_sorting()

### Community 109 - "test_session6c_rendering_and_batch_export.py"
Cohesion: 0.23
Nodes (7): _create_test_mp4(), _setup_test_env(), test_audio_preservation_and_silent_video_support(), test_batch_export_rendering_pipeline(), test_output_verification_rejects_corrupted_renders(), test_render_candidate_with_clip_editing_integration(), test_standard_presets_catalog_all_aspect_ratios()

### Community 111 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.08
Nodes (24): 1. Backend Pytest Suite, 1. Character Extraction Studio & Character Library (Milestone 10), 2. Frontend Vitest Suite, 2. Smart Reframing & Subject Tracking (Milestone 7), 3. TypeScript Type Checking, 3. Video Analysis & Multimodal Understanding (Milestone 5), 4. AI Highlight Discovery & Shorts Candidate Ranking (Milestone 6), 4. Frontend Production Build (+16 more)

### Community 112 - "6. Multiple Shorts Batch Export Engine"
Cohesion: 0.29
Nodes (6): 1. Product Vision & Mission Statement, 2. Requirement Taxonomy & Numbering, 3. Detailed Specification by Domain, 4. Summary Parity Ledger, Core Architecture Axioms, ZezEdit 1.0 — Exact Product Parity Specification

### Community 113 - ".validate_external_path"
Cohesion: 0.33
Nodes (5): 1. Mission & Product Vision, 2. Hardware & Resource Constraints (Mandatory), 4. Mandatory Data Protection & Reliability Rules, 5. Planned Milestone Sequence, ZezEdit 2.0 — Master Requirements Specification

### Community 114 - "base.py"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 115 - "character_env"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 116 - "timeline_env"
Cohesion: 0.40
Nodes (5): required, type, tracks, items, type

### Community 117 - "pytest"
Cohesion: 0.07
Nodes (20): BoundaryViolationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory(), validate_storage_root_path(), test_health_and_system_info_endpoints() (+12 more)

### Community 119 - "height"
Cohesion: 0.50
Nodes (4): 6. Multiple Shorts Batch Export Engine, Batch Export Request Payload:, Batch Export Response Payload:, Output File Organization:

### Community 120 - "test_session21_multimodal_intelligence_and_tracking.py"
Cohesion: 0.12
Nodes (8): build_crop_filter_expression(), _simplify_keyframes(), get_temporal_context_at(), TemporalContext, create_moving_subject_video(), test_alternate_exports_same_candidate(), test_moving_subject_tracking_and_dynamic_crop(), test_permanent_novelty_ledger_survives_deletions()

### Community 122 - "schema_version"
Cohesion: 0.67
Nodes (3): minimum, type, duration_sec

### Community 123 - "source_kind"
Cohesion: 0.67
Nodes (3): minimum, type, height

### Community 124 - "width"
Cohesion: 0.67
Nodes (3): enum, type, kind

### Community 125 - "zoom_px_per_sec"
Cohesion: 0.67
Nodes (3): minimum, type, playhead_sec

### Community 126 - "api/__init__.py"
Cohesion: 0.67
Nodes (3): schema_version, const, type

### Community 127 - ".cors_origin_list"
Cohesion: 0.67
Nodes (3): source_kind, enum, type

### Community 128 - "core/__init__.py"
Cohesion: 0.67
Nodes (3): width, minimum, type

### Community 129 - ".ensure_directories"
Cohesion: 0.67
Nodes (3): zoom_px_per_sec, minimum, type

### Community 145 - "test_session15_endurance_and_recovery.py"
Cohesion: 0.10
Nodes (12): _heartbeat_ticker(), test_jobs_stalled_detector_with_non_numeric_pid(), mock_settings(), temp_db(), test_enforce_completion_evidence_missing(), test_heartbeat_ticker_keeps_ticking_with_active_callbacks(), _run_test(), test_watchdog_detects_stalled_job_when_heartbeats_stop() (+4 more)

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1545 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `config.py` to `subprocess`, `config.py`, `MediaService`, `Settings`, `sqlite3`, `.from_root`, `Settings`, `.from_root`, `core.py`, `ProjectService`, `test_session15_endurance_and_recovery.py`, `StorageLayout`, `create_app`, `HighlightDiscoveryEngine`, `ZezEdit 2.0 — Milestone 17 Verification & Restoration Report`, `SettingsService`, `MediaPipelineService`, `characters.py`, `test_session17_queue_and_workflow.py`, `ZezEdit 2.0 — Media Storage & Processing Pipeline`, `error_envelope.schema.json`, `pytest`, `.__init__`, `Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)`, `README.md`, `ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis`, `test_milestone20_production_reliability.py`, `character.py`, `ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)`, `Effects`, `test_session6c_rendering_and_batch_export.py`, `ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report`, `pytest`, `test_milestone19_desktop_operations.py`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `subprocess` be split into smaller, more focused modules?**
  _Cohesion score 0.06896551724137931 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `README.md` to `config.py`, `projects.ts`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `cancel_job()`) actually correct?**
  _`JobOrchestrator` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Should `config.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07377706495589414 - nodes in this community are weakly interconnected._