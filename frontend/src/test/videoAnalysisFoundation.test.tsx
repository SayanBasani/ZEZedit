import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as apiClient from '../services/apiClient';

describe('P2.1: Video Analysis Foundation - API & Client Layer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('correctly constructs project-scoped URL for startMediaAnalysis', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        id: 'run-123',
        media_asset_id: 'med-1',
        project_id: 'proj-1',
        status: 'pending',
        profile: 'balanced',
        progress_pct: 0,
        stored_file_id: 'sf-1',
        source_signature: '1024:1234:abcdef',
        created_at: '2026-11-20T12:00:00Z',
        updated_at: '2026-11-20T12:00:00Z',
      }),
    } as any);

    const res = await apiClient.startMediaAnalysis('proj-1', 'med-1', 'balanced');
    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/projects/proj-1/media/med-1/analysis');
    expect(res.id).toBe('run-123');
    expect(res.stored_file_id).toBe('sf-1');
  });

  it('correctly constructs global asset URL when projectId is empty', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        id: 'run-global-1',
        media_asset_id: 'med-1',
        project_id: 'proj-resolved',
        status: 'pending',
        profile: 'fast',
        progress_pct: 0,
        created_at: '2026-11-20T12:00:00Z',
        updated_at: '2026-11-20T12:00:00Z',
      }),
    } as any);

    const res = await apiClient.startMediaAnalysis('', 'med-1', 'fast');
    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/media/med-1/analysis');
    expect(calledUrl).not.toContain('/projects//');
    expect(res.id).toBe('run-global-1');
  });

  it('handles MEDIA_FILE_MISSING error cleanly from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        detail: {
          error_code: 'MEDIA_FILE_MISSING',
          message: "Media asset 'med-missing' source file is missing or inaccessible on disk.",
          details: { media_asset_id: 'med-missing' },
        },
      }),
    } as any);

    await expect(apiClient.startMediaAnalysis('proj-1', 'med-missing')).rejects.toThrow();
  });

  it('handles STORAGE_QUOTA_EXCEEDED error cleanly from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        detail: {
          error_code: 'STORAGE_QUOTA_EXCEEDED',
          message: 'Temporary storage quota exceeded for video analysis.',
          details: { media_asset_id: 'med-1' },
        },
      }),
    } as any);

    await expect(apiClient.startMediaAnalysis('proj-1', 'med-1')).rejects.toThrow();
  });

  it('handles cancellation and retry endpoints', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ run_id: 'run-1', status: 'cancelled' }),
    } as any);

    const cancelRes = await apiClient.cancelAnalysisRun('proj-1', 'med-1', 'run-1');
    expect(cancelRes.status).toBe('cancelled');
    expect(fetchSpy.mock.calls[0][0]).toContain('/projects/proj-1/media/med-1/analysis/run-1/cancel');

    fetchSpy.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ run_id: 'run-1', status: 'pending' }),
    } as any);

    const retryRes = await apiClient.retryAnalysisRun('proj-1', 'med-1', 'run-1');
    expect(retryRes.status).toBe('pending');
    expect(fetchSpy.mock.calls[1][0]).toContain('/projects/proj-1/media/med-1/analysis/run-1/retry');
  });

  it('generates correct frame and thumbnail URLs for both project and global contexts', () => {
    const projFrameUrl = apiClient.getFrameImageUrl('proj-1', 'med-1', 'frame-abc');
    expect(projFrameUrl).toContain('/projects/proj-1/media/med-1/analysis/frame-image/frame-abc');

    const globalFrameUrl = apiClient.getFrameImageUrl('', 'med-1', 'frame-abc');
    expect(globalFrameUrl).toContain('/media/med-1/analysis/frame-image/frame-abc');
    expect(globalFrameUrl).not.toContain('/projects//');

    const projThumbUrl = apiClient.getSceneThumbnailUrl('proj-1', 'med-1', 'scene-xyz');
    expect(projThumbUrl).toContain('/projects/proj-1/media/med-1/analysis/scene-thumbnail/scene-xyz');

    const globalThumbUrl = apiClient.getSceneThumbnailUrl('', 'med-1', 'scene-xyz');
    expect(globalThumbUrl).toContain('/media/med-1/analysis/scene-thumbnail/scene-xyz');
    expect(globalThumbUrl).not.toContain('/projects//');
  });
});
