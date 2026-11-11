export interface DependencyCheck {
  available: boolean;
  path_or_url: string | null;
  version: string | null;
  details: string | null;
}

export interface DatabaseHealth {
  connected: boolean;
  path: string;
  journal_mode: string;
  current_migration: string | null;
  applied_migrations: string[];
}

export interface StorageHealth {
  root: string;
  writable: boolean;
  buckets_ready: boolean;
}

export interface OllamaHealth {
  reachable: boolean;
  base_url: string;
  installed_models: string[];
  details: string | null;
}

export interface HealthResponse {
  status: 'ready' | 'degraded';
  app_name: string;
  app_version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
  storage: StorageHealth;
  ffmpeg: DependencyCheck;
  ffprobe: DependencyCheck;
  ollama: OllamaHealth;
}

export interface SystemInfoResponse {
  app_version: string;
  os_platform: string;
  python_version: string;
  cpu_count: number;
  execution_mode: string;
  max_concurrent_jobs: number;
  ffmpeg_threads: number;
  storage_root: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    request_id?: string | null;
  };
}
