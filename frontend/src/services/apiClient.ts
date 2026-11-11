import { ApiErrorEnvelope, HealthResponse, SystemInfoResponse } from '../types/health';

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

async function request<T>(endpoint: string, timeoutMs = 10000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: { Accept: 'application/json' },
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
        // Fallback to HTTP status text
      }
      throw new ApiClientError(message, code, requestId);
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

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health', 12000);
}

export function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return request<SystemInfoResponse>('/system/info', 8000);
}
