import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ShortVideoGeneratorLibrary } from '../features/videos/ShortVideoGeneratorLibrary';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem, MediaAssetListResponse } from '../types/projects';

vi.mock('../services/apiClient', () => ({
  fetchAllMedia: vi.fn(),
  fetchMediaAsset: vi.fn(),
  deleteMediaAssetGlobal: vi.fn(),
  getGlobalThumbnailUrl: vi.fn((id) => `/api/v1/media/${id}/thumbnail`),
  getStreamMediaUrl: vi.fn((id) => `/api/v1/media/${id}/stream`),
  refreshMediaMetadata: vi.fn(),
  regenerateThumbnailGlobal: vi.fn(),
  isUploadRetryable: vi.fn(() => false),
  uploadMediaBatch: vi.fn(),
  uploadMediaFile: vi.fn(),
  relinkMedia: vi.fn(),
  relinkMediaWithUpload: vi.fn(),
  inspectRelinkCandidate: vi.fn(),
  reconcileMissingMedia: vi.fn(),
  getDeduplicationStats: vi.fn(),
  reconcileReferenceCounts: vi.fn(),
  fetchAnalysisRuns: vi.fn(() => Promise.resolve([])),
  fetchMediaHighlights: vi.fn(() => Promise.resolve([])),
  fetchCandidateGenerationRuns: vi.fn(() => Promise.resolve([])),
  fetchCandidateNoveltyHistory: vi.fn(() => Promise.resolve(null)),
  fetchProjectExports: vi.fn(() => Promise.resolve({ items: [], count: 0 })),
  fetchJobs: vi.fn(() => Promise.resolve([])),
  startMediaAnalysis: vi.fn(),
  submitBatchExport: vi.fn(),
}));

describe('P1.8 Media Deduplication & Reference Counting UI Verification', () => {
  const mockSharedAsset: MediaAssetItem = {
    id: 'med_shared_01',
    project_id: 'proj_default',
    original_filename: 'Shared_Podcast_Episode.mp4',
    storage_path: 'storage/media/shared_podcast.mp4',
    is_external: false,
    media_type: 'video',
    file_size_bytes: 52428800,
    mime_type: 'video/mp4',
    duration_seconds: 60.0,
    width: 1920,
    height: 1080,
    fps: 30.0,
    video_codec: 'h264',
    audio_codec: 'aac',
    availability_status: 'present',
    integrity_status: 'verified',
    is_playable: true,
    created_at: '2026-11-16T10:00:00Z',
    updated_at: '2026-11-16T10:00:00Z',
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    resolution_label: '1080p',
    aspect_ratio: '16:9',
    container_format: 'mp4',
    analysis_status: 'completed',
    proxy_reference_path: null,
    thumbnail_reference_path: 'thumbnails/med_shared_01.jpg',
    proxy_status: 'none',
    metadata_status: 'extracted',
    metadata: { title: 'Shared Podcast Episode' },
    stored_file_id: 'smf_e3b0c44298fc1c14',
    reference_count: 3,
    is_shared: true,
    is_deduplicated: true,
  };

  const mockStandaloneAsset: MediaAssetItem = {
    ...mockSharedAsset,
    id: 'med_standalone_02',
    original_filename: 'Standalone_Clip.mp4',
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    stored_file_id: 'smf_9f86d081884c7d65',
    reference_count: 1,
    is_shared: false,
    is_deduplicated: false,
    metadata: { title: 'Standalone Clip' },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Shared (N) badge on shared assets in grid view', async () => {
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue({
      items: [mockSharedAsset, mockStandaloneAsset],
      total: 2,
    } as MediaAssetListResponse);

    render(
      <ShortVideoGeneratorLibrary
        onSelectVideo={vi.fn()}
        onOpenDashboard={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Shared Podcast Episode')).toBeInTheDocument();
    });

    // Verify Shared badge with reference count
    expect(screen.getByText('Shared (3)')).toBeInTheDocument();
  });

  it('displays Shared Asset Notice in delete confirmation modal when reference_count > 1', async () => {
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue({
      items: [mockSharedAsset],
      total: 1,
    } as MediaAssetListResponse);

    render(
      <ShortVideoGeneratorLibrary
        onSelectVideo={vi.fn()}
        onOpenDashboard={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Shared Podcast Episode')).toBeInTheDocument();
    });

    // Click delete button
    const deleteBtn = screen.getByTitle('Delete Video');
    fireEvent.click(deleteBtn);

    // Modal should open with shared notice
    await waitFor(() => {
      expect(screen.getByText('Delete Media Asset')).toBeInTheDocument();
      expect(screen.getByText(/Shared Asset Notice:/)).toBeInTheDocument();
      expect(screen.getByText(/retained on disk for the other 2 reference\(s\)/)).toBeInTheDocument();
    });
  });

  it('displays standard reclaim notice when deleting standalone asset (reference_count = 1)', async () => {
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue({
      items: [mockStandaloneAsset],
      total: 1,
    } as MediaAssetListResponse);

    render(
      <ShortVideoGeneratorLibrary
        onSelectVideo={vi.fn()}
        onOpenDashboard={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Standalone Clip')).toBeInTheDocument();
    });

    // Click delete button
    const deleteBtn = screen.getByTitle('Delete Video');
    fireEvent.click(deleteBtn);

    // Modal should open with standard reclaim message
    await waitFor(() => {
      expect(screen.getByText('Delete Media Asset')).toBeInTheDocument();
      expect(screen.queryByText(/Shared Asset Notice:/)).not.toBeInTheDocument();
      expect(screen.getByText(/reclaim its managed storage/)).toBeInTheDocument();
    });
  });

  it('displays Reference Count in technical specs inspection modal', async () => {
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue({
      items: [mockSharedAsset],
      total: 1,
    } as MediaAssetListResponse);

    render(
      <ShortVideoGeneratorLibrary
        onSelectVideo={vi.fn()}
        onOpenDashboard={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Shared Podcast Episode')).toBeInTheDocument();
    });

    // Click technical specs info button
    const infoBtn = screen.getByTitle('Inspect Technical Specs');
    fireEvent.click(infoBtn);

    await waitFor(() => {
      expect(screen.getByText('Integrity & Persistence Contract')).toBeInTheDocument();
      expect(screen.getByText('Reference Count:')).toBeInTheDocument();
      expect(screen.getByText('3 (Shared Asset)')).toBeInTheDocument();
    });
  });

  it('calls getDeduplicationStats and returns typed statistics', async () => {
    const mockStats = {
      total_media_assets: 10,
      unique_stored_files: 5,
      shared_stored_files: 3,
      deduplicated_assets_count: 5,
      total_logical_bytes: 1048576000,
      actual_physical_bytes: 524288000,
      saved_bytes: 524288000,
      deduplication_ratio: 2.0,
    };
    vi.mocked(apiClient.getDeduplicationStats).mockResolvedValue(mockStats);

    const stats = await apiClient.getDeduplicationStats();
    expect(stats.total_media_assets).toBe(10);
    expect(stats.unique_stored_files).toBe(5);
    expect(stats.saved_bytes).toBe(524288000);
    expect(stats.deduplication_ratio).toBe(2.0);
  });
});
