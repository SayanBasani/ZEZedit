# Graph Report - ZezEdit  (2026-11-15)

## Corpus Check
- 221 files · ~377,007 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .xml 3, .example 1, (none) 1)

## Summary
- 3469 nodes · 9771 edges · 150 communities (124 shown, 26 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1105 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f0a97396`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- subprocess
- AppError
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
- StorageLayout
- core.py
- ProjectService
- sqlite_session
- _heartbeat_ticker
- sqlite3
- config.py
- test_milestone5_analysis.py
- NotFoundError
- StorageLayout
- start_highlight_discovery
- create_app
- ExportService
- get_health
- analysis.py
- TimelineService
- test_milestone9_timeline.py
- .create_backup
- post
- ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification
- SubjectTracker
- ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration
- HighlightDiscoveryEngine
- settings.py
- ZezEdit 2.0 — Milestone 17 Verification & Restoration Report
- CropKeyframe
- SettingsService
- get_settings
- base.py
- CharacterCandidate
- ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report
- ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification
- MediaPipelineService
- ZezEdit 2.0 — Local-First AI Video Editor
- characters.py
- compilerOptions
- ZezEdit 2.0 — Feature Status Tracker
- BackupService
- ZezEdit 2.0 — Media Storage & Processing Pipeline
- error_envelope.schema.json
- .generate_framing_keyframes
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
- 3. Detailed Milestone Breakdown
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- character_service.py
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- ZezEdit 2.0 — API Design & Conventions
- Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)
- character.py
- create_synthetic_test_video
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Database Design & Migration Strategy
- get_temporal_context_at
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
- README.md
- items
- .clear_all_user_data
- 2. Canonical Data Models
- 6. Multiple Shorts Batch Export Engine
- .validate_external_path
- base.py
- character_env
- timeline_env
- delete_transcript_correction
- clip_edits.py
- height
- create_moving_subject_video
- get_recovery_status_endpoint
- schema_version
- source_kind
- width
- zoom_px_per_sec
- api/__init__.py
- .cors_origin_list
- core/__init__.py
- .ensure_directories
- list_ai_providers
- zezedit-backend
- .check_asset_integrity
- temp_db
- test_stale_queued_job_timeout_cleanup
- test_atomic_job_claiming_guarantee
- test_timeline_redo_empty_stack_validation

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 237 edges
2. `Settings` - 144 edges
3. `JobOrchestrator` - 143 edges
4. `request()` - 130 edges
5. `StorageLayout` - 93 edges
6. `AppError` - 82 edges
7. `get_settings()` - 82 edges
8. `NotFoundError` - 77 edges
9. `create_app()` - 75 edges
10. `run_migrations()` - 71 edges

## Surprising Connections (you probably didn't know these)
- `Non-Destructive Transcript Corrections (`ZEZ-025`)` --references--> `get_transcript()`  [INFERRED]
  docs/reports/milestone_15_analysis_restoration_report.md → backend/app/api/v1/analysis.py
- `Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration` --references--> `ExportService`  [INFERRED]
  docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md → backend/app/services/export_service.py
- `15. Multi-Track Timeline & Custom Clip Editing` --references--> `ExportService`  [INFERRED]
  docs/reports/milestone_18_unified_video_to_shorts_pipeline_report.md → backend/app/services/export_service.py
- `**Milestone 13: Interactive Reframing Review, Draggable Crop Canvas & Versioned Render History**` --references--> `FramingEngine`  [INFERRED]
  docs/reports/milestone_12_reconstruction_report.md → backend/app/services/framing_engine.py
- `Components` --references--> `get_temporal_context_at()`  [INFERRED]
  docs/architecture/MEDIA_PIPELINE.md → backend/app/services/temporal_aggregator.py

## Import Cycles
- None detected.

## Communities (150 total, 26 thin omitted)

### Community 0 - "subprocess"
Cohesion: 0.06
Nodes (32): ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream(), sample_analysis_frames(), _sample_one() (+24 more)

### Community 1 - "AppError"
Cohesion: 0.06
Nodes (24): AppError, BoundaryViolationError, MigrationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory() (+16 more)

### Community 2 - "CharacterService"
Cohesion: 0.05
Nodes (102): CharacterStudio(), ProjectsView(), TimelineEditor(), addTimelineTextOverlay(), addTimelineTrack(), ApiClientError, approveAIPlan(), archiveProject() (+94 more)

### Community 3 - "JobOrchestrator"
Cohesion: 0.05
Nodes (32): confirm_candidate(), detach_observation(), export_character(), get_character_service(), get_extraction_job(), get_library_character(), list_candidates(), list_library_characters() (+24 more)

### Community 4 - "config.py"
Cohesion: 0.05
Nodes (39): lifespan(), _queue_poller(), JobRecord, JobOrchestrator, test_job_retry_lifecycle_and_event_timeline(), test_queue_stats_aggregation(), test_job_checkpointing_and_recovery(), test_resource_aware_scheduler_and_priority() (+31 more)

### Community 5 - "MediaService"
Cohesion: 0.08
Nodes (14): get_media(), get_media_global(), get_media_proxy_global(), get_media_thumbnail_global(), get_proxy_file(), get_thumbnail_file(), stream_media_global(), update_media() (+6 more)

### Community 6 - "v1/timeline.py"
Cohesion: 0.05
Nodes (62): ResourceInspector(), DocumentationView(), AIProviderManager(), categorizeJobType(), CategoryFilter, formatDuration(), formatTimeOnly(), ProcessesManagerView (+54 more)

### Community 7 - "v1/reframing.py"
Cohesion: 0.07
Nodes (59): 4. Post-Import Action Flow, Milestone 3 — Frontend Application Shell, Dashboard & Design System, `ZEZ-005`: Post-Import Guided Ingestion Flow, Badge(), BadgeProps, Button(), ButtonProps, ConfirmDialog() (+51 more)

### Community 8 - "Button"
Cohesion: 0.08
Nodes (66): Card(), CardProps, EmptyState(), AnalysisWorkspace(), AspectRatioOption, CREATIVE_DIRECTION_LABELS, CreativeDirectionOption, SingleVideoStudio() (+58 more)

### Community 9 - "Settings"
Cohesion: 0.04
Nodes (19): Settings, StorageService, m15_env(), storage_jobs_env(), test_temp_cache_cleanup_execute_with_valid_token(), test_temp_cache_cleanup_invalid_token_rejected(), env(), media_env() (+11 more)

### Community 10 - "AppError"
Cohesion: 0.05
Nodes (56): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, App(), NavSection, SidebarNavButton(), SidebarNavButtonProps, defaultToastValue (+48 more)

### Community 11 - "ExportService"
Cohesion: 0.05
Nodes (20): BatchExportItem, BatchExportRequest, BatchExportResponse, cancel_export(), create_batch_export_jobs(), create_export_preview(), create_export_render_job(), delete_export() (+12 more)

### Community 12 - "sqlite3"
Cohesion: 0.06
Nodes (31): ClipEditingService, _setup_test_orchestrator(), test_active_external_child_pid_never_marked_stalled_within_grace(), test_checkpoint_never_heals_failed_status(), test_complete_job_rejects_failed_status(), test_completed_or_100pct_job_never_marked_stalled(), test_dead_os_pid_marked_stalled_after_grace(), test_in_process_job_stalls_when_silent_beyond_timeout() (+23 more)

### Community 13 - "system.ts"
Cohesion: 0.06
Nodes (21): add_text_overlay(), approve_plan(), create_timeline(), delete_clip(), delete_track(), duplicate_clip(), get_ai_editor_service(), get_command_service() (+13 more)

### Community 14 - ".from_root"
Cohesion: 0.06
Nodes (17): download_export_video(), AudioConfig, CaptionConfig, RenderExportRequest, ValidationDetails, AudioPipeline, hex_to_ass_color(), test_audio_pipeline_loudnorm_and_volume_filter_chains() (+9 more)

### Community 15 - "Settings"
Cohesion: 0.10
Nodes (32): AddTextOverlayRequest, AIConversation, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType, ContentProps (+24 more)

### Community 16 - "StorageLayout"
Cohesion: 0.05
Nodes (28): get_settings_service(), get_analysis_pipeline(), get_db_path(), create_backup(), get_backup_service(), restore_backup(), get_clip_editing_service(), get_export_service() (+20 more)

### Community 17 - "core.py"
Cohesion: 0.07
Nodes (32): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, CandidateResponse, delete_candidate(), DiscoverHighlightsRequest, generate_more_highlights() (+24 more)

### Community 18 - "ProjectService"
Cohesion: 0.09
Nodes (19): check_project_media_integrity(), generate_proxy_endpoint(), get_media_service(), get_media_workflow_state(), get_pipeline_service(), import_local_file(), import_local_file_global(), inspect_relink() (+11 more)

### Community 19 - "sqlite_session"
Cohesion: 0.07
Nodes (42): 7. Video Workspace Implementation, BatchExportModal(), BatchExportModalProps, DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), ASPECT_RATIO_OPTIONS, CandidateClipEditorModal() (+34 more)

### Community 20 - "_heartbeat_ticker"
Cohesion: 0.50
Nodes (4): _heartbeat_ticker(), _ticker(), test_heartbeat_ticker_keeps_ticking_with_active_callbacks(), _run_test()

### Community 21 - "sqlite3"
Cohesion: 0.08
Nodes (41): AnalysisWorkspaceProps, CharacterStudioProps, ExportStudioProps, HighlightsWorkspace(), HighlightsWorkspaceProps, PostImportModalProps, ReframingReviewModal(), ReframingReviewModalProps (+33 more)

### Community 22 - "config.py"
Cohesion: 0.04
Nodes (22): _backup_before_upgrade(), _file_sha256(), MigrationResult, _parse_version_and_name(), run_migrations(), test_real_ffmpeg_reframing_render(), large_library_service(), test_large_library_aspect_and_status_filters() (+14 more)

### Community 23 - "test_milestone5_analysis.py"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 24 - "NotFoundError"
Cohesion: 0.08
Nodes (11): NotFoundError, ValidationError, TimelineClip, UpdateClipPropsRequest, TimelineCommandService, test_timeline_consecutive_undo_redo_stack(), test_timeline_new_command_clears_redo_history(), test_timeline_track_deletion_and_clip_cascade() (+3 more)

### Community 25 - "StorageLayout"
Cohesion: 0.13
Nodes (11): DetectedSubject, SubjectTrack, FramingEngine, calculate_aspect_ratio(), test_framing_strategies_single_two_person_and_group(), test_creative_direction_aliases_and_educational(), test_framing_engine_center_and_speaker_strategies(), test_framing_engine_action_object_framing() (+3 more)

### Community 26 - "start_highlight_discovery"
Cohesion: 0.06
Nodes (37): dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49 (+29 more)

### Community 27 - "create_app"
Cohesion: 0.04
Nodes (27): configure_logging(), create_app(), test_character_api_routes(), test_silent_video_analysis_pipeline(), test_standard_video_analysis_and_caching(), test_temporal_context_and_thumbnails_serving(), client(), app_and_client() (+19 more)

### Community 28 - "ExportService"
Cohesion: 0.10
Nodes (12): get_analysis_cache(), compute_source_signature(), _now_utc(), VideoAnalysisPipeline, on_transcribe_progress(), run_real_video_verification(), test_create_analysis_run_idempotency(), test_full_timeline_coverage_and_temporal_alignment() (+4 more)

### Community 29 - "get_health"
Cohesion: 0.09
Nodes (12): CreateReframingPlanRequest, get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), ManualOverrideItem, preview_crop_geometry(), render_reframed_video(), RenderRevisionRequest (+4 more)

### Community 30 - "analysis.py"
Cohesion: 0.08
Nodes (8): get_ai_conversation(), get_plan(), list_plans(), reject_plan(), send_ai_message(), AIEditingPlan, AIEditorService, test_ai_video_editor_assistant()

### Community 31 - "TimelineService"
Cohesion: 0.09
Nodes (8): add_track(), get_active_timeline(), update_track(), TimelineRecord, TimelineTrack, TimelineService, timeline_env(), test_timeline_rendering_pipeline()

### Community 32 - "test_milestone9_timeline.py"
Cohesion: 0.10
Nodes (28): test_ai_provider(), get_doc_article(), list_doc_articles(), list_doc_categories(), AIProviderCapability, AIProviderDTO, AIProviderTestRequest, AIProviderTestResponse (+20 more)

### Community 34 - "post"
Cohesion: 0.09
Nodes (19): archive_project(), create_project(), delete_project(), get_project(), get_project_events(), list_projects(), restore_project(), update_project() (+11 more)

### Community 35 - "ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification"
Cohesion: 0.10
Nodes (7): get_db_integrity_endpoint(), get_storage_breakdown_endpoint(), inspect_storage_endpoint(), preview_user_data_cleanup_endpoint(), _format_bytes(), test_storage_breakdown_categories_accuracy(), test_temp_cache_cleanup_preview_no_file_deletion()

### Community 36 - "SubjectTracker"
Cohesion: 0.09
Nodes (21): A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, D. Audio and Transcription, Database Migration: `0010_transcript_corrections_and_audio.sql`, E. Scene Detection, F. Visual Understanding, Files Created, G. Temporal Context Aggregation (+13 more)

### Community 37 - "ZezEdit 2.0 — Milestone 15 Report: Video Analysis, AI Understanding & Temporal Context Engine Restoration"
Cohesion: 0.07
Nodes (30): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+22 more)

### Community 38 - "HighlightDiscoveryEngine"
Cohesion: 0.07
Nodes (17): format_timestamp(), GeneratedCandidate, HighlightDiscoveryEngine, _now_utc(), QualityGateResult, ScoreBreakdown, main(), test_highlight_discovery_engine() (+9 more)

### Community 39 - "settings.py"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 40 - "ZezEdit 2.0 — Milestone 17 Verification & Restoration Report"
Cohesion: 0.11
Nodes (12): cancel_job(), create_job(), delete_job(), delete_jobs_history(), _enrich_job_response(), get_job(), get_job_checkpoint(), get_job_logs() (+4 more)

### Community 41 - "CropKeyframe"
Cohesion: 0.12
Nodes (8): CropKeyframe, build_crop_filter_expression(), _simplify_keyframes(), test_preview_and_renderer_expression_parity(), test_crop_filter_expression_constant_y_simplification(), test_crop_filter_expression_stationary_crop(), test_dynamic_crop_filter_expression_generation(), `ZEZ-055`: Authoritative Preview-to-Render Mathematical Parity (13M.12/13M.13)

### Community 42 - "SettingsService"
Cohesion: 0.09
Nodes (15): render_timeline(), ExportPreset, TimelineRenderRequest, _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models (+7 more)

### Community 43 - "get_settings"
Cohesion: 0.19
Nodes (5): get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 45 - "CharacterCandidate"
Cohesion: 0.13
Nodes (6): CaptionEngine, format_ass_timestamp(), test_caption_engine_ass_file_generation_and_styling(), test_caption_engine_empty_segments(), test_format_ass_timestamp_precision(), test_caption_engine_ass_generation()

### Community 46 - "ZezEdit 2.0 — Milestone 18: Unified Video-to-Shorts Production Pipeline Report"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 47 - "ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification"
Cohesion: 0.17
Nodes (9): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, clear_all_user_data_endpoint(), ClearAllDataRequest, create_backup_endpoint(), execute_cleanup_endpoint(), preview_cleanup_endpoint() (+1 more)

### Community 48 - "MediaPipelineService"
Cohesion: 0.14
Nodes (6): delete_media(), delete_media_global(), get_media_stats(), MediaStorageStatsResponse, MediaPipelineService, test_media_pipeline_proxy_lifecycle_and_delete()

### Community 49 - "ZezEdit 2.0 — Local-First AI Video Editor"
Cohesion: 0.12
Nodes (15): ReframingRenderer, Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12) (+7 more)

### Community 50 - "characters.py"
Cohesion: 0.16
Nodes (8): ProviderHealth, SpeechToTextProvider, StructuredPlanResult, TextLLMProvider, VisionLanguageProvider, 4. Backend Module Boundaries (`backend/app/`), 5. AI Provider Abstraction Boundaries, ADR-05: Dynamic Authoritative AI Provider Abstraction

### Community 51 - "compilerOptions"
Cohesion: 0.10
Nodes (13): _format_run_response(), get_analysis_run(), get_audio_analysis(), get_context(), get_frame_image(), get_sampled_frames(), get_scene_thumbnail(), get_scenes() (+5 more)

### Community 52 - "ZezEdit 2.0 — Feature Status Tracker"
Cohesion: 0.09
Nodes (21): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+13 more)

### Community 53 - "BackupService"
Cohesion: 0.11
Nodes (6): _compute_iou(), SubjectTracker, test_moving_subject_tracking_and_dynamic_crop(), test_subject_tracker_detection_person_and_object(), test_subject_tracker_multi_subject_tracking_separate_tracks(), test_subject_tracker_scene_cut_termination()

### Community 54 - "ZezEdit 2.0 — Media Storage & Processing Pipeline"
Cohesion: 0.27
Nodes (17): _setup_test_orchestrator(), test_case_01_normal_completion(), test_case_02_long_cpu_operation_heartbeat(), test_case_03_long_ffmpeg_child_process_alive(), test_case_04_slow_transcription_progress(), test_case_05_worker_thread_crash(), test_case_06_worker_process_crash(), test_case_07_worker_deadlock_detected() (+9 more)

### Community 55 - "error_envelope.schema.json"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 56 - ".generate_framing_keyframes"
Cohesion: 0.15
Nodes (3): test_portrait_crop_geometry_and_bounds(), test_trajectory_smoothing_and_scene_cut_isolation(), `ZEZ-044`: Boundary Safety Containment (13M.12)

### Community 57 - "error_envelope.schema.json"
Cohesion: 0.15
Nodes (8): DatabaseHealth, DependencyCheck, DiagnosticItem, HealthResponse, OllamaHealth, StorageHealth, SystemDiagnosticsResponse, SystemInfoResponse

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
Nodes (5): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback(), 3. Video Analysis & Multimodal Understanding (Milestone 5)

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
Cohesion: 0.10
Nodes (18): AnalysisRunResponse, AudioAnalysisItem, cancel_analysis(), create_or_update_transcript_correction(), delete_transcript_correction(), get_analysis_telemetry(), _now_utc(), retry_analysis() (+10 more)

### Community 69 - "pytest"
Cohesion: 0.11
Nodes (17): 1. Storage Separation & Source Immutability, 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First), 3. Smart Reframing & Portrait Rendering Architecture, 5. Milestone 4 Implementation Details: Media Ingestion & Proxies, 5. Video Analysis Engine (Milestone 5), 6. Smart Reframing & Dynamic Crop Renderer (Milestone 7), 7. Rendering Engine & Export Pipeline (Milestone 8), Authoritative Crop Math & Preview Parity (+9 more)

### Community 70 - "Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)"
Cohesion: 0.20
Nodes (10): 1. Overview Tab, 2. Analysis Tab, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Scenes Tab, 5. AI Highlights Tab, 6. Smart Reframing Tab, 7. Shorts & Export Tab (+2 more)

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
Cohesion: 0.18
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
Cohesion: 0.15
Nodes (12): test_non_destructive_transcript_corrections(), Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`), `ZEZ-021`: Automated Audio Extraction for ASR, `ZEZ-022`: Faster-Whisper Local Speech Transcription, `ZEZ-023`: Word-Level Timestamp Alignment, `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer, `ZEZ-025`: Non-Destructive Transcript Text Corrections, `ZEZ-026`: FFmpeg Visual Scene Cut Detection (+4 more)

### Community 82 - "ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis"
Cohesion: 0.15
Nodes (12): 1. Parity Metrics & Scorecard Summary, 2. Complete 100-Requirement Parity Matrix, Domain A: Application Shell, Dashboard & Navigation, Domain B: Media Management, Proxies & Storage, Domain C: Video Analysis & Speech Understanding, Domain D & E: AI Multimodal Understanding & Highlight Discovery, Domain F: Smart Reframing & Subject Tracking (13M.12/13M.13), Domain G: Shorts Generation & FFmpeg Rendering (+4 more)

### Community 83 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.15
Nodes (13): Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`), `ZEZ-069`: Multi-Track Timeline NLE Canvas, `ZEZ-070`: Non-Destructive Clip Trimming & Splitting, `ZEZ-071`: Ripple Delete & Gap Closing, `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing, `ZEZ-073`: Persistent Timeline Undo & Redo History, `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration, `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`) (+5 more)

### Community 84 - "3. Detailed Milestone Breakdown"
Cohesion: 0.29
Nodes (6): 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction, 4. Export Overwrite & Confirmation Rules, 5. AI Video Editor Security Boundary, 6. Backup & Restore Strategy, ZezEdit 2.0 — Security & Data Safety Architecture

### Community 85 - "Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)"
Cohesion: 0.17
Nodes (11): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification, Milestone 6: AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking Verification (+3 more)

### Community 86 - "Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 87 - "Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)"
Cohesion: 0.18
Nodes (10): 1. Executive Summary, 2. Unslop Visual & Interaction Audit, 3. Product Workflow Gap Analysis, 4. Feature Recovery Matrix, 5. Unslop Design Direction for ZezEdit 2.0, A. Surfaces and Colors, B. Typography & Copy, Current Broken Workflow: (+2 more)

### Community 88 - "character_service.py"
Cohesion: 0.33
Nodes (6): G. Recommended Next Five Corrective Milestones, Priority 1: Milestone 12 — Real Vision & Face Detection Engine (Fix DEF-02 & DEF-03), Priority 2: Milestone 13 — Conversational LLM Editor Integration (Fix DEF-04), Priority 3: Milestone 14 — Timeline Multi-Track Advanced Editing & Ripple Operations, Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration, Priority 5: Milestone 16 — Production Desktop Packaging & Offline Installer

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

### Community 94 - "create_synthetic_test_video"
Cohesion: 0.20
Nodes (5): client(), create_synthetic_test_video(), test_batch_render_recovery_action(), test_failed_render_preserves_script_and_retry_works(), test_five_candidates_generate_five_exports_and_mp4s()

### Community 95 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.20
Nodes (9): 1. API Versioning & Base Prefix, 2. Resource Naming & HTTP Method Conventions, 3. Standard Request & Response Conventions, 4. Implemented vs Planned Endpoint Inventory, Centralized Error Response Contract, Implemented in Milestones 1–6, Planned Endpoints (Milestones 10–12), Success Envelopes (+1 more)

### Community 96 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.20
Nodes (10): Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`), `ZEZ-001`: Studio Application Shell & Responsive Drawer, `ZEZ-002`: Studio Dashboard View, `ZEZ-003`: Project Management & Lifecycle Operations, `ZEZ-004`: Unified Video Workspace Navigation, `ZEZ-006`: System Monitor & Hardware Resource Widget, `ZEZ-007`: Studio Light / Dark Theme Synchronization, `ZEZ-008`: Notification Center & Job Completion Toasts (+2 more)

### Community 97 - "get_temporal_context_at"
Cohesion: 0.40
Nodes (3): get_temporal_context_at(), TemporalContext, test_temporal_aggregator_query()

### Community 98 - "ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)"
Cohesion: 0.22
Nodes (8): AnalysisRunRecord, CandidateClipEditRecord, SampledFrameRecord, SpeechTurnRecord, TranscriptSegmentRecord, VideoSceneRecord, VisualObservationRecord, B. Architectural Query Examples Executed

### Community 99 - "compilerOptions"
Cohesion: 0.22
Nodes (4): test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint()

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

### Community 108 - "README.md"
Cohesion: 0.18
Nodes (5): 1. Overview, 2. Context & State Flow, A. State Hierarchy, B. Shared Media URL & Thumbnail Resolution, ZezEdit 2.0 — Video Workspace Architecture

### Community 109 - "items"
Cohesion: 0.29
Nodes (6): 1. Overview & Principles, 2. Database Schema (Migration `0009_character_studio.sql`), 3. Human Review Operations, 4. Documented JSON Export Schema, Fundamental Constraints & Transparency Principles, ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library

### Community 110 - ".clear_all_user_data"
Cohesion: 0.29
Nodes (7): 1. Backend Pytest Suite, 2. Frontend Vitest Suite, 3. TypeScript Type Checking, 4. Frontend Production Build, 5. SQLite Database Integrity, 6. Live Browser Verification, F. Test Evidence Summary

### Community 111 - "2. Canonical Data Models"
Cohesion: 0.18
Nodes (10): 1. Character Extraction Studio & Character Library (Milestone 10), 2. Smart Reframing & Subject Tracking (Milestone 7), 4. AI Highlight Discovery & Shorts Candidate Ranking (Milestone 6), 5. Rendering Engine & Shorts Export Pipeline (Milestone 8), 6. AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), A. Executive Summary, B. Ten-Milestone Verification Table, C. Feature-Level Deep Dive Audit (+2 more)

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

### Community 118 - "clip_edits.py"
Cohesion: 0.27
Nodes (4): CandidateEditSaveRequest, save_candidate_edit(), track_candidate_subjects(), TrackCandidateRequest

### Community 119 - "height"
Cohesion: 0.50
Nodes (4): 6. Multiple Shorts Batch Export Engine, Batch Export Request Payload:, Batch Export Response Payload:, Output File Organization:

### Community 120 - "create_moving_subject_video"
Cohesion: 0.24
Nodes (4): create_moving_subject_video(), test_alternate_exports_same_candidate(), test_analysis_reuse_and_signature_invalidation(), test_permanent_novelty_ledger_survives_deletions()

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

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1536 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `config.py` to `subprocess`, `AppError`, `.__init__`, `Settings`, `ExportService`, `sqlite3`, `.from_root`, `StorageLayout`, `core.py`, `ProjectService`, `test_stale_queued_job_timeout_cleanup`, `_heartbeat_ticker`, `test_atomic_job_claiming_guarantee`, `config.py`, `StorageLayout`, `create_app`, `ExportService`, `post`, `ZezEdit 2.0 — Milestone 17 Verification & Restoration Report`, `SettingsService`, `MediaPipelineService`, `characters.py`, `ZezEdit 2.0 — Media Storage & Processing Pipeline`, `pytest`, `.__init__`, `Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)`, `README.md`, `ZezEdit 2.0 — UI, Navigation & Feature Gap Analysis`, `character.py`, `ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)`, `Effects`, `2. Canonical Data Models`?**
  _High betweenness centrality (0.251) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `subprocess` be split into smaller, more focused modules?**
  _Cohesion score 0.06126331811263318 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `README.md` to `config.py`, `v1/reframing.py`?**
  _High betweenness centrality (0.161) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `cancel_job()`) actually correct?**
  _`JobOrchestrator` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Should `AppError` be split into smaller, more focused modules?**
  _Cohesion score 0.061052631578947365 - nodes in this community are weakly interconnected._