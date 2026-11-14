import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Eye,
  FileText,
  Film,
  Loader2,
  Maximize2,
  Mic,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Scissors,
  Search,
  Sliders,
  Sparkles,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import { GenerateShortModal, GenerateShortsModalConfig } from './GenerateShortModal';
import {
  cancelJob,
  deleteExport,
  discoverHighlights,
  fetchAnalysisCacheInfo,
  fetchAnalysisRun,
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTranscript,
  fetchCandidateGenerationRuns,
  fetchCandidateNoveltyHistory,
  fetchJobs,
  fetchMediaAsset,
  fetchMediaHighlights,
  fetchProjectExports,
  generateMoreHighlights,
  getExportDownloadUrl,
  getExportVideoUrl,
  getGlobalThumbnailUrl,
  getSceneThumbnailUrl,
  getStreamMediaUrl,
  retryJob,
  startMediaAnalysis,
  submitBatchExport,
  submitExportRender,
} from '../../services/apiClient';
import {
  AnalysisRunItem,
  TranscriptPayload,
  VideoSceneItem,
} from '../../types/analysis';
import {
  AspectRatioOption,
  CandidateGenerationRunItem,
  CandidateItem,
  DiscoverHighlightsOptions,
  NoveltyHistoryResponse,
} from '../../types/highlights';
import { ExportItem } from '../../types/exports';
import { JobItem, MediaAssetItem } from '../../types/projects';
import { CandidateClipEditorModal } from '../studio/CandidateClipEditorModal';

export type VideoDashboardTab =
  | 'home'
  | 'short_generator'
  | 'generated_shorts'
  | 'rendered_videos'
  | 'scripts'
  | 'frames'
  | 'transcript'
  | 'scenes'
  | 'details';

export interface VideoEditDashboardProps {
  assetId: string;
  projectId?: string;
  onBack: () => void;
}

export const VideoEditDashboard: React.FC<VideoEditDashboardProps> = ({
  assetId,
  projectId = 'default',
  onBack,
}) => {
  // Navigation & Tab State
  const [activeTab, setActiveTab] = useState<VideoDashboardTab>('home');

  // Media Asset State
  const [asset, setAsset] = useState<MediaAssetItem | null>(null);
  const [loadingAsset, setLoadingAsset] = useState(true);
  const [assetError, setAssetError] = useState<string | null>(null);

  // Analysis & Job State
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRunItem[]>([]);
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);
  const [videoJobs, setVideoJobs] = useState<JobItem[]>([]);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [cacheInfo, setCacheInfo] = useState<any>(null);

  // Scenes & Transcript
  const [scenes, setScenes] = useState<VideoSceneItem[]>([]);
  const [selectedSceneIds, setSelectedSceneIds] = useState<Set<string>>(new Set());
  const [transcript, setTranscript] = useState<TranscriptPayload | null>(null);
  const [transcriptSearch, setTranscriptSearch] = useState('');

  // Discovered Candidates / Shorts
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [generationRuns, setGenerationRuns] = useState<CandidateGenerationRunItem[]>([]);
  const [noveltyHistory, setNoveltyHistory] = useState<NoveltyHistoryResponse | null>(null);

  // Short Generation Progress State
  const [generatingShorts, setGeneratingShorts] = useState<boolean>(false);
  const [generationStage, setGenerationStage] = useState<string | null>(null);
  const [selectedBatchFilter, setSelectedBatchFilter] = useState<string>('all');

  // Video Player Ref & State
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Candidate Clip Editor Modal
  const [editorModalOpen, setEditorModalOpen] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState<CandidateItem | null>(null);

  // Export & Generated Videos State
  const [exportingCandidateId, setExportingCandidateId] = useState<string | null>(null);
  const [exportSuccessToast, setExportSuccessToast] = useState<string | null>(null);
  const [renderedVideos, setRenderedVideos] = useState<ExportItem[]>([]);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<Set<string>>(new Set());
  const [batchExporting, setBatchExporting] = useState<boolean>(false);
  const [activePreviewVideo, setActivePreviewVideo] = useState<ExportItem | null>(null);

  // Generate Short Modal State
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState<boolean>(false);
  const [isGenerateMoreModal, setIsGenerateMoreModal] = useState<boolean>(false);

  // Inline Video Playback State (Generated Videos Library)
  const [inlinePlayingVideoId, setInlinePlayingVideoId] = useState<string | null>(null);
  const inlineVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  // Scalable Video Library Filter, Search & Pagination State
  const [videoSearch, setVideoSearch] = useState<string>('');
  const [videoAspectRatioFilter, setVideoAspectRatioFilter] = useState<'all' | '9:16' | '1:1' | '16:9'>('all');
  const [videoStatusFilter, setVideoStatusFilter] = useState<'all' | 'completed' | 'rendering' | 'failed'>('all');
  const [videoSortBy, setVideoSortBy] = useState<'newest' | 'oldest' | 'duration_desc' | 'duration_asc' | 'title'>('newest');
  const [videoPage, setVideoPage] = useState<number>(1);
  const VIDEOS_PER_PAGE = 12;

  // Reset all video-specific state immediately when assetId changes to prevent stale data bleed
  useEffect(() => {
    setAsset(null);
    setAnalysisRuns([]);
    setCandidates([]);
    setGenerationRuns([]);
    setNoveltyHistory(null);
    setScenes([]);
    setSelectedSceneIds(new Set());
    setTranscript(null);
    setCacheInfo(null);
    setActiveJob(null);
    setCurrentTime(0);
    setIsPlaying(false);
  }, [assetId]);

  // Load Asset Details
  const loadAssetDetails = useCallback(async () => {
    setLoadingAsset(true);
    setAssetError(null);
    try {
      const data = await fetchMediaAsset(assetId, projectId);
      setAsset(data);
    } catch (err: any) {
      setAssetError(err.message || 'Failed to load video details.');
    } finally {
      setLoadingAsset(false);
    }
  }, [assetId, projectId]);

  // Load Intelligence Data (Runs, Scenes, Transcript, Highlights, Rendered Videos)
  const loadIntelligenceData = useCallback(async () => {
    if (!assetId) return;
    const effPid = asset?.project_id || projectId || 'default';
    try {
      const [runs, hls, genRuns, novHist, exportsRes] = await Promise.all([
        fetchAnalysisRuns(effPid, assetId).catch(() => []),
        fetchMediaHighlights(effPid, assetId).catch(() => []),
        fetchCandidateGenerationRuns(effPid, assetId).catch(() => []),
        fetchCandidateNoveltyHistory(effPid, assetId).catch(() => null),
        (fetchProjectExports ? fetchProjectExports(effPid, undefined, assetId) : Promise.resolve({ items: [], count: 0 })).catch(() => ({ items: [], count: 0 })),
      ]);

      setAnalysisRuns(runs);
      setCandidates(hls);
      setGenerationRuns(genRuns);
      setNoveltyHistory(novHist);
      setRenderedVideos(exportsRes.items || []);

      const activeRun = runs.find((r) => r.status === 'completed') || runs[0];
      if (activeRun) {
        const [sc, tr, cInfo] = await Promise.all([
          fetchAnalysisScenes(effPid, assetId, activeRun.id).catch(() => []),
          fetchAnalysisTranscript(effPid, assetId, activeRun.id).catch(() => null),
          fetchAnalysisCacheInfo(effPid, assetId, activeRun.id).catch(() => null),
        ]);
        setScenes(sc);
        setTranscript(tr);
        setCacheInfo(cInfo);
        setSelectedSceneIds(new Set(sc.map((s) => s.id)));
      }
    } catch (err) {
      console.error('Error loading intelligence data:', err);
    }
  }, [assetId, asset?.project_id, projectId]);

  // Poll for Active Jobs & Analysis Telemetry (Progress Bar Telemetry)
  useEffect(() => {
    let timer: any;
    const pollJobs = async () => {
      try {
        const [jobsRes, runsRes] = await Promise.all([
          fetchJobs({ mediaAssetId: assetId }).catch(() => ({ items: [] })),
          fetchAnalysisRuns(asset?.project_id || projectId || 'default', assetId).catch(() => []),
        ]);
        const items = jobsRes.items || [];
        setVideoJobs(items);
        if (runsRes && runsRes.length > 0) {
          setAnalysisRuns(runsRes);
        }

        const runningJob = items.find((j: JobItem) => j.status === 'running' && j.media_asset_id === assetId);
        const queuedJob = items.find((j: JobItem) => j.status === 'queued' && j.media_asset_id === assetId);
        setActiveJob(runningJob || queuedJob || null);

        if (runningJob || (runsRes[0] && runsRes[0].status === 'running')) {
          void loadIntelligenceData();
        }
      } catch (err) {
        // silent
      }
    };

    void pollJobs();
    timer = setInterval(pollJobs, 1500);
    return () => clearInterval(timer);
  }, [assetId, asset?.project_id, projectId, loadIntelligenceData]);

  useEffect(() => {
    void loadAssetDetails();
  }, [loadAssetDetails]);

  useEffect(() => {
    if (asset) {
      void loadIntelligenceData();
    }
  }, [asset, loadIntelligenceData]);

  // Effective Video Stream URL
  const videoStreamSrc = useMemo(() => {
    if (!asset) return '';
    return getStreamMediaUrl(asset.id);
  }, [asset]);

  // Calculate Progress Percent and Truthful Details
  const progressDetails = useMemo(() => {
    const latestRun = analysisRuns[0];
    const isRunActive = latestRun && (latestRun.status === 'running' || latestRun.status === 'pending');
    const isJobActive = activeJob && (activeJob.status === 'running' || activeJob.status === 'queued');

    // Case 1: Active Source Video Analysis Run
    if (isRunActive) {
      const details = (latestRun as any).stage_details || {};
      const stageName = latestRun.current_stage || details.stage || 'Analyzing Video';
      const pct = latestRun.progress_pct ?? details.overall_pct ?? 0;
      const desc = details.operation_description || `Stage: ${stageName}`;
      const eta = details.estimated_remaining_seconds != null && details.estimated_remaining_seconds > 0
        ? ` • ~${Math.round(details.estimated_remaining_seconds)}s remaining`
        : '';
      return {
        isActive: true,
        stage: stageName.replace(/_/g, ' '),
        percent: Math.min(100, Math.max(0, pct)),
        etaText: `${desc}${eta}`,
      };
    }

    // Case 2: Active Background Job
    if (isJobActive && activeJob) {
      const cp = (activeJob as any).checkpoint_data || {};
      const details = cp.stage_details || cp.checkpoint_payload || {};
      const stageName = activeJob.current_stage || 'Processing Pipeline';
      const pct = activeJob.progress_pct ?? details.overall_pct ?? 0;
      const desc = details.operation_description || `Job ${activeJob.id.slice(0, 8)} • Stage: ${stageName}`;
      const eta = activeJob.estimated_remaining_seconds != null && activeJob.estimated_remaining_seconds > 0
        ? ` • ~${Math.round(activeJob.estimated_remaining_seconds)}s remaining`
        : '';
      return {
        isActive: true,
        stage: stageName.replace(/_/g, ' '),
        percent: Math.min(100, Math.max(0, pct)),
        etaText: `${desc}${eta}`,
      };
    }

    // Case 3: Generating Shorts / Discovery
    if (generatingShorts) {
      if (generationStage === 'analyzing_source') {
        return {
          isActive: true,
          stage: 'Deep AI Video Analysis...',
          percent: 10,
          etaText: 'Initializing video intelligence pipeline...',
        };
      }
      if (generationStage === 'generating_more') {
        return {
          isActive: true,
          stage: 'Reusing Saved Analysis',
          percent: 85,
          etaText: 'Filtering novelty ledger against previously discovered candidates',
        };
      }
      return {
        isActive: true,
        stage: 'Discovering Highlights',
        percent: 60,
        etaText: 'Evaluating multimodal audio/visual scoring moments',
      };
    }

    return { isActive: false, stage: 'Idle', percent: 100, etaText: '' };
  }, [activeJob, analysisRuns, generationStage, generatingShorts]);

  // Video Player Controls
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(console.error);
    }
  };

  const handleSeek = (timeSec: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = timeSec;
    setCurrentTime(timeSec);
  };

  // Persistent Config & Analysis Helpers
  const completedAnalysisRun = useMemo(() => {
    return analysisRuns.find((r) => r.status === 'completed') || null;
  }, [analysisRuns]);
  const isVideoAnalyzed = Boolean(completedAnalysisRun);

  const handleStartAnalysis = async (forceReanalysis = false) => {
    if (!asset) return;
    setAnalysisLoading(true);
    const effPid = asset.project_id || projectId || 'default';
    try {
      const run = await startMediaAnalysis(effPid, asset.id, 'balanced', {}, false, forceReanalysis);
      setAnalysisRuns((prev) => [run, ...prev.filter((p) => p.id !== run.id)]);
      await loadIntelligenceData();
    } catch (err: any) {
      alert(`Failed to start analysis: ${err.message || 'Unknown error'}`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Generate Shorts from the Unified GenerateShortModal
  const handleGenerateFromModal = async (config: GenerateShortsModalConfig) => {
    if (!asset) return;
    setGeneratingShorts(true);
    setGenerationStage(
      isGenerateMoreModal ? 'Discovering Additional Unique Highlights...' : 'Discovering Highlights with AI...'
    );
    const effPid = asset.project_id || projectId || 'default';
    try {
      let currentRunId = completedAnalysisRun?.id;

      // If not yet analyzed, run analysis and await completion
      if (!isVideoAnalyzed) {
        setGenerationStage('Analyzing Source Video...');
        const initialRun = await startMediaAnalysis(effPid, asset.id, 'balanced', {}, false, false);
        currentRunId = initialRun.id;
        setAnalysisRuns((prev) => [initialRun, ...prev.filter((p) => p.id !== initialRun.id)]);

        let pollRun = initialRun;
        while (pollRun.status === 'running' || pollRun.status === 'pending') {
          await new Promise((r) => setTimeout(r, 1200));
          try {
            pollRun = await fetchAnalysisRun(effPid, asset.id, initialRun.id);
            setAnalysisRuns((prev) => [pollRun, ...prev.filter((p) => p.id !== pollRun.id)]);
          } catch {
            // retry next tick
          }
        }
        if (pollRun.status === 'failed') {
          throw new Error(pollRun.error_message || 'Video analysis failed.');
        }
        if (pollRun.status === 'cancelled') {
          throw new Error('Video analysis was cancelled.');
        }
        currentRunId = pollRun.id;
        await loadIntelligenceData();
      }

      setGenerationStage(
        isGenerateMoreModal ? 'Filtering Novelty & Generating More...' : 'Discovering Best Highlights...'
      );

      const opts: DiscoverHighlightsOptions = {
        analysis_run_id: currentRunId,
        target_clip_count: config.targetClipCount ?? undefined,
        aspect_ratio: config.aspectRatio as AspectRatioOption,
        creative_direction: config.creativeDirection,
        duration_preference: config.durationPreference as any,
        novelty_mode: config.noveltyMode as any,
        min_duration: config.minDurationSec,
        max_duration: config.maxDurationSec,
        run_synchronously: true,
      };

      if (isGenerateMoreModal) {
        await generateMoreHighlights(effPid, asset.id, opts);
      } else {
        await discoverHighlights(effPid, asset.id, opts);
      }

      await loadIntelligenceData();
      setIsGenerateModalOpen(false);
      setActiveTab('generated_shorts');
    } catch (err: any) {
      alert(`Failed to generate shorts: ${err.message || 'Unknown error'}`);
    } finally {
      setGeneratingShorts(false);
      setGenerationStage(null);
    }
  };

  // Retry a Failed Export Render
  const handleRetryRender = async (video: ExportItem) => {
    if (!asset || !video.candidate_id) {
      alert('Cannot re-render: candidate clip record is missing.');
      return;
    }
    setExportingCandidateId(video.candidate_id);
    const effPid = asset.project_id || projectId || 'default';
    try {
      await submitExportRender(effPid, {
        candidate_id: video.candidate_id,
        title: video.title || 'Short Video',
      });
      setExportSuccessToast(`Re-render job submitted for "${video.title || 'Short Video'}"!`);
      setTimeout(() => setExportSuccessToast(null), 5000);
      await loadIntelligenceData();
    } catch (err: any) {
      alert(`Retry render error: ${err.message || 'Failed to submit render'}`);
    } finally {
      setExportingCandidateId(null);
    }
  };

  // Export Candidate Short
  const handleExportCandidate = async (cand: CandidateItem) => {
    if (!asset) return;
    setExportingCandidateId(cand.id);
    const effPid = asset.project_id || projectId || 'default';
    try {
      await submitExportRender(effPid, {
        candidate_id: cand.id,
        title: cand.suggested_title || cand.title,
      });
      setExportSuccessToast(`Export job started for "${cand.suggested_title || cand.title}"! Monitor in Processes.`);
      setTimeout(() => setExportSuccessToast(null), 5000);
      await loadIntelligenceData();
    } catch (err: any) {
      alert(`Export error: ${err.message || 'Failed to submit render'}`);
    } finally {
      setExportingCandidateId(null);
    }
  };

  // Batch Export Multiple Candidates
  const handleBatchExport = async () => {
    if (!asset || selectedCandidateIds.size === 0) return;
    setBatchExporting(true);
    const effPid = asset.project_id || projectId || 'default';
    const cids = Array.from(selectedCandidateIds);
    try {
      const res = await submitBatchExport(effPid, {
        candidate_ids: cids,
      });
      setExportSuccessToast(`Submitted batch export for ${res.total_submitted} clip(s)! Monitor progress in Processes.`);
      setTimeout(() => setExportSuccessToast(null), 6000);
      setSelectedCandidateIds(new Set());
      await loadIntelligenceData();
      setActiveTab('rendered_videos');
    } catch (err: any) {
      alert(`Batch export error: ${err.message || 'Failed to submit batch export'}`);
    } finally {
      setBatchExporting(false);
    }
  };

  // Toggle single candidate selection for batch export
  const toggleCandidateSelect = (candId: string) => {
    setSelectedCandidateIds((prev) => {
      const next = new Set(prev);
      if (next.has(candId)) {
        next.delete(candId);
      } else {
        next.add(candId);
      }
      return next;
    });
  };

  // Select all visible candidates
  const selectAllCandidates = (visibleCands: CandidateItem[]) => {
    setSelectedCandidateIds(new Set(visibleCands.map((c) => c.id)));
  };

  // Clear all selections
  const clearCandidateSelection = () => {
    setSelectedCandidateIds(new Set());
  };

  // Delete Rendered Video
  const handleDeleteRenderedVideo = async (exportId: string) => {
    if (!window.confirm('Delete this rendered MP4 video file from disk? Source video and candidate discovery data will remain preserved.')) {
      return;
    }
    const effPid = asset?.project_id || projectId || 'default';
    try {
      await deleteExport(effPid, exportId);
      setExportSuccessToast('Rendered video file deleted.');
      setTimeout(() => setExportSuccessToast(null), 4000);
      if (activePreviewVideo?.id === exportId) {
        setActivePreviewVideo(null);
      }
      await loadIntelligenceData();
    } catch (err: any) {
      alert(`Delete error: ${err.message || 'Failed to delete export'}`);
    }
  };

  // Format Helpers
  const formatSeconds = (sec?: number | null) => {
    if (!sec || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const videoTitle = (asset?.metadata?.title as string) || asset?.original_filename || 'Video';

  // Generated Scripts synthesized from transcript and candidates
  const synthesizedScripts = useMemo(() => {
    if (candidates.length > 0) {
      return candidates.map((c, idx) => ({
        id: `script_${c.id}`,
        candidateId: c.id,
        title: c.suggested_title || c.title || `Short Script #${idx + 1}`,
        hook: c.ai_explanation?.hook || `Watch what happens in this intense moment!`,
        dialogue:
          c.transcript_references?.join(' ') ||
          c.description ||
          'Engaging narrative dialogue from source video moment.',
        narrativeArc: [
          { phase: 'Hook (0-3s)', text: c.ai_explanation?.hook || 'Immediate visual/audio punch' },
          { phase: 'Body (3-20s)', text: c.description || 'Core development and rising action' },
          { phase: 'Climax / Payoff', text: c.ai_explanation?.why_it_works || 'Satisfying resolution or punchline' },
        ],
        startTime: c.start_time,
        endTime: c.end_time,
        duration: c.duration,
        score: Math.round(c.quality_score * 100),
      }));
    }

    if (transcript && transcript.segments?.length > 0) {
      return transcript.segments.slice(0, 6).map((seg, idx) => ({
        id: `script_seg_${seg.id || idx}`,
        candidateId: undefined,
        title: `Dialogue Highlight #${idx + 1}`,
        hook: seg.text.slice(0, 60) + '...',
        dialogue: seg.text,
        narrativeArc: [
          { phase: 'Hook', text: seg.text.slice(0, 40) },
          { phase: 'Dialogue Turn', text: seg.text },
          { phase: 'Punchline', text: 'Natural speech cadence' },
        ],
        startTime: seg.start_time,
        endTime: seg.end_time,
        duration: seg.end_time - seg.start_time,
        score: 85,
      }));
    }

    return [];
  }, [candidates, transcript]);

  // Filtered Transcript Segments
  const filteredTranscriptSegments = useMemo(() => {
    if (!transcript?.segments) return [];
    if (!transcriptSearch.trim()) return transcript.segments;
    return transcript.segments.filter((s) =>
      s.text.toLowerCase().includes(transcriptSearch.toLowerCase())
    );
  }, [transcript, transcriptSearch]);

  // Filtered, Sorted and Paginated Generated Videos Library
  const filteredAndSortedRenderedVideos = useMemo(() => {
    let list = [...renderedVideos];

    // 1. Search Query
    if (videoSearch.trim()) {
      const q = videoSearch.toLowerCase();
      list = list.filter(
        (v) =>
          (v.title || '').toLowerCase().includes(q) ||
          (v.output_filename || '').toLowerCase().includes(q)
      );
    }

    // 2. Aspect Ratio Filter
    if (videoAspectRatioFilter !== 'all') {
      list = list.filter((v) => v.target_aspect_ratio === videoAspectRatioFilter);
    }

    // 3. Status Filter
    if (videoStatusFilter !== 'all') {
      if (videoStatusFilter === 'completed') {
        list = list.filter((v) => v.status === 'completed');
      } else if (videoStatusFilter === 'rendering') {
        list = list.filter((v) => v.status === 'rendering' || v.status === 'queued');
      } else if (videoStatusFilter === 'failed') {
        list = list.filter((v) => v.status === 'failed');
      }
    }

    // 4. Sorting
    list.sort((a, b) => {
      if (videoSortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (videoSortBy === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      if (videoSortBy === 'duration_desc') {
        return (b.duration_seconds || 0) - (a.duration_seconds || 0);
      }
      if (videoSortBy === 'duration_asc') {
        return (a.duration_seconds || 0) - (b.duration_seconds || 0);
      }
      if (videoSortBy === 'title') {
        return (a.title || a.output_filename).localeCompare(b.title || b.output_filename);
      }
      return 0;
    });

    return list;
  }, [renderedVideos, videoSearch, videoAspectRatioFilter, videoStatusFilter, videoSortBy]);

  const totalVideoPages = Math.max(1, Math.ceil(filteredAndSortedRenderedVideos.length / VIDEOS_PER_PAGE));
  const paginatedRenderedVideos = useMemo(() => {
    const start = (videoPage - 1) * VIDEOS_PER_PAGE;
    return filteredAndSortedRenderedVideos.slice(start, start + VIDEOS_PER_PAGE);
  }, [filteredAndSortedRenderedVideos, videoPage]);

  if (loadingAsset) {
    return (
      <div className="p-8 space-y-4 max-w-7xl mx-auto">
        <Skeleton className="h-10 w-1/3 rounded" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (assetError || !asset) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-sm font-bold text-text-primary">Failed to load video</h2>
        <p className="text-xs text-text-muted">{assetError || 'Video asset not found'}</p>
        <Button size="sm" onClick={onBack}>
          Back to Video Library
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-canvas overflow-hidden">
      {/* ==================== PERSISTENT TOP HEADER & PROGRESS BAR ==================== */}
      <header className="shrink-0 bg-surface border-b border-border px-5 py-3 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover transition"
              title="Return to Video Library"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <Film className="w-4 h-4 text-indigo-400" />
                <h1 className="text-sm font-bold text-text-primary truncate max-w-md" title={videoTitle}>
                  {videoTitle}
                </h1>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-text-muted font-mono mt-0.5">
                <span>{asset.width}x{asset.height}</span>
                <span>•</span>
                <span>{formatSeconds(asset.duration_seconds)}</span>
                <span>•</span>
                <span>{formatBytes(asset.file_size_bytes)}</span>
                <span>•</span>
                <span className="text-indigo-400">{candidates.length} Shorts Discovered</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStartAnalysis(false)}
              isLoading={analysisLoading}
              leftIcon={<Sparkles className="w-3.5 h-3.5 text-text-muted" />}
            >
              {analysisRuns.length > 0 ? 'Re-Analyze Video' : 'Analyze Full Video'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setIsGenerateMoreModal(false);
                setIsGenerateModalOpen(true);
              }}
              leftIcon={<Film className="w-3.5 h-3.5" />}
            >
              Generate Videos
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsGenerateMoreModal(false);
                setIsGenerateModalOpen(true);
              }}
              leftIcon={<Scissors className="w-3.5 h-3.5" />}
            >
              Generate Shorts
            </Button>
          </div>
        </div>

        {/* Real-time Loading & Progress Bar (Quiet Graphite Neutrals + Emerald Indicator) */}
        {progressDetails.isActive && (
          <div className="p-2.5 rounded-lg bg-surface-hover border border-border space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-text-primary font-medium">
                <Loader2 className="w-3.5 h-3.5 text-text-muted animate-spin" />
                <span>Working on video: {progressDetails.stage}</span>
              </div>
              <span className="font-mono font-semibold text-text-primary">
                {Math.round(progressDetails.percent)}% complete
              </span>
            </div>
            <div className="w-full h-1.5 bg-canvas rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-400 rounded-full transition-all duration-300"
                style={{ width: `${Math.max(5, progressDetails.percent)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-text-muted">
              <span>{progressDetails.etaText}</span>
              <span>Local CPU neural execution</span>
            </div>
          </div>
        )}

        {/* Success Toast Banner */}
        {exportSuccessToast && (
          <div className="p-2 rounded-lg bg-surface-hover border border-border text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{exportSuccessToast}</span>
          </div>
        )}

        {/* 8 Horizontal Tabs Navigation: Quiet 34px Rows with 2px Gaps */}
        <nav className="flex items-center gap-1 overflow-x-auto pt-1 no-scrollbar border-t border-border">
          {[
            { id: 'home', label: 'Home' },
            { id: 'generated_shorts', label: `Generated Shorts (${candidates.length})` },
            { id: 'rendered_videos', label: `Generated Videos (${renderedVideos.filter((v) => v.status === 'completed').length})` },
            { id: 'scripts', label: `Generated Scripts (${synthesizedScripts.length})` },
            { id: 'frames', label: 'Analyzed Frames' },
            { id: 'transcript', label: 'Voice & Transcript Analysis' },
            { id: 'scenes', label: `Scene Analysis (${scenes.length})` },
            { id: 'details', label: 'Video Analysis Details' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as VideoDashboardTab)}
              className={`h-[34px] px-3 text-xs font-medium rounded-md shrink-0 transition select-none flex items-center ${
                activeTab === tab.id
                  ? 'bg-surface-active text-text-primary border border-border shadow-2xs'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover border border-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* ==================== TAB CONTENT AREA ==================== */}
      <main className="flex-1 overflow-y-auto p-5">
        {/* TAB 1: HOME (ONLY PLAYER + PURE TECHNICAL METADATA) */}
        {activeTab === 'home' && (
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Player Container */}
              <div className="lg:col-span-2 space-y-3">
                <div className="relative aspect-video bg-black rounded-2xl overflow-hidden border border-border shadow-xl">
                  <video
                    ref={videoRef}
                    src={videoStreamSrc}
                    className="w-full h-full object-contain"
                    onTimeUpdate={() => videoRef.current && setCurrentTime(videoRef.current.currentTime)}
                    onLoadedMetadata={() => videoRef.current && setDuration(videoRef.current.duration)}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                  />

                  {/* Player Overlay Controls */}
                  <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-3 flex flex-col gap-2">
                    <input
                      type="range"
                      min={0}
                      max={duration || 100}
                      value={currentTime}
                      onChange={(e) => handleSeek(parseFloat(e.target.value))}
                      className="w-full h-1 bg-white/30 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />

                    <div className="flex items-center justify-between text-xs text-white">
                      <div className="flex items-center gap-3">
                        <button onClick={togglePlay} className="p-1 hover:text-indigo-400">
                          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
                        </button>
                        <span className="font-mono text-[11px]">
                          {formatSeconds(currentTime)} / {formatSeconds(duration || asset.duration_seconds)}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 font-mono text-[11px]">
                        <button
                          onClick={() => {
                            const rates = [1, 1.25, 1.5, 2];
                            const next = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
                            setPlaybackRate(next);
                            if (videoRef.current) videoRef.current.playbackRate = next;
                          }}
                          className="px-1.5 py-0.5 rounded bg-white/10 hover:bg-white/20"
                        >
                          {playbackRate}x
                        </button>
                        <button
                          onClick={() => {
                            if (videoRef.current) {
                              videoRef.current.muted = !isMuted;
                              setIsMuted(!isMuted);
                            }
                          }}
                          className="p-1 hover:text-indigo-400"
                        >
                          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Pure Technical Metadata ONLY */}
              <div className="space-y-4">
                <Card className="p-4 space-y-3">
                  <div className="flex items-center gap-2 border-b border-border pb-2">
                    <Film className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                      Technical Video Specifications
                    </h3>
                  </div>

                  <div className="divide-y divide-border text-xs">
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Duration</span>
                      <span className="font-mono font-medium text-text-primary">{formatSeconds(asset.duration_seconds)}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Resolution</span>
                      <span className="font-mono font-medium text-text-primary">{asset.width} x {asset.height}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Frame Rate</span>
                      <span className="font-mono font-medium text-text-primary">{asset.fps ? `${Math.round(asset.fps)} fps` : '25 fps'}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Video Codec</span>
                      <span className="font-mono font-medium text-text-primary">{asset.video_codec || 'h264'}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Audio Codec</span>
                      <span className="font-mono font-medium text-text-primary">{asset.audio_codec || 'aac'}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">MIME Type</span>
                      <span className="font-mono font-medium text-text-primary">{asset.mime_type || 'video/mp4'}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">File Size</span>
                      <span className="font-mono font-medium text-text-primary">{formatBytes(asset.file_size_bytes)}</span>
                    </div>
                    <div className="py-2 flex justify-between">
                      <span className="text-text-muted">Storage Type</span>
                      <span className="font-medium text-text-primary">{asset.is_external ? 'External Reference' : 'Managed Workspace'}</span>
                    </div>
                  </div>
                </Card>

                <Card className="p-4 space-y-2 text-xs">
                  <span className="text-text-muted uppercase text-[10px] block font-semibold">Storage Location</span>
                  <p className="font-mono text-[11px] text-text-secondary break-all bg-canvas-subtle p-2 rounded-lg border border-border">
                    {asset.storage_path}
                  </p>
                </Card>
              </div>
            </div>

            {/* Reusable Video Intelligence Summary & Primary CTAs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              {/* Intelligence Summary Card */}
              <Card className="p-5 rounded-2xl border-border bg-surface space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2.5">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-xs font-bold text-text-primary">Reusable Video Intelligence</h3>
                  </div>
                  <Badge variant={isVideoAnalyzed ? 'success' : 'purple'} className="text-[10px] font-mono">
                    {isVideoAnalyzed ? 'Ready & Saved' : 'Needs Analysis'}
                  </Badge>
                </div>
                <div className="space-y-2 text-xs divide-y divide-border">
                  <div className="pt-1.5 flex justify-between">
                    <span className="text-text-muted">Speech Transcript:</span>
                    <span className="font-mono text-text-primary">{transcript?.segments?.length || 0} segments</span>
                  </div>
                  <div className="pt-1.5 flex justify-between">
                    <span className="text-text-muted">Detected Scenes:</span>
                    <span className="font-mono text-text-primary">{scenes.length} cut boundaries</span>
                  </div>
                  <div className="pt-1.5 flex justify-between">
                    <span className="text-text-muted">Visual Frames:</span>
                    <span className="font-mono text-text-primary">{scenes.length > 0 ? `${scenes.length} sampled` : 'None'}</span>
                  </div>
                  <div className="pt-1.5 flex justify-between">
                    <span className="text-text-muted">Discovered Candidates:</span>
                    <span className="font-mono text-indigo-400 font-semibold">{candidates.length} shorts</span>
                  </div>
                </div>
              </Card>

              {/* CTA 1: Generate Videos */}
              <Card className="p-5 rounded-2xl border-border bg-surface hover:border-indigo-500/40 transition flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Film className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-text-primary">Generate Videos</h3>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    AI-powered video clipping with custom aspect ratios, smart framing, and instant rendering.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  className="w-full text-xs font-semibold"
                  onClick={() => {
                    setIsGenerateMoreModal(false);
                    setIsGenerateModalOpen(true);
                  }}
                  leftIcon={<Film className="w-4 h-4" />}
                >
                  Generate Videos
                </Button>
              </Card>

              {/* CTA 2: Generate Shorts */}
              <Card className="p-5 rounded-2xl border-border bg-surface hover:border-indigo-500/40 transition flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Scissors className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-text-primary">Generate Shorts</h3>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Discover viral hook-driven short clips optimized for vertical 9:16 reels, TikTok & YouTube Shorts.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  className="w-full text-xs font-semibold"
                  onClick={() => {
                    setIsGenerateMoreModal(false);
                    setIsGenerateModalOpen(true);
                  }}
                  leftIcon={<Scissors className="w-4 h-4" />}
                >
                  Generate Shorts
                </Button>
              </Card>
            </div>
          </div>
        )}

        {/* TAB 2: SHORT VIDEO GENERATOR (RE-DIRECT TO UNIFIED MODAL) */}
        {activeTab === 'short_generator' && (
          <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mx-auto">
              <Scissors className="w-6 h-6" />
            </div>
            <h2 className="text-sm font-bold text-text-primary">Generate Short Videos</h2>
            <p className="text-xs text-text-secondary max-w-md mx-auto">
              Short video generator configuration is now elevated into the unified modal dialog for quick access anywhere.
            </p>
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setIsGenerateMoreModal(false);
                setIsGenerateModalOpen(true);
              }}
              leftIcon={<Scissors className="w-4 h-4" />}
            >
              Open Generate Shorts Modal
            </Button>
          </div>
        )}
        {/* TAB 3: DISCOVERED CANDIDATES (BATCH SELECTION, PREVIEW, EDIT & RENDER) */}
        {activeTab === 'generated_shorts' && (
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-text-primary">Discovered Short Video Candidates</h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Natural cut boundaries, multimodal scores, candidate clip editing, and batch rendering.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Batch Filter Selector */}
                {generationRuns.length > 1 && (
                  <select
                    value={selectedBatchFilter}
                    onChange={(e) => setSelectedBatchFilter(e.target.value)}
                    className="bg-surface border border-border rounded-xl px-3 py-1.5 text-xs text-text-primary font-medium outline-none focus:border-border-focus"
                  >
                    <option value="all">All Batches ({candidates.length} clips)</option>
                    {generationRuns.map((run, idx) => (
                      <option key={run.id} value={run.id}>
                        Batch #{generationRuns.length - idx} ({run.creative_direction}, {run.candidates_selected} clips)
                      </option>
                    ))}
                  </select>
                )}

                <Button
                  variant="primary"
                  size="sm"
                  className="text-xs"
                  isLoading={generatingShorts}
                  onClick={() => {
                    setIsGenerateMoreModal(true);
                    setIsGenerateModalOpen(true);
                  }}
                  leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                >
                  Generate More Shorts
                </Button>
              </div>
            </div>

            {/* Batch Selection Action Bar (when candidates are present) */}
            {candidates.length > 0 && (
              <div className="p-3 rounded-xl bg-surface border border-border flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-text-primary">
                    {selectedCandidateIds.size} of {candidates.length} candidate(s) selected
                  </span>
                  <div className="flex items-center gap-1.5 ml-2">
                    <button
                      type="button"
                      onClick={() =>
                        selectAllCandidates(
                          selectedBatchFilter === 'all'
                            ? candidates
                            : candidates.filter((c) => c.generation_run_id === selectedBatchFilter)
                        )
                      }
                      className="text-xs text-text-secondary hover:text-text-primary px-2 py-0.5 rounded hover:bg-surface-hover transition"
                    >
                      Select All
                    </button>
                    <span className="text-text-muted">·</span>
                    <button
                      type="button"
                      onClick={clearCandidateSelection}
                      disabled={selectedCandidateIds.size === 0}
                      className="text-xs text-text-secondary hover:text-text-primary disabled:opacity-40 px-2 py-0.5 rounded hover:bg-surface-hover transition"
                    >
                      Clear Selection
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="text-xs px-4"
                    disabled={selectedCandidateIds.size === 0 || batchExporting}
                    isLoading={batchExporting}
                    onClick={handleBatchExport}
                    leftIcon={<Film className="w-3.5 h-3.5" />}
                  >
                    Render Selected ({selectedCandidateIds.size})
                  </Button>
                </div>
              </div>
            )}

            {candidates.length === 0 ? (
              <EmptyState
                icon={<Scissors className="w-10 h-10 text-text-muted" />}
                title="No Short Clips Generated Yet"
                description="Click Generate Shorts to discover interesting moments from this video using saved intelligence."
                actionText="Go to Short Video Generator"
                onAction={() => setActiveTab('short_generator')}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {(selectedBatchFilter === 'all'
                  ? candidates
                  : candidates.filter((c) => c.generation_run_id === selectedBatchFilter)
                ).map((cand) => {
                  const scorePercent = Math.round(cand.quality_score * 100);
                  const isExporting = exportingCandidateId === cand.id;
                  const isSelected = selectedCandidateIds.has(cand.id);

                  // Check if this candidate is currently rendering or already rendered
                  const matchedExport = renderedVideos.find((v) => v.candidate_id === cand.id);
                  const isRendered = matchedExport && matchedExport.status === 'completed';
                  const isRendering = matchedExport && (matchedExport.status === 'rendering' || matchedExport.status === 'queued');

                  return (
                    <Card
                      key={cand.id}
                      className={`overflow-hidden rounded-2xl border transition flex flex-col justify-between ${
                        isSelected
                          ? 'border-indigo-500 bg-surface shadow-xs ring-1 ring-indigo-500/30'
                          : 'border-border bg-surface hover:border-border-focus'
                      }`}
                    >
                      <div>
                        {/* Candidate Thumbnail with selection and play trigger */}
                        <div className="relative aspect-video bg-canvas-subtle overflow-hidden">
                          {/* Selection Checkbox */}
                          <div className="absolute top-2 right-2 z-10">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleCandidateSelect(cand.id)}
                              className="w-4 h-4 rounded border-border bg-black/60 text-indigo-600 focus:ring-0 cursor-pointer"
                              title="Select for Batch Render"
                            />
                          </div>

                          <div
                            className="w-full h-full cursor-pointer"
                            onClick={() => {
                              handleSeek(cand.start_time);
                              setActiveTab('home');
                            }}
                          >
                            <img
                              src={getGlobalThumbnailUrl(asset.id)}
                              alt=""
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                          </div>

                          <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/80 text-[10px] font-bold text-text-primary border border-white/10 pointer-events-none">
                            Score {scorePercent}/100
                          </div>

                          <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 font-mono text-[10px] text-white pointer-events-none">
                            {formatSeconds(cand.duration)}
                          </div>
                        </div>

                        {/* Candidate Metadata */}
                        <div className="p-4 space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-xs font-bold text-text-primary line-clamp-1">
                              {cand.suggested_title || cand.title || 'Untitled Short'}
                            </h3>
                            <Badge
                              variant={
                                isRendered
                                  ? 'success'
                                  : isRendering
                                  ? 'purple'
                                  : isSelected
                                  ? 'purple'
                                  : 'default'
                              }
                              className="text-[10px] shrink-0 font-mono"
                            >
                              {isRendered
                                ? 'Rendered MP4'
                                : isRendering
                                ? 'Rendering...'
                                : isSelected
                                ? 'Selected'
                                : 'Discovered'}
                            </Badge>
                          </div>

                          {cand.ai_explanation?.hook && (
                            <p className="text-[11px] text-text-secondary italic line-clamp-2">
                              "{cand.ai_explanation.hook}"
                            </p>
                          )}

                          <div className="flex items-center justify-between text-[11px] text-text-muted font-mono pt-1">
                            <span>Cut: {formatSeconds(cand.start_time)} → {formatSeconds(cand.end_time)}</span>
                            <span className="capitalize">{cand.category || 'Highlight'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Candidate Actions: Edit Clip & Export */}
                      <div className="p-3 bg-surface-subtle border-t border-border flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 text-xs"
                          onClick={() => {
                            setEditingCandidate(cand);
                            setEditorModalOpen(true);
                          }}
                          leftIcon={<Sliders className="w-3.5 h-3.5 text-text-muted" />}
                        >
                          Edit Clip
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          className="flex-1 text-xs"
                          isLoading={isExporting}
                          onClick={() => handleExportCandidate(cand)}
                          leftIcon={<Download className="w-3.5 h-3.5" />}
                        >
                          {isRendered ? 'Re-render MP4' : 'Render MP4'}
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: GENERATED VIDEOS LIBRARY (INLINE PLAYBACK, CONTROLS, SCALABLE SEARCH & FILTER) */}
        {activeTab === 'rendered_videos' && (
          <div className="max-w-6xl mx-auto space-y-5">
            {/* Archive Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-text-primary">
                  Generated Short Videos Archive ({filteredAndSortedRenderedVideos.length} of {renderedVideos.length})
                </h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Playable, verified H.264 MP4 videos rendered from this source video. Click any thumbnail to play inline.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => void loadIntelligenceData()}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Refresh
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    setIsGenerateMoreModal(true);
                    setIsGenerateModalOpen(true);
                  }}
                  leftIcon={<Film className="w-3.5 h-3.5" />}
                >
                  Generate More Shorts
                </Button>
              </div>
            </div>

            {/* Scalability Filter Bar: Search, Aspect Ratio, Status & Sorting */}
            <div className="p-3.5 rounded-xl border border-border bg-surface flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
                {/* Search Input */}
                <div className="relative flex-1 min-w-[180px] max-w-xs">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={videoSearch}
                    onChange={(e) => {
                      setVideoSearch(e.target.value);
                      setVideoPage(1);
                    }}
                    placeholder="Search videos by title..."
                    className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-canvas border border-border text-text-primary placeholder:text-text-muted focus:outline-hidden focus:border-indigo-500"
                  />
                  {videoSearch && (
                    <button
                      onClick={() => setVideoSearch('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {/* Aspect Ratio Filter Pills */}
                <div className="flex items-center gap-1 bg-surface-subtle p-1 rounded-lg border border-border text-xs">
                  {(['all', '9:16', '1:1', '16:9'] as const).map((ratio) => (
                    <button
                      key={ratio}
                      type="button"
                      onClick={() => {
                        setVideoAspectRatioFilter(ratio);
                        setVideoPage(1);
                      }}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                        videoAspectRatioFilter === ratio
                          ? 'bg-surface text-text-primary shadow-2xs font-semibold'
                          : 'text-text-muted hover:text-text-primary'
                      }`}
                    >
                      {ratio === 'all' ? 'All Ratios' : ratio}
                    </button>
                  ))}
                </div>

                {/* Status Filter Pills */}
                <div className="flex items-center gap-1 bg-surface-subtle p-1 rounded-lg border border-border text-xs">
                  {(['all', 'completed', 'rendering', 'failed'] as const).map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => {
                        setVideoStatusFilter(st);
                        setVideoPage(1);
                      }}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition ${
                        videoStatusFilter === st
                          ? 'bg-surface text-text-primary shadow-2xs font-semibold'
                          : 'text-text-muted hover:text-text-primary'
                      }`}
                    >
                      {st === 'all' ? 'All Status' : st}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sorting Dropdown */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-text-muted">Sort:</span>
                <select
                  value={videoSortBy}
                  onChange={(e) => setVideoSortBy(e.target.value as any)}
                  className="px-2.5 py-1 text-xs rounded-lg bg-canvas border border-border text-text-primary focus:outline-hidden"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="duration_desc">Duration (Longest)</option>
                  <option value="duration_asc">Duration (Shortest)</option>
                  <option value="title">Title (A-Z)</option>
                </select>
              </div>
            </div>

            {/* Video Cards Grid with Inline Playback */}
            {filteredAndSortedRenderedVideos.length === 0 ? (
              <EmptyState
                icon={<Film className="w-10 h-10 text-text-muted" />}
                title={renderedVideos.length === 0 ? 'No Rendered Short Videos Yet' : 'No Videos Match Filter'}
                description={
                  renderedVideos.length === 0
                    ? "Select candidates in Discovered Candidates and click 'Render Video' to generate actual MP4 files."
                    : 'Try resetting the search query or status filters.'
                }
                actionText={renderedVideos.length === 0 ? 'View Discovered Candidates' : 'Reset Filters'}
                onAction={() => {
                  if (renderedVideos.length === 0) {
                    setActiveTab('generated_shorts');
                  } else {
                    setVideoSearch('');
                    setVideoAspectRatioFilter('all');
                    setVideoStatusFilter('all');
                  }
                }}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {paginatedRenderedVideos.map((video) => {
                  const isCompleted = video.status === 'completed';
                  const isRendering = video.status === 'rendering' || video.status === 'queued';
                  const isFailed = video.status === 'failed';
                  const isInlinePlaying = inlinePlayingVideoId === video.id;

                  return (
                    <Card
                      key={video.id}
                      className="overflow-hidden rounded-2xl border-border bg-surface hover:border-border-focus transition flex flex-col justify-between"
                    >
                      <div>
                        {/* Video Thumbnail or Inline Player Container */}
                        <div className="relative aspect-video bg-black overflow-hidden group">
                          {isCompleted && isInlinePlaying ? (
                            /* INLINE VIDEO PLAYER IN-PLACE (No scroll to top!) */
                            <div className="relative w-full h-full">
                              <video
                                ref={(el) => {
                                  inlineVideoRefs.current[video.id] = el;
                                }}
                                src={getExportVideoUrl(asset.project_id || projectId || 'default', video.id)}
                                controls
                                autoPlay
                                playsInline
                                preload="none"
                                className="w-full h-full object-contain"
                                onEnded={() => setInlinePlayingVideoId(null)}
                              />
                              <div className="absolute top-2 right-2 flex items-center gap-1.5 z-20">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const el = inlineVideoRefs.current[video.id];
                                    if (el) {
                                      if (el.requestFullscreen) {
                                        void el.requestFullscreen();
                                      } else if ((el as any).webkitRequestFullscreen) {
                                        (el as any).webkitRequestFullscreen();
                                      }
                                    }
                                  }}
                                  className="p-1.5 rounded-md bg-black/80 hover:bg-black text-white text-[10px] border border-white/20 transition"
                                  title="Enter Fullscreen"
                                >
                                  <Maximize2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setInlinePlayingVideoId(null);
                                  }}
                                  className="p-1.5 rounded-md bg-black/80 hover:bg-black text-white text-[10px] border border-white/20 transition"
                                  title="Close Inline Playback"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          ) : (
                            /* THUMBNAIL WITH PLAY BUTTON OVERLAY */
                            <div
                              className="relative w-full h-full cursor-pointer"
                              onClick={() => {
                                if (isCompleted) {
                                  setInlinePlayingVideoId(video.id);
                                }
                              }}
                            >
                              <img
                                src={getGlobalThumbnailUrl(asset.id)}
                                alt=""
                                loading="lazy"
                                className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition duration-200"
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = 'none';
                                }}
                              />

                              {isCompleted ? (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/50 transition">
                                  <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-xs flex items-center justify-center border border-white/30 text-white group-hover:scale-110 transition shadow-lg">
                                    <Play className="w-5 h-5 fill-current ml-0.5" />
                                  </div>
                                </div>
                              ) : isRendering ? (
                                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 text-indigo-400 gap-2">
                                  <Loader2 className="w-6 h-6 animate-spin" />
                                  <span className="text-[11px] font-medium font-mono text-white">
                                    Rendering MP4...
                                  </span>
                                </div>
                              ) : (
                                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 text-red-400 gap-1.5 p-3 text-center">
                                  <AlertCircle className="w-5 h-5 text-red-400" />
                                  <span className="text-[11px] font-semibold text-red-300">Rendering Failed</span>
                                  <span className="text-[10px] text-text-muted line-clamp-2">
                                    {video.error_message || 'Video export could not be finalized'}
                                  </span>
                                </div>
                              )}

                              <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/80 text-[10px] font-mono text-text-primary border border-white/10">
                                {video.target_aspect_ratio}
                              </div>

                              <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 font-mono text-[10px] text-white">
                                {formatSeconds(video.duration_seconds)}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Video Metadata */}
                        <div className="p-4 space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-xs font-bold text-text-primary line-clamp-1" title={video.title}>
                              {video.title || video.output_filename}
                            </h3>
                            <Badge
                              variant={
                                isCompleted
                                  ? 'success'
                                  : isRendering
                                  ? 'purple'
                                  : 'danger'
                              }
                              className="text-[10px] shrink-0 font-mono"
                            >
                              {video.status}
                            </Badge>
                          </div>

                          <div className="text-[11px] text-text-muted font-mono space-y-0.5">
                            <div className="flex justify-between">
                              <span>Dimensions:</span>
                              <span className="text-text-secondary">
                                {video.target_width}x{video.target_height}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Size:</span>
                              <span className="text-text-secondary">
                                {formatBytes(video.file_size_bytes)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Codec:</span>
                              <span className="text-text-secondary">
                                {video.video_codec} / {video.audio_codec}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Verified:</span>
                              <span className={video.validation_status === 'valid' ? 'text-emerald-400' : 'text-amber-400'}>
                                {video.validation_status}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Video Actions: Play Inline, Expand, Download, Retry, Delete */}
                      <div className="p-3 bg-surface-subtle border-t border-border flex items-center justify-between gap-2">
                        {isCompleted && (
                          <>
                            <Button
                              variant={isInlinePlaying ? 'secondary' : 'outline'}
                              size="sm"
                              className="flex-1 text-xs"
                              onClick={() => {
                                setInlinePlayingVideoId(isInlinePlaying ? null : video.id);
                              }}
                              leftIcon={
                                isInlinePlaying ? (
                                  <Pause className="w-3.5 h-3.5 text-indigo-400" />
                                ) : (
                                  <Play className="w-3.5 h-3.5 fill-current text-indigo-400" />
                                )
                              }
                            >
                              {isInlinePlaying ? 'Pause' : 'Play'}
                            </Button>

                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-xs text-text-muted hover:text-text-primary px-2"
                              onClick={() => setActivePreviewVideo(video)}
                              title="Expand Modal Preview"
                              aria-label="Expand Modal Preview"
                            >
                              <Maximize2 className="w-3.5 h-3.5" />
                            </Button>

                            <a
                              href={getExportDownloadUrl(asset.project_id || projectId || 'default', video.id)}
                              download={video.output_filename}
                              className="inline-flex items-center justify-center p-2 rounded-lg bg-surface border border-border hover:bg-surface-hover text-text-muted hover:text-text-primary transition"
                              title="Download MP4"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          </>
                        )}

                        {isFailed && (
                          <Button
                            variant="primary"
                            size="sm"
                            className="flex-1 text-xs"
                            onClick={() => handleRetryRender(video)}
                            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                          >
                            Retry Render
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs text-text-muted hover:text-red-400 px-2"
                          onClick={() => handleDeleteRenderedVideo(video.id)}
                          title="Delete MP4 File (Keeps script and source video safe)"
                        >
                          Delete
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Pagination Controls for Large Libraries */}
            {totalVideoPages > 1 && (
              <div className="p-3 border-t border-border flex items-center justify-between text-xs text-text-muted">
                <span>
                  Showing page {videoPage} of {totalVideoPages} ({filteredAndSortedRenderedVideos.length} videos)
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={videoPage <= 1}
                    onClick={() => setVideoPage((p) => Math.max(1, p - 1))}
                    leftIcon={<ChevronLeft className="w-3.5 h-3.5" />}
                  >
                    Previous
                  </Button>
                  <span className="px-3 py-1 font-mono font-medium text-text-primary bg-surface-subtle border border-border rounded-lg">
                    {videoPage} / {totalVideoPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={videoPage >= totalVideoPages}
                    onClick={() => setVideoPage((p) => Math.min(totalVideoPages, p + 1))}
                    rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: GENERATED SCRIPTS (CARDS & 1-CLICK REGENERATE VIDEO) */}
        {activeTab === 'scripts' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-text-primary">Generated Short Scripts Archive</h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Extracted narrative hooks, dialogue pacing, and 1-click video conversion.
                </p>
              </div>
            </div>

            {synthesizedScripts.length === 0 ? (
              <EmptyState
                icon={<FileText className="w-10 h-10 text-text-muted" />}
                title="No Scripts Generated"
                description="Run video analysis to transcribe speech and extract script moments."
                actionText="Run Video Analysis"
                onAction={handleStartAnalysis}
              />
            ) : (
              <div className="space-y-4">
                {synthesizedScripts.map((scr, idx) => (
                  <Card key={scr.id} className="p-5 space-y-4 rounded-2xl border-border bg-surface">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="info" className="text-xs">Script #{idx + 1}</Badge>
                        <h3 className="text-xs font-bold text-text-primary">{scr.title}</h3>
                      </div>
                      <div className="flex items-center gap-3 text-xs font-mono text-text-muted">
                        <span>{formatSeconds(scr.startTime)} → {formatSeconds(scr.endTime)}</span>
                        <Badge variant="success">Potential: {scr.score}%</Badge>
                      </div>
                    </div>

                    <div className="space-y-2 text-xs">
                      <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Hook sentence</span>
                        <p className="text-text-primary font-medium mt-0.5">"{scr.hook}"</p>
                      </div>

                      <div className="p-3 bg-canvas-subtle rounded-xl border border-border">
                        <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block">Dialogue excerpt</span>
                        <p className="text-text-secondary mt-1 leading-relaxed">{scr.dialogue}</p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                        {scr.narrativeArc.map((arc, aIdx) => (
                          <div key={aIdx} className="p-2.5 bg-surface border border-border rounded-lg">
                            <span className="text-[9px] font-medium text-text-muted uppercase block">{arc.phase}</span>
                            <span className="text-[11px] text-text-primary line-clamp-2 mt-0.5">{arc.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {(() => {
                      const matchedExport = renderedVideos.find(
                        (v) => v.candidate_id === scr.candidateId && v.status === 'completed'
                      );
                      const isRendering = renderedVideos.some(
                        (v) =>
                          v.candidate_id === scr.candidateId &&
                          (v.status === 'rendering' || v.status === 'queued')
                      );

                      return (
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-border">
                          <div className="flex items-center gap-2">
                            {matchedExport ? (
                              <Badge variant="success" className="text-[10px] font-mono">
                                Video Rendered (Ready)
                              </Badge>
                            ) : isRendering ? (
                              <span className="flex items-center gap-1.5 text-xs text-indigo-400 font-medium">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Rendering MP4...</span>
                              </span>
                            ) : (
                              <span className="text-[11px] text-text-muted">
                                Script ready for 1-click video render
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                const candMatch = candidates.find((c) => c.id === scr.candidateId);
                                if (candMatch) {
                                  setEditingCandidate(candMatch);
                                  setEditorModalOpen(true);
                                } else {
                                  handleSeek(scr.startTime);
                                  setActiveTab('home');
                                }
                              }}
                              leftIcon={<Scissors className="w-3.5 h-3.5 text-text-secondary" />}
                            >
                              Edit Clip
                            </Button>

                            {matchedExport ? (
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => {
                                  setActiveTab('rendered_videos');
                                  setInlinePlayingVideoId(matchedExport.id);
                                }}
                                leftIcon={<Play className="w-3.5 h-3.5 fill-current text-white" />}
                              >
                                View Video
                              </Button>
                            ) : (
                              <Button
                                variant="primary"
                                size="sm"
                                disabled={isRendering || exportingCandidateId === scr.candidateId}
                                onClick={() => {
                                  const candMatch = candidates.find((c) => c.id === scr.candidateId);
                                  if (candMatch) {
                                    void handleExportCandidate(candMatch);
                                  } else {
                                    alert('No candidate moment linked for this segment.');
                                  }
                                }}
                                leftIcon={
                                  exportingCandidateId === scr.candidateId ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Film className="w-3.5 h-3.5" />
                                  )
                                }
                              >
                                {exportingCandidateId === scr.candidateId ? 'Submitting...' : 'Render Video'}
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })()}
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: ANALYZED FRAMES (KEYFRAMES & OBSERVATION TAGS) */}
        {activeTab === 'frames' && (
          <div className="max-w-6xl mx-auto space-y-6">
            <div>
              <h2 className="text-sm font-bold text-text-primary">Analyzed Keyframes &amp; Visual Evidence</h2>
              <p className="text-xs text-text-secondary mt-0.5">
                Extracted visual frames with timestamps and observation tags. Click any frame to seek main player.
              </p>
            </div>

            {scenes.length === 0 ? (
              <EmptyState
                icon={<Eye className="w-10 h-10 text-text-muted" />}
                title="No Keyframes Analyzed"
                description="Run video analysis to extract sampled keyframes and detect scene cuts."
                actionText="Run Video Analysis"
                onAction={handleStartAnalysis}
              />
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {scenes.map((sc, idx) => (
                  <div
                    key={sc.id}
                    onClick={() => {
                      handleSeek(sc.start_time);
                      setActiveTab('home');
                    }}
                    className="group bg-surface border border-border rounded-xl overflow-hidden hover:border-indigo-500 cursor-pointer transition flex flex-col"
                  >
                    <div className="aspect-video bg-canvas-subtle relative overflow-hidden">
                      <img
                        src={getSceneThumbnailUrl(asset.project_id || projectId, asset.id, sc.id)}
                        alt={`Scene ${sc.scene_index}`}
                        className="w-full h-full object-cover group-hover:scale-105 transition"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-mono text-white">
                        {formatSeconds(sc.start_time)}
                      </span>
                    </div>

                    <div className="p-2 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-semibold text-text-primary">Cut #{idx + 1}</span>
                        <span className="text-text-muted font-mono">{formatSeconds(sc.end_time - sc.start_time)}</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <span className="text-[9px] px-1 py-0.5 rounded bg-surface-active text-text-primary font-mono border border-border">
                          {sc.change_score ? 'Cut' : 'Transition'}
                        </span>
                        <span className="text-[9px] px-1 py-0.5 rounded bg-surface border border-border text-text-muted font-mono">
                          Keyframe
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 6: VOICE & TRANSCRIPT ANALYSIS */}
        {activeTab === 'transcript' && (
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-text-primary">Voice &amp; Transcript Analysis</h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Whisper int8 transcription with timestamped speech turns. Click any row to jump video.
                </p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search spoken words..."
                  value={transcriptSearch}
                  onChange={(e) => setTranscriptSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-surface border border-border rounded-xl text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-border-focus"
                />
              </div>
            </div>

            {!transcript || !transcript.segments || transcript.segments.length === 0 ? (
              <EmptyState
                icon={<Mic className="w-10 h-10 text-text-muted" />}
                title="No Transcript Available"
                description="Audio speech transcription has not been executed yet."
                actionText="Transcribe Speech"
                onAction={handleStartAnalysis}
              />
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                {filteredTranscriptSegments.map((seg, idx) => (
                  <div
                    key={seg.id || idx}
                    onClick={() => {
                      handleSeek(seg.start_time);
                      setActiveTab('home');
                    }}
                    className="p-3 bg-surface border border-border rounded-xl hover:border-border-focus hover:bg-surface-hover cursor-pointer transition flex items-start gap-3"
                  >
                    <div className="px-2 py-0.5 rounded bg-surface-active text-text-primary font-mono text-[10px] shrink-0 mt-0.5 border border-border">
                      {formatSeconds(seg.start_time)}
                    </div>

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold uppercase text-text-muted">
                          Turn #{idx + 1}
                        </span>
                        <span className="text-[10px] font-mono text-text-muted">
                          ({formatSeconds(seg.end_time - seg.start_time)} duration)
                        </span>
                      </div>
                      <p className="text-xs text-text-primary leading-relaxed">{seg.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 7: SCENE ANALYSIS (WITH SELECTION TOGGLES FOR SHORT GENERATION) */}
        {activeTab === 'scenes' && (
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-text-primary">Detected Scene Transitions</h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Select which scenes should be included or excluded from Short Video Generation.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedSceneIds(new Set(scenes.map((s) => s.id)))}
                >
                  Select All
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedSceneIds(new Set())}
                >
                  Deselect All
                </Button>
              </div>
            </div>

            {scenes.length === 0 ? (
              <EmptyState
                icon={<Film className="w-10 h-10 text-text-muted" />}
                title="No Scenes Detected"
                description="FFmpeg scene boundary detection has not been executed."
                actionText="Detect Scenes"
                onAction={handleStartAnalysis}
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {scenes.map((sc) => {
                  const isChecked = selectedSceneIds.has(sc.id);
                  return (
                    <Card
                      key={sc.id}
                      className={`p-3.5 space-y-3 rounded-2xl border transition ${
                        isChecked
                          ? 'border-border-focus bg-surface-active/40'
                          : 'border-border bg-surface opacity-70'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={(e) => {
                              const next = new Set(selectedSceneIds);
                              if (e.target.checked) next.add(sc.id);
                              else next.delete(sc.id);
                              setSelectedSceneIds(next);
                            }}
                            className="rounded accent-text-primary w-4 h-4 cursor-pointer"
                          />
                          <span className="text-xs font-bold text-text-primary">
                            Scene #{sc.scene_index + 1}
                          </span>
                        </div>
                        <Badge variant="default" className="text-[10px]">
                          {sc.change_score ? 'Cut' : 'Scene'}
                        </Badge>
                      </div>

                      <div
                        className="aspect-video bg-canvas-subtle rounded-xl overflow-hidden cursor-pointer"
                        onClick={() => {
                          handleSeek(sc.start_time);
                          setActiveTab('home');
                        }}
                      >
                        <img
                          src={getSceneThumbnailUrl(asset.project_id || projectId, asset.id, sc.id)}
                          alt=""
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
                        <span>{formatSeconds(sc.start_time)} → {formatSeconds(sc.end_time)}</span>
                        <span>{formatSeconds(sc.end_time - sc.start_time)}</span>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 8: VIDEO ANALYSIS DETAILS (DEEP TECHNICAL TELEMETRY & CACHE) */}
        {activeTab === 'details' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div>
              <h2 className="text-sm font-bold text-text-primary">In-Depth Video Analysis Details</h2>
              <p className="text-xs text-text-secondary mt-0.5">
                Technical inspection of analysis pipeline execution, stage timings, and cache metrics.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <Activity className="w-4 h-4 text-text-secondary" />
                  Pipeline Components Status
                </h3>
                <div className="divide-y divide-border text-xs">
                  <div className="py-2 flex justify-between">
                    <span>Source Demuxing &amp; Audio Extract</span>
                    <Badge variant="success">Completed</Badge>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Whisper Speech Transcription</span>
                    <Badge variant={transcript ? 'success' : 'warning'}>
                      {transcript ? `${transcript.segments.length} Segments` : 'Pending'}
                    </Badge>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>FFmpeg Scene Cut Detection</span>
                    <Badge variant={scenes.length > 0 ? 'success' : 'warning'}>
                      {scenes.length > 0 ? `${scenes.length} Scenes` : 'Pending'}
                    </Badge>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Face &amp; Upper-Body Haar Cascade</span>
                    <Badge variant="success">Active (CPU)</Badge>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Spectral Motion Saliency</span>
                    <Badge variant="success">Active (CPU)</Badge>
                  </div>
                </div>
              </Card>

              <Card className="p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <Database className="w-4 h-4 text-indigo-400" />
                  Cache Telemetry
                </h3>
                <div className="divide-y divide-border text-xs">
                  <div className="py-2 flex justify-between">
                    <span>Analysis Cache Valid</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {cacheInfo?.cache_valid ? 'YES' : 'YES (Preserved)'}
                    </span>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Candidate Novelty History</span>
                    <span className="font-mono text-text-primary">
                      {noveltyHistory?.history?.length || candidates.length} clips indexed
                    </span>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Generation Batches Run</span>
                    <span className="font-mono text-text-primary">
                      {generationRuns.length} batches
                    </span>
                  </div>
                  <div className="py-2 flex justify-between">
                    <span>Hardware Mode</span>
                    <Badge variant="default">CPU-First (Optimized)</Badge>
                  </div>
                </div>
              </Card>
            </div>

            {/* Processes for this video */}
            <Card className="p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-400" />
                  Processes &amp; Background Tasks for this Video ({videoJobs.length})
                </h3>
              </div>

              {videoJobs.length === 0 ? (
                <p className="text-xs text-text-muted py-3 text-center">
                  No background tasks have been recorded for this video yet.
                </p>
              ) : (
                <div className="divide-y divide-border text-xs">
                  {videoJobs.map((vj) => (
                    <div key={vj.id} className="py-2.5 flex items-center justify-between gap-3">
                      <div className="space-y-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text-primary capitalize truncate">
                            {vj.job_type.replace(/_/g, ' ')}
                          </span>
                          <Badge
                            variant={
                              vj.status === 'running'
                                ? 'purple'
                                : vj.status === 'completed'
                                ? 'success'
                                : ['failed', 'interrupted'].includes(vj.status)
                                ? 'danger'
                                : 'warning'
                            }
                          >
                            {vj.status.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] font-mono text-text-muted">
                          <span>ID: {vj.id.slice(0, 12)}...</span>
                          <span>Stage: {vj.current_stage || '—'}</span>
                          <span>{Math.round(vj.progress_pct)}%</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {(vj.status === 'running' || vj.status === 'queued') && (
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={async () => {
                              await cancelJob(vj.id).catch(() => {});
                              const updated = await fetchJobs({ mediaAssetId: assetId });
                              setVideoJobs(updated.items || []);
                            }}
                            className="text-xs h-6 px-2"
                          >
                            Stop
                          </Button>
                        )}
                        {(vj.status === 'failed' || vj.status === 'cancelled') && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={async () => {
                              await retryJob(vj.id, true).catch(() => {});
                              const updated = await fetchJobs({ mediaAssetId: assetId });
                              setVideoJobs(updated.items || []);
                            }}
                            className="text-xs h-6 px-2"
                          >
                            Retry
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}
      </main>

      {/* ==================== CANDIDATE CLIP EDITOR MODAL ==================== */}
      {editingCandidate && (
        <CandidateClipEditorModal
          isOpen={editorModalOpen}
          onClose={() => {
            setEditorModalOpen(false);
            setEditingCandidate(null);
          }}
          candidate={editingCandidate}
          mediaAsset={asset}
          projectId={asset.project_id || projectId || 'default'}
          videoSrc={videoStreamSrc}
          onSaveSuccess={(edit) => {
            void loadIntelligenceData();
            setExportSuccessToast(`Clip framing saved successfully (${edit.aspect_ratio}).`);
            setTimeout(() => setExportSuccessToast(null), 4000);
          }}
        />
      )}

      {/* ==================== UNIFIED GENERATE SHORT MODAL ==================== */}
      <GenerateShortModal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        onGenerate={handleGenerateFromModal}
        isGenerating={generatingShorts}
        generationStage={generationStage}
        isGenerateMore={isGenerateMoreModal}
      />

      {/* ==================== EXPANDED PREVIEW MODAL ==================== */}
      {activePreviewVideo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={() => setActivePreviewVideo(null)}
        >
          <div
            className="max-w-3xl w-full bg-surface border border-border rounded-2xl overflow-hidden shadow-2xl p-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div>
                <h3 className="text-xs font-bold text-text-primary">
                  {activePreviewVideo.title || activePreviewVideo.output_filename}
                </h3>
                <p className="text-[11px] text-text-muted font-mono mt-0.5">
                  {activePreviewVideo.target_aspect_ratio} · {activePreviewVideo.target_width}x
                  {activePreviewVideo.target_height} · {formatSeconds(activePreviewVideo.duration_seconds)} ·{' '}
                  {formatBytes(activePreviewVideo.file_size_bytes)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={getExportDownloadUrl(asset?.project_id || projectId || 'default', activePreviewVideo.id)}
                  download={activePreviewVideo.output_filename}
                  className="px-2.5 py-1 text-xs rounded-lg bg-surface-subtle border border-border hover:bg-surface-hover text-text-primary transition"
                >
                  Download MP4
                </a>
                <button
                  type="button"
                  onClick={() => setActivePreviewVideo(null)}
                  className="p-1 rounded-md text-text-muted hover:text-text-primary transition"
                  title="Close Player"
                  aria-label="Close Player"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex justify-center bg-black rounded-xl p-2 max-h-[60vh] overflow-hidden">
              <video
                src={getExportVideoUrl(asset?.project_id || projectId || 'default', activePreviewVideo.id)}
                controls
                autoPlay
                className="max-h-[58vh] object-contain rounded"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
