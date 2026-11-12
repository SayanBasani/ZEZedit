import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BatchExportModal } from '../features/exports/BatchExportModal';
import * as apiClient from '../services/apiClient';
import { CandidateItem } from '../types/highlights';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    submitBatchExport: vi.fn(),
    fetchVideoWorkflowState: vi.fn(),
    fetchProjectHighlights: vi.fn(),
    fetchExportPresets: vi.fn().mockResolvedValue([]),
    fetchProjectExports: vi.fn().mockResolvedValue({ items: [], count: 0 }),
    fetchAnalysisRuns: vi.fn().mockResolvedValue([]),
  };
});

describe('Milestone 18: Unified Video-to-Shorts Pipeline Frontend Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockCandidates: CandidateItem[] = [
    {
      id: 'cand_01',
      project_id: 'proj_01',
      media_asset_id: 'med_01',
      analysis_run_id: 'run_01',
      start_time: 10.0,
      end_time: 25.0,
      duration: 15.0,
      suggested_start_time: 10.0,
      suggested_end_time: 25.0,
      is_user_modified: false,
      title: 'Top AI Breakthrough',
      suggested_title: 'Top AI Breakthrough',
      description: 'Speaker discussing local AI models.',
      category: 'insight',
      secondary_categories: [],
      quality_score: 0.94,
      score_breakdown: {
        semantic_interest: 0.95,
        narrative_completeness: 0.9,
        conversation_structure: 0.95,
        visual_interest: 0.9,
        audio_evidence: 0.9,
        opening_clarity: 0.95,
        ending_completeness: 0.9,
        duration_suitability: 0.9,
        context_dependency_penalty: 0.0,
        total_score: 0.94,
      },
      gate_results: {
        overall_status: 'approved',
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
      review_status: 'approved',
      transcript_references: [],
      scene_references: [],
      visual_evidence: [],
      audio_evidence: [],
      ai_explanation: { hook: 'Strong hook' },
      alternative_of_candidate_id: null,
      overlap_group_id: null,
      scoring_version: '2.0.0',
      queued_for_render: false,
      created_at: '2026-11-12T08:00:00Z',
      updated_at: '2026-11-12T08:00:00Z',
    },
    {
      id: 'cand_02',
      project_id: 'proj_01',
      media_asset_id: 'med_01',
      analysis_run_id: 'run_01',
      start_time: 40.0,
      end_time: 70.0,
      duration: 30.0,
      suggested_start_time: 40.0,
      suggested_end_time: 70.0,
      is_user_modified: false,
      title: 'Hilarious Blooper',
      suggested_title: 'Hilarious Blooper',
      description: 'Host laughing at funny mistake.',
      category: 'humor',
      secondary_categories: [],
      quality_score: 0.88,
      score_breakdown: {
        semantic_interest: 0.85,
        narrative_completeness: 0.9,
        conversation_structure: 0.88,
        visual_interest: 0.9,
        audio_evidence: 0.85,
        opening_clarity: 0.88,
        ending_completeness: 0.85,
        duration_suitability: 0.9,
        context_dependency_penalty: 0.0,
        total_score: 0.88,
      },
      gate_results: {
        overall_status: 'approved',
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
      review_status: 'approved',
      transcript_references: [],
      scene_references: [],
      visual_evidence: [],
      audio_evidence: [],
      ai_explanation: { hook: 'Funny moment' },
      alternative_of_candidate_id: null,
      overlap_group_id: null,
      scoring_version: '2.0.0',
      queued_for_render: false,
      created_at: '2026-11-12T08:00:00Z',
      updated_at: '2026-11-12T08:00:00Z',
    },
  ];

  it('renders BatchExportModal and displays candidate selection', () => {
    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_01"
        candidates={mockCandidates}
      />
    );

    expect(screen.getByText(/Batch Export Multiple Shorts/i)).toBeInTheDocument();
    expect(screen.getByText('Top AI Breakthrough')).toBeInTheDocument();
    expect(screen.getByText('Hilarious Blooper')).toBeInTheDocument();
    expect(screen.getByText(/Render 2 Shorts/i)).toBeInTheDocument();
  });

  it('allows deselecting candidates and updates render count', () => {
    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_01"
        candidates={mockCandidates}
      />
    );

    const deselectButton = screen.getByText('Deselect All');
    fireEvent.click(deselectButton);

    expect(screen.getByText(/Render 0 Shorts/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render 0 Shorts/i })).toBeDisabled();

    const selectButton = screen.getByText('Select All');
    fireEvent.click(selectButton);

    expect(screen.getByText(/Render 2 Shorts/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Render 2 Shorts/i })).not.toBeDisabled();
  });

  it('submits batch export payload to apiClient and displays success response', async () => {
    const mockSuccessResponse = {
      batch_id: 'batch_test123',
      project_id: 'proj_01',
      total_requested: 2,
      total_submitted: 2,
      items: [
        {
          candidate_id: 'cand_01',
          export_id: 'exp_01',
          job_id: 'job_01',
          status: 'queued',
          output_filename: 'Top_AI_Breakthrough_9x16.mp4',
        },
        {
          candidate_id: 'cand_02',
          export_id: 'exp_02',
          job_id: 'job_02',
          status: 'queued',
          output_filename: 'Hilarious_Blooper_9x16.mp4',
        },
      ],
      skipped_candidates: [],
    };

    vi.mocked(apiClient.submitBatchExport).mockResolvedValueOnce(mockSuccessResponse);
    const onSuccess = vi.fn();

    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_01"
        candidates={mockCandidates}
        onSuccess={onSuccess}
      />
    );

    const submitBtn = screen.getByRole('button', { name: /Render 2 Shorts/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.submitBatchExport).toHaveBeenCalledWith('proj_01', {
        candidate_ids: ['cand_01', 'cand_02'],
        preset: 'vertical_9_16',
        caption_mode: 'word_highlight',
        normalize_audio: true,
      });
      expect(onSuccess).toHaveBeenCalledWith(mockSuccessResponse);
      expect(screen.getByText(/Batch Render Successfully Queued!/i)).toBeInTheDocument();
      expect(screen.getByText(/Top_AI_Breakthrough_9x16.mp4/i)).toBeInTheDocument();
    });
  });
});
