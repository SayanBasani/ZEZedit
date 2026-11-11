import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnalysisWorkspace } from '../features/analysis/AnalysisWorkspace';
import { MediaAssetItem } from '../types/projects';
import * as apiClient from '../services/apiClient';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    fetchAnalysisRuns: vi.fn().mockResolvedValue([
      {
        id: 'run-1',
        media_asset_id: 'med-1',
        project_id: 'proj-1',
        status: 'completed',
        profile: 'balanced',
        progress_pct: 100,
        current_stage: 'completed',
        created_at: '2026-11-11T12:00:00Z',
        updated_at: '2026-11-11T12:02:00Z',
      },
    ]),
    fetchAnalysisTranscript: vi.fn().mockResolvedValue({
      analysis_run_id: 'run-1',
      segments_count: 2,
      turns_count: 1,
      segments: [
        {
          id: 'seg-1',
          start_time: 0.0,
          end_time: 2.5,
          text: 'Welcome to ZezEdit video analysis',
          language: 'en',
          confidence: 0.95,
          words: [],
        },
      ],
      speech_turns: [
        {
          id: 'turn-1',
          start_time: 0.0,
          end_time: 2.5,
          speaker_label: 'Speaker 1',
          text: 'Welcome to ZezEdit video analysis',
          turn_type: 'statement',
        },
      ],
    }),
    fetchAnalysisScenes: vi.fn().mockResolvedValue([
      {
        id: 'scene-1',
        scene_index: 0,
        start_time: 0.0,
        end_time: 4.0,
        representative_timestamp: 2.0,
        change_score: 0.35,
      },
    ]),
    fetchAnalysisObservations: vi.fn().mockResolvedValue([
      {
        id: 'obs-1',
        timestamp: 2.0,
        category: 'scene_setting',
        description: 'Indoor studio with high-contrast lighting',
        provider_model: 'qwen3-vl:4b-instruct',
        confidence: 0.9,
      },
    ]),
    fetchAnalysisContext: vi.fn().mockResolvedValue({
      analysis_run_id: 'run-1',
      query_timestamp: 1.5,
      current_scene: {
        id: 'scene-1',
        scene_index: 0,
        start_time: 0.0,
        end_time: 4.0,
        representative_timestamp: 2.0,
        change_score: 0.35,
      },
      active_segment: null,
      active_speech_turn: null,
      nearby_segments: [],
      nearby_visual_observations: [],
      nearest_frame: null,
    }),
    startMediaAnalysis: vi.fn().mockResolvedValue({
      id: 'run-2',
      media_asset_id: 'med-1',
      project_id: 'proj-1',
      status: 'pending',
      profile: 'fast',
      progress_pct: 0,
      current_stage: 'queued',
      created_at: '2026-11-11T12:05:00Z',
      updated_at: '2026-11-11T12:05:00Z',
    }),
    cancelAnalysisRun: vi.fn().mockResolvedValue({
      message: 'Cancelled',
      run_id: 'run-1',
      status: 'cancelled',
    }),
    getProxyUrl: vi.fn().mockReturnValue('/api/v1/projects/proj-1/media/med-1/proxy'),
    getThumbnailUrl: vi.fn().mockReturnValue('/api/v1/projects/proj-1/media/med-1/thumbnail'),
  };
});

describe('AnalysisWorkspace Component', () => {
  const mockAsset: MediaAssetItem = {
    id: 'med-1',
    project_id: 'proj-1',
    original_filename: 'interview_clip.mp4',
    storage_path: 'D:\\Videos\\interview_clip.mp4',
    is_external: true,
    media_type: 'video',
    file_size_bytes: 52428800,
    mime_type: 'video/mp4',
    duration_seconds: 64.5,
    width: 1920,
    height: 1080,
    fps: 29.97,
    video_codec: 'h264',
    audio_codec: 'aac',
    availability_status: 'present',
    metadata_status: 'complete',
    proxy_reference_path: null,
    thumbnail_reference_path: 'thumbnails/med-1.jpg',
    proxy_status: 'ready',
    metadata: {},
    created_at: '2026-11-11T10:00:00Z',
    updated_at: '2026-11-11T10:00:00Z',
  };

  it('renders workspace with video metadata and back button', async () => {
    const handleBack = vi.fn();
    render(<AnalysisWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={handleBack} />);

    await waitFor(() => {
      expect(screen.getByText('interview_clip.mp4')).toBeInTheDocument();
      expect(screen.getByText(/1920×1080/)).toBeInTheDocument();
    });

    const backBtn = screen.getByLabelText('Back to Media Library');
    fireEvent.click(backBtn);
    expect(handleBack).toHaveBeenCalledTimes(1);
  });

  it('renders transcript segments and speech turns', async () => {
    render(<AnalysisWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Welcome to ZezEdit video analysis')).toBeInTheDocument();
      expect(screen.getByText('Speaker 1')).toBeInTheDocument();
    });
  });

  it('switches between multimodal tabs: scenes, visuals, and context', async () => {
    render(<AnalysisWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/Scenes \(1\)/)).toBeInTheDocument();
    });

    // Click Scenes Tab
    fireEvent.click(screen.getByText(/Scenes \(1\)/));
    await waitFor(() => {
      expect(screen.getAllByText('Scene 1').length).toBeGreaterThan(0);
    });

    // Click Visuals Tab
    fireEvent.click(screen.getByText(/Visuals \(1\)/));
    await waitFor(() => {
      expect(screen.getByText('Indoor studio with high-contrast lighting')).toBeInTheDocument();
    });

    // Click Context Tab
    fireEvent.click(screen.getByText('Context'));
    await waitFor(() => {
      expect(screen.getByText('Playhead Timestamp')).toBeInTheDocument();
    });
  });
});
