import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { SettingsManager } from '../features/settings/SettingsManager';
import { MediaLibraryView } from '../features/media/MediaLibraryView';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem, ProjectItem } from '../types/projects';
import {
  BackupItem,
  CleanupPreview,
  DbIntegrityReport,
  RecoveryStatus,
  StorageBreakdown,
} from '../types/system';

describe('Milestone 20: Production Hardening, Storage Management & Recovery', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('SettingsManager Multi-Tab Architecture', () => {
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

    const mockBackups: BackupItem[] = [
      {
        backup_filename: 'backup_manual_20261112.db',
        backup_path: 'D:\\ZezEdit\\storage\\backups\\backup_manual_20261112.db',
        file_size_bytes: 15_000_000,
        created_at: '2026-11-12T08:00:00Z',
        is_safety_snapshot: false,
        integrity_verified: true,
      },
      {
        backup_filename: 'backup_pre_restore_20261112.db',
        backup_path: 'D:\\ZezEdit\\storage\\backups\\backup_pre_restore_20261112.db',
        file_size_bytes: 14_900_000,
        created_at: '2026-11-12T07:50:00Z',
        is_safety_snapshot: true,
        integrity_verified: true,
      },
    ];

    const mockRecovery: RecoveryStatus = {
      last_backup: mockBackups[0],
      total_backups_available: 2,
      interrupted_jobs_count: 0,
      interrupted_jobs: [],
      missing_media_count: 0,
      missing_media_assets: [],
      last_project_activity: {
        project_id: 'proj_1',
        event_type: 'timeline_saved',
        created_at: '2026-11-12T08:15:00Z',
      },
      recovery_ready: true,
      checked_at: '2026-11-12T08:30:00Z',
    };

    const mockDbIntegrity: DbIntegrityReport = {
      healthy: true,
      integrity_check: 'ok',
      foreign_key_check: 'ok',
      journal_mode: 'WAL',
      table_counts: {
        projects: 3,
        media_assets: 8,
        analysis_runs: 5,
        shorts_candidates: 12,
        render_exports: 4,
        jobs: 15,
      },
      orphaned_records: {
        shorts_candidates: 0,
      },
      issues: [],
      checked_at: '2026-11-12T08:30:00Z',
    };

    beforeEach(() => {
      vi.spyOn(apiClient, 'fetchAppSettings').mockResolvedValue({
        storage_root: 'D:\\ZezEdit\\storage',
        temporary_storage_location: 'D:\\ZezEdit\\storage\\temp',
        proxy_resolution: '480p',
        proxy_generate_on_import: true,
        cpu_processing_limits: { max_threads: 4, max_concurrent_jobs: 1 },
        memory_limits_mb: 8192,
        ai_provider_config: { ollama_base_url: 'http://127.0.0.1:11434' },
        model_preferences: { default_vision_model: 'qwen3-vl:4b-instruct' },
        default_export_preferences: { resolution: '1080x1920', codec: 'libx264' },
        application_appearance: { theme: 'dark' },
      });
      vi.spyOn(apiClient, 'fetchHealth').mockResolvedValue({
        status: 'healthy',
        database: { status: 'healthy', database: 'zezedit.db', tables: 8 },
        storage: { status: 'healthy', storage_root: 'D:\\ZezEdit\\storage', accessible: true, writable: true },
        ollama: { reachable: true, base_url: 'http://127.0.0.1:11434', installed_models: ['qwen3-vl:4b-instruct'] },
        dependencies: { ffmpeg: { available: true }, ffprobe: { available: true } },
      } as any);
      vi.spyOn(apiClient, 'fetchStorageBreakdown').mockResolvedValue(mockStorage);
      vi.spyOn(apiClient, 'fetchBackups').mockResolvedValue(mockBackups);
      vi.spyOn(apiClient, 'fetchRecoveryStatus').mockResolvedValue(mockRecovery);
      vi.spyOn(apiClient, 'fetchDbIntegrity').mockResolvedValue(mockDbIntegrity);
    });

    it('renders General tab by default and switches to Processing & Performance tab', async () => {
      render(<SettingsManager />);

      await waitFor(() => {
        expect(screen.getByText('Studio Settings & Operations')).toBeInTheDocument();
        expect(screen.getByText('Appearance & Theme')).toBeInTheDocument();
      });

      // Switch to Performance tab
      const perfTabBtn = screen.getByRole('button', { name: /Processing & Performance/i });
      fireEvent.click(perfTabBtn);

      expect(screen.getByText('CPU-First Hardware Limits')).toBeInTheDocument();
      expect(screen.getByText('Priority Dispatch Rules & Resource Guard')).toBeInTheDocument();
      expect(screen.getByText(/Timeline & Preview \(Priority 200\)/i)).toBeInTheDocument();
    });

    it('switches to Storage tab and displays breakdown and cache preview', async () => {
      const mockPreview: CleanupPreview = {
        eligible_files_count: 5,
        total_bytes_to_free: 120_000_000,
        confirmation_token: 'CLEANUP_5_120',
        eligible_files_preview: [
          { path: 'D:\\ZezEdit\\storage\\temp\\chunk1.wav', filename: 'chunk1.wav', category: 'temp_buffer', size_bytes: 24_000_000 },
        ],
        protected_categories: ['source_media', 'database', 'rendered_exports'],
        generated_at: '2026-11-12T08:35:00Z',
      };
      vi.spyOn(apiClient, 'previewCacheCleanup').mockResolvedValue(mockPreview);

      render(<SettingsManager />);

      await waitFor(() => {
        expect(screen.getByText('Studio Settings & Operations')).toBeInTheDocument();
      });

      // Switch to Storage tab
      const storageTabBtn = screen.getByRole('button', { name: /Storage Management/i });
      fireEvent.click(storageTabBtn);

      expect(screen.getByText('Disk Space Overview')).toBeInTheDocument();
      expect(screen.getByText('Managed Storage Category Breakdown')).toBeInTheDocument();
      expect(screen.getByText('Safe Disposable Cache Cleanup')).toBeInTheDocument();

      // Click Preview Cleanup
      const previewBtn = screen.getByRole('button', { name: /Preview Cleanup/i });
      fireEvent.click(previewBtn);

      await waitFor(() => {
        expect(screen.getByText('Cleanup Preview Assessment')).toBeInTheDocument();
        expect(screen.getByText('CLEANUP_5_120')).toBeInTheDocument();
      });
    });

    it('switches to Backups & Recovery tab and displays verified backups and snapshot creator', async () => {
      render(<SettingsManager />);

      await waitFor(() => {
        expect(screen.getByText('Studio Settings & Operations')).toBeInTheDocument();
      });

      // Switch to Backups tab
      const backupsTabBtn = screen.getByRole('button', { name: /Backups & Recovery/i });
      fireEvent.click(backupsTabBtn);

      expect(screen.getByText('Create Database Backup Snapshot')).toBeInTheDocument();
      expect(screen.getByText('Crash Recovery & Project Health')).toBeInTheDocument();
      expect(screen.getByText(/Existing Backups/i)).toBeInTheDocument();
      expect(screen.getAllByText('backup_manual_20261112.db').length).toBeGreaterThan(0);
      expect(screen.getByText('backup_pre_restore_20261112.db')).toBeInTheDocument();
    });

    it('switches to Diagnostics tab and displays PRAGMA integrity check and row counts', async () => {
      render(<SettingsManager />);

      await waitFor(() => {
        expect(screen.getByText('Studio Settings & Operations')).toBeInTheDocument();
      });

      // Switch to Diagnostics tab
      const diagTabBtn = screen.getByRole('button', { name: /Diagnostics/i });
      fireEvent.click(diagTabBtn);

      expect(screen.getByText('Database Diagnostics & PRAGMA Verification')).toBeInTheDocument();
      expect(screen.getByText(/PRAGMA: ok/i)).toBeInTheDocument();
      expect(screen.getByText(/FK Valid \(0 violations\)/i)).toBeInTheDocument();
      expect(screen.getByText('Database Table Row Counts')).toBeInTheDocument();
      expect(screen.getByText('projects')).toBeInTheDocument();
      expect(screen.getByText('shorts_candidates')).toBeInTheDocument();
    });
  });

  describe('MediaLibraryView Integrity & Relink Dialog', () => {
    const mockProjects: ProjectItem[] = [
      { id: 'proj_1', name: 'Podcast Episode 1', description: 'Test Project', status: 'active', project_config: {}, created_at: '2026-11-12T00:00:00Z', updated_at: '2026-11-12T00:00:00Z', last_opened_at: null, archived_at: null, storage_subdir: 'proj_1' },
    ];

    const mockMedia: MediaAssetItem[] = [
      {
        id: 'asset_1',
        project_id: 'proj_1',
        original_filename: 'interview_raw.mp4',
        storage_path: 'D:\\Videos\\interview_raw.mp4',
        is_external: true,
        media_type: 'video',
        file_size_bytes: 500_000_000,
        mime_type: 'video/mp4',
        duration_seconds: 120.0,
        width: 1920,
        height: 1080,
        fps: 30.0,
        video_codec: 'h264',
        audio_codec: 'aac',
        availability_status: 'missing',
        proxy_reference_path: null,
        thumbnail_reference_path: null,
        proxy_status: 'none',
        metadata_status: 'extracted',
        metadata: {},
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      },
    ];

    it('renders Verify Integrity button and allows opening Relink dialog with comparison preview', async () => {
      vi.spyOn(apiClient, 'checkProjectMediaIntegrity').mockResolvedValue({
        project_id: 'proj_1',
        total_assets: 1,
        online_count: 0,
        missing_count: 1,
        corrupted_count: 0,
        all_healthy: false,
        assets: [],
        checked_at: '2026-11-12T08:40:00Z',
      });

      vi.spyOn(apiClient, 'inspectRelinkCandidate').mockResolvedValue({
        match_status: 'compatible',
        warnings: ['Resolution mismatch: Candidate is 1280x720, original was 1920x1080.'],
        comparison: {
          original_duration: 120.0,
          candidate_duration: 120.0,
          original_resolution: '1920x1080',
          candidate_resolution: '1280x720',
        },
      });

      render(
        <MediaLibraryView
          projects={mockProjects}
          currentProjectId="proj_1"
          onSelectProject={vi.fn()}
          media={mockMedia}
          stats={null}
          loading={false}
          onRefresh={vi.fn()}
        />
      );

      // Verify Integrity button is present
      const verifyBtn = screen.getByRole('button', { name: /Verify Integrity/i });
      expect(verifyBtn).toBeInTheDocument();
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(screen.getByText(/Integrity check complete: 0 online, 1 missing, 0 corrupted/i)).toBeInTheDocument();
      });

      // Click Relink File button on missing asset
      const relinkBtn = screen.getByRole('button', { name: /Relink File/i });
      fireEvent.click(relinkBtn);

      expect(screen.getByText('Relink Media File with Integrity Check')).toBeInTheDocument();

      // Enter candidate path and verify candidate
      const input = screen.getByPlaceholderText(/D:\\Videos\\interview_take_1\.mp4/i);
      fireEvent.change(input, { target: { value: 'D:\\Videos\\new_interview.mp4' } });

      const verifyCandidateBtn = screen.getByRole('button', { name: /Verify Candidate/i });
      fireEvent.click(verifyCandidateBtn);

      await waitFor(() => {
        expect(screen.getByText('Candidate Verification:')).toBeInTheDocument();
        expect(screen.getByText('COMPATIBLE')).toBeInTheDocument();
        expect(screen.getByText(/Resolution mismatch: Candidate is 1280x720/i)).toBeInTheDocument();
      });
    });
  });
});
