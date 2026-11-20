import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as apiClient from '../services/apiClient';

describe('P2.3: Smart Reframing, Subject Tracking & Portrait Composition - Client Layer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('globalAnalyzeReframing correctly calls global analyze endpoint', async () => {
    const mockPlan = {
      id: 'ref-global-1',
      project_id: 'proj-1',
      media_asset_id: 'med-123',
      target_aspect_ratio: '9:16',
      framing_strategy: 'single_subject',
      status: 'completed',
      source_width: 1920,
      source_height: 1080,
      output_width: 1080,
      output_height: 1920,
      start_time: 0.0,
      end_time: 15.0,
      duration: 15.0,
      base_zoom: 1.0,
      headroom_factor: 0.15,
      smoothing_window_seconds: 0.8,
      keyframes: [],
      detected_tracks: [],
      scene_cuts: [],
      warnings: [],
      active_revision_id: 'rev-1',
      created_at: '2026-11-20T12:00:00Z',
      updated_at: '2026-11-20T12:00:00Z',
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => mockPlan,
    } as any);

    const plan = await apiClient.globalAnalyzeReframing('med-123', {
      target_aspect_ratio: '9:16',
      framing_strategy: 'single_subject',
      base_zoom: 1.2,
      headroom_factor: 0.18,
    });

    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/media/med-123/reframing/analyze');
    expect(plan.id).toBe('ref-global-1');
    expect(plan.framing_strategy).toBe('single_subject');
  });

  it('fetchMediaReframingPlans supports both project and global routes', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    } as any);

    // Project-scoped
    await apiClient.fetchMediaReframingPlans('med-123', 'proj-alpha');
    expect((fetchSpy.mock.calls[0][0] as string)).toContain('/api/v1/projects/proj-alpha/media/med-123/reframing/plans');

    // Global
    await apiClient.fetchMediaReframingPlans('med-123');
    expect((fetchSpy.mock.calls[1][0] as string)).toContain('/api/v1/media/med-123/reframing/plans');
  });

  it('globalFetchCropPreview and globalSaveCropOverrides function with exact coordinates', async () => {
    const mockCrop = {
      plan_id: 'ref-1',
      timestamp: 3.5,
      crop_x: 606,
      crop_y: 0,
      crop_w: 606,
      crop_h: 1080,
      zoom: 1.0,
      strategy: 'single_subject',
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockCrop,
    } as any);

    const crop = await apiClient.globalFetchCropPreview('ref-1', 3.5);
    expect(fetchSpy).toHaveBeenCalled();
    expect((fetchSpy.mock.calls[0][0] as string)).toContain('/api/v1/reframing/ref-1/preview?timestamp=3.5');
    expect(crop.crop_x).toBe(606);
    expect(crop.crop_h).toBe(1080);

    // Save manual overrides
    await apiClient.globalSaveCropOverrides('ref-1', [
      { timestamp: 3.5, crop_x: 550, crop_y: 0, zoom: 1.1 },
    ], 'User Adjusted Crop');

    expect((fetchSpy.mock.calls[1][0] as string)).toContain('/api/v1/reframing/ref-1/overrides');
    const body = JSON.parse(fetchSpy.mock.calls[1][1]?.body as string);
    expect(body.manual_overrides[0].crop_x).toBe(550);
    expect(body.revision_label).toBe('User Adjusted Crop');
  });

  it('globalRenderReframingRevision and getGlobalRenderedVideoUrl construct expected endpoints', async () => {
    const mockRenderRes = {
      output_path: 'shorts/proj-1/ref-1_rev2.mp4',
      output_width: 1080,
      output_height: 1920,
      duration: 15.0,
      file_size_bytes: 4500000,
      crop_w: 606,
      crop_h: 1080,
      keyframes_count: 32,
      revision_id: 'rev-2',
      revision_number: 2,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockRenderRes,
    } as any);

    const res = await apiClient.globalRenderReframingRevision('ref-1', 'rev-2');
    expect(fetchSpy).toHaveBeenCalled();
    expect((fetchSpy.mock.calls[0][0] as string)).toContain('/api/v1/reframing/ref-1/render');
    expect(res.output_width).toBe(1080);
    expect(res.output_height).toBe(1920);

    const videoUrl = apiClient.getGlobalRenderedVideoUrl('ref-1', 'rev-2');
    expect(videoUrl).toContain('/api/v1/reframing/ref-1/video?revision_id=rev-2');
  });
});
