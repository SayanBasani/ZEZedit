import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Eye,
  FileText,
  Film,
  Layers,
  Loader2,
  MessageSquare,
  Pause,
  Play,
  RotateCcw,
  Search,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import {
  cancelAnalysisRun,
  fetchAnalysisContext,
  fetchAnalysisRuns,
  fetchAnalysisScenes,
  fetchAnalysisTranscript,
  fetchAnalysisObservations,
  getProxyUrl,
  getThumbnailUrl,
  startMediaAnalysis,
} from '../../services/apiClient';
import {
  AnalysisRunItem,
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
}

export const AnalysisWorkspace: React.FC<AnalysisWorkspaceProps> = ({
  projectId,
  mediaAsset,
  onBack,
}) => {
  const [runs, setRuns] = useState<AnalysisRunItem[]>([]);
  const [selectedRun, setSelectedRun] = useState<AnalysisRunItem | null>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'scenes' | 'vision' | 'context'>('transcript');
  const [profile, setProfile] = useState<'fast' | 'balanced' | 'detailed'>('balanced');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Analysis Data
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegmentItem[]>([]);
  const [speechTurns, setSpeechTurns] = useState<SpeechTurnItem[]>([]);
  const [scenes, setScenes] = useState<VideoSceneItem[]>([]);
  const [observations, setObservations] = useState<VisualObservationItem[]>([]);
  const [temporalContext, setTemporalContext] = useState<TemporalContextPayload | null>(null);

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
        // ignore polling error
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [projectId, mediaAsset.id, selectedRun]);

  // Load run details
  const loadRunDetails = useCallback(async (runId: string) => {
    try {
      const [tData, sData, oData] = await Promise.all([
        fetchAnalysisTranscript(projectId, mediaAsset.id, runId),
        fetchAnalysisScenes(projectId, mediaAsset.id, runId),
        fetchAnalysisObservations(projectId, mediaAsset.id, runId),
      ]);
      setTranscriptSegments(tData.segments);
      setSpeechTurns(tData.speech_turns);
      setScenes(sData);
      setObservations(oData);
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
      const newRun = await startMediaAnalysis(projectId, mediaAsset.id, profile);
      setRuns([newRun, ...runs]);
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

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  // Video source preference: proxy if available, else original
  const videoSrc = getProxyUrl(projectId, mediaAsset.id);

  if (loading && runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] text-muted-foreground gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm">Loading analysis workspace...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] space-y-4 p-4 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} aria-label="Back to Media Library">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Film className="w-5 h-5 text-primary" />
              {mediaAsset.original_filename}
            </h1>
            <p className="text-xs text-muted-foreground">
              {mediaAsset.width && mediaAsset.height ? `${mediaAsset.width}×${mediaAsset.height}` : 'Unknown'} •{' '}
              {mediaAsset.fps ? `${mediaAsset.fps.toFixed(1)} fps` : 'Unknown fps'} •{' '}
              {formatSeconds(duration)}
            </p>
          </div>
        </div>

        {/* Analysis controls */}
        <div className="flex items-center gap-2">
          {selectedRun && (selectedRun.status === 'running' || selectedRun.status === 'pending') ? (
            <div className="flex items-center gap-3 bg-muted/60 px-3 py-1.5 rounded-lg border border-border">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <div className="flex flex-col">
                <span className="text-xs font-medium capitalize">
                  {selectedRun.current_stage?.replace('_', ' ') || 'Processing...'}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {selectedRun.progress_pct.toFixed(0)}% completed
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleCancelRun} className="text-destructive h-7 px-2">
                <XCircle className="w-3.5 h-3.5 mr-1" /> Cancel
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value as 'fast' | 'balanced' | 'detailed')}
                className="bg-background border border-border rounded-lg text-xs px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="fast">Fast (Quick scan, fewer frames)</option>
                <option value="balanced">Balanced (Whisper + scenes + vision)</option>
                <option value="detailed">Detailed (Dense keyframe inspection)</option>
              </select>
              <Button onClick={handleStartAnalysis} size="sm" className="gap-1.5">
                <Sparkles className="w-4 h-4" /> Start Analysis
              </Button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-destructive/15 border border-destructive text-destructive text-sm p-3 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Video Player on Left, Multimodal Analysis on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        {/* Left Column: Player & Timeline */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          <Card className="flex-1 flex flex-col justify-between overflow-hidden bg-black/90 p-0 border-border">
            <div className="relative flex-1 flex items-center justify-center bg-black min-h-[320px]">
              <video
                ref={videoRef}
                src={videoSrc}
                poster={getThumbnailUrl(projectId, mediaAsset.id)}
                className="w-full h-full max-h-[460px] object-contain"
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
            </div>

            {/* Custom Video Controls Bar */}
            <div className="p-3 bg-card/95 border-t border-border flex flex-col space-y-2">
              {/* Scrub bar */}
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-muted-foreground w-14">
                  {formatSeconds(currentTime)}
                </span>
                <input
                  type="range"
                  min="0"
                  max={duration || 100}
                  step="0.05"
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  className="flex-1 h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                />
                <span className="text-[11px] font-mono text-muted-foreground w-14 text-right">
                  {formatSeconds(duration)}
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Button variant="ghost" size="sm" onClick={() => handleSeek(0)} aria-label="Restart Video">
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={togglePlay} aria-label={isPlaying ? 'Pause' : 'Play'}>
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </Button>
                </div>
                {selectedRun && (
                  <Badge variant={selectedRun.status === 'completed' ? 'success' : 'default'} className="text-[11px]">
                    {selectedRun.profile} profile • {selectedRun.status}
                  </Badge>
                )}
              </div>
            </div>
          </Card>

          {/* Quick Scene Markers Bar */}
          {scenes.length > 0 && (
            <Card className="p-3">
              <span className="text-xs font-semibold text-muted-foreground mb-2 block flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" /> Visual Scene Cuts ({scenes.length})
              </span>
              <div className="flex gap-1.5 overflow-x-auto pb-1">
                {scenes.map((sc) => {
                  const isCurrent = currentTime >= sc.start_time && currentTime <= sc.end_time;
                  return (
                    <button
                      key={sc.id}
                      onClick={() => handleSeek(sc.representative_timestamp)}
                      className={`flex-shrink-0 text-left px-2.5 py-1.5 rounded-lg border text-xs transition-colors ${
                        isCurrent
                          ? 'border-primary bg-primary/10 text-primary font-medium'
                          : 'border-border bg-muted/40 hover:bg-muted text-muted-foreground'
                      }`}
                    >
                      <div className="font-semibold">Scene {sc.scene_index + 1}</div>
                      <div className="text-[10px] font-mono">
                        {formatSeconds(sc.start_time)} - {formatSeconds(sc.end_time)}
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Multimodal Tabs (Transcript, Scenes, Vision, Context) */}
        <div className="lg:col-span-5 flex flex-col space-y-3 min-h-0">
          <div className="flex border-b border-border bg-card rounded-t-lg px-2">
            <button
              onClick={() => setActiveTab('transcript')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'transcript'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <FileText className="w-3.5 h-3.5" /> Transcript ({transcriptSegments.length})
            </button>
            <button
              onClick={() => setActiveTab('scenes')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'scenes'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Layers className="w-3.5 h-3.5" /> Scenes ({scenes.length})
            </button>
            <button
              onClick={() => setActiveTab('vision')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'vision'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Eye className="w-3.5 h-3.5" /> Visuals ({observations.length})
            </button>
            <button
              onClick={() => {
                setActiveTab('context');
                queryContext(currentTime);
              }}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'context'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Activity className="w-3.5 h-3.5" /> Context
            </button>
          </div>

          <Card className="flex-1 overflow-hidden p-3 flex flex-col min-h-0">
            {/* Tab 1: Transcript & Speech Turns */}
            {activeTab === 'transcript' && (
              <div className="flex flex-col h-full space-y-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search spoken dialogue..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="w-full bg-muted/40 border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                  {speechTurns.length > 0 ? (
                    speechTurns
                      .filter((t) => !searchFilter || t.text.toLowerCase().includes(searchFilter.toLowerCase()))
                      .map((turn) => {
                        const isSpeaking = currentTime >= turn.start_time && currentTime <= turn.end_time;
                        return (
                          <div
                            key={turn.id}
                            onClick={() => handleSeek(turn.start_time)}
                            className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                              isSpeaking
                                ? 'border-primary bg-primary/10 shadow-sm'
                                : 'border-border/60 hover:bg-muted/40'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-primary flex items-center gap-1">
                                <MessageSquare className="w-3 h-3" /> {turn.speaker_label}
                              </span>
                              <span className="text-[10px] font-mono text-muted-foreground">
                                {formatSeconds(turn.start_time)} - {formatSeconds(turn.end_time)}
                              </span>
                            </div>
                            <p className="text-foreground leading-relaxed">{turn.text}</p>
                            <div className="mt-1 flex items-center gap-1">
                              <Badge variant="default" className="text-[9px] py-0 px-1">
                                {turn.turn_type}
                              </Badge>
                            </div>
                          </div>
                        );
                      })
                  ) : (
                    <div className="h-48 flex flex-col items-center justify-center text-muted-foreground text-xs text-center p-4">
                      <FileText className="w-8 h-8 mb-2 opacity-40" />
                      <p>No speech transcript available for this asset.</p>
                      <p className="text-[11px] mt-1 text-muted-foreground/80">
                        Run video analysis to perform speech recognition via Faster-Whisper.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Detected Scenes List */}
            {activeTab === 'scenes' && (
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {scenes.length > 0 ? (
                  scenes.map((sc) => {
                    const isCurrent = currentTime >= sc.start_time && currentTime <= sc.end_time;
                    return (
                      <div
                        key={sc.id}
                        onClick={() => handleSeek(sc.representative_timestamp)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition-colors ${
                          isCurrent
                            ? 'border-primary bg-primary/10 font-medium'
                            : 'border-border/60 hover:bg-muted/40'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-primary" />
                          <div>
                            <div className="font-semibold">Scene {sc.scene_index + 1}</div>
                            <div className="text-[10px] text-muted-foreground">
                              Duration: {(sc.end_time - sc.start_time).toFixed(1)}s (Cut score: {sc.change_score})
                            </div>
                          </div>
                        </div>
                        <span className="font-mono text-xs text-muted-foreground">
                          {formatSeconds(sc.start_time)} → {formatSeconds(sc.end_time)}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center text-muted-foreground text-xs text-center p-4">
                    <Layers className="w-8 h-8 mb-2 opacity-40" />
                    <p>No visual scenes detected.</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Visual Observations from Ollama / Heuristics */}
            {activeTab === 'vision' && (
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {observations.length > 0 ? (
                  observations.map((obs) => (
                    <div
                      key={obs.id}
                      onClick={() => handleSeek(obs.timestamp)}
                      className="p-2.5 rounded-lg border border-border/60 hover:bg-muted/40 text-xs cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant="info" className="text-[10px] uppercase">
                          {obs.category.replace('_', ' ')}
                        </Badge>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {formatSeconds(obs.timestamp)}
                        </span>
                      </div>
                      <p className="text-foreground leading-relaxed">{obs.description}</p>
                      <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>Model: {obs.provider_model}</span>
                        <span>Confidence: {(obs.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center text-muted-foreground text-xs text-center p-4">
                    <Eye className="w-8 h-8 mb-2 opacity-40" />
                    <p>No visual observations recorded.</p>
                    <p className="text-[11px] mt-1 text-muted-foreground/80">
                      Ollama model (qwen3-vl:4b-instruct) will analyze sampled keyframes during analysis.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Temporal Context Inspector */}
            {activeTab === 'context' && (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="font-semibold text-foreground">Playhead Timestamp</span>
                  <span className="font-mono text-primary font-bold">{formatSeconds(currentTime)}</span>
                </div>

                {temporalContext?.current_scene && (
                  <div className="p-2.5 bg-muted/30 border border-border rounded-lg">
                    <span className="font-semibold text-xs text-primary block mb-1">Active Visual Scene</span>
                    <p>
                      Scene {temporalContext.current_scene.scene_index + 1} ({formatSeconds(temporalContext.current_scene.start_time)} - {formatSeconds(temporalContext.current_scene.end_time)})
                    </p>
                  </div>
                )}

                {temporalContext?.active_speech_turn ? (
                  <div className="p-2.5 bg-muted/30 border border-border rounded-lg">
                    <span className="font-semibold text-xs text-primary block mb-1">
                      Active Dialogue: {temporalContext.active_speech_turn.speaker_label}
                    </span>
                    <p className="italic">"{temporalContext.active_speech_turn.text}"</p>
                  </div>
                ) : (
                  <div className="p-2 bg-muted/20 border border-dashed border-border rounded-lg text-muted-foreground">
                    No speech turn detected at this exact second.
                  </div>
                )}

                {temporalContext?.nearby_visual_observations && temporalContext.nearby_visual_observations.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-xs text-foreground block">Nearby Observations</span>
                    {temporalContext.nearby_visual_observations.map((obs) => (
                      <div key={obs.id} className="p-2 bg-muted/30 border border-border rounded-lg">
                        <div className="flex justify-between text-[10px] text-muted-foreground">
                          <span className="font-semibold text-foreground">{obs.category}</span>
                          <span>{formatSeconds(obs.timestamp)}</span>
                        </div>
                        <p className="mt-0.5">{obs.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
