import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PostImportModal } from '../features/media/PostImportModal';
import * as apiClient from '../services/apiClient';
import { MediaAssetItem } from '../types/projects';

const mockAsset: MediaAssetItem = {
  id: 'asset_post_m24',
  project_id: 'proj_m24',
  original_filename: 'sample_podcast.mp4',
  storage_path: 'media/asset_post_m24/sample_podcast.mp4',
  is_external: false,
  media_type: 'video',
  file_size_bytes: 45000000,
  mime_type: 'video/mp4',
  duration_seconds: 120.5,
  width: 1920,
  height: 1080,
  fps: 30.0,
  video_codec: 'h264',
  audio_codec: 'aac',
  availability_status: 'present',
  proxy_reference_path: null,
  thumbnail_reference_path: null,
  proxy_status: 'ready',
  metadata_status: 'complete',
  metadata: {},
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

describe('Milestone 24: PostImportModal Component Verification (ZEZ-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders modal with asset metadata and duration correctly', () => {
    render(
      <PostImportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_m24"
        asset={mockAsset}
        onOpenWorkspace={vi.fn()}
        onImportAnother={vi.fn()}
      />
    );

    expect(screen.getByText('Media Ingested Successfully')).toBeInTheDocument();
    expect(screen.getByText('sample_podcast.mp4')).toBeInTheDocument();
    expect(screen.getByText('Ready for Editing')).toBeInTheDocument();
    expect(screen.getByText('1920x1080')).toBeInTheDocument();
    expect(screen.getByText('30 fps')).toBeInTheDocument();
  });

  it('allows switching analysis depth profile between fast, balanced, and detailed', () => {
    render(
      <PostImportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_m24"
        asset={mockAsset}
        onOpenWorkspace={vi.fn()}
        onImportAnother={vi.fn()}
      />
    );

    const detailedBtn = screen.getByRole('button', { name: /^detailed$/i });
    fireEvent.click(detailedBtn);
    expect(detailedBtn.className).toContain('bg-indigo-600/20');

    const fastBtn = screen.getByRole('button', { name: /^fast$/i });
    fireEvent.click(fastBtn);
    expect(fastBtn.className).toContain('bg-indigo-600/20');
  });

  it('navigates directly to workspace overview when user clicks Open Video Workspace', () => {
    const mockOpenWorkspace = vi.fn();
    const mockClose = vi.fn();

    render(
      <PostImportModal
        isOpen={true}
        onClose={mockClose}
        projectId="proj_m24"
        asset={mockAsset}
        onOpenWorkspace={mockOpenWorkspace}
        onImportAnother={vi.fn()}
      />
    );

    const openWorkspaceBtn = screen.getByText('Open Video Workspace');
    fireEvent.click(openWorkspaceBtn);

    expect(mockClose).toHaveBeenCalledTimes(1);
    expect(mockOpenWorkspace).toHaveBeenCalledWith(mockAsset, 'overview');
  });

  it('triggers startMediaAnalysis when clicking Start Analysis', async () => {
    const analysisSpy = vi.spyOn(apiClient, 'startMediaAnalysis').mockResolvedValue({
      id: 'analysis_run_999',
      project_id: 'proj_m24',
      media_asset_id: 'asset_post_m24',
      status: 'running',
      progress_pct: 0,
      profile: 'balanced',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });

    render(
      <PostImportModal
        isOpen={true}
        onClose={vi.fn()}
        projectId="proj_m24"
        asset={mockAsset}
        onOpenWorkspace={vi.fn()}
        onImportAnother={vi.fn()}
      />
    );

    const startBtn = screen.getByRole('button', { name: /Start Analysis/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(analysisSpy).toHaveBeenCalledWith(
        'proj_m24',
        'asset_post_m24',
        'balanced',
        {},
        false
      );
    });
  });
});
