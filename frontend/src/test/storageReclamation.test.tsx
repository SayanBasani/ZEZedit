import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { SettingsManager } from '../features/settings/SettingsManager';
import * as apiClient from '../services/apiClient';
import { StorageBreakdown } from '../types/system';

describe('Storage Reclamation & Data Cleanup in SettingsManager', () => {
  const mockStorage: StorageBreakdown = {
    storage_root: 'D:\\ZezEdit\\storage',
    total_disk_space_bytes: 500_000_000_000,
    free_disk_space_bytes: 250_000_000_000,
    used_disk_space_bytes: 250_000_000_000,
    is_low_storage: false,
    low_storage_threshold_bytes: 5_000_000_000,
    categories: {
      source_media_bytes: 15_000_000_000,
      proxies_bytes: 2_000_000_000,
      thumbnails_bytes: 100_000_000,
      extracted_frames_bytes: 500_000_000,
      temp_cache_bytes: 1_200_000_000,
      exports_bytes: 4_500_000_000,
      database_bytes: 50_000_000,
      backups_bytes: 150_000_000,
      logs_bytes: 10_000_000,
    },
    directories: {
      media: 'D:\\ZezEdit\\storage\\media',
      temp: 'D:\\ZezEdit\\storage\\temp',
      exports: 'D:\\ZezEdit\\storage\\exports',
    },
  };

  const mockPreview: apiClient.UserDataCleanupPreview = {
    total_managed_user_bytes: 23_350_000_000,
    estimated_reclaimable_bytes: 23_350_000_000,
    formatted_reclaimable_space: '21.75 GB',
    video_count: 4,
    clip_count: 12,
    frame_count: 180,
    temp_file_count: 35,
    active_jobs_count: 1,
    categories: {},
    required_confirmation_text: 'DELETE ALL USER DATA',
    confirmation_prompt: 'Type DELETE ALL USER DATA to confirm',
    storage_root: 'D:\\ZezEdit\\storage',
    generated_at: '2026-11-13T08:00:00Z',
  };

  const mockReclamationResult: apiClient.ClearAllDataResult = {
    status: 'success',
    message: 'All managed user data has been permanently cleared and disk space reclaimed.',
    before_bytes: 23_400_000_000,
    after_bytes: 50_000_000,
    actual_reclaimed_bytes: 23_350_000_000,
    formatted_reclaimed_space: '21.75 GB',
    deleted_files_count: 231,
    purged_tables_count: 14,
    source_videos_deleted: 4,
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
    vi.spyOn(apiClient, 'fetchHealth').mockResolvedValue({
      status: 'ready',
      app_name: 'ZezEdit',
      app_version: '2.0.0-alpha.1',
      environment: 'development',
      timestamp: '2026-11-13T08:00:00Z',
      database: { connected: true, path: 'storage/db/zezedit.db', journal_mode: 'wal', current_migration: '0016', applied_migrations: [] },
      storage: { root: 'D:\\ZezEdit\\storage', writable: true, buckets_ready: true },
      ffmpeg: { available: true, path_or_url: 'ffmpeg', version: '9.0', details: null },
      ffprobe: { available: true, path_or_url: 'ffprobe', version: '9.0', details: null },
      ollama: { reachable: true, base_url: 'http://127.0.0.1:11434', installed_models: [], details: null },
    });
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
      checked_at: '2026-11-13T08:00:00Z',
    });
    vi.spyOn(apiClient, 'fetchDbIntegrity').mockResolvedValue({
      healthy: true,
      integrity_check: 'ok',
      foreign_key_check: 'ok',
      journal_mode: 'wal',
      table_counts: {},
      orphaned_records: {},
      issues: [],
      checked_at: '2026-11-13T08:00:00Z',
    });
    vi.spyOn(apiClient, 'fetchUserDataCleanupPreview').mockResolvedValue(mockPreview);
    vi.spyOn(apiClient, 'clearAllUserData').mockResolvedValue(mockReclamationResult);
  });

  it('renders Storage tab with Disk Overview and Refresh button', async () => {
    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });

    // Switch to Storage tab
    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(screen.getByText('Disk Space Overview')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Refresh Storage Usage/i })).toBeInTheDocument();
    });

    // Click refresh
    fireEvent.click(screen.getByRole('button', { name: /Refresh Storage Usage/i }));
    expect(apiClient.fetchStorageBreakdown).toHaveBeenCalled();
  });

  it('opens Complete Storage Reclamation modal, displays preview assessment, and completes wipe', async () => {
    render(<SettingsManager />);

    await waitFor(() => {
      expect(screen.getByText('Storage Management')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Storage Management'));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /Clear All Data\.\.\./i })
      ).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /Clear All Data\.\.\./i }));

    await waitFor(() => {
      expect(apiClient.fetchUserDataCleanupPreview).toHaveBeenCalled();
      expect(screen.getByText('Storage Cleanup Assessment')).toBeInTheDocument();
      expect(screen.getByText('~21.75 GB reclaimable')).toBeInTheDocument();
      expect(screen.getByText(/running process\(es\) will be stopped/i)).toBeInTheDocument();
    });

    // The submit button is disabled initially
    const confirmBtn = screen.getByRole('button', { name: /Permanently Reclaim All User Data/i });
    expect(confirmBtn).toBeDisabled();

    // Type the required confirmation token
    const input = screen.getByPlaceholderText('Type DELETE ALL USER DATA to confirm');
    fireEvent.change(input, { target: { value: 'DELETE ALL USER DATA' } });

    // Now button should be enabled
    expect(confirmBtn).not.toBeDisabled();

    // Submit
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.clearAllUserData).toHaveBeenCalledWith('DELETE ALL USER DATA');
      expect(
        screen.getByText(/Total Storage Reclamation Complete: Reclaimed 21\.75 GB/i)
      ).toBeInTheDocument();
    });
  });
});
