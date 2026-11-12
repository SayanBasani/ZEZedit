import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BatchExportModal } from '../features/exports/BatchExportModal';
import * as apiClient from '../services/apiClient';
import { CandidateItem } from '../types/highlights';

const mockCandidates: CandidateItem[] = [
  {
    id: 'cand_m24_1',
    project_id: 'proj_1',
    media_asset_id: 'med_1',
    analysis_run_id: 'ar_1',
    start_time: 10.0,
    end_time: 25.0,
    duration: 15.0,
    suggested_start_time: 10.0,
    suggested_end_time: 25.0,
    is_user_modified: false,
    title: 'Epic Highlight Reel One',
    suggested_title: 'Epic Highlight Reel One',
    description: 'High emotional peak detected',
    category: 'dialogue',
    secondary_categories: ['viral'],
    quality_score: 94.0,
    score_breakdown: {
      semantic_interest: 20,
      narrative_completeness: 20,
      conversation_structure: 18,
      visual_interest: 18,
      audio_evidence: 10,
      opening_clarity: 10,
      ending_completeness: 8,
      duration_suitability: 5,
      context_dependency_penalty: 0,
      total_score: 94.0,
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
    rejection_reason: null,
    transcript_references: ['t1'],
    scene_references: ['s1'],
    visual_evidence: [],
    audio_evidence: [],
    ai_explanation: {
      hook: 'This is amazing',
      why_it_works: 'Strong emotion',
      strengths: ['Hook'],
      risks: [],
    },
    scoring_version: '1.0',
    queued_for_render: true,
    created_at: '2026-11-12T00:00:00Z',
    updated_at: '2026-11-12T00:00:00Z',
  },
  {
    id: 'cand_m24_2',
    project_id: 'proj_1',
    media_asset_id: 'med_1',
    analysis_run_id: 'ar_1',
    start_time: 40.0,
    end_time: 55.0,
    duration: 15.0,
    suggested_start_time: 40.0,
    suggested_end_time: 55.0,
    is_user_modified: false,
    title: 'Surprise Reaction Clip',
    suggested_title: 'Surprise Reaction Clip',
    description: 'Audience laughter peak',
    category: 'reaction',
    secondary_categories: ['humor'],
    quality_score: 88.0,
    score_breakdown: {
      semantic_interest: 18,
      narrative_completeness: 18,
      conversation_structure: 16,
      visual_interest: 16,
      audio_evidence: 10,
      opening_clarity: 8,
      ending_completeness: 8,
      duration_suitability: 5,
      context_dependency_penalty: 0,
      total_score: 88.0,
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
    rejection_reason: null,
    transcript_references: ['t2'],
    scene_references: ['s2'],
    visual_evidence: [],
    audio_evidence: [],
    ai_explanation: {
      hook: 'Unbelievable',
      why_it_works: 'High laughter energy',
      strengths: ['Humor'],
      risks: [],
    },
    scoring_version: '1.0',
    queued_for_render: false,
    created_at: '2026-11-12T00:00:00Z',
    updated_at: '2026-11-12T00:00:00Z',
  },
];

describe('Milestone 24: BatchExportModal Component Verification (ZEZ-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders modal with approved candidates list and default export preset', () => {
    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_1"
        candidates={mockCandidates}
      />
    );

    expect(screen.getByText('Batch Export Multiple Shorts')).toBeInTheDocument();
    expect(screen.getByText('Epic Highlight Reel One')).toBeInTheDocument();
    expect(screen.getByText('Surprise Reaction Clip')).toBeInTheDocument();
    expect(screen.getByText('9:16 Vertical (Shorts/Reels)')).toBeInTheDocument();
  });

  it('allows selecting and deselecting all candidates dynamically', () => {
    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_1"
        candidates={mockCandidates}
      />
    );

    const deselectBtn = screen.getByText('Deselect All');
    fireEvent.click(deselectBtn);

    const exportBtn = screen.getByRole('button', { name: /Render 0 Shorts/i });
    expect(exportBtn).toBeDisabled();

    const selectAllBtn = screen.getByText('Select All');
    fireEvent.click(selectAllBtn);

    expect(screen.getByRole('button', { name: /Render 2 Shorts/i })).not.toBeDisabled();
  });

  it('allows changing export preset and caption overlay mode', () => {
    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_1"
        candidates={mockCandidates}
      />
    );

    const presetSelect = screen.getByDisplayValue('9:16 Vertical (Shorts/Reels)') as HTMLSelectElement;
    fireEvent.change(presetSelect, { target: { value: 'square_1_1' } });
    expect(presetSelect.value).toBe('square_1_1');

    const captionSelect = screen.getByDisplayValue('Animated Word Highlight') as HTMLSelectElement;
    fireEvent.change(captionSelect, { target: { value: 'none' } });
    expect(captionSelect.value).toBe('none');
  });

  it('dispatches batch export request and displays confirmation with job link', async () => {
    const submitSpy = vi.spyOn(apiClient, 'submitBatchExport').mockResolvedValue({
      batch_id: 'batch_m24_1',
      project_id: 'proj_1',
      total_requested: 2,
      total_submitted: 2,
      items: [
        {
          candidate_id: 'cand_m24_1',
          export_id: 'exp_1',
          job_id: 'job_1',
          status: 'queued',
          output_filename: 'clip1.mp4',
        },
        {
          candidate_id: 'cand_m24_2',
          export_id: 'exp_2',
          job_id: 'job_2',
          status: 'queued',
          output_filename: 'clip2.mp4',
        },
      ],
      skipped_candidates: [],
    });

    const mockNavigate = vi.fn();

    render(
      <BatchExportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_1"
        candidates={mockCandidates}
        onNavigateToQueue={mockNavigate}
      />
    );

    const exportBtn = screen.getByRole('button', { name: /Render 2 Shorts/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith(
        'proj_1',
        expect.objectContaining({
          candidate_ids: ['cand_m24_1', 'cand_m24_2'],
          preset: 'vertical_9_16',
        })
      );
      expect(screen.getByText('Batch Render Successfully Queued!')).toBeInTheDocument();
    });

    const queueLink = screen.getByRole('button', { name: /View Working Queue/i });
    fireEvent.click(queueLink);
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });
});
