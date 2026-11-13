import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VideoEditDashboard } from '../features/videos/VideoEditDashboard';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem } from '../types/projects';

vi.mock('../services/apiClient');

const mockVideoA: MediaAssetItem = {
  id: 'med_video_aaa_111',
  project_id: 'default',
  original_filename: 'Video_Alpha_Interview.mp4',
  storage_path: 'media/video_aaa.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 45000000,
  duration_seconds: 120.0,
  width: 1920,
  height: 1080,
  fps: 30.0,
  video_codec: 'h264',
  audio_codec: 'aac',
  mime_type: 'video/mp4',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'ready',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  metadata: { title: 'Alpha Documentary Interview' },
};

const mockVideoB: MediaAssetItem = {
  id: 'med_video_bbb_222',
  project_id: 'default',
  original_filename: 'Video_Beta_ActionScene.mp4',
  storage_path: 'media/video_bbb.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 98000000,
  duration_seconds: 360.0,
  width: 3840,
  height: 2160,
  fps: 60.0,
  video_codec: 'hevc',
  audio_codec: 'aac',
  mime_type: 'video/mp4',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'ready',
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  metadata: { title: 'Beta Action Stunt Sequence' },
};

describe('Video Dashboard Isolation Verification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchJobs).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(apiClient.getStreamMediaUrl).mockImplementation((id) => `http://stream/${id}`);
    vi.mocked(apiClient.getGlobalThumbnailUrl).mockImplementation((id) => `http://thumb/${id}`);
    vi.mocked(apiClient.fetchCandidateGenerationRuns).mockResolvedValue([]);
    vi.mocked(apiClient.fetchCandidateNoveltyHistory).mockResolvedValue(null as any);
    vi.mocked(apiClient.fetchAnalysisScenes).mockResolvedValue([]);
    vi.mocked(apiClient.fetchAnalysisTranscript).mockResolvedValue(null as any);
    vi.mocked(apiClient.fetchAnalysisCacheInfo).mockResolvedValue(null as any);
    if (apiClient.fetchProjectExports) {
      vi.mocked(apiClient.fetchProjectExports).mockResolvedValue({ items: [], count: 0 } as any);
    }
  });

  it('renders strictly isolated metadata and intelligence data for Video A', async () => {
    vi.mocked(apiClient.fetchMediaAsset).mockResolvedValue(mockVideoA);
    vi.mocked(apiClient.fetchAnalysisRuns).mockResolvedValue([
      {
        id: 'run_aaa',
        project_id: 'default',
        media_asset_id: 'med_video_aaa_111',
        status: 'completed',
        profile: 'balanced',
        current_stage: 'completed',
        progress_pct: 100,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(apiClient.fetchMediaHighlights).mockResolvedValue([
      {
        id: 'cand_aaa_1',
        project_id: 'default',
        media_asset_id: 'med_video_aaa_111',
        analysis_run_id: 'run_aaa',
        title: 'Alpha Insight Moment',
        start_time: 10.0,
        end_time: 35.0,
        duration: 25.0,
        quality_score: 0.94,
        category: 'Viral Hook',
      } as any,
    ]);

    render(<VideoEditDashboard assetId="med_video_aaa_111" onBack={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Documentary Interview')).toBeInTheDocument();
      expect(screen.getByText('1920x1080')).toBeInTheDocument();
      expect(screen.getByText('1 Shorts Discovered')).toBeInTheDocument();
    });

    // Ensure Video B details do NOT leak in
    expect(screen.queryByText('Beta Action Stunt Sequence')).not.toBeInTheDocument();
    expect(screen.queryByText('3840x2160')).not.toBeInTheDocument();
  });

  it('renders strictly isolated metadata and intelligence data for Video B', async () => {
    vi.mocked(apiClient.fetchMediaAsset).mockResolvedValue(mockVideoB);
    vi.mocked(apiClient.fetchAnalysisRuns).mockResolvedValue([
      {
        id: 'run_bbb',
        project_id: 'default',
        media_asset_id: 'med_video_bbb_222',
        status: 'completed',
        profile: 'balanced',
        current_stage: 'completed',
        progress_pct: 100,
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      },
    ]);
    vi.mocked(apiClient.fetchMediaHighlights).mockResolvedValue([
      {
        id: 'cand_bbb_1',
        project_id: 'default',
        media_asset_id: 'med_video_bbb_222',
        analysis_run_id: 'run_bbb',
        title: 'Beta Car Chase Climax',
        start_time: 45.0,
        end_time: 75.0,
        duration: 30.0,
        quality_score: 0.98,
        category: 'Action Spectacle',
      } as any,
    ]);

    render(<VideoEditDashboard assetId="med_video_bbb_222" onBack={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Beta Action Stunt Sequence')).toBeInTheDocument();
      expect(screen.getByText('3840x2160')).toBeInTheDocument();
      expect(screen.getByText('1 Shorts Discovered')).toBeInTheDocument();
    });

    // Ensure Video A details do NOT leak into Video B dashboard
    expect(screen.queryByText('Alpha Documentary Interview')).not.toBeInTheDocument();
    expect(screen.queryByText('1920x1080')).not.toBeInTheDocument();
  });
});
