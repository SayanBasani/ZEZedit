import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { ResourceInspector } from '../components/system/ResourceInspector';
import { WorkingQueueView } from '../features/queue/WorkingQueueView';
import { AIProviderManager } from '../features/providers/AIProviderManager';
import { DocumentationView } from '../features/docs/DocumentationView';
import * as apiClient from '../services/apiClient';
import { JobItem } from '../types/projects';

describe('Milestone 19: Desktop Operations Center & Supporting Utilities', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('ResourceInspector Component', () => {
    it('renders CPU and RAM indicator and handles pin and Escape key dismiss', async () => {
      vi.spyOn(apiClient, 'fetchSystemResources').mockResolvedValue({
        cpu_percent: 24.5,
        process_cpu_percent: 3.2,
        cpu_count_logical: 12,
        cpu_count_physical: 8,
        memory_total_mb: 16384,
        memory_available_mb: 8192,
        memory_used_mb: 8192,
        memory_percent: 50.0,
        process_memory_rss_mb: 180,
        process_memory_vms_mb: 400,
        active_workers: 1,
        pending_jobs: 0,
        max_concurrent_jobs: 2,
        execution_mode: 'cpu_first',
        timestamp: '2026-11-12T08:00:00Z',
      });

      render(<ResourceInspector />);

      // Verify indicator pill metrics
      await waitFor(() => {
        expect(screen.getByText('25%')).toBeInTheDocument();
        expect(screen.getByText('50%')).toBeInTheDocument();
        expect(screen.getByText('1w')).toBeInTheDocument();
      });

      // Click to open floating inspector
      const triggerBtn = screen.getByLabelText('Hardware resource monitor');
      fireEvent.click(triggerBtn);

      expect(screen.getByText('Resource Inspector')).toBeInTheDocument();
      expect(screen.getByText('Host CPU Usage')).toBeInTheDocument();
      expect(screen.getByText('System RAM')).toBeInTheDocument();
      expect(screen.getByText('CPU-First Baseline')).toBeInTheDocument();

      // Click pin button
      const pinBtn = screen.getByLabelText('Pin inspector window');
      fireEvent.click(pinBtn);
      expect(pinBtn).toHaveClass('text-indigo-400');

      // Press Escape key -> should dismiss
      fireEvent.keyDown(window, { key: 'Escape' });
      await waitFor(() => {
        expect(screen.queryByText('Host CPU Usage')).not.toBeInTheDocument();
      });
    });
  });

  describe('WorkingQueueView Component', () => {
    it('renders queue stats, distribution chart, task types, and filters jobs', async () => {
      const mockJobs: JobItem[] = [
        {
          id: 'job_01',
          project_id: 'proj_01',
          job_type: 'video_analysis',
          status: 'running',
          priority: 100,
          progress_pct: 45.0,
          current_stage: 'speech_recognition',
          worker_id: 'w1',
          worker_pid: 1234,
          input_config: {},
          result_metadata: null,
          error_message: null,
          retry_count: 0,
          max_attempts: 2,
          created_at: '2026-11-12T08:00:00Z',
          started_at: '2026-11-12T08:00:05Z',
          completed_at: null,
          cancellation_requested_at: null,
          cancelled_at: null,
          updated_at: '2026-11-12T08:00:10Z',
        },
        {
          id: 'job_02',
          project_id: 'proj_01',
          job_type: 'batch_export',
          status: 'failed',
          priority: 100,
          progress_pct: 10.0,
          current_stage: 'encoding_candidate_1',
          worker_id: 'w1',
          worker_pid: 1234,
          input_config: {},
          result_metadata: null,
          error_message: 'FFmpeg transcode timeout',
          retry_count: 1,
          max_attempts: 2,
          created_at: '2026-11-12T07:50:00Z',
          started_at: '2026-11-12T07:50:05Z',
          completed_at: null,
          cancellation_requested_at: null,
          cancelled_at: null,
          updated_at: '2026-11-12T07:50:20Z',
        },
      ];

      vi.spyOn(apiClient, 'fetchJobs').mockResolvedValue({ items: mockJobs, total: 2 });
      vi.spyOn(apiClient, 'fetchQueueStats').mockResolvedValue({
        total_jobs: 2,
        queued: 0,
        running: 1,
        completed: 0,
        failed: 1,
        cancelled: 0,
        by_type: { video_analysis: 1, batch_export: 1 },
        active_job_ids: ['job_01'],
      });

      render(
        <WorkingQueueView
          projects={[{ id: 'proj_01', name: 'Podcast Episode 4', status: 'active', created_at: '', updated_at: '' } as any]}
        />
      );

      // Verify header and metric cards
      await waitFor(() => {
        expect(screen.getByText('Working Queue & Jobs')).toBeInTheDocument();
        expect(screen.getByText('Queue Status & Task Type Distribution')).toBeInTheDocument();
      });

      // Verify task type chips
      expect(screen.getAllByText('video analysis').length).toBeGreaterThan(0);
      expect(screen.getAllByText('batch export').length).toBeGreaterThan(0);

      // Verify jobs in table
      expect(screen.getByText('job_01')).toBeInTheDocument();
      expect(screen.getByText('job_02')).toBeInTheDocument();
      expect(screen.getByText('R1')).toBeInTheDocument(); // Retry badge

      // Filter by "running"
      fireEvent.click(screen.getByRole('button', { name: 'running' }));
      expect(screen.getByText('job_01')).toBeInTheDocument();
      expect(screen.queryByText('job_02')).not.toBeInTheDocument();
    });
  });

  describe('AIProviderManager Component', () => {
    it('renders provider inventory, task assignments, and secret masking input', async () => {
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
          capabilities: [{ task: 'visual_understanding', supported: true, description: 'Vision' }],
          latency_ms: 15.2,
          last_health_check: '2026-11-12T08:00:00Z',
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
          capabilities: [{ task: 'speech_transcription', supported: true, description: 'ASR' }],
          latency_ms: 5.0,
          last_health_check: '2026-11-12T08:00:00Z',
          details: 'faster-whisper on CPU',
        },
        {
          id: 'heuristic-engine',
          name: 'ZezEdit Deterministic Heuristics',
          provider_type: 'heuristic',
          status: 'ready',
          is_local: true,
          base_url: null,
          active_model: 'deterministic_v2',
          available_models: ['deterministic_v2'],
          capabilities: [{ task: 'motion_detection', supported: true, description: 'Delta' }],
          latency_ms: 1.0,
          last_health_check: '2026-11-12T08:00:00Z',
          details: 'Zero-dependency fallback',
        },
      ]);

      render(<AIProviderManager />);

      await waitFor(() => {
        expect(screen.getByText('AI Provider Manager')).toBeInTheDocument();
        expect(screen.getByText('Ollama Local Inference')).toBeInTheDocument();
        expect(screen.getByText('Faster-Whisper Speech Engine')).toBeInTheDocument();
        expect(screen.getByText('ZezEdit Deterministic Heuristics')).toBeInTheDocument();
      });

      // Verify task assignment matrix
      expect(screen.getByText('Studio Task-to-Engine Assignments')).toBeInTheDocument();
      expect(screen.getByText('1. Speech Transcription & Word Timestamps')).toBeInTheDocument();
      expect(screen.getByText('3. Highlight Discovery & Rationale Scoring')).toBeInTheDocument();
      expect(screen.getByText('4. Smart Reframing & Subject Tracking')).toBeInTheDocument();

      // Verify secret masking input
      const secretInput = screen.getByPlaceholderText('Bearer ••••••••••••••••');
      expect(secretInput).toHaveAttribute('type', 'password');

      // Click "Show" to reveal
      const showBtn = screen.getByRole('button', { name: 'Show' });
      fireEvent.click(showBtn);
      expect(secretInput).toHaveAttribute('type', 'text');
    });
  });

  describe('DocumentationView Component', () => {
    it('renders categories and articles and supports searching guides', async () => {
      vi.spyOn(apiClient, 'fetchDocCategories').mockResolvedValue([
        { id: 'getting-started', name: 'Getting Started', description: 'Basics', article_count: 2 },
        { id: 'system-operations', name: 'System & Operations', description: 'Ops', article_count: 2 },
      ]);
      vi.spyOn(apiClient, 'fetchDocArticles').mockResolvedValue([
        {
          id: 'architecture-overview',
          title: 'ZezEdit Architecture & CPU-First Execution',
          category: 'getting-started',
          summary: 'Why ZezEdit runs locally on CPU.',
          tags: ['architecture', 'cpu'],
          reading_time_minutes: 3,
        },
        {
          id: 'troubleshooting-guide',
          title: 'Troubleshooting: FFmpeg & Memory',
          category: 'system-operations',
          summary: 'Solutions for missing binaries and errors.',
          tags: ['troubleshooting', 'ffmpeg'],
          reading_time_minutes: 4,
        },
      ]);
      vi.spyOn(apiClient, 'fetchDocArticleDetail').mockResolvedValue({
        id: 'architecture-overview',
        title: 'ZezEdit Architecture & CPU-First Execution',
        category: 'getting-started',
        summary: 'Why ZezEdit runs locally on CPU.',
        markdown_content: '# ZezEdit Architecture\n\nCPU-first execution model.',
        tags: ['architecture', 'cpu'],
        related_article_ids: ['troubleshooting-guide'],
        updated_at: '2026-11-12T06:30:00Z',
      });

      render(<DocumentationView />);

      await waitFor(() => {
        expect(screen.getByText('Studio Documentation & User Guides')).toBeInTheDocument();
        expect(screen.getAllByText('ZezEdit Architecture & CPU-First Execution').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Troubleshooting: FFmpeg & Memory').length).toBeGreaterThan(0);
      });

      // Filter with search input
      const searchInput = screen.getByPlaceholderText('Search guides, topics, tags...');
      fireEvent.change(searchInput, { target: { value: 'troubleshoot' } });

      // Click on the matching article in the filtered list
      const matchedArticles = screen.getAllByText('Troubleshooting: FFmpeg & Memory');
      expect(matchedArticles.length).toBeGreaterThan(0);
      fireEvent.click(matchedArticles[0]);

      // Architecture article is no longer in the left articles list
      const leftArticleButtons = screen.getAllByRole('button');
      const hasArchitectureInList = leftArticleButtons.some((b) => b.textContent?.includes('Why ZezEdit runs locally on CPU'));
      expect(hasArchitectureInList).toBe(false);
    });
  });
});
