import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ShortVideoGeneratorLibrary } from '../features/videos/ShortVideoGeneratorLibrary';
import { MediaRelinkModal } from '../features/media/MediaRelinkModal';
import { VideoEditDashboard } from '../features/videos/VideoEditDashboard';
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
  fetchAnalysisRuns: vi.fn(() => Promise.resolve([])),
  fetchMediaHighlights: vi.fn(() => Promise.resolve([])),
  fetchCandidateGenerationRuns: vi.fn(() => Promise.resolve([])),
  fetchCandidateNoveltyHistory: vi.fn(() => Promise.resolve(null)),
  fetchProjectExports: vi.fn(() => Promise.resolve({ items: [], count: 0 })),
  fetchJobs: vi.fn(() => Promise.resolve([])),
  startMediaAnalysis: vi.fn(),
  submitBatchExport: vi.fn(),
}));

describe('P1.7 Media Relinking, Missing File Recovery & External Media Handling', () => {
  const mockMissingAsset: MediaAssetItem = {
    id: 'med_missing_01',
    project_id: 'proj_default',
    original_filename: 'External_Lecture_Session.mp4',
    storage_path: 'E:\\ExternalDrive\\Videos\\External_Lecture_Session.mp4',
    is_external: true,
    media_type: 'video',
    file_size_bytes: 104857600,
    mime_type: 'video/mp4',
    duration_seconds: 120.0,
    width: 1920,
    height: 1080,
    fps: 30.0,
    video_codec: 'h264',
    audio_codec: 'aac',
    availability_status: 'missing',
    integrity_status: 'missing',
    is_playable: false,
    created_at: '2026-11-16T10:00:00Z',
    updated_at: '2026-11-16T10:00:00Z',
    sha256: 'abc123sha256',
    resolution_label: '1080p',
    aspect_ratio: '16:9',
    container_format: 'mp4',
    analysis_status: 'none',
    proxy_reference_path: null,
    thumbnail_reference_path: null,
    proxy_status: 'none',
    metadata_status: 'extracted',
    metadata: {},
  };

  const mockPresentAsset: MediaAssetItem = {
    ...mockMissingAsset,
    id: 'med_present_02',
    original_filename: 'Local_Interview.mp4',
    storage_path: 'D:\\Videos\\Local_Interview.mp4',
    availability_status: 'present',
    integrity_status: 'verified',
    is_playable: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders MISSING FILE warning badge and Relink File button on missing videos in library', async () => {
    const listRes: MediaAssetListResponse = {
      items: [mockMissingAsset, mockPresentAsset],
      total: 2,
      page: 1,
      page_size: 12,
      total_pages: 1,
    };
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue(listRes);

    render(<ShortVideoGeneratorLibrary onOpenDashboard={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText('External_Lecture_Session.mp4').length).toBeGreaterThanOrEqual(1);
    });

    // Check for MISSING FILE badge on the missing asset
    const missingBadges = screen.getAllByText('FILE MISSING');
    expect(missingBadges.length).toBeGreaterThanOrEqual(1);

    // Verify Relink File action button is rendered for missing video
    const relinkButtons = screen.getAllByRole('button', { name: /Relink File/i });
    expect(relinkButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('triggers external drive reconnection check from library header', async () => {
    const listRes: MediaAssetListResponse = {
      items: [mockMissingAsset],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    };
    vi.mocked(apiClient.fetchAllMedia).mockResolvedValue(listRes);
    vi.mocked(apiClient.reconcileMissingMedia).mockResolvedValue({
      total_checked: 1,
      restored_count: 1,
      still_missing_count: 0,
      restored_assets: ['med_missing_01'],
      still_missing_assets: [],
    });

    render(<ShortVideoGeneratorLibrary onOpenDashboard={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText('External_Lecture_Session.mp4').length).toBeGreaterThanOrEqual(1);
    });

    const checkDrivesBtn = screen.getByRole('button', { name: /Check Drives/i });
    fireEvent.click(checkDrivesBtn);

    await waitFor(() => {
      expect(apiClient.reconcileMissingMedia).toHaveBeenCalledWith('default');
      expect(screen.getByText(/External media reconnected! Restored 1 media file/i)).toBeInTheDocument();
    });
  });

  it('opens MediaRelinkModal, inspects local candidate path and displays comparison preview', async () => {
    vi.mocked(apiClient.inspectRelinkCandidate).mockResolvedValue({
      match_status: 'compatible',
      warnings: ['Candidate duration differs by 5.20s (Original: 120.00s, Candidate: 125.20s)'],
      comparison: {
        original_duration: 120.0,
        candidate_duration: 125.2,
        original_resolution: '1920x1080',
        candidate_resolution: '1920x1080',
        sha256_match: false,
      },
    });

    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <MediaRelinkModal
        isOpen={true}
        onClose={handleClose}
        asset={mockMissingAsset}
        projectId="proj_default"
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByText(/Relink Media File with Integrity Check/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Asset: External_Lecture_Session\.mp4/i)).toBeInTheDocument();

    // Fill candidate path
    const pathInput = screen.getByPlaceholderText(/e\.g\. D:\\Videos\\interview_take_1\.mp4/i);
    fireEvent.change(pathInput, { target: { value: 'D:\\Videos\\Restored_Session.mp4' } });

    // Click Verify Candidate
    const verifyBtn = screen.getByRole('button', { name: /Verify Candidate/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(apiClient.inspectRelinkCandidate).toHaveBeenCalledWith(
        'proj_default',
        'med_missing_01',
        'D:\\Videos\\Restored_Session.mp4'
      );
      expect(screen.getByText('COMPATIBLE')).toBeInTheDocument();
      expect(screen.getByText(/Candidate duration differs by 5\.20s/i)).toBeInTheDocument();
    });
  });

  it('executes atomic relink with force flag and calls onSuccess callback', async () => {
    vi.mocked(apiClient.relinkMedia).mockResolvedValue({
      asset: {
        ...mockMissingAsset,
        availability_status: 'present',
        integrity_status: 'verified',
        storage_path: 'D:\\Videos\\Restored_Session.mp4',
        relinked_at: '2026-11-16T15:00:00Z',
      },
      match_status: 'compatible',
      warnings: [],
      comparison: {},
      relinked_at: '2026-11-16T15:00:00Z',
    });

    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <MediaRelinkModal
        isOpen={true}
        onClose={handleClose}
        asset={mockMissingAsset}
        projectId="proj_default"
        onSuccess={handleSuccess}
      />
    );

    const pathInput = screen.getByPlaceholderText(/e\.g\. D:\\Videos\\interview_take_1\.mp4/i);
    fireEvent.change(pathInput, { target: { value: 'D:\\Videos\\Restored_Session.mp4' } });

    const relinkSubmitBtn = screen.getByRole('button', { name: /Relink & Restore/i });
    fireEvent.click(relinkSubmitBtn);

    await waitFor(() => {
      expect(apiClient.relinkMedia).toHaveBeenCalledWith(
        'proj_default',
        'med_missing_01',
        'D:\\Videos\\Restored_Session.mp4',
        false
      );
      expect(screen.getByText(/Successfully relinked/i)).toBeInTheDocument();
    });
  });

  it('supports streaming replacement video file upload relinking in MediaRelinkModal', async () => {
    vi.mocked(apiClient.relinkMediaWithUpload).mockResolvedValue({
      asset: {
        ...mockMissingAsset,
        availability_status: 'present',
        storage_path: 'managed/replacement.mp4',
        relinked_at: '2026-11-16T15:00:00Z',
      },
      match_status: 'compatible',
      warnings: [],
      comparison: {},
      relinked_at: '2026-11-16T15:00:00Z',
    });

    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <MediaRelinkModal
        isOpen={true}
        onClose={handleClose}
        asset={mockMissingAsset}
        projectId="proj_default"
        onSuccess={handleSuccess}
      />
    );

    // Switch to Upload Replacement File tab
    const uploadTab = screen.getByRole('button', { name: /Upload Replacement File/i });
    fireEvent.click(uploadTab);

    expect(screen.getByText(/Choose replacement video file/i)).toBeInTheDocument();

    // Select file
    const file = new File([new Uint8Array(2048)], 'replacement.mp4', { type: 'video/mp4' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('replacement.mp4')).toBeInTheDocument();
    });

    const relinkSubmitBtn = screen.getByRole('button', { name: /Relink & Restore/i });
    fireEvent.click(relinkSubmitBtn);

    await waitFor(() => {
      expect(apiClient.relinkMediaWithUpload).toHaveBeenCalled();
    });
  });

  it('renders top warning banner and replaces video player when source media is missing in VideoEditDashboard', async () => {
    vi.mocked(apiClient.fetchMediaAsset).mockResolvedValue(mockMissingAsset);

    render(<VideoEditDashboard assetId="med_missing_01" projectId="proj_default" onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText(/Source video file missing/i).length).toBeGreaterThanOrEqual(1);
    });

    // Verify top warning banner with storage path
    expect(screen.getByText(/Physical file missing at:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/E:\\ExternalDrive\\Videos\\External_Lecture_Session\.mp4/i).length).toBeGreaterThanOrEqual(1);

    // Check that Home tab player replaced with Missing Source Video card
    expect(screen.getByText(/Relink the source video or reconnect the external drive/i)).toBeInTheDocument();

    // Check that clicking Relink opens modal
    const relinkSourceBtns = screen.getAllByRole('button', { name: /Relink Source/i });
    fireEvent.click(relinkSourceBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/Relink Media File with Integrity Check/i)).toBeInTheDocument();
    });
  });
});
