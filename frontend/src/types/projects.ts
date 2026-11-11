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
