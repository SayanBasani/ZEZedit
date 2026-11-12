import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CandidateClipEditorModal } from '../features/studio/CandidateClipEditorModal';
import * as apiClient from '../services/apiClient';
import { CandidateItem, CandidateClipEdit } from '../types/highlights';
import { MediaAssetItem } from '../types/projects';

vi.mock('../services/apiClient', () => ({
  fetchCandidateEdit: vi.fn(),
  saveCandidateEdit: vi.fn(),
  resetCandidateEdit: vi.fn(),
  trackCandidateSubjects: vi.fn(),
}));

const mockAsset: MediaAssetItem = {
  id: 'med_test_session5',
  project_id: 'proj_test_session5',
  original_filename: 'interview_clip.mp4',
  storage_path: 'D:/media/interview_clip.mp4',
  is_external: true,
  media_type: 'video',
  file_size_bytes: 50 * 1024 * 1024,
  mime_type: 'video/mp4',
  duration_seconds: 120.0,
  width: 1920,
  height: 1080,
  fps: 30,
  video_codec: 'h264',
  audio_codec: 'aac',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'extracted',
  metadata: {},
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

const mockCandidate: CandidateItem = {
  id: 'cand_test_session5',
  project_id: 'proj_test_session5',
  media_asset_id: 'med_test_session5',
  analysis_run_id: 'run_test_session5',
  start_time: 15.0,
  end_time: 40.0,
  duration: 25.0,
  suggested_start_time: 15.0,
  suggested_end_time: 40.0,
  is_user_modified: false,
  title: 'Epic Interview Moment',
  suggested_title: 'Epic Interview Moment',
  description: 'High energy conversation moment',
  category: 'Conversation',
  secondary_categories: ['Humor'],
  quality_score: 92.5,
  score_breakdown: {
    semantic_interest: 90,
    narrative_completeness: 88,
    conversation_structure: 92,
    visual_interest: 85,
    audio_evidence: 90,
    opening_clarity: 95,
    ending_completeness: 90,
    duration_suitability: 95,
    context_dependency_penalty: 0,
    total_score: 92.5,
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
  transcript_references: [],
  scene_references: [],
  visual_evidence: [],
  audio_evidence: [],
  ai_explanation: { why_it_works: 'Compelling moment' },
  scoring_version: '2.0.0-m4',
  queued_for_render: false,
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

const mockEditResponse: CandidateClipEdit = {
  id: 'cce_mock_001',
  candidate_id: 'cand_test_session5',
  project_id: 'proj_test_session5',
  media_asset_id: 'med_test_session5',
  original_start_time: 15.0,
  original_end_time: 40.0,
  edited_start_time: 15.0,
  edited_end_time: 40.0,
  edited_duration: 25.0,
  aspect_ratio: '9:16',
  framing_mode: 'center',
  manual_crop_x_pct: 50.0,
  manual_crop_y_pct: 50.0,
  manual_crop_zoom: 1.0,
  tracking_status: 'none',
  version: 1,
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
  media_duration: 120.0,
  media_width: 1920,
  media_height: 1080,
  candidate_title: 'Epic Interview Moment',
};

describe('Session 5: Candidate Clip Editing & Reframing Modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchCandidateEdit).mockResolvedValue(mockEditResponse);
  });

  it('renders candidate title, duration badge, aspect ratio, and transport controls', async () => {
    render(
      <CandidateClipEditorModal
        isOpen={true}
        onClose={vi.fn()}
        candidate={mockCandidate}
        mediaAsset={mockAsset}
        projectId="proj_test_session5"
        videoSrc="http://localhost:8000/media.mp4"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Epic Interview Moment')).toBeInTheDocument();
      expect(screen.getByText('25.0s')).toBeInTheDocument();
      expect(screen.getByText('Timeline Trimming Handles')).toBeInTheDocument();
      expect(screen.getByText('Target Aspect Ratio')).toBeInTheDocument();
      expect(screen.getByText('Reset to Original')).toBeInTheDocument();
      expect(screen.getByText('Save Clip Edit')).toBeInTheDocument();
    });
  });

  it('allows switching aspect ratios and framing modes', async () => {
    render(
      <CandidateClipEditorModal
        isOpen={true}
        onClose={vi.fn()}
        candidate={mockCandidate}
        mediaAsset={mockAsset}
        projectId="proj_test_session5"
        videoSrc="http://localhost:8000/media.mp4"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Epic Interview Moment')).toBeInTheDocument();
    });

    // Switch aspect ratio to 1:1
    const squareBtn = screen.getByRole('button', { name: /1:1/i });
    fireEvent.click(squareBtn);

    // Switch framing mode to Manual Offset
    const manualBtn = screen.getByRole('button', { name: /Manual Offset/i });
    fireEvent.click(manualBtn);

    expect(screen.getByText(/Horizontal Offset \(X\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Vertical Offset \(Y\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Digital Zoom/i)).toBeInTheDocument();

    // Switch framing mode to Smart Tracking
    const trackingBtn = screen.getByRole('button', { name: /Smart Tracking/i });
    fireEvent.click(trackingBtn);

    expect(screen.getByText('Smart Subject Tracking Engine')).toBeInTheDocument();
    expect(screen.getByText('Run Subject Tracking on Clip')).toBeInTheDocument();
  });

  it('persists clip edit when clicking Save Clip Edit', async () => {
    vi.mocked(apiClient.saveCandidateEdit).mockResolvedValue({
      ...mockEditResponse,
      edited_start_time: 18.0,
      edited_end_time: 38.0,
      edited_duration: 20.0,
      aspect_ratio: '1:1',
      framing_mode: 'manual',
    });

    render(
      <CandidateClipEditorModal
        isOpen={true}
        onClose={vi.fn()}
        candidate={mockCandidate}
        mediaAsset={mockAsset}
        projectId="proj_test_session5"
        videoSrc="http://localhost:8000/media.mp4"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Save Clip Edit')).toBeInTheDocument();
    });

    const saveBtn = screen.getByText('Save Clip Edit');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.saveCandidateEdit).toHaveBeenCalledWith(
        'proj_test_session5',
        'med_test_session5',
        'cand_test_session5',
        expect.objectContaining({
          aspect_ratio: '9:16',
          framing_mode: 'center',
        })
      );
      expect(screen.getByText(/Clip edits saved successfully!/i)).toBeInTheDocument();
    });
  });

  it('reverts to initial discovery boundaries when clicking Reset to Original', async () => {
    vi.mocked(apiClient.resetCandidateEdit).mockResolvedValue({
      ...mockEditResponse,
      edited_start_time: 15.0,
      edited_end_time: 40.0,
      edited_duration: 25.0,
      aspect_ratio: '9:16',
      framing_mode: 'center',
    });

    render(
      <CandidateClipEditorModal
        isOpen={true}
        onClose={vi.fn()}
        candidate={mockCandidate}
        mediaAsset={mockAsset}
        projectId="proj_test_session5"
        videoSrc="http://localhost:8000/media.mp4"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Reset to Original')).toBeInTheDocument();
    });

    const resetBtn = screen.getByText('Reset to Original');
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(apiClient.resetCandidateEdit).toHaveBeenCalledWith(
        'proj_test_session5',
        'med_test_session5',
        'cand_test_session5'
      );
      expect(screen.getByText(/Reverted clip boundaries and framing back to initial discovery state/i)).toBeInTheDocument();
    });
  });
});
