import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CharacterStudio } from '../features/characters/CharacterStudio';
import * as apiClient from '../services/apiClient';
import {
  CharacterCandidate,
  CharacterExportPayload,
  CharacterProfile,
} from '../types/character';
import { MediaAssetItem } from '../types/projects';

// Mock apiClient functions
vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClient>('../services/apiClient');
  return {
    ...actual,
    getCharacterCandidates: vi.fn(),
    getCharacterLibrary: vi.fn(),
    runCharacterExtraction: vi.fn(),
    renameCharacterCandidate: vi.fn(),
    confirmCharacterCandidate: vi.fn(),
    mergeCharacterCandidates: vi.fn(),
    splitCharacterCandidate: vi.fn(),
    detachCharacterObservation: vi.fn(),
    rejectCharacterCandidate: vi.fn(),
    exportCharacterJson: vi.fn(),
  };
});

describe('CharacterStudio Component (Milestone 10)', () => {
  const mockMediaAssets: MediaAssetItem[] = [
    {
      id: 'med_test_1',
      project_id: 'p_test',
      original_filename: 'interview_clip.mp4',
      storage_path: '/storage/interview_clip.mp4',
      is_external: false,
      media_type: 'video',
      file_size_bytes: 5242880,
      mime_type: 'video/mp4',
      duration_seconds: 60.0,
      width: 1920,
      height: 1080,
      fps: 30,
      video_codec: 'h264',
      audio_codec: 'aac',
      availability_status: 'present',
      proxy_reference_path: null,
      thumbnail_reference_path: null,
      proxy_status: 'none',
      metadata_status: 'ready',
      metadata: {},
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    },
  ];

  const mockCandidates: CharacterCandidate[] = [
    {
      id: 'cand_1',
      job_id: 'job_1',
      project_id: 'p_test',
      label: 'Candidate #1',
      review_status: 'provisional',
      confirmed_character_id: null,
      observation_count: 2,
      sampled_screen_time_seconds: 2.0,
      estimated_screen_time_seconds: 3.5,
      representative_thumbnail_path: '/storage/characters/p_test/thumbs/obs_1.jpg',
      detection_methodology: 'opencv_haar_spatial_temporal',
      clustering_confidence: 0.85,
      notes: 'Provisional group',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
      observations: [
        {
          id: 'obs_1',
          candidate_id: 'cand_1',
          job_id: 'job_1',
          project_id: 'p_test',
          media_asset_id: 'med_test_1',
          timestamp: 1.0,
          frame_path: '/storage/f1.jpg',
          thumbnail_path: '/storage/t1.jpg',
          bounding_box: { x: 100, y: 50, width: 80, height: 90 },
          detection_type: 'face',
          confidence: 0.88,
          detection_method: 'opencv_haar',
          unverified_dialogue: '[Temporal Dialogue]: "Hello and welcome" (Unverified Speaker)',
          is_detached: false,
          created_at: '2026-11-12T00:00:00Z',
        },
        {
          id: 'obs_2',
          candidate_id: 'cand_1',
          job_id: 'job_1',
          project_id: 'p_test',
          media_asset_id: 'med_test_1',
          timestamp: 2.0,
          frame_path: '/storage/f2.jpg',
          thumbnail_path: '/storage/t2.jpg',
          bounding_box: { x: 110, y: 55, width: 85, height: 95 },
          detection_type: 'face',
          confidence: 0.82,
          detection_method: 'opencv_haar',
          unverified_dialogue: null,
          is_detached: false,
          created_at: '2026-11-12T00:00:00Z',
        },
      ],
    },
    {
      id: 'cand_2',
      job_id: 'job_1',
      project_id: 'p_test',
      label: 'Candidate #2',
      review_status: 'provisional',
      confirmed_character_id: null,
      observation_count: 1,
      sampled_screen_time_seconds: 1.0,
      estimated_screen_time_seconds: 1.0,
      representative_thumbnail_path: null,
      detection_methodology: 'opencv_haar_spatial_temporal',
      clustering_confidence: 0.75,
      notes: 'Second group',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
      observations: [],
    },
  ];

  const mockProfiles: CharacterProfile[] = [
    {
      id: 'char_prof_1',
      project_id: 'p_test',
      name: 'Dr. Sarah Connor',
      avatar_path: '/storage/avatar1.jpg',
      biography: 'Lead robotics specialist',
      appearance_tags: ['glasses', 'lab coat', 'expert'],
      total_appearances: 3,
      total_screen_time_seconds: 45.5,
      metadata_json: {},
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.getCharacterCandidates).mockResolvedValue(mockCandidates);
    vi.mocked(apiClient.getCharacterLibrary).mockResolvedValue(mockProfiles);
  });

  it('renders extraction studio with disclaimer banner and candidate list', async () => {
    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getByText('Character Extraction Studio')).toBeInTheDocument();
      expect(screen.getByText(/Transparency Notice/i)).toBeInTheDocument();
      expect(screen.getAllByText('Candidate #1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Candidate #2')).toBeInTheDocument();
    });
  });

  it('displays candidate details, screen time breakdown, and dialogue observations', async () => {
    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getByText('Sampled Frames Screen Time')).toBeInTheDocument();
      expect(screen.getByText('2.0s')).toBeInTheDocument();
      expect(screen.getByText('3.5s')).toBeInTheDocument();
      expect(screen.getByText(/Hello and welcome/i)).toBeInTheDocument();
    });
  });

  it('supports inline candidate renaming', async () => {
    vi.mocked(apiClient.renameCharacterCandidate).mockResolvedValue({
      ...mockCandidates[0],
      label: 'Host Alex',
    });

    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getAllByText('Candidate #1').length).toBeGreaterThanOrEqual(1);
    });

    const editButtons = screen.getAllByTitle('Rename candidate');
    fireEvent.click(editButtons[0]);

    const input = screen.getByPlaceholderText('Enter character name...');
    fireEvent.change(input, { target: { value: 'Host Alex' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(apiClient.renameCharacterCandidate).toHaveBeenCalledWith('p_test', 'cand_1', 'Host Alex');
    });
  });

  it('opens confirmation modal and saves to Character Library', async () => {
    vi.mocked(apiClient.confirmCharacterCandidate).mockResolvedValue({
      id: 'char_new',
      project_id: 'p_test',
      name: 'Confirmed Host',
      avatar_path: null,
      biography: 'Host of the program',
      appearance_tags: ['host', 'suit'],
      total_appearances: 1,
      total_screen_time_seconds: 2.0,
      metadata_json: {},
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });

    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getByText('Confirm to Library')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Confirm to Library'));

    // Check modal opened
    expect(screen.getByPlaceholderText('e.g. Host Alex')).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText('e.g. Host Alex');
    fireEvent.change(nameInput, { target: { value: 'Confirmed Host' } });

    const confirmButtons = screen.getAllByText('Confirm Character');
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(apiClient.confirmCharacterCandidate).toHaveBeenCalledWith(
        'p_test',
        'cand_1',
        expect.objectContaining({ name: 'Confirmed Host' })
      );
    });
  });

  it('switches to Character Library tab and renders verified profiles and tags', async () => {
    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getByText(/Character Library \(1\)/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Character Library \(1\)/i));

    await waitFor(() => {
      expect(screen.getByText('Dr. Sarah Connor')).toBeInTheDocument();
      expect(screen.getByText('Lead robotics specialist')).toBeInTheDocument();
      expect(screen.getByText('glasses')).toBeInTheDocument();
      expect(screen.getByText('45.5s')).toBeInTheDocument();
    });
  });

  it('exports character metadata as documented JSON payload', async () => {
    const mockExportPayload: CharacterExportPayload = {
      export_version: '2.0.0',
      exported_at: '2026-11-12T00:00:00Z',
      profile: mockProfiles[0],
      associated_candidates: [],
      screen_time_summary: {
        total_appearances: 3,
        total_screen_time_seconds: 45.5,
        candidate_clusters_count: 1,
      },
      disclaimer: 'ZezEdit 2.0 Character Studio metadata.',
    };

    vi.mocked(apiClient.exportCharacterJson).mockResolvedValue(mockExportPayload);

    render(<CharacterStudio projectId="p_test" mediaAssets={mockMediaAssets} />);

    await waitFor(() => {
      expect(screen.getByText(/Character Library \(1\)/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Character Library \(1\)/i));

    await waitFor(() => {
      expect(screen.getByText('Export JSON')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Export JSON'));

    await waitFor(() => {
      expect(apiClient.exportCharacterJson).toHaveBeenCalledWith('p_test', 'char_prof_1');
      expect(screen.getByText(/Character Export JSON \(Dr\. Sarah Connor\)/i)).toBeInTheDocument();
      expect(screen.getByText('Download File')).toBeInTheDocument();
    });
  });
});
