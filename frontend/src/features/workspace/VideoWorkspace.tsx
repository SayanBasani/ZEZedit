import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileText,
  Film,
  Flame,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Scissors,
  Sliders,
  Sparkles,
  User,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/States';
import {
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTranscript,
  fetchProjectHighlights,
  fetchVideoWorkflowState,
  getProxyUrl,
  getSceneThumbnailUrl,
  getThumbnailUrl,
} from '../../services/apiClient';
import {
  TranscriptSegmentItem,
  VideoSceneItem,
} from '../../types/analysis';
import { CandidateItem } from '../../types/highlights';
import { MediaAssetItem, ProjectItem } from '../../types/projects';
import { VideoWorkflowState } from '../../types/system';
import { AnalysisWorkspace } from '../analysis/AnalysisWorkspace';
import { CharacterStudio } from '../characters/CharacterStudio';
import { BatchExportModal } from '../exports/BatchExportModal';
import { ExportStudio } from '../exports/ExportStudio';
import { HighlightsWorkspace } from '../highlights/HighlightsWorkspace';
import { ReframingWorkspace } from '../reframing/ReframingWorkspace';
import { TimelineEditor } from '../timeline/TimelineEditor';

export type VideoWorkspaceSubTab =
  | 'overview'
  | 'analysis'
  | 'transcript'
  | 'scenes'
  | 'highlights'
  | 'reframing'
  | 'exports'
  | 'timeline'
  | 'characters';

export interface VideoWorkspaceProps {
  project: ProjectItem;
  asset: MediaAssetItem;
  allProjectMedia?: MediaAssetItem[];
  onBack: () => void;
  onSelectMedia?: (asset: MediaAssetItem) => void;
  initialSubTab?: VideoWorkspaceSubTab;
}

export const VideoWorkspace: React.FC<VideoWorkspaceProps> = ({
  project,
  asset,
  allProjectMedia = [],
  onBack,
  onSelectMedia,
  initialSubTab = 'overview',
}) => {
  const [activeSubTab, setActiveSubTab] = useState<VideoWorkspaceSubTab>(() => {
    try {
      const saved = localStorage.getItem(`zezedit_tab_${asset.id}`);
      if (saved) return saved as VideoWorkspaceSubTab;
    } catch {
      // fallback
    }
    return initialSubTab;
  });
  const [nextVideoModalOpen, setNextVideoModalOpen] = useState(false);
  const [batchExportModalOpen, setBatchExportModalOpen] = useState(false);

  // Workflow State & Autosave tracking (Milestone 18)
  const [workflowState, setWorkflowState] = useState<VideoWorkflowState | null>(null);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [autosaveStatus, setAutosaveStatus] = useState<'saved' | 'saving'>('saved');

  // Player state for Overview & Transcript tabs
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const duration = asset.duration_seconds || 0;
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [useProxy, setUseProxy] = useState<boolean>(asset.proxy_status === 'ready');

  // Analysis / Transcript / Scenes data
  const [segments, setSegments] = useState<TranscriptSegmentItem[]>([]);
  const [scenes, setScenes] = useState<VideoSceneItem[]>([]);
  const [transcriptSearch, setTranscriptSearch] = useState<string>('');

  // Persist tab per video
  const handleTabChange = (tab: VideoWorkspaceSubTab) => {
    setActiveSubTab(tab);
    setAutosaveStatus('saving');
    try {
      localStorage.setItem(`zezedit_tab_${asset.id}`, tab);
    } catch {
      // ignore
    }
    setTimeout(() => setAutosaveStatus('saved'), 400);
  };

  // Sync initial subTab if it changes from outside
  useEffect(() => {
    if (initialSubTab && initialSubTab !== 'overview') {
      setActiveSubTab(initialSubTab);
    }
  }, [initialSubTab]);

  // Load authoritative workflow state & candidates
  const loadWorkflowAndCandidates = useCallback(async () => {
    try {
      const [wfState, hlRes] = await Promise.all([
        fetchVideoWorkflowState(project.id, asset.id).catch(() => null),
        fetchProjectHighlights(project.id).catch(() => null),
      ]);
      if (wfState) setWorkflowState(wfState);
      if (hlRes?.candidates) {
        // Filter candidates belonging to this asset if media_asset_id is present, else all project candidates
        const assetCandidates = hlRes.candidates.filter(
          (c: CandidateItem) => !c.media_asset_id || c.media_asset_id === asset.id
        );
        setCandidates(assetCandidates.length > 0 ? assetCandidates : hlRes.candidates);
      }
    } catch (err) {
      console.error('Failed to load workflow state:', err);
    }
  }, [project.id, asset.id]);

  useEffect(() => {
    void loadWorkflowAndCandidates();
  }, [loadWorkflowAndCandidates, activeSubTab]);

  // Load analysis runs, transcripts, and scenes
  const loadAssetData = useCallback(async () => {
    try {
      const runList = await fetchAnalysisRuns(project.id, asset.id);
      const latestRun = runList[0];
      if (latestRun) {
        const [transRes, scenesRes] = await Promise.all([
          fetchAnalysisTranscript(project.id, asset.id, latestRun.id).catch(() => null),
          fetchAnalysisScenes(project.id, asset.id, latestRun.id).catch(() => []),
        ]);
        if (transRes) setSegments(transRes.segments || []);
        if (scenesRes) setScenes(scenesRes);
      }
    } catch {
      // ignore
    }
  }, [project.id, asset.id]);

  useEffect(() => {
    void loadAssetData();
  }, [loadAssetData]);

  // Player controls
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const formatTimecode = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '--';
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  // Video source resolution
  const videoSrc = useProxy && asset.proxy_status === 'ready'
    ? getProxyUrl(project.id, asset.id)
    : `/api/v1/projects/${project.id}/media/${asset.id}/stream`;

  const filteredSegments = segments.filter((s) => {
    if (!transcriptSearch.trim()) return true;
    return s.text.toLowerCase().includes(transcriptSearch.toLowerCase());
  });

  const getStageBadgeStyle = (stage?: string) => {
    switch (stage) {
      case 'ANALYZING':
      case 'DISCOVERING':
      case 'REFRAMING':
      case 'EXPORTING':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
      case 'ANALYSIS_COMPLETED':
      case 'READY_FOR_DISCOVERY':
      case 'CANDIDATES_AVAILABLE':
        return 'bg-violet-500/10 border-violet-500/30 text-violet-400';
      case 'READY_FOR_REVIEW':
      case 'REVIEW_IN_PROGRESS':
        return 'bg-sky-500/10 border-sky-500/30 text-sky-400';
      case 'SHORTS_APPROVED':
      case 'READY_FOR_EXPORT':
        return 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400';
      case 'EXPORT_COMPLETED':
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
      case 'FAILED':
        return 'bg-rose-500/10 border-rose-500/30 text-rose-400';
      default:
        return 'bg-zinc-500/10 border-zinc-500/30 text-zinc-400';
    }
  };

  const formatStageLabel = (stage?: string) => {
    if (!stage) return 'Ready for Analysis';
    return stage
      .toLowerCase()
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const renderPrimaryAction = () => {
    const stage = workflowState?.current_stage || 'READY_FOR_ANALYSIS';
    const approvedCount = workflowState?.approved_short_counts || 0;
    const candCount = workflowState?.candidate_counts.total || 0;

    if (stage === 'IMPORTED' || stage === 'READY_FOR_ANALYSIS') {
      return (
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Activity className="w-3.5 h-3.5" />}
          onClick={() => handleTabChange('analysis')}
          className="text-xs"
        >
          Start AI Analysis
        </Button>
      );
    }

    if (stage === 'ANALYZING') {
      return (
        <Button
          size="sm"
          variant="secondary"
          leftIcon={<Clock className="w-3.5 h-3.5 animate-spin" />}
          onClick={() => handleTabChange('analysis')}
          className="text-xs text-amber-400 border-amber-500/30"
        >
          Analyzing... View
        </Button>
      );
    }

    if (stage === 'ANALYSIS_COMPLETED' || stage === 'READY_FOR_DISCOVERY') {
      return (
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Flame className="w-3.5 h-3.5" />}
          onClick={() => handleTabChange('highlights')}
          className="text-xs"
        >
          Discover AI Highlights
        </Button>
      );
    }

    if (stage === 'DISCOVERING') {
      return (
        <Button
          size="sm"
          variant="secondary"
          leftIcon={<Clock className="w-3.5 h-3.5 animate-spin" />}
          onClick={() => handleTabChange('highlights')}
          className="text-xs text-amber-400 border-amber-500/30"
        >
          Discovering... View
        </Button>
      );
    }

    if (stage === 'CANDIDATES_AVAILABLE' || stage === 'READY_FOR_REVIEW' || stage === 'REVIEW_IN_PROGRESS') {
      return (
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Sparkles className="w-3.5 h-3.5" />}
          onClick={() => handleTabChange('highlights')}
          className="text-xs"
        >
          Review Shorts ({candCount})
        </Button>
      );
    }

    if (stage === 'SHORTS_APPROVED' || stage === 'READY_FOR_EXPORT' || (approvedCount > 0 && stage !== 'EXPORT_COMPLETED')) {
      return (
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Download className="w-3.5 h-3.5" />}
          onClick={() => setBatchExportModalOpen(true)}
          className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
        >
          Batch Export Approved ({approvedCount})
        </Button>
      );
    }

    if (stage === 'EXPORT_COMPLETED') {
      return (
        <Button
          size="sm"
          variant="secondary"
          leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
          onClick={() => setNextVideoModalOpen(true)}
          className="text-xs border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10"
        >
          Next Video Edit →
        </Button>
      );
    }

    return (
      <Button
        size="sm"
        variant="primary"
        leftIcon={<ArrowRight className="w-3.5 h-3.5" />}
        onClick={() => handleTabChange('exports')}
        className="text-xs"
      >
        Shorts & Export
      </Button>
    );
  };

  const completed = workflowState?.completed_stages || [];

  return (
    <div className="h-full flex flex-col bg-canvas text-text-primary overflow-hidden select-none">
      {/* Top Workspace Header */}
      <div className="shrink-0 h-13 px-4 border-b border-border bg-surface/90 backdrop-blur-sm flex items-center justify-between gap-4">
        {/* Left: Back & Asset Identity */}
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            className="text-text-muted hover:text-text-primary px-2"
          >
            Library
          </Button>

          <div className="h-4 w-px bg-border shrink-0" />

          <div className="min-w-0 flex items-center gap-2">
            <div className="p-1 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
              <Film className="w-3.5 h-3.5" />
            </div>
            <h2 className="text-xs font-semibold text-text-primary truncate max-w-[240px] sm:max-w-md" title={asset.original_filename}>
              {asset.original_filename}
            </h2>
            <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-surface-hover text-[10px] font-mono text-text-muted">
              {asset.width && asset.height ? `${asset.width}x${asset.height}` : 'Audio'}
            </span>
            <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-surface-hover text-[10px] font-mono text-text-muted">
              {formatTimecode(asset.duration_seconds || 0)}
            </span>
          </div>
        </div>

        {/* Right: Quick State, Next Video Action & Project Context */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setNextVideoModalOpen(true)}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1 bg-indigo-600/15 border-indigo-500/30 text-indigo-400 hover:bg-indigo-600/25"
          >
            <span>Next Video</span>
          </Button>

          <span className="text-[11px] font-mono text-text-muted hidden md:inline">
            Project: <strong className="text-text-primary font-medium">{project.name}</strong>
          </span>
          {asset.proxy_status === 'ready' && (
            <Badge variant="success" size="sm">
              Proxy 480p
            </Badge>
          )}
          <Badge variant={asset.is_external ? 'default' : 'purple'} size="sm">
            {asset.is_external ? 'External' : 'Managed'}
          </Badge>
        </div>
      </div>

      {/* ==================== AUTHORITATIVE WORKFLOW STAGE HEADER BANNER (MILESTONE 18) ==================== */}
      <div className="shrink-0 px-4 py-2 border-b border-border bg-surface-hover/30 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left: Current Authoritative Stage & Progress Stepper */}
        <div className="flex items-center gap-3 overflow-x-auto no-scrollbar py-0.5">
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-[11px] font-medium text-text-muted">Pipeline:</span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border flex items-center gap-1.5 ${getStageBadgeStyle(
                workflowState?.current_stage
              )}`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              <span>{formatStageLabel(workflowState?.current_stage)}</span>
            </span>
          </div>

          <div className="h-3.5 w-px bg-border shrink-0 hidden sm:block" />

          {/* Stepper Steps */}
          <div className="hidden md:flex items-center gap-1.5 text-[11px] font-mono text-text-muted shrink-0">
            <span className="text-emerald-400 font-medium">1. Ingest ✓</span>
            <span className="text-border">→</span>
            <span className={completed.includes('ANALYSIS_COMPLETED') ? 'text-emerald-400 font-medium' : 'text-text-muted'}>
              2. Analysis {completed.includes('ANALYSIS_COMPLETED') ? '✓' : ''}
            </span>
            <span className="text-border">→</span>
            <span className={completed.includes('CANDIDATES_AVAILABLE') ? 'text-emerald-400 font-medium' : 'text-text-muted'}>
              3. Highlights {completed.includes('CANDIDATES_AVAILABLE') ? '✓' : ''}
            </span>
            <span className="text-border">→</span>
            <span className={completed.includes('SHORTS_APPROVED') ? 'text-emerald-400 font-medium' : 'text-text-muted'}>
              4. Review {completed.includes('SHORTS_APPROVED') ? '✓' : ''}
            </span>
            <span className="text-border">→</span>
            <span className={completed.includes('EXPORT_COMPLETED') ? 'text-emerald-400 font-medium' : 'text-text-muted'}>
              5. Export {completed.includes('EXPORT_COMPLETED') ? '✓' : ''}
            </span>
          </div>
        </div>

        {/* Right: Telemetry Counts, Autosave State & Dynamic Next Action */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-text-muted">
            <span title="Discovered candidate shorts">
              Cand: <strong className="text-text-primary">{workflowState?.candidate_counts.total || 0}</strong>
            </span>
            <span>•</span>
            <span title="Approved candidate shorts">
              Approved: <strong className="text-emerald-400">{workflowState?.approved_short_counts || 0}</strong>
            </span>
            <span>•</span>
            <span title="Rendered short videos">
              Exported: <strong className="text-indigo-400">{workflowState?.export_counts.completed || 0}</strong>
            </span>
          </div>

          <div className="h-3.5 w-px bg-border shrink-0 hidden lg:block" />

          {/* Autosave Status */}
          <span className="text-[10px] font-mono text-emerald-400/90 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>{autosaveStatus === 'saving' ? 'Saving...' : 'Auto-saved'}</span>
          </span>

          {/* Dynamic Next-Action Dispatch */}
          {renderPrimaryAction()}
        </div>
      </div>

      {/* Sub-Workspace Tab Navigation Strip */}
      <div className="shrink-0 px-4 border-b border-border bg-surface flex items-center gap-1 overflow-x-auto no-scrollbar">
        {[
          { id: 'overview', label: 'Overview', icon: <Eye className="w-3.5 h-3.5" /> },
          { id: 'analysis', label: 'Analysis', icon: <Activity className="w-3.5 h-3.5" /> },
          { id: 'transcript', label: 'Transcript', icon: <FileText className="w-3.5 h-3.5" /> },
          { id: 'scenes', label: 'Scenes', icon: <Layers className="w-3.5 h-3.5" /> },
          { id: 'highlights', label: 'AI Highlights', icon: <Flame className="w-3.5 h-3.5" /> },
          { id: 'reframing', label: 'Smart Reframing', icon: <Sliders className="w-3.5 h-3.5" /> },
          { id: 'characters', label: 'Characters', icon: <User className="w-3.5 h-3.5" /> },
          { id: 'exports', label: 'Shorts & Export', icon: <Download className="w-3.5 h-3.5" /> },
          { id: 'timeline', label: 'Timeline Editor', icon: <Scissors className="w-3.5 h-3.5" /> },
        ].map((tab) => {
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id as VideoWorkspaceSubTab)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition whitespace-nowrap ${
                isActive
                  ? 'border-indigo-500 text-indigo-400 font-semibold'
                  : 'border-transparent text-text-muted hover:text-text-primary hover:border-border'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>


      {/* Sub-Workspace Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* ==================== 1. OVERVIEW SUB-WORKSPACE ==================== */}
        {activeSubTab === 'overview' && (
          <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Main Video Player & Playhead */}
              <div className="lg:col-span-2 space-y-3">
                <div className="relative aspect-video bg-black rounded-xl overflow-hidden border border-border shadow-md group">
                  <video
                    ref={videoRef}
                    src={videoSrc}
                    poster={asset.thumbnail_reference_path ? getThumbnailUrl(project.id, asset.id) : undefined}
                    onTimeUpdate={handleTimeUpdate}
                    onEnded={() => setIsPlaying(false)}
                    className="w-full h-full object-contain cursor-pointer"
                    onClick={togglePlay}
                  />

                  {/* Play/Pause Center Button Overlay on Pause */}
                  {!isPlaying && (
                    <button
                      onClick={togglePlay}
                      className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition text-white"
                      aria-label="Play video"
                    >
                      <div className="w-14 h-14 rounded-full bg-indigo-600/90 hover:bg-indigo-600 flex items-center justify-center shadow-lg transition transform hover:scale-105">
                        <Play className="w-6 h-6 ml-0.5" />
                      </div>
                    </button>
                  )}

                  {/* Transport Scrub Bar */}
                  <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/90 via-black/50 to-transparent flex flex-col gap-1.5">
                    <input
                      type="range"
                      min={0}
                      max={duration || 100}
                      step={0.1}
                      value={currentTime}
                      onChange={(e) => handleSeek(parseFloat(e.target.value))}
                      className="w-full h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />

                    <div className="flex items-center justify-between text-xs text-white/90 font-mono">
                      <div className="flex items-center gap-2">
                        <button onClick={togglePlay} className="p-1 hover:text-indigo-400">
                          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </button>
                        <span>
                          {formatTimecode(currentTime)} / {formatTimecode(duration)}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {asset.proxy_status === 'ready' && (
                          <button
                            onClick={() => setUseProxy(!useProxy)}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium transition ${
                              useProxy
                                ? 'bg-indigo-600 text-white'
                                : 'bg-white/20 text-white/70 hover:text-white'
                            }`}
                            title="Toggle 480p proxy playback"
                          >
                            {useProxy ? 'Proxy Scrub: ON' : 'Proxy Scrub: OFF'}
                          </button>
                        )}
                        <button onClick={() => setIsMuted(!isMuted)} className="p-1 hover:text-indigo-400">
                          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quick Action Navigation Bar */}
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  <Button
                    size="sm"
                    variant="primary"
                    leftIcon={<Activity className="w-4 h-4" />}
                    onClick={() => setActiveSubTab('analysis')}
                  >
                    Run Full Analysis
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Flame className="w-4 h-4" />}
                    onClick={() => setActiveSubTab('highlights')}
                  >
                    AI Highlights
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Sliders className="w-4 h-4" />}
                    onClick={() => setActiveSubTab('reframing')}
                  >
                    9:16 Reframer
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Scissors className="w-4 h-4" />}
                    onClick={() => setActiveSubTab('timeline')}
                  >
                    Timeline Editor
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Download className="w-4 h-4" />}
                    onClick={() => setActiveSubTab('exports')}
                  >
                    Shorts Export
                  </Button>
                </div>
              </div>

              {/* Right Col: Media Specs & Pipeline Status */}
              <div className="space-y-4">
                {/* Media Specifications Card */}
                <Card className="space-y-3 p-4">
                  <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    File Specifications
                  </h3>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">Duration</span>
                      <span className="text-text-primary">{formatTimecode(asset.duration_seconds || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">Resolution</span>
                      <span className="text-text-primary">
                        {asset.width && asset.height ? `${asset.width}x${asset.height}` : 'Audio Only'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">Frame Rate</span>
                      <span className="text-text-primary">
                        {asset.fps ? `${Math.round(asset.fps * 100) / 100} fps` : '--'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">Video Codec</span>
                      <span className="text-text-primary uppercase">{asset.video_codec || 'H.264'}</span>
                    </div>
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">Audio Codec</span>
                      <span className="text-text-primary uppercase">{asset.audio_codec || 'AAC'}</span>
                    </div>
                    <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
                      <span className="text-text-muted">File Size</span>
                      <span className="text-text-primary">{formatBytes(asset.file_size_bytes)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-muted">Storage</span>
                      <span className="text-text-primary">{asset.is_external ? 'External' : 'Managed'}</span>
                    </div>
                  </div>
                </Card>

                {/* Processing Pipeline Matrix */}
                <Card className="space-y-3 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                      Processing Pipeline
                    </h3>
                    <button
                      onClick={loadAssetData}
                      className="text-[11px] text-indigo-400 hover:underline flex items-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" /> Refresh
                    </button>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-surface-hover/50">
                      <span className="text-text-secondary">Metadata & Ingestion</span>
                      <Badge variant="success" size="sm">Ready</Badge>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-surface-hover/50">
                      <span className="text-text-secondary">Poster Thumbnail</span>
                      {asset.thumbnail_reference_path ? (
                        <Badge variant="success" size="sm">Ready</Badge>
                      ) : (
                        <Badge variant="warning" size="sm">Pending</Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-surface-hover/50">
                      <span className="text-text-secondary">480p Scrub Proxy</span>
                      {asset.proxy_status === 'ready' ? (
                        <Badge variant="success" size="sm">Ready</Badge>
                      ) : (
                        <Badge variant="default" size="sm">{asset.proxy_status}</Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-surface-hover/50">
                      <span className="text-text-secondary">Whisper Transcript</span>
                      {segments.length > 0 ? (
                        <Badge variant="success" size="sm">{segments.length} segments</Badge>
                      ) : (
                        <Badge variant="default" size="sm">Not run</Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded-lg bg-surface-hover/50">
                      <span className="text-text-secondary">Scene Cut Analysis</span>
                      {scenes.length > 0 ? (
                        <Badge variant="success" size="sm">{scenes.length} cuts</Badge>
                      ) : (
                        <Badge variant="default" size="sm">Not run</Badge>
                      )}
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* ==================== 2. VIDEO ANALYSIS SUB-WORKSPACE ==================== */}
        {activeSubTab === 'analysis' && (
          <AnalysisWorkspace
            projectId={project.id}
            mediaAsset={asset}
            onBack={() => setActiveSubTab('overview')}
            onNavigateToHighlights={() => setActiveSubTab('highlights')}
          />
        )}

        {/* ==================== 3. TRANSCRIPT & AUDIO SUB-WORKSPACE ==================== */}
        {activeSubTab === 'transcript' && (
          <div className="max-w-5xl mx-auto p-4 sm:p-6 space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-surface p-3.5 rounded-xl border border-border">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-semibold text-text-primary">
                  Timestamped Transcript ({segments.length} segments)
                </span>
              </div>

              <div className="w-full sm:w-64">
                <input
                  type="text"
                  placeholder="Search transcript text..."
                  value={transcriptSearch}
                  onChange={(e) => setTranscriptSearch(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-canvas border border-border rounded-lg text-text-primary focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {segments.length === 0 ? (
              <EmptyState
                title="No transcript available"
                description="Speech has not been transcribed for this video yet. Run video analysis to generate timestamped Whisper segments."
                actionText="Go to Analysis"
                onAction={() => setActiveSubTab('analysis')}
              />
            ) : (
              <div className="space-y-2">
                {filteredSegments.map((segment) => (
                  <div
                    key={segment.id}
                    onClick={() => handleSeek(segment.start_time)}
                    className="p-3 bg-surface hover:bg-surface-hover/80 border border-border rounded-xl transition cursor-pointer flex items-start gap-3 group"
                  >
                    <button
                      className="px-2 py-0.5 rounded bg-indigo-600/10 border border-indigo-500/20 text-[11px] font-mono text-indigo-400 shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition"
                      title="Seek player to timestamp"
                    >
                      {formatTimecode(segment.start_time)}
                    </button>
                    <p className="text-xs text-text-primary leading-relaxed flex-1">
                      {segment.text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ==================== 4. SCENES SUB-WORKSPACE ==================== */}
        {activeSubTab === 'scenes' && (
          <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between bg-surface p-3.5 rounded-xl border border-border">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-semibold text-text-primary">
                  Detected Scene Cuts ({scenes.length} scenes)
                </span>
              </div>
            </div>

            {scenes.length === 0 ? (
              <EmptyState
                title="No scenes detected"
                description="Scene detection has not been executed for this video yet. Run video analysis to compute scene cuts."
                actionText="Run Video Analysis"
                onAction={() => setActiveSubTab('analysis')}
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {scenes.map((scene) => (
                  <Card
                    key={scene.id}
                    onClick={() => handleSeek(scene.start_time)}
                    className="p-0 overflow-hidden cursor-pointer group hover:border-indigo-500/50 transition border border-border"
                  >
                    <div className="relative aspect-video bg-black flex items-center justify-center border-b border-border overflow-hidden">
                      <img
                        src={getSceneThumbnailUrl(project.id, asset.id, scene.id)}
                        alt={`Scene ${scene.scene_index + 1}`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-mono text-white">
                        {formatTimecode(scene.start_time)} - {formatTimecode(scene.end_time)}
                      </span>
                    </div>
                    <div className="p-3 space-y-1">
                      <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                        <span>Scene {scene.scene_index}</span>
                        <span className="text-[10px] text-text-muted font-mono">
                          {Math.round((scene.end_time - scene.start_time) * 10) / 10}s
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted font-mono">
                        Cut score: {scene.change_score ? scene.change_score.toFixed(2) : 'detected'}
                      </p>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ==================== 5. AI HIGHLIGHTS SUB-WORKSPACE ==================== */}
        {activeSubTab === 'highlights' && (
          <HighlightsWorkspace
            projectId={project.id}
            mediaAssets={allProjectMedia.length ? allProjectMedia : [asset]}
            preselectedAssetId={asset.id}
            onNavigateToAnalysis={() => setActiveSubTab('analysis')}
          />
        )}

        {/* ==================== 6. SMART REFRAMING SUB-WORKSPACE ==================== */}
        {activeSubTab === 'reframing' && (
          <ReframingWorkspace
            projectId={project.id}
            mediaAsset={asset}
            onBack={() => setActiveSubTab('overview')}
          />
        )}

        {/* ==================== 7. SHORTS & EXPORT SUB-WORKSPACE ==================== */}
        {activeSubTab === 'exports' && (
          <ExportStudio
            projectId={project.id}
            mediaAssets={allProjectMedia.length ? allProjectMedia : [asset]}
            onNavigateToHighlights={() => setActiveSubTab('highlights')}
            onNavigateToReframing={() => setActiveSubTab('reframing')}
          />
        )}

        {/* ==================== 8. MULTI-TRACK TIMELINE SUB-WORKSPACE ==================== */}
        {activeSubTab === 'timeline' && (
          <TimelineEditor currentProject={project} />
        )}

        {/* ==================== 9. CHARACTER STUDIO SUB-WORKSPACE (PRESERVED AS DEFERRED) ==================== */}
        {activeSubTab === 'characters' && (
          <CharacterStudio
            projectId={project.id}
            mediaAssets={allProjectMedia.length ? allProjectMedia : [asset]}
          />
        )}
      </div>

      {/* ==================== BATCH EXPORT MODAL (MILESTONE 18) ==================== */}
      <BatchExportModal
        isOpen={batchExportModalOpen}
        onClose={() => setBatchExportModalOpen(false)}
        projectId={project.id}
        candidates={candidates}
        onSuccess={() => {
          void loadWorkflowAndCandidates();
        }}
      />

      {/* ==================== NEXT VIDEO TRANSITION MODAL ==================== */}
      {nextVideoModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-xl bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <Film className="w-4 h-4 text-indigo-400" />
                  <span>Next Video Selection</span>
                </h3>
                <p className="text-xs text-text-muted mt-0.5">
                  Select another source video to edit. All current boundary trims, highlights, and timeline states are saved.
                </p>
              </div>
              <button
                onClick={() => setNextVideoModalOpen(false)}
                className="p-1.5 text-text-muted hover:text-text-primary rounded-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                Available Videos in {project.name}
              </div>

              {allProjectMedia.filter((m) => m.id !== asset.id).length === 0 ? (
                <div className="py-8 text-center text-text-muted space-y-3">
                  <p className="text-xs">No other videos currently imported in this project.</p>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => {
                      setNextVideoModalOpen(false);
                      onBack();
                    }}
                  >
                    Go to Library to Import New Video
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {allProjectMedia
                    .filter((m) => m.id !== asset.id)
                    .map((other) => (
                      <div
                        key={other.id}
                        className="p-3 rounded-xl border border-border bg-surface-hover/50 hover:border-indigo-500/50 hover:bg-surface-hover flex items-center justify-between gap-3 transition cursor-pointer"
                        onClick={() => {
                          if (onSelectMedia) {
                            onSelectMedia(other);
                            setActiveSubTab('overview');
                            setNextVideoModalOpen(false);
                          }
                        }}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-16 h-10 rounded-lg bg-black/40 border border-border/60 overflow-hidden shrink-0 flex items-center justify-center">
                            {other.thumbnail_reference_path ? (
                              <img
                                src={getThumbnailUrl(project.id, other.id)}
                                alt=""
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Film className="w-4 h-4 text-text-muted" />
                            )}
                          </div>
                          <div className="min-w-0 space-y-0.5">
                            <span className="text-xs font-semibold text-text-primary block truncate">
                              {other.original_filename}
                            </span>
                            <span className="text-[10px] text-text-muted font-mono block">
                              {formatTimecode(other.duration_seconds || 0)} • {other.width}x{other.height} • {formatBytes(other.file_size_bytes)}
                            </span>
                          </div>
                        </div>

                        <Button size="sm" variant="secondary" className="shrink-0 text-xs">
                          Edit This Video
                        </Button>
                      </div>
                    ))}
                </div>
              )}
            </div>

            <div className="p-3 border-t border-border flex items-center justify-between bg-surface/80">
              <span className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Workspace auto-saved
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => onBack()}>
                  Return to Library
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setNextVideoModalOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
