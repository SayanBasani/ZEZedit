export interface SystemResourceMetrics {
  cpu_percent: number;
  process_cpu_percent: number;
  cpu_count_logical: number;
  cpu_count_physical: number;
  memory_total_mb: number;
  memory_available_mb: number;
  memory_used_mb: number;
  memory_percent: number;
  process_memory_rss_mb: number;
  process_memory_vms_mb: number;
  active_workers: number;
  pending_jobs: number;
  max_concurrent_jobs: number;
  execution_mode: string;
  timestamp: string;
}

export interface QueueStats {
  total_jobs: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  by_type: Record<string, number>;
  active_job_ids: string[];
}

export interface JobLogs {
  job_id: string;
  job_type: string;
  status: string;
  current_stage: string | null;
  progress_percent: number;
  error_message: string | null;
  logs: string[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AIProviderCapability {
  task: string;
  supported: boolean;
  description: string;
}

export interface AIProvider {
  id: string;
  name: string;
  provider_type: 'local_llm' | 'local_asr' | 'heuristic';
  status: 'ready' | 'offline' | 'degraded';
  is_local: boolean;
  base_url: string | null;
  active_model: string;
  available_models: string[];
  capabilities: AIProviderCapability[];
  latency_ms: number | null;
  last_health_check: string | null;
  details: string | null;
}

export interface AIProviderTestResult {
  provider_id: string;
  reachable: boolean;
  latency_ms: number | null;
  available_models: string[];
  error: string | null;
}

export interface DocCategory {
  id: string;
  name: string;
  description: string;
  article_count: number;
}

export interface DocArticle {
  id: string;
  title: string;
  category: string;
  summary: string;
  tags: string[];
  reading_time_minutes: number;
}

export interface DocArticleDetail {
  id: string;
  title: string;
  category: string;
  summary: string;
  markdown_content: string;
  tags: string[];
  related_article_ids: string[];
  updated_at: string;
}

export interface CandidateCounts {
  total: number;
  recommended: number;
  approved: number;
  rejected: number;
  modified: number;
}

export interface ExportCounts {
  total: number;
  completed: number;
  failed: number;
  rendering: number;
}

export interface VideoWorkflowState {
  video_id: string;
  project_id: string;
  video_name: string;
  duration_seconds: number;
  current_stage: string;
  completed_stages: string[];
  available_next_actions: string[];
  active_jobs: Array<Record<string, unknown>>;
  failed_jobs: Array<Record<string, unknown>>;
  candidate_counts: CandidateCounts;
  approved_short_counts: number;
  export_counts: ExportCounts;
  last_modified: string | null;
}

export interface BatchExportItemPayload {
  candidate_id: string;
  title?: string;
  preset?: string;
  caption_mode?: string;
  normalize_audio?: boolean;
}

export interface BatchExportPayload {
  candidate_ids: string[];
  preset?: string;
  caption_mode?: string;
  normalize_audio?: boolean;
  export_items?: BatchExportItemPayload[];
}

export interface BatchExportItemResult {
  candidate_id: string;
  export_id: string;
  job_id: string;
  status: string;
  output_filename: string;
}

export interface SkippedCandidate {
  candidate_id: string;
  reason: string;
}

export interface BatchExportResponse {
  batch_id: string;
  project_id: string;
  total_requested: number;
  total_submitted: number;
  items: BatchExportItemResult[];
  skipped_candidates: SkippedCandidate[];
}

export interface StorageBreakdown {
  storage_root: string;
  total_disk_space_bytes: number;
  free_disk_space_bytes: number;
  used_disk_space_bytes: number;
  total_application_storage_bytes?: number;
  recoverable_storage_bytes?: number;
  protected_storage_bytes?: number;
  is_low_storage: boolean;
  low_storage_threshold_bytes: number;
  categories: {
    source_media_bytes: number;
    canonical_shared_media_bytes?: number;
    logical_media_assets_bytes?: number;
    generated_video_bytes?: number;
    rendered_exports_bytes?: number;
    extracted_audio_bytes?: number;
    keyframes_and_thumbnails_bytes?: number;
    transcripts_and_analysis_bytes?: number;
    temporary_uploads_bytes?: number;
    temporary_rendering_bytes?: number;
    database_and_backups_bytes?: number;
    proxies_bytes: number;
    thumbnails_bytes: number;
    extracted_frames_bytes: number;
    temp_cache_bytes: number;
    exports_bytes: number;
    database_bytes: number;
    backups_bytes: number;
    logs_bytes: number;
    characters_bytes?: number;
    timelines_bytes?: number;
  };
  directories: Record<string, string>;
  quota_status?: StorageQuotaStatus | null;
}

export interface CleanupCandidateItem {
  candidate_id: string;
  relative_path: string;
  category: string;
  size_bytes: number;
  reason: string;
  last_modified_at: string;
  associated_project_id?: string | null;
  associated_job_id?: string | null;
  is_blocked: boolean;
  protection_reason?: string | null;
}

export interface MaintenanceCleanupPreview {
  preview_id: string;
  total_candidates: number;
  eligible_candidates_count: number;
  total_eligible_bytes: number;
  blocked_candidates_count: number;
  total_blocked_bytes: number;
  categories_summary: Record<string, { count: number; bytes: number }>;
  candidates: CleanupCandidateItem[];
  protected_categories: string[];
  generated_at: string;
}

export interface MaintenanceCleanupExecution {
  status: string;
  operation_id: string;
  deleted_count: number;
  bytes_reclaimed: number;
  skipped_count: number;
  failed_count: number;
  deleted_items: Array<{
    candidate_id: string;
    path: string;
    category: string;
    size_bytes: number;
  }>;
  skipped_items: Array<{
    candidate_id: string;
    path: string;
    reason: string;
  }>;
  failed_items: Array<{
    candidate_id: string;
    path: string;
    error: string;
  }>;
  executed_at: string;
}

export interface StorageQuotaSettings {
  id: string;
  storage_limit_bytes?: number | null;
  generated_video_limit_bytes?: number | null;
  temp_storage_limit_bytes?: number | null;
  warning_threshold_percent: number;
  auto_prune_enabled: boolean;
  auto_prune_retention_hours: number;
  auto_prune_categories: string[];
  max_temp_storage_bytes?: number | null;
  updated_at: string;
}

export interface StorageQuotaStatus {
  quota_settings: StorageQuotaSettings;
  total_usage_bytes: number;
  total_utilization_pct?: number | null;
  generated_video_usage_bytes: number;
  generated_video_utilization_pct?: number | null;
  temp_storage_usage_bytes: number;
  temp_storage_utilization_pct?: number | null;
  is_warning: boolean;
  is_exceeded: boolean;
  warning_reasons: string[];
}

export interface CleanupAuditItem {
  id: string;
  operation_id: string;
  timestamp: string;
  cleanup_category: string;
  files_examined: number;
  files_deleted: number;
  files_skipped: number;
  bytes_reclaimed: number;
  is_automatic: boolean;
  failure_reasons: Array<{ candidate_id?: string; path?: string; error?: string }>;
  details: Record<string, any>;
}

export interface CleanupPreview {
  eligible_files_count: number;
  total_bytes_to_free: number;
  confirmation_token: string;
  eligible_files_preview: Array<{
    path: string;
    filename: string;
    category: string;
    size_bytes: number;
  }>;
  protected_categories: string[];
  generated_at: string;
}

export interface CleanupExecution {
  status: string;
  deleted_files_count: number;
  freed_bytes: number;
  executed_at: string;
}

export interface BackupItem {
  backup_filename: string;
  backup_path: string;
  file_size_bytes: number;
  created_at: string;
  is_safety_snapshot: boolean;
  integrity_verified: boolean;
}

export interface DbIntegrityReport {
  healthy: boolean;
  integrity_check: string;
  foreign_key_check: string;
  journal_mode: string;
  table_counts: Record<string, number>;
  orphaned_records: Record<string, number>;
  issues: string[];
  checked_at: string;
}

export interface RecoveryStatus {
  last_backup: BackupItem | null;
  total_backups_available: number;
  interrupted_jobs_count: number;
  interrupted_jobs: Array<{ id: string; job_type: string; updated_at: string }>;
  missing_media_count: number;
  missing_media_assets: Array<{ id: string; project_id: string; original_filename: string; storage_path: string }>;
  last_project_activity: { project_id: string; event_type: string; created_at: string } | null;
  recovery_ready: boolean;
  checked_at: string;
}

export interface MediaRelinkResult {
  asset: any;
  match_status: 'exact' | 'compatible' | 'mismatch';
  warnings: string[];
  comparison: Record<string, any>;
  relinked_at?: string | null;
}

export interface MediaReconcileResult {
  total_checked: number;
  restored_count: number;
  still_missing_count: number;
  restored_assets: string[];
  still_missing_assets: string[];
}

export interface MediaIntegrityResult {
  asset_id: string;
  project_id: string;
  original_filename: string;
  storage_path: string;
  availability_status: string;
  integrity_status: string;
  file_exists: boolean;
  file_size_bytes: number;
  size_matches: boolean;
  probe_ok: boolean;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  issues: string[];
  checked_at: string;
}

