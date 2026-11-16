import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ShortVideoGeneratorLibrary } from '../features/videos/ShortVideoGeneratorLibrary';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem, MediaAssetListResponse } from '../types/projects';

vi.mock('../services/apiClient', () => ({
  fetchAllMedia: vi.fn(),
  deleteMediaAssetGlobal: vi.fn(),
  getGlobalThumbnailUrl: vi.fn((id) => `/api/v1/media/${id}/thumbnail`),
  getStreamMediaUrl: vi.fn((id) => `/api/v1/media/${id}/stream`),
  refreshMediaMetadata: vi.fn(),
  regenerateThumbnailGlobal: vi.fn(),
  isUploadRetryable: vi.fn(() => false),
  uploadMediaBatch: vi.fn(),
  uploadMediaFile: vi.fn(),
}));

describe('P1.6 Media Library & Asset Management Frontend Acceptance', () => {
  const mockMediaList: MediaAssetItem[] = [
    {
      id: 'med_test_01',
      project_id: 'proj_default',
      original_filename: '4K_Wildlife_Doc.mp4',
      storage_path: 'media/4K_Wildlife_Doc.mp4',
      is_external: false,
      media_type: 'video',
      file_size_bytes: 524288000,
      mime_type: 'video/mp4',
      duration_seconds: 125.4,
      width: 3840,
      height: 2160,
      fps: 60.0,
      video_codec: 'h264',
      audio_codec: 'aac',
      availability_status: 'present',
      proxy_reference_path: 'proxies/med_test_01.mp4',
      thumbnail_reference_path: 'thumbnails/med_test_01.jpg',
      proxy_status: 'ready',
      metadata_status: 'extracted',
      metadata: { title: '4K Wildlife Documentary' },
      created_at: '2026-11-16T10:00:00Z',
      updated_at: '2026-11-16T10:00:00Z',
      sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
      integrity_status: 'verified',
      upload_attempt_id: 'att_test_01',
      resolution_label: '4K',
      aspect_ratio: '16:9',
      container_format: 'mp4',
      audio_stream_count: 1,
      subtitle_stream_count: 1,
      audio_languages: ['eng'],
      subtitle_languages: ['eng'],
      analysis_status: 'completed',
    },
    {
      id: 'med_test_02',
      project_id: 'proj_default',
      original_filename: 'Interview_Raw.mkv',
      storage_path: 'media/Interview_Raw.mkv',
      is_external: false,
      media_type: 'video',
      file_size_bytes: 104857600,
      mime_type: 'video/x-matroska',
      duration_seconds: 45.2,
      width: 1920,
      height: 1080,
      fps: 24.0,
      video_codec: 'hevc',
      audio_codec: 'opus',
      availability_status: 'present',
      proxy_reference_path: null,
      thumbnail_reference_path: null,
      proxy_status: 'none',
      metadata_status: 'extracted',
      metadata: { title: 'Raw MKV Interview' },
      created_at: '2026-11-16T09:00:00Z',
      updated_at: '2026-11-16T09:00:00Z',
      sha256: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
      integrity_status: 'verified',
      upload_attempt_id: 'att_test_02',
      resolution_label: '1080p',
      aspect_ratio: '16:9',
      container_format: 'mkv',
      audio_stream_count: 2,
      subtitle_stream_count: 0,
      audio_languages: ['eng', 'spa'],
      analysis_status: 'none',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.fetchAllMedia as any).mockResolvedValue({
      items: mockMediaList,
      total: 2,
      page: 1,
      page_size: 12,
      total_pages: 1,
    } as MediaAssetListResponse);
  });

  it('renders central media library header, search bar, and filter controls', async () => {
    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    expect(screen.getByText('Short Video Generator')).toBeDefined();
    expect(screen.getByText(/Central video library/i)).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText('4K Wildlife Documentary')).toBeDefined();
      expect(screen.getByText('Raw MKV Interview')).toBeDefined();
    });

    // Check filter labels
    expect(screen.getByText('Resolution')).toBeDefined();
    expect(screen.getByText('Format')).toBeDefined();
    expect(screen.getByText('Video Codec')).toBeDefined();
    expect(screen.getByText('Analysis')).toBeDefined();
    expect(screen.getByText('Integrity')).toBeDefined();
    expect(screen.getByText('Sort Order')).toBeDefined();
  });

  it('displays accurate technical metadata badges on media cards', async () => {
    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    await waitFor(() => {
      expect(screen.getByText('4K Wildlife Documentary')).toBeDefined();
    });

    // 4K and 1080p badges
    expect(screen.getByText('4K')).toBeDefined();
    expect(screen.getByText('1080p')).toBeDefined();

    // Container badges
    expect(screen.getAllByText('MP4').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('MKV').length).toBeGreaterThanOrEqual(1);

    // Codec badges
    expect(screen.getByText('h264')).toBeDefined();
    expect(screen.getByText('hevc')).toBeDefined();

    // Integrity badges
    const verifiedBadges = screen.getAllByText('verified');
    expect(verifiedBadges.length).toBeGreaterThanOrEqual(1);

    // Analysis badge
    expect(screen.getByText('completed')).toBeDefined();
  });

  it('opens stream topology and inspection modal with native player and specs', async () => {
    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    await waitFor(() => {
      expect(screen.getByText('4K Wildlife Documentary')).toBeDefined();
    });

    // Click "Inspect Technical Specs" on first card
    const inspectBtns = screen.getAllByTitle('Inspect Technical Specs');
    fireEvent.click(inspectBtns[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText('Stream Topology & Technical Specifications')).toBeDefined();
      expect(screen.getByText('Integrity & Persistence Contract')).toBeDefined();
    });

    // Video player rendered with streaming URL
    const videoEl = document.querySelector('video');
    expect(videoEl).toBeDefined();
    expect(videoEl?.getAttribute('src')).toBe('/api/v1/media/med_test_01/stream');

    // SHA-256 displayed
    expect(screen.getByText('9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08')).toBeDefined();

    // Audio stream count and languages
    expect(screen.getByText(/Audio Languages:/i)).toBeDefined();
    expect(screen.getByText(/Subtitles:/i)).toBeDefined();
  });

  it('triggers metadata refresh and thumbnail regeneration from detail modal', async () => {
    const updatedAsset = {
      ...mockMediaList[0],
      duration_seconds: 130.0,
      width: 3840,
      height: 2160,
    };
    (apiClient.refreshMediaMetadata as any).mockResolvedValue(updatedAsset);
    (apiClient.regenerateThumbnailGlobal as any).mockResolvedValue(updatedAsset);

    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    await waitFor(() => {
      expect(screen.getByText('4K Wildlife Documentary')).toBeDefined();
    });

    // Open detail modal
    const inspectBtns = screen.getAllByTitle('Inspect Technical Specs');
    fireEvent.click(inspectBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Refresh Metadata')).toBeDefined();
      expect(screen.getByText('Regenerate Thumbnail')).toBeDefined();
    });

    // Click refresh metadata
    fireEvent.click(screen.getByText('Refresh Metadata'));
    await waitFor(() => {
      expect(apiClient.refreshMediaMetadata).toHaveBeenCalledWith('med_test_01');
    });

    // Click regenerate thumbnail
    fireEvent.click(screen.getByText('Regenerate Thumbnail'));
    await waitFor(() => {
      expect(apiClient.regenerateThumbnailGlobal).toHaveBeenCalledWith('med_test_01');
    });
  });

  it('handles safe deletion dialog and displays dependency conflict warning', async () => {
    (apiClient.deleteMediaAssetGlobal as any).mockRejectedValueOnce(
      new Error('Cannot delete asset: 2 export(s) depend on this video.')
    );

    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    await waitFor(() => {
      expect(screen.getByText('4K Wildlife Documentary')).toBeDefined();
    });

    // Click delete on first card
    const deleteBtns = screen.getAllByTitle('Delete Video');
    fireEvent.click(deleteBtns[0]);

    // Delete modal opens
    await waitFor(() => {
      expect(screen.getByText('Delete Media Asset')).toBeDefined();
      expect(screen.getByText('Confirm Delete')).toBeDefined();
    });

    // Click Confirm Delete
    fireEvent.click(screen.getByText('Confirm Delete'));

    // Should display dependency conflict and force delete button
    await waitFor(() => {
      expect(screen.getByText('Dependency Conflict')).toBeDefined();
      expect(screen.getByText(/2 export\(s\) depend on this video/i)).toBeDefined();
      expect(screen.getByText('Force Delete Video & Dependent Exports')).toBeDefined();
    });

    // Click Force Delete
    (apiClient.deleteMediaAssetGlobal as any).mockResolvedValueOnce(undefined);
    fireEvent.click(screen.getByText('Force Delete Video & Dependent Exports'));

    await waitFor(() => {
      expect(apiClient.deleteMediaAssetGlobal).toHaveBeenCalledWith('med_test_01', false, true);
    });
  });
});
