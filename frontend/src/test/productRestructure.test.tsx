import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShortVideoGeneratorLibrary } from '../features/videos/ShortVideoGeneratorLibrary';
import { VideoEditDashboard } from '../features/videos/VideoEditDashboard';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem } from '../types/projects';

const mockVideoAsset: MediaAssetItem = {
  id: 'med_test_123',
  project_id: 'default',
  original_filename: 'Action_Movie_Scene.mp4',
  storage_path: 'D:/ZezEdit/storage/media/Action_Movie_Scene.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 104857600,
  mime_type: 'video/mp4',
  duration_seconds: 180.5,
  width: 1920,
  height: 1080,
  fps: 30,
  video_codec: 'h264',
  audio_codec: 'aac',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'complete',
  metadata: { title: 'Action Movie Scene' },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('Product Restructure — Video-Centric Workflows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(apiClient, 'fetchAllMedia').mockResolvedValue({
      items: [mockVideoAsset],
      total: 1,
    });
    vi.spyOn(apiClient, 'fetchMediaAsset').mockResolvedValue(mockVideoAsset);
    vi.spyOn(apiClient, 'fetchJobs').mockResolvedValue({ items: [], total: 0 } as any);
    vi.spyOn(apiClient, 'fetchAnalysisRuns').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchMediaHighlights').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchCandidateGenerationRuns').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchCandidateNoveltyHistory').mockResolvedValue({ novelty_records: [], total_indexed: 0 } as any);
  });

  it('renders ShortVideoGeneratorLibrary with direct upload area and video card', async () => {
    const handleOpen = vi.fn();
    render(<ShortVideoGeneratorLibrary onOpenDashboard={handleOpen} />);

    expect(screen.getByText('Short Video Generator')).toBeDefined();
    expect(screen.getByText(/Central video library/i)).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText('Action Movie Scene')).toBeDefined();
    });

    const openBtn = screen.getByRole('button', { name: /Open Video Dashboard/i });
    expect(openBtn).toBeDefined();
    fireEvent.click(openBtn);
    expect(handleOpen).toHaveBeenCalledWith(mockVideoAsset);
  });

  it('renders VideoEditDashboard with 8 horizontal tabs and technical specs', async () => {
    const handleBack = vi.fn();
    render(
      <VideoEditDashboard
        assetId={mockVideoAsset.id}
        projectId="default"
        onBack={handleBack}
      />
    );

    // Header title
    await waitFor(() => {
      expect(screen.getByText('Action Movie Scene')).toBeDefined();
    });

    // Verify 8 tabs are rendered
    expect(screen.getByRole('button', { name: 'Home' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Short Video Generator' })).toBeDefined();
    expect(screen.getByRole('button', { name: /Generated Shorts/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Generated Scripts/i })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Analyzed Frames' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Voice & Transcript Analysis' })).toBeDefined();
    expect(screen.getByRole('button', { name: /Scene Analysis/i })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Video Analysis Details' })).toBeDefined();

    // In Home tab: technical specs table
    expect(screen.getByText('Technical Video Specifications')).toBeDefined();
    expect(screen.getByText('1920 x 1080')).toBeDefined();

    // Switch to Short Video Generator tab
    const genTabBtn = screen.getByRole('button', { name: 'Short Video Generator' });
    fireEvent.click(genTabBtn);

    expect(screen.getByText(/1. How Many Short Video Clips Do You Want\?/i)).toBeDefined();
    expect(screen.getByText(/2. Creative Direction & Context Focus/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /Generate Shorts Now/i })).toBeDefined();
  });
});
