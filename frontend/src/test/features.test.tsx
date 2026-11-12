import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DashboardView } from '../features/dashboard/DashboardView';
import { ProjectsManager } from '../features/projects/ProjectsManager';
import { SettingsManager } from '../features/settings/SettingsManager';
import { ThemeProvider } from '../context/ThemeContext';
import { ProjectItem, JobItem } from '../types/projects';

// Mock apiClient
vi.mock('../services/apiClient', () => ({
  fetchAppSettings: vi.fn().mockResolvedValue({
    storage_root: 'D:\\ZezEdit\\storage',
    temporary_storage_location: 'D:\\ZezEdit\\storage\\temp',
    proxy_resolution: '480p',
    proxy_generate_on_import: true,
    cpu_processing_limits: {
      max_threads: 4,
      max_concurrent_jobs: 1,
      target_device: 'cpu',
    },
    memory_limits_mb: 8192,
    ai_provider_config: { ollama_endpoint: 'http://127.0.0.1:11434' },
    model_preferences: { primary: 'qwen3-vl:4b-instruct' },
    default_export_preferences: {
      resolution: '1080x1920',
      fps: 30,
      format: 'mp4',
    },
    application_appearance: { theme: 'dark' },
  }),
  fetchHealth: vi.fn().mockResolvedValue({
    status: 'ok',
    version: '2.0.0-alpha.1',
    timestamp: '2026-11-11T12:00:00Z',
    database: { connected: true, integrity: 'ok', schema_version: 2 },
    ollama: { reachable: true, active_model: 'qwen3-vl:4b-instruct' },
    storage: {
      storage_root: 'D:\\ZezEdit\\storage',
      writable: true,
      free_space_gb: 120.5,
      total_space_gb: 512.0,
      low_space_warning: false,
    },
  }),
  updateAppSettings: vi.fn().mockResolvedValue({}),
  fetchStorageBreakdown: vi.fn().mockResolvedValue({
    storage_root: 'D:\\ZezEdit\\storage',
    total_disk_space_bytes: 500_000_000_000,
    free_disk_space_bytes: 250_000_000_000,
    used_disk_space_bytes: 250_000_000_000,
    is_low_storage: false,
    low_storage_threshold_bytes: 5_000_000_000,
    categories: {
      source_media_bytes: 0,
      proxies_bytes: 0,
      thumbnails_bytes: 0,
      extracted_frames_bytes: 0,
      temp_cache_bytes: 0,
      exports_bytes: 0,
      database_bytes: 0,
      backups_bytes: 0,
      logs_bytes: 0,
    },
    directories: {},
  }),
  fetchBackups: vi.fn().mockResolvedValue([]),
  fetchRecoveryStatus: vi.fn().mockResolvedValue({
    last_backup: null,
    total_backups_available: 0,
    interrupted_jobs_count: 0,
    interrupted_jobs: [],
    missing_media_count: 0,
    missing_media_assets: [],
    last_project_activity: null,
    recovery_ready: true,
    checked_at: '2026-11-12T00:00:00Z',
  }),
  fetchDbIntegrity: vi.fn().mockResolvedValue({
    healthy: true,
    integrity_check: 'ok',
    foreign_key_check: 'ok',
    journal_mode: 'WAL',
    table_counts: {},
    orphaned_records: {},
    issues: [],
    checked_at: '2026-11-12T00:00:00Z',
  }),
}));

const createMockProject = (overrides: Partial<ProjectItem>): ProjectItem => ({
  id: 'proj-1',
  name: 'Default Project',
  description: 'Default description',
  status: 'active',
  project_config: {},
  storage_subdir: 'proj-1-dir',
  created_at: '2026-11-11T10:00:00Z',
  updated_at: '2026-11-11T12:00:00Z',
  last_opened_at: null,
  archived_at: null,
  ...overrides,
});

const createMockJob = (overrides: Partial<JobItem>): JobItem => ({
  id: 'job-1',
  project_id: 'proj-1',
  job_type: 'media_import',
  status: 'running',
  priority: 1,
  progress_pct: 45,
  current_stage: 'Extracting keyframes',
  worker_id: 'worker-1',
  worker_pid: 1234,
  input_config: {},
  result_metadata: null,
  error_message: null,
  retry_count: 0,
  max_attempts: 3,
  created_at: '2026-11-11T12:05:00Z',
  started_at: '2026-11-11T12:05:01Z',
  completed_at: null,
  cancellation_requested_at: null,
  cancelled_at: null,
  updated_at: '2026-11-11T12:06:00Z',
  ...overrides,
});

describe('Feature View: DashboardView', () => {
  const mockProjects: ProjectItem[] = [
    createMockProject({
      id: 'proj-1',
      name: 'Podcast Highlight Reel',
      description: 'Long form conversation',
      status: 'active',
    }),
    createMockProject({
      id: 'proj-2',
      name: 'Tutorial Shorts',
      description: 'Quick vertical clips',
      status: 'archived',
    }),
  ];

  const mockJobs: JobItem[] = [
    createMockJob({
      id: 'job-1',
      project_id: 'proj-1',
      job_type: 'media_import',
      status: 'running',
      progress_pct: 45,
      current_stage: 'Extracting keyframes',
    }),
  ];

  it('renders project metrics and active background jobs', () => {
    const handleNavigate = vi.fn();
    const handleCreateProject = vi.fn();
    const handleOpenProject = vi.fn();

    render(
      <DashboardView
        projects={mockProjects}
        jobs={mockJobs}
        loading={false}
        onNavigate={handleNavigate}
        onCreateProject={handleCreateProject}
        onOpenProject={handleOpenProject}
      />
    );

    expect(screen.getByText(/Video intelligence and short generation studio/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Short Video Generator/i)).toBeInTheDocument();
    expect(screen.getByText(/Processing telemetry & pipeline stage performance/i)).toBeInTheDocument();
  });

  it('triggers navigation when clicking project card or action button', () => {
    const handleNavigate = vi.fn();
    const handleCreateProject = vi.fn();
    const handleOpenProject = vi.fn();

    render(
      <DashboardView
        projects={mockProjects}
        jobs={[]}
        loading={false}
        onNavigate={handleNavigate}
        onCreateProject={handleCreateProject}
        onOpenProject={handleOpenProject}
      />
    );

    const openGenBtn = screen.getByRole('button', { name: /Open Short Video Generator/i });
    fireEvent.click(openGenBtn);
    expect(handleNavigate).toHaveBeenCalledWith('videos');

    const queueBtn = screen.getByRole('button', { name: /Inspect Working Queue/i });
    fireEvent.click(queueBtn);
    expect(handleNavigate).toHaveBeenCalledWith('queue');
  });
});

describe('Feature View: ProjectsManager', () => {
  const mockProjects: ProjectItem[] = [
    createMockProject({
      id: 'proj-1',
      name: 'Alpha Video',
      description: 'First video',
      status: 'active',
    }),
    createMockProject({
      id: 'proj-2',
      name: 'Beta Clip',
      description: 'Second video',
      status: 'archived',
    }),
  ];

  it('filters projects by search term and status tab', () => {
    const { container } = render(
      <ProjectsManager
        projects={mockProjects}
        loading={false}
        onRefresh={vi.fn()}
        onCreate={vi.fn().mockResolvedValue(undefined)}
        onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />
    );

    // Initial state: "active" tab selected -> shows Alpha Video, hides Beta Clip
    expect(screen.getByText('Alpha Video')).toBeInTheDocument();
    expect(screen.queryByText('Beta Clip')).not.toBeInTheDocument();

    // Select Archived in status dropdown
    const selects = container.querySelectorAll('select');
    const statusSelect = selects[0];
    fireEvent.change(statusSelect, { target: { value: 'archived' } });
    expect(screen.getByText('Beta Clip')).toBeInTheDocument();
    expect(screen.queryByText('Alpha Video')).not.toBeInTheDocument();

    // Select All in status dropdown
    fireEvent.change(statusSelect, { target: { value: 'all' } });
    expect(screen.getByText('Alpha Video')).toBeInTheDocument();
    expect(screen.getByText('Beta Clip')).toBeInTheDocument();

    // Search filter
    const searchInput = screen.getByRole('searchbox');
    fireEvent.change(searchInput, { target: { value: 'Alpha' } });
    expect(screen.getByText('Alpha Video')).toBeInTheDocument();
    expect(screen.queryByText('Beta Clip')).not.toBeInTheDocument();
  });
});

describe('Feature View: SettingsManager', () => {
  it('renders theme selector and configuration groups', async () => {
    render(
      <ThemeProvider>
        <SettingsManager />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/appearance & theme/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/protected storage boundary/i)).toBeInTheDocument();

    // Switch to performance tab
    fireEvent.click(screen.getByRole('button', { name: /Processing & Performance/i }));
    expect(screen.getByText(/cpu-first hardware limits/i)).toBeInTheDocument();
  });
});
