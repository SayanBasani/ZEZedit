export interface ProjectItem {
  id: string;
  name: string;
  description: string | null;
  status: 'active' | 'archived' | 'deleted';
  project_config: Record<string, any>;
  storage_subdir: string;
  created_at: string;
  updated_at: string;
  last_opened_at: string | null;
  archived_at: string | null;
}

export interface ProjectListResponse {
  items: ProjectItem[];
  total: number;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
  project_config?: Record<string, any>;
}

export interface MediaAssetItem {
  id: string;
  project_id: string;
  original_filename: string;
  storage_path: string;
  is_external: boolean;
  media_type: string;
  file_size_bytes: number;
  mime_type: string | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  availability_status: 'present' | 'missing' | 'deleted';
  proxy_reference_path: string | null;
  thumbnail_reference_path: string | null;
  proxy_status: 'none' | 'generating' | 'ready' | 'failed';
  metadata_status: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  sha256?: string | null;
  integrity_status?: string | null;
  upload_attempt_id?: string | null;
  integrity_details_json?: string | null;
  last_integrity_check?: string | null;
  media_asset_id?: string | null;
  parent_job_id?: string | null;
  video_title?: string | null;
  elapsed_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
  display_filename?: string | null;
  file_extension?: string | null;
  container_format?: string | null;
  resolution_label?: string | null;
  aspect_ratio?: string | null;
  audio_stream_count?: number;
  subtitle_stream_count?: number;
  audio_languages?: string[];
  subtitle_languages?: string[];
  pixel_format?: string | null;
  bitrate?: number | null;
  analysis_status?: string;
  is_playable?: boolean;
  thumbnail_available?: boolean;
  thumbnail_url?: string | null;
  streaming_url?: string | null;
  dashboard_url?: string | null;
  relinked_at?: string | null;
  previous_storage_path?: string | null;
  previous_sha256?: string | null;
  relink_match_status?: string | null;
  stored_file_id?: string | null;
  reference_count?: number;
  is_shared?: boolean;
  is_deduplicated?: boolean;
}

export interface MediaListQueryParams {
  search?: string;
  resolution?: string;
  format?: string;
  video_codec?: string;
  duration_min?: number;
  duration_max?: number;
  date_from?: string;
  date_to?: string;
  integrity_status?: string;
  analysis_status?: string;
  missing_thumbnail?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
  availability?: string;
  media_type?: string;
  proxy_status?: string;
}

export interface MediaImportLocalPayload {
  file_path: string;
  copy_to_storage?: boolean;
  generate_proxy?: boolean;
  generate_thumbnail?: boolean;
}

export interface MediaStorageStats {
  project_id: string;
  total_media_count: number;
  total_media_bytes: number;
  total_proxy_bytes: number;
  total_thumbnail_bytes: number;
  managed_files_count: number;
  external_files_count: number;
}

export interface MediaAssetListResponse {
  items: MediaAssetItem[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

export interface MediaBatchUploadItemResult {
  filename: string;
  success: boolean;
  media_id?: string | null;
  asset?: MediaAssetItem | null;
  error?: string | null;
  error_code?: string | null;
  is_deduplicated?: boolean;
  reference_count?: number;
}

export interface MediaDeduplicationStats {
  total_media_assets: number;
  unique_stored_files: number;
  shared_stored_files: number;
  deduplicated_assets_count: number;
  total_logical_bytes: number;
  actual_physical_bytes: number;
  saved_bytes: number;
  deduplication_ratio: number;
}

export interface MediaBatchUploadResponse {
  total: number;
  succeeded: number;
  failed: number;
  items: MediaBatchUploadItemResult[];
}

export type UploadTransferState =
  | 'idle'
  | 'waiting'
  | 'queued'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error'
  | 'failed'
  | 'aborted'
  | 'cancelled'
  | 'retrying';

export interface UploadProgressInfo {
  filename: string;
  loaded: number;
  total: number | null;
  percentage: number | null;
  state: UploadTransferState;
  error?: string | null;
  mediaAsset?: MediaAssetItem | null;
  attemptId?: string;
  attemptCount?: number;
  retryable?: boolean;
}

export interface UploadProgressOptions {
  onProgress?: (progress: UploadProgressInfo) => void;
  signal?: AbortSignal;
  testDelaySeconds?: number;
  attemptId?: string;
  attemptCount?: number;
  expectedSize?: number;
  expectedSha256?: string;
  testFailureCode?: number;
  testFailRegistration?: boolean;
  testFailPublication?: boolean;
  testNetworkError?: boolean;
}

export interface JobItem {
  id: string;
  project_id: string | null;
  job_type: string;
  status: 'queued' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed' | 'interrupted';
  priority: number;
  progress_pct: number;
  current_stage: string | null;
  worker_id: string | null;
  worker_pid: number | null;
  input_config: Record<string, any>;
  result_metadata: Record<string, any> | null;
  error_message: string | null;
  retry_count: number;
  max_attempts: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  cancellation_requested_at: string | null;
  cancelled_at: string | null;
  updated_at: string;
  media_asset_id?: string | null;
  parent_job_id?: string | null;
  video_title?: string | null;
  elapsed_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
}

export interface JobListResponse {
  items: JobItem[];
  total: number;
}

export interface AppSettingsData {
  storage_root: string;
  temporary_storage_location: string;
  proxy_resolution: string;
  proxy_generate_on_import: boolean;
  cpu_processing_limits: Record<string, any>;
  memory_limits_mb: number;
  ai_provider_config: Record<string, any>;
  model_preferences: Record<string, any>;
  default_export_preferences: Record<string, any>;
  application_appearance: Record<string, any>;
}
