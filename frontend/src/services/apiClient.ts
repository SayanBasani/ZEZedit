import { ApiErrorEnvelope, HealthResponse, SystemInfoResponse } from '../types/health';
import {
  AppSettingsData,
  JobItem,
  JobListResponse,
  MediaAssetListResponse,
  ProjectCreatePayload,
  ProjectItem,
  ProjectListResponse,
} from '../types/projects';

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
export function fetchProjectMedia(projectId: string): Promise<MediaAssetListResponse> {
  return request<MediaAssetListResponse>(`/projects/${projectId}/media`);
}

// ==================== JOBS ====================
export function fetchJobs(projectId?: string): Promise<JobListResponse> {
  const q = projectId ? `?project_id=${projectId}` : '';
  return request<JobListResponse>(`/jobs${q}`);
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
