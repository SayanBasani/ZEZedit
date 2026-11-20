import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as apiClient from '../services/apiClient';

describe('P2.2: Multimodal Highlight Discovery & Candidate Ranking - Client Layer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchMediaRecommendations correctly calls recommendations endpoint', async () => {
    const mockRecs = [
      {
        id: 'cand-1',
        rank_position: 1,
        quality_score: 92.5,
        title: 'Top Moment',
        evidence_coverage: 1.0,
        signal_scores: {
          speech_interest: 88,
          emotional_intensity: 95,
          audio_activity: 90,
          visual_interest: 85,
          context_completeness: 92,
          narrative_coherence: 94,
          distinctiveness: 91,
        },
      },
    ];
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockRecs,
    } as any);

    const res = await apiClient.fetchMediaRecommendations('proj-1', 'med-123', 5);
    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/projects/proj-1/media/med-123/highlights/recommendations?limit=5');
    expect(res).toHaveLength(1);
    expect(res[0].rank_position).toBe(1);
    expect(res[0].evidence_coverage).toBe(1.0);
    expect(res[0].signal_scores?.speech_interest).toBe(88);
  });

  it('fetchMediaHighlights supports filtering, pagination, and sorting parameters', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        candidates: [],
        total: 0,
        page: 1,
        page_size: 20,
      }),
    } as any);

    await apiClient.fetchMediaHighlights('proj-1', 'med-123', {
      limit: 10,
      offset: 0,
      min_score: 60,
      category: 'hook',
      sort_by: 'rank_position',
      order: 'asc',
    });

    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/projects/proj-1/media/med-123/highlights?');
    expect(calledUrl).toContain('limit=10');
    expect(calledUrl).toContain('min_score=60');
    expect(calledUrl).toContain('category=hook');
    expect(calledUrl).toContain('sort_by=rank_position');
    expect(calledUrl).toContain('order=asc');
  });

  it('discoverHighlights passes multimodal options including force_rediscovery and custom_weights', async () => {
    const mockCandidates = [
      {
        id: 'c-1',
        rank_position: 1,
        quality_score: 89.0,
        evidence_coverage: 0.86,
        signal_scores: { speech_interest: 90, emotional_intensity: 85 },
      },
    ];
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockCandidates,
    } as any);

    const customWeights = {
      speech_interest: 0.35,
      emotional_intensity: 0.25,
      audio_activity: 0.1,
      visual_interest: 0.1,
      context_completeness: 0.1,
      narrative_coherence: 0.05,
      distinctiveness: 0.05,
    };

    const res = await apiClient.discoverHighlights('proj-1', 'med-123', {
      force_rediscovery: true,
      creative_direction: 'podcast',
      custom_weights: customWeights,
      min_score: 55,
      min_separation_seconds: 4.0,
    });

    expect(fetchSpy).toHaveBeenCalled();
    const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
    expect(body.force_rediscovery).toBe(true);
    expect(body.creative_direction).toBe('podcast');
    expect(body.custom_weights.speech_interest).toBe(0.35);
    expect(body.min_score).toBe(55);
    expect(body.min_separation_seconds).toBe(4.0);
    expect(res[0].rank_position).toBe(1);
    expect(res[0].evidence_coverage).toBe(0.86);
  });
});
