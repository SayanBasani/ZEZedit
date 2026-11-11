import { ApiErrorEnvelope, HealthResponse, SystemInfoResponse } from '../types/health';
import {
  AnalysisRunItem,
  SampledFrameItem,
  TemporalContextPayload,
  TranscriptPayload,
  VideoSceneItem,
  VisualObservationItem,
} from '../types/analysis';
import {
  CandidateItem,
  DiscoverHighlightsOptions,
  HighlightsOverview,
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
  AIConversation,
  AIEditingPlan,
  AIMessage,
  AddTextOverlayRequest,
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
export function fetchProjectMedia(
  projectId: string,
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
  return request<MediaAssetListResponse>(`/projects/${projectId}/media${q}`);
}

export function importLocalMedia(
  projectId: string,
  payload: MediaImportLocalPayload
): Promise<MediaAssetItem> {
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

  const res = await fetch(
    `${API_BASE}/projects/${projectId}/media/upload?generate_proxy=${generateProxy}&generate_thumbnail=${generateThumbnail}`,
    {
      method: 'POST',
      body: formData,
    }
  );

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
  newStoragePath: string
): Promise<MediaAssetItem> {
  return request<MediaAssetItem>(`/projects/${projectId}/media/${assetId}/relink`, {
    method: 'POST',
    body: JSON.stringify({ new_storage_path: newStoragePath }),
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
  return `${API_BASE}/projects/${projectId}/media/${assetId}/thumbnail`;
}

export function getProxyUrl(projectId: string, assetId: string): string {
  return `${API_BASE}/projects/${projectId}/media/${assetId}/proxy`;
}

// ==================== JOBS ====================
export function fetchJobs(projectId?: string): Promise<JobListResponse> {
  const q = projectId ? `?project_id=${projectId}` : '';
  return request<JobListResponse>(`/jobs${q}`);
}

export function fetchJob(jobId: string): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}`);
}

export function cancelJob(jobId: string): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}/cancel`, { method: 'POST' });
}

export function retryJob(jobId: string): Promise<JobItem> {
  return request<JobItem>(`/jobs/${jobId}/retry`, { method: 'POST' });
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

// ==================== VIDEO ANALYSIS ====================
export function startMediaAnalysis(
  projectId: string,
  assetId: string,
  profile: 'fast' | 'balanced' | 'detailed' = 'balanced',
  config: Record<string, unknown> = {},
  runSynchronously = false
): Promise<AnalysisRunItem> {
  return request<AnalysisRunItem>(`/projects/${projectId}/media/${assetId}/analysis`, {
    method: 'POST',
    body: JSON.stringify({ profile, config, run_synchronously: runSynchronously }),
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

export function getFrameImageUrl(projectId: string, assetId: string, frameId: string): string {
  return `${API_BASE}/projects/${projectId}/media/${assetId}/analysis/frame-image/${frameId}`;
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
  reviewStatus?: string
): Promise<CandidateItem[]> {
  const qs = reviewStatus ? `?review_status=${reviewStatus}` : '';
  return request<CandidateItem[]>(`/projects/${projectId}/media/${assetId}/highlights${qs}`);
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


