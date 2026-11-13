import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { ProcessesManagerView } from '../features/queue/WorkingQueueView';
import * as apiClient from '../services/apiClient';
import { JobItem } from '../types/projects';
import { QueueStats, JobLogs } from '../types/system';

describe('ProcessesManagerView / WorkingQueueView', () => {
  const mockJobs: JobItem[] = [
    {
      id: 'job_001_run',
      project_id: 'default',
      media_asset_id: 'asset_vid_1',
      video_title: 'Keynote_Presentation.mp4',
      job_type: 'analyze_video',
      status: 'running',
      priority: 100,
      progress_pct: 45.0,
      current_stage: 'whisper_transcription',
      worker_id: 'worker_proc_1',
      worker_pid: 1234,
      input_config: { media_asset_id: 'asset_vid_1' },
      result_metadata: null,
      error_message: null,
      retry_count: 0,
      max_attempts: 2,
      created_at: '2026-11-13T08:00:00Z',
      started_at: '2026-11-13T08:00:05Z',
      completed_at: null,
      cancellation_requested_at: null,
      cancelled_at: null,
      updated_at: '2026-11-13T08:01:00Z',
      elapsed_seconds: 55,
      estimated_remaining_seconds: 60,
    },
    {
      id: 'job_002_fail',
      project_id: 'default',
      media_asset_id: 'asset_vid_2',
      video_title: 'Podcast_Episode_12.mp4',
      job_type: 'export_mp4',
      status: 'failed',
      priority: 150,
      progress_pct: 12.0,
      current_stage: 'rendering_ffmpeg',
      worker_id: 'worker_proc_2',
      worker_pid: null,
      input_config: { media_asset_id: 'asset_vid_2' },
      result_metadata: null,
      error_message: 'FFmpeg exit code 1: Invalid pixel format',
      retry_count: 0,
      max_attempts: 2,
      created_at: '2026-11-13T07:30:00Z',
      started_at: '2026-11-13T07:30:02Z',
      completed_at: '2026-11-13T07:30:15Z',
      cancellation_requested_at: null,
      cancelled_at: null,
      updated_at: '2026-11-13T07:30:15Z',
      elapsed_seconds: 13,
      estimated_remaining_seconds: null,
    },
    {
      id: 'job_003_done',
      project_id: 'default',
      media_asset_id: 'asset_vid_1',
      video_title: 'Keynote_Presentation.mp4',
      job_type: 'generate_proxy',
      status: 'completed',
      priority: 50,
      progress_pct: 100.0,
      current_stage: 'completed',
      worker_id: 'worker_proc_3',
      worker_pid: null,
      input_config: { media_asset_id: 'asset_vid_1' },
      result_metadata: { proxy_path: 'storage/proxies/vid1.mp4' },
      error_message: null,
      retry_count: 0,
      max_attempts: 2,
      created_at: '2026-11-13T07:00:00Z',
      started_at: '2026-11-13T07:00:02Z',
      completed_at: '2026-11-13T07:00:20Z',
      cancellation_requested_at: null,
      cancelled_at: null,
      updated_at: '2026-11-13T07:00:20Z',
      elapsed_seconds: 18,
      estimated_remaining_seconds: 0,
    },
  ];

  const mockStats: QueueStats = {
    total_jobs: 3,
    running: 1,
    queued: 0,
    completed: 1,
    failed: 1,
    cancelled: 0,
    by_type: {
      analyze_video: 1,
      export_mp4: 1,
      generate_proxy: 1,
    },
    active_job_ids: ['job_001_run'],
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'fetchJobs').mockResolvedValue({ items: mockJobs, total: mockJobs.length });
    vi.spyOn(apiClient, 'fetchQueueStats').mockResolvedValue(mockStats);
    const mockLogs: JobLogs = {
      job_id: 'job_001_run',
      job_type: 'analyze_video',
      status: 'running',
      progress_percent: 45,
      current_stage: 'whisper_transcription',
      logs: [
        '2026-11-13T08:00:05Z [INFO] Initializing video analysis',
        '2026-11-13T08:00:10Z [INFO] Demuxing audio stream',
        '2026-11-13T08:00:20Z [INFO] Running Whisper speech transcription',
      ],
      error_message: null,
      created_at: '2026-11-13T08:00:00Z',
      started_at: '2026-11-13T08:00:05Z',
      completed_at: null,
    };
    vi.spyOn(apiClient, 'fetchJobLogs').mockResolvedValue(mockLogs);
    vi.spyOn(apiClient, 'cancelJob').mockResolvedValue({ ...mockJobs[0], status: 'cancelled' });
    vi.spyOn(apiClient, 'retryJob').mockResolvedValue({
      ...mockJobs[1],
      id: 'job_002_fail_attempt2',
      parent_job_id: 'job_002_fail',
      status: 'queued',
      retry_count: 1,
    });
    vi.spyOn(apiClient, 'deleteJob').mockResolvedValue({ status: 'success', deleted_job_id: 'job_003_done' });
    vi.spyOn(apiClient, 'deleteJobHistory').mockResolvedValue({ status: 'success', deleted_count: 1 });
    window.confirm = vi.fn().mockReturnValue(true);
  });

  it('renders Central Process Manager title and summary cards correctly', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Processes' })).toBeInTheDocument();
      expect(screen.getByText('Central Process Manager')).toBeInTheDocument();
    });

    // Metric Summary Cards
    expect(screen.getByText('Total Processes')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // total jobs
    expect(screen.getAllByText('analyze video').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Keynote_Presentation.mp4').length).toBeGreaterThan(0);
  });

  it('filters processes by Category', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByText('job_001_run')).toBeInTheDocument();
    });

    // Filter to Rendering (in Table, analyze video row job_001_run disappears and export mp4 row job_002_fail remains)
    const renderingBtn = screen.getByRole('button', { name: 'Rendering' });
    fireEvent.click(renderingBtn);

    await waitFor(() => {
      expect(screen.getByText('job_002_fail')).toBeInTheDocument();
      expect(screen.queryByText('job_001_run')).not.toBeInTheDocument();
    });
  });

  it('filters processes by Status', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByText('job_001_run')).toBeInTheDocument();
    });

    // Filter by 'failed' (job_001_run disappears, job_002_fail remains)
    const failedBtn = screen.getByRole('button', { name: 'failed' });
    fireEvent.click(failedBtn);

    await waitFor(() => {
      expect(screen.getByText('job_002_fail')).toBeInTheDocument();
      expect(screen.queryByText('job_001_run')).not.toBeInTheDocument();
    });
  });

  it('filters processes by search query', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByText('job_001_run')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by ID, type, video, or stage...');
    fireEvent.change(searchInput, { target: { value: 'Podcast' } });

    await waitFor(() => {
      expect(screen.getByText('job_002_fail')).toBeInTheDocument();
      expect(screen.queryByText('job_001_run')).not.toBeInTheDocument();
    });
  });

  it('opens process details drawer and displays logs', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Inspect Details & Logs').length).toBeGreaterThan(0);
    });

    // Click on inspect logs button for first job
    const inspectBtns = screen.getAllByTitle('Inspect Details & Logs');
    fireEvent.click(inspectBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Process Details & Execution Trace')).toBeInTheDocument();
      expect(screen.getByText('ID: job_001_run')).toBeInTheDocument();
      expect(screen.getByText(/Running Whisper speech transcription/i)).toBeInTheDocument();
    });
  });

  it('triggers process cancellation on running process', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByTitle('Stop / Cancel Process (Terminates worker subprocess tree)')).toBeInTheDocument();
    });

    const cancelBtn = screen.getByTitle('Stop / Cancel Process (Terminates worker subprocess tree)');
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(apiClient.cancelJob).toHaveBeenCalledWith('job_001_run');
    });
  });

  it('triggers process retry creating new attempt', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByTitle('Retry Process (Creates new attempt linked to this run)')).toBeInTheDocument();
    });

    const retryBtn = screen.getByTitle('Retry Process (Creates new attempt linked to this run)');
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(apiClient.retryJob).toHaveBeenCalledWith('job_002_fail', true);
    });
  });

  it('triggers delete process record', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getAllByTitle('Delete Process Record (Does not delete source video or media)').length).toBeGreaterThan(0);
    });

    const deleteBtns = screen.getAllByTitle('Delete Process Record (Does not delete source video or media)');
    fireEvent.click(deleteBtns[deleteBtns.length - 1]);

    await waitFor(() => {
      expect(apiClient.deleteJob).toHaveBeenCalledWith('job_003_done');
    });
  });

  it('triggers clear completed history', async () => {
    render(<ProcessesManagerView />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Clear Completed History/i })).toBeInTheDocument();
    });

    const clearHistoryBtn = screen.getByRole('button', { name: /Clear Completed History/i });
    fireEvent.click(clearHistoryBtn);

    await waitFor(() => {
      expect(apiClient.deleteJobHistory).toHaveBeenCalledWith('completed');
    });
  });
});
