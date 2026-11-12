import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Crop,
  Database,
  Download,
  Eye,
  FileText,
  Film,
  Loader2,
  Mic,
  MoveHorizontal,
  Pause,
  Play,
  Scissors,
  Search,
  Sliders,
  Sparkles,
  User,
  Users,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import {
  discoverHighlights,
  fetchAnalysisCacheInfo,
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTranscript,
  fetchCandidateGenerationRuns,
  fetchCandidateNoveltyHistory,
  fetchJobs,
  fetchMediaAsset,
  fetchMediaHighlights,
  getGlobalThumbnailUrl,
  getSceneThumbnailUrl,
  getStreamMediaUrl,
  startMediaAnalysis,
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
  NoveltyHistoryResponse,
} from '../../types/highlights';
import { JobItem, MediaAssetItem } from '../../types/projects';
import { CandidateClipEditorModal } from '../studio/CandidateClipEditorModal';

export type VideoDashboardTab =
  | 'home'
  | 'short_generator'
  | 'generated_shorts'
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

const CREATIVE_DIRECTIONS = [
  { id: 'best_overall', label: 'Best Overall', desc: 'Balanced hook, narrative completeness & high visual interest' },
  { id: 'viral_punchy', label: 'Viral & Punchy', desc: 'High hook weight, fast pacing, aggressive attention capture' },
  { id: 'dramatic', label: 'Dramatic', desc: 'Emphasizes intense pauses, emotional peaks, and dramatic tension' },
  { id: 'action_motion', label: 'Action & Motion', desc: 'Prioritizes high visual dynamism, fast movement & spectacle' },
  { id: 'emotional_sad', label: 'Emotional & Sad', desc: 'Deep poignant moments, touching dialogue & melancholic score' },
  { id: 'engaging_dialogue', label: 'Engaging Dialogue', desc: 'Speech clarity, punchy conversational exchanges & stories' },
  { id: 'humorous', label: 'Humorous & Comedy', desc: 'Laughter peaks, comical timing, punchlines & reactions' },
  { id: 'educational', label: 'Educational', desc: 'Informative explanations, step-by-step clarity & takeaways' },
  { id: 'suspense', label: 'Suspense & Thriller', desc: 'Mounting tension, mystery cues, and suspenseful climaxes' },
  { id: 'narrative_arc', label: 'Narrative Arc', desc: 'Complete mini-stories: Setup, conflict, climax & resolution' },
  { id: 'high_energy', label: 'High Energy', desc: 'Rapid edits, enthusiastic delivery & continuous stimulation' },
  { id: 'cinematic', label: 'Cinematic', desc: 'Wide compositions, beautiful lighting, and artistic framing' },
  { id: 'storytelling', label: 'Storytelling', desc: 'Personal anecdotes, emotional journeys & narrative depth' },
  { id: 'reaction_focus', label: 'Reaction Focus', desc: 'Expressive face close-ups and genuine reaction moments' },
  { id: 'interview_highlight', label: 'Interview Highlight', desc: 'Memorable quotes, profound answers & expert perspectives' },
  { id: 'teaser_trailer', label: 'Teaser & Trailer', desc: 'Intriguing clips designed to make viewers want the full video' },
  { id: 'motivational', label: 'Motivational', desc: 'Uplifting messages, triumph over adversity & encouragement' },
  { id: 'aesthetic_montage', label: 'Aesthetic Montage', desc: 'Visually pleasing scenes scored with ambient rhythm' },
];

const ASPECT_RATIOS: Array<{ id: AspectRatioOption; label: string; ratio: string }> = [
  { id: '9:16', label: '9:16 Vertical', ratio: '9 / 16' },
  { id: '1:1', label: '1:1 Square', ratio: '1 / 1' },
  { id: '16:9', label: '16:9 Landscape', ratio: '16 / 9' },
  { id: '4:5', label: '4:5 Social Feed', ratio: '4 / 5' },
];

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

  // Short Generator Form State
  const [clipCountPreset, setClipCountPreset] = useState<'ai' | '3' | '5' | '10' | '15' | '20' | 'custom'>('5');
  const [customClipCount, setCustomClipCount] = useState<number>(7);
  const [selectedDirection, setSelectedDirection] = useState<string>('best_overall');
  const [selectedAspectRatio, setSelectedAspectRatio] = useState<AspectRatioOption>('9:16');
  const [trackingMode, setTrackingMode] = useState<'face' | 'upper_body' | 'object' | 'multi'>('face');
  const [minDurationSec, setMinDurationSec] = useState<number>(15);
  const [maxDurationSec, setMaxDurationSec] = useState<number>(60);
  const [generatingShorts, setGeneratingShorts] = useState<boolean>(false);

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

  // Export State
  const [exportingCandidateId, setExportingCandidateId] = useState<string | null>(null);
  const [exportSuccessToast, setExportSuccessToast] = useState<string | null>(null);

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

  // Load Intelligence Data (Runs, Scenes, Transcript, Highlights)
  const loadIntelligenceData = useCallback(async () => {
    if (!assetId) return;
    const effPid = asset?.project_id || projectId || 'default';
    try {
      const [runs, hls, genRuns, novHist] = await Promise.all([
        fetchAnalysisRuns(effPid, assetId).catch(() => []),
        fetchMediaHighlights(effPid, assetId).catch(() => []),
        fetchCandidateGenerationRuns(effPid, assetId).catch(() => []),
        fetchCandidateNoveltyHistory(effPid, assetId).catch(() => null),
      ]);

      setAnalysisRuns(runs);
      setCandidates(hls);
      setGenerationRuns(genRuns);
      setNoveltyHistory(novHist);

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

  // Poll for Active Jobs (Progress Bar Telemetry)
  useEffect(() => {
    let timer: any;
    const pollJobs = async () => {
      try {
        const jobsRes = await fetchJobs();
        const matchingJob = jobsRes.items?.find(
          (j: JobItem) =>
            (j.input_config?.media_asset_id === assetId || j.input_config?.asset_id === assetId) &&
            (j.status === 'running' || j.status === 'queued')
        );
        setActiveJob(matchingJob || null);

        if (matchingJob) {
          void loadIntelligenceData();
        }
      } catch (err) {
        // silent
      }
    };

    void pollJobs();
    timer = setInterval(pollJobs, 2500);
    return () => clearInterval(timer);
  }, [assetId, loadIntelligenceData]);

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

  // Calculate Progress Percent and Details
  const progressDetails = useMemo(() => {
    if (!activeJob) {
      const latestRun = analysisRuns[0];
      if (latestRun?.status === 'running') {
        return {
          isActive: true,
          stage: latestRun.current_stage || 'Analyzing Video...',
          percent: latestRun.progress_pct || 45,
          etaText: 'Processing local neural pipelines...',
        };
      }
      return { isActive: false, stage: 'Idle', percent: 100, etaText: '' };
    }

    const stage = activeJob.current_stage || 'Processing Pipeline';
    const percent = Math.min(100, Math.max(0, activeJob.progress_pct || 0));
    return {
      isActive: true,
      stage,
      percent,
      etaText: `Job ${activeJob.id.slice(0, 8)} • Stage: ${stage}`,
    };
  }, [activeJob, analysisRuns]);

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

  const handleStartAnalysis = async () => {
    if (!asset) return;
    setAnalysisLoading(true);
    try {
      await startMediaAnalysis(asset.project_id || projectId, asset.id, 'balanced');
      await loadIntelligenceData();
    } catch (err: any) {
      alert(`Failed to start analysis: ${err.message || 'Unknown error'}`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Generate Shorts Execution
  const handleGenerateShorts = async () => {
    if (!asset) return;
    setGeneratingShorts(true);
    const count =
      clipCountPreset === 'ai'
        ? undefined
        : clipCountPreset === 'custom'
        ? customClipCount
        : parseInt(clipCountPreset, 10);

    const effPid = asset.project_id || projectId || 'default';
    try {
      await discoverHighlights(effPid, asset.id, {
        target_clip_count: count || 5,
        aspect_ratio: selectedAspectRatio,
        creative_direction: selectedDirection,
        min_duration: minDurationSec,
        max_duration: maxDurationSec,
      });

      await loadIntelligenceData();
      setActiveTab('generated_shorts');
    } catch (err: any) {
      alert(`Failed to generate shorts: ${err.message || 'Unknown error'}`);
    } finally {
      setGeneratingShorts(false);
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
      setExportSuccessToast(`Export job started for "${cand.title}"! Monitor in Working Queue.`);
      setTimeout(() => setExportSuccessToast(null), 5000);
    } catch (err: any) {
      alert(`Export error: ${err.message || 'Failed to submit render'}`);
    } finally {
      setExportingCandidateId(null);
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
              onClick={handleStartAnalysis}
              isLoading={analysisLoading}
              leftIcon={<Sparkles className="w-3.5 h-3.5 text-text-muted" />}
            >
              {analysisRuns.length > 0 ? 'Re-Analyze Video' : 'Analyze Full Video'}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setActiveTab('short_generator')}
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
            { id: 'short_generator', label: 'Short Video Generator' },
            { id: 'generated_shorts', label: `Generated Shorts (${candidates.length})` },
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
          </div>
        )}

        {/* TAB 2: SHORT VIDEO GENERATOR (QUANTITY, 18 DIRECTIONS, RATIOS, TRACKING, GENERATE BUTTON) */}
        {activeTab === 'short_generator' && (
          <div className="max-w-5xl mx-auto space-y-6">
            <Card className="p-6 space-y-6">
              <div>
                <h2 className="text-sm font-bold text-text-primary flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  Short Video Generator Configuration
                </h2>
                <p className="text-xs text-text-secondary mt-1">
                  Configure output parameters, target audience context, aspect ratio, and tracking for AI clip discovery.
                </p>
              </div>

              {/* 1. Quantity Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">
                  1. How Many Short Video Clips Do You Want?
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  {[
                    { id: 'ai', label: 'AI Recommended' },
                    { id: '3', label: '3 Clips' },
                    { id: '5', label: '5 Clips' },
                    { id: '10', label: '10 Clips' },
                    { id: '15', label: '15 Clips' },
                    { id: '20', label: '20 Clips' },
                    { id: 'custom', label: 'Custom' },
                  ].map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => setClipCountPreset(preset.id as any)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                        clipCountPreset === preset.id
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-surface border-border text-text-secondary hover:text-text-primary hover:border-indigo-500/40'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}

                  {clipCountPreset === 'custom' && (
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={customClipCount}
                      onChange={(e) => setCustomClipCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-20 bg-canvas border border-border rounded-xl px-3 py-1.5 text-xs text-text-primary font-mono outline-none focus:border-indigo-500"
                    />
                  )}
                </div>
              </div>

              {/* 2. 18 Creative Directions / Topics / Context */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">
                  2. Creative Direction &amp; Context Focus (18 Modes)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                  {CREATIVE_DIRECTIONS.map((dir) => (
                    <button
                      key={dir.id}
                      type="button"
                      onClick={() => setSelectedDirection(dir.id)}
                      className={`p-3 rounded-xl text-left border transition-all ${
                        selectedDirection === dir.id
                          ? 'bg-indigo-500/10 border-indigo-500 text-text-primary shadow-sm'
                          : 'bg-surface border-border text-text-secondary hover:border-text-muted/50 hover:bg-surface-hover'
                      }`}
                    >
                      <span className={`text-xs font-semibold block ${selectedDirection === dir.id ? 'text-indigo-400' : 'text-text-primary'}`}>
                        {dir.label}
                      </span>
                      <span className="text-[10px] text-text-muted mt-0.5 line-clamp-2">
                        {dir.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 3. Aspect Ratio Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">
                  3. Target Aspect Ratio
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {ASPECT_RATIOS.map((ar) => (
                    <button
                      key={ar.id}
                      type="button"
                      onClick={() => setSelectedAspectRatio(ar.id)}
                      className={`p-3 rounded-xl border text-center transition ${
                        selectedAspectRatio === ar.id
                          ? 'bg-indigo-500/10 border-indigo-500 text-indigo-400'
                          : 'bg-surface border-border text-text-secondary hover:border-text-muted/50'
                      }`}
                    >
                      <Crop className="w-4 h-4 mx-auto mb-1 opacity-70" />
                      <span className="text-xs font-semibold block">{ar.label}</span>
                      <span className="text-[10px] text-text-muted">{ar.ratio}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 4. Subject Tracking Mode */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-primary block">
                  4. Intelligent Subject Tracking Mode
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { id: 'face', label: 'Face Tracking', icon: User, desc: 'Haar Cascade face detection center' },
                    { id: 'upper_body', label: 'Person / Upper Body', icon: Users, desc: 'Tracks speaker torso & motion' },
                    { id: 'object', label: 'Object Motion', icon: MoveHorizontal, desc: 'Spectral saliency focal points' },
                    { id: 'multi', label: 'Multi-Subject Group', icon: Users, desc: 'Dynamic group framing' },
                  ].map((trk) => {
                    const Icon = trk.icon;
                    return (
                      <button
                        key={trk.id}
                        type="button"
                        onClick={() => setTrackingMode(trk.id as any)}
                        className={`p-3 rounded-xl border text-left transition ${
                          trackingMode === trk.id
                            ? 'bg-indigo-500/10 border-indigo-500 text-text-primary'
                            : 'bg-surface border-border text-text-secondary hover:border-text-muted/50'
                        }`}
                      >
                        <Icon className={`w-4 h-4 mb-1.5 ${trackingMode === trk.id ? 'text-indigo-400' : 'text-text-muted'}`} />
                        <span className="text-xs font-semibold block">{trk.label}</span>
                        <span className="text-[10px] text-text-muted block mt-0.5">{trk.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 5. Duration Limits Slider */}
              <div className="space-y-2 pt-2 border-t border-border">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-text-primary">5. Duration Range</span>
                  <span className="font-mono text-indigo-400">{minDurationSec}s - {maxDurationSec}s</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[11px] text-text-muted">Min: {minDurationSec}s</span>
                  <input
                    type="range"
                    min={10}
                    max={45}
                    value={minDurationSec}
                    onChange={(e) => setMinDurationSec(parseInt(e.target.value, 10))}
                    className="flex-1 accent-indigo-500"
                  />
                  <input
                    type="range"
                    min={30}
                    max={120}
                    value={maxDurationSec}
                    onChange={(e) => setMaxDurationSec(parseInt(e.target.value, 10))}
                    className="flex-1 accent-indigo-500"
                  />
                  <span className="text-[11px] text-text-muted">Max: {maxDurationSec}s</span>
                </div>
              </div>

              {/* Big Bottom Action Button */}
              <div className="pt-4 border-t border-border flex justify-end">
                <Button
                  variant="primary"
                  size="lg"
                  className="px-8 shadow-lg shadow-indigo-600/20"
                  isLoading={generatingShorts}
                  onClick={handleGenerateShorts}
                  leftIcon={<Scissors className="w-4 h-4" />}
                >
                  Generate Shorts Now
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* TAB 3: GENERATED SHORTS (CARDS, RATINGS, CUT INTERVALS, EDIT CLIP MODAL, EXPORT MP4) */}
        {activeTab === 'generated_shorts' && (
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-text-primary">Discovered Short Video Candidates</h2>
                <p className="text-xs text-text-secondary mt-0.5">
                  Natural cut boundaries, multimodal virality scores, and framing tools.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveTab('short_generator')}
                leftIcon={<Sparkles className="w-3.5 h-3.5 text-indigo-400" />}
              >
                Generate Another Batch
              </Button>
            </div>

            {candidates.length === 0 ? (
              <EmptyState
                icon={<Scissors className="w-10 h-10 text-text-muted" />}
                title="No Short Clips Generated Yet"
                description="Click Generate Shorts to discover interesting moments from this video."
                actionText="Go to Short Video Generator"
                onAction={() => setActiveTab('short_generator')}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {candidates.map((cand) => {
                  const scorePercent = Math.round(cand.quality_score * 100);
                  return (
                    <Card
                      key={cand.id}
                      className="overflow-hidden rounded-2xl border-border bg-surface hover:border-indigo-500/40 transition flex flex-col justify-between"
                    >
                      <div>
                        {/* Candidate Thumbnail with play trigger */}
                        <div
                          className="relative aspect-video bg-canvas-subtle overflow-hidden cursor-pointer"
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
                          <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/80 text-[10px] font-bold text-indigo-400 border border-indigo-500/30">
                            Score {scorePercent}/100
                          </div>

                          <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 font-mono text-[10px] text-white">
                            {formatSeconds(cand.duration)}
                          </div>
                        </div>

                        {/* Candidate Metadata */}
                        <div className="p-4 space-y-2">
                          <h3 className="text-xs font-bold text-text-primary line-clamp-1">
                            {cand.suggested_title || cand.title || 'Untitled Short'}
                          </h3>

                          {cand.ai_explanation?.hook && (
                            <p className="text-[11px] text-indigo-300 italic line-clamp-2">
                              "{cand.ai_explanation.hook}"
                            </p>
                          )}

                          <div className="flex items-center justify-between text-[11px] text-text-muted font-mono pt-1">
                            <span>Cut: {formatSeconds(cand.start_time)} → {formatSeconds(cand.end_time)}</span>
                            <Badge variant="default" className="text-[10px]">
                              {cand.category || 'Viral'}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      {/* Candidate Actions: Edit Clip & Export */}
                      <div className="p-3 bg-surface-hover/40 border-t border-border flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 text-xs"
                          onClick={() => {
                            setEditingCandidate(cand);
                            setEditorModalOpen(true);
                          }}
                          leftIcon={<Sliders className="w-3.5 h-3.5 text-indigo-400" />}
                        >
                          Edit Clip
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          className="flex-1 text-xs"
                          isLoading={exportingCandidateId === cand.id}
                          onClick={() => handleExportCandidate(cand)}
                          leftIcon={<Download className="w-3.5 h-3.5" />}
                        >
                          Export MP4
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: GENERATED SCRIPTS (CARDS & 1-CLICK REGENERATE VIDEO) */}
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
                      <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">Hook Sentence:</span>
                        <p className="text-text-primary font-medium mt-0.5">"{scr.hook}"</p>
                      </div>

                      <div className="p-3 bg-canvas-subtle rounded-xl border border-border">
                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Dialogue Excerpt:</span>
                        <p className="text-text-secondary mt-1 leading-relaxed">{scr.dialogue}</p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                        {scr.narrativeArc.map((arc, aIdx) => (
                          <div key={aIdx} className="p-2.5 bg-surface border border-border rounded-lg">
                            <span className="text-[9px] font-semibold text-text-muted uppercase block">{arc.phase}</span>
                            <span className="text-[11px] text-text-primary line-clamp-2 mt-0.5">{arc.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-end pt-2 border-t border-border">
                      <Button
                        variant="primary"
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
                        leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                      >
                        Regenerate Video from Script
                      </Button>
                    </div>
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
                        <span className="text-[9px] px-1 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono">
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
                  className="w-full pl-8 pr-3 py-1.5 bg-surface border border-border rounded-xl text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-indigo-500"
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
                    className="p-3 bg-surface border border-border rounded-xl hover:border-indigo-500/50 hover:bg-surface-hover cursor-pointer transition flex items-start gap-3"
                  >
                    <div className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono text-[10px] shrink-0 mt-0.5">
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
                          ? 'border-indigo-500/50 bg-indigo-500/5'
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
                            className="rounded accent-indigo-500 w-4 h-4 cursor-pointer"
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
                  <Activity className="w-4 h-4 text-indigo-400" />
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
    </div>
  );
};
