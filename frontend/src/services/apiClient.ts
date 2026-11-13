import { ApiErrorEnvelope, HealthResponse, SystemInfoResponse } from '../types/health';
import {
  AnalysisRunItem,
  AudioAnalysisItem,
  SampledFrameItem,
  TemporalContextPayload,
  TranscriptCorrectionItem,
  TranscriptPayload,
  VideoSceneItem,
  VisualObservationItem,
} from '../types/analysis';
import {
  CandidateItem,
  CandidateClipEdit,
  CandidateClipEditSavePayload,
  CandidateGenerationRunItem,
  DiscoverHighlightsOptions,
  HighlightsOverview,
  NoveltyHistoryResponse,
  UpdateCandidatePayload,
} from '../types/highlights';
import {
  CropPreviewData,
  ReframingPlanItem,
  ReframingRevisionItem,
  RenderResultPayload,
} from '../types/reframing';
import {
  AppSettingsData,
  JobItem,
  JobListResponse,
  MediaAssetItem,
  MediaAssetListResponse,
  MediaImportLocalPayload,
  MediaStorageStats,
  ProjectCreatePayload,
  ProjectItem,
  ProjectListResponse,
} from '../types/projects';
import {
  AddTextOverlayRequest,
  AIConversation,
  AIEditingPlan,
  AIMessage,
  CreateTimelineRequest,
  InsertClipRequest,
  MoveClipRequest,
  SplitClipRequest,
  TimelineClip,
  TimelineHistoryResponse,
  TimelineRecord,
  TimelineRenderRequest,
  TimelineTrack,
  TrimClipRequest,
  UpdateClipPropsRequest,
} from '../types/timeline';
import {
  CharacterCandidate,
  CharacterExportPayload,
  CharacterProfile,
  ConfirmCandidateRequest,
  ExtractionJobConfig,
  ExtractionJobStatus,
  MergeCandidatesRequest,
  SplitCandidateRequest,
  UpdateProfileRequest,
} from '../types/character';
import {
  BackupItem,
  CleanupExecution,
  CleanupPreview,
  DbIntegrityReport,
  MediaIntegrityResult,
  MediaRelinkResult,
  RecoveryStatus,
  StorageBreakdown,
} from '../types/system';

const API_BASE = '/api/v1';

export class ApiClientError extends Error {
  code: string;
  requestId: string | null;

  constructor(message: string, code = 'REQUEST_FAILED', requestId: string | null = null) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.requestId = requestId;
  }
}

async function request<T>(endpoint: string, options?: RequestInit, timeoutMs = 10000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      let code = `HTTP_${response.status}`;
      let message = `${response.status} ${response.statusText}`;
      let requestId: string | null = null;
      try {
        const body = (await response.json()) as Partial<ApiErrorEnvelope>;
        if (body.error) {
          code = body.error.code || code;
          message = body.error.message || message;
          requestId = body.error.request_id || null;
        }
      } catch {
        // Fallback
      }
      throw new ApiClientError(message, code, requestId);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiClientError(`Request timed out after ${timeoutMs / 1000}s`, 'TIMEOUT');
    }
    throw new ApiClientError(
      err instanceof Error ? err.message : 'Unable to reach backend API',
      'NETWORK_ERROR'
    );
  } finally {
    window.clearTimeout(timer);
  }
}

// ==================== HEALTH & SYSTEM ====================
export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', undefined, 12000);
}

export function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return request<SystemInfoResponse>('/system/info', undefined, 8000);
}

// ==================== PROJECTS ====================
export function fetchProjects(includeArchived = false): Promise<ProjectListResponse> {
  return request<ProjectListResponse>(`/projects?include_archived=${includeArchived}`);
}

export function createProject(payload: ProjectCreatePayload): Promise<ProjectItem> {
  return request<ProjectItem>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchProject(projectId: string): Promise<ProjectItem> {
  return request<ProjectItem>(`/projects/${projectId}`);
}

export function archiveProject(projectId: string): Promise<ProjectItem> {
  return request<ProjectItem>(`/projects/${projectId}/archive`, { method: 'POST' });
}

export function restoreProject(projectId: string): Promise<ProjectItem> {
  return request<ProjectItem>(`/projects/${projectId}/restore`, { method: 'POST' });
}

export function deleteProject(projectId: string): Promise<void> {
  return request<void>(`/projects/${projectId}?confirmation=true`, { method: 'DELETE' });
}

// ==================== MEDIA ASSETS ====================
export function fetchAllMedia(
  params?: {
    media_type?: string;
    availability?: string;
    proxy_status?: string;
    search?: string;
  }
): Promise<MediaAssetListResponse> {
  const query = new URLSearchParams();
  if (params?.media_type && params.media_type !== 'all') query.set('media_type', params.media_type);
  if (params?.availability && params.availability !== 'all') query.set('availability', params.availability);
  if (params?.proxy_status && params.proxy_status !== 'all') query.set('proxy_status', params.proxy_status);
  if (params?.search && params.search.trim()) query.set('search', params.search.trim());

  const q = query.toString() ? `?${query.toString()}` : '';
  return request<MediaAssetListResponse>(`/media${q}`);
}

export function fetchProjectMedia(
  projectId: string,
  params?: {
    media_type?: string;
    availability?: string;
    proxy_status?: string;
    search?: string;
  }
): Promise<MediaAssetListResponse> {
  if (!projectId || projectId === 'all') {
    return fetchAllMedia(params);
  }
  const query = new URLSearchParams();
  if (params?.media_type && params.media_type !== 'all') query.set('media_type', params.media_type);
  if (params?.availability && params.availability !== 'all') query.set('availability', params.availability);
  if (params?.proxy_status && params.proxy_status !== 'all') query.set('proxy_status', params.proxy_status);
  if (params?.search && params.search.trim()) query.set('search', params.search.trim());

  const q = query.toString() ? `?${query.toString()}` : '';
  return request<MediaAssetListResponse>(`/projects/${projectId}/media${q}`);
}

export function fetchMediaAsset(assetId: string, projectId?: string): Promise<MediaAssetItem> {
  if (projectId && projectId !== 'all') {
    return request<MediaAssetItem>(`/projects/${projectId}/media/${assetId}`);
  }
  return request<MediaAssetItem>(`/media/${assetId}`);
}

export function importLocalMedia(
  projectId: string,
  payload: MediaImportLocalPayload
): Promise<MediaAssetItem> {
  if (!projectId || projectId === 'all') {
    return request<MediaAssetItem>(`/media/import-local`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
  return request<MediaAssetItem>(`/projects/${projectId}/media/import-local`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function uploadMediaFile(
  projectId: string,
  file: File,
  generateProxy = false,
  generateThumbnail = true
): Promise<MediaAssetItem> {
  const formData = new FormData();
  formData.append('file', file);

  const endpoint = (!projectId || projectId === 'all')
    ? `${API_BASE}/media/upload?generate_proxy=${generateProxy}&generate_thumbnail=${generateThumbnail}`
    : `${API_BASE}/projects/${projectId}/media/upload?generate_proxy=${generateProxy}&generate_thumbnail=${generateThumbnail}`;

  const res = await fetch(endpoint, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let msg = `Upload failed with status ${res.status}`;
    try {
      const err = await res.json();
      if (err.error?.message) msg = err.error.message;
    } catch {
      // ignore
    }
    throw new ApiClientError(msg, `HTTP_${res.status}`);
  }

  return (await res.json()) as MediaAssetItem;
}

export function generateProxy(
  projectId: string,
  assetId: string,
  profile = '480p'
): Promise<MediaAssetItem> {
  return request<MediaAssetItem>(`/projects/${projectId}/media/${assetId}/proxy`, {
    method: 'POST',
    body: JSON.stringify({ profile }),
  });
}

export function regenerateThumbnail(
  projectId: string,
  assetId: string
): Promise<MediaAssetItem> {
  return request<MediaAssetItem>(`/projects/${projectId}/media/${assetId}/thumbnail/regenerate`, {
    method: 'POST',
  });
}

export function relinkMedia(
  projectId: string,
  assetId: string,
  newStoragePath: string,
  force = false
): Promise<MediaRelinkResult> {
  return request<MediaRelinkResult>(`/projects/${projectId}/media/${assetId}/relink`, {
    method: 'POST',
    body: JSON.stringify({ new_storage_path: newStoragePath, force }),
  });
}

export function inspectRelinkCandidate(
  projectId: string,
  assetId: string,
  newStoragePath: string
): Promise<{ match_status: 'exact' | 'compatible' | 'mismatch'; warnings: string[]; comparison: Record<string, any> }> {
  return request(`/projects/${projectId}/media/${assetId}/relink/inspect`, {
    method: 'POST',
    body: JSON.stringify({ new_storage_path: newStoragePath }),
  });
}

export function checkAssetIntegrity(
  projectId: string,
  assetId: string
): Promise<MediaIntegrityResult> {
  return request<MediaIntegrityResult>(`/projects/${projectId}/media/${assetId}/integrity`);
}

export function checkProjectMediaIntegrity(
  projectId: string
): Promise<{
  project_id: string;
  total_assets: number;
  online_count: number;
  missing_count: number;
  corrupted_count: number;
  all_healthy: boolean;
  assets: MediaIntegrityResult[];
  checked_at: string;
}> {
  return request(`/projects/${projectId}/media/check-integrity`, {
    method: 'POST',
  });
}

export function deleteMediaAsset(
  projectId: string,
  assetId: string,
  deleteSource = false
): Promise<void> {
  return request<void>(
    `/projects/${projectId}/media/${assetId}?delete_source=${deleteSource}`,
    { method: 'DELETE' }
  );
}

export function fetchMediaStats(projectId: string): Promise<MediaStorageStats> {
  return request<MediaStorageStats>(`/projects/${projectId}/media/storage-stats`);
}

export function getThumbnailUrl(projectId: string, assetId: string): string {
  if (!projectId || projectId === 'all') {
    return `${API_BASE}/media/${assetId}/thumbnail`;
  }
  return `${API_BASE}/projects/${projectId}/media/${assetId}/thumbnail`;
}

export function getGlobalThumbnailUrl(assetId: string): string {
  return `${API_BASE}/media/${assetId}/thumbnail`;
}

export function getProxyUrl(projectId: string, assetId: string): string {
  return `${API_BASE}/projects/${projectId}/media/${assetId}/proxy`;
}

// ==================== JOBS / PROCESSES ====================
export interface FetchJobsParams {
  projectId?: string;
  mediaAssetId?: string;
  status?: string;
  jobType?: string;
  search?: string;
  limit?: number;
}

export function fetchJobs(params?: FetchJobsParams | string): Promise<JobListResponse> {
  if (typeof params === 'string') {
    const q = params ? `?project_id=${params}` : '';
    return request<JobListResponse>(`/jobs${q}`);
  }
  const searchParams = new URLSearchParams();
  if (params?.projectId && params.projectId !== 'all') searchParams.set('project_id', params.projectId);
  if (params?.mediaAssetId) searchParams.set('media_asset_id', params.mediaAssetId);
  if (params?.status && params.status !== 'all') searchParams.set('status', params.status);
  if (params?.jobType && params.jobType !== 'all') searchParams.set('job_type', params.jobType);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.limit) searchParams.set('limit', String(params.limit));

  const qs = searchParams.toString();
  return request<JobListResponse>(`/jobs${qs ? `?${qs}` : ''}`);
}

export function fetchJob(jobId: string): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}`);
}

export function cancelJob(jobId: string): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}/cancel`, { method: 'POST' });
}

export function retryJob(jobId: string, newAttempt = false): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}/retry?new_attempt=${newAttempt}`, { method: 'POST' });
}

export function deleteJob(jobId: string): Promise<{ status: string; deleted_job_id: string }> {
  return request<{ status: string; deleted_job_id: string }>(`/jobs/${jobId}`, { method: 'DELETE' });
}

export function deleteJobHistory(status?: string): Promise<{ status: string; deleted_count: number }> {
  const q = status ? `?status=${status}` : '';
  return request<{ status: string; deleted_count: number }>(`/jobs/history${q}`, { method: 'DELETE' });
}

// ==================== SETTINGS ====================
export function fetchAppSettings(): Promise<AppSettingsData> {
  return request<AppSettingsData>('/settings');
}

export function updateAppSettings(updates: Partial<AppSettingsData>): Promise<AppSettingsData> {
  return request<AppSettingsData>('/settings', {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export function fetchStorageBreakdown(): Promise<StorageBreakdown> {
  return request<StorageBreakdown>('/storage/breakdown');
}

export function previewCacheCleanup(): Promise<CleanupPreview> {
  return request<CleanupPreview>('/storage/cleanup/preview', { method: 'POST' });
}

export function executeCacheCleanup(confirmationToken: string): Promise<CleanupExecution> {
  return request<CleanupExecution>('/storage/cleanup/execute', {
    method: 'POST',
    body: JSON.stringify({ confirmation_token: confirmationToken }),
  });
}

export interface ClearAllDataResult {
  status: string;
  message?: string;
  before_bytes?: number;
  after_bytes?: number;
  reclaimed_bytes?: number;
  freed_bytes?: number;
  actual_reclaimed_bytes?: number;
  formatted_reclaimed_space?: string;
  deleted_files_count: number;
  purged_tables_count?: number;
  source_videos_deleted?: number;
  generated_clips_deleted?: number;
  extracted_frames_deleted?: number;
  thumbnails_deleted?: number;
  analysis_records_deleted?: number;
  temp_files_deleted?: number;
  remaining_managed_user_files?: number;
  cleared_categories?: string[];
  truncated_tables?: string[];
  timestamp?: string;
}

export interface UserDataCleanupPreview {
  total_managed_user_bytes?: number;
  estimated_reclaimable_bytes: number;
  formatted_reclaimable_space?: string;
  categories: Record<string, any>;
  source_videos_count?: number;
  video_count?: number;
  generated_clips_count?: number;
  clip_count?: number;
  analysis_artifacts_count?: number;
  frame_count?: number;
  temp_files_count?: number;
  temp_file_count?: number;
  active_jobs_count: number;
  active_jobs?: Array<{
    id: string;
    job_type: string;
    status: string;
    current_stage: string;
  }>;
  warning?: string | null;
  required_confirmation_text?: string;
  confirmation_prompt?: string;
  storage_root?: string;
  generated_at?: string;
}

export function fetchUserDataCleanupPreview(): Promise<UserDataCleanupPreview> {
  return request<UserDataCleanupPreview>('/storage/cleanup-preview');
}

export function clearAllData(confirmation = 'DELETE'): Promise<ClearAllDataResult> {
  return request<ClearAllDataResult>('/storage/clear-all-data', {
    method: 'POST',
    body: JSON.stringify({ confirmation }),
  });
}

export function clearAllUserData(confirmation = 'DELETE ALL USER DATA'): Promise<ClearAllDataResult> {
  return request<ClearAllDataResult>('/storage/clear-all-user-data', {
    method: 'POST',
    body: JSON.stringify({ confirmation }),
  });
}

export function deleteMediaAssetGlobal(assetId: string, deleteSource = false): Promise<void> {
  return request<void>(`/media/${assetId}?delete_source=${deleteSource}`, {
    method: 'DELETE',
  });
}

export function updateMediaAssetGlobal(
  assetId: string,
  updates: Partial<MediaAssetItem>
): Promise<MediaAssetItem> {
  return request<MediaAssetItem>(`/media/${assetId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export function getStreamMediaUrl(assetId: string): string {
  return `${API_BASE}/media/${assetId}/stream`;
}

export function fetchBackups(): Promise<BackupItem[]> {
  return request<BackupItem[]>('/backups');
}

export function createBackup(label = 'manual'): Promise<{
  backup_filename: string;
  backup_path: string;
  file_size_bytes: number;
  created_at: string;
  integrity_verified: boolean;
}> {
  return request('/backups', {
    method: 'POST',
    body: JSON.stringify({ label }),
  });
}

export function restoreBackup(backupFilename: string): Promise<{
  restored_from: string;
  safety_snapshot: string;
  restored_at: string;
  status: string;
}> {
  return request('/backups/restore', {
    method: 'POST',
    body: JSON.stringify({ backup_filename: backupFilename }),
  });
}

export function fetchDbIntegrity(): Promise<DbIntegrityReport> {
  return request<DbIntegrityReport>('/system/db-integrity');
}

export function fetchRecoveryStatus(): Promise<RecoveryStatus> {
  return request<RecoveryStatus>('/system/recovery-status');
}

// ==================== VIDEO ANALYSIS ====================
export function startMediaAnalysis(
  projectId: string,
  assetId: string,
  profile: 'fast' | 'balanced' | 'detailed' = 'balanced',
  config: Record<string, unknown> = {},
  runSynchronously = false,
  forceReanalysis = false
): Promise<AnalysisRunItem> {
  return request<AnalysisRunItem>(`/projects/${projectId}/media/${assetId}/analysis`, {
    method: 'POST',
    body: JSON.stringify({
      profile,
      config,
      run_synchronously: runSynchronously,
      force_reanalysis: forceReanalysis,
    }),
  });
}

export function fetchAnalysisRuns(projectId: string, assetId: string): Promise<AnalysisRunItem[]> {
  return request<AnalysisRunItem[]>(`/projects/${projectId}/media/${assetId}/analysis`);
}

export function fetchAnalysisRun(projectId: string, assetId: string, runId: string): Promise<AnalysisRunItem> {
  return request<AnalysisRunItem>(`/projects/${projectId}/media/${assetId}/analysis/${runId}`);
}

export function fetchAnalysisTranscript(projectId: string, assetId: string, runId: string): Promise<TranscriptPayload> {
  return request<TranscriptPayload>(`/projects/${projectId}/media/${assetId}/analysis/${runId}/transcript`);
}

export function fetchAnalysisScenes(projectId: string, assetId: string, runId: string): Promise<VideoSceneItem[]> {
  return request<VideoSceneItem[]>(`/projects/${projectId}/media/${assetId}/analysis/${runId}/scenes`);
}

export function fetchAnalysisFrames(projectId: string, assetId: string, runId: string): Promise<SampledFrameItem[]> {
  return request<SampledFrameItem[]>(`/projects/${projectId}/media/${assetId}/analysis/${runId}/frames`);
}

export function fetchAnalysisObservations(projectId: string, assetId: string, runId: string): Promise<VisualObservationItem[]> {
  return request<VisualObservationItem[]>(`/projects/${projectId}/media/${assetId}/analysis/${runId}/visual-observations`);
}

export function fetchAudioAnalysis(projectId: string, assetId: string, runId: string): Promise<AudioAnalysisItem | null> {
  return request<AudioAnalysisItem | null>(`/projects/${projectId}/media/${assetId}/analysis/${runId}/audio`);
}

export function fetchAnalysisContext(
  projectId: string,
  assetId: string,
  runId: string,
  timestamp: number,
  window = 15.0
): Promise<TemporalContextPayload> {
  return request<TemporalContextPayload>(
    `/projects/${projectId}/media/${assetId}/analysis/${runId}/context?timestamp=${timestamp}&window=${window}`
  );
}

export function cancelAnalysisRun(projectId: string, assetId: string, runId: string): Promise<{ message: string; run_id: string; status: string }> {
  return request<{ message: string; run_id: string; status: string }>(
    `/projects/${projectId}/media/${assetId}/analysis/${runId}/cancel`,
    { method: 'POST' }
  );
}

export function fetchAnalysisTelemetry(
  projectId: string,
  assetId: string,
  runId: string
): Promise<{
  run_id: string;
  job_id?: string;
  media_asset_id: string;
  project_id: string;
  status: string;
  profile: string;
  progress_pct: number;
  current_stage: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  source_signature?: string;
  stage_details?: Record<string, any>;
  job?: Record<string, any>;
}> {
  return request(`/projects/${projectId}/media/${assetId}/analysis/${runId}/telemetry`);
}

export function retryAnalysisRun(
  projectId: string,
  assetId: string,
  runId: string
): Promise<{ run_id: string; job_id?: string; status: string }> {
  return request(`/projects/${projectId}/media/${assetId}/analysis/${runId}/retry`, { method: 'POST' });
}

export function fetchAnalysisCacheInfo(
  projectId: string,
  assetId: string,
  runId: string
): Promise<{
  run_id: string;
  media_asset_id: string;
  status: string;
  persisted_signature?: string;
  current_signature: string;
  is_cache_valid: boolean;
  records: Record<string, number>;
}> {
  return request(`/projects/${projectId}/media/${assetId}/analysis/${runId}/cache`);
}

export function getFrameImageUrl(projectId: string, assetId: string, frameId: string): string {
  return `${API_BASE}/projects/${projectId}/media/${assetId}/analysis/frame-image/${frameId}`;
}

export function getSceneThumbnailUrl(projectId: string, assetId: string, sceneId: string): string {
  return `${API_BASE}/projects/${projectId}/media/${assetId}/analysis/scene-thumbnail/${sceneId}`;
}

export function fetchTranscriptCorrections(projectId: string, assetId: string): Promise<TranscriptCorrectionItem[]> {
  return request<TranscriptCorrectionItem[]>(`/projects/${projectId}/media/${assetId}/transcript/corrections`);
}

export function saveTranscriptCorrection(
  projectId: string,
  assetId: string,
  payload: { segment_id?: string; start_time: number; end_time: number; original_text: string; corrected_text: string }
): Promise<TranscriptCorrectionItem> {
  return request<TranscriptCorrectionItem>(`/projects/${projectId}/media/${assetId}/transcript/corrections`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deleteTranscriptCorrection(
  projectId: string,
  assetId: string,
  correctionId: string
): Promise<{ message: string; correction_id: string }> {
  return request<{ message: string; correction_id: string }>(
    `/projects/${projectId}/media/${assetId}/transcript/corrections/${correctionId}`,
    { method: 'DELETE' }
  );
}

// ==================== HIGHLIGHT DISCOVERY & REVIEW ====================
export function discoverHighlights(
  projectId: string,
  assetId: string,
  options: DiscoverHighlightsOptions = {}
): Promise<CandidateItem[]> {
  return request<CandidateItem[]>(
    `/projects/${projectId}/media/${assetId}/highlights/discover`,
    {
      method: 'POST',
      body: JSON.stringify(options),
    },
    options.run_synchronously ? 60000 : 15000
  );
}

export function generateMoreHighlights(
  projectId: string,
  assetId: string,
  options: DiscoverHighlightsOptions = {}
): Promise<CandidateItem[]> {
  return request<CandidateItem[]>(
    `/projects/${projectId}/media/${assetId}/highlights/generate-more`,
    {
      method: 'POST',
      body: JSON.stringify(options),
    },
    options.run_synchronously ? 60000 : 15000
  );
}

export function fetchCandidateGenerationRuns(
  projectId: string,
  assetId: string
): Promise<CandidateGenerationRunItem[]> {
  return request<CandidateGenerationRunItem[]>(
    `/projects/${projectId}/media/${assetId}/highlights/runs`
  );
}

export function fetchCandidateGenerationRun(
  projectId: string,
  assetId: string,
  runId: string
): Promise<CandidateGenerationRunItem> {
  return request<CandidateGenerationRunItem>(
    `/projects/${projectId}/media/${assetId}/highlights/runs/${runId}`
  );
}

export function fetchCandidateNoveltyHistory(
  projectId: string,
  assetId: string
): Promise<NoveltyHistoryResponse> {
  return request<NoveltyHistoryResponse>(
    `/projects/${projectId}/media/${assetId}/highlights/history`
  );
}

export function fetchProjectHighlights(
  projectId: string,
  reviewStatus?: string,
  category?: string,
  search?: string
): Promise<HighlightsOverview> {
  const params = new URLSearchParams();
  if (reviewStatus) params.append('review_status', reviewStatus);
  if (category) params.append('category', category);
  if (search) params.append('search', search);

  const qs = params.toString();
  return request<HighlightsOverview>(`/projects/${projectId}/highlights${qs ? `?${qs}` : ''}`);
}

export function fetchMediaHighlights(
  projectId: string,
  assetId: string,
  reviewStatus?: string,
  generationRunId?: string
): Promise<CandidateItem[]> {
  const params = new URLSearchParams();
  if (reviewStatus) params.append('review_status', reviewStatus);
  if (generationRunId) params.append('generation_run_id', generationRunId);
  const qs = params.toString();
  return request<CandidateItem[]>(`/projects/${projectId}/media/${assetId}/highlights${qs ? `?${qs}` : ''}`);
}

export function fetchCandidateDetails(
  projectId: string,
  candidateId: string
): Promise<CandidateItem> {
  return request<CandidateItem>(`/projects/${projectId}/highlights/${candidateId}`);
}

export function updateCandidate(
  projectId: string,
  candidateId: string,
  updates: UpdateCandidatePayload
): Promise<CandidateItem> {
  return request<CandidateItem>(`/projects/${projectId}/highlights/${candidateId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export function approveCandidate(projectId: string, candidateId: string): Promise<CandidateItem> {
  return request<CandidateItem>(`/projects/${projectId}/highlights/${candidateId}/approve`, {
    method: 'POST',
  });
}

export function rejectCandidate(
  projectId: string,
  candidateId: string,
  reason?: string
): Promise<CandidateItem> {
  const qs = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return request<CandidateItem>(`/projects/${projectId}/highlights/${candidateId}/reject${qs}`, {
    method: 'POST',
  });
}

export function restoreCandidate(projectId: string, candidateId: string): Promise<CandidateItem> {
  return request<CandidateItem>(`/projects/${projectId}/highlights/${candidateId}/restore`, {
    method: 'POST',
  });
}

export function queueCandidateRender(
  projectId: string,
  candidateId: string,
  queued = true
): Promise<CandidateItem> {
  return request<CandidateItem>(
    `/projects/${projectId}/highlights/${candidateId}/queue-render?queued=${queued}`,
    { method: 'POST' }
  );
}

export function bulkReviewCandidates(
  projectId: string,
  candidateIds: string[],
  action: 'approve' | 'reject' | 'restore',
  rejectionReason?: string
): Promise<{ updated_count: number; candidate_ids: string[]; action: string }> {
  return request<{ updated_count: number; candidate_ids: string[]; action: string }>(
    `/projects/${projectId}/highlights/bulk-review`,
    {
      method: 'POST',
      body: JSON.stringify({
        candidate_ids: candidateIds,
        action,
        rejection_reason: rejectionReason,
      }),
    }
  );
}

export function fetchCandidateAlternatives(
  projectId: string,
  candidateId: string
): Promise<CandidateItem[]> {
  return request<CandidateItem[]>(`/projects/${projectId}/highlights/${candidateId}/alternatives`);
}

export function fetchCandidateEdit(
  projectId: string,
  mediaAssetId: string,
  candidateId: string
): Promise<CandidateClipEdit> {
  return request<CandidateClipEdit>(
    `/projects/${projectId}/media/${mediaAssetId}/candidates/${candidateId}/edit`
  );
}

export function saveCandidateEdit(
  projectId: string,
  mediaAssetId: string,
  candidateId: string,
  payload: CandidateClipEditSavePayload
): Promise<CandidateClipEdit> {
  return request<CandidateClipEdit>(
    `/projects/${projectId}/media/${mediaAssetId}/candidates/${candidateId}/edit`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export function resetCandidateEdit(
  projectId: string,
  mediaAssetId: string,
  candidateId: string
): Promise<CandidateClipEdit> {
  return request<CandidateClipEdit>(
    `/projects/${projectId}/media/${mediaAssetId}/candidates/${candidateId}/edit/reset`,
    {
      method: 'POST',
    }
  );
}

export function trackCandidateSubjects(
  projectId: string,
  mediaAssetId: string,
  candidateId: string,
  targetAspectRatio: string = '9:16'
): Promise<CandidateClipEdit> {
  return request<CandidateClipEdit>(
    `/projects/${projectId}/media/${mediaAssetId}/candidates/${candidateId}/edit/track`,
    {
      method: 'POST',
      body: JSON.stringify({ target_aspect_ratio: targetAspectRatio }),
    }
  );
}

// ==================== SMART REFRAMING & PORTRAIT COMPOSITION ====================
export function analyzeReframing(
  projectId: string,
  mediaAssetId: string,
  options: {
    candidate_id?: string;
    target_aspect_ratio?: string;
    framing_strategy?: string;
    base_zoom?: number;
    headroom_factor?: number;
    smoothing_window?: number;
    pinned_subject_id?: string;
  } = {}
): Promise<ReframingPlanItem> {
  return request<ReframingPlanItem>(
    `/projects/${projectId}/media/${mediaAssetId}/reframing/analyze`,
    {
      method: 'POST',
      body: JSON.stringify(options),
    },
    60000
  );
}

export function fetchReframingPlan(
  projectId: string,
  planId: string
): Promise<ReframingPlanItem> {
  return request<ReframingPlanItem>(`/projects/${projectId}/reframing/${planId}`);
}

export function fetchCropPreview(
  projectId: string,
  planId: string,
  timestamp: number
): Promise<CropPreviewData> {
  return request<CropPreviewData>(
    `/projects/${projectId}/reframing/${planId}/preview?timestamp=${timestamp}`
  );
}

export function saveCropOverrides(
  projectId: string,
  planId: string,
  overrides: Array<{
    timestamp: number;
    crop_x?: number;
    crop_y?: number;
    zoom?: number;
    headroom?: number;
    target_center_x?: number;
    target_center_y?: number;
    action?: string;
  }>,
  revisionLabel?: string
): Promise<ReframingPlanItem> {
  return request<ReframingPlanItem>(`/projects/${projectId}/reframing/${planId}/overrides`, {
    method: 'POST',
    body: JSON.stringify({
      manual_overrides: overrides,
      revision_label: revisionLabel,
    }),
  });
}

export function fetchReframingRevisions(
  projectId: string,
  planId: string
): Promise<ReframingRevisionItem[]> {
  return request<ReframingRevisionItem[]>(`/projects/${projectId}/reframing/${planId}/revisions`);
}

export function restoreReframingRevision(
  projectId: string,
  planId: string,
  revisionId: string
): Promise<ReframingPlanItem> {
  return request<ReframingPlanItem>(
    `/projects/${projectId}/reframing/${planId}/revisions/${revisionId}/restore`,
    { method: 'POST' }
  );
}

export function renderReframingRevision(
  projectId: string,
  planId: string,
  revisionId?: string
): Promise<RenderResultPayload> {
  return request<RenderResultPayload>(
    `/projects/${projectId}/reframing/${planId}/render`,
    {
      method: 'POST',
      body: JSON.stringify({ revision_id: revisionId }),
    },
    120000
  );
}

export function getRenderedVideoUrl(
  projectId: string,
  planId: string,
  revisionId?: string
): string {
  const qs = revisionId ? `?revision_id=${revisionId}` : '';
  return `${API_BASE}/projects/${projectId}/reframing/${planId}/video${qs}`;
}

// ==================== RENDERING ENGINE, EXPORT & SHORTS ====================
import {
  ExportItem,
  ExportPresetItem,
  RenderExportPayload,
} from '../types/exports';

export function fetchExportPresets(projectId: string): Promise<ExportPresetItem[]> {
  return request<ExportPresetItem[]>(`/projects/${projectId}/exports/presets`);
}

export function submitExportRender(
  projectId: string,
  payload: RenderExportPayload,
  runSynchronously: boolean = false
): Promise<{ export_id: string; job_id: string; status: string; output_filename: string }> {
  const qs = runSynchronously ? '?run_synchronously=true' : '';
  return request<{ export_id: string; job_id: string; status: string; output_filename: string }>(
    `/projects/${projectId}/exports/render${qs}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    runSynchronously ? 180000 : 30000
  );
}

export function submitExportPreview(
  projectId: string,
  payload: RenderExportPayload
): Promise<{ export_id: string; job_id: string; status: string; preview_result: any }> {
  return request<{ export_id: string; job_id: string; status: string; preview_result: any }>(
    `/projects/${projectId}/exports/preview`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    90000
  );
}

export function fetchProjectExports(
  projectId: string,
  candidateId?: string
): Promise<{ items: ExportItem[]; count: number }> {
  const qs = candidateId ? `?candidate_id=${candidateId}` : '';
  return request<{ items: ExportItem[]; count: number }>(`/projects/${projectId}/exports${qs}`);
}

export function fetchExportDetails(projectId: string, exportId: string): Promise<ExportItem> {
  return request<ExportItem>(`/projects/${projectId}/exports/${exportId}`);
}

export function cancelExportRender(
  projectId: string,
  exportId: string
): Promise<{ export_id: string; job_id: string; status: string }> {
  return request<{ export_id: string; job_id: string; status: string }>(
    `/projects/${projectId}/exports/${exportId}/cancel`,
    { method: 'POST' }
  );
}

export function deleteExport(
  projectId: string,
  exportId: string
): Promise<{ export_id: string; deleted: boolean }> {
  return request<{ export_id: string; deleted: boolean }>(
    `/projects/${projectId}/exports/${exportId}`,
    { method: 'DELETE' }
  );
}

export function getExportVideoUrl(projectId: string, exportId: string): string {
  return `${API_BASE}/projects/${projectId}/exports/${exportId}/video`;
}

// ==================== TIMELINE & AI VIDEO EDITOR ====================

export function fetchTimeline(projectId: string): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timeline`);
}

export function createTimeline(
  projectId: string,
  payload: CreateTimelineRequest
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateTimelineSettings(
  projectId: string,
  timelineId: string,
  settings: { name?: string; fps?: number; canvas_width?: number; canvas_height?: number }
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines/${timelineId}/settings`, {
    method: 'PATCH',
    body: JSON.stringify(settings),
  });
}

export function addTimelineTrack(
  projectId: string,
  timelineId: string,
  track: { name: string; track_type: string; track_subtype?: string; track_order?: number }
): Promise<TimelineTrack> {
  return request<TimelineTrack>(`/projects/${projectId}/timelines/${timelineId}/tracks`, {
    method: 'POST',
    body: JSON.stringify(track),
  });
}

export function updateTimelineTrack(
  projectId: string,
  timelineId: string,
  trackId: string,
  updates: { name?: string; is_visible?: boolean; is_muted?: boolean; is_locked?: boolean; track_order?: number; height?: number }
): Promise<TimelineTrack> {
  return request<TimelineTrack>(`/projects/${projectId}/timelines/${timelineId}/tracks/${trackId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export function deleteTimelineTrack(
  projectId: string,
  timelineId: string,
  trackId: string
): Promise<{ message: string }> {
  return request<{ message: string }>(`/projects/${projectId}/timelines/${timelineId}/tracks/${trackId}`, {
    method: 'DELETE',
  });
}

export function insertTimelineClip(
  projectId: string,
  timelineId: string,
  clip: InsertClipRequest
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/clips`, {
    method: 'POST',
    body: JSON.stringify(clip),
  });
}

export function moveTimelineClip(
  projectId: string,
  timelineId: string,
  moveReq: MoveClipRequest
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/clips/move`, {
    method: 'POST',
    body: JSON.stringify(moveReq),
  });
}

export function trimTimelineClip(
  projectId: string,
  timelineId: string,
  trimReq: TrimClipRequest
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/clips/trim`, {
    method: 'POST',
    body: JSON.stringify(trimReq),
  });
}

export function splitTimelineClip(
  projectId: string,
  timelineId: string,
  splitReq: SplitClipRequest
): Promise<TimelineClip[]> {
  return request<TimelineClip[]>(`/projects/${projectId}/timelines/${timelineId}/clips/split`, {
    method: 'POST',
    body: JSON.stringify(splitReq),
  });
}

export function deleteTimelineClip(
  projectId: string,
  timelineId: string,
  clipId: string
): Promise<{ message: string }> {
  return request<{ message: string }>(`/projects/${projectId}/timelines/${timelineId}/clips/${clipId}`, {
    method: 'DELETE',
  });
}

export function duplicateTimelineClip(
  projectId: string,
  timelineId: string,
  clipId: string
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/clips/${clipId}/duplicate`, {
    method: 'POST',
  });
}

export function updateTimelineClipProps(
  projectId: string,
  timelineId: string,
  clipId: string,
  props: UpdateClipPropsRequest
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/clips/${clipId}`, {
    method: 'PATCH',
    body: JSON.stringify(props),
  });
}

export function addTimelineTextOverlay(
  projectId: string,
  timelineId: string,
  overlay: AddTextOverlayRequest
): Promise<TimelineClip> {
  return request<TimelineClip>(`/projects/${projectId}/timelines/${timelineId}/overlays/text`, {
    method: 'POST',
    body: JSON.stringify(overlay),
  });
}

export function fetchTimelineHistory(
  projectId: string,
  timelineId: string
): Promise<TimelineHistoryResponse> {
  return request<TimelineHistoryResponse>(`/projects/${projectId}/timelines/${timelineId}/history`);
}

export function undoTimeline(
  projectId: string,
  timelineId: string
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines/${timelineId}/history/undo`, {
    method: 'POST',
  });
}

export function redoTimeline(
  projectId: string,
  timelineId: string
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines/${timelineId}/history/redo`, {
    method: 'POST',
  });
}

export function fetchAIConversation(
  projectId: string,
  timelineId: string
): Promise<AIConversation> {
  return request<AIConversation>(`/projects/${projectId}/timelines/${timelineId}/ai/conversation`);
}

export function sendAIMessage(
  projectId: string,
  timelineId: string,
  msg: { message: string; playhead_time?: number; selected_clip_id?: string; selected_track_id?: string }
): Promise<AIMessage> {
  return request<AIMessage>(`/projects/${projectId}/timelines/${timelineId}/ai/messages`, {
    method: 'POST',
    body: JSON.stringify(msg),
  });
}

export function approveAIPlan(
  projectId: string,
  timelineId: string,
  planId: string
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines/${timelineId}/ai/plans/${planId}/approve`, {
    method: 'POST',
  });
}

export function rejectAIPlan(
  projectId: string,
  timelineId: string,
  planId: string
): Promise<AIEditingPlan> {
  return request<AIEditingPlan>(`/projects/${projectId}/timelines/${timelineId}/ai/plans/${planId}/reject`, {
    method: 'POST',
  });
}

export function fetchAIPlans(
  projectId: string,
  timelineId: string
): Promise<AIEditingPlan[]> {
  return request<AIEditingPlan[]>(`/projects/${projectId}/timelines/${timelineId}/ai/plans`);
}

export function restoreAIPlan(
  projectId: string,
  timelineId: string,
  planId: string
): Promise<TimelineRecord> {
  return request<TimelineRecord>(`/projects/${projectId}/timelines/${timelineId}/ai/plans/${planId}/restore`, {
    method: 'POST',
  });
}

export function renderTimeline(
  projectId: string,
  timelineId: string,
  renderReq: TimelineRenderRequest
): Promise<{ job_id: string; timeline_id: string; status: string; message: string }> {
  return request<{ job_id: string; timeline_id: string; status: string; message: string }>(
    `/projects/${projectId}/timelines/${timelineId}/render`,
    {
      method: 'POST',
      body: JSON.stringify(renderReq),
    }
  );
}

// --- Milestone 10: Character Extraction Studio & Character Library ---

export function runCharacterExtraction(
  projectId: string,
  config: ExtractionJobConfig
): Promise<ExtractionJobStatus> {
  return request<ExtractionJobStatus>(`/projects/${projectId}/characters/extract`, {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export function getCharacterExtractionJob(
  projectId: string,
  jobId: string
): Promise<ExtractionJobStatus> {
  return request<ExtractionJobStatus>(`/projects/${projectId}/characters/jobs/${jobId}`);
}

export function getCharacterCandidates(
  projectId: string,
  jobId?: string,
  includeDetached = false
): Promise<CharacterCandidate[]> {
  const params = new URLSearchParams();
  if (jobId) params.append('job_id', jobId);
  if (includeDetached) params.append('include_detached', 'true');
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<CharacterCandidate[]>(`/projects/${projectId}/characters/candidates${qs}`);
}

export function renameCharacterCandidate(
  projectId: string,
  candidateId: string,
  label: string
): Promise<CharacterCandidate> {
  return request<CharacterCandidate>(`/projects/${projectId}/characters/candidates/${candidateId}`, {
    method: 'PATCH',
    body: JSON.stringify({ label }),
  });
}

export function confirmCharacterCandidate(
  projectId: string,
  candidateId: string,
  data: ConfirmCandidateRequest
): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/projects/${projectId}/characters/candidates/${candidateId}/confirm`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function mergeCharacterCandidates(
  projectId: string,
  req: MergeCandidatesRequest
): Promise<CharacterCandidate> {
  return request<CharacterCandidate>(`/projects/${projectId}/characters/candidates/merge`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function splitCharacterCandidate(
  projectId: string,
  candidateId: string,
  req: SplitCandidateRequest
): Promise<CharacterCandidate[]> {
  return request<CharacterCandidate[]>(`/projects/${projectId}/characters/candidates/${candidateId}/split`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export function detachCharacterObservation(
  projectId: string,
  candidateId: string,
  observationId: string
): Promise<CharacterCandidate> {
  return request<CharacterCandidate>(
    `/projects/${projectId}/characters/candidates/${candidateId}/observations/${observationId}`,
    {
      method: 'DELETE',
    }
  );
}

export function rejectCharacterCandidate(
  projectId: string,
  candidateId: string
): Promise<CharacterCandidate> {
  return request<CharacterCandidate>(`/projects/${projectId}/characters/candidates/${candidateId}/reject`, {
    method: 'POST',
  });
}

export function getCharacterLibrary(
  projectId: string,
  query?: string
): Promise<CharacterProfile[]> {
  const qs = query ? `?query=${encodeURIComponent(query)}` : '';
  return request<CharacterProfile[]>(`/projects/${projectId}/characters/library${qs}`);
}

export function getCharacterProfile(
  projectId: string,
  characterId: string
): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/projects/${projectId}/characters/library/${characterId}`);
}

export function updateCharacterProfile(
  projectId: string,
  characterId: string,
  data: UpdateProfileRequest
): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/projects/${projectId}/characters/library/${characterId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export function exportCharacterJson(
  projectId: string,
  characterId: string
): Promise<CharacterExportPayload> {
  return request<CharacterExportPayload>(`/projects/${projectId}/characters/library/${characterId}/export`);
}


// ==================== SYSTEM RESOURCE MONITORING ====================

export function fetchSystemResources(): Promise<import('../types/system').SystemResourceMetrics> {
  return request<import('../types/system').SystemResourceMetrics>('/system/resources');
}


// ==================== WORKING QUEUE & STATS ====================

export function fetchQueueStats(): Promise<import('../types/system').QueueStats> {
  return request<import('../types/system').QueueStats>('/jobs/stats');
}

export function fetchJobLogs(jobId: string): Promise<import('../types/system').JobLogs> {
  return request<import('../types/system').JobLogs>(`/jobs/${jobId}/logs`);
}


// ==================== AI PROVIDERS ====================

export function fetchAIProviders(): Promise<import('../types/system').AIProvider[]> {
  return request<import('../types/system').AIProvider[]>('/ai-providers');
}

export function testAIProvider(
  providerId: string,
  baseUrl?: string
): Promise<import('../types/system').AIProviderTestResult> {
  return request<import('../types/system').AIProviderTestResult>('/ai-providers/test', {
    method: 'POST',
    body: JSON.stringify({ provider_id: providerId, base_url: baseUrl }),
  });
}

export function updateAIProvider(
  providerId: string,
  data: { base_url?: string; active_model?: string }
): Promise<import('../types/system').AIProvider> {
  return request<import('../types/system').AIProvider>(`/ai-providers/${providerId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}


// ==================== DOCUMENTATION CENTER ====================

export function fetchDocCategories(): Promise<import('../types/system').DocCategory[]> {
  return request<import('../types/system').DocCategory[]>('/docs/categories');
}

export function fetchDocArticles(
  category?: string,
  query?: string
): Promise<import('../types/system').DocArticle[]> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (query) params.append('query', query);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<import('../types/system').DocArticle[]>(`/docs/articles${qs}`);
}

export function fetchDocArticleDetail(
  articleId: string
): Promise<import('../types/system').DocArticleDetail> {
  return request<import('../types/system').DocArticleDetail>(`/docs/articles/${articleId}`);
}


// ==================== MILESTONE 18 WORKFLOW & BATCH EXPORT ====================

export function fetchVideoWorkflowState(
  projectId: string,
  mediaAssetId: string
): Promise<import('../types/system').VideoWorkflowState> {
  return request<import('../types/system').VideoWorkflowState>(
    `/projects/${projectId}/media/${mediaAssetId}/workflow`
  );
}

export function submitBatchExport(
  projectId: string,
  payload: import('../types/system').BatchExportPayload
): Promise<import('../types/system').BatchExportResponse> {
  return request<import('../types/system').BatchExportResponse>(
    `/projects/${projectId}/exports/batch`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );
}





