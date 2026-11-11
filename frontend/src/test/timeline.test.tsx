import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TimelineEditor } from '../features/timeline/TimelineEditor';
import * as apiClient from '../services/apiClient';
import { TimelineRecord, TimelineHistoryResponse, AIConversation } from '../types/timeline';
import { ProjectItem } from '../types/projects';

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClient>('../services/apiClient');
  return {
    ...actual,
    fetchTimeline: vi.fn(),
    fetchTimelineHistory: vi.fn(),
    fetchAIConversation: vi.fn(),
    fetchProjectMedia: vi.fn(),
    undoTimeline: vi.fn(),
    redoTimeline: vi.fn(),
    splitTimelineClip: vi.fn(),
    deleteTimelineClip: vi.fn(),
    duplicateTimelineClip: vi.fn(),
    sendAIMessage: vi.fn(),
    approveAIPlan: vi.fn(),
    rejectAIPlan: vi.fn(),
    renderTimeline: vi.fn(),
  };
});

const mockProject: ProjectItem = {
  id: 'p_test',
  name: 'Test Timeline Project',
  description: 'Test project description',
  status: 'active',
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

const mockTimeline: TimelineRecord = {
  id: 'tl_1',
  project_id: 'p_test',
  name: 'Main Sequence',
  duration: 8.0,
  fps: 30,
  canvas_width: 1080,
  canvas_height: 1920,
  time_base: '1/30',
  revision: 3,
  is_active: true,
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
  tracks: [
    {
      id: 'tr_v2',
      timeline_id: 'tl_1',
      name: 'V2 - Overlays',
      track_type: 'overlay',
      track_subtype: 'text',
      track_order: 0,
      is_visible: true,
      is_muted: false,
      is_locked: false,
      height: 56,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
      clips: [
        {
          id: 'cl_txt_1',
          timeline_id: 'tl_1',
          track_id: 'tr_v2',
          source_media_id: null,
          clip_type: 'text',
          name: 'Text: Subscribe',
          timeline_start: 1.0,
          timeline_end: 4.0,
          source_in: 0.0,
          source_out: 0.0,
          speed: 1.0,
          volume: 1.0,
          opacity: 1.0,
          transform_props: { x: 0, y: 0, scale: 1, rotation: 0 },
          content_props: { text: 'Subscribe Now!', font_family: 'Arial', font_size: 48, color: '#FFFFFF', alignment: 'center' },
          audio_props: { fade_in: 0, fade_out: 0, is_muted: false },
          created_at: '2026-11-12T00:00:00Z',
          updated_at: '2026-11-12T00:00:00Z',
        },
      ],
    },
    {
      id: 'tr_v1',
      timeline_id: 'tl_1',
      name: 'V1 - Main Video',
      track_type: 'video',
      track_subtype: 'main_video',
      track_order: 1,
      is_visible: true,
      is_muted: false,
      is_locked: false,
      height: 72,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
      clips: [
        {
          id: 'cl_vid_1',
          timeline_id: 'tl_1',
          track_id: 'tr_v1',
          source_media_id: 'm_1',
          clip_type: 'video',
          name: 'Opening Shot',
          timeline_start: 0.0,
          timeline_end: 8.0,
          source_in: 0.0,
          source_out: 8.0,
          speed: 1.0,
          volume: 1.0,
          opacity: 1.0,
          transform_props: { x: 0, y: 0, scale: 1, rotation: 0 },
          content_props: { text: '', font_family: 'Arial', font_size: 48, color: '#FFFFFF', alignment: 'center' },
          audio_props: { fade_in: 0, fade_out: 0, is_muted: false },
          created_at: '2026-11-12T00:00:00Z',
          updated_at: '2026-11-12T00:00:00Z',
        },
      ],
    },
  ],
};

const mockHistory: TimelineHistoryResponse = {
  timeline_id: 'tl_1',
  current_revision: 3,
  can_undo: true,
  can_redo: false,
  history: [],
};

const mockAIConversation: AIConversation = {
  id: 'conv_1',
  project_id: 'p_test',
  timeline_id: 'tl_1',
  title: 'AI Video Editor',
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
  messages: [
    {
      id: 'msg_1',
      conversation_id: 'conv_1',
      role: 'user',
      content: 'Shorten opening shot',
      context_snapshot: {},
      created_at: '2026-11-12T00:00:00Z',
    },
    {
      id: 'msg_2',
      conversation_id: 'conv_1',
      role: 'assistant',
      content: 'I generated a trim plan:',
      context_snapshot: {},
      plan: {
        id: 'plan_1',
        conversation_id: 'conv_1',
        project_id: 'p_test',
        timeline_id: 'tl_1',
        target_revision: 3,
        user_instruction: 'Shorten opening shot',
        explanation: 'Trims 2 seconds from the end of the opening shot.',
        operations: [
          {
            command_type: 'TrimClip',
            description: "Trim 'Opening Shot' to 6.0s",
            parameters: { clip_id: 'cl_vid_1', new_timeline_end: 6.0 },
          },
        ],
        warnings: ['Reduces clip length on timeline.'],
        status: 'proposed',
        created_at: '2026-11-12T00:00:00Z',
      },
      created_at: '2026-11-12T00:00:01Z',
    },
  ],
};

describe('TimelineEditor Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.fetchTimeline).mockResolvedValue(mockTimeline);
    vi.mocked(apiClient.fetchTimelineHistory).mockResolvedValue(mockHistory);
    vi.mocked(apiClient.fetchAIConversation).mockResolvedValue(mockAIConversation);
    vi.mocked(apiClient.fetchProjectMedia).mockResolvedValue({ items: [], count: 0 });
  });

  it('renders sequence header, tracks, and clips', async () => {
    render(<TimelineEditor currentProject={mockProject} />);

    await waitFor(() => {
      expect(screen.getByText('Main Sequence')).toBeInTheDocument();
      expect(screen.getByText('Rev 3')).toBeInTheDocument();
      expect(screen.getByText('V1 - Main Video')).toBeInTheDocument();
      expect(screen.getByText('V2 - Overlays')).toBeInTheDocument();
      expect(screen.getByText('Opening Shot')).toBeInTheDocument();
      expect(screen.getByText('Text: Subscribe')).toBeInTheDocument();
    });
  });

  it('allows clip selection and opens properties inspector', async () => {
    render(<TimelineEditor currentProject={mockProject} />);

    await waitFor(() => {
      expect(screen.getByText('Opening Shot')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Opening Shot'));

    await waitFor(() => {
      expect(screen.getByText('Clip Name')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Opening Shot')).toBeInTheDocument();
      expect(screen.getByText('Audio Volume')).toBeInTheDocument();
      expect(screen.getByText('Playback Speed')).toBeInTheDocument();
    });
  });

  it('triggers Undo and Redo operations through command history', async () => {
    vi.mocked(apiClient.undoTimeline).mockResolvedValue({
      ...mockTimeline,
      revision: 4,
    });

    render(<TimelineEditor currentProject={mockProject} />);

    await waitFor(() => {
      expect(screen.getByTitle('Undo (Ctrl+Z)')).toBeInTheDocument();
    });

    const undoBtn = screen.getByTitle('Undo (Ctrl+Z)');
    expect(undoBtn).not.toBeDisabled();

    fireEvent.click(undoBtn);

    await waitFor(() => {
      expect(apiClient.undoTimeline).toHaveBeenCalledWith('p_test', 'tl_1');
    });
  });

  it('renders AI Assistant tab with proposed editing plan and handles approval', async () => {
    vi.mocked(apiClient.approveAIPlan).mockResolvedValue({
      ...mockTimeline,
      revision: 4,
    });

    render(<TimelineEditor currentProject={mockProject} />);

    await waitFor(() => {
      expect(screen.getByText('AI Editor')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('AI Editor'));

    await waitFor(() => {
      expect(screen.getByText('Proposed Editing Plan')).toBeInTheDocument();
      expect(screen.getByText('Trims 2 seconds from the end of the opening shot.')).toBeInTheDocument();
      expect(screen.getByText('• Trim \'Opening Shot\' to 6.0s')).toBeInTheDocument();
      expect(screen.getByText('Approve & Execute')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Approve & Execute'));

    await waitFor(() => {
      expect(apiClient.approveAIPlan).toHaveBeenCalledWith('p_test', 'tl_1', 'plan_1');
    });
  });

  it('triggers timeline video rendering', async () => {
    vi.mocked(apiClient.renderTimeline).mockResolvedValue({
      job_id: 'job_render_1',
      timeline_id: 'tl_1',
      status: 'queued',
      message: 'Timeline render enqueued',
    });

    render(<TimelineEditor currentProject={mockProject} />);

    await waitFor(() => {
      expect(screen.getByText('Render Video')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Render Video'));

    await waitFor(() => {
      expect(apiClient.renderTimeline).toHaveBeenCalledWith('p_test', 'tl_1', {
        preset_id: 'shorts_reels_9_16',
        title: 'Main Sequence Render',
      });
      expect(screen.getByText(/Render job enqueued/i)).toBeInTheDocument();
    });
  });
});
