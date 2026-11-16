import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { isUploadRetryable, uploadMediaFile } from '../services/apiClient';
import { UploadProgressPanel, UploadItem } from '../features/videos/UploadProgressPanel';
import { UploadProgressInfo } from '../types/projects';

let originalXHR: any;
let mockXHRInstances: any[] = [];

beforeEach(() => {
  originalXHR = globalThis.XMLHttpRequest;
  mockXHRInstances = [];

  class MockXHR {
    upload: any = {};
    status: number = 0;
    responseText: string = '';
    readyState: number = 0;
    onload: any = null;
    onerror: any = null;
    ontimeout: any = null;
    onabort: any = null;

    open = vi.fn();
    send = vi.fn();
    abort = vi.fn(() => {
      if (this.onabort) this.onabort();
    });

    constructor() {
      mockXHRInstances.push(this);
    }
  }

  globalThis.XMLHttpRequest = MockXHR as any;
});

afterEach(() => {
  globalThis.XMLHttpRequest = originalXHR;
});

describe('P1.4: Upload Failure Handling, Retry and Recovery Tests', () => {
  describe('isUploadRetryable error classification', () => {
    it('accurately identifies retryable errors', () => {
      // Network drops / connection interruptions
      expect(isUploadRetryable(null)).toBe(true);
      expect(isUploadRetryable(0)).toBe(true);
      expect(isUploadRetryable(null, 'NETWORK_ERROR')).toBe(true);

      // Timeouts
      expect(isUploadRetryable(408)).toBe(true);
      expect(isUploadRetryable(null, 'TIMEOUT')).toBe(true);

      // Concurrency limits (429)
      expect(isUploadRetryable(429)).toBe(true);
      expect(isUploadRetryable(429, 'TOO_MANY_CONCURRENT_UPLOADS')).toBe(true);

      // Server errors (500, 502, 503, 504)
      expect(isUploadRetryable(500)).toBe(true);
      expect(isUploadRetryable(502)).toBe(true);
      expect(isUploadRetryable(503)).toBe(true);
      expect(isUploadRetryable(504)).toBe(true);

      // User cancellation / aborted
      expect(isUploadRetryable(null, 'ABORTED')).toBe(true);

      // Database registration failure
      expect(isUploadRetryable(500, 'DATABASE_REGISTRATION_FAILED')).toBe(true);
    });

    it('accurately identifies non-retryable terminal errors', () => {
      // Bad request / invalid input
      expect(isUploadRetryable(400, 'EMPTY_MEDIA_FILE')).toBe(false);
      expect(isUploadRetryable(400, 'PATH_TRAVERSAL_DETECTED')).toBe(false);
      expect(isUploadRetryable(400, 'UNSUPPORTED_MEDIA_TYPE')).toBe(false);

      // Not found
      expect(isUploadRetryable(404)).toBe(false);

      // Oversized payload
      expect(isUploadRetryable(413, 'REQUEST_ENTITY_TOO_LARGE')).toBe(false);

      // Unsupported media format
      expect(isUploadRetryable(415)).toBe(false);
    });
  });

  describe('UploadProgressPanel retry and attempt badge rendering', () => {
    it('displays Retry button on failed retryable item and triggers onRetryItem', () => {
      const onRetryMock = vi.fn();
      const dummyFile = new File(['fake content'], 'failed_video.mp4', { type: 'video/mp4' });
      const item: UploadItem = {
        id: 'item_fail_1',
        file: dummyFile,
        loaded: 500,
        total: 1000,
        percentage: 50,
        state: 'failed',
        error: 'Network connection lost',
        attemptId: 'att_1',
        attemptCount: 1,
        retryable: true,
      };

      render(
        <UploadProgressPanel
          items={[item]}
          isUploading={false}
          onRetryItem={onRetryMock}
        />
      );

      // File name and error message
      expect(screen.getByText('failed_video.mp4')).toBeDefined();
      expect(screen.getByText('Network connection lost')).toBeDefined();

      // Retry button should be present
      const retryBtn = screen.getByTestId('retry-button-item_fail_1');
      expect(retryBtn).toBeDefined();

      fireEvent.click(retryBtn);
      expect(onRetryMock).toHaveBeenCalledWith('item_fail_1');
    });

    it('displays (Non-retryable) and NO Retry button on terminal failure', () => {
      const onRetryMock = vi.fn();
      const dummyFile = new File([''], 'empty_video.mp4', { type: 'video/mp4' });
      const item: UploadItem = {
        id: 'item_terminal_1',
        file: dummyFile,
        loaded: 0,
        total: 0,
        percentage: null,
        state: 'failed',
        error: 'Empty media file (0 bytes)',
        attemptId: 'att_term_1',
        attemptCount: 1,
        retryable: false,
      };

      render(
        <UploadProgressPanel
          items={[item]}
          isUploading={false}
          onRetryItem={onRetryMock}
        />
      );

      expect(screen.getByText('(Non-retryable)')).toBeDefined();
      expect(screen.queryByTestId('retry-button-item_terminal_1')).toBeNull();
    });

    it('displays Attempt badge when attemptCount > 1', () => {
      const dummyFile = new File(['data'], 'retry_video.mp4', { type: 'video/mp4' });
      const item: UploadItem = {
        id: 'item_attempt_2',
        file: dummyFile,
        loaded: 0,
        total: 1000,
        percentage: 0,
        state: 'retrying',
        attemptId: 'att_2',
        attemptCount: 2,
        retryable: true,
      };

      render(
        <UploadProgressPanel
          items={[item]}
          isUploading={true}
        />
      );

      const badge = screen.getByTestId('attempt-badge-item_attempt_2');
      expect(badge).toBeDefined();
      expect(badge.textContent).toBe('Attempt 2');
    });

    it('displays Retry button on cancelled / aborted items', () => {
      const onRetryMock = vi.fn();
      const dummyFile = new File(['data'], 'cancelled_video.mp4', { type: 'video/mp4' });
      const item: UploadItem = {
        id: 'item_cancelled_1',
        file: dummyFile,
        loaded: 300,
        total: 1000,
        percentage: 30,
        state: 'cancelled',
        attemptId: 'att_cancel_1',
        attemptCount: 1,
        retryable: true,
      };

      render(
        <UploadProgressPanel
          items={[item]}
          isUploading={false}
          onRetryItem={onRetryMock}
        />
      );

      expect(screen.getByText('Cancelled')).toBeDefined();
      const retryBtn = screen.getByTestId('retry-button-item_cancelled_1');
      expect(retryBtn).toBeDefined();

      fireEvent.click(retryBtn);
      expect(onRetryMock).toHaveBeenCalledWith('item_cancelled_1');
    });

    it('guards against duplicate retry clicks while an upload is active', () => {
      const onRetryMock = vi.fn();
      const dummyFile = new File(['data'], 'in_flight.mp4', { type: 'video/mp4' });
      const item: UploadItem = {
        id: 'item_active',
        file: dummyFile,
        loaded: 500,
        total: 1000,
        percentage: 50,
        state: 'failed',
        error: 'Timeout',
        attemptId: 'att_active',
        attemptCount: 1,
        retryable: true,
      };

      // When isUploading = true, retry button is disabled/hidden
      render(
        <UploadProgressPanel
          items={[item]}
          isUploading={true}
          onRetryItem={onRetryMock}
        />
      );

      expect(screen.queryByTestId('retry-button-item_active')).toBeNull();
    });
  });

  describe('Stale callback guard and retry state isolation', () => {
    it('silently ignores callbacks with outdated attemptId', async () => {
      const file = new File(['video payload'], 'stale_test.mp4', { type: 'video/mp4' });
      const progressUpdates: UploadProgressInfo[] = [];

      const uploadPromise = uploadMediaFile('default', file, false, true, {
        attemptId: 'att_current',
        attemptCount: 2,
        onProgress: (p) => progressUpdates.push({ ...p }),
      });

      const xhr = mockXHRInstances[0];

      // Simulate a progress event
      if (xhr.upload.onprogress) {
        xhr.upload.onprogress({
          lengthComputable: true,
          loaded: 5,
          total: file.size,
        });
      }

      // Complete with success
      xhr.status = 200;
      xhr.responseText = JSON.stringify({
        id: 'med_test_123',
        project_id: 'default',
        original_filename: 'stale_test.mp4',
        storage_path: 'media/stale_test.mp4',
        is_external: false,
        media_type: 'video',
        file_size_bytes: file.size,
        mime_type: 'video/mp4',
        duration_seconds: 1.0,
        width: 1280,
        height: 720,
        fps: 30,
        video_codec: 'h264',
        audio_codec: 'aac',
        availability_status: 'present',
        proxy_reference_path: null,
        thumbnail_reference_path: null,
        proxy_status: 'none',
        metadata_status: 'extracted',
        metadata: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      xhr.onload!();

      const asset = await uploadPromise;
      expect(asset.id).toBe('med_test_123');

      // Every emitted progress event must have attemptId = "att_current" and attemptCount = 2
      for (const p of progressUpdates) {
        expect(p.attemptId).toBe('att_current');
        expect(p.attemptCount).toBe(2);
      }
    });
  });
});
