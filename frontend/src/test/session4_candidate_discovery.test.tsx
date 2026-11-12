import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SingleVideoStudio } from '../features/studio/SingleVideoStudio';
import * as apiClient from '../services/apiClient';
import { CandidateGenerationRunItem, CandidateItem, NoveltyHistoryResponse } from '../types/highlights';
import { MediaAssetItem, ProjectItem } from '../types/projects';
import { AnalysisRunItem } from '../types/analysis';

vi.mock('../services/apiClient', () => ({
  fetchMediaAsset: vi.fn(),
  fetchProject: vi.fn(),
  fetchAnalysisRuns: vi.fn(),
  fetchMediaHighlights: vi.fn(),
  fetchProjectExports: vi.fn(),
  fetchJobs: vi.fn(),
  fetchAnalysisTranscript: vi.fn(),
  fetchAnalysisScenes: vi.fn(),
  fetchAnalysisCacheInfo: vi.fn(),
  fetchAnalysisTelemetry: vi.fn(),
  discoverHighlights: vi.fn(),
  generateMoreHighlights: vi.fn(),
  fetchCandidateGenerationRuns: vi.fn(),
  fetchCandidateNoveltyHistory: vi.fn(),
  startMediaAnalysis: vi.fn(),
  cancelAnalysisRun: vi.fn(),
  retryAnalysisRun: vi.fn(),
  submitExportRender: vi.fn(),
  getProxyUrl: vi.fn(() => 'http://localhost/video.mp4'),
  getSceneThumbnailUrl: vi.fn(() => 'http://localhost/thumb.jpg'),
}));

const mockAsset: MediaAssetItem = {
  id: 'med_session4_test',
  project_id: 'proj_session4_test',
  original_filename: 'cinematic_feature_trailer.mp4',
  storage_path: 'D:/media/cinematic_feature_trailer.mp4',
  is_external: true,
  media_type: 'video',
  file_size_bytes: 85 * 1024 * 1024,
  mime_type: 'video/mp4',
  duration_seconds: 300,
  width: 1920,
  height: 1080,
  fps: 30,
  video_codec: 'h264',
  audio_codec: 'aac',
  availability_status: 'present',
  proxy_reference_path: 'D:/media/proxy.mp4',
  thumbnail_reference_path: 'D:/media/thumb.jpg',
  proxy_status: 'ready',
  metadata_status: 'extracted',
  metadata: {},
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

const mockProject: ProjectItem = {
  id: 'proj_session4_test',
  name: 'Feature Film Production',
  description: 'Test session 4 project',
  status: 'active',
  storage_subdir: 'proj_session4_test',
  project_config: {},
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
  last_opened_at: null,
  archived_at: null,
};

const mockAnalysisRun: AnalysisRunItem = {
  id: 'run_session4_1',
  project_id: 'proj_session4_test',
  media_asset_id: 'med_session4_test',
  profile: 'balanced',
  status: 'completed',
  progress_pct: 100,
  current_stage: 'completed',
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

const mockCandidates: CandidateItem[] = [
  {
    id: 'cand_novelty_1',
    project_id: 'proj_session4_test',
    media_asset_id: 'med_session4_test',
    analysis_run_id: 'run_session4_1',
    start_time: 14.5,
    end_time: 42.0,
    duration: 27.5,
    suggested_start_time: 14.5,
    suggested_end_time: 42.0,
    is_user_modified: false,
    title: 'High Octane Cyber Rooftop Chase',
    suggested_title: 'Rooftop Chase',
    description: 'Intense parkour chase scene with high audio dynamic peaks.',
    category: 'Action',
    secondary_categories: ['Suspense'],
    quality_score: 0.91,
    creative_direction: 'action_motion',
    natural_boundary_confidence: 0.95,
    generation_run_id: 'genrun_001',
    score_breakdown: {
      semantic_interest: 0.88,
      narrative_completeness: 0.90,
      conversation_structure: 0.85,
      visual_interest: 0.92,
      audio_evidence: 0.89,
      opening_clarity: 0.90,
      ending_completeness: 0.92,
      duration_suitability: 0.95,
      context_dependency_penalty: 0.05,
      total_score: 0.91,
      hook_strength: 92,
      dialogue_interest: 78,
      emotional_signal: 80,
      action_motion: 96,
      attractiveness_estimate: 91,
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
    transcript_references: ['seg_1', 'seg_2'],
    scene_references: ['scene_1'],
    visual_evidence: [],
    audio_evidence: [],
    ai_explanation: {
      why_it_works: 'Dynamic camera sweeps snap cleanly to dialogue completion.',
      hook: 'Look behind you before you jump!',
    },
    scoring_version: '2.0.0-multimodal',
    queued_for_render: false,
    created_at: '2026-11-12T01:00:00Z',
    updated_at: '2026-11-12T01:00:00Z',
  },
];

const mockGenRuns: CandidateGenerationRunItem[] = [
  {
    id: 'genrun_001',
    project_id: 'proj_session4_test',
    media_asset_id: 'med_session4_test',
    analysis_run_id: 'run_session4_1',
    creative_direction: 'action_motion',
    aspect_ratio: '9:16',
    requested_count: 5,
    min_duration: 12,
    max_duration: 60,
    status: 'completed',
    candidates_discovered: 8,
    candidates_selected: 1,
    candidates_rejected: 0,
    novelty_exclusions: 2,
    warnings: [],
    created_at: '2026-11-12T01:00:00Z',
  },
];

const mockNoveltyHistory: NoveltyHistoryResponse = {
  media_asset_id: 'med_session4_test',
  total_clips_generated: 1,
  total_duration_covered: 27.5,
  history: [
    {
      id: 'nov_1',
      candidate_id: 'cand_novelty_1',
      start_time: 14.5,
      end_time: 42.0,
      duration: 27.5,
      creative_direction: 'action_motion',
      aspect_ratio: '9:16',
      score: 0.91,
      title: 'High Octane Cyber Rooftop Chase',
      created_at: '2026-11-12T01:00:00Z',
    },
  ],
};

describe('Session 4: Intelligent Candidate Discovery, Multimodal Scoring & Novelty', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchMediaAsset).mockResolvedValue(mockAsset);
    vi.mocked(apiClient.fetchProject).mockResolvedValue(mockProject);
    vi.mocked(apiClient.fetchAnalysisRuns).mockResolvedValue([mockAnalysisRun]);
    vi.mocked(apiClient.fetchMediaHighlights).mockResolvedValue(mockCandidates);
    vi.mocked(apiClient.fetchProjectExports).mockResolvedValue({ items: [], count: 0 });
    vi.mocked(apiClient.fetchJobs).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(apiClient.fetchAnalysisTranscript).mockResolvedValue({
      analysis_run_id: 'run_session4_1',
      segments_count: 0,
      turns_count: 0,
      segments: [],
      speech_turns: [],
    });
    vi.mocked(apiClient.fetchAnalysisScenes).mockResolvedValue([]);
    vi.mocked(apiClient.fetchAnalysisCacheInfo).mockResolvedValue({
      run_id: 'run_session4_1',
      media_asset_id: 'med_session4_test',
      status: 'completed',
      current_signature: 'sig_123',
      is_cache_valid: true,
      records: {},
    });
    vi.mocked(apiClient.fetchCandidateGenerationRuns).mockResolvedValue(mockGenRuns);
    vi.mocked(apiClient.fetchCandidateNoveltyHistory).mockResolvedValue(mockNoveltyHistory);
  });

  it('renders multimodal scoring, natural boundary badge, and novelty filter status', async () => {
    render(
      <SingleVideoStudio
        assetId="med_session4_test"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Octane Cyber Rooftop Chase')).toBeInTheDocument();
    });

    // Check Natural Cut badge
    expect(screen.getByText(/Natural Cut 95%/i)).toBeInTheDocument();

    // Check Creative Direction badge
    expect(screen.getByText('Action & Motion')).toBeInTheDocument();

    // Check Attractiveness estimate
    expect(screen.getByText(/Attractiveness: 91\/100/i)).toBeInTheDocument();

    // Check Novelty status banner
    expect(screen.getByText(/Novelty filter active: tIoU < 0.50/i)).toBeInTheDocument();
    expect(screen.getByText(/1 historical moments indexed/i)).toBeInTheDocument();
  });

  it('expands multimodal scoring breakdown component on toggle', async () => {
    render(
      <SingleVideoStudio
        assetId="med_session4_test"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Octane Cyber Rooftop Chase')).toBeInTheDocument();
    });

    // Click Breakdown toggle
    const breakdownBtn = screen.getByRole('button', { name: /breakdown/i });
    fireEvent.click(breakdownBtn);

    // Verify Multimodal Signal components are displayed
    await waitFor(() => {
      expect(screen.getByText(/Multimodal Signal Scoring/i)).toBeInTheDocument();
      expect(screen.getByText('Hook Strength')).toBeInTheDocument();
      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getAllByText('Action & Motion').length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('96%')).toBeInTheDocument();
      expect(screen.getByText(/Dynamic camera sweeps snap cleanly to dialogue completion/i)).toBeInTheDocument();
    });
  });

  it('triggers Generate More Shorts with persistent novelty non-repetition', async () => {
    vi.mocked(apiClient.generateMoreHighlights).mockResolvedValue([
      {
        ...mockCandidates[0],
        id: 'cand_novelty_2',
        title: 'Dramatic Alley Escape',
        start_time: 65.0,
        end_time: 92.0,
        duration: 27.0,
      },
    ]);

    render(
      <SingleVideoStudio
        assetId="med_session4_test"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Octane Cyber Rooftop Chase')).toBeInTheDocument();
    });

    // Find and click "Generate More Shorts" button
    const genMoreBtn = screen.getByRole('button', { name: /generate more shorts/i });
    fireEvent.click(genMoreBtn);

    await waitFor(() => {
      expect(apiClient.generateMoreHighlights).toHaveBeenCalledWith(
        'proj_session4_test',
        'med_session4_test',
        expect.objectContaining({
          analysis_run_id: 'run_session4_1',
          target_clip_count: 10,
          min_duration: 12,
          max_duration: 60,
          aspect_ratio: '9:16',
          run_synchronously: true,
        })
      );
    });
  });

  it('opens and displays Candidate Batches drawer', async () => {
    render(
      <SingleVideoStudio
        assetId="med_session4_test"
        onBack={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Octane Cyber Rooftop Chase')).toBeInTheDocument();
    });

    // Open Candidate Batches drawer
    const batchesBtn = screen.getByRole('button', { name: /candidate batches \(1\)/i });
    fireEvent.click(batchesBtn);

    await waitFor(() => {
      expect(screen.getByText(/Candidate Discovery Runs & Novelty Tracking/i)).toBeInTheDocument();
      expect(screen.getByText('Batch #1')).toBeInTheDocument();
      expect(screen.getByText('Novelty Exclusions:')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });
});
