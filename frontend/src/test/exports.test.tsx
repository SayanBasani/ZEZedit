import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ExportStudio } from '../features/exports/ExportStudio';
import * as apiClient from '../services/apiClient';
import { ExportItem, ExportPresetItem } from '../types/exports';
import { CandidateItem } from '../types/highlights';
import { JobItem } from '../types/projects';

// Mock apiClient functions
vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClient>('../services/apiClient');
  return {
    ...actual,
    fetchExportPresets: vi.fn(),
    fetchProjectHighlights: vi.fn(),
    fetchProjectExports: vi.fn(),
    submitExportRender: vi.fn(),
    submitExportPreview: vi.fn(),
    fetchJob: vi.fn(),
    cancelExportRender: vi.fn(),
    deleteExport: vi.fn(),
    getExportVideoUrl: vi.fn().mockImplementation((pid, expId) => `/api/v1/projects/${pid}/exports/${expId}/video`),
  };
});

describe('ExportStudio Component (Milestone 8)', () => {
  const mockPresets: ExportPresetItem[] = [
    {
      preset_id: 'shorts_reels_9_16',
      name: 'YouTube Shorts / Reels (9:16)',
      description: 'Vertical 1080x1920 video',
      target_aspect_ratio: '9:16',
      target_width: 1080,
      target_height: 1920,
      video_codec: 'libx264',
      audio_codec: 'aac',
      pixel_fmt: 'yuv420p',
      fps: 30.0,
      crf: 22,
      audio_bitrate: '128k',
    },
    {
      preset_id: 'landscape_16_9',
      name: 'Widescreen Landscape (16:9)',
      description: 'Widescreen 1920x1080',
      target_aspect_ratio: '16:9',
      target_width: 1920,
      target_height: 1080,
      video_codec: 'libx264',
      audio_codec: 'aac',
      pixel_fmt: 'yuv420p',
      fps: 30.0,
      crf: 22,
      audio_bitrate: '128k',
    },
  ];

  const mockCandidate: CandidateItem = {
    id: 'cand_123',
    project_id: 'proj_1',
    media_asset_id: 'med_1',
    analysis_run_id: 'run_1',
    start_time: 1.5,
    end_time: 7.5,
    duration: 6.0,
    suggested_start_time: 1.5,
    suggested_end_time: 7.5,
    is_user_modified: false,
    title: 'Engaging Interview Moment',
    suggested_title: 'Engaging Interview',
    description: 'A great conversational hook.',
    category: 'Conversation',
    secondary_categories: [],
    quality_score: 84.5,
    score_breakdown: {
      semantic_interest: 18,
      narrative_completeness: 17,
      conversation_structure: 14,
      visual_interest: 13,
      audio_evidence: 8,
      opening_clarity: 9,
      ending_completeness: 8,
      duration_suitability: 8,
      context_dependency_penalty: -2,
      total_score: 84.5,
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
    ai_explanation: { hook: 'What happened next?' },
    scoring_version: '2.0.0-m6',
    queued_for_render: true,
    created_at: '2026-11-12T00:00:00Z',
    updated_at: '2026-11-12T00:00:00Z',
  };

  const mockExportItem: ExportItem = {
    id: 'exp_001',
    project_id: 'proj_1',
    candidate_id: 'cand_123',
    media_asset_id: 'med_1',
    title: 'Rendered_Short_1',
    export_preset: 'shorts_reels_9_16',
    target_aspect_ratio: '9:16',
    target_width: 1080,
    target_height: 1920,
    video_codec: 'h264',
    audio_codec: 'aac',
    pixel_fmt: 'yuv420p',
    fps: 30.0,
    crf: 22,
    audio_bitrate: '128k',
    caption_config: {
      mode: 'word_highlight',
      font_family: 'Arial',
      font_size: 24,
      bold: true,
      text_color: '#FFFFFF',
      highlight_color: '#FACC15',
      outline_color: '#000000',
      outline_width: 2.5,
      shadow_depth: 1.5,
      alignment: 2,
      margin_v: 90,
      max_words_per_line: 5,
      max_lines: 2,
      burn_in: true,
    },
    audio_config: {
      volume: 1.0,
      fade_in_seconds: 0.2,
      fade_out_seconds: 0.2,
      normalize_loudness: false,
      sample_rate: 48000,
      channels: 2,
    },
    output_path: 'D:/ZezEdit/storage/exports/proj_1/short1.mp4',
    output_filename: 'short1.mp4',
    file_size_bytes: 4500000,
    duration_seconds: 6.0,
    status: 'completed',
    validation_status: 'valid',
    validation_details: {
      is_valid: true,
      duration: 6.0,
      width: 1080,
      height: 1920,
      video_codec: 'h264',
      audio_codec: 'aac',
      pixel_fmt: 'yuv420p',
      file_size_bytes: 4500000,
      playable: true,
      errors: [],
    },
    created_at: '2026-11-12T00:10:00Z',
    completed_at: '2026-11-12T00:10:05Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchExportPresets).mockResolvedValue(mockPresets);
    vi.mocked(apiClient.fetchProjectHighlights).mockResolvedValue({
      project_id: 'proj_1',
      total_candidates: 1,
      recommended_count: 0,
      needs_review_count: 0,
      approved_count: 1,
      rejected_count: 0,
      candidates: [mockCandidate],
    });
    vi.mocked(apiClient.fetchProjectExports).mockResolvedValue({
      items: [mockExportItem],
      count: 1,
    });
  });

  it('renders Export Studio with toolbar, candidate info, and presets', async () => {
    render(<ExportStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('Shorts Rendering & Export Studio')).toBeInTheDocument();
      expect(screen.getByText('YouTube Shorts / Reels (9:16)')).toBeInTheDocument();
      expect(screen.getByText('Engaging Interview Moment')).toBeInTheDocument();
    });
  });

  it('switches between configuration tabs: Presets, Captions, and Audio', async () => {
    render(<ExportStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('1. Preset & Aspect')).toBeInTheDocument();
    });

    // Switch to Captions tab
    fireEvent.click(screen.getByText('2. Captions & Style'));
    expect(screen.getByText('Word Highlight')).toBeInTheDocument();
    expect(screen.getByText('Phrase Bursts')).toBeInTheDocument();
    expect(screen.getByText('No Captions')).toBeInTheDocument();

    // Switch to Audio tab
    fireEvent.click(screen.getByText('3. Audio & Volume'));
    expect(screen.getByText('Source Volume')).toBeInTheDocument();
    expect(screen.getByText('EBU R128 Loudness Normalization')).toBeInTheDocument();
  });

  it('allows selecting caption modes and tweaking font family', async () => {
    render(<ExportStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('2. Captions & Style')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('2. Captions & Style'));

    // Select Phrase Bursts
    fireEvent.click(screen.getByText('Phrase Bursts'));
    expect(screen.getByText('Phrase Bursts')).toBeInTheDocument();

    // Select font family
    const fontSelect = screen.getByDisplayValue('Arial');
    fireEvent.change(fontSelect, { target: { value: 'Montserrat' } });
    expect(screen.getByDisplayValue('Montserrat')).toBeInTheDocument();
  });

  it('triggers export render job and updates active job monitor', async () => {
    vi.mocked(apiClient.submitExportRender).mockResolvedValue({
      export_id: 'exp_new',
      job_id: 'job_render_1',
      status: 'queued',
      output_filename: 'Engaging_Interview_9x16_exp_new.mp4',
    });

    const mockRunningJob: JobItem = {
      id: 'job_render_1',
      project_id: 'proj_1',
      job_type: 'export_render',
      status: 'running',
      priority: 100,
      progress_pct: 65.0,
      current_stage: 'rendering_video',
      worker_id: null,
      worker_pid: 1234,
      input_config: {},
      result_metadata: null,
      error_message: null,
      retry_count: 0,
      max_attempts: 2,
      created_at: '2026-11-12T00:15:00Z',
      started_at: '2026-11-12T00:15:01Z',
      completed_at: null,
      cancellation_requested_at: null,
      cancelled_at: null,
      updated_at: '2026-11-12T00:15:02Z',
    };
    vi.mocked(apiClient.fetchJob).mockResolvedValue(mockRunningJob);

    render(<ExportStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('Start Full Render Export (1080p)')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start Full Render Export (1080p)'));

    await waitFor(() => {
      expect(apiClient.submitExportRender).toHaveBeenCalledWith(
        'proj_1',
        expect.objectContaining({
          candidate_id: 'cand_123',
          preset_id: 'shorts_reels_9_16',
        }),
        false
      );
      expect(screen.getByText('Rendering Video Export...')).toBeInTheDocument();
      expect(screen.getByText('65%')).toBeInTheDocument();
    });
  });

  it('renders completed export item in history and player with validation badge', async () => {
    render(<ExportStudio projectId="proj_1" />);

    await waitFor(() => {
      expect(screen.getByText('Export History (1)')).toBeInTheDocument();
      expect(screen.getAllByText('Rendered_Short_1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('FFprobe Verified')).toBeInTheDocument();
      expect(screen.getByText('1080x1920')).toBeInTheDocument();
    });
  });
});
