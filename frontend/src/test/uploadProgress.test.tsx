import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { formatBytes, uploadMediaFile } from '../services/apiClient';
import { UploadProgressPanel, UploadItem } from '../features/videos/UploadProgressPanel';
import { UploadProgressInfo } from '../types/projects';

describe('P1.2: Accurate Byte-Based Upload Progress Tests', () => {
  describe('formatBytes helper', () => {
    it('formats null, undefined, 0, and NaN honestly as 0 B', () => {
      expect(formatBytes(null)).toBe('0 B');
      expect(formatBytes(undefined)).toBe('0 B');
      expect(formatBytes(0)).toBe('0 B');
      expect(formatBytes(NaN)).toBe('0 B');
    });

    it('formats bytes, KB, MB, and GB accurately with 1 decimal place by default', () => {
      expect(formatBytes(500)).toBe('500 B');
      expect(formatBytes(1024)).toBe('1 KB');
      expect(formatBytes(1536)).toBe('1.5 KB');
      expect(formatBytes(1048576)).toBe('1 MB');
      expect(formatBytes(25690112)).toBe('24.5 MB');
      expect(formatBytes(1073741824)).toBe('1 GB');
    });
  });

  describe('UploadProgressPanel Component', () => {
    it('renders empty when items is empty', () => {
      const { container } = render(
        <UploadProgressPanel items={[]} isUploading={false} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('displays filename, bytes transmitted, total bytes, and percentage truthfully', () => {
      const file = new File(['test'], 'demo_video.mp4', { type: 'video/mp4' });
      const items: UploadItem[] = [
        {
          id: '1',
          file,
          loaded: 25690112, // 24.5 MB
          total: 83886080, // 80 MB
          percentage: 30.625,
          state: 'uploading',
        },
      ];

      render(<UploadProgressPanel items={items} isUploading={true} />);

      expect(screen.getByText('demo_video.mp4')).toBeDefined();
      expect(screen.getAllByText(/24.5 MB \/ 80 MB/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/\(30.6%\)/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Uploading video...')).toBeDefined();
    });

    it('handles unknown totals honestly without fabricating a percentage', () => {
      const file = new File(['test'], 'stream_video.mp4', { type: 'video/mp4' });
      const items: UploadItem[] = [
        {
          id: '2',
          file,
          loaded: 1048576, // 1 MB
          total: null,
          percentage: null,
          state: 'uploading',
        },
      ];

      render(<UploadProgressPanel items={items} isUploading={true} />);

      expect(screen.getByText(/1 MB transferred/)).toBeDefined();
      // Must not display a fabricated 0% or 100%
      expect(screen.queryByText('NaN%')).toBeNull();
      expect(screen.queryByText('undefined%')).toBeNull();
    });

    it('visibly separates server processing state from byte transmission', () => {
      const file = new File(['test'], 'processing_video.mp4', { type: 'video/mp4' });
      const items: UploadItem[] = [
        {
          id: '3',
          file,
          loaded: 5242880,
          total: 5242880,
          percentage: 100,
          state: 'processing',
        },
      ];

      render(<UploadProgressPanel items={items} isUploading={true} />);

      expect(screen.getByText(/Processing on server\.\.\./)).toBeDefined();
      // Should not claim upload is complete while still processing
      expect(screen.queryByText('Upload complete')).toBeNull();
    });

    it('displays completed state with success indicator when server persists record', () => {
      const file = new File(['test'], 'done_video.mp4', { type: 'video/mp4' });
      const items: UploadItem[] = [
        {
          id: '4',
          file,
          loaded: 5242880,
          total: 5242880,
          percentage: 100,
          state: 'completed',
        },
      ];

      render(<UploadProgressPanel items={items} isUploading={false} />);

      expect(screen.getByText('Upload complete')).toBeDefined();
      expect(screen.getByText(/Completed/)).toBeDefined();
    });

    it('displays error state truthfully on failure with error details', () => {
      const file = new File(['test'], 'failed_video.mp4', { type: 'video/mp4' });
      const items: UploadItem[] = [
        {
          id: '5',
          file,
          loaded: 1024,
          total: 5242880,
          percentage: 0.02,
          state: 'error',
          error: 'Connection interrupted by host',
        },
      ];

      render(<UploadProgressPanel items={items} isUploading={false} />);

      expect(screen.getByText('Upload failed')).toBeDefined();
      expect(screen.getByText('Connection interrupted by host')).toBeDefined();
    });

    it('triggers onCancel when Cancel button is clicked during upload', () => {
      const file = new File(['test'], 'cancelling_video.mp4', { type: 'video/mp4' });
      const handleCancel = vi.fn();
      const items: UploadItem[] = [
        {
          id: '6',
          file,
          loaded: 500,
          total: 1000,
          percentage: 50,
          state: 'uploading',
        },
      ];

      render(
        <UploadProgressPanel
          items={items}
          isUploading={true}
          onCancel={handleCancel}
        />
      );

      const cancelBtn = screen.getByText('Cancel');
      fireEvent.click(cancelBtn);
      expect(handleCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe('uploadMediaFile Transport & Progress Calculation', () => {
    let originalXHR: any;
    let mockXHRInstances: any[];

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

    it('calculates percentage strictly as loaded / total * 100 and enforces monotonicity', async () => {
      const file = new File(['abcdefgh'], 'mono.mp4', { type: 'video/mp4' });
      const progressSnapshots: UploadProgressInfo[] = [];

      const uploadPromise = uploadMediaFile('default', file, false, true, {
        onProgress: (p) => progressSnapshots.push({ ...p }),
      });

      const xhr = mockXHRInstances[0];
      expect(xhr).toBeDefined();

      // Simulate first progress event: 2 bytes of 8 (25%)
      xhr.upload.onprogress({
        lengthComputable: true,
        loaded: 2,
        total: 8,
      });

      // Simulate second progress event: 4 bytes of 8 (50%)
      xhr.upload.onprogress({
        lengthComputable: true,
        loaded: 4,
        total: 8,
      });

      // Simulate a faulty backward event: 3 bytes (should NOT move loaded backward)
      xhr.upload.onprogress({
        lengthComputable: true,
        loaded: 3,
        total: 8,
      });

      // Simulate reaching 8 bytes (100% -> processing)
      xhr.upload.onprogress({
        lengthComputable: true,
        loaded: 8,
        total: 8,
      });

      // Simulate server response
      xhr.status = 201;
      xhr.responseText = JSON.stringify({
        id: 'med_test123',
        original_filename: 'mono.mp4',
        storage_path: 'storage/media/default/mono.mp4',
        file_size_bytes: 8,
      });
      xhr.onload();

      const result = await uploadPromise;
      expect(result.id).toBe('med_test123');

      // Verify snapshots
      expect(progressSnapshots.length).toBeGreaterThanOrEqual(4);
      // Check monotonicity: loaded must never decrease
      for (let i = 1; i < progressSnapshots.length; i++) {
        expect(progressSnapshots[i].loaded).toBeGreaterThanOrEqual(progressSnapshots[i - 1].loaded);
      }
      // Check 100% cap
      for (const p of progressSnapshots) {
        if (p.percentage !== null) {
          expect(p.percentage).toBeLessThanOrEqual(100);
          expect(p.percentage).toBeGreaterThanOrEqual(0);
        }
      }
      // Check transition to processing at loaded == total
      const processingSnapshot = progressSnapshots.find((s) => s.state === 'processing');
      expect(processingSnapshot).toBeDefined();
      expect(processingSnapshot?.loaded).toBe(8);

      // Final snapshot must be completed
      const finalSnapshot = progressSnapshots[progressSnapshots.length - 1];
      expect(finalSnapshot.state).toBe('completed');
    });

    it('handles lengthComputable === false without guessing totals', async () => {
      const file = new File([''], 'unknown.mp4', { type: 'video/mp4' });
      // override file size to 0 to simulate unknown
      Object.defineProperty(file, 'size', { value: 0 });

      const progressSnapshots: UploadProgressInfo[] = [];
      const uploadPromise = uploadMediaFile('default', file, false, true, {
        onProgress: (p) => progressSnapshots.push({ ...p }),
      });

      const xhr = mockXHRInstances[0];
      xhr.upload.onprogress({
        lengthComputable: false,
        loaded: 1024,
        total: 0,
      });

      xhr.status = 201;
      xhr.responseText = JSON.stringify({ id: 'med_unk' });
      xhr.onload();

      await uploadPromise;

      const unkSnapshot = progressSnapshots.find((s) => s.loaded === 1024);
      expect(unkSnapshot).toBeDefined();
      expect(unkSnapshot?.total).toBeNull();
      expect(unkSnapshot?.percentage).toBeNull();
    });

    it('handles aborted requests cleanly with state = aborted', async () => {
      const file = new File(['data'], 'aborted.mp4', { type: 'video/mp4' });
      const controller = new AbortController();
      const progressSnapshots: UploadProgressInfo[] = [];

      const uploadPromise = uploadMediaFile('default', file, false, true, {
        signal: controller.signal,
        onProgress: (p) => progressSnapshots.push({ ...p }),
      });

      const xhr = mockXHRInstances[0];
      xhr.upload.onprogress({
        lengthComputable: true,
        loaded: 2,
        total: 4,
      });

      // Abort
      controller.abort();

      await expect(uploadPromise).rejects.toThrow();

      const last = progressSnapshots[progressSnapshots.length - 1];
      expect(last.state).toBe('aborted');
    });

    it('handles HTTP error status codes truthfully with state = error', async () => {
      const file = new File(['data'], 'err.mp4', { type: 'video/mp4' });
      const progressSnapshots: UploadProgressInfo[] = [];

      const uploadPromise = uploadMediaFile('default', file, false, true, {
        onProgress: (p) => progressSnapshots.push({ ...p }),
      });

      const xhr = mockXHRInstances[0];
      xhr.status = 400;
      xhr.responseText = JSON.stringify({
        error: { code: 'INVALID_VIDEO', message: 'Video stream contains corrupted moov atom' },
      });
      xhr.onload();

      await expect(uploadPromise).rejects.toThrow(/Video stream contains corrupted moov atom/);

      const last = progressSnapshots[progressSnapshots.length - 1];
      expect(last.state).toBe('error');
      expect(last.error).toContain('corrupted moov atom');
    });
  });
});
