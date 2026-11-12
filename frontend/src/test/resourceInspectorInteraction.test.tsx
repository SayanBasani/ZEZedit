import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceInspector } from '../components/system/ResourceInspector';
import * as apiClient from '../services/apiClient';

describe('Milestone 24: ResourceInspector Component Interactive Verification (ZEZ-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('displays CPU, memory, and execution mode correctly on hover', async () => {
    vi.spyOn(apiClient, 'fetchSystemResources').mockResolvedValue({
      cpu_percent: 32.1,
      process_cpu_percent: 4.5,
      cpu_count_logical: 8,
      cpu_count_physical: 4,
      memory_total_mb: 16000,
      memory_available_mb: 8000,
      memory_used_mb: 8000,
      memory_percent: 50.0,
      process_memory_rss_mb: 220,
      process_memory_vms_mb: 500,
      active_workers: 2,
      pending_jobs: 1,
      max_concurrent_jobs: 2,
      execution_mode: 'cpu_first',
      timestamp: '2026-11-12T00:00:00Z',
    });

    render(<ResourceInspector />);

    // Wait until metrics pill updates
    expect(await screen.findByText('32%')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('2w')).toBeInTheDocument();

    // Hover container to open dropdown
    const trigger = screen.getByLabelText('Hardware resource monitor');
    fireEvent.mouseEnter(trigger.parentElement || trigger);

    expect(screen.getByText('Resource Inspector')).toBeInTheDocument();
    expect(screen.getByText('Host CPU Usage')).toBeInTheDocument();
    expect(screen.getByText('CPU-First Baseline')).toBeInTheDocument();
    expect(screen.getByText('Job Concurrency')).toBeInTheDocument();
  });

  it('allows pinning inspector floating window so it stays open on mouse leave', async () => {
    vi.spyOn(apiClient, 'fetchSystemResources').mockResolvedValue({
      cpu_percent: 15.0,
      process_cpu_percent: 2.0,
      cpu_count_logical: 8,
      cpu_count_physical: 4,
      memory_total_mb: 16000,
      memory_available_mb: 12000,
      memory_used_mb: 4000,
      memory_percent: 25.0,
      process_memory_rss_mb: 150,
      process_memory_vms_mb: 300,
      active_workers: 0,
      pending_jobs: 0,
      max_concurrent_jobs: 2,
      execution_mode: 'cpu_first',
      timestamp: '2026-11-12T00:00:00Z',
    });

    render(<ResourceInspector />);

    expect(await screen.findByText('15%')).toBeInTheDocument();

    const trigger = screen.getByLabelText('Hardware resource monitor');
    fireEvent.click(trigger);

    expect(screen.getByText('Resource Inspector')).toBeInTheDocument();

    const pinBtn = screen.getByLabelText('Pin inspector window');
    fireEvent.click(pinBtn);

    // Mouse leave should keep it open when pinned
    fireEvent.mouseLeave(trigger.parentElement || trigger);
    expect(screen.getByText('Resource Inspector')).toBeInTheDocument();
  });

  it('closes inspector when user presses Escape key', async () => {
    vi.spyOn(apiClient, 'fetchSystemResources').mockResolvedValue({
      cpu_percent: 20.0,
      process_cpu_percent: 2.0,
      cpu_count_logical: 8,
      cpu_count_physical: 4,
      memory_total_mb: 16000,
      memory_available_mb: 12000,
      memory_used_mb: 4000,
      memory_percent: 25.0,
      process_memory_rss_mb: 150,
      process_memory_vms_mb: 300,
      active_workers: 0,
      pending_jobs: 0,
      max_concurrent_jobs: 2,
      execution_mode: 'cpu_first',
      timestamp: '2026-11-12T00:00:00Z',
    });

    render(<ResourceInspector />);

    expect(await screen.findByText('20%')).toBeInTheDocument();

    const trigger = screen.getByLabelText('Hardware resource monitor');
    fireEvent.click(trigger);
    expect(screen.getByText('Resource Inspector')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByText('Resource Inspector')).not.toBeInTheDocument();
  });
});
