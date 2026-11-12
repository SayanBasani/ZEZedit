import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SingleVideoStudio } from '../features/studio/SingleVideoStudio';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem, ProjectItem } from '../types/projects';
import { AnalysisRunItem } from '../types/analysis';
import { CandidateItem } from '../types/highlights';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    fetchMediaAsset: vi.fn(),
    fetchProject: vi.fn(),
    fetchAnalysisRuns: vi.fn(),
    fetchMediaHighlights: vi.fn(),
    fetchProjectExports: vi.fn(),
    fetchJobs: vi.fn(),
    fetchAnalysisTranscript: vi.fn(),
    fetchAnalysisScenes: vi.fn(),
    startMediaAnalysis: vi.fn(),
    discoverHighlights: vi.fn(),
    submitExportRender: vi.fn(),
    getProxyUrl: vi.fn().mockReturnValue('/api/v1/projects/p1/media/m1/proxy'),
    getSceneThumbnailUrl: vi.fn().mockReturnValue('/api/v1/projects/p1/media/m1/scenes/s1/thumb'),
    getThumbnailUrl: vi.fn().mockReturnValue('/api/v1/projects/p1/media/m1/thumbnail'),
  };
});

describe('SingleVideoStudio Component (Session 2)', () => {
  const mockAsset: MediaAssetItem = {
    id: 'med_test_1',
    project_id: 'proj_test_1',
    original_filename: 'movie_action_sequence.mp4',
    storage_path: 'D:\\Videos\\movie_action_sequence.mp4',
    is_external: true,
    media_type: 'video',
    file_size_bytes: 104857600, // 100 MB
    mime_type: 'video/mp4',
    duration_seconds: 300.5,
    width: 1920,
    height: 1080,
    fps: 25.0,
    video_codec: 'h264',
    audio_codec: 'aac',
    availability_status: 'present',
    proxy_reference_path: 'D:\\ZezEdit\\storage\\proxies\\med_test_1_proxy.mp4',
    thumbnail_reference_path: 'D:\\ZezEdit\\storage\\thumbnails\\med_test_1.jpg',
    proxy_status: 'ready',
    metadata_status: 'extracted',
    metadata: {},
    created_at: '2026-11-12T10:00:00Z',
    updated_at: '2026-11-12T10:00:00Z',
  };

  const mockProject: ProjectItem = {
    id: 'proj_test_1',
    name: 'Feature Film Alpha',
    description: 'Test project',
    status: 'active',
    storage_subdir: 'proj_test_1',
    project_config: {},
    created_at: '2026-11-12T09:00:00Z',
    updated_at: '2026-11-12T09:00:00Z',
    last_opened_at: null,
    archived_at: null,
  };

  const mockAnalysisRuns: AnalysisRunItem[] = [
    {
      id: 'run_101',
      media_asset_id: 'med_test_1',
      project_id: 'proj_test_1',
      status: 'completed',
      profile: 'balanced',
      progress_pct: 100.0,
      current_stage: 'completed',
      error_message: undefined,
      created_at: '2026-11-12T10:05:00Z',
      updated_at: '2026-11-12T10:07:00Z',
    },
  ];

  const mockCandidates: CandidateItem[] = [
    {
      id: 'cand_1',
      project_id: 'proj_test_1',
      media_asset_id: 'med_test_1',
      analysis_run_id: 'run_101',
      start_time: 45.0,
      end_time: 82.5,
      duration: 37.5,
      suggested_start_time: 45.0,
      suggested_end_time: 82.5,
      is_user_modified: false,
      title: 'Dramatic Bridge Confrontation',
      suggested_title: 'Dramatic Bridge Confrontation',
      description: 'High stakes argument between leads before the jump.',
      category: 'Dramatic',
      secondary_categories: ['Action'],
      quality_score: 0.94,
      score_breakdown: {
        semantic_interest: 0.95,
        narrative_completeness: 0.92,
        conversation_structure: 0.88,
        visual_interest: 0.96,
        audio_evidence: 0.91,
        opening_clarity: 0.95,
        ending_completeness: 0.93,
        duration_suitability: 0.94,
        context_dependency_penalty: 0.05,
        total_score: 0.94,
      },
      gate_results: {
        overall_status: 'recommended',
        minimum_score_pass: true,
        duration_pass: true,
        transcript_pass: true,
        narrative_pass: true,
        visual_pass: true,
        context_pass: true,
        failure_reasons: [],
      },
      warnings: [],
      missing_evidence: [],
      review_status: 'recommended',
      rejection_reason: null,
      transcript_references: ['seg_1', 'seg_2'],
      scene_references: ['sc_3'],
      visual_evidence: [],
      audio_evidence: [],
      ai_explanation: { hook: 'Strong confrontation opening' },
      alternative_of_candidate_id: null,
      overlap_group_id: null,
      scoring_version: '2.0.0-m6',
      queued_for_render: false,
      created_at: '2026-11-12T10:08:00Z',
      updated_at: '2026-11-12T10:08:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchMediaAsset).mockResolvedValue(mockAsset);
    vi.mocked(apiClient.fetchProject).mockResolvedValue(mockProject);
    vi.mocked(apiClient.fetchAnalysisRuns).mockResolvedValue(mockAnalysisRuns);
    vi.mocked(apiClient.fetchMediaHighlights).mockResolvedValue(mockCandidates);
    vi.mocked(apiClient.fetchProjectExports).mockResolvedValue({ items: [], count: 0 });
    vi.mocked(apiClient.fetchJobs).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(apiClient.fetchAnalysisTranscript).mockResolvedValue({
      analysis_run_id: 'run_101',
      segments_count: 1,
      turns_count: 0,
      speech_turns: [],
      segments: [
        {
          id: 'seg_1',
          start_time: 45.0,
          end_time: 50.0,
          text: 'We cannot turn back now!',
          confidence: 0.98,
        },
      ],
    });
    vi.mocked(apiClient.fetchAnalysisScenes).mockResolvedValue([
      {
        id: 'sc_1',
        scene_index: 0,
        start_time: 44.5,
        end_time: 83.0,
        representative_timestamp: 50.0,
        change_score: 0.8,
        thumbnail_path: 'sc_1_thumb.jpg',
      },
    ]);
  });

  it('loads media metadata, project name, and discovered candidates', async () => {
    render(
      <SingleVideoStudio
        assetId="med_test_1"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('movie_action_sequence.mp4')).toBeInTheDocument();
      expect(screen.getByText('Feature Film Alpha')).toBeInTheDocument();
      expect(screen.getByText('1920x1080')).toBeInTheDocument();
      expect(screen.getByText('25fps')).toBeInTheDocument();
      expect(screen.getByText('Present')).toBeInTheDocument();
    });

    // Check candidate card
    expect(screen.getByText('Dramatic Bridge Confrontation')).toBeInTheDocument();
    expect(screen.getByText('Dramatic')).toBeInTheDocument();
    expect(screen.getByText(/Attractiveness: 94\/100/)).toBeInTheDocument();
  });

  it('displays error state when asset does not exist and handles return', async () => {
    vi.mocked(apiClient.fetchMediaAsset).mockRejectedValueOnce(
      new Error("Media asset 'invalid_id' not found.")
    );

    const handleBack = vi.fn();
    render(
      <SingleVideoStudio
        assetId="invalid_id"
        onBack={handleBack}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Unable to Open Video Studio')).toBeInTheDocument();
      expect(screen.getByText(/Media asset 'invalid_id' not found/)).toBeInTheDocument();
    });

    const returnBtn = screen.getByRole('button', { name: /return to media library/i });
    fireEvent.click(returnBtn);
    expect(handleBack).toHaveBeenCalledTimes(1);
  });

  it('updates upfront configuration: aspect ratio, clip count, and creative direction', async () => {
    render(
      <SingleVideoStudio
        assetId="med_test_1"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('movie_action_sequence.mp4')).toBeInTheDocument();
    });

    // Select 1:1 Square
    const squareBtn = screen.getByRole('button', { name: /1:1 square/i });
    fireEvent.click(squareBtn);
    expect(screen.getByText(/framing: 1:1/i)).toBeInTheDocument();

    // Select 20 clips
    const twentyBtn = screen.getByRole('button', { name: /20 clips/i });
    fireEvent.click(twentyBtn);

    // Change creative direction
    const vibeSelect = screen.getByRole('combobox');
    fireEvent.change(vibeSelect, { target: { value: 'dramatic' } });
    expect(vibeSelect).toHaveValue('dramatic');
  });

  it('dispatches highlight discovery when analysis is already completed', async () => {
    vi.mocked(apiClient.discoverHighlights).mockResolvedValueOnce(mockCandidates);

    render(
      <SingleVideoStudio
        assetId="med_test_1"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('movie_action_sequence.mp4')).toBeInTheDocument();
    });

    const genBtn = screen.getByRole('button', { name: /generate additional shorts/i });
    fireEvent.click(genBtn);

    await waitFor(() => {
      expect(apiClient.discoverHighlights).toHaveBeenCalledWith(
        'proj_test_1',
        'med_test_1',
        expect.objectContaining({
          analysis_run_id: 'run_101',
          target_clip_count: 10,
          min_duration: 12,
          max_duration: 60,
          run_synchronously: true,
        })
      );
    });
  });

  it('handles single clip export trigger', async () => {
    vi.mocked(apiClient.submitExportRender).mockResolvedValueOnce({
      export_id: 'exp_1',
      job_id: 'job_1',
      status: 'queued',
      output_filename: 'out.mp4',
    });

    render(
      <SingleVideoStudio
        assetId="med_test_1"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Dramatic Bridge Confrontation')).toBeInTheDocument();
    });

    const exportBtn = screen.getByRole('button', { name: /export mp4/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(apiClient.submitExportRender).toHaveBeenCalledWith(
        'proj_test_1',
        expect.objectContaining({
          candidate_id: 'cand_1',
          preset_id: 'shorts_reels_9_16',
          title: 'Dramatic Bridge Confrontation',
        })
      );
    });
  });

  it('toggles collapsible transcript and scene drawers', async () => {
    render(
      <SingleVideoStudio
        assetId="med_test_1"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('movie_action_sequence.mp4')).toBeInTheDocument();
    });

    // Open Transcript Drawer
    const transcriptBtn = screen.getByRole('button', { name: /full transcript/i });
    fireEvent.click(transcriptBtn);

    await waitFor(() => {
      expect(screen.getByText('We cannot turn back now!')).toBeInTheDocument();
    });

    // Open Scenes Drawer
    const scenesBtn = screen.getByRole('button', { name: /detected scenes/i });
    fireEvent.click(scenesBtn);

    await waitFor(() => {
      expect(screen.getByText(/visual scene cuts detected by ffmpeg/i)).toBeInTheDocument();
    });
  });
});
