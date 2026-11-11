import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MediaLibraryView } from '../features/media/MediaLibraryView';
import { MediaAssetItem, MediaStorageStats, ProjectItem } from '../types/projects';
import * as apiClient from '../services/apiClient';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    importLocalMedia: vi.fn().mockResolvedValue({}),
    uploadMediaFile: vi.fn().mockResolvedValue({}),
    generateProxy: vi.fn().mockResolvedValue({}),
    regenerateThumbnail: vi.fn().mockResolvedValue({}),
    relinkMedia: vi.fn().mockResolvedValue({}),
    deleteMediaAsset: vi.fn().mockResolvedValue(undefined),
    getThumbnailUrl: vi.fn().mockReturnValue('/api/v1/projects/proj-1/media/med-1/thumbnail'),
    getProxyUrl: vi.fn().mockReturnValue('/api/v1/projects/proj-1/media/med-1/proxy'),
  };
});

describe('Feature View: MediaLibraryView', () => {
  const mockProjects: ProjectItem[] = [
    {
      id: 'proj-1',
      name: 'Alpha Video Project',
      description: 'Test project description',
      status: 'active',
      storage_subdir: 'proj-1-dir',
      project_config: {},
      created_at: '2026-11-11T10:00:00Z',
      updated_at: '2026-11-11T12:00:00Z',
      last_opened_at: null,
      archived_at: null,
    },
  ];

  const mockMedia: MediaAssetItem[] = [
    {
      id: 'med-1',
      project_id: 'proj-1',
      original_filename: 'camera_take_1.mp4',
      storage_path: 'D:\\Videos\\camera_take_1.mp4',
      is_external: true,
      media_type: 'video',
      file_size_bytes: 104857600, // 100 MB
      mime_type: 'video/mp4',
      duration_seconds: 125.4,
      width: 1920,
      height: 1080,
      fps: 30.0,
      video_codec: 'h264',
      audio_codec: 'aac',
      availability_status: 'present',
      proxy_reference_path: 'D:\\ZezEdit\\storage\\proxies\\med-1_proxy_480p.mp4',
      thumbnail_reference_path: 'D:\\ZezEdit\\storage\\thumbnails\\med-1.jpg',
      proxy_status: 'ready',
      metadata_status: 'extracted',
      metadata: {},
      created_at: '2026-11-11T10:05:00Z',
      updated_at: '2026-11-11T10:06:00Z',
    },
    {
      id: 'med-2',
      project_id: 'proj-1',
      original_filename: 'voiceover_track.wav',
      storage_path: 'D:\\ZezEdit\\storage\\media\\proj-1-dir\\voiceover_track.wav',
      is_external: false,
      media_type: 'audio',
      file_size_bytes: 20971520, // 20 MB
      mime_type: 'audio/wav',
      duration_seconds: 60.0,
      width: null,
      height: null,
      fps: null,
      video_codec: null,
      audio_codec: 'pcm_s16le',
      availability_status: 'present',
      proxy_reference_path: null,
      thumbnail_reference_path: null,
      proxy_status: 'none',
      metadata_status: 'extracted',
      metadata: {},
      created_at: '2026-11-11T10:10:00Z',
      updated_at: '2026-11-11T10:10:00Z',
    },
    {
      id: 'med-3',
      project_id: 'proj-1',
      original_filename: 'missing_clip.mov',
      storage_path: 'E:\\ExternalDrive\\missing_clip.mov',
      is_external: true,
      media_type: 'video',
      file_size_bytes: 52428800,
      mime_type: 'video/quicktime',
      duration_seconds: 45.0,
      width: 1280,
      height: 720,
      fps: 24.0,
      video_codec: 'prores',
      audio_codec: 'pcm_s16le',
      availability_status: 'missing',
      proxy_reference_path: null,
      thumbnail_reference_path: null,
      proxy_status: 'none',
      metadata_status: 'extracted',
      metadata: {},
      created_at: '2026-11-11T10:15:00Z',
      updated_at: '2026-11-11T10:15:00Z',
    },
  ];

  const mockStats: MediaStorageStats = {
    project_id: 'proj-1',
    total_media_count: 3,
    total_media_bytes: 178257920,
    total_proxy_bytes: 15728640,
    total_thumbnail_bytes: 204800,
    managed_files_count: 1,
    external_files_count: 2,
  };

  it('renders media metrics and assets in grid view', () => {
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText('Media Library')).toBeInTheDocument();
    expect(screen.getByText('camera_take_1.mp4')).toBeInTheDocument();
    expect(screen.getByText('voiceover_track.wav')).toBeInTheDocument();
    expect(screen.getByText('480p Ready')).toBeInTheDocument();
    expect(screen.getByText('Missing from Disk')).toBeInTheDocument();
  });

  it('filters media by media type tab', () => {
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={vi.fn()}
      />
    );

    // Filter to Audios
    const audioTab = screen.getByRole('button', { name: /audios/i });
    fireEvent.click(audioTab);

    expect(screen.getByText('voiceover_track.wav')).toBeInTheDocument();
    expect(screen.queryByText('camera_take_1.mp4')).not.toBeInTheDocument();

    // Filter to Videos
    const videoTab = screen.getByRole('button', { name: /videos/i });
    fireEvent.click(videoTab);

    expect(screen.getByText('camera_take_1.mp4')).toBeInTheDocument();
    expect(screen.queryByText('voiceover_track.wav')).not.toBeInTheDocument();
  });

  it('filters media by live search input', () => {
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={vi.fn()}
      />
    );

    const searchInput = screen.getByRole('searchbox');
    fireEvent.change(searchInput, { target: { value: 'camera' } });

    expect(screen.getByText('camera_take_1.mp4')).toBeInTheDocument();
    expect(screen.queryByText('voiceover_track.wav')).not.toBeInTheDocument();
    expect(screen.queryByText('missing_clip.mov')).not.toBeInTheDocument();
  });

  it('switches between grid and list view mode', () => {
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={vi.fn()}
      />
    );

    const listViewBtn = screen.getByTitle('List View');
    fireEvent.click(listViewBtn);

    // List view table headers
    expect(screen.getByText('Format / Codec')).toBeInTheDocument();
    expect(screen.getByText('Storage')).toBeInTheDocument();
    expect(screen.getAllByText('External')[0]).toBeInTheDocument();
  });

  it('opens import dialog and triggers local path import', async () => {
    const handleRefresh = vi.fn();
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={handleRefresh}
      />
    );

    const importBtn = screen.getByRole('button', { name: /import media/i });
    fireEvent.click(importBtn);

    expect(screen.getByText('Import Media to Project')).toBeInTheDocument();

    const pathInput = screen.getByLabelText(/absolute file path on disk/i);
    fireEvent.change(pathInput, { target: { value: 'D:\\Videos\\new_clip.mp4' } });

    const submitBtn = screen.getByRole('button', { name: /import file/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.importLocalMedia).toHaveBeenCalledWith('proj-1', {
        file_path: 'D:\\Videos\\new_clip.mp4',
        copy_to_storage: false,
        generate_proxy: false,
        generate_thumbnail: true,
      });
    });
  });

  it('opens asset details dialog when clicking Details', () => {
    render(
      <MediaLibraryView
        projects={mockProjects}
        currentProjectId="proj-1"
        onSelectProject={vi.fn()}
        media={mockMedia}
        stats={mockStats}
        loading={false}
        onRefresh={vi.fn()}
      />
    );

    const detailBtns = screen.getAllByRole('button', { name: /details/i });
    fireEvent.click(detailBtns[0]);

    expect(screen.getByText('Resolution')).toBeInTheDocument();
    expect(screen.getByText('1920x1080')).toBeInTheDocument();
    expect(screen.getByText('Storage Path:')).toBeInTheDocument();
  });
});
