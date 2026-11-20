import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { SettingsManager } from '../features/settings/SettingsManager';
import * as apiClient from '../services/apiClient';
import {
  StorageBreakdown,
  StorageQuotaStatus,
  MaintenanceCleanupPreview,
  MaintenanceCleanupExecution,
  CleanupAuditItem,
} from '../types/system';
import { HealthResponse } from '../types/health';

describe('P1.9 Storage Management, Quotas & Safe Cleanup in SettingsManager', () => {
  const mockStorage: StorageBreakdown = {
    storage_root: 'D:\\ZezEdit\\storage',
    total_disk_space_bytes: 500_000_000_000,
    free_disk_space_bytes: 250_000_000_000,
    used_disk_space_bytes: 250_000_000_000,
    is_low_storage: false,
    low_storage_threshold_bytes: 5_000_000_000,
    total_application_storage_bytes: 18_500_000_000,
    recoverable_storage_bytes: 2_500_000_000,
    protected_storage_bytes: 16_000_000_000,
    categories: {
      source_media_bytes: 12_000_000_000,
      canonical_shared_media_bytes: 10_000_000_000,
      logical_media_assets_bytes: 24_000_000_000,
      generated_video_bytes: 3_000_000_000,
      rendered_exports_bytes: 1_500_000_000,
      extracted_audio_bytes: 400_000_000,
      keyframes_and_thumbnails_bytes: 200_000_000,
      temporary_uploads_bytes: 800_000_000,
      temporary_rendering_bytes: 1_200_000_000,
      transcripts_and_analysis_bytes: 100_000_000,
      database_and_backups_bytes: 300_000_000,
      proxies_bytes: 0,
      thumbnails_bytes: 200_000_000,
      extracted_frames_bytes: 100_000_000,
      temp_cache_bytes: 2_000_000_000,
      exports_bytes: 1_500_000_000,
      database_bytes: 150_000_000,
      backups_bytes: 150_000_000,
      logs_bytes: 10_000_000,
    },
    directories: {
      media: 'D:\\ZezEdit\\storage\\media',
      temp: 'D:\\ZezEdit\\storage\\temp',
      exports: 'D:\\ZezEdit\\storage\\exports',
    },
  };

  const mockQuotaStatus: StorageQuotaStatus = {
    quota_settings: {
      id: '1',
      storage_limit_bytes: 50_000_000_000,
      generated_video_limit_bytes: 10_000_000_000,
      temp_storage_limit_bytes: 5_000_000_000,
      warning_threshold_percent: 80,
      auto_prune_enabled: false,
      auto_prune_retention_hours: 24,
      auto_prune_categories: ['orphaned_uploads', 'abandoned_ffmpeg'],
      updated_at: '2026-11-20T10:00:00Z',
    },
    total_usage_bytes: 18_500_000_000,
    total_utilization_pct: 37.0,
    generated_video_usage_bytes: 3_000_000_000,
    generated_video_utilization_pct: 30.0,
    temp_storage_usage_bytes: 2_000_000_000,
    temp_storage_utilization_pct: 40.0,
    is_warning: false,
    is_exceeded: false,
    warning_reasons: [],
  };

  const mockCleanupPreview: MaintenanceCleanupPreview = {
    preview_id: 'prev-12345',
    total_candidates: 2,
    eligible_candidates_count: 1,
    total_eligible_bytes: 500_000_000,
    blocked_candidates_count: 1,
    total_blocked_bytes: 1_000_000_000,
    categories_summary: {
      orphaned_uploads: { count: 1, bytes: 500_000_000 },
      abandoned_ffmpeg: { count: 1, bytes: 1_000_000_000 },
    },
    candidates: [
      {
        candidate_id: 'cand-1',
        relative_path: 'temp/upload_123.part',
        category: 'orphaned_uploads',
        size_bytes: 500_000_000,
        reason: 'Orphaned partial upload chunk older than 2 hours',
        last_modified_at: '2026-11-20T08:00:00Z',
        is_blocked: false,
      },
      {
        candidate_id: 'cand-2',
        relative_path: 'temp/job_active_99/scratch.mp4',
        category: 'abandoned_ffmpeg',
        size_bytes: 1_000_000_000,
        reason: 'Scratch render file from active job',
        last_modified_at: '2026-11-20T09:30:00Z',
        is_blocked: true,
        protection_reason: 'Job active_99 is currently running',
      },
    ],
    protected_categories: ['canonical_shared_media', 'active_jobs'],
    generated_at: '2026-11-20T10:00:00Z',
  };

  const mockCleanupExecution: MaintenanceCleanupExecution = {
    status: 'success',
    operation_id: 'maint-20261120-101010-abc',
    deleted_count: 1,
    bytes_reclaimed: 500_000_000,
    skipped_count: 1,
    failed_count: 0,
    deleted_items: [
      {
        candidate_id: 'cand-1',
        path: 'temp/upload_123.part',
        category: 'orphaned_uploads',
        size_bytes: 500_000_000,
      },
    ],
    skipped_items: [
      {
        candidate_id: 'cand-2',
        path: 'temp/job_active_99/scratch.mp4',
        reason: 'Job active_99 is currently running',
      },
    ],
    failed_items: [],
    executed_at: '2026-11-20T10:10:10Z',
  };

  const mockHistory: CleanupAuditItem[] = [
    {
      id: 'audit-1',
      operation_id: 'maint-20261120-101010-abc',
      timestamp: '2026-11-20T10:10:10Z',
      cleanup_category: 'orphaned_uploads',
      files_examined: 2,
      files_deleted: 1,
      files_skipped: 1,
      bytes_reclaimed: 500_000_000,
      is_automatic: false,
      failure_reasons: [],
      details: {},
    },
  ];

  const mockHealth: HealthResponse = {
    status: 'ready',
    app_name: 'ZEZEdit',
    app_version: '2.0.0-alpha.1',
    environment: 'development',
    timestamp: '2026-11-20T10:00:00Z',
    database: { connected: true, path: 'storage/db/zezedit.db', journal_mode: 'wal', current_migration: '0021', applied_migrations: [] },
    storage: { root: 'D:\\ZezEdit\\storage', writable: true, buckets_ready: true },
    ffmpeg: { available: true, path_or_url: 'ffmpeg', version: '9.0', details: null },
    ffprobe: { available: true, path_or_url: 'ffprobe', version: '9.0', details: null },
    ollama: { reachable: true, base_url: 'http://127.0.0.1:11434', installed_models: [], details: null },
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'fetchAppSettings').mockResolvedValue({
      storage_root: 'D:\\ZezEdit\\storage',
      temporary_storage_location: 'D:\\ZezEdit\\storage\\temp',
      proxy_resolution: '480p',
      proxy_generate_on_import: false,
      cpu_processing_limits: { max_threads: 4, max_concurrent_jobs: 1 },
      memory_limits_mb: 8192,
      ai_provider_config: {},
      model_preferences: {},
      default_export_preferences: { resolution: '1080x1920' },
      application_appearance: {},
    });
    vi.spyOn(apiClient, 'fetchStorageBreakdown').mockResolvedValue(mockStorage);
    vi.spyOn(apiClient, 'fetchStorageQuotas').mockResolvedValue(mockQuotaStatus);
    vi.spyOn(apiClient, 'fetchCleanupHistory').mockResolvedValue(mockHistory);
    vi.spyOn(apiClient, 'fetchHealth').mockResolvedValue(mockHealth);
    vi.spyOn(apiClient, 'fetchBackups').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchRecoveryStatus').mockResolvedValue({
      last_backup: null,
      total_backups_available: 0,
      interrupted_jobs_count: 0,
      interrupted_jobs: [],
      missing_media_count: 0,
      missing_media_assets: [],
      last_project_activity: null,
      recovery_ready: true,
      checked_at: '2026-11-20T10:00:00Z',
    });
    vi.spyOn(apiClient, 'fetchDbIntegrity').mockResolvedValue({
      healthy: true,
      integrity_check: 'ok',
      foreign_key_check: 'ok',
      journal_mode: 'wal',
      table_counts: {},
      orphaned_records: {},
      issues: [],
      checked_at: '2026-11-20T10:00:00Z',
    });
  });

  it('renders P1.9 storage overview and category breakdown with deduplication active', async () => {
    render(<SettingsManager />);

    // Click Storage tab
    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    // Storage Overview
    await waitFor(() => {
      expect(screen.getByText('Disk Space Overview')).toBeInTheDocument();
      expect(screen.getByText('Deduplication Active')).toBeInTheDocument();
    });

    // Check specific breakdown labels
    expect(screen.getByText('Source Media')).toBeInTheDocument();
    expect(screen.getByText('Canonical Shared Media')).toBeInTheDocument();
    expect(screen.getByText('Logical Assets (Virtual)')).toBeInTheDocument();
    expect(screen.getByText('Temporary Uploads')).toBeInTheDocument();
    expect(screen.getByText('Temporary Renders')).toBeInTheDocument();
  });

  it('updates storage quotas when user submits quota form', async () => {
    const updateSpy = vi.spyOn(apiClient, 'updateStorageQuotas').mockResolvedValue({
      ...mockQuotaStatus.quota_settings,
      storage_limit_bytes: 80 * 1024 * 1024 * 1024,
    });

    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(screen.getByText('Storage Quotas & Automatic Pruning Policies')).toBeInTheDocument();
    });

    // Change overall quota input
    const overallInput = screen.getAllByPlaceholderText('Unlimited')[0];
    fireEvent.change(overallInput, { target: { value: '80' } });

    // Submit quota form
    const saveQuotaBtn = screen.getByRole('button', { name: /Save Quotas & Policies/i });
    fireEvent.click(saveQuotaBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          storage_limit_bytes: 80 * 1024 * 1024 * 1024,
        })
      );
    });
  });

  it('previews maintenance cleanup and renders candidates with protected status', async () => {
    vi.spyOn(apiClient, 'previewMaintenanceCleanup').mockResolvedValue(mockCleanupPreview);

    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(screen.getByText('Safe Maintenance Cleanup & Crash Recovery')).toBeInTheDocument();
    });

    // Click Preview Candidates button
    const previewBtn = screen.getByRole('button', { name: /Scan Cleanup Candidates/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText(/upload_123\.part/)).toBeInTheDocument();
      expect(screen.getByText(/scratch\.mp4/)).toBeInTheDocument();
      expect(screen.getByText(/Job active_99 is currently running/)).toBeInTheDocument();
    });
  });

  it('executes safe cleanup and records execution summary', async () => {
    vi.spyOn(apiClient, 'previewMaintenanceCleanup').mockResolvedValue(mockCleanupPreview);
    const execSpy = vi.spyOn(apiClient, 'executeMaintenanceCleanup').mockResolvedValue(mockCleanupExecution);

    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    // Trigger preview first
    const previewBtn = screen.getByRole('button', { name: /Scan Cleanup Candidates/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Execute Safe Cleanup/i })).toBeInTheDocument();
    });

    // Click reclaim button
    const reclaimBtn = screen.getByRole('button', { name: /Execute Safe Cleanup/i });
    fireEvent.click(reclaimBtn);

    await waitFor(() => {
      expect(execSpy).toHaveBeenCalled();
      expect(screen.getByText(/Cleanup Completed Successfully/i)).toBeInTheDocument();
    });
  });

  it('recovers stale artifacts and displays success toast', async () => {
    const recoverSpy = vi.spyOn(apiClient, 'recoverStaleArtifacts').mockResolvedValue({
      status: 'success',
      recovered_files_count: 4,
      bytes_reclaimed: 150_000_000,
      formatted_bytes_reclaimed: '143.05 MB',
      missing_media_detected: 0,
      timestamp: '2026-11-20T10:10:10Z',
    });

    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Recover Stale Artifacts/i })).toBeInTheDocument();
    });

    const recoverBtn = screen.getByRole('button', { name: /Recover Stale Artifacts/i });
    fireEvent.click(recoverBtn);

    await waitFor(() => {
      expect(recoverSpy).toHaveBeenCalled();
      expect(screen.getByText(/Recovered 4 stale artifacts/i)).toBeInTheDocument();
    });
  });

  it('displays cleanup audit history in table', async () => {
    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(screen.getByText(/Recent Storage Cleanup Audit History/i)).toBeInTheDocument();
      expect(screen.getByText('maint-20261120-101010-abc')).toBeInTheDocument();
      expect(screen.getByText('Manual')).toBeInTheDocument();
    });
  });
});
