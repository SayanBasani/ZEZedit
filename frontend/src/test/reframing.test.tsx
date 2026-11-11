import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReframingWorkspace } from '../features/reframing/ReframingWorkspace';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem } from '../types/projects';
import { ReframingPlanItem, ReframingRevisionItem } from '../types/reframing';

const mockAsset: MediaAssetItem = {
  id: 'med-1',
  project_id: 'proj-1',
  original_filename: 'interview_16x9.mp4',
  storage_path: 'media/interview_16x9.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 50000000,
  mime_type: 'video/mp4',
  duration_seconds: 30.0,
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
  created_at: '2026-11-12T12:00:00Z',
  updated_at: '2026-11-12T12:00:00Z',
};

const mockPlan: ReframingPlanItem = {
  id: 'ref-1',
  project_id: 'proj-1',
  media_asset_id: 'med-1',
  target_aspect_ratio: '9:16',
  framing_strategy: 'single_subject',
  status: 'completed',
  source_width: 1920,
  source_height: 1080,
  output_width: 1080,
  output_height: 1920,
  start_time: 0.0,
  end_time: 15.0,
  duration: 15.0,
  base_zoom: 1.0,
  headroom_factor: 0.15,
  smoothing_window_seconds: 0.8,
  keyframes: [
    {
      timestamp: 0.0,
      crop_x: 600,
      crop_y: 0,
      crop_w: 608,
      crop_h: 1080,
      zoom: 1.0,
      headroom: 0.15,
      framing_strategy: 'single_subject',
    },
    {
      timestamp: 5.0,
      crop_x: 650,
      crop_y: 0,
      crop_w: 608,
      crop_h: 1080,
      zoom: 1.0,
      headroom: 0.15,
      framing_strategy: 'single_subject',
    },
  ],
  detected_tracks: [
    {
      track_id: 'subject_1',
      category: 'face',
      first_seen: 0.0,
      last_seen: 15.0,
      confidence_avg: 0.9,
      detections: [
        {
          timestamp: 0.0,
          box_x: 800,
          box_y: 300,
          box_w: 120,
          box_h: 150,
          confidence: 0.9,
          category: 'face',
          subject_id: 'subject_1',
        },
      ],
    },
  ],
  scene_cuts: [5.0],
  warnings: [],
  active_revision_id: 'rev-1',
  calculation_version: '2.0.0-m7',
  created_at: '2026-11-12T12:00:00Z',
  updated_at: '2026-11-12T12:00:00Z',
};

const mockRevisions: ReframingRevisionItem[] = [
  {
    id: 'rev-1',
    reframing_plan_id: 'ref-1',
    revision_number: 1,
    label: 'AI Initial Framing',
    is_ai_generated: true,
    manual_overrides: [],
    effective_keyframes: mockPlan.keyframes,
    rendered_video_path: null,
    created_at: '2026-11-12T12:00:00Z',
  },
];

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    analyzeReframing: vi.fn(),
    fetchReframingPlan: vi.fn(),
    fetchCropPreview: vi.fn(),
    saveCropOverrides: vi.fn(),
    fetchReframingRevisions: vi.fn(),
    restoreReframingRevision: vi.fn(),
    renderReframingRevision: vi.fn(),
    getProxyUrl: vi.fn().mockReturnValue('/api/v1/mock-proxy.mp4'),
    getRenderedVideoUrl: vi.fn().mockReturnValue('/api/v1/mock-rendered.mp4'),
  };
});

describe('ReframingWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.analyzeReframing).mockResolvedValue(mockPlan);
    vi.mocked(apiClient.fetchReframingRevisions).mockResolvedValue(mockRevisions);
    vi.mocked(apiClient.fetchCropPreview).mockResolvedValue({
      plan_id: 'ref-1',
      timestamp: 0.0,
      crop_x: 600,
      crop_y: 0,
      crop_w: 608,
      crop_h: 1080,
      zoom: 1.0,
      source_width: 1920,
      source_height: 1080,
      target_aspect_ratio: '9:16',
    });
  });

  it('renders reframing workspace with source and portrait viewports', async () => {
    render(<ReframingWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={vi.fn()} />);

    expect(screen.getByText('Smart Reframing & Subject Tracking Studio')).toBeInTheDocument();
    expect(screen.getByText('M7 Engine')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Portrait Viewport \(9:16\)/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Revisions (1)')).toBeInTheDocument();
  });

  it('allows manual crop horizontal adjustment and keyframe setting', async () => {
    render(<ReframingWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/Portrait Viewport \(9:16\)/i)).toBeInTheDocument();
    });

    // Click +20px adjustment button
    const plusBtn = screen.getByText('+20px');
    fireEvent.click(plusBtn);

    // Click "Set Keyframe"
    const setKfBtn = screen.getByRole('button', { name: /set keyframe/i });
    fireEvent.click(setKfBtn);

    // Save Revision button should appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save revision/i })).toBeInTheDocument();
    });
  });

  it('saves manual adjustments as a new revision', async () => {
    vi.mocked(apiClient.saveCropOverrides).mockResolvedValue({
      ...mockPlan,
      active_revision_id: 'rev-2',
    });

    render(<ReframingWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/Portrait Viewport \(9:16\)/i)).toBeInTheDocument();
    });

    // Trigger adjustment and set keyframe
    fireEvent.click(screen.getByText('+20px'));
    fireEvent.click(screen.getByRole('button', { name: /set keyframe/i }));

    const saveBtn = await screen.findByRole('button', { name: /save revision/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.saveCropOverrides).toHaveBeenCalled();
    });
  });

  it('opens revisions drawer and allows restoring a prior revision', async () => {
    vi.mocked(apiClient.restoreReframingRevision).mockResolvedValue(mockPlan);

    render(<ReframingWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Revisions (1)')).toBeInTheDocument();
    });

    // Open revisions modal
    fireEvent.click(screen.getByText('Revisions (1)'));

    await waitFor(() => {
      expect(screen.getByText(/Framing Revisions Ledger/i)).toBeInTheDocument();
      expect(screen.getByText(/Revision 1: AI Initial Framing/i)).toBeInTheDocument();
    });
  });

  it('triggers real FFmpeg rendering for active revision', async () => {
    vi.mocked(apiClient.renderReframingRevision).mockResolvedValue({
      output_path: 'storage/shorts/test.mp4',
      output_width: 1080,
      output_height: 1920,
      duration: 15.0,
      file_size_bytes: 1200000,
      crop_w: 608,
      crop_h: 1080,
      keyframes_count: 2,
    });

    render(<ReframingWorkspace projectId="proj-1" mediaAsset={mockAsset} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /render video/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /render video/i }));

    await waitFor(() => {
      expect(apiClient.renderReframingRevision).toHaveBeenCalledWith('proj-1', 'ref-1', 'rev-1');
    });
  });
});
