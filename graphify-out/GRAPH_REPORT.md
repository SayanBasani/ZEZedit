# Graph Report - ZezEdit  (2026-11-14)

## Corpus Check
- 209 files · ~336,067 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .xml 3, .example 1, (none) 1)

## Summary
- 3266 nodes · 8940 edges · 175 communities (129 shown, 46 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 917 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9ce10fb8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- apiClient.ts
- App.tsx
- v1/media.py
- AppError
- core/storage.py
- settings.py
- highlights.py
- MediaService
- Button
- TimelineService
- highlights.ts
- JobOrchestrator
- HighlightDiscoveryEngine
- clip_edits.py
- test_milestone24_timeline_operations_coverage.py
- CharacterStudio.tsx
- ProjectService
- core.py
- .execute_render_job
- Settings
- preview_user_data_cleanup_endpoint
- CharacterService
- subprocess
- visual_understanding.py
- ExportStudio.tsx
- logging.py
- SubjectTracker
- MediaAssetItem
- ExportService
- get_health
- analysis.py
- test_workflow_state_evaluation_lifecycle
- test_milestone9_timeline.py
- CharacterStudio.tsx
- NotFoundError
- ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification
- TimelineCommandService
- ai_providers.py
- CropKeyframe
- SpeechToTextProvider
- get
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- get_settings
- v1/health.py
- JobOrchestrator
- CharacterCandidate
- CaptionConfig
- settings.py
- ZezEdit 2.0 — Local-First AI Video Editor
- characters.py
- core.py
- ZezEdit 2.0 — Feature Status Tracker
- VideoAnalysisPipeline
- ZezEdit 2.0 — Media Storage & Processing Pipeline
- error_envelope.schema.json
- 3. Core Functional Modules (A–J)
- reframing_service.py
- ReframingService
- Unslop
- test_milestone2_core.py
- reframing_renderer.py
- .analyze_and_create_plan
- Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)
- projects.ts
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
- ai_providers.py
- OutputValidator
- VideoAnalysisPipeline
- entities.py
- .get_job
- TimelineRenderer
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- 3. Detailed Milestone Breakdown
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- character_service.py
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- ExportService
- .trim_clip
- character.py
- export.py
- .request_cancellation
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Authoritative Job Orchestration Design
- ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)
- compilerOptions
- schemas/health.py
- v1/jobs.py
- ZezEdit 2.0 — Security & Data Safety Architecture
- 3. Sub-Workspace Breakdown
- Effects
- ExportStudio.tsx
- ZezEdit 2.0 — Security & Data Safety Architecture
- F. Test Evidence Summary
- 3. Detailed Specification by Domain
- OllamaProvider
- .create_job
- sqlite3
- sqlite_session
- base.py
- character_env
- timeline_env
- delete_transcript_correction
- duration_sec
- height
- kind
- playhead_sec
- app/__init__.py
- .generate_framing_keyframes
- base.py
- WhisperTranscriber
- test_direct_upload_verification.py
- TestClient
- ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)
- exports.py
- get
- test_job_orchestrator_state_machine_and_recovery
- ReframingRenderer
- F. Test Evidence Summary
- C. Feature-Level Deep Dive Audit
- list_export_presets
- .delete_job
- ZezEdit 2.0 — Feature & Verification Checklist
- .cancel_export_render
- .ensure_directories
- ZezEdit 2.0 — Master Requirements Specification
- v1/timeline.py
- 24. Conclusion, Parity Scorecard & Milestone 19 Transition Path
- 6. Windows 11 Startup & Shutdown Lifecycle
- BinaryStatus
- test_format_ass_timestamp_precision
- test_api_endpoints_end_to_end

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 199 edges
2. `request()` - 129 edges
3. `Settings` - 127 edges
4. `JobOrchestrator` - 95 edges
5. `StorageLayout` - 88 edges
6. `NotFoundError` - 77 edges
7. `AppError` - 76 edges
8. `get_settings()` - 76 edges
9. `create_app()` - 70 edges
10. `TimelineCommandService` - 63 edges

## Surprising Connections (you probably didn't know these)
- `Non-Destructive Transcript Corrections (`ZEZ-025`)` --references--> `get_transcript()`  [INFERRED]
  docs/reports/milestone_15_analysis_restoration_report.md → backend/app/api/v1/analysis.py
- `Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration` --references--> `ExportService`  [INFERRED]
  docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md → backend/app/services/export_service.py
- `15. Multi-Track Timeline & Custom Clip Editing` --references--> `ExportService`  [INFERRED]
  docs/reports/milestone_18_unified_video_to_shorts_pipeline_report.md → backend/app/services/export_service.py
- `1. Core Mandate: One Single Job System` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/JOB_ORCHESTRATION.md → backend/app/services/jobs.py
- `Components` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/MEDIA_PIPELINE.md → backend/app/services/jobs.py

## Import Cycles
- None detected.

## Communities (175 total, 46 thin omitted)

### Community 0 - "apiClient.ts"
Cohesion: 0.04
Nodes (109): FoundationOverview(), MODULE_ROADMAP, ProjectsView(), formatBytes(), SettingsManager(), SettingsTab, TimelineEditor(), addTimelineTextOverlay() (+101 more)

### Community 1 - "App.tsx"
Cohesion: 0.07
Nodes (30): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, App(), NavSection, SidebarNavButton(), SidebarNavButtonProps, defaultToastValue (+22 more)

### Community 2 - "v1/media.py"
Cohesion: 0.08
Nodes (20): delete_media(), delete_media_global(), generate_proxy_endpoint(), get_media_service(), get_media_stats(), get_pipeline_service(), import_local_file(), import_local_file_global() (+12 more)

### Community 3 - "AppError"
Cohesion: 0.07
Nodes (11): AppError, calculate_aspect_ratio(), MediaProbeResult, MediaStreamInfo, parse_fraction(), probe_media_file(), generate_proxy(), generate_thumbnail() (+3 more)

### Community 4 - "core/storage.py"
Cohesion: 0.10
Nodes (16): BoundaryViolationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory(), validate_storage_root_path(), test_health_and_system_info_endpoints() (+8 more)

### Community 5 - "settings.py"
Cohesion: 0.11
Nodes (8): create_backup(), restore_backup(), get_db_integrity_endpoint(), get_recovery_status_endpoint(), BackupService, test_sqlite_foreign_key_and_integrity_check(), test_sqlite_online_backup_generation(), test_backup_and_restore_verification()

### Community 6 - "highlights.py"
Cohesion: 0.08
Nodes (27): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, CandidateResponse, DiscoverHighlightsRequest, generate_more_highlights(), get_candidate_alternatives() (+19 more)

### Community 7 - "MediaService"
Cohesion: 0.07
Nodes (11): check_project_media_integrity(), get_media(), get_proxy_file(), get_thumbnail_file(), inspect_relink(), relink_media(), update_media(), update_media_global() (+3 more)

### Community 8 - "Button"
Cohesion: 0.10
Nodes (47): Milestone 3 — Frontend Application Shell, Dashboard & Design System, Badge(), BadgeProps, Button(), ButtonProps, Card(), CardProps, ConfirmDialog() (+39 more)

### Community 9 - "TimelineService"
Cohesion: 0.10
Nodes (12): add_track(), delete_track(), update_timeline_settings(), update_track(), CreateTrackRequest, TimelineTrack, UpdateTrackRequest, TimelineService (+4 more)

### Community 10 - "highlights.ts"
Cohesion: 0.07
Nodes (42): BatchExportModal(), BatchExportModalProps, HighlightsWorkspace(), ReframingReviewModal(), ASPECT_RATIO_OPTIONS, CandidateClipEditorModal(), CandidateClipEditorModalProps, formatTimecode() (+34 more)

### Community 11 - "JobOrchestrator"
Cohesion: 0.08
Nodes (45): ResourceInspector(), DocumentationView(), AIProviderManager(), categorizeJobType(), CategoryFilter, formatDuration(), formatTimeOnly(), ProcessesManagerView (+37 more)

### Community 12 - "HighlightDiscoveryEngine"
Cohesion: 0.07
Nodes (17): format_timestamp(), GeneratedCandidate, HighlightDiscoveryEngine, _now_utc(), QualityGateResult, ScoreBreakdown, main(), test_highlight_discovery_engine() (+9 more)

### Community 13 - "clip_edits.py"
Cohesion: 0.12
Nodes (7): CandidateEditSaveRequest, get_candidate_edit(), reset_candidate_edit(), save_candidate_edit(), track_candidate_subjects(), TrackCandidateRequest, ManualOverrideItem

### Community 14 - "test_milestone24_timeline_operations_coverage.py"
Cohesion: 0.14
Nodes (24): AddTextOverlayRequest, AIConversation, AIEditingPlan, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType (+16 more)

### Community 15 - "CharacterStudio.tsx"
Cohesion: 0.13
Nodes (24): CharacterStudio(), confirmCharacterCandidate(), detachCharacterObservation(), exportCharacterJson(), getCharacterCandidates(), getCharacterLibrary(), mergeCharacterCandidates(), rejectCharacterCandidate() (+16 more)

### Community 16 - "ProjectService"
Cohesion: 0.12
Nodes (7): archive_project(), create_project(), delete_project(), restore_project(), ProjectRecord, ProjectService, test_project_lifecycle_and_events()

### Community 17 - "core.py"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 18 - ".execute_render_job"
Cohesion: 0.16
Nodes (6): BatchExportItem, BatchExportRequest, BatchExportResponse, create_batch_export_jobs(), create_export_preview(), create_export_render_job()

### Community 19 - "Settings"
Cohesion: 0.03
Nodes (50): get_settings_service(), get_backup_service(), get_export_service(), Settings, MigrationError, StorageLayout, _backup_before_upgrade(), _file_sha256() (+42 more)

### Community 20 - "preview_user_data_cleanup_endpoint"
Cohesion: 0.11
Nodes (6): inspect_storage_endpoint(), _format_bytes(), StorageService, test_storage_breakdown_categories_accuracy(), test_temp_cache_cleanup_execute_with_valid_token(), test_temp_cache_cleanup_preview_no_file_deletion()

### Community 21 - "CharacterService"
Cohesion: 0.05
Nodes (32): confirm_candidate(), detach_observation(), export_character(), get_character_service(), get_extraction_job(), get_library_character(), list_candidates(), list_library_characters() (+24 more)

### Community 22 - "subprocess"
Cohesion: 0.06
Nodes (37): dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49 (+29 more)

### Community 23 - "visual_understanding.py"
Cohesion: 0.17
Nodes (4): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback()

### Community 24 - "ExportStudio.tsx"
Cohesion: 0.08
Nodes (8): get_ai_conversation(), get_plan(), list_plans(), reject_plan(), send_ai_message(), SendAIMessageRequest, AIEditorService, test_ai_video_editor_assistant()

### Community 26 - "SubjectTracker"
Cohesion: 0.10
Nodes (7): SubjectTrack, _compute_iou(), SubjectTracker, test_subject_tracker_detection_person_and_object(), test_subject_tracker_multi_subject_tracking_separate_tracks(), test_subject_tracker_scene_cut_termination(), 4. Features Already Restored in ZezEdit 2.0

### Community 27 - "MediaAssetItem"
Cohesion: 0.16
Nodes (19): 7. Video Workspace Implementation, ReframingWorkspace(), analyzeReframing(), fetchCropPreview(), fetchReframingRevisions(), getRenderedVideoUrl(), renderReframingRevision(), restoreReframingRevision() (+11 more)

### Community 28 - "ExportService"
Cohesion: 0.08
Nodes (60): 4. Post-Import Action Flow, AnalysisWorkspace(), AspectRatioOption, CREATIVE_DIRECTION_LABELS, CreativeDirectionOption, SingleVideoStudio(), STAGE_LABELS, ASPECT_RATIOS (+52 more)

### Community 29 - "get_health"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 30 - "analysis.py"
Cohesion: 0.07
Nodes (29): AnalysisRunResponse, AudioAnalysisItem, create_or_update_transcript_correction(), delete_transcript_correction(), _format_run_response(), get_analysis_pipeline(), get_analysis_run(), get_analysis_telemetry() (+21 more)

### Community 31 - "test_workflow_state_evaluation_lifecycle"
Cohesion: 0.18
Nodes (8): WorkflowStage, seed_analysis_run(), seed_candidate(), seed_export(), test_batch_export_endpoint_success(), test_batch_export_validation_and_skipped(), test_multi_video_data_isolation(), test_workflow_state_evaluation_lifecycle()

### Community 32 - "test_milestone9_timeline.py"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 33 - "CharacterStudio.tsx"
Cohesion: 0.08
Nodes (26): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+18 more)

### Community 34 - "NotFoundError"
Cohesion: 0.07
Nodes (7): NotFoundError, ValidationError, TimelineRecord, test_timeline_duration_auto_calculation(), test_timeline_redo_empty_stack_validation(), test_timeline_undo_empty_stack_validation(), test_persistent_undo_and_redo()

### Community 35 - "ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification"
Cohesion: 0.09
Nodes (21): A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, D. Audio and Transcription, Database Migration: `0010_transcript_corrections_and_audio.sql`, E. Scene Detection, F. Visual Understanding, Files Created, G. Temporal Context Aggregation (+13 more)

### Community 36 - "TimelineCommandService"
Cohesion: 0.10
Nodes (10): add_text_overlay(), duplicate_clip(), split_clip(), update_clip_props(), InsertClipRequest, TimelineCommandService, test_timeline_duplicate_clip_naming_and_props(), timeline_env() (+2 more)

### Community 37 - "ai_providers.py"
Cohesion: 0.09
Nodes (7): get_clip_editing_service(), ClipEditingService, test_api_clip_edit_routes(), test_db_setup(), test_get_or_create_edit_creates_default(), test_reset_to_original_preserves_pristine_candidate(), test_save_edit_and_validation()

### Community 38 - "CropKeyframe"
Cohesion: 0.14
Nodes (6): CropKeyframe, build_crop_filter_expression(), _simplify_keyframes(), test_preview_and_renderer_expression_parity(), test_dynamic_crop_filter_expression_generation(), `ZEZ-055`: Authoritative Preview-to-Render Mathematical Parity (13M.12/13M.13)

### Community 39 - "SpeechToTextProvider"
Cohesion: 0.17
Nodes (10): SpeechToTextProvider, TextLLMProvider, VisionLanguageProvider, 1. Overview & Guiding Principles, 2. High-Level System Architecture, 3. Frontend Module Boundaries (`frontend/src/`), 4. Backend Module Boundaries (`backend/app/`), 5. AI Provider Abstraction Boundaries (+2 more)

### Community 40 - "get"
Cohesion: 0.12
Nodes (8): get_asset_integrity(), get_media_global(), get_media_proxy_global(), get_media_thumbnail_global(), get_media_workflow_state(), list_all_media(), list_media(), stream_media_global()

### Community 41 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.18
Nodes (10): A. Executive Summary, B. Ten-Milestone Verification Table, E. Implementation Classification: Real vs Heuristic vs Mocked, G. Recommended Next Five Corrective Milestones, Priority 1: Milestone 12 — Real Vision & Face Detection Engine (Fix DEF-02 & DEF-03), Priority 2: Milestone 13 — Conversational LLM Editor Integration (Fix DEF-04), Priority 3: Milestone 14 — Timeline Multi-Track Advanced Editing & Ripple Operations, Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration (+2 more)

### Community 42 - "get_settings"
Cohesion: 0.05
Nodes (37): get_reframing_service(), get_settings(), ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream() (+29 more)

### Community 43 - "v1/health.py"
Cohesion: 0.16
Nodes (7): _check_storage_writable(), get_health(), get_system_diagnostics(), get_system_info(), get_system_resources(), probe_media_binary(), DiagnosticItem

### Community 44 - "JobOrchestrator"
Cohesion: 0.12
Nodes (5): get_job_orchestrator(), get_queue_stats(), JobOrchestrator, test_resource_aware_scheduler_and_priority(), test_job_orchestrator_linkage_and_telemetry()

### Community 45 - "CharacterCandidate"
Cohesion: 0.09
Nodes (21): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+13 more)

### Community 46 - "CaptionConfig"
Cohesion: 0.14
Nodes (5): CaptionEngine, format_ass_timestamp(), test_caption_engine_ass_file_generation_and_styling(), test_caption_engine_empty_segments(), test_caption_engine_ass_generation()

### Community 48 - "settings.py"
Cohesion: 0.19
Nodes (9): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, clear_all_user_data_endpoint(), ClearAllDataRequest, create_backup_endpoint(), execute_cleanup_endpoint(), preview_cleanup_endpoint() (+1 more)

### Community 49 - "ZezEdit 2.0 — Local-First AI Video Editor"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 50 - "characters.py"
Cohesion: 0.11
Nodes (19): 1. Prerequisites, 2. Installation commands, 3. Environment and setup steps, 4. Exact Windows PowerShell backend startup commands, 5. Exact Windows PowerShell frontend startup commands, 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12 & 13), AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Architecture & Documentation (+11 more)

### Community 51 - "core.py"
Cohesion: 0.09
Nodes (35): get_doc_article(), list_doc_articles(), list_doc_categories(), get_project(), get_project_events(), list_projects(), update_project(), AIProviderCapability (+27 more)

### Community 52 - "ZezEdit 2.0 — Feature Status Tracker"
Cohesion: 0.11
Nodes (18): ShortsCandidateRecord, AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Character Extraction Studio, Character Library & System Integration (Milestone 10), Core Backend, Database & Project Management (Milestone 2), Core Foundation & Architecture (Milestone 1), Core Product Workflow, Working Queue & Desktop Operations (Milestone 17), Frontend Application Shell, Dashboard & Design System (Milestone 3), Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11) (+10 more)

### Community 53 - "VideoAnalysisPipeline"
Cohesion: 0.08
Nodes (15): cancel_analysis(), get_analysis_cache(), retry_analysis(), _run_analysis_worker(), start_analysis(), compute_source_signature(), _now_utc(), VideoAnalysisPipeline (+7 more)

### Community 54 - "ZezEdit 2.0 — Media Storage & Processing Pipeline"
Cohesion: 0.11
Nodes (17): 1. Storage Separation & Source Immutability, 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First), 3. Smart Reframing & Portrait Rendering Architecture, 5. Milestone 4 Implementation Details: Media Ingestion & Proxies, 5. Video Analysis Engine (Milestone 5), 6. Smart Reframing & Dynamic Crop Renderer (Milestone 7), 7. Rendering Engine & Export Pipeline (Milestone 8), Authoritative Crop Math & Preview Parity (+9 more)

### Community 55 - "error_envelope.schema.json"
Cohesion: 0.11
Nodes (17): type, type, properties, required, type, type, properties, code (+9 more)

### Community 56 - "3. Core Functional Modules (A–J)"
Cohesion: 0.18
Nodes (5): _error_payload(), register_exception_handlers(), handle_app_error(), handle_unexpected_error(), handle_validation_error()

### Community 57 - "reframing_service.py"
Cohesion: 0.15
Nodes (7): DetectedSubject, FramingEngine, test_framing_strategies_single_two_person_and_group(), test_framing_engine_action_object_framing(), test_framing_engine_group_framing(), test_framing_engine_single_subject(), test_framing_engine_two_person_joint_framing()

### Community 58 - "ReframingService"
Cohesion: 0.10
Nodes (10): get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), preview_crop_geometry(), render_reframed_video(), RenderRevisionRequest, restore_reframing_revision(), save_manual_overrides() (+2 more)

### Community 59 - "Unslop"
Cohesion: 0.12
Nodes (16): 1. Executive Summary & Historical Context, 2. Surviving Evidence Sources & Provenance, 3. Pre-Deletion Architecture & Data Flows, 4. Reconstructed Pre-Deletion Feature Inventory (20 Application Areas), 5. Milestone 13M.12 Deep-Dive Investigation, 6. Milestone 13M.13 Deep-Dive Investigation, 7. Historical UI Reconstruction, 8. Summary of Reconstructed Pre-Deletion Baseline (+8 more)

### Community 60 - "test_milestone2_core.py"
Cohesion: 0.12
Nodes (17): type, type, properties, type, type, type, type, clips (+9 more)

### Community 61 - "reframing_renderer.py"
Cohesion: 0.12
Nodes (16): 1. Spacing, 2. Color, 3. Icons, 4. Copy, 5. Type, 6. Layout, 7. Details, 8. Visuals (+8 more)

### Community 62 - ".analyze_and_create_plan"
Cohesion: 0.14
Nodes (4): create_reframing_plan(), CreateReframingPlanRequest, ReframingPlanRecord, ReframingRevisionRecord

### Community 63 - "Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)"
Cohesion: 0.12
Nodes (16): type, exclusiveMinimum, type, type, properties, aspect_ratio, fps, project_id (+8 more)

### Community 64 - "projects.ts"
Cohesion: 0.08
Nodes (29): `ZEZ-005`: Post-Import Guided Ingestion Flow, AnalysisWorkspaceProps, CharacterStudioProps, DashboardViewProps, ExportStudioProps, HighlightsWorkspaceProps, MediaLibraryViewProps, PostImportModalProps (+21 more)

### Community 65 - "test_candidate_human_review_workflow"
Cohesion: 0.14
Nodes (14): Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12), `ZEZ-048`: Structured Tracking Telemetry & Diagnostics JSON (13M.12) (+6 more)

### Community 66 - "Tokens"
Cohesion: 0.14
Nodes (14): Accent, App layout, Buttons, Dark, Depth, Icons, Light, Motion (+6 more)

### Community 67 - "ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library"
Cohesion: 0.17
Nodes (6): 1. Overview & Principles, 2. Database Schema (Migration `0009_character_studio.sql`), 3. Human Review Operations, 4. Documented JSON Export Schema, Fundamental Constraints & Transparency Principles, ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library

### Community 68 - "Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)"
Cohesion: 0.20
Nodes (10): Domain J: System Infrastructure, Diagnostics & Reliability (`ZEZ-091` – `ZEZ-100`), `ZEZ-091`: Forward-Only Versioned SQLite Migrations, `ZEZ-092`: Pre-Migration Automatic Database Snapshot, `ZEZ-093`: Path Traversal & Anti-Root Recursive Deletion Guard, `ZEZ-094`: Single Authoritative Job Orchestrator & State Machine, `ZEZ-096`: Comprehensive Health & Diagnostics Probe (`/api/v1/health`), `ZEZ-097`: Graphify Knowledge Graph Auto-Maintenance, `ZEZ-098`: Unslop Studio Dark Design Standard (+2 more)

### Community 69 - "pytest"
Cohesion: 0.14
Nodes (14): Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`), `ZEZ-056`: Piecewise-Linear Dynamic FFmpeg Crop Filtergraph (13M.12), `ZEZ-057`: Burned-in Subtitles & Karaoke Word-Level ASS Styling, `ZEZ-058`: Professional Audio Processing & EBU R128 Loudness Normalization, `ZEZ-059`: Export Presets & Aspect Ratio Conversion, `ZEZ-060`: Strict Multi-Point Output Validation Gate, `ZEZ-061`: Poster Frame Cover Thumbnail Extraction, `ZEZ-062`: Render Progress Monitoring via FFmpeg `-progress` Pipe (+6 more)

### Community 70 - "Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)"
Cohesion: 0.14
Nodes (13): 10. Test and Acceptance Criteria, 11. Current Verified Restoration Coverage, 12. Recommended Next Implementation Milestone, 1. ZezEdit 1.0 Feature Inventory, 2. Historical Evidence References, 3. Exact Parity Requirements Identified, 5. Missing Functionality (Parity Gap), 6. Features That Cannot Be Recovered With Available Evidence (+5 more)

### Community 71 - "WorkflowStateMachine"
Cohesion: 0.18
Nodes (5): VideoWorkflowStateResponse, WorkflowStateMachine, Milestone 18: Unified Video-to-Shorts Production Pipeline Checklist, 1. Executive Summary, 23. Graphify Knowledge Graph & Topological Codebase Health

### Community 72 - "README.md"
Cohesion: 0.15
Nodes (12): test_non_destructive_transcript_corrections(), Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`), `ZEZ-021`: Automated Audio Extraction for ASR, `ZEZ-022`: Faster-Whisper Local Speech Transcription, `ZEZ-023`: Word-Level Timestamp Alignment, `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer, `ZEZ-025`: Non-Destructive Transcript Text Corrections, `ZEZ-026`: FFmpeg Visual Scene Cut Detection (+4 more)

### Community 73 - "6. Multiple Shorts Batch Export Engine"
Cohesion: 0.50
Nodes (4): 6. Multiple Shorts Batch Export Engine, Batch Export Request Payload:, Batch Export Response Payload:, Output File Organization:

### Community 74 - "Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)"
Cohesion: 0.15
Nodes (12): 1. Parity Metrics & Scorecard Summary, 2. Complete 100-Requirement Parity Matrix, Domain A: Application Shell, Dashboard & Navigation, Domain B: Media Management, Proxies & Storage, Domain C: Video Analysis & Speech Understanding, Domain D & E: AI Multimodal Understanding & Highlight Discovery, Domain F: Smart Reframing & Subject Tracking (13M.12/13M.13), Domain G: Shorts Generation & FFmpeg Rendering (+4 more)

### Community 75 - "ZezEdit 2.0 — Milestone 13 Completion Report: ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan"
Cohesion: 0.15
Nodes (13): Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`), `ZEZ-069`: Multi-Track Timeline NLE Canvas, `ZEZ-070`: Non-Destructive Clip Trimming & Splitting, `ZEZ-071`: Ripple Delete & Gap Closing, `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing, `ZEZ-073`: Persistent Timeline Undo & Redo History, `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration, `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`) (+5 more)

### Community 76 - "ai_providers.py"
Cohesion: 0.14
Nodes (7): list_ai_providers(), update_ai_provider(), get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 78 - "OutputValidator"
Cohesion: 0.18
Nodes (6): OutputValidator, test_output_validator_success_and_tampered_metadata(), test_output_validator_gate(), AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), Milestone 9: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing Checklist, AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

### Community 79 - "VideoAnalysisPipeline"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 80 - "entities.py"
Cohesion: 0.18
Nodes (9): AnalysisRunRecord, CandidateClipEditRecord, ProjectEventRecord, SampledFrameRecord, SpeechTurnRecord, TranscriptSegmentRecord, VideoSceneRecord, VisualObservationRecord (+1 more)

### Community 82 - "TimelineRenderer"
Cohesion: 0.08
Nodes (14): render_timeline(), ExportPreset, _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models, 2. `timeline_tracks` Table (+6 more)

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
Cohesion: 0.13
Nodes (7): delete_export(), download_export_video(), get_export_details(), list_exports(), stream_export_video(), ExportRecord, ExportService

### Community 92 - ".trim_clip"
Cohesion: 0.14
Nodes (6): get_history(), TrimClipRequest, test_timeline_consecutive_undo_redo_stack(), test_timeline_new_command_clears_redo_history(), test_timeline_trim_clip_bounds_and_duration(), test_timeline_update_clip_props_volume_and_speed()

### Community 93 - "character.py"
Cohesion: 0.22
Nodes (8): 1. Engine & Pragmas, 2. Versioned Migration Strategy (Historical Lesson Applied), 3. Planned Domain Entity Relationship Diagram, 4. Schema Breakdown: Implemented vs Planned, 5. Limitations & Alternatives Considered, Implemented Tables (Migrations 0001–0005), Planned Tables for Subsequent Milestones (Schema Blueprint), ZezEdit 2.0 — Database Design & Migration Strategy

### Community 94 - "export.py"
Cohesion: 0.22
Nodes (8): 1. Core Mandate: One Single Job System, 2. Job States & Lifecycle Transitions, 3. Canonical Job Types & Concurrency Policy, 4. Worker Ownership & Child Process PID Registry, 5. Restart Recovery Rules, 6. Retry Rules & Per-Job Logs, 7. Alternatives Considered & Limitations, ZezEdit 2.0 — Authoritative Job Orchestration Design

### Community 96 - "ZezEdit 2.0 — Database Design & Migration Strategy"
Cohesion: 0.22
Nodes (8): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, strict, include

### Community 98 - "ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)"
Cohesion: 0.29
Nodes (7): Dithering, Duotone, Effects, Glyphs, Halftone dots, Implementation, Performance

### Community 99 - "compilerOptions"
Cohesion: 0.29
Nodes (7): Decide what the visual is, Generate it, Objects for moments, Prompt recipe, Put it on the page, Styles that work, Visuals

### Community 100 - "schemas/health.py"
Cohesion: 0.16
Nodes (7): DatabaseHealth, DependencyCheck, HealthResponse, OllamaHealth, StorageHealth, SystemDiagnosticsResponse, SystemInfoResponse

### Community 101 - "v1/jobs.py"
Cohesion: 0.22
Nodes (11): cancel_job(), create_job(), _enrich_job_response(), get_job(), get_job_checkpoint(), get_job_logs(), list_jobs(), retry_job() (+3 more)

### Community 102 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.29
Nodes (6): 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction, 4. Export Overwrite & Confirmation Rules, 5. AI Video Editor Security Boundary, 6. Backup & Restore Strategy, ZezEdit 2.0 — Security & Data Safety Architecture

### Community 103 - "3. Sub-Workspace Breakdown"
Cohesion: 0.12
Nodes (15): 1. Overview, 1. Overview Tab, 2. Analysis Tab, 2. Context & State Flow, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Scenes Tab, 5. AI Highlights Tab (+7 more)

### Community 104 - "Effects"
Cohesion: 0.29
Nodes (6): 1. Product Vision & Mission Statement, 2. Requirement Taxonomy & Numbering, 3. Detailed Specification by Domain, 4. Summary Parity Ledger, Core Architecture Axioms, ZezEdit 1.0 — Exact Product Parity Specification

### Community 105 - "ExportStudio.tsx"
Cohesion: 0.19
Nodes (17): DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), cancelExportRender(), deleteExport(), fetchExportPresets(), fetchJob(), getExportVideoUrl() (+9 more)

### Community 106 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 107 - "F. Test Evidence Summary"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 108 - "3. Detailed Specification by Domain"
Cohesion: 0.40
Nodes (5): required, type, tracks, items, type

### Community 109 - "OllamaProvider"
Cohesion: 0.18
Nodes (6): test_ai_provider(), get_backup_service(), get_capabilities_endpoint(), get_settings_service(), get_storage_service(), OllamaProvider

### Community 110 - ".create_job"
Cohesion: 0.10
Nodes (8): test_job_retry_lifecycle_and_event_timeline(), test_queue_stats_aggregation(), test_job_completion_and_result_metadata(), test_job_failure_records_error_message(), test_job_priority_queue_dispatch_order(), test_job_retry_lifecycle_and_max_attempts(), test_job_state_transitions_and_progress(), test_jobs_rest_api_list_and_stats()

### Community 112 - "sqlite3"
Cohesion: 0.13
Nodes (21): _setup_test_env(), test_api_parity_processes_and_jobs_routes(), test_delete_job_history(), test_delete_single_job_record(), test_job_cancellation_lifecycle(), test_job_creation_with_media_asset_and_parent(), test_list_jobs_filtering_and_video_title(), test_restart_recovery_marks_running_jobs_interrupted() (+13 more)

### Community 113 - "sqlite_session"
Cohesion: 0.16
Nodes (7): create_sqlite_connection(), sqlite_session(), get_temporal_context_at(), TemporalContext, test_migration_and_foreign_keys(), test_temporal_aggregator_query(), test_novelty_ledger_rejects_exact_and_near_identical_repeats()

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

### Community 132 - ".generate_framing_keyframes"
Cohesion: 0.19
Nodes (3): test_portrait_crop_geometry_and_bounds(), test_trajectory_smoothing_and_scene_cut_isolation(), `ZEZ-044`: Boundary Safety Containment (13M.12)

### Community 135 - "WhisperTranscriber"
Cohesion: 0.25
Nodes (3): WhisperTranscriber, C. Restored Analysis Pipeline, Execution Stages

### Community 137 - "TestClient"
Cohesion: 0.22
Nodes (4): test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint()

### Community 138 - "ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)"
Cohesion: 0.22
Nodes (8): ADR-01: Single Local Monolith (FastAPI + React) vs Microservices, ADR-02: CPU-First Local Processing & Streaming I/O, ADR-03: SQLite WAL + Forward-Only SQL Migrations, ADR-04: Centralized Error Handling & Structured Logging, ADR-06: Decoupled Evidence-Based Character Extraction (No 3D Studio), ADR-07: Testing Strategy (Multi-Layer Gate), ADR-08: Shared Contract Directory (`shared/contracts/`), ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)

### Community 139 - "exports.py"
Cohesion: 0.06
Nodes (19): AudioConfig, CaptionConfig, RenderExportRequest, ValidationDetails, AudioPipeline, hex_to_ass_color(), test_audio_pipeline_loudnorm_and_volume_filter_chains(), test_export_delete_endpoint() (+11 more)

### Community 140 - "get"
Cohesion: 0.25
Nodes (3): get_storage_breakdown_endpoint(), list_backups_endpoint(), preview_user_data_cleanup_endpoint()

### Community 141 - "test_job_orchestrator_state_machine_and_recovery"
Cohesion: 0.25
Nodes (3): test_job_orchestrator_state_machine_and_recovery(), `ZEZ-095`: Unclean Shutdown Recovery of Interrupted Jobs, 7. Working Queue Integration & Parallel Job Execution

### Community 151 - "F. Test Evidence Summary"
Cohesion: 0.29
Nodes (7): 1. Backend Pytest Suite, 2. Frontend Vitest Suite, 3. TypeScript Type Checking, 4. Frontend Production Build, 5. SQLite Database Integrity, 6. Live Browser Verification, F. Test Evidence Summary

### Community 152 - "C. Feature-Level Deep Dive Audit"
Cohesion: 0.29
Nodes (7): 1. Character Extraction Studio & Character Library (Milestone 10), 2. Smart Reframing & Subject Tracking (Milestone 7), 3. Video Analysis & Multimodal Understanding (Milestone 5), 4. AI Highlight Discovery & Shorts Candidate Ranking (Milestone 6), 5. Rendering Engine & Shorts Export Pipeline (Milestone 8), 6. AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), C. Feature-Level Deep Dive Audit

### Community 155 - "ZezEdit 2.0 — Feature & Verification Checklist"
Cohesion: 0.17
Nodes (11): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification, Milestone 6: AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking Verification (+3 more)

### Community 158 - "ZezEdit 2.0 — Master Requirements Specification"
Cohesion: 0.33
Nodes (5): 1. Mission & Product Vision, 2. Hardware & Resource Constraints (Mandatory), 4. Mandatory Data Protection & Reliability Rules, 5. Planned Milestone Sequence, ZezEdit 2.0 — Master Requirements Specification

### Community 159 - "v1/timeline.py"
Cohesion: 0.08
Nodes (15): approve_plan(), create_timeline(), delete_clip(), get_active_timeline(), get_ai_editor_service(), get_command_service(), get_timeline(), get_timeline_renderer() (+7 more)

### Community 163 - "24. Conclusion, Parity Scorecard & Milestone 19 Transition Path"
Cohesion: 0.67
Nodes (3): 24. Conclusion, Parity Scorecard & Milestone 19 Transition Path, Parity Scorecard Summary:, Transition Path to Milestone 19:

### Community 165 - "6. Windows 11 Startup & Shutdown Lifecycle"
Cohesion: 0.67
Nodes (3): 6. Windows 11 Startup & Shutdown Lifecycle, Graceful Shutdown Sequence, Startup Sequence

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1473 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **46 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `JobOrchestrator` to `v1/media.py`, `AppError`, `highlights.py`, `test_job_orchestrator_state_machine_and_recovery`, `ProjectService`, `Settings`, `preview_user_data_cleanup_endpoint`, `.delete_job`, `.__init__`, `SpeechToTextProvider`, `ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report`, `get_settings`, `v1/health.py`, `VideoAnalysisPipeline`, `ZezEdit 2.0 — Media Storage & Processing Pipeline`, `Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)`, `pytest`, `Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)`, `entities.py`, `.get_job`, `TimelineRenderer`, `ExportService`, `export.py`, `.request_cancellation`, `v1/jobs.py`, `.create_job`, `sqlite3`?**
  _High betweenness centrality (0.225) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `apiClient.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.04269972451790634 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `pytest` to `ExportStudio.tsx`, `JobOrchestrator`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `_run_discovery_background()`) actually correct?**
  _`JobOrchestrator` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07439024390243902 - nodes in this community are weakly interconnected._