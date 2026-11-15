# Graph Report - ZezEdit  (2026-11-15)

## Corpus Check
- 213 files · ~344,896 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .xml 3, .example 1, (none) 1)

## Summary
- 3328 nodes · 9137 edges · 173 communities (119 shown, 54 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 908 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7cbaed24`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- apiClient.ts
- ToastNotificationCenter.tsx
- .db_file
- AppError
- core/storage.py
- settings.py
- highlights.py
- AppError
- Button
- TimelineService
- highlights.ts
- system.ts
- HighlightDiscoveryEngine
- clip_edits.py
- test_milestone24_timeline_operations_coverage.py
- WorkingQueueView.tsx
- ProjectService
- core.py
- exports.py
- run_migrations
- preview_user_data_cleanup_endpoint
- CharacterService
- subprocess
- visual_understanding.py
- ExportStudio.tsx
- SubjectTracker
- test_session8_tracking_and_novelty.py
- ExportService
- get_health
- analysis.py
- .from_root
- test_milestone9_timeline.py
- CharacterStudio.tsx
- ValidationError
- ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification
- test_milestone5_analysis.py
- v1/__init__.py
- CropKeyframe
- SpeechToTextProvider
- v1/reframing.py
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- get_settings
- v1/health.py
- CharacterCandidate
- CaptionConfig
- probe_media_file
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
- models/reframing.py
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
- get_rendered_video_file
- .analyze_and_create_plan
- TimelineRenderer
- ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report
- 3. Detailed Milestone Breakdown
- Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)
- Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)
- Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)
- character_service.py
- ._generate_thumbnail
- ZezEdit 2.0 — API Design & Conventions
- list_exports
- .trim_clip
- character.py
- export.py
- ZezEdit 2.0 — Database Design & Migration Strategy
- ZezEdit 2.0 — Authoritative Job Orchestration Design
- ZezEdit 2.0 — Architecture & Technology Decision Records (ADRs)
- compilerOptions
- get_reframing_service
- v1/jobs.py
- 3. Sub-Workspace Breakdown
- Effects
- ExportStudio.tsx
- ZezEdit 2.0 — Security & Data Safety Architecture
- F. Test Evidence Summary
- 3. Detailed Specification by Domain
- ai_providers.py
- JobOrchestrator
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
- test_job_priority_queue_dispatch_order
- WhisperTranscriber
- test_jobs_rest_api_list_and_stats
- TestClient
- README.md
- export_service.py
- test_large_library_offset_limit_stability
- test_large_library_search_filter
- test_large_library_aspect_and_status_filters
- test_large_library_sorting
- test_first_generation_reuses_existing_analysis
- test_aspect_ratio_and_creative_direction_changes_reuse_analysis
- .delete_job
- ZezEdit 2.0 — Feature & Verification Checklist
- test_changing_aspect_ratio_cannot_bypass_novelty
- .ensure_directories
- ZezEdit 2.0 — Master Requirements Specification
- v1/timeline.py
- 24. Conclusion, Parity Scorecard & Milestone 19 Transition Path
- ZezEdit 2.0 — System Architecture
- test_exhaustion_returns_honest_warning_without_fillers
- test_ai_recommended_clip_count_and_natural_duration
- test_standard_presets_catalog_all_aspect_ratios

## God Nodes (most connected - your core abstractions)
1. `sqlite_session()` - 201 edges
2. `Settings` - 133 edges
3. `request()` - 129 edges
4. `JobOrchestrator` - 100 edges
5. `StorageLayout` - 91 edges
6. `AppError` - 79 edges
7. `NotFoundError` - 77 edges
8. `get_settings()` - 76 edges
9. `create_app()` - 70 edges
10. `TimelineCommandService` - 63 edges

## Surprising Connections (you probably didn't know these)
- `Priority 4: Milestone 15 — Performance Optimization & Hardware Acceleration` --references--> `ExportService`  [INFERRED]
  docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md → backend/app/services/export_service.py
- `15. Multi-Track Timeline & Custom Clip Editing` --references--> `ExportService`  [INFERRED]
  docs/reports/milestone_18_unified_video_to_shorts_pipeline_report.md → backend/app/services/export_service.py
- `1. Core Mandate: One Single Job System` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/JOB_ORCHESTRATION.md → backend/app/services/jobs.py
- `Components` --references--> `JobOrchestrator`  [INFERRED]
  docs/architecture/MEDIA_PIPELINE.md → backend/app/services/jobs.py
- `Domain G: Shorts Generation & FFmpeg Rendering` --references--> `JobOrchestrator`  [INFERRED]
  docs/reconstruction/FEATURE_PARITY_MATRIX.md → backend/app/services/jobs.py

## Import Cycles
- None detected.

## Communities (173 total, 54 thin omitted)

### Community 0 - "apiClient.ts"
Cohesion: 0.05
Nodes (102): CharacterStudio(), ProjectsView(), TimelineEditor(), addTimelineTextOverlay(), addTimelineTrack(), ApiClientError, approveAIPlan(), archiveProject() (+94 more)

### Community 1 - "ToastNotificationCenter.tsx"
Cohesion: 0.15
Nodes (15): defaultToastValue, ToastAction, ToastCard(), ToastCardProps, ToastContainer(), ToastContainerProps, ToastContext, ToastContextValue (+7 more)

### Community 2 - ".db_file"
Cohesion: 0.29
Nodes (4): get_analysis_pipeline(), get_db_path(), get_backup_service(), get_clip_editing_service()

### Community 3 - "AppError"
Cohesion: 0.08
Nodes (6): Settings, StorageLayout, MediaStreamInfo, test_real_ffmpeg_reframing_render(), test_large_library_payload_size_comparison(), test_clear_all_data_validation()

### Community 4 - "core/storage.py"
Cohesion: 0.07
Nodes (21): BoundaryViolationError, MigrationError, RootDeletionForbiddenError, UnsafeStorageRootError, is_path_confined(), resolve_contained_path(), safe_delete_directory(), validate_storage_root_path() (+13 more)

### Community 5 - "settings.py"
Cohesion: 0.08
Nodes (13): create_backup(), restore_backup(), create_backup_endpoint(), get_db_integrity_endpoint(), get_recovery_status_endpoint(), get_storage_breakdown_endpoint(), list_backups_endpoint(), preview_cleanup_endpoint() (+5 more)

### Community 6 - "highlights.py"
Cohesion: 0.08
Nodes (27): approve_candidate(), bulk_review_candidates(), BulkReviewRequest, CandidateGenerationRunResponse, CandidateResponse, DiscoverHighlightsRequest, generate_more_highlights(), get_candidate_alternatives() (+19 more)

### Community 7 - "AppError"
Cohesion: 0.04
Nodes (43): check_project_media_integrity(), delete_media(), delete_media_global(), generate_proxy_endpoint(), get_asset_integrity(), get_media(), get_media_global(), get_media_proxy_global() (+35 more)

### Community 8 - "Button"
Cohesion: 0.10
Nodes (51): Milestone 3 — Frontend Application Shell, Dashboard & Design System, Badge(), BadgeProps, Button(), ButtonProps, Card(), CardProps, ConfirmDialog() (+43 more)

### Community 9 - "TimelineService"
Cohesion: 0.06
Nodes (18): add_track(), delete_track(), get_active_timeline(), get_timeline(), update_timeline_settings(), update_track(), NotFoundError, CreateTrackRequest (+10 more)

### Community 10 - "highlights.ts"
Cohesion: 0.07
Nodes (41): BatchExportModal(), BatchExportModalProps, HighlightsWorkspace(), ASPECT_RATIO_OPTIONS, CandidateClipEditorModal(), CandidateClipEditorModalProps, formatTimecode(), approveCandidate() (+33 more)

### Community 11 - "system.ts"
Cohesion: 0.04
Nodes (77): D. Critical Defects & Technical Debt Registry, Milestone 11: Full Repository Audit, Evidence-Based Verification & Technical Debt Checklist, 5. UX Problems Identified and Corrected, App(), NavSection, SidebarNavButton(), SidebarNavButtonProps, ResourceInspector() (+69 more)

### Community 12 - "HighlightDiscoveryEngine"
Cohesion: 0.08
Nodes (11): HighlightDiscoveryEngine, _now_utc(), main(), test_highlight_discovery_engine(), test_quality_gates_and_statuses(), test_candidate_discovery_and_natural_boundaries(), test_creative_direction_weighting_differentiation(), test_empty_transcript_visual_fallback() (+3 more)

### Community 13 - "clip_edits.py"
Cohesion: 0.12
Nodes (7): CandidateEditSaveRequest, get_candidate_edit(), reset_candidate_edit(), save_candidate_edit(), track_candidate_subjects(), TrackCandidateRequest, ClipEditingService

### Community 14 - "test_milestone24_timeline_operations_coverage.py"
Cohesion: 0.18
Nodes (18): AIConversation, AIEditingPlan, AIMessage, AIPlanOperation, AudioProps, ClipType, CommandType, ContentProps (+10 more)

### Community 15 - "WorkingQueueView.tsx"
Cohesion: 0.12
Nodes (22): DashboardViewProps, ProjectsManagerProps, categorizeJobType(), CategoryFilter, formatDuration(), formatTimeOnly(), ProcessesManagerView, StatusFilter (+14 more)

### Community 16 - "ProjectService"
Cohesion: 0.08
Nodes (14): delete_project(), get_project_service(), AnalysisRunRecord, CandidateClipEditRecord, ProjectEventRecord, ProjectRecord, SampledFrameRecord, SpeechTurnRecord (+6 more)

### Community 17 - "core.py"
Cohesion: 0.05
Nodes (25): args, chrome, positionals, args, chrome, file, frame, frames (+17 more)

### Community 18 - "exports.py"
Cohesion: 0.08
Nodes (17): BatchExportItem, BatchExportRequest, BatchExportResponse, cancel_export(), create_batch_export_jobs(), create_export_preview(), create_export_render_job(), delete_export() (+9 more)

### Community 19 - "run_migrations"
Cohesion: 0.04
Nodes (24): _backup_before_upgrade(), _file_sha256(), MigrationResult, run_migrations(), client_with_clean_storage(), sample_videos(), character_env(), m15_env() (+16 more)

### Community 20 - "preview_user_data_cleanup_endpoint"
Cohesion: 0.08
Nodes (10): clear_all_user_data_endpoint(), inspect_storage_endpoint(), preview_user_data_cleanup_endpoint(), _format_bytes(), StorageService, test_storage_breakdown_categories_accuracy(), test_temp_cache_cleanup_execute_with_valid_token(), test_temp_cache_cleanup_preview_no_file_deletion() (+2 more)

### Community 21 - "CharacterService"
Cohesion: 0.05
Nodes (33): confirm_candidate(), detach_observation(), export_character(), get_character_service(), get_extraction_job(), get_library_character(), list_candidates(), list_library_characters() (+25 more)

### Community 22 - "subprocess"
Cohesion: 0.06
Nodes (37): dependencies, lucide-react@^0.468.0, react@^18.3.1, react-dom@^18.3.1, devDependencies, autoprefixer@^10.4.20, jsdom@^31.0.0, postcss@^8.4.49 (+29 more)

### Community 23 - "visual_understanding.py"
Cohesion: 0.10
Nodes (11): _encode_image_b64(), OllamaVisionAnalyzer, VisualObservation, test_visual_understanding_fallback(), 1. Character Extraction Studio & Character Library (Milestone 10), 2. Smart Reframing & Subject Tracking (Milestone 7), 3. Video Analysis & Multimodal Understanding (Milestone 5), 4. AI Highlight Discovery & Shorts Candidate Ranking (Milestone 6) (+3 more)

### Community 24 - "ExportStudio.tsx"
Cohesion: 0.09
Nodes (6): get_ai_conversation(), get_plan(), list_plans(), reject_plan(), send_ai_message(), AIEditorService

### Community 26 - "SubjectTracker"
Cohesion: 0.14
Nodes (4): SubjectTrack, _compute_iou(), SubjectTracker, 4. Features Already Restored in ZezEdit 2.0

### Community 27 - "test_session8_tracking_and_novelty.py"
Cohesion: 0.14
Nodes (8): format_timestamp(), GeneratedCandidate, QualityGateResult, ScoreBreakdown, test_intra_batch_containment_deduplication(), test_subject_tracker_detection_person_and_object(), test_subject_tracker_multi_subject_tracking_separate_tracks(), test_subject_tracker_scene_cut_termination()

### Community 28 - "ExportService"
Cohesion: 0.08
Nodes (59): AnalysisWorkspace(), AspectRatioOption, CREATIVE_DIRECTION_LABELS, CreativeDirectionOption, SingleVideoStudio(), STAGE_LABELS, GenerateShortModal(), VideoDashboardTab (+51 more)

### Community 29 - "get_health"
Cohesion: 0.07
Nodes (29): 10. Queue Chart Implementation, 11. Resource Inspector Implementation, 12. AI Provider Manager Implementation, 13. Documentation Center Implementation, 14. Exact Frontend Files Changed & Added, 15. Exact Backend Files Changed & Added, 17. Database Migrations and Tables, 18. Actual AI Providers and Models Tested (+21 more)

### Community 30 - "analysis.py"
Cohesion: 0.06
Nodes (30): AnalysisRunResponse, AudioAnalysisItem, cancel_analysis(), create_or_update_transcript_correction(), delete_transcript_correction(), _format_run_response(), get_analysis_run(), get_audio_analysis() (+22 more)

### Community 31 - ".from_root"
Cohesion: 0.04
Nodes (29): configure_logging(), create_app(), lifespan(), WorkflowStage, test_silent_video_analysis_pipeline(), test_standard_video_analysis_and_caching(), test_temporal_context_and_thumbnails_serving(), client() (+21 more)

### Community 32 - "test_milestone9_timeline.py"
Cohesion: 0.08
Nodes (25): 10. Restoration Roadmap, 11. Test and Verification Evidence, 12. Files Created or Modified, 13. Git Status, 14. Recommended Next Milestone, 1. Executive Summary, 2. Evidence Sources, 3. Pre-Deletion Architecture (+17 more)

### Community 33 - "CharacterStudio.tsx"
Cohesion: 0.07
Nodes (27): 10. Batch Export Modal UI & Aspect Ratio Presets, 11. Per-Video State Persistence & Non-Destructive Autosave, 12. Connected Video-to-Shorts Production Workspace, 13. Highlight Review & Boundary Enforcement, 14. Smart Reframing & 9:16 Crop Trajectory Integration, 15. Multi-Track Timeline & Custom Clip Editing, 16. Next Video Selection Workflow & Save-Before-Switch Protection, 17. Hardware Resource Telemetry & CPU Confinement (+19 more)

### Community 34 - "ValidationError"
Cohesion: 0.12
Nodes (12): ValidationError, AddTextOverlayRequest, InsertClipRequest, SplitClipRequest, TimelineClip, test_timeline_duration_auto_calculation(), test_timeline_split_clip_boundary_constraints(), test_timeline_text_overlay_creation_and_auto_track() (+4 more)

### Community 35 - "ZezEdit 2.0 — Milestone 12 Completion Report: Pre-Deletion Baseline Reconstruction & Feature Parity Specification"
Cohesion: 0.07
Nodes (29): detect_scenes_ffmpeg(), generate_scene_thumbnails(), test_scene_detection_and_thumbnails(), test_scene_detection(), A. Historical ZezEdit 1.0 Behavior, Algorithm & Outputs, B. Current Implementation Before Changes, C. Restored Analysis Pipeline (+21 more)

### Community 36 - "test_milestone5_analysis.py"
Cohesion: 0.16
Nodes (10): NormalizedSegment, segment_dialogue_turns(), SegmentWord, SpeechTurn, get_temporal_context_at(), TemporalContext, test_analysis_api_flow(), test_audio_extractor() (+2 more)

### Community 37 - "v1/__init__.py"
Cohesion: 0.17
Nodes (5): get_doc_article(), list_doc_articles(), list_doc_categories(), DocArticleDTO, DocCategoryDTO

### Community 38 - "CropKeyframe"
Cohesion: 0.14
Nodes (7): CropKeyframe, build_crop_filter_expression(), ReframingRenderer, _simplify_keyframes(), test_preview_and_renderer_expression_parity(), test_dynamic_crop_filter_expression_generation(), `ZEZ-048`: Structured Tracking Telemetry & Diagnostics JSON (13M.12)

### Community 39 - "SpeechToTextProvider"
Cohesion: 0.16
Nodes (8): ProviderHealth, SpeechToTextProvider, StructuredPlanResult, TextLLMProvider, VisionLanguageProvider, 4. Backend Module Boundaries (`backend/app/`), 5. AI Provider Abstraction Boundaries, ADR-05: Dynamic Authoritative AI Provider Abstraction

### Community 40 - "v1/reframing.py"
Cohesion: 0.20
Nodes (8): create_reframing_plan(), CreateReframingPlanRequest, ManualOverrideItem, render_reframed_video(), RenderRevisionRequest, restore_reframing_revision(), save_manual_overrides(), SaveOverridesRequest

### Community 41 - "ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report"
Cohesion: 0.11
Nodes (17): 1. Backend Pytest Suite, 2. Frontend Vitest Suite, 3. TypeScript Type Checking, 4. Frontend Production Build, 5. SQLite Database Integrity, 6. Live Browser Verification, A. Executive Summary, B. Ten-Milestone Verification Table (+9 more)

### Community 42 - "get_settings"
Cohesion: 0.11
Nodes (16): get_settings(), ProcessingError, AudioMetadata, detect_audio_silence(), extract_audio_16k_mono(), extract_audio_chunk(), inspect_audio_stream(), sample_analysis_frames() (+8 more)

### Community 43 - "v1/health.py"
Cohesion: 0.09
Nodes (15): _check_storage_writable(), get_health(), get_system_diagnostics(), get_system_info(), get_system_resources(), BinaryStatus, probe_media_binary(), DatabaseHealth (+7 more)

### Community 45 - "CharacterCandidate"
Cohesion: 0.09
Nodes (22): 10. Files Created and Modified, 11. Recommended Next Five Milestones, 12. Verification Screenshot Gallery, 1. Executive Summary, 2. Unslop Installation and Verification, 3. Graphify Installation and Verification, 4. Graphify Initial Build and Query Examples, 6. User Journey Verification (+14 more)

### Community 46 - "CaptionConfig"
Cohesion: 0.08
Nodes (13): CaptionConfig, CaptionEngine, format_ass_timestamp(), hex_to_ass_color(), test_caption_engine_ass_file_generation_and_styling(), test_caption_engine_empty_segments(), test_export_render_submission_and_query(), test_export_request_validation_models() (+5 more)

### Community 47 - "probe_media_file"
Cohesion: 0.14
Nodes (7): calculate_aspect_ratio(), MediaProbeResult, parse_fraction(), probe_media_file(), test_real_ffprobe_extraction(), test_real_proxy_generation(), test_real_thumbnail_generation()

### Community 48 - "settings.py"
Cohesion: 0.19
Nodes (10): BackupCreateRequest, BackupRestoreRequest, CleanupExecuteRequest, ClearAllDataRequest, execute_cleanup_endpoint(), get_backup_service(), get_capabilities_endpoint(), get_settings_service() (+2 more)

### Community 49 - "ZezEdit 2.0 — Local-First AI Video Editor"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+11 more)

### Community 50 - "characters.py"
Cohesion: 0.11
Nodes (19): 1. Prerequisites, 2. Installation commands, 3. Environment and setup steps, 4. Exact Windows PowerShell backend startup commands, 5. Exact Windows PowerShell frontend startup commands, 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12 & 13), AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Architecture & Documentation (+11 more)

### Community 51 - "core.py"
Cohesion: 0.12
Nodes (28): archive_project(), create_project(), get_project(), get_project_events(), list_projects(), restore_project(), update_project(), AIProviderCapability (+20 more)

### Community 52 - "ZezEdit 2.0 — Feature Status Tracker"
Cohesion: 0.11
Nodes (18): ShortsCandidateRecord, AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6), Character Extraction Studio, Character Library & System Integration (Milestone 10), Core Backend, Database & Project Management (Milestone 2), Core Foundation & Architecture (Milestone 1), Core Product Workflow, Working Queue & Desktop Operations (Milestone 17), Frontend Application Shell, Dashboard & Design System (Milestone 3), Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11) (+10 more)

### Community 53 - "VideoAnalysisPipeline"
Cohesion: 0.09
Nodes (13): get_analysis_cache(), get_analysis_telemetry(), compute_source_signature(), _heartbeat_ticker(), _ticker(), _now_utc(), VideoAnalysisPipeline, on_transcribe_progress() (+5 more)

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
Nodes (7): DetectedSubject, test_framing_strategies_single_two_person_and_group(), test_compute_temporal_overlap_containment(), test_framing_engine_action_object_framing(), test_framing_engine_group_framing(), test_framing_engine_single_subject(), test_framing_engine_two_person_joint_framing()

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

### Community 64 - "projects.ts"
Cohesion: 0.06
Nodes (41): AnalysisWorkspaceProps, CharacterStudioProps, ExportStudioProps, HighlightsWorkspaceProps, PostImportModalProps, ReframingReviewModal(), ReframingReviewModalProps, ReframingWorkspace() (+33 more)

### Community 65 - "test_candidate_human_review_workflow"
Cohesion: 0.15
Nodes (13): Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`), `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12), `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12), `ZEZ-043`: Strict Velocity Clamping (13M.12), `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12), `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12), `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12), `ZEZ-049`: UI Tracking Status Pill (13M.12) (+5 more)

### Community 66 - "Tokens"
Cohesion: 0.14
Nodes (14): Accent, App layout, Buttons, Dark, Depth, Icons, Light, Motion (+6 more)

### Community 67 - "ZezEdit 2.0 — Architecture: Character Extraction Studio & Character Library"
Cohesion: 0.29
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
Cohesion: 0.21
Nodes (7): get_media_workflow_state(), VideoWorkflowStateResponse, WorkflowStateMachine, Milestone 18: Unified Video-to-Shorts Production Pipeline Checklist, 1. Executive Summary, 23. Graphify Knowledge Graph & Topological Codebase Health, 4. Authoritative Workflow Lifecycle State Machine

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
Cohesion: 0.20
Nodes (5): get_settings_endpoint(), update_settings_endpoint(), AppSettingsDTO, SettingsService, test_settings_storage_and_secret_redaction()

### Community 78 - "OutputValidator"
Cohesion: 0.18
Nodes (6): OutputValidator, test_output_validator_success_and_tampered_metadata(), test_output_validator_gate(), AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9), Milestone 9: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing Checklist, AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

### Community 79 - "VideoAnalysisPipeline"
Cohesion: 0.18
Nodes (11): Components, Copy, Icons, Landing pages and heroes, Motion, Signs of slop, Spacing, Surfaces and color (+3 more)

### Community 80 - "get_rendered_video_file"
Cohesion: 0.22
Nodes (4): get_reframing_plan(), get_rendered_video_file(), list_reframing_revisions(), preview_crop_geometry()

### Community 82 - "TimelineRenderer"
Cohesion: 0.09
Nodes (13): render_timeline(), _format_ass_time(), TimelineRenderer, 1. Core Architectural Rule: One Shared Document Model, 1. `timelines` Table, 2. Canonical Data Models, 2. `timeline_tracks` Table, 3. Persistent Reversible Command System (Undo / Redo) (+5 more)

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
Cohesion: 0.18
Nodes (11): Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`), `ZEZ-001`: Studio Application Shell & Responsive Drawer, `ZEZ-002`: Studio Dashboard View, `ZEZ-003`: Project Management & Lifecycle Operations, `ZEZ-004`: Unified Video Workspace Navigation, `ZEZ-005`: Post-Import Guided Ingestion Flow, `ZEZ-006`: System Monitor & Hardware Resource Widget, `ZEZ-007`: Studio Light / Dark Theme Synchronization (+3 more)

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

### Community 92 - ".trim_clip"
Cohesion: 0.15
Nodes (9): TrimClipRequest, UpdateClipPropsRequest, test_timeline_consecutive_undo_redo_stack(), test_timeline_duplicate_clip_naming_and_props(), test_timeline_new_command_clears_redo_history(), test_timeline_redo_empty_stack_validation(), test_timeline_trim_clip_bounds_and_duration(), test_timeline_undo_empty_stack_validation() (+1 more)

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

### Community 101 - "v1/jobs.py"
Cohesion: 0.15
Nodes (13): cancel_job(), create_job(), _enrich_job_response(), get_job(), get_job_checkpoint(), get_job_logs(), get_job_orchestrator(), get_queue_stats() (+5 more)

### Community 103 - "3. Sub-Workspace Breakdown"
Cohesion: 0.12
Nodes (16): 1. Overview, 1. Overview Tab, 2. Analysis Tab, 2. Context & State Flow, 3. Sub-Workspace Breakdown, 3. Transcript & Audio Tab, 4. Post-Import Action Flow, 4. Scenes Tab (+8 more)

### Community 104 - "Effects"
Cohesion: 0.29
Nodes (6): 1. Product Vision & Mission Statement, 2. Requirement Taxonomy & Numbering, 3. Detailed Specification by Domain, 4. Summary Parity Ledger, Core Architecture Axioms, ZezEdit 1.0 — Exact Product Parity Specification

### Community 105 - "ExportStudio.tsx"
Cohesion: 0.20
Nodes (16): DEFAULT_AUDIO_CONFIG, DEFAULT_CAPTION_CONFIG, ExportStudio(), cancelExportRender(), deleteExport(), fetchExportPresets(), fetchJob(), getExportVideoUrl() (+8 more)

### Community 106 - "ZezEdit 2.0 — Security & Data Safety Architecture"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 107 - "F. Test Evidence Summary"
Cohesion: 0.40
Nodes (4): required, $schema, title, type

### Community 108 - "3. Detailed Specification by Domain"
Cohesion: 0.40
Nodes (5): required, type, tracks, items, type

### Community 109 - "ai_providers.py"
Cohesion: 0.13
Nodes (7): get_settings_service(), list_ai_providers(), test_ai_provider(), update_ai_provider(), OllamaProvider, AIProviderUpdateRequest, test_large_library_pagination_performance()

### Community 110 - "JobOrchestrator"
Cohesion: 0.08
Nodes (13): JobRecord, JobOrchestrator, test_job_retry_lifecycle_and_event_timeline(), test_queue_stats_aggregation(), test_job_checkpointing_and_recovery(), test_resource_aware_scheduler_and_priority(), test_job_cancellation_immediate_when_queued(), test_job_completion_and_result_metadata() (+5 more)

### Community 112 - "sqlite3"
Cohesion: 0.06
Nodes (48): _setup_test_orchestrator(), test_active_external_child_pid_never_marked_stalled_within_grace(), test_checkpoint_heals_premature_stalled_status(), test_complete_job_heals_premature_stalled_status(), test_completed_or_100pct_job_never_marked_stalled(), test_dead_os_pid_marked_stalled_after_grace(), test_in_process_job_stalls_when_silent_beyond_timeout(), test_export_delete_endpoint() (+40 more)

### Community 113 - "sqlite_session"
Cohesion: 0.16
Nodes (4): create_sqlite_connection(), sqlite_session(), test_migration_and_foreign_keys(), test_novelty_ledger_rejects_exact_and_near_identical_repeats()

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
Cohesion: 0.15
Nodes (5): FramingEngine, test_portrait_crop_geometry_and_bounds(), test_trajectory_smoothing_and_scene_cut_isolation(), `ZEZ-044`: Boundary Safety Containment (13M.12), `ZEZ-055`: Authoritative Preview-to-Render Mathematical Parity (13M.12/13M.13)

### Community 137 - "TestClient"
Cohesion: 0.21
Nodes (5): client(), test_ai_providers_list_and_test_probe(), test_documentation_center_endpoints(), test_queue_stats_and_job_logs(), test_system_resources_endpoint()

### Community 138 - "README.md"
Cohesion: 0.10
Nodes (14): 1. Threat Model & Context, 3. Source Media Immutability & Missing vs Deleted Distinction, 4. Export Overwrite & Confirmation Rules, 5. AI Video Editor Security Boundary, 6. Backup & Restore Strategy, ZezEdit 2.0 — Security & Data Safety Architecture, ADR-01: Single Local Monolith (FastAPI + React) vs Microservices, ADR-02: CPU-First Local Processing & Streaming I/O (+6 more)

### Community 139 - "export_service.py"
Cohesion: 0.13
Nodes (7): AudioConfig, ExportPreset, ValidationDetails, AudioPipeline, test_audio_pipeline_loudnorm_and_volume_filter_chains(), test_audio_pipeline_filters(), test_export_presets_catalog()

### Community 155 - "ZezEdit 2.0 — Feature & Verification Checklist"
Cohesion: 0.17
Nodes (11): Milestone 10: Character Extraction Studio, Character Library & End-to-End Reliability Checklist, Milestone 12: Pre-Deletion Baseline Reconstruction & Feature Parity Checklist, Milestone 13: ZezEdit 1.0 Exact Feature Parity Specification Checklist, Milestone 1 — Architecture Redesign & Safe Project Foundation, Milestone 2 — Core Backend, Database & Persistent Project Management, Milestone 4 — Media Ingestion, Import & Media Library, Milestone 5: Video Analysis Engine, Transcription & Visual Understanding Verification, Milestone 6: AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking Verification (+3 more)

### Community 158 - "ZezEdit 2.0 — Master Requirements Specification"
Cohesion: 0.33
Nodes (5): 1. Mission & Product Vision, 2. Hardware & Resource Constraints (Mandatory), 4. Mandatory Data Protection & Reliability Rules, 5. Planned Milestone Sequence, ZezEdit 2.0 — Master Requirements Specification

### Community 159 - "v1/timeline.py"
Cohesion: 0.06
Nodes (19): add_text_overlay(), approve_plan(), create_timeline(), delete_clip(), duplicate_clip(), get_ai_editor_service(), get_command_service(), get_history() (+11 more)

### Community 163 - "24. Conclusion, Parity Scorecard & Milestone 19 Transition Path"
Cohesion: 0.67
Nodes (3): 24. Conclusion, Parity Scorecard & Milestone 19 Transition Path, Parity Scorecard Summary:, Transition Path to Milestone 19:

### Community 165 - "ZezEdit 2.0 — System Architecture"
Cohesion: 0.25
Nodes (7): 1. Overview & Guiding Principles, 2. High-Level System Architecture, 3. Frontend Module Boundaries (`frontend/src/`), 6. Windows 11 Startup & Shutdown Lifecycle, Graceful Shutdown Sequence, Startup Sequence, ZezEdit 2.0 — System Architecture

## Knowledge Gaps
- **1 isolated node(s):** `zezedit-backend`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1490 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **54 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobOrchestrator` connect `JobOrchestrator` to `AppError`, `highlights.py`, `AppError`, `export_service.py`, `HighlightDiscoveryEngine`, `test_milestone24_timeline_operations_coverage.py`, `ProjectService`, `exports.py`, `run_migrations`, `preview_user_data_cleanup_endpoint`, `.delete_job`, `.from_root`, `.execute_render_job`, `SpeechToTextProvider`, `ZezEdit 2.0 — Comprehensive Technical Audit & Evidence-Based Verification Report`, `get_settings`, `v1/health.py`, `.__init__`, `VideoAnalysisPipeline`, `ZezEdit 2.0 — Media Storage & Processing Pipeline`, `Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)`, `pytest`, `Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)`, `TimelineRenderer`, `export.py`, `v1/jobs.py`, `sqlite3`, `sqlite_session`?**
  _High betweenness centrality (0.241) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Settings` (e.g. with `get_settings_service()` and `list_ai_providers()`) actually correct?**
  _`Settings` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zezedit-backend` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `apiClient.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.04520592020592021 - nodes in this community are weakly interconnected._
- **Why does ``ZEZ-063`: Graceful Render Job Cancellation` connect `pytest` to `JobOrchestrator`, `WorkingQueueView.tsx`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `JobOrchestrator` (e.g. with `get_system_resources()` and `_run_discovery_background()`) actually correct?**
  _`JobOrchestrator` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Should `AppError` be split into smaller, more focused modules?**
  _Cohesion score 0.07637362637362638 - nodes in this community are weakly interconnected._