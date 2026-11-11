import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  CheckCircle,
  Download,
  History,
  Maximize2,
  Pause,
  Play,
  RefreshCw,
  Sliders,
  Video,
  X,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import {
  analyzeReframing,
  fetchCropPreview,
  fetchReframingRevisions,
  getProxyUrl,
  getRenderedVideoUrl,
  renderReframingRevision,
  restoreReframingRevision,
  saveCropOverrides,
} from '../../services/apiClient';
import { MediaAssetItem } from '../../types/projects';
import {
  CropPreviewData,
  DetectedSubjectItem,
  ReframingPlanItem,
  ReframingRevisionItem,
} from '../../types/reframing';

interface ReframingWorkspaceProps {
  projectId: string;
  mediaAsset: MediaAssetItem;
  candidateId?: string;
  onBack: () => void;
}

export const ReframingWorkspace: React.FC<ReframingWorkspaceProps> = ({
  projectId,
  mediaAsset,
  candidateId,
  onBack,
}) => {
  const [plan, setPlan] = useState<ReframingPlanItem | null>(null);
  const [revisions, setRevisions] = useState<ReframingRevisionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [rendering, setRendering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Video playback & timeline state
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);

  // Interactive crop manual adjustments
  const [currentCrop, setCurrentCrop] = useState<CropPreviewData | null>(null);
  const [manualX, setManualX] = useState<number>(0);
  const [manualY, setManualY] = useState<number>(0);
  const [manualZoom, setManualZoom] = useState<number>(1.0);
  const [manualHeadroom, setManualHeadroom] = useState<number>(0.15);
  const [dirtyOverride, setDirtyOverride] = useState<boolean>(false);
  const [stagedOverrides, setStagedOverrides] = useState<
    Array<{
      timestamp: number;
      crop_x?: number;
      crop_y?: number;
      zoom?: number;
      headroom?: number;
    }>
  >([]);

  // Revision history drawer
  const [showRevisionsModal, setShowRevisionsModal] = useState<boolean>(false);
  const [newRevisionLabel, setNewRevisionLabel] = useState<string>('');

  // Target aspect ratio
  const [targetAspect, setTargetAspect] = useState<string>('9:16');
  const [framingStrategy, setFramingStrategy] = useState<string>('auto');

  // Video source URL
  const videoSrc = getProxyUrl(projectId, mediaAsset.id);

  // Initialize or fetch existing reframing plan
  const loadPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Analyze or create plan
      const newPlan = await analyzeReframing(projectId, mediaAsset.id, {
        candidate_id: candidateId,
        target_aspect_ratio: targetAspect,
        framing_strategy: framingStrategy,
        base_zoom: manualZoom,
        headroom_factor: manualHeadroom,
      });
      setPlan(newPlan);
      setCurrentTime(newPlan.start_time);
      setDuration(newPlan.duration);

      // Load revision history
      const revs = await fetchReframingRevisions(projectId, newPlan.id);
      setRevisions(revs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze reframing.');
    } finally {
      setLoading(false);
    }
  }, [projectId, mediaAsset.id, candidateId, targetAspect, framingStrategy, manualZoom, manualHeadroom]);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  // Update current crop preview when playback scrubs
  const updateCropPreview = useCallback(
    async (time: number) => {
      if (!plan) return;
      try {
        const preview = await fetchCropPreview(projectId, plan.id, time);
        setCurrentCrop(preview);
        if (!dirtyOverride) {
          setManualX(preview.crop_x);
          setManualY(preview.crop_y);
          setManualZoom(preview.zoom);
        }
      } catch {
        // quiet error on fast scrubbing
      }
    },
    [projectId, plan, dirtyOverride]
  );

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const t = videoRef.current.currentTime;
      setCurrentTime(t);
      void updateCropPreview(t);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
      void updateCropPreview(time);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      void videoRef.current.play();
      setIsPlaying(true);
    }
  };

  // Set manual keyframe override at current timestamp
  const handleSetKeyframe = () => {
    if (!plan) return;
    const newOverride = {
      timestamp: roundDec(currentTime, 2),
      crop_x: Math.round(manualX),
      crop_y: Math.round(manualY),
      zoom: roundDec(manualZoom, 2),
      headroom: roundDec(manualHeadroom, 2),
    };

    setStagedOverrides((prev) => {
      const filtered = prev.filter((o) => Math.abs(o.timestamp - newOverride.timestamp) > 0.1);
      return [...filtered, newOverride].sort((a, b) => a.timestamp - b.timestamp);
    });
    setDirtyOverride(true);
    setSuccessMsg(`Set keyframe at ${newOverride.timestamp.toFixed(2)}s`);
    setTimeout(() => setSuccessMsg(null), 2500);
  };

  // Save manual adjustments as a new immutable revision
  const handleSaveRevision = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const updated = await saveCropOverrides(
        projectId,
        plan.id,
        stagedOverrides,
        newRevisionLabel || undefined
      );
      setPlan(updated);
      setStagedOverrides([]);
      setDirtyOverride(false);
      setNewRevisionLabel('');

      const revs = await fetchReframingRevisions(projectId, plan.id);
      setRevisions(revs);
      setSuccessMsg('Successfully created new framing revision!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save revision.');
    } finally {
      setLoading(false);
    }
  };

  // Restore a prior revision
  const handleRestoreRevision = async (revId: string) => {
    if (!plan) return;
    setLoading(true);
    try {
      const restored = await restoreReframingRevision(projectId, plan.id, revId);
      setPlan(restored);
      setShowRevisionsModal(false);
      const revs = await fetchReframingRevisions(projectId, plan.id);
      setRevisions(revs);
      setSuccessMsg('Restored revision.');
      setTimeout(() => setSuccessMsg(null), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore revision.');
    } finally {
      setLoading(false);
    }
  };

  // Render video via FFmpeg
  const handleRenderVideo = async () => {
    if (!plan) return;
    setRendering(true);
    setError(null);
    try {
      await renderReframingRevision(projectId, plan.id, plan.active_revision_id || undefined);
      const revs = await fetchReframingRevisions(projectId, plan.id);
      setRevisions(revs);
      setSuccessMsg('Render complete! Vertical video is ready.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Render failed.');
    } finally {
      setRendering(false);
    }
  };

  const roundDec = (val: number, dec = 2) => {
    const factor = Math.pow(10, dec);
    return Math.round(val * factor) / factor;
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  // Calculate overlay box style for source landscape player
  const overlayStyle = useMemo(() => {
    if (!plan || !currentCrop) return null;
    const srcW = plan.source_width || 1920;
    const srcH = plan.source_height || 1080;

    const leftPct = (manualX / srcW) * 100;
    const topPct = (manualY / srcH) * 100;
    const widthPct = (currentCrop.crop_w / srcW) * 100;
    const heightPct = (currentCrop.crop_h / srcH) * 100;

    return {
      left: `${leftPct}%`,
      top: `${topPct}%`,
      width: `${widthPct}%`,
      height: `${heightPct}%`,
    };
  }, [plan, currentCrop, manualX, manualY]);

  // Find active subject detections near current timestamp
  const activeDetections = useMemo(() => {
    if (!plan || !plan.detected_tracks) return [];
    const res: DetectedSubjectItem[] = [];
    for (const trk of plan.detected_tracks) {
      const match = trk.detections.find((d) => Math.abs(d.timestamp - currentTime) <= 0.3);
      if (match) res.push(match);
    }
    return res;
  }, [plan, currentTime]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Top Header */}
      <div className="border-b border-border bg-surface px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} aria-label="Back">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Camera className="w-5 h-5 text-brand" />
              <h1 className="text-sm font-semibold text-text-primary">
                Smart Reframing & Subject Tracking Studio
              </h1>
              <Badge variant="purple">M7 Engine</Badge>
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Subject-aware vertical 9:16 composition with mathematical preview/renderer parity.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Aspect Ratio Selector */}
          <div className="flex items-center bg-surface-card border border-border rounded-lg p-0.5 text-xs">
            {['9:16', '1:1', '16:9'].map((ar) => (
              <button
                key={ar}
                onClick={() => setTargetAspect(ar)}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  targetAspect === ar
                    ? 'bg-brand text-white'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                {ar}
              </button>
            ))}
          </div>

          {/* Strategy Selector */}
          <select
            value={framingStrategy}
            onChange={(e) => setFramingStrategy(e.target.value)}
            className="text-xs bg-surface-card border border-border rounded-lg px-2.5 py-1 text-text-primary focus:outline-none"
          >
            <option value="auto">Auto Strategy</option>
            <option value="single_subject">Single Subject</option>
            <option value="two_person">Two People</option>
            <option value="group">Group</option>
          </select>

          {/* Revisions History Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowRevisionsModal(true)}
            title="View revision history"
          >
            <History className="w-3.5 h-3.5 mr-1.5" />
            Revisions ({revisions.length})
          </Button>

          {/* Render Action Button */}
          <Button
            variant="primary"
            size="sm"
            onClick={handleRenderVideo}
            disabled={rendering || loading}
            title="Render real 9:16 vertical video via FFmpeg"
          >
            {rendering ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Rendering...
              </>
            ) : (
              <>
                <Video className="w-3.5 h-3.5 mr-1.5" /> Render Video
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mx-6 mt-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="mx-6 mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Split Viewports */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-6 overflow-y-auto min-h-0">
        {/* Left Viewport (7 Cols): Source Landscape Viewport with Overlays */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          <Card className="flex-1 flex flex-col justify-between overflow-hidden bg-black/95 p-0 border-border relative">
            <div className="relative flex-1 flex items-center justify-center bg-black min-h-[360px]">
              <video
                ref={videoRef}
                src={videoSrc}
                className="w-full h-full max-h-[460px] object-contain"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={() => {
                  if (videoRef.current) setDuration(videoRef.current.duration);
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />

              {/* Crop Window Overlay Box */}
              {overlayStyle && (
                <div
                  style={overlayStyle}
                  className="absolute border-2 border-emerald-400 bg-emerald-500/15 pointer-events-none transition-all duration-75 shadow-lg flex items-start justify-between p-1.5"
                >
                  <span className="text-[10px] font-mono font-bold bg-emerald-500 text-black px-1 rounded shadow-xs">
                    {targetAspect} Portrait
                  </span>
                  <span className="text-[10px] font-mono text-emerald-300 bg-black/70 px-1 rounded">
                    Zoom: {manualZoom.toFixed(2)}x
                  </span>
                </div>
              )}

              {/* Detected Subjects Bounding Boxes */}
              {plan &&
                activeDetections.map((det, i) => {
                  const srcW = plan.source_width || 1920;
                  const srcH = plan.source_height || 1080;
                  const left = `${(det.box_x / srcW) * 100}%`;
                  const top = `${(det.box_y / srcH) * 100}%`;
                  const width = `${(det.box_w / srcW) * 100}%`;
                  const height = `${(det.box_h / srcH) * 100}%`;

                  return (
                    <div
                      key={i}
                      style={{ left, top, width, height }}
                      className="absolute border border-cyan-400/80 bg-cyan-500/10 pointer-events-none rounded"
                    >
                      <span className="text-[9px] font-mono bg-cyan-600 text-white px-1 absolute -top-4 left-0 rounded shadow-xs">
                        {det.subject_id || det.category} ({Math.round(det.confidence * 100)}%)
                      </span>
                    </div>
                  );
                })}
            </div>

            {/* Playback & Scrubber Controls */}
            <div className="bg-surface/90 border-t border-border p-3 flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="p-1.5 rounded-lg bg-surface-card hover:bg-surface-hover text-text-primary"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <span className="text-xs font-mono text-text-muted">
                  {formatSeconds(currentTime)} / {formatSeconds(duration)}
                </span>
                <input
                  type="range"
                  min="0"
                  max={duration || 10}
                  step="0.05"
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  className="flex-1 accent-brand cursor-pointer"
                />
              </div>

              {/* Scene Cut & Keyframe timeline markers */}
              <div className="flex items-center justify-between text-[10px] text-text-muted font-mono px-1">
                <span>Strategy: {plan?.framing_strategy || 'single_subject'}</span>
                <span>Active Tracked Subjects: {activeDetections.length}</span>
                <span>Scene Cuts: {plan?.scene_cuts?.length ?? 0}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Viewport (5 Cols): True Portrait 9:16 Preview & Manual Controls */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Portrait Composition Preview Window */}
          <Card className="flex flex-col items-center justify-center p-4 bg-surface border-border">
            <div className="flex items-center justify-between w-full mb-2">
              <span className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                <Maximize2 className="w-3.5 h-3.5 text-brand" /> Portrait Viewport ({targetAspect})
              </span>
              <Badge variant="purple">Authoritative Math</Badge>
            </div>

            {/* 9:16 Box simulating rendered video output */}
            <div className="relative w-[216px] h-[384px] bg-black rounded-xl overflow-hidden border-2 border-emerald-500/50 shadow-2xl flex items-center justify-center">
              {currentCrop && (
                <div
                  className="relative overflow-hidden w-full h-full"
                  style={{
                    backgroundColor: '#050505',
                  }}
                >
                  {/* Cropped video view positioned according to exact crop coordinates */}
                  <div
                    style={{
                      position: 'absolute',
                      left: `-${(manualX / (currentCrop.crop_w || 1)) * 100}%`,
                      top: `-${(manualY / (currentCrop.crop_h || 1)) * 100}%`,
                      width: `${((plan?.source_width || 1920) / (currentCrop.crop_w || 608)) * 100}%`,
                      height: `${((plan?.source_height || 1080) / (currentCrop.crop_h || 1080)) * 100}%`,
                    }}
                  >
                    <video
                      src={videoSrc}
                      className="w-full h-full object-cover pointer-events-none"
                    />
                  </div>

                  {/* Corner indicator */}
                  <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-0.5 rounded text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                    {Math.round(manualX)}, {Math.round(manualY)}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Manual Adjustments & Keyframe Insertion Card */}
          <Card className="p-4 bg-surface border-border space-y-3">
            <h3 className="text-xs font-semibold text-text-primary flex items-center gap-1.5 uppercase tracking-wider">
              <Sliders className="w-3.5 h-3.5 text-brand" /> Manual Crop & Headroom Fine-Tuning
            </h3>

            {/* Horizontal Position */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-text-muted">Horizontal Crop (X)</span>
                <span className="font-mono font-bold text-brand">{Math.round(manualX)}px</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setManualX((v) => Math.max(0, v - 20));
                    setDirtyOverride(true);
                  }}
                  className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary"
                >
                  -20px
                </button>
                <input
                  type="range"
                  min="0"
                  max={(plan?.source_width || 1920) - (currentCrop?.crop_w || 600)}
                  value={manualX}
                  onChange={(e) => {
                    setManualX(parseFloat(e.target.value));
                    setDirtyOverride(true);
                  }}
                  className="flex-1 accent-brand cursor-pointer"
                />
                <button
                  onClick={() => {
                    setManualX((v) =>
                      Math.min((plan?.source_width || 1920) - (currentCrop?.crop_w || 600), v + 20)
                    );
                    setDirtyOverride(true);
                  }}
                  className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary"
                >
                  +20px
                </button>
              </div>
            </div>

            {/* Zoom Slider */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-text-muted">Framing Zoom</span>
                <span className="font-mono font-bold text-brand">{manualZoom.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="2.5"
                step="0.05"
                value={manualZoom}
                onChange={(e) => {
                  setManualZoom(parseFloat(e.target.value));
                  setDirtyOverride(true);
                }}
                className="w-full accent-brand cursor-pointer"
              />
            </div>

            {/* Headroom Adjustment */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-text-muted">Headroom Margin</span>
                <span className="font-mono font-bold text-brand">{Math.round(manualHeadroom * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.35"
                step="0.01"
                value={manualHeadroom}
                onChange={(e) => {
                  setManualHeadroom(parseFloat(e.target.value));
                  setDirtyOverride(true);
                }}
                className="w-full accent-brand cursor-pointer"
              />
            </div>

            {/* Keyframe Staging Buttons */}
            <div className="pt-2 flex items-center justify-between gap-2 border-t border-border">
              <Button size="sm" variant="outline" onClick={handleSetKeyframe}>
                Set Keyframe ({formatSeconds(currentTime)})
              </Button>

              {dirtyOverride && (
                <Button size="sm" variant="primary" onClick={handleSaveRevision}>
                  Save Revision ({stagedOverrides.length})
                </Button>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Revision History Modal */}
      {showRevisionsModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between bg-surface-card">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <History className="w-4 h-4 text-brand" /> Framing Revisions Ledger
              </h3>
              <button
                onClick={() => setShowRevisionsModal(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {revisions.map((rev) => {
                const isActive = rev.id === plan?.active_revision_id;
                return (
                  <div
                    key={rev.id}
                    className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 ${
                      isActive
                        ? 'border-brand bg-brand/10'
                        : 'border-border bg-surface-card hover:border-border-hover'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-text-primary">
                          Revision {rev.revision_number}: {rev.label}
                        </span>
                        {rev.is_ai_generated && <Badge variant="default">AI Generated</Badge>}
                        {isActive && <Badge variant="success">Active</Badge>}
                      </div>
                      <div className="text-[11px] text-text-muted mt-1 font-mono">
                        Overrides: {rev.manual_overrides?.length ?? 0} • Created:{' '}
                        {new Date(rev.created_at).toLocaleTimeString()}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {!isActive && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestoreRevision(rev.id)}
                        >
                          Restore
                        </Button>
                      )}

                      {rev.rendered_video_path && (
                        <a
                          href={getRenderedVideoUrl(projectId, plan!.id, rev.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1 text-xs rounded bg-surface border border-border text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                        >
                          <Download className="w-3.5 h-3.5" /> Video
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-3 border-t border-border bg-surface-card flex justify-end">
              <Button size="sm" variant="secondary" onClick={() => setShowRevisionsModal(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
