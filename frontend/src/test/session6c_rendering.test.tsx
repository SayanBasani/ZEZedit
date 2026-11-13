import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VideoEditDashboard } from '../features/videos/VideoEditDashboard';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem } from '../types/projects';

const mockVideoAsset: MediaAssetItem = {
  id: 'vid_123',
  project_id: 'default',
  original_filename: 'interview_clip.mp4',
  storage_path: 'D:/ZezEdit/storage/media/interview_clip.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 15_000_000,
  mime_type: 'video/mp4',
  duration_seconds: 120.0,
  width: 1920,
  height: 1080,
  fps: 30.0,
  video_codec: 'h264',
  audio_codec: 'aac',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'complete',
  metadata: { title: 'Interview Clip' },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockCandidates = [
  {
    id: 'cand_1',
    title: 'Exciting Hook',
    start_time: 10.0,
    end_time: 25.0,
    duration: 15.0,
    quality_score: 92.5,
    creative_direction: 'viral_hook',
    media_asset_id: 'vid_123',
    suggested_title: 'Exciting Hook',
    review_status: 'approved',
  },
  {
    id: 'cand_2',
    title: 'Action Climax',
    start_time: 45.0,
    end_time: 60.0,
    duration: 15.0,
    quality_score: 88.0,
    creative_direction: 'dramatic',
    media_asset_id: 'vid_123',
    suggested_title: 'Action Climax',
    review_status: 'approved',
  },
];

const mockExports = [
  {
    id: 'exp_001',
    project_id: 'default',
    candidate_id: 'cand_1',
    title: 'Hook Render',
    output_filename: 'hook_render.mp4',
    status: 'completed',
    validation_status: 'valid',
    target_aspect_ratio: '9:16',
    target_width: 1080,
    target_height: 1920,
    duration_seconds: 15.0,
    file_size_bytes: 4_200_000,
    video_codec: 'h264',
    audio_codec: 'aac',
    created_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
  },
];

describe('Session 6C: Generated Videos and Batch Export UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(apiClient, 'fetchMediaAsset').mockResolvedValue(mockVideoAsset);
    vi.spyOn(apiClient, 'fetchJobs').mockResolvedValue({ items: [], total: 0 } as any);
    vi.spyOn(apiClient, 'fetchAnalysisRuns').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchMediaHighlights').mockResolvedValue(mockCandidates as any);
    vi.spyOn(apiClient, 'fetchCandidateGenerationRuns').mockResolvedValue([]);
    vi.spyOn(apiClient, 'fetchCandidateNoveltyHistory').mockResolvedValue({ novelty_records: [], total_indexed: 0 } as any);
    vi.spyOn(apiClient, 'fetchProjectExports').mockResolvedValue({ items: mockExports, count: 1 } as any);
    vi.spyOn(apiClient, 'submitBatchExport').mockResolvedValue({
      total_requested: 2,
      total_submitted: 2,
      items: [],
      skipped_candidates: [],
    } as any);
  });

  it('renders Candidate tab with selection checkboxes and batch action bar', async () => {
    render(
      <VideoEditDashboard
        assetId={mockVideoAsset.id}
        projectId="default"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Interview Clip')).toBeDefined();
    });

    // Switch to Generated Shorts tab
    const shortsTab = screen.getByRole('button', { name: /Generated Shorts/i });
    fireEvent.click(shortsTab);

    // Verify candidates load
    await waitFor(() => {
      expect(screen.getByText('Exciting Hook')).toBeDefined();
      expect(screen.getByText('Action Climax')).toBeDefined();
    });

    // Checkboxes should exist
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThanOrEqual(2);

    // Select candidate 1
    fireEvent.click(checkboxes[0]);

    // Sticky batch bar appears
    expect(screen.getByText(/Render Selected/i)).toBeDefined();
  });

  it('renders Generated Videos tab with playable video cards and download link', async () => {
    render(
      <VideoEditDashboard
        assetId={mockVideoAsset.id}
        projectId="default"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Interview Clip')).toBeDefined();
    });

    // Find Generated Videos tab
    const genTab = screen.getByRole('button', { name: /Generated Videos/i });
    expect(genTab).toBeDefined();

    fireEvent.click(genTab);

    // Should display the rendered video card
    await waitFor(() => {
      expect(screen.getByText('Hook Render')).toBeDefined();
      expect(screen.getByText(/1080x1920/i)).toBeDefined();
      expect(screen.getByText(/valid/i)).toBeDefined();
    });

    // Verify Play button is present
    const playBtn = screen.getByRole('button', { name: /^Play$/i });
    expect(playBtn).toBeDefined();

    // Verify Download link is present with proper href
    const downloadLink = screen.getByRole('link', { name: /Download/i });
    expect(downloadLink).toBeDefined();
    expect(downloadLink.getAttribute('href')).toContain('/exports/exp_001/download');
  });

  it('opens in-browser HTML5 player when play button is clicked', async () => {
    render(
      <VideoEditDashboard
        assetId={mockVideoAsset.id}
        projectId="default"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Interview Clip')).toBeDefined();
    });

    const genTab = screen.getByRole('button', { name: /Generated Videos/i });
    fireEvent.click(genTab);

    await waitFor(() => {
      expect(screen.getByText('Hook Render')).toBeDefined();
    });

    const playBtn = screen.getByRole('button', { name: /^Play$/i });
    fireEvent.click(playBtn);

    // Player modal should appear with Close and Download buttons
    expect(screen.getByRole('button', { name: /Close Player/i })).toBeDefined();
  });
});
