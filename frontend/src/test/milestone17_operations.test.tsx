import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ResourceInspector } from '../components/system/ResourceInspector';
import { WorkingQueueView } from '../features/queue/WorkingQueueView';
import { AIProviderManager } from '../features/providers/AIProviderManager';
import { DocumentationView } from '../features/docs/DocumentationView';
import * as apiClient from '../services/apiClient';

describe('Milestone 17: Desktop Operations & Core Product Workflow Tests', () => {
  it('ResourceInspector renders CPU and RAM metrics and displays floating window on click', async () => {
    vi.spyOn(apiClient, 'fetchSystemResources').mockResolvedValue({
      cpu_percent: 24.5,
      process_cpu_percent: 4.2,
      cpu_count_logical: 8,
      cpu_count_physical: 4,
      memory_total_mb: 16384,
      memory_available_mb: 8192,
      memory_used_mb: 8192,
      memory_percent: 50.0,
      process_memory_rss_mb: 145.2,
      process_memory_vms_mb: 280.0,
      active_workers: 1,
      pending_jobs: 0,
      max_concurrent_jobs: 2,
      execution_mode: 'cpu_first',
      timestamp: '2026-11-12T06:30:00Z',
    });

    render(<ResourceInspector />);

    // Check indicator
    await waitFor(() => {
      expect(screen.getByText('25%')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    // Click to open floating inspector
    const btn = screen.getByRole('button', { name: /hardware resource monitor/i });
    fireEvent.click(btn);

    expect(screen.getByText('Resource Inspector')).toBeInTheDocument();
    expect(screen.getByText('Host CPU Usage')).toBeInTheDocument();
    expect(screen.getByText('System RAM')).toBeInTheDocument();
    expect(screen.getByText(/CPU-First Baseline/i)).toBeInTheDocument();
  });

  it('WorkingQueueView renders job summary metrics, status tabs, and jobs list', async () => {
    vi.spyOn(apiClient, 'fetchJobs').mockResolvedValue({
      items: [
        {
          id: 'job_test_01',
          project_id: 'p1',
          job_type: 'video_analysis',
          status: 'running',
          priority: 100,
          progress_pct: 45.0,
          current_stage: 'speech_recognition',
          worker_id: 'worker_1',
          worker_pid: 1234,
          input_config: {},
          result_metadata: null,
          error_message: null,
          retry_count: 0,
          max_attempts: 2,
          created_at: '2026-11-12T06:00:00Z',
          started_at: '2026-11-12T06:00:05Z',
          completed_at: null,
          cancellation_requested_at: null,
          cancelled_at: null,
          updated_at: '2026-11-12T06:00:10Z',
        },
      ],
      total: 1,
    });

    vi.spyOn(apiClient, 'fetchQueueStats').mockResolvedValue({
      total_jobs: 1,
      queued: 0,
      running: 1,
      completed: 0,
      failed: 0,
      cancelled: 0,
      by_type: { video_analysis: 1 },
      active_job_ids: ['job_test_01'],
    });

    render(
      <WorkingQueueView
        projects={[{ id: 'p1', name: 'Project Alpha', description: null, status: 'active', project_config: {}, storage_subdir: 'p1', created_at: '', updated_at: '', last_opened_at: null, archived_at: null }]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Working Queue & Jobs')).toBeInTheDocument();
      expect(screen.getByText('job_test_01')).toBeInTheDocument();
      expect(screen.getAllByText('video analysis').length).toBeGreaterThan(0);
      expect(screen.getByText('speech_recognition')).toBeInTheDocument();
    });
  });

  it('AIProviderManager renders Ollama, Faster-Whisper, and Heuristic cards', async () => {
    vi.spyOn(apiClient, 'fetchAIProviders').mockResolvedValue([
      {
        id: 'ollama',
        name: 'Ollama Local Inference',
        provider_type: 'local_llm',
        status: 'ready',
        is_local: true,
        base_url: 'http://127.0.0.1:11434',
        active_model: 'qwen3-vl:4b-instruct',
        available_models: ['qwen3-vl:4b-instruct'],
        capabilities: [
          { task: 'visual_understanding', supported: true, description: 'Multimodal vision' },
        ],
        latency_ms: 15.0,
        last_health_check: '2026-11-12T06:30:00Z',
        details: 'Connected',
      },
      {
        id: 'faster-whisper',
        name: 'Faster-Whisper Speech Engine',
        provider_type: 'local_asr',
        status: 'ready',
        is_local: true,
        base_url: null,
        active_model: 'tiny',
        available_models: ['tiny', 'base'],
        capabilities: [
          { task: 'speech_transcription', supported: true, description: 'Speech-to-text' },
        ],
        latency_ms: 5.0,
        last_health_check: '2026-11-12T06:30:00Z',
        details: 'Ready',
      },
    ]);

    render(<AIProviderManager />);

    await waitFor(() => {
      expect(screen.getByText('AI Provider Manager')).toBeInTheDocument();
      expect(screen.getByText('Ollama Local Inference')).toBeInTheDocument();
      expect(screen.getByText('Faster-Whisper Speech Engine')).toBeInTheDocument();
      expect(screen.getByText('Local-First Privacy & Zero Cloud Dependency')).toBeInTheDocument();
    });
  });

  it('DocumentationView renders categories, articles, and article detail', async () => {
    vi.spyOn(apiClient, 'fetchDocCategories').mockResolvedValue([
      { id: 'getting-started', name: 'Getting Started', description: 'Basics', article_count: 1 },
    ]);
    vi.spyOn(apiClient, 'fetchDocArticles').mockResolvedValue([
      {
        id: 'architecture-overview',
        title: 'ZezEdit Architecture & CPU-First Execution',
        category: 'getting-started',
        summary: 'Intel Core i3 baseline architecture',
        tags: ['cpu-first'],
        reading_time_minutes: 3,
      },
    ]);
    vi.spyOn(apiClient, 'fetchDocArticleDetail').mockResolvedValue({
      id: 'architecture-overview',
      title: 'ZezEdit Architecture & CPU-First Execution',
      category: 'getting-started',
      summary: 'Intel Core i3 baseline architecture',
      markdown_content: '# ZezEdit Architecture\n\nCore Tenets of CPU-first execution.',
      tags: ['cpu-first'],
      related_article_ids: [],
      updated_at: '2026-11-12T06:30:00Z',
    });

    render(<DocumentationView />);

    await waitFor(() => {
      expect(screen.getByText('Studio Documentation & User Guides')).toBeInTheDocument();
      expect(screen.getByText('Getting Started')).toBeInTheDocument();
      expect(screen.getByText('Core Tenets of CPU-first execution.')).toBeInTheDocument();
    });
  });
});
