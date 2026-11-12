import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { ToastProvider, useToast } from '../components/system/ToastNotificationCenter';

const TestConsumer: React.FC = () => {
  const toast = useToast();

  return (
    <div>
      <button onClick={() => toast.success('Video exported successfully', { title: 'Export Ready' })}>
        Trigger Success
      </button>
      <button
        onClick={() =>
          toast.error('FFmpeg render error: exit code 1', {
            title: 'Render Error',
            action: {
              label: 'Retry Job',
              onClick: () => {
                const el = document.getElementById('action-result');
                if (el) el.textContent = 'Action Clicked';
              },
            },
          })
        }
      >
        Trigger Error With Action
      </button>
      <button onClick={() => toast.warning('High memory usage detected')}>
        Trigger Warning
      </button>
      <button onClick={() => toast.info('Auto-saving timeline revision')}>
        Trigger Info
      </button>
      <button onClick={() => toast.clearAll()}>Clear All</button>
      <div id="action-result">Idle</div>
    </div>
  );
};

describe('ToastNotificationCenter (ZEZ-008)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders and self-dismisses success toast after 4000ms duration', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Success'));

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Export Ready')).toBeInTheDocument();
    expect(screen.getByText('Video exported successfully')).toBeInTheDocument();

    // Fast-forward 3900ms - should still be present
    act(() => {
      vi.advanceTimersByTime(3900);
    });
    expect(screen.getByText('Video exported successfully')).toBeInTheDocument();

    // Advance past 4000ms - should be dismissed
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByText('Video exported successfully')).not.toBeInTheDocument();
  });

  it('supports action callback button inside toast card', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Error With Action'));

    expect(screen.getByText('Render Error')).toBeInTheDocument();
    const actionBtn = screen.getByText('Retry Job');
    expect(actionBtn).toBeInTheDocument();

    fireEvent.click(actionBtn);
    expect(screen.getByText('Action Clicked')).toBeInTheDocument();
    // After clicking action, toast should be dismissed
    expect(screen.queryByText('Render Error')).not.toBeInTheDocument();
  });

  it('allows manual dismissal via close button', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Warning'));
    expect(screen.getByText('High memory usage detected')).toBeInTheDocument();

    const closeBtn = screen.getByLabelText('Dismiss notification');
    fireEvent.click(closeBtn);

    expect(screen.queryByText('High memory usage detected')).not.toBeInTheDocument();
  });

  it('clears all active toasts on clearAll()', async () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Warning'));
    fireEvent.click(screen.getByText('Trigger Info'));

    expect(screen.getByText('High memory usage detected')).toBeInTheDocument();
    expect(screen.getByText('Auto-saving timeline revision')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Clear All'));

    expect(screen.queryByText('High memory usage detected')).not.toBeInTheDocument();
    expect(screen.queryByText('Auto-saving timeline revision')).not.toBeInTheDocument();
  });
});
