import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Check,
  Edit2,
  Eye,
  FileText,
  Film,
  Layers,
  Loader2,
  Maximize2,
  MessageSquare,
  Pause,
  Play,
  RotateCcw,
  Search,
  Sparkles,
  Undo2,
  Volume2,
  X,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import {
  cancelAnalysisRun,
  deleteTranscriptCorrection,
  fetchAnalysisContext,
  fetchAnalysisObservations,
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTranscript,
  fetchAudioAnalysis,
  getProxyUrl,
  getSceneThumbnailUrl,
  getThumbnailUrl,
  saveTranscriptCorrection,
  startMediaAnalysis,
} from '../../services/apiClient';
import {
  AnalysisRunItem,
  AudioAnalysisItem,
  SpeechTurnItem,
  TemporalContextPayload,
  TranscriptSegmentItem,
  VideoSceneItem,
  VisualObservationItem,
} from '../../types/analysis';
import { MediaAssetItem } from '../../types/projects';

interface AnalysisWorkspaceProps {
  projectId: string;
  mediaAsset: MediaAssetItem;
  onBack: () => void;
  onNavigateToHighlights?: () => void;
}

export const AnalysisWorkspace: React.FC<AnalysisWorkspaceProps> = ({
  projectId,
  mediaAsset,
  onBack,
  onNavigateToHighlights,
}) => {
  const [runs, setRuns] = useState<AnalysisRunItem[]>([]);
  const [selectedRun, setSelectedRun] = useState<AnalysisRunItem | null>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'scenes' | 'vision' | 'audio' | 'context'>('transcript');
  const [profile, setProfile] = useState<'fast' | 'balanced' | 'detailed'>('balanced');
  const [forceReanalysis, setForceReanalysis] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Analysis Data
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegmentItem[]>([]);
  const [speechTurns, setSpeechTurns] = useState<SpeechTurnItem[]>([]);
  const [scenes, setScenes] = useState<VideoSceneItem[]>([]);
  const [observations, setObservations] = useState<VisualObservationItem[]>([]);
  const [audioAnalysis, setAudioAnalysis] = useState<AudioAnalysisItem | null>(null);
  const [temporalContext, setTemporalContext] = useState<TemporalContextPayload | null>(null);

  // Transcript Inline Correction State (ZEZ-025)
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const [isSavingCorrection, setIsSavingCorrection] = useState<boolean>(false);

  // Lightbox Modal State (ZEZ-027)
  const [lightboxScene, setLightboxScene] = useState<VideoSceneItem | null>(null);

  // Player state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(mediaAsset.duration_seconds || 0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [searchFilter, setSearchFilter] = useState<string>('');

  const loadRuns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedRuns = await fetchAnalysisRuns(projectId, mediaAsset.id);
      setRuns(fetchedRuns);
      if (fetchedRuns.length > 0) {
        setSelectedRun(fetchedRuns[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis runs');
    } finally {
      setLoading(false);
    }
  }, [projectId, mediaAsset.id]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Poll active run
  useEffect(() => {
    if (!selectedRun || (selectedRun.status !== 'running' && selectedRun.status !== 'pending')) {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const fetchedRuns = await fetchAnalysisRuns(projectId, mediaAsset.id);
        setRuns(fetchedRuns);
        const current = fetchedRuns.find((r) => r.id === selectedRun.id);
        if (current) {
          setSelectedRun(current);
        }
      } catch {
        // quiet polling error
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [projectId, mediaAsset.id, selectedRun]);

  // Load run details
  const loadRunDetails = useCallback(async (runId: string) => {
    try {
      const [tData, sData, oData, aData] = await Promise.all([
        fetchAnalysisTranscript(projectId, mediaAsset.id, runId),
        fetchAnalysisScenes(projectId, mediaAsset.id, runId),
        fetchAnalysisObservations(projectId, mediaAsset.id, runId),
        fetchAudioAnalysis(projectId, mediaAsset.id, runId).catch(() => null),
      ]);
      setTranscriptSegments(tData.segments);
      setSpeechTurns(tData.speech_turns);
      setScenes(sData);
      setObservations(oData);
      setAudioAnalysis(aData);
    } catch (err) {
      console.error('Failed to load analysis details:', err);
    }
  }, [projectId, mediaAsset.id]);

  useEffect(() => {
    if (selectedRun && selectedRun.status === 'completed') {
      loadRunDetails(selectedRun.id);
    }
  }, [selectedRun, loadRunDetails]);

  // Load temporal context when scrubbing
  const queryContext = useCallback(
    async (time: number) => {
      if (!selectedRun || selectedRun.status !== 'completed') return;
      try {
        const ctx = await fetchAnalysisContext(projectId, mediaAsset.id, selectedRun.id, time);
        setTemporalContext(ctx);
      } catch {
        // quiet context query error
      }
    },
    [projectId, mediaAsset.id, selectedRun]
  );

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
      queryContext(time);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleStartAnalysis = async () => {
    try {
      setError(null);
      const newRun = await startMediaAnalysis(
        projectId,
        mediaAsset.id,
        profile,
        {},
        false,
        forceReanalysis
      );
      setRuns([newRun, ...runs.filter((r) => r.id !== newRun.id)]);
      setSelectedRun(newRun);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger video analysis');
    }
  };

  const handleCancelRun = async () => {
    if (!selectedRun) return;
    try {
      await cancelAnalysisRun(projectId, mediaAsset.id, selectedRun.id);
      setSelectedRun({ ...selectedRun, status: 'cancelled' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel analysis run');
    }
  };

  // Non-destructive transcript correction handlers (ZEZ-025)
  const handleStartEdit = (segment: TranscriptSegmentItem) => {
    setEditingSegmentId(segment.id);
    setEditingText(segment.corrected_text || segment.text);
  };

  const handleCancelEdit = () => {
    setEditingSegmentId(null);
    setEditingText('');
  };

  const handleSaveCorrection = async (segment: TranscriptSegmentItem) => {
    if (!editingText.trim() || editingText === (segment.corrected_text || segment.text)) {
      setEditingSegmentId(null);
      return;
    }
    setIsSavingCorrection(true);
    try {
      const saved = await saveTranscriptCorrection(projectId, mediaAsset.id, {
        segment_id: segment.id,
        start_time: segment.start_time,
        end_time: segment.end_time,
        original_text: segment.text,
        corrected_text: editingText.trim(),
      });
      setTranscriptSegments((prev) =>
        prev.map((s) =>
          s.id === segment.id
            ? { ...s, corrected_text: saved.corrected_text, is_corrected: true, correction_id: saved.id }
            : s
        )
      );
      setEditingSegmentId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save transcript correction');
    } finally {
      setIsSavingCorrection(false);
    }
  };

  const handleRevertCorrection = async (segment: TranscriptSegmentItem) => {
    if (!segment.correction_id) return;
    try {
      await deleteTranscriptCorrection(projectId, mediaAsset.id, segment.correction_id);
      setTranscriptSegments((prev) =>
        prev.map((s) =>
          s.id === segment.id
            ? { ...s, corrected_text: null, is_corrected: false, correction_id: null }
            : s
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revert transcript correction');
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  const videoSrc = getProxyUrl(projectId, mediaAsset.id);

  if (loading && runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] text-text-muted gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
        <p className="text-sm">Loading analysis workspace...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] space-y-4 p-4 max-w-7xl mx-auto select-none">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} aria-label="Back to Media Library">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2 text-text-primary">
              <Film className="w-5 h-5 text-brand" />
              {mediaAsset.original_filename}
            </h1>
            <p className="text-xs text-text-muted">
              {mediaAsset.width && mediaAsset.height ? `${mediaAsset.width}×${mediaAsset.height}` : 'Unknown'} •{' '}
              {mediaAsset.fps ? `${mediaAsset.fps.toFixed(1)} fps` : 'Unknown fps'} •{' '}
              {formatSeconds(duration)}
            </p>
          </div>
        </div>

        {/* Run Selector & Analysis Controls (ZEZ-029, ZEZ-030) */}
        <div className="flex items-center gap-2">
          {runs.length > 0 && (
            <div className="flex items-center gap-1.5 mr-2">
              <span className="text-[11px] text-text-muted">Run:</span>
              <select
                value={selectedRun?.id || ''}
                onChange={(e) => {
                  const r = runs.find((item) => item.id === e.target.value);
                  if (r) setSelectedRun(r);
                }}
                className="bg-surface border border-border rounded-lg text-xs px-2 py-1 text-text-primary focus:outline-none"
              >
                {runs.map((r, i) => (
                  <option key={r.id} value={r.id}>
                    Run #{runs.length - i} ({r.profile}) — {r.status}
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedRun && (selectedRun.status === 'running' || selectedRun.status === 'pending') ? (
            <div className="flex items-center gap-3 bg-surface px-3 py-1.5 rounded-lg border border-border">
              <Loader2 className="w-4 h-4 animate-spin text-brand" />
              <div className="flex flex-col">
                <span className="text-xs font-medium capitalize text-text-primary">
                  {selectedRun.current_stage?.replace('_', ' ') || 'Processing...'}
                </span>
                <span className="text-[10px] text-text-muted">
                  {selectedRun.progress_pct.toFixed(0)}% completed
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleCancelRun} className="text-red-400 h-7 px-2">
                <XCircle className="w-3.5 h-3.5 mr-1" /> Cancel
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value as 'fast' | 'balanced' | 'detailed')}
                className="bg-surface border border-border rounded-lg text-xs px-2.5 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="fast">Fast (Quick scan, fewer frames)</option>
                <option value="balanced">Balanced (Whisper + scenes + vision)</option>
                <option value="detailed">Detailed (Dense keyframe inspection)</option>
              </select>

              <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer px-1">
                <input
                  type="checkbox"
                  checked={forceReanalysis}
                  onChange={(e) => setForceReanalysis(e.target.checked)}
                  className="rounded border-border text-brand focus:ring-brand"
                />
                <span>Force fresh</span>
              </label>

              <Button onClick={handleStartAnalysis} size="sm" variant="primary" className="gap-1.5">
                <Sparkles className="w-4 h-4" /> Start Analysis
              </Button>

              {onNavigateToHighlights && selectedRun?.status === 'completed' && (
                <Button
                  onClick={onNavigateToHighlights}
                  size="sm"
                  variant="outline"
                  className="gap-1.5 border-amber-500/40 text-amber-400 hover:bg-amber-500/10"
                >
                  <Sparkles className="w-4 h-4" /> Discover Highlights
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-3 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Grid: Video Player on Left, Multimodal Analysis on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        {/* Left Column: Player & Quick Scene Markers */}
        <div className="lg:col-span-7 flex flex-col space-y-3 min-h-0">
          <Card className="flex-1 flex flex-col justify-between overflow-hidden bg-black/90 p-0 border-border">
            <div className="relative flex-1 flex items-center justify-center bg-black min-h-[300px]">
              <video
                ref={videoRef}
                src={videoSrc}
                poster={getThumbnailUrl(projectId, mediaAsset.id)}
                className="w-full h-full max-h-[440px] object-contain cursor-pointer"
                onClick={togglePlay}
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setCurrentTime(videoRef.current.currentTime);
                  }
                }}
                onLoadedMetadata={() => {
                  if (videoRef.current) {
                    setDuration(videoRef.current.duration);
                  }
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />

              {!isPlaying && (
                <button
                  onClick={togglePlay}
                  className="absolute inset-0 flex items-center justify-center bg-black/25 hover:bg-black/35 transition text-white"
                  aria-label="Play video"
                >
                  <div className="w-12 h-12 rounded-full bg-brand/90 hover:bg-brand flex items-center justify-center shadow-lg transition transform hover:scale-105">
                    <Play className="w-5 h-5 ml-0.5" />
                  </div>
                </button>
              )}
            </div>

            {/* Custom Video Controls Bar */}
            <div className="p-3 bg-surface border-t border-border flex flex-col space-y-2">
              {/* Scrub bar */}
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-text-muted w-14">
                  {formatSeconds(currentTime)}
                </span>
                <input
                  type="range"
                  min="0"
                  max={duration || 100}
                  step="0.05"
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  className="flex-1 h-1.5 bg-canvas rounded-lg appearance-none cursor-pointer accent-brand"
                />
                <span className="text-[11px] font-mono text-text-muted w-14 text-right">
                  {formatSeconds(duration)}
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Button variant="ghost" size="sm" onClick={() => handleSeek(0)} aria-label="Restart Video">
                    <RotateCcw className="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={togglePlay} aria-label={isPlaying ? 'Pause' : 'Play'}>
                    {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  </Button>
                </div>
                {selectedRun && (
                  <Badge variant={selectedRun.status === 'completed' ? 'success' : 'default'} size="sm">
                    {selectedRun.profile} profile • {selectedRun.status}
                  </Badge>
                )}
              </div>
            </div>
          </Card>

          {/* Quick Scene Markers Bar */}
          {scenes.length > 0 && (
            <Card className="p-3 bg-surface border-border">
              <span className="text-xs font-medium text-text-muted mb-2 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-brand" /> Visual Scene Cuts ({scenes.length})
              </span>
              <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                {scenes.map((sc) => {
                  const isCurrent = currentTime >= sc.start_time && currentTime <= sc.end_time;
                  return (
                    <button
                      key={sc.id}
                      onClick={() => handleSeek(sc.representative_timestamp)}
                      className={`flex-shrink-0 text-left px-2.5 py-1.5 rounded-lg border text-xs transition ${
                        isCurrent
                          ? 'border-brand bg-brand/10 text-brand font-medium'
                          : 'border-border bg-canvas hover:bg-surface-hover text-text-secondary'
                      }`}
                    >
                      <div className="font-medium">Scene {sc.scene_index + 1}</div>
                      <div className="text-[10px] font-mono text-text-muted">
                        {formatSeconds(sc.start_time)} - {formatSeconds(sc.end_time)}
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Multimodal Tabs (Transcript, Scenes, Vision, Audio, Context) */}
        <div className="lg:col-span-5 flex flex-col space-y-3 min-h-0">
          <div className="flex border-b border-border bg-surface rounded-t-lg px-2 overflow-x-auto no-scrollbar">
            <button
              onClick={() => setActiveTab('transcript')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                activeTab === 'transcript'
                  ? 'border-brand text-brand'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <FileText className="w-3.5 h-3.5" /> Transcript ({transcriptSegments.length})
            </button>
            <button
              onClick={() => setActiveTab('scenes')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                activeTab === 'scenes'
                  ? 'border-brand text-brand'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <Layers className="w-3.5 h-3.5" /> Scenes ({scenes.length})
            </button>
            <button
              onClick={() => setActiveTab('vision')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                activeTab === 'vision'
                  ? 'border-brand text-brand'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <Eye className="w-3.5 h-3.5" /> Visuals ({observations.length})
            </button>
            <button
              onClick={() => setActiveTab('audio')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                activeTab === 'audio'
                  ? 'border-brand text-brand'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <Volume2 className="w-3.5 h-3.5" /> Audio
            </button>
            <button
              onClick={() => {
                setActiveTab('context');
                queryContext(currentTime);
              }}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                activeTab === 'context'
                  ? 'border-brand text-brand'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <Activity className="w-3.5 h-3.5" /> Context
            </button>
          </div>

          <Card className="flex-1 overflow-hidden p-3 flex flex-col min-h-0 bg-surface border-border">
            {/* Tab 1: Transcript & Speech Turns (ZEZ-024, ZEZ-025) */}
            {activeTab === 'transcript' && (
              <div className="flex flex-col h-full space-y-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Search dialogue words..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="w-full bg-canvas border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                  {transcriptSegments.length > 0 ? (
                    transcriptSegments
                      .filter((seg) => !searchFilter || (seg.corrected_text || seg.text).toLowerCase().includes(searchFilter.toLowerCase()))
                      .map((seg) => {
                        const isSpeaking = currentTime >= seg.start_time && currentTime <= seg.end_time;
                        const isEditing = editingSegmentId === seg.id;
                        return (
                          <div
                            key={seg.id}
                            className={`p-2.5 rounded-lg border text-xs transition ${
                              isSpeaking
                                ? 'border-brand bg-brand/10 shadow-xs'
                                : 'border-border/60 hover:bg-surface-hover'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-1.5">
                                <span className="font-semibold text-text-primary text-[11px] flex items-center gap-1">
                                  <MessageSquare className="w-3 h-3 text-brand" />{' '}
                                  {speechTurns.find(
                                    (t) => t.start_time <= seg.start_time && t.end_time >= seg.end_time
                                  )?.speaker_label || speechTurns[0]?.speaker_label || 'Speaker 1'}
                                </span>
                                <button
                                  onClick={() => handleSeek(seg.start_time)}
                                  className="text-[10px] font-mono text-brand hover:underline font-medium"
                                  title="Jump to dialogue"
                                >
                                  {formatSeconds(seg.start_time)} - {formatSeconds(seg.end_time)}
                                </button>
                                {seg.is_corrected && (
                                  <Badge variant="purple" size="sm" className="text-[9px] py-0 px-1">
                                    Edited
                                  </Badge>
                                )}
                              </div>

                              <div className="flex items-center gap-1">
                                {!isEditing && (
                                  <button
                                    onClick={() => handleStartEdit(seg)}
                                    className="p-1 text-text-muted hover:text-text-primary rounded transition"
                                    title="Edit transcript text (non-destructive correction)"
                                  >
                                    <Edit2 className="w-3 h-3" />
                                  </button>
                                )}
                                {seg.is_corrected && !isEditing && (
                                  <button
                                    onClick={() => handleRevertCorrection(seg)}
                                    className="p-1 text-text-muted hover:text-amber-400 rounded transition"
                                    title="Revert to original Whisper ASR text"
                                  >
                                    <Undo2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            </div>

                            {isEditing ? (
                              <div className="space-y-1.5 mt-1">
                                <textarea
                                  value={editingText}
                                  onChange={(e) => setEditingText(e.target.value)}
                                  rows={2}
                                  className="w-full bg-canvas border border-brand/50 rounded p-1.5 text-xs text-text-primary focus:outline-none"
                                />
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button size="sm" variant="ghost" onClick={handleCancelEdit} disabled={isSavingCorrection}>
                                    Cancel
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="primary"
                                    onClick={() => handleSaveCorrection(seg)}
                                    disabled={isSavingCorrection}
                                    className="gap-1"
                                  >
                                    <Check className="w-3 h-3" /> Save Correction
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <p
                                onClick={() => handleSeek(seg.start_time)}
                                className="text-text-primary leading-relaxed cursor-pointer"
                              >
                                {seg.corrected_text || seg.text}
                              </p>
                            )}

                            {seg.is_corrected && !isEditing && (
                              <p className="text-[10px] text-text-muted mt-1 italic truncate">
                                Original: "{seg.text}"
                              </p>
                            )}
                          </div>
                        );
                      })
                  ) : (
                    <div className="h-48 flex flex-col items-center justify-center text-text-muted text-xs text-center p-4">
                      <FileText className="w-8 h-8 mb-2 opacity-40" />
                      <p>No speech transcript available.</p>
                      <p className="text-[11px] mt-1 text-text-muted">
                        Run video analysis to perform speech recognition via Faster-Whisper.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Detected Scenes with Real Thumbnails & Lightbox (ZEZ-026, ZEZ-027) */}
            {activeTab === 'scenes' && (
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {scenes.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {scenes.map((sc) => {
                      const isCurrent = currentTime >= sc.start_time && currentTime <= sc.end_time;
                      const thumbUrl = getSceneThumbnailUrl(projectId, mediaAsset.id, sc.id);
                      return (
                        <div
                          key={sc.id}
                          className={`rounded-lg border p-2 text-xs flex flex-col gap-1.5 transition ${
                            isCurrent
                              ? 'border-brand bg-brand/10 font-medium'
                              : 'border-border/60 hover:bg-surface-hover bg-canvas'
                          }`}
                        >
                          <div className="relative aspect-video bg-black rounded overflow-hidden group">
                            <img
                              src={thumbUrl}
                              alt={`Scene ${sc.scene_index + 1}`}
                              className="w-full h-full object-cover cursor-pointer"
                              onClick={() => handleSeek(sc.representative_timestamp)}
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).style.display = 'none';
                              }}
                            />
                            <button
                              onClick={() => setLightboxScene(sc)}
                              className="absolute top-1 right-1 p-1 bg-black/60 hover:bg-black/80 text-white rounded opacity-0 group-hover:opacity-100 transition"
                              title="View full keyframe"
                            >
                              <Maximize2 className="w-3 h-3" />
                            </button>
                            <span className="absolute bottom-1 right-1 px-1 py-0.5 bg-black/70 text-[9px] font-mono text-white rounded">
                              {(sc.end_time - sc.start_time).toFixed(1)}s
                            </span>
                          </div>

                          <div className="flex items-center justify-between">
                            <span
                              onClick={() => handleSeek(sc.representative_timestamp)}
                              className="font-medium text-text-primary cursor-pointer hover:text-brand"
                            >
                              Scene {sc.scene_index + 1}
                            </span>
                            <span className="font-mono text-[10px] text-text-muted">
                              {formatSeconds(sc.start_time)} → {formatSeconds(sc.end_time)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center text-text-muted text-xs text-center p-4">
                    <Layers className="w-8 h-8 mb-2 opacity-40" />
                    <p>No visual scenes detected.</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Visual Observations from Ollama (ZEZ-031) */}
            {activeTab === 'vision' && (
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {observations.length > 0 ? (
                  observations.map((obs) => (
                    <div
                      key={obs.id}
                      onClick={() => handleSeek(obs.timestamp)}
                      className="p-2.5 rounded-lg border border-border/60 hover:bg-surface-hover text-xs cursor-pointer transition bg-canvas"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant="info" size="sm" className="text-[10px] uppercase">
                          {obs.category.replace('_', ' ')}
                        </Badge>
                        <span className="font-mono text-[10px] text-text-muted">
                          {formatSeconds(obs.timestamp)}
                        </span>
                      </div>
                      <p className="text-text-primary leading-relaxed">{obs.description}</p>
                      <div className="mt-1 flex items-center justify-between text-[10px] text-text-muted">
                        <span>Provider: {obs.provider_model}</span>
                        <span>Confidence: {(obs.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center text-text-muted text-xs text-center p-4">
                    <Eye className="w-8 h-8 mb-2 opacity-40" />
                    <p>No visual observations recorded.</p>
                    <p className="text-[11px] mt-1 text-text-muted">
                      Local Ollama (qwen3-vl:4b-instruct) will analyze sampled keyframes during analysis.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Audio Analysis Metadata & Silence Intervals (ZEZ-021) */}
            {activeTab === 'audio' && (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                {audioAnalysis ? (
                  <div className="space-y-3">
                    <div className="p-3 bg-canvas border border-border rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-text-primary">Audio Stream Status</span>
                        <Badge variant={audioAnalysis.has_audio ? 'success' : 'default'} size="sm">
                          {audioAnalysis.has_audio ? 'Audio Detected' : 'No Audio Track'}
                        </Badge>
                      </div>
                      {audioAnalysis.has_audio ? (
                        <div className="grid grid-cols-2 gap-2 text-text-secondary text-[11px] pt-1">
                          <div>Codec: <span className="font-mono text-text-primary">{audioAnalysis.codec_name || 'N/A'}</span></div>
                          <div>Sample Rate: <span className="font-mono text-text-primary">{audioAnalysis.sample_rate || 16000} Hz</span></div>
                          <div>Channels: <span className="font-mono text-text-primary">{audioAnalysis.channels || 1}</span></div>
                          <div>Speech Density: <span className="font-mono text-brand font-semibold">{(audioAnalysis.speech_density * 100).toFixed(1)}%</span></div>
                        </div>
                      ) : (
                        <p className="text-text-muted text-[11px]">
                          Synthesized silent 16kHz mono track to allow analysis pipeline to complete safely.
                        </p>
                      )}
                    </div>

                    {audioAnalysis.silence_intervals && audioAnalysis.silence_intervals.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="font-medium text-text-muted block text-[11px]">
                          Detected Silence Periods ({audioAnalysis.silence_intervals.length})
                        </span>
                        <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                          {audioAnalysis.silence_intervals.map((inv, idx) => (
                            <div
                              key={idx}
                              onClick={() => handleSeek(inv.start)}
                              className="p-1.5 bg-canvas border border-border/60 hover:bg-surface-hover rounded flex items-center justify-between cursor-pointer"
                            >
                              <span className="font-mono text-[10px] text-text-muted">
                                {formatSeconds(inv.start)} → {formatSeconds(inv.end)}
                              </span>
                              <span className="text-[10px] text-text-secondary font-mono">
                                {inv.duration.toFixed(2)}s silence
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center text-text-muted text-xs text-center p-4">
                    <Volume2 className="w-8 h-8 mb-2 opacity-40" />
                    <p>No audio analysis record found for this run.</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 5: Temporal Context Inspector (ZEZ-032) */}
            {activeTab === 'context' && (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="font-medium text-text-primary">Playhead Timestamp</span>
                  <span className="font-mono text-brand font-bold">{formatSeconds(currentTime)}</span>
                </div>

                {temporalContext?.current_scene && (
                  <div className="p-2.5 bg-canvas border border-border rounded-lg">
                    <span className="font-semibold text-xs text-brand block mb-1">Active Visual Scene</span>
                    <p className="text-text-primary">
                      Scene {temporalContext.current_scene.scene_index + 1} ({formatSeconds(temporalContext.current_scene.start_time)} - {formatSeconds(temporalContext.current_scene.end_time)})
                    </p>
                  </div>
                )}

                {temporalContext?.active_speech_turn ? (
                  <div className="p-2.5 bg-canvas border border-border rounded-lg">
                    <span className="font-semibold text-xs text-brand block mb-1">
                      Active Dialogue: {temporalContext.active_speech_turn.speaker_label}
                    </span>
                    <p className="italic text-text-primary">"{temporalContext.active_speech_turn.text}"</p>
                  </div>
                ) : (
                  <div className="p-2 bg-canvas border border-dashed border-border rounded-lg text-text-muted">
                    No speech detected at this exact second.
                  </div>
                )}

                {temporalContext?.nearby_visual_observations && temporalContext.nearby_visual_observations.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-medium text-xs text-text-muted block">Nearby Observations</span>
                    {temporalContext.nearby_visual_observations.map((obs) => (
                      <div key={obs.id} className="p-2 bg-canvas border border-border rounded-lg">
                        <div className="flex justify-between text-[10px] text-text-muted">
                          <span className="font-medium text-text-primary">{obs.category}</span>
                          <span>{formatSeconds(obs.timestamp)}</span>
                        </div>
                        <p className="mt-0.5 text-text-secondary">{obs.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Lightbox Scene Thumbnail Modal (ZEZ-027) */}
      {lightboxScene && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-xs"
          onClick={() => setLightboxScene(null)}
        >
          <div
            className="max-w-3xl w-full bg-surface border border-border rounded-xl p-4 space-y-3 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-text-primary">
                Scene {lightboxScene.scene_index + 1} Keyframe ({formatSeconds(lightboxScene.start_time)} - {formatSeconds(lightboxScene.end_time)})
              </span>
              <button
                onClick={() => setLightboxScene(null)}
                className="p-1 hover:bg-surface-hover rounded text-text-muted hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center">
              <img
                src={getSceneThumbnailUrl(projectId, mediaAsset.id, lightboxScene.id)}
                alt={`Scene ${lightboxScene.scene_index + 1}`}
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex items-center justify-between text-xs text-text-muted">
              <span>Representative timestamp: {formatSeconds(lightboxScene.representative_timestamp)}</span>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  handleSeek(lightboxScene.representative_timestamp);
                  setLightboxScene(null);
                }}
              >
                Jump to Scene
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
