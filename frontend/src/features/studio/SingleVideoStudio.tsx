import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  Eye,
  FileText,
  Film,
  History,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Scissors,
  ShieldCheck,
  Sliders,
  Sparkles,
  Volume2,
  VolumeX,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import {
  cancelAnalysisRun,
  discoverHighlights,
  fetchAnalysisCacheInfo,
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTelemetry,
  fetchAnalysisTranscript,
  fetchCandidateGenerationRuns,
  fetchCandidateNoveltyHistory,
  fetchJob,
  fetchJobs,
  fetchMediaAsset,
  fetchMediaHighlights,
  fetchProject,
  fetchProjectExports,
  generateMoreHighlights,
  getProxyUrl,
  getSceneThumbnailUrl,
  retryAnalysisRun,
  startMediaAnalysis,
  submitExportRender,
} from '../../services/apiClient';
import {
  AnalysisRunItem,
  TranscriptPayload,
  VideoSceneItem,
} from '../../types/analysis';
import {
  CandidateGenerationRunItem,
  CandidateItem,
  NoveltyHistoryResponse,
} from '../../types/highlights';
import { ExportItem } from '../../types/exports';
import { JobItem, MediaAssetItem, ProjectItem } from '../../types/projects';
import { CandidateClipEditorModal } from './CandidateClipEditorModal';

export type AspectRatioOption = '9:16' | '1:1' | '16:9' | '4:5';

export type CreativeDirectionOption =
  | 'best_overall'
  | 'viral_punchy'
  | 'dramatic'
  | 'action_motion'
  | 'emotional_sad'
  | 'engaging_dialogue'
  | 'humorous'
  | 'funny_humor';

export interface SingleVideoStudioProps {
  assetId: string;
  projectId?: string;
  onBack: () => void;
  onNavigateTimeline?: (asset: MediaAssetItem) => void;
}

const STAGE_LABELS: Record<string, string> = {
  validating_source: 'Validating Source & Integrity',
  extracting_metadata: 'Extracting Stream Metadata',
  extracting_audio: 'Demuxing Audio Track (16kHz WAV)',
  transcribing_speech: 'Transcribing Speech (Faster-Whisper int8)',
  segmenting_dialogue: 'Segmenting Dialogue & Speaker Turns',
  detecting_scenes: 'Detecting Scene Boundaries (FFmpeg)',
  sampling_frames: 'Sampling Keyframes',
  analyzing_visuals: 'Analyzing Visual Semantics',
  persisting_results: 'Persisting Records to SQLite',
  completed: 'Video Analysis Complete (100%)',
  failed: 'Analysis Failed',
  cancelled: 'Analysis Cancelled',
  queued: 'Queued for Analysis',
};

const CREATIVE_DIRECTION_LABELS: Record<string, string> = {
  best_overall: 'Best Overall',
  viral_punchy: 'Viral & Punchy',
  dramatic: 'Dramatic',
  action_motion: 'Action & Motion',
  emotional_sad: 'Emotional / Sad',
  engaging_dialogue: 'Engaging Dialogue',
  humorous: 'Humorous',
  funny_humor: 'Humorous',
};

export const SingleVideoStudio: React.FC<SingleVideoStudioProps> = ({
  assetId,
  projectId: initialProjectId,
  onBack,
  onNavigateTimeline,
}) => {
  // Core Asset & Project State
  const [asset, setAsset] = useState<MediaAssetItem | null>(null);
  const [project, setProject] = useState<ProjectItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Analysis, Candidates & Exports State
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRunItem[]>([]);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [generationRuns, setGenerationRuns] = useState<CandidateGenerationRunItem[]>([]);
  const [noveltyHistory, setNoveltyHistory] = useState<NoveltyHistoryResponse | null>(null);
  const [selectedRunFilter, setSelectedRunFilter] = useState<string>('all');
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [, setExportsList] = useState<ExportItem[]>([]);
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);
  const [transcript, setTranscript] = useState<TranscriptPayload | null>(null);
  const [scenes, setScenes] = useState<VideoSceneItem[]>([]);

  // Telemetry & Cache State
  const [telemetry, setTelemetry] = useState<{
    stage?: string;
    stage_pct?: number;
    overall_pct?: number;
    elapsed_seconds?: number;
    warnings?: string[];
    cached_stages?: string[];
    timings?: Record<string, number>;
    source_signature?: string;
  } | null>(null);
  const [cacheInfo, setCacheInfo] = useState<{
    is_cache_valid?: boolean;
    records?: Record<string, number>;
  } | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  // Upfront Configuration State
  const [aspectRatio, setAspectRatio] = useState<AspectRatioOption>('9:16');
  const [clipCount, setClipCount] = useState<number>(10);
  const [customClipCount, setCustomClipCount] = useState<string>('');
  const [creativeDirection, setCreativeDirection] = useState<CreativeDirectionOption>('best_overall');
  const [minDuration] = useState<number>(12);
  const [maxDuration] = useState<number>(60);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Video Player State
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateItem | null>(null);
  const [editingCandidate, setEditingCandidate] = useState<CandidateItem | null>(null);
  const [isClipEditorOpen, setIsClipEditorOpen] = useState<boolean>(false);

  // Collapsible Intelligence Sections
  const [activeDrawer, setActiveDrawer] = useState<'transcript' | 'scenes' | 'details' | 'runs' | null>(null);
  const [transcriptSearch, setTranscriptSearch] = useState<string>('');

  // 1. Load Asset & Dependencies
  const loadStudioData = useCallback(async (targetAssetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const assetData = await fetchMediaAsset(targetAssetId, initialProjectId);
      if (!assetData) {
        throw new Error(`Media asset '${targetAssetId}' not found.`);
      }
      setAsset(assetData);

      const resolvedPid = assetData.project_id || initialProjectId || 'default';

      try {
        const projData = await fetchProject(resolvedPid);
        setProject(projData);
      } catch {
        // non-blocking
      }

      const [runsRes, candidatesRes, exportsRes, jobsRes, genRunsRes, noveltyRes] = await Promise.allSettled([
        fetchAnalysisRuns(resolvedPid, targetAssetId),
        fetchMediaHighlights(resolvedPid, targetAssetId),
        fetchProjectExports(resolvedPid, targetAssetId),
        fetchJobs(resolvedPid),
        fetchCandidateGenerationRuns(resolvedPid, targetAssetId),
        fetchCandidateNoveltyHistory(resolvedPid, targetAssetId),
      ]);

      const runs = runsRes.status === 'fulfilled' ? runsRes.value : [];
      setAnalysisRuns(runs);

      const cands = candidatesRes.status === 'fulfilled' ? candidatesRes.value : [];
      setCandidates(cands);

      const genRuns = genRunsRes.status === 'fulfilled' ? genRunsRes.value : [];
      setGenerationRuns(genRuns);

      const novelty = noveltyRes.status === 'fulfilled' ? noveltyRes.value : null;
      setNoveltyHistory(novelty);

      const exps = exportsRes.status === 'fulfilled' ? exportsRes.value.items : [];
      setExportsList(exps);

      if (jobsRes.status === 'fulfilled') {
        const allJobs = jobsRes.value.items;
        const running = allJobs.find(
          (j) =>
            (j.status === 'running' || j.status === 'queued') &&
            (j.input_config?.media_asset_id === targetAssetId ||
              j.input_config?.asset_id === targetAssetId)
        );
        if (running) {
          setActiveJob(running);
        }
      }

      const completedRun = runs.find((r) => r.status === 'completed') || runs[0];
      if (completedRun) {
        fetchAnalysisTranscript(resolvedPid, targetAssetId, completedRun.id)
          .then(setTranscript)
          .catch(() => null);
        fetchAnalysisScenes(resolvedPid, targetAssetId, completedRun.id)
          .then(setScenes)
          .catch(() => null);
        fetchAnalysisCacheInfo(resolvedPid, targetAssetId, completedRun.id)
          .then(setCacheInfo)
          .catch(() => null);
      }
    } catch (err: any) {
      setError(err?.message || `Failed to load video studio for asset '${targetAssetId}'.`);
    } finally {
      setLoading(false);
    }
  }, [initialProjectId]);

  useEffect(() => {
    if (assetId) {
      void loadStudioData(assetId);
    }
  }, [assetId, loadStudioData]);

  // 2. Poll Active Job & Analysis Telemetry
  useEffect(() => {
    const isJobActive = activeJob && (activeJob.status === 'running' || activeJob.status === 'queued');
    const runningRun = analysisRuns.find((r) => r.status === 'running' || r.status === 'pending');

    if (!isJobActive && !runningRun) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const pid = asset?.project_id || 'default';
        const targetRunId = runningRun?.id || (activeJob?.input_config?.run_id as string);

        if (targetRunId && asset?.id) {
          try {
            const telem = await fetchAnalysisTelemetry(pid, asset.id, targetRunId);
            setTelemetry({
              stage: telem.current_stage || telem.stage_details?.stage,
              stage_pct: telem.stage_details?.stage_pct,
              overall_pct: telem.progress_pct,
              elapsed_seconds: telem.stage_details?.elapsed_seconds,
              warnings: telem.stage_details?.warnings,
              cached_stages: telem.stage_details?.cached_stages,
              timings: telem.stage_details?.timings,
              source_signature: telem.source_signature,
            });

            if (telem.status === 'completed' || telem.status === 'failed' || telem.status === 'cancelled') {
              void loadStudioData(asset.id);
            }
          } catch {
            // fallback silently
          }
        }

        if (activeJob) {
          const updated = await fetchJob(activeJob.id);
          setActiveJob(updated);
          if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
            if (asset?.id) {
              void loadStudioData(asset.id);
            }
          }
        }
      } catch {
        // retry silently
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob, analysisRuns, asset?.id, asset?.project_id, loadStudioData]);

  // Format Helpers
  const formatBytes = (bytes?: number | null): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDuration = (seconds?: number | null): string => {
    if (!seconds || seconds <= 0) return '00:00';
    const totalSecs = Math.floor(seconds);
    const m = Math.floor(totalSecs / 60);
    const s = totalSecs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Video Transport Handlers
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      void videoRef.current.play();
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration || asset?.duration_seconds || 0);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const selectCandidateForPreview = (cand: CandidateItem) => {
    setSelectedCandidate(cand);
    handleSeek(cand.start_time);
    if (videoRef.current) {
      void videoRef.current.play();
      setIsPlaying(true);
    }
  };

  // 3. Execution Handlers
  const handleTriggerAnalysis = async (forceReanalysis = false) => {
    if (!asset) return;
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      const pid = asset.project_id || 'default';
      const runRes = await startMediaAnalysis(pid, asset.id, 'balanced', {}, false, forceReanalysis);
      setActionMessage(`Analysis pipeline initiated (Run ID: ${runRes.id}). Monitoring telemetry...`);
      await loadStudioData(asset.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to start video analysis pipeline.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelAnalysis = async () => {
    const run = analysisRuns.find((r) => r.status === 'running' || r.status === 'pending');
    if (!run || !asset) return;
    setIsCancelling(true);
    try {
      const pid = asset.project_id || 'default';
      await cancelAnalysisRun(pid, asset.id, run.id);
      setActionMessage('Analysis cancellation requested.');
      await loadStudioData(asset.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel analysis run.');
    } finally {
      setIsCancelling(false);
    }
  };

  const handleRetryAnalysis = async () => {
    const run = analysisRuns.find((r) => r.status === 'failed' || r.status === 'cancelled') || analysisRuns[0];
    if (!run || !asset) return;
    setIsRetrying(true);
    try {
      const pid = asset.project_id || 'default';
      await retryAnalysisRun(pid, asset.id, run.id);
      setActionMessage('Analysis run re-enqueued.');
      await loadStudioData(asset.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to retry analysis.');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleGenerateShorts = async () => {
    if (!asset) return;
    const completedRun = analysisRuns.find((r) => r.status === 'completed');
    if (!completedRun) {
      setError('Please complete video analysis before generating shorts.');
      return;
    }
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      const pid = asset.project_id || 'default';
      const targetCount = customClipCount ? parseInt(customClipCount, 10) : clipCount;
      setActionMessage(`Discovering ${targetCount} candidate shorts in ${aspectRatio} (${CREATIVE_DIRECTION_LABELS[creativeDirection] || creativeDirection})...`);
      const newCandidates = await discoverHighlights(pid, asset.id, {
        analysis_run_id: completedRun.id,
        target_clip_count: targetCount,
        min_duration: minDuration,
        max_duration: maxDuration,
        creative_direction: creativeDirection,
        aspect_ratio: aspectRatio,
        run_synchronously: true,
      });
      await loadStudioData(asset.id);
      setActionMessage(`Discovered ${newCandidates.length} candidate shorts from analyzed media.`);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate shorts candidates.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGenerateMoreShorts = async () => {
    if (!asset) return;
    const completedRun = analysisRuns.find((r) => r.status === 'completed');
    if (!completedRun) {
      setError('Please complete video analysis before generating shorts.');
      return;
    }
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      const pid = asset.project_id || 'default';
      const targetCount = customClipCount ? parseInt(customClipCount, 10) : clipCount;
      setActionMessage(`Extracting additional ${targetCount} non-repeating candidates (tIoU < 0.50)...`);
      const newCandidates = await generateMoreHighlights(pid, asset.id, {
        analysis_run_id: completedRun.id,
        target_clip_count: targetCount,
        min_duration: minDuration,
        max_duration: maxDuration,
        creative_direction: creativeDirection,
        aspect_ratio: aspectRatio,
        run_synchronously: true,
      });
      await loadStudioData(asset.id);
      if (newCandidates.length > 0) {
        setActionMessage(`Extracted ${newCandidates.length} new non-repeating candidates. Novelty ledger updated.`);
      } else {
        setActionMessage('All distinct high-interest moments have been discovered for this video under current novelty thresholds.');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to generate additional shorts.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Single-Clip Export Trigger
  const handleExportCandidate = async (cand: CandidateItem) => {
    if (!asset) return;
    try {
      const pid = asset.project_id || 'default';
      const presetMap: Record<AspectRatioOption, string> = {
        '9:16': 'shorts_reels_9_16',
        '1:1': 'square_1_1',
        '16:9': 'landscape_16_9',
        '4:5': 'shorts_reels_9_16',
      };
      await submitExportRender(pid, {
        candidate_id: cand.id,
        preset_id: presetMap[aspectRatio] || 'shorts_reels_9_16',
        title: cand.title,
      });
      const exps = await fetchProjectExports(pid, asset.id);
      setExportsList(exps.items);
      setActionMessage(`Export queued for "${cand.title}". Track progress in Working Queue.`);
    } catch (err: any) {
      setError(err?.message || `Failed to export candidate "${cand.title}".`);
    }
  };

  // Filtered transcript
  const filteredTranscriptSegments = useMemo(() => {
    if (!transcript?.segments) return [];
    if (!transcriptSearch.trim()) return transcript.segments;
    const q = transcriptSearch.toLowerCase();
    return transcript.segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [transcript, transcriptSearch]);

  // Loading View
  if (loading && !asset) {
    return (
      <div className="h-full w-full flex flex-col p-6 space-y-4 bg-canvas text-text-primary">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-64" />
        </div>
        <Skeleton className="h-14 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  // Error View
  if (error && !asset) {
    return (
      <div className="h-full w-full flex items-center justify-center p-6 bg-canvas">
        <Card className="max-w-md w-full p-6 text-center space-y-4 border border-rose-500/30">
          <AlertCircle className="w-10 h-10 text-rose-400 mx-auto" />
          <h2 className="text-base font-semibold text-text-primary">Unable to Open Video Studio</h2>
          <p className="text-xs text-text-muted">{error}</p>
          <Button variant="primary" size="sm" onClick={onBack} leftIcon={<ArrowLeft className="w-4 h-4" />}>
            Return to Media Library
          </Button>
        </Card>
      </div>
    );
  }

  if (!asset) return null;

  const currentRun = analysisRuns.find((r) => r.status === 'running' || r.status === 'pending') || analysisRuns[0];
  const isAnalyzing = activeJob?.status === 'running' || currentRun?.status === 'running';
  const isAnalysisFailed = currentRun?.status === 'failed' || activeJob?.status === 'failed';
  const isAnalysisCancelled = currentRun?.status === 'cancelled' || activeJob?.status === 'cancelled';
  const isAnalysisComplete = currentRun?.status === 'completed';

  const rawStageKey = telemetry?.stage || currentRun?.current_stage || activeJob?.current_stage || 'validating_source';
  const currentStageLabel = STAGE_LABELS[rawStageKey] || rawStageKey.replace(/_/g, ' ');
  const currentProgressPct = telemetry?.overall_pct ?? currentRun?.progress_pct ?? activeJob?.progress_pct ?? 0;

  return (
    <div className="h-full w-full flex flex-col overflow-y-auto bg-canvas text-text-primary select-none">
      {/* 1. STUDIO HEADER */}
      <header className="shrink-0 border-b border-border bg-surface/80 backdrop-blur-sm px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface transition flex items-center gap-1.5 text-xs font-medium"
            title="Return to Media Library"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Media Library</span>
          </button>

          <div className="h-4 w-px bg-border shrink-0" />

          <div className="flex items-center gap-2 min-w-0">
            <Film className="w-4 h-4 text-brand shrink-0" />
            <h1 className="text-sm font-semibold text-text-primary truncate" title={asset.original_filename}>
              {asset.original_filename}
            </h1>
          </div>

          <div className="hidden md:flex items-center gap-1.5 text-xs font-mono text-text-muted shrink-0">
            <Badge variant="default" size="sm">
              {formatDuration(asset.duration_seconds)}
            </Badge>
            {asset.width && asset.height && (
              <Badge variant="default" size="sm">
                {asset.width}x{asset.height}
              </Badge>
            )}
            {asset.fps && (
              <Badge variant="default" size="sm">
                {Math.round(asset.fps)}fps
              </Badge>
            )}
            <Badge variant="default" size="sm">
              {formatBytes(asset.file_size_bytes)}
            </Badge>
            {project && (
              <Badge variant="info" size="sm">
                {project.name}
              </Badge>
            )}
            {asset.availability_status === 'missing' ? (
              <Badge variant="danger" size="sm">
                Missing from Disk
              </Badge>
            ) : (
              <Badge variant="success" size="sm">
                Present
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {onNavigateTimeline && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateTimeline(asset)}
              leftIcon={<Scissors className="w-3.5 h-3.5 text-text-secondary" />}
              title="Open multi-track non-linear editor"
            >
              Timeline Editor
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => void loadStudioData(asset.id)}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            title="Reload analysis and candidate status"
          >
            Refresh
          </Button>
        </div>
      </header>

      {/* 2. GLOBAL ANALYSIS & TELEMETRY PROGRESS BANNER */}
      <section className="shrink-0 border-b border-border bg-canvas-subtle/50 px-4 py-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2.5 text-xs font-medium">
            {isAnalyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-brand shrink-0" />
                <span className="text-text-primary font-semibold">
                  {currentStageLabel}
                </span>
                {telemetry?.elapsed_seconds !== undefined && (
                  <span className="text-[11px] font-mono text-text-muted">
                    ({telemetry.elapsed_seconds.toFixed(1)}s elapsed)
                  </span>
                )}
                {/* Cancel Action */}
                <button
                  type="button"
                  onClick={handleCancelAnalysis}
                  disabled={isCancelling}
                  className="inline-flex items-center gap-1 text-[11px] font-mono text-rose-400 hover:text-rose-300 border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 rounded transition ml-2"
                  title="Cancel active analysis pipeline"
                >
                  <XCircle className="w-3 h-3" />
                  <span>{isCancelling ? 'Cancelling...' : 'Cancel'}</span>
                </button>
              </>
            ) : isAnalysisFailed ? (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                <span className="text-rose-400 font-semibold">Analysis Failed</span>
                <button
                  type="button"
                  onClick={handleRetryAnalysis}
                  disabled={isRetrying}
                  className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-400 hover:text-amber-300 border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 rounded transition ml-2"
                  title="Retry failed analysis"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>{isRetrying ? 'Retrying...' : 'Retry'}</span>
                </button>
              </>
            ) : isAnalysisCancelled ? (
              <>
                <XCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span className="text-amber-400 font-medium">Analysis Cancelled</span>
                <button
                  type="button"
                  onClick={handleRetryAnalysis}
                  disabled={isRetrying}
                  className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-400 hover:text-amber-300 border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 rounded transition ml-2"
                  title="Re-enqueue analysis"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Resume Analysis</span>
                </button>
              </>
            ) : isAnalysisComplete ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-text-secondary">
                  Video Analysis Complete (100%) •{' '}
                  <strong className="text-text-primary">
                    {candidates.length > 0 ? `${candidates.length} Shorts Discovered` : 'Ready for Candidate Discovery'}
                  </strong>
                </span>
                {cacheInfo?.is_cache_valid && (
                  <Badge variant="info" size="sm" className="font-mono text-[10px] ml-1">
                    Cached Run
                  </Badge>
                )}
              </>
            ) : (
              <>
                <Sliders className="w-3.5 h-3.5 text-text-muted shrink-0" />
                <span className="text-text-secondary">Ready to analyze. Configure settings below and click Analyze Video.</span>
              </>
            )}
          </div>

          <div className="flex items-center gap-2.5 text-xs font-mono text-text-muted">
            {isAnalyzing && (
              <span className="font-semibold text-brand">
                {Math.round(currentProgressPct)}%
              </span>
            )}
            {actionMessage && (
              <span className="text-brand text-[11px] truncate max-w-md">{actionMessage}</span>
            )}
          </div>
        </div>

        {/* Measurable Progress Track */}
        <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden border border-border/50">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              isAnalyzing ? 'bg-brand' : isAnalysisComplete ? 'bg-emerald-500' : 'bg-transparent'
            }`}
            style={{
              width: `${
                isAnalyzing
                  ? Math.max(5, Math.round(currentProgressPct))
                  : isAnalysisComplete
                  ? 100
                  : 0
              }%`,
            }}
          />
        </div>
      </section>

      {/* 3. MAIN WORKSPACE: UPFRONT CONTROLS + HERO DISPLAY */}
      <div className="flex-1 min-h-0 p-4 space-y-4">
        {/* UPFRONT CONFIGURATION BAR */}
        <Card className="p-4 border border-border bg-surface/90 shadow-xs space-y-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2.5">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-text-primary flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-brand" />
                Generation Configuration
              </h2>
              <p className="text-[11px] text-text-muted mt-0.5">
                Configure target aspect ratio, clip count, and style before running video intelligence.
              </p>
            </div>

            {/* Pipeline Action Buttons */}
            <div className="flex items-center gap-2">
              {!isAnalysisComplete ? (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleTriggerAnalysis(false)}
                  disabled={isSubmitting || isAnalyzing}
                  isLoading={isSubmitting && isAnalyzing}
                  leftIcon={<Sparkles className="w-3.5 h-3.5 text-amber-300" />}
                  className="text-xs font-medium px-4 py-1.5 shadow-xs"
                >
                  Analyze Full Video
                </Button>
              ) : (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTriggerAnalysis(true)}
                    disabled={isSubmitting || isAnalyzing}
                    leftIcon={<RotateCcw className="w-3.5 h-3.5 text-text-secondary" />}
                    className="text-xs font-medium px-3 py-1.5"
                    title="Force re-running analysis bypassing cache"
                  >
                    Force Re-Analyze
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleGenerateShorts}
                    disabled={isSubmitting || isAnalyzing}
                    isLoading={isSubmitting}
                    leftIcon={<Sparkles className="w-3.5 h-3.5 text-amber-300" />}
                    className="text-xs font-medium px-4 py-1.5 shadow-xs"
                    title="Run fresh candidate discovery with current settings"
                  >
                    {candidates.length > 0 ? 'Generate Additional Shorts' : 'Discover Shorts'}
                  </Button>

                  {candidates.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleGenerateMoreShorts}
                      disabled={isSubmitting || isAnalyzing}
                      isLoading={isSubmitting}
                      leftIcon={<Plus className="w-3.5 h-3.5" />}
                      className="text-xs font-medium px-3.5 py-1.5 shadow-xs"
                      title="Discover more non-repeating candidates without duplicating past moments"
                    >
                      Generate More Shorts (Novelty)
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {/* Aspect Ratio Options */}
            <div className="space-y-1.5">
              <label className="text-text-secondary font-medium block">Aspect Ratio / Framing</label>
              <div className="grid grid-cols-2 gap-1.5">
                {(
                  [
                    { id: '9:16', label: '9:16 Vertical', sub: 'Shorts, Reels, TikTok' },
                    { id: '1:1', label: '1:1 Square', sub: 'Instagram Feed' },
                    { id: '16:9', label: '16:9 Landscape', sub: 'Standard YouTube' },
                    { id: '4:5', label: '4:5 Portrait', sub: 'Social Media' },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setAspectRatio(opt.id)}
                    className={`p-2 rounded-lg border text-left transition ${
                      aspectRatio === opt.id
                        ? 'border-brand bg-brand/10 text-text-primary ring-1 ring-brand/30'
                        : 'border-border bg-canvas-subtle text-text-secondary hover:text-text-primary hover:border-border-hover'
                    }`}
                  >
                    <span className="font-semibold block">{opt.label}</span>
                    <span className="text-[10px] text-text-muted block truncate">{opt.sub}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Quantity of Shorts */}
            <div className="space-y-1.5">
              <label className="text-text-secondary font-medium block">Target Quantity of Shorts</label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {[5, 6, 10, 15, 20].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => {
                      setClipCount(num);
                      setCustomClipCount('');
                    }}
                    className={`px-3 py-1.5 rounded-lg border font-mono text-xs transition ${
                      clipCount === num && !customClipCount
                        ? 'border-brand bg-brand/10 text-text-primary font-semibold'
                        : 'border-border bg-canvas-subtle text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {num} clips
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-text-muted font-mono">Custom:</span>
                <input
                  type="number"
                  min="1"
                  max="50"
                  placeholder="e.g. 12"
                  value={customClipCount}
                  onChange={(e) => setCustomClipCount(e.target.value)}
                  className="w-24 px-2 py-1 rounded bg-canvas border border-border text-xs font-mono text-text-primary focus:outline-none focus:border-brand"
                />
              </div>
            </div>

            {/* Creative Direction */}
            <div className="space-y-1.5">
              <label className="text-text-secondary font-medium block">Creative Direction / Tone</label>
              <select
                value={creativeDirection}
                onChange={(e) => setCreativeDirection(e.target.value as CreativeDirectionOption)}
                className="w-full px-2.5 py-2 rounded-lg bg-canvas border border-border text-xs text-text-primary focus:outline-none focus:border-brand"
              >
                <option value="best_overall">Best Overall (Balanced Intelligence)</option>
                <option value="viral_punchy">Viral & Punchy (Hook-Heavy, High Change Score)</option>
                <option value="dramatic">Dramatic (Emotional Climaxes, Narrative Peaks)</option>
                <option value="action_motion">Action & Motion (Rapid Visual Dynamics)</option>
                <option value="emotional_sad">Emotional / Sad (Subtle Moments, Piano / Dialogue)</option>
                <option value="engaging_dialogue">Engaging Dialogue (High Speech Density)</option>
                <option value="funny_humor">Humorous (Punchlines & Expressions)</option>
              </select>

              <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-text-muted">
                <span>Duration Bounds:</span>
                <span>
                  {minDuration}s – {maxDuration}s
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* HERO PREVIEW & CANDIDATES COLUMN */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* LEFT: Video Player Preview (7 cols) */}
          <Card className="lg:col-span-7 p-4 border border-border bg-surface/90 flex flex-col space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5 text-brand" />
                Source Video Preview
              </span>
              <span className="text-[11px] font-mono text-text-muted">
                {formatDuration(currentTime)} / {formatDuration(duration || asset.duration_seconds)}
              </span>
            </div>

            {/* Aspect Ratio Framing Container */}
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center border border-border/80 group">
              <video
                ref={videoRef}
                src={getProxyUrl(asset.project_id || 'default', asset.id)}
                className="w-full h-full object-contain"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                muted={isMuted}
                playsInline
              />

              {/* Aspect Ratio Crop Guide Overlay */}
              {aspectRatio === '9:16' && (
                <div
                  className="absolute pointer-events-none border-2 border-brand/60 rounded-md shadow-[0_0_0_9999px_rgba(0,0,0,0.5)] transition-all"
                  style={{
                    height: '92%',
                    aspectRatio: '9/16',
                  }}
                />
              )}
              {aspectRatio === '1:1' && (
                <div
                  className="absolute pointer-events-none border-2 border-brand/60 rounded-md shadow-[0_0_0_9999px_rgba(0,0,0,0.5)] transition-all"
                  style={{
                    height: '88%',
                    aspectRatio: '1/1',
                  }}
                />
              )}
              {aspectRatio === '4:5' && (
                <div
                  className="absolute pointer-events-none border-2 border-brand/60 rounded-md shadow-[0_0_0_9999px_rgba(0,0,0,0.5)] transition-all"
                  style={{
                    height: '90%',
                    aspectRatio: '4/5',
                  }}
                />
              )}
            </div>

            {/* Video Transport Controls */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={togglePlay}
                  className="p-1.5 rounded-lg bg-brand/10 text-brand hover:bg-brand/20 transition"
                  title={isPlaying ? 'Pause' : 'Play'}
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>

                <button
                  type="button"
                  onClick={() => setIsMuted(!isMuted)}
                  className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-canvas-subtle transition"
                  title={isMuted ? 'Unmute' : 'Mute'}
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
              </div>

              {/* Scrubber Bar */}
              <input
                type="range"
                min="0"
                max={duration || asset.duration_seconds || 1}
                step="0.1"
                value={currentTime}
                onChange={(e) => handleSeek(parseFloat(e.target.value))}
                className="flex-1 h-1.5 bg-canvas rounded-lg appearance-none cursor-pointer accent-brand"
              />

              <span className="text-[11px] font-mono text-text-muted shrink-0">
                {formatDuration(currentTime)}
              </span>
            </div>
          </Card>

          {/* RIGHT: Discovered Shorts List (5 cols) */}
          <div className="lg:col-span-5 flex flex-col space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-1.5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-brand" />
                Discovered Shorts Candidates ({candidates.length})
              </h3>
              {candidates.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-text-muted">Framing: {aspectRatio}</span>
                  {generationRuns.length > 1 && (
                    <select
                      value={selectedRunFilter}
                      onChange={(e) => setSelectedRunFilter(e.target.value)}
                      className="bg-canvas border border-border text-[10px] rounded px-1.5 py-0.5 text-text-primary focus:outline-none focus:border-brand font-mono"
                      title="Filter candidate clips by discovery run"
                    >
                      <option value="all">All Batches ({candidates.length})</option>
                      {generationRuns.map((r, idx) => (
                        <option key={r.id} value={r.id}>
                          Batch #{generationRuns.length - idx} ({CREATIVE_DIRECTION_LABELS[r.creative_direction] || r.creative_direction})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>

            {/* Novelty & Exclusion Ledger Banner */}
            {candidates.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface border border-border text-[10px] font-mono">
                <div className="flex items-center gap-1.5 text-text-secondary">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Novelty filter active: tIoU &lt; 0.50</span>
                </div>
                {noveltyHistory && (
                  <span className="text-text-muted">
                    {noveltyHistory.total_clips_generated} historical moments indexed
                  </span>
                )}
              </div>
            )}

            {candidates.length === 0 ? (
              <Card className="flex-1 flex items-center justify-center p-8 border border-border border-dashed bg-surface/50 text-center">
                <EmptyState
                  title={isAnalyzing ? 'Analyzing Video Content...' : 'No Shorts Discovered Yet'}
                  description={
                    isAnalyzing
                      ? 'Faster-Whisper, scene boundary cuts, and keyframe sampling are analyzing the entire video duration.'
                      : isAnalysisComplete
                      ? 'Full-video analysis is complete! Click "Discover Shorts" to extract viral candidate segments.'
                      : 'Configure framing and clip quantity above, then click Analyze Full Video to begin.'
                  }
                  actionText={isAnalyzing ? undefined : isAnalysisComplete ? 'Discover Shorts' : 'Analyze Full Video'}
                  onAction={isAnalyzing ? undefined : isAnalysisComplete ? handleGenerateShorts : () => handleTriggerAnalysis(false)}
                />
              </Card>
            ) : (
              <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
                {candidates
                  .filter((c) => selectedRunFilter === 'all' || c.generation_run_id === selectedRunFilter)
                  .map((cand, idx) => (
                    <Card
                      key={cand.id}
                      className={`p-3 border transition cursor-pointer space-y-2 ${
                        selectedCandidate?.id === cand.id
                          ? 'border-brand bg-brand/5 shadow-xs ring-1 ring-brand/30'
                          : 'border-border bg-surface hover:border-border-hover'
                      }`}
                      onClick={() => selectCandidateForPreview(cand)}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="font-mono text-[10px] text-text-muted">#{idx + 1}</span>
                            <h4 className="text-xs font-semibold text-text-primary truncate max-w-[220px]" title={cand.title}>
                              {cand.title}
                            </h4>
                            <Badge variant="default" size="sm">
                              {cand.category}
                            </Badge>
                            <Badge variant="info" size="sm" className="text-[10px]">
                              {CREATIVE_DIRECTION_LABELS[cand.creative_direction || creativeDirection] || cand.creative_direction || 'Standard'}
                            </Badge>
                            {cand.natural_boundary_confidence !== undefined && (
                              <span title="Speech closure and scene cut boundary confidence">
                                <Badge
                                  variant={cand.natural_boundary_confidence >= 0.8 ? 'success' : 'default'}
                                  size="sm"
                                  className="font-mono text-[10px]"
                                >
                                  <ShieldCheck className="w-2.5 h-2.5 mr-0.5 inline" />
                                  Natural Cut {Math.round(cand.natural_boundary_confidence * 100)}%
                                </Badge>
                              </span>
                            )}
                          </div>

                          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-text-muted">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-text-secondary" />
                              {formatDuration(cand.start_time)} – {formatDuration(cand.end_time)} ({cand.duration.toFixed(1)}s)
                            </span>
                            <span>•</span>
                            <span className="text-text-primary font-medium">
                              Attractiveness: {Math.round(cand.quality_score * 100)}/100 (estimate)
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedCandidateId(expandedCandidateId === cand.id ? null : cand.id);
                              }}
                              className="inline-flex items-center gap-0.5 text-[10px] text-brand hover:text-brand-hover ml-1 transition"
                              title="Toggle multimodal scoring breakdown"
                            >
                              <span>Breakdown</span>
                              {expandedCandidateId === cand.id ? (
                                <ChevronUp className="w-3 h-3" />
                              ) : (
                                <ChevronDown className="w-3 h-3" />
                              )}
                            </button>
                          </div>

                          {cand.description && (
                            <p className="text-[11px] text-text-secondary line-clamp-1 italic">
                              "{cand.description}"
                            </p>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => selectCandidateForPreview(cand)}
                            leftIcon={<Play className="w-3 h-3" />}
                            className="text-[11px] py-1 px-2 text-text-secondary hover:text-text-primary"
                            title="Seek preview player to this moment"
                          >
                            Preview
                          </Button>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingCandidate(cand);
                              setIsClipEditorOpen(true);
                            }}
                            leftIcon={<Sliders className="w-3 h-3 text-text-secondary" />}
                            className="text-[11px] py-1 px-2 text-text-secondary hover:text-text-primary"
                            title="Open interactive clip preview, trimming & reframing editor"
                          >
                            Edit Clip
                          </Button>

                          {onNavigateTimeline && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onNavigateTimeline(asset)}
                              leftIcon={<Scissors className="w-3 h-3 text-text-secondary" />}
                              className="text-[11px] py-1 px-2 text-text-secondary hover:text-text-primary"
                              title="Open in Timeline Editor"
                            >
                              Timeline
                            </Button>
                          )}

                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => void handleExportCandidate(cand)}
                            leftIcon={<Download className="w-3 h-3" />}
                            className="text-[11px] py-1 px-2.5 font-medium shadow-xs"
                            title={`Render standalone MP4 in ${aspectRatio}`}
                          >
                            Export MP4
                          </Button>
                        </div>
                      </div>

                      {/* Multimodal Score Breakdown & Natural Boundary Details Panel */}
                      {expandedCandidateId === cand.id && (
                        <div
                          className="pt-2 border-t border-border/50 bg-canvas-subtle/50 -mx-3 -mb-3 p-3 rounded-b-lg space-y-2 text-[10px] font-mono"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span className="uppercase text-text-muted block font-semibold text-[9px] tracking-wider">
                            Multimodal Signal Scoring (0–100)
                          </span>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Hook Strength</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.hook_strength ?? Math.round(cand.quality_score * 100)}%
                              </span>
                            </div>
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Dialogue Interest</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.dialogue_interest ?? 0}%
                              </span>
                            </div>
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Emotional Signal</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.emotional_signal ?? 0}%
                              </span>
                            </div>
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Action & Motion</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.action_motion ?? 0}%
                              </span>
                            </div>
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Visual Presentation</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.visual_interest ?? 0}%
                              </span>
                            </div>
                            <div className="p-1 rounded bg-surface border border-border/40">
                              <span className="text-text-muted block truncate">Narrative Completeness</span>
                              <span className="text-brand font-semibold">
                                {cand.score_breakdown?.narrative_completeness ?? 0}%
                              </span>
                            </div>
                          </div>

                          {cand.ai_explanation?.why_it_works && (
                            <p className="text-[11px] font-sans text-text-secondary pt-1 border-t border-border/40">
                              <strong className="text-text-primary">Why it works:</strong> {cand.ai_explanation.why_it_works}
                            </p>
                          )}
                          {cand.ai_explanation?.hook && (
                            <p className="text-[10px] text-brand/90 font-mono">
                              Opening Hook: {cand.ai_explanation.hook}
                            </p>
                          )}
                        </div>
                      )}
                    </Card>
                  ))}
              </div>
            )}
          </div>
        </div>

        {/* 4. COLLAPSIBLE VIDEO INTELLIGENCE DRAWER */}
        <section className="pt-2 border-t border-border">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <button
              onClick={() => setActiveDrawer(activeDrawer === 'transcript' ? null : 'transcript')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition ${
                activeDrawer === 'transcript'
                  ? 'border-brand bg-brand/10 text-brand'
                  : 'border-border bg-surface text-text-secondary hover:text-text-primary'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Full Transcript ({transcript?.segments?.length || 0})</span>
            </button>

            <button
              onClick={() => setActiveDrawer(activeDrawer === 'scenes' ? null : 'scenes')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition ${
                activeDrawer === 'scenes'
                  ? 'border-brand bg-brand/10 text-brand'
                  : 'border-border bg-surface text-text-secondary hover:text-text-primary'
              }`}
            >
              <Film className="w-3.5 h-3.5" />
              <span>Detected Scenes ({scenes.length})</span>
            </button>

            <button
              onClick={() => setActiveDrawer(activeDrawer === 'runs' ? null : 'runs')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition ${
                activeDrawer === 'runs'
                  ? 'border-brand bg-brand/10 text-brand'
                  : 'border-border bg-surface text-text-secondary hover:text-text-primary'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Candidate Batches ({generationRuns.length})</span>
            </button>

            <button
              onClick={() => setActiveDrawer(activeDrawer === 'details' ? null : 'details')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition ${
                activeDrawer === 'details'
                  ? 'border-brand bg-brand/10 text-brand'
                  : 'border-border bg-surface text-text-secondary hover:text-text-primary'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Technical & Telemetry Details</span>
            </button>
          </div>

          {/* Transcript Drawer */}
          {activeDrawer === 'transcript' && (
            <Card className="p-3.5 border border-border bg-surface space-y-2.5 max-h-60 overflow-y-auto">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-text-primary">Searchable Whisper Transcript</span>
                <input
                  type="search"
                  placeholder="Filter dialogue..."
                  value={transcriptSearch}
                  onChange={(e) => setTranscriptSearch(e.target.value)}
                  className="px-2.5 py-1 text-xs rounded bg-canvas border border-border text-text-primary focus:outline-none focus:border-brand w-48"
                />
              </div>

              {filteredTranscriptSegments.length === 0 ? (
                <p className="text-xs text-text-muted italic">No transcript segments available for this video.</p>
              ) : (
                <div className="space-y-1 divide-y divide-border/40 font-mono text-xs">
                  {filteredTranscriptSegments.map((seg) => (
                    <div
                      key={seg.id}
                      onClick={() => handleSeek(seg.start_time)}
                      className="pt-1.5 pb-1 flex items-start gap-3 hover:bg-canvas-subtle p-1 rounded cursor-pointer transition"
                    >
                      <span className="text-[10px] text-brand shrink-0">
                        {formatDuration(seg.start_time)}
                      </span>
                      <span className="text-text-primary font-sans text-xs">{seg.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Scene Cuts Drawer */}
          {activeDrawer === 'scenes' && (
            <Card className="p-3.5 border border-border bg-surface space-y-2.5 max-h-60 overflow-y-auto">
              <span className="text-xs font-semibold text-text-primary block">
                Visual Scene Cuts Detected by FFmpeg
              </span>
              {scenes.length === 0 ? (
                <p className="text-xs text-text-muted italic">No scene cuts detected yet. Run analysis to extract scenes.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
                  {scenes.map((scene) => (
                    <div
                      key={scene.id}
                      onClick={() => handleSeek(scene.start_time)}
                      className="p-1 rounded bg-canvas border border-border hover:border-brand cursor-pointer transition text-center space-y-1"
                    >
                      <div className="aspect-video bg-black/60 rounded overflow-hidden flex items-center justify-center">
                        <img
                          src={getSceneThumbnailUrl(asset.project_id || 'default', asset.id, scene.id)}
                          alt=""
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-text-muted block">
                        {formatDuration(scene.start_time)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Candidate Batches & Novelty Ledger Drawer */}
          {activeDrawer === 'runs' && (
            <Card className="p-3.5 border border-border bg-surface space-y-3 max-h-64 overflow-y-auto">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-text-primary">
                  Candidate Discovery Runs & Novelty Tracking
                </span>
                {noveltyHistory && (
                  <span className="text-[10px] font-mono text-emerald-400">
                    Novelty threshold: tIoU &lt; 0.50 ({noveltyHistory.total_clips_generated} historical moments)
                  </span>
                )}
              </div>

              {generationRuns.length === 0 ? (
                <p className="text-xs text-text-muted italic">No candidate discovery batches run yet.</p>
              ) : (
                <div className="space-y-2">
                  {generationRuns.map((r, idx) => (
                    <div
                      key={r.id}
                      className="p-2.5 rounded bg-canvas border border-border text-[11px] font-mono space-y-1.5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-text-primary">
                            Batch #{generationRuns.length - idx}
                          </span>
                          <span className="text-[10px] text-text-muted">({r.id.slice(0, 14)}...)</span>
                          <Badge variant="info" size="sm">
                            {CREATIVE_DIRECTION_LABELS[r.creative_direction] || r.creative_direction}
                          </Badge>
                          <Badge variant="default" size="sm">
                            {r.aspect_ratio}
                          </Badge>
                        </div>
                        <Badge variant={r.status === 'completed' ? 'success' : 'warning'} size="sm">
                          {r.status}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-text-muted pt-1 border-t border-border/40">
                        <div>
                          <span>Requested: </span>
                          <strong className="text-text-primary">{r.requested_count}</strong>
                        </div>
                        <div>
                          <span>Selected: </span>
                          <strong className="text-emerald-400">{r.candidates_selected}</strong>
                        </div>
                        <div>
                          <span>Novelty Exclusions: </span>
                          <strong className="text-amber-400">{r.novelty_exclusions}</strong>
                        </div>
                        <div>
                          <span>Duration Bounds: </span>
                          <span className="text-text-primary">{r.min_duration}s–{r.max_duration}s</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Technical & Telemetry Details Drawer */}
          {activeDrawer === 'details' && (
            <Card className="p-3.5 border border-border bg-surface space-y-3">
              <span className="text-xs font-semibold text-text-primary block">Technical Source & Pipeline Telemetry</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px] text-text-muted">
                <div>
                  <span className="block text-[10px] uppercase">Storage Path</span>
                  <span className="text-text-primary truncate block" title={asset.storage_path}>
                    {asset.storage_path}
                  </span>
                </div>
                <div>
                  <span className="block text-[10px] uppercase">Source Signature</span>
                  <span className="text-text-primary truncate block font-mono text-[10px]" title={telemetry?.source_signature || (currentRun as any)?.source_signature || 'Not computed'}>
                    {telemetry?.source_signature || (currentRun as any)?.source_signature || 'Not computed'}
                  </span>
                </div>
                <div>
                  <span className="block text-[10px] uppercase">Video Codec</span>
                  <span className="text-text-primary">{asset.video_codec || 'unknown'}</span>
                </div>
                <div>
                  <span className="block text-[10px] uppercase">Audio Codec</span>
                  <span className="text-text-primary">{asset.audio_codec || 'unknown'}</span>
                </div>
              </div>

              {/* Stage Timings Breakdown if available */}
              {(telemetry?.timings || (currentRun as any)?.stage_details?.timings) && (
                <div className="pt-2 border-t border-border/50">
                  <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                    Pipeline Execution Timings
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[10px]">
                    {Object.entries(telemetry?.timings || (currentRun as any)?.stage_details?.timings || {}).map(([key, val]) => (
                      <div key={key} className="p-1.5 rounded bg-canvas-subtle border border-border/40">
                        <span className="text-text-muted block truncate">{key.replace('_s', '')}</span>
                        <span className="text-brand font-semibold">{Number(val).toFixed(2)}s</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}
        </section>
      </div>

      {/* Interactive Candidate Clip Editor Modal */}
      {isClipEditorOpen && editingCandidate && asset && (
        <CandidateClipEditorModal
          isOpen={isClipEditorOpen}
          onClose={() => {
            setIsClipEditorOpen(false);
            setEditingCandidate(null);
          }}
          candidate={editingCandidate}
          mediaAsset={asset}
          projectId={asset.project_id || initialProjectId || 'default'}
          videoSrc={getProxyUrl(asset.project_id || 'default', asset.id)}
          onSaveSuccess={() => {
            void loadStudioData(asset.id);
          }}
        />
      )}
    </div>
  );
};
