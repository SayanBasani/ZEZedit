import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HighlightsWorkspace } from '../features/highlights/HighlightsWorkspace';
import * as apiClient from '../services/apiClient';
import { CandidateItem, HighlightsOverview } from '../types/highlights';
import { MediaAssetItem } from '../types/projects';

const mockCandidates: CandidateItem[] = [
  {
    id: 'cand-1',
    project_id: 'proj-1',
    media_asset_id: 'med-1',
    analysis_run_id: 'run-1',
    start_time: 10.0,
    end_time: 35.0,
    duration: 25.0,
    suggested_start_time: 10.0,
    suggested_end_time: 35.0,
    is_user_modified: false,
    title: 'Why Privacy and Local AI Matters',
    suggested_title: 'Why Privacy and Local AI Matters',
    description: 'Discussion on local inference and offline editing advantages.',
    category: 'dialogue',
    secondary_categories: ['insightful'],
    quality_score: 84.5,
    score_breakdown: {
      semantic_interest: 18.0,
      narrative_completeness: 17.5,
      conversation_structure: 14.0,
      visual_interest: 12.0,
      audio_evidence: 8.0,
      opening_clarity: 8.0,
      ending_completeness: 8.0,
      duration_suitability: 4.0,
      context_dependency_penalty: -5.0,
      total_score: 84.5,
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
    transcript_references: ['t1', 't2'],
    scene_references: ['sc1'],
    visual_evidence: [{ timestamp: 12.0, description: 'Speaker gesturing' }],
    audio_evidence: [],
    ai_explanation: {
      hook: 'Why did you decide to build an AI video editor completely local first?',
      why_it_works: 'Strong opening question followed by confident value statement.',
      strengths: ['Clear question-answer arc', 'High visual engagement'],
      risks: [],
    },
    alternative_of_candidate_id: null,
    overlap_group_id: 'grp-1',
    scoring_version: '2.0.0-m6',
    queued_for_render: false,
    created_at: '2026-11-11T12:00:00Z',
    updated_at: '2026-11-11T12:00:00Z',
  },
  {
    id: 'cand-2',
    project_id: 'proj-1',
    media_asset_id: 'med-1',
    analysis_run_id: 'run-1',
    start_time: 50.0,
    end_time: 72.0,
    duration: 22.0,
    suggested_start_time: 50.0,
    suggested_end_time: 72.0,
    is_user_modified: false,
    title: 'The Real Performance Numbers',
    suggested_title: 'The Real Performance Numbers',
    description: 'Benchmarking CPU inference on modest hardware.',
    category: 'insightful',
    secondary_categories: [],
    quality_score: 62.0,
    score_breakdown: {
      semantic_interest: 12.0,
      narrative_completeness: 11.0,
      conversation_structure: 9.0,
      visual_interest: 10.0,
      audio_evidence: 7.0,
      opening_clarity: 6.0,
      ending_completeness: 7.0,
      duration_suitability: 5.0,
      context_dependency_penalty: -5.0,
      total_score: 62.0,
    },
    gate_results: {
      overall_status: 'needs_review',
      minimum_score_pass: true,
      duration_pass: true,
      transcript_pass: true,
      narrative_pass: true,
      visual_pass: true,
      context_pass: true,
      failure_reasons: ['Mildly abrupt opening'],
    },
    warnings: ['Mildly abrupt opening'],
    missing_evidence: [],
    review_status: 'needs_review',
    rejection_reason: null,
    transcript_references: ['t3'],
    scene_references: ['sc2'],
    visual_evidence: [],
    audio_evidence: [],
    ai_explanation: {
      hook: 'Let us check the benchmark graph.',
      why_it_works: 'Direct technical comparison.',
    },
    alternative_of_candidate_id: null,
    overlap_group_id: null,
    scoring_version: '2.0.0-m6',
    queued_for_render: false,
    created_at: '2026-11-11T12:00:00Z',
    updated_at: '2026-11-11T12:00:00Z',
  },
];

const mockOverview: HighlightsOverview = {
  project_id: 'proj-1',
  total_candidates: 2,
  recommended_count: 1,
  needs_review_count: 1,
  approved_count: 0,
  rejected_count: 0,
  candidates: mockCandidates,
};

const mockMediaAssets: MediaAssetItem[] = [
  {
    id: 'med-1',
    project_id: 'proj-1',
    original_filename: 'podcast_interview.mp4',
    storage_path: 'media/podcast_interview.mp4',
    is_external: false,
    media_type: 'video',
    file_size_bytes: 50000000,
    mime_type: 'video/mp4',
    duration_seconds: 120.0,
    width: 1920,
    height: 1080,
    fps: 30.0,
    video_codec: 'h264',
    audio_codec: 'aac',
    availability_status: 'present',
    proxy_reference_path: null,
    thumbnail_reference_path: 'thumbnails/med-1.jpg',
    proxy_status: 'ready',
    metadata_status: 'complete',
    metadata: {},
    created_at: '2026-11-11T12:00:00Z',
    updated_at: '2026-11-11T12:00:00Z',
  },
];

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    fetchProjectHighlights: vi.fn(),
    approveCandidate: vi.fn(),
    rejectCandidate: vi.fn(),
    restoreCandidate: vi.fn(),
    updateCandidate: vi.fn(),
    queueCandidateRender: vi.fn(),
    bulkReviewCandidates: vi.fn(),
    fetchCandidateAlternatives: vi.fn().mockResolvedValue([]),
    discoverHighlights: vi.fn().mockResolvedValue([]),
  };
});

describe('HighlightsWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchProjectHighlights).mockResolvedValue(mockOverview);
  });

  it('renders highlights workspace metrics and candidate cards', async () => {
    render(
      <HighlightsWorkspace
        projectId="proj-1"
        mediaAssets={mockMediaAssets}
      />
    );

    // Verify studio header
    expect(screen.getByText('Shorts Highlights Studio')).toBeInTheDocument();
    expect(screen.getByText('M6 Engine')).toBeInTheDocument();

    // Verify metrics
    await waitFor(() => {
      expect(screen.getByText('Why Privacy and Local AI Matters')).toBeInTheDocument();
    });

    expect(screen.getByText('The Real Performance Numbers')).toBeInTheDocument();
    expect(screen.getByText('Total Found')).toBeInTheDocument();
    expect(screen.getByText('Recommended')).toBeInTheDocument();
  });

  it('filters candidates by review status tab', async () => {
    render(
      <HighlightsWorkspace
        projectId="proj-1"
        mediaAssets={mockMediaAssets}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Why Privacy and Local AI Matters')).toBeInTheDocument();
    });

    // Click recommended filter tab
    const recTab = screen.getByRole('button', { name: /^recommended$/i });
    fireEvent.click(recTab);

    await waitFor(() => {
      expect(apiClient.fetchProjectHighlights).toHaveBeenCalledWith(
        'proj-1',
        'recommended',
        undefined,
        undefined
      );
    });
  });

  it('allows approving and rejecting candidate clips', async () => {
    vi.mocked(apiClient.approveCandidate).mockResolvedValue({
      ...mockCandidates[0],
      review_status: 'approved',
    });

    render(
      <HighlightsWorkspace
        projectId="proj-1"
        mediaAssets={mockMediaAssets}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Why Privacy and Local AI Matters')).toBeInTheDocument();
    });

    const approveButtons = screen.getAllByTitle('Approve candidate');
    expect(approveButtons.length).toBeGreaterThan(0);
    fireEvent.click(approveButtons[0]);

    await waitFor(() => {
      expect(apiClient.approveCandidate).toHaveBeenCalledWith('proj-1', 'cand-1');
    });
  });

  it('opens detail inspector and allows adjusting boundaries', async () => {
    vi.mocked(apiClient.updateCandidate).mockResolvedValue({
      ...mockCandidates[0],
      start_time: 10.5,
      is_user_modified: true,
      duration: 24.5,
    });

    render(
      <HighlightsWorkspace
        projectId="proj-1"
        mediaAssets={mockMediaAssets}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Why Privacy and Local AI Matters')).toBeInTheDocument();
    });

    // Click inspect on first card
    const inspectButtons = screen.getAllByRole('button', { name: /inspect/i });
    fireEvent.click(inspectButtons[0]);

    // Inspector modal should open
    await waitFor(() => {
      expect(screen.getByText(/Boundary Fine-Tuning/i)).toBeInTheDocument();
      expect(screen.getByText(/Explainable Score Breakdown/i)).toBeInTheDocument();
    });

    // Click +0.1s on start boundary
    const plusPointOne = screen.getAllByText('+0.1s')[0];
    fireEvent.click(plusPointOne);

    // Save boundary changes button should appear
    const saveBtn = screen.getByRole('button', { name: /save boundary changes/i });
    expect(saveBtn).toBeInTheDocument();
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.updateCandidate).toHaveBeenCalled();
    });
  });

  it('toggles Shorts render queue flag', async () => {
    vi.mocked(apiClient.queueCandidateRender).mockResolvedValue({
      ...mockCandidates[0],
      queued_for_render: true,
    });

    render(
      <HighlightsWorkspace
        projectId="proj-1"
        mediaAssets={mockMediaAssets}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Why Privacy and Local AI Matters')).toBeInTheDocument();
    });

    const queueButtons = screen.getAllByTitle('Include in final Shorts render queue');
    fireEvent.click(queueButtons[0]);

    await waitFor(() => {
      expect(apiClient.queueCandidateRender).toHaveBeenCalledWith('proj-1', 'cand-1', true);
    });
  });
});
