import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Download,
  History,
  Maximize2,
  Move,
  Pause,
  Play,
  RefreshCw,
  Sliders,
  Sparkles,
  Target,
  Trash2,
  User,
  Users,
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
  CropKeyframeItem,
  CropPreviewData,
  DetectedSubjectItem,
  ReframingPlanItem,
  ReframingRevisionItem,
} from '../../types/reframing';

export interface ReframingWorkspaceProps {
  projectId: string;
  mediaAsset: MediaAssetItem;
  candidateId?: string;
  onBack: () => void;
  isModalView?: boolean;
  onCloseModal?: () => void;
}

export const ReframingWorkspace: React.FC<ReframingWorkspaceProps> = ({
  projectId,
  mediaAsset,
  candidateId,
  onBack,
  isModalView = false,
  onCloseModal,
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

  // On-canvas draggable & resizable crop state (ZEZ-051)
  const videoContainerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingCropRef = useRef<boolean>(false);
  const dragStartPosRef = useRef<{ clientX: number; clientY: number; startX: number; startY: number; startZoom: number }>({
    clientX: 0,
    clientY: 0,
    startX: 0,
    startY: 0,
    startZoom: 1.0,
  });
  const [isDraggingCrop, setIsDraggingCrop] = useState<boolean>(false);
  const [activeHandle, setActiveHandle] = useState<string | null>(null);

  // Revision history drawer
  const [showRevisionsModal, setShowRevisionsModal] = useState<boolean>(false);
  const [newRevisionLabel, setNewRevisionLabel] = useState<string>('');

  // Target aspect ratio & character focus
  const [targetAspect, setTargetAspect] = useState<string>('9:16');
  const [framingStrategy, setFramingStrategy] = useState<string>('auto');
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);

  // Video source URL
  const videoSrc = getProxyUrl(projectId, mediaAsset.id);

  // Initialize or fetch existing reframing plan
  const loadPlan = useCallback(async (pinnedId?: string | null, strategy?: string) => {
    setLoading(true);
    setError(null);
    try {
      const strat = strategy || framingStrategy;
      const pid = pinnedId !== undefined ? pinnedId : selectedCharacterId;
      // Analyze or create plan
      const newPlan = await analyzeReframing(projectId, mediaAsset.id, {
        candidate_id: candidateId,
        target_aspect_ratio: targetAspect,
        framing_strategy: strat,
        base_zoom: manualZoom,
        headroom_factor: manualHeadroom,
        pinned_subject_id: pid || undefined,
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
  }, [projectId, mediaAsset.id, candidateId, targetAspect, framingStrategy, selectedCharacterId, manualZoom, manualHeadroom]);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  // Extract unique detected subjects / characters from tracking results
  const availableCharacters = useMemo(() => {
    if (!plan || !plan.detected_tracks) return [];
    return plan.detected_tracks.map((trk, idx) => ({
      id: trk.track_id || trk.detections[0]?.subject_id || `subj_${idx + 1}`,
      label: `Character ${idx + 1}`,
      count: trk.detections.length,
      category: trk.detections[0]?.category || 'face',
    }));
  }, [plan]);

  // Handle character focus selection
  const handleSelectCharacter = async (charId: string | null, strat: string) => {
    setSelectedCharacterId(charId);
    setFramingStrategy(strat);
    await loadPlan(charId, strat);
    setSuccessMsg(charId ? `Focusing automatically on ${charId} without manual keyframes!` : `Framing set to ${strat}`);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

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

  // On-canvas draggable & resizable crop handlers (ZEZ-051)
  const handleCropPointerDown = (e: React.PointerEvent, handle: string = 'move') => {
    e.preventDefault();
    e.stopPropagation();
    if (!videoContainerRef.current || !plan) return;

    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    isDraggingCropRef.current = true;
    setIsDraggingCrop(true);
    setActiveHandle(handle);

    dragStartPosRef.current = {
      clientX: e.clientX,
      clientY: e.clientY,
      startX: manualX,
      startY: manualY,
      startZoom: manualZoom,
    };
  };

  const handleCropPointerMove = (e: React.PointerEvent) => {
    if (!isDraggingCropRef.current || !videoContainerRef.current || !plan || !currentCrop) return;
    const rect = videoContainerRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const srcW = plan.source_width || 1920;
    const srcH = plan.source_height || 1080;
    const deltaScreenX = e.clientX - dragStartPosRef.current.clientX;
    const deltaScreenY = e.clientY - dragStartPosRef.current.clientY;

    const deltaSrcX = deltaScreenX * (srcW / rect.width);
    const deltaSrcY = deltaScreenY * (srcH / rect.height);

    if (activeHandle === 'move') {
      const maxCropX = Math.max(0, srcW - (currentCrop.crop_w || 608));
      const maxCropY = Math.max(0, srcH - (currentCrop.crop_h || 1080));
      const newX = Math.max(0, Math.min(maxCropX, dragStartPosRef.current.startX + deltaSrcX));
      const newY = Math.max(0, Math.min(maxCropY, dragStartPosRef.current.startY + deltaSrcY));
      setManualX(Math.round(newX));
      setManualY(Math.round(newY));
      setDirtyOverride(true);
    } else if (activeHandle === 'se' || activeHandle === 'e' || activeHandle === 's') {
      const zoomFactor = 1 - (deltaSrcX / srcW) * 0.8;
      const newZoom = Math.max(0.6, Math.min(2.5, dragStartPosRef.current.startZoom * zoomFactor));
      setManualZoom(roundDec(newZoom, 2));
      setDirtyOverride(true);
    } else if (activeHandle === 'nw' || activeHandle === 'w' || activeHandle === 'n') {
      const zoomFactor = 1 + (deltaSrcX / srcW) * 0.8;
      const newZoom = Math.max(0.6, Math.min(2.5, dragStartPosRef.current.startZoom * zoomFactor));
      setManualZoom(roundDec(newZoom, 2));
      setDirtyOverride(true);
    }
  };

  const handleCropPointerUp = (e: React.PointerEvent) => {
    if (!isDraggingCropRef.current) return;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    isDraggingCropRef.current = false;
    setIsDraggingCrop(false);
    setActiveHandle(null);
  };

  const handleCropDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!plan || !currentCrop) return;
    const srcW = plan.source_width || 1920;
    const srcH = plan.source_height || 1080;
    const centerX = Math.max(0, (srcW - currentCrop.crop_w) / 2);
    const centerY = Math.max(0, (srcH - currentCrop.crop_h) / 2);
    setManualX(Math.round(centerX));
    setManualY(Math.round(centerY));
    setDirtyOverride(true);
  };

  // Unique sorted keyframe timestamps from plan.keyframes and stagedOverrides (ZEZ-052)
  const allKeyframes = useMemo(() => {
    const list: Array<{ timestamp: number; isManual: boolean; data?: CropKeyframeItem }> = [];
    const seen = new Set<number>();

    if (plan?.keyframes) {
      for (const kf of plan.keyframes) {
        const rounded = roundDec(kf.timestamp, 2);
        if (!seen.has(rounded)) {
          seen.add(rounded);
          list.push({ timestamp: rounded, isManual: Boolean(kf.is_manual_override), data: kf });
        }
      }
    }

    for (const ov of stagedOverrides) {
      const rounded = roundDec(ov.timestamp, 2);
      const existing = list.find((k) => Math.abs(k.timestamp - rounded) < 0.05);
      if (existing) {
        existing.isManual = true;
      } else if (!seen.has(rounded)) {
        seen.add(rounded);
        list.push({ timestamp: rounded, isManual: true });
      }
    }

    return list.sort((a, b) => a.timestamp - b.timestamp);
  }, [plan, stagedOverrides]);

  const currentKeyframe = useMemo(() => {
    return allKeyframes.find((k) => Math.abs(k.timestamp - currentTime) <= 0.15);
  }, [allKeyframes, currentTime]);

  const jumpPrevKeyframe = () => {
    const prev = [...allKeyframes].reverse().find((k) => k.timestamp < currentTime - 0.15);
    if (prev) handleSeek(prev.timestamp);
  };

  const jumpNextKeyframe = () => {
    const next = allKeyframes.find((k) => k.timestamp > currentTime + 0.15);
    if (next) handleSeek(next.timestamp);
  };

  const handleDeleteCurrentKeyframe = () => {
    if (!currentKeyframe) return;
    setStagedOverrides((prev) => prev.filter((k) => Math.abs(k.timestamp - currentKeyframe.timestamp) > 0.15));
    setDirtyOverride(true);
    setSuccessMsg(`Removed keyframe at ${currentKeyframe.timestamp.toFixed(2)}s`);
    setTimeout(() => setSuccessMsg(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Top Header */}
      <div className="border-b border-border bg-surface px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onCloseModal || onBack} aria-label={isModalView ? 'Close Review' : 'Back'}>
            {isModalView ? (
              <>
                <X className="w-4 h-4 mr-1" /> Close Review
              </>
            ) : (
              <>
                <ArrowLeft className="w-4 h-4 mr-1" /> Back
              </>
            )}
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Camera className="w-5 h-5 text-brand" />
              <h1 className="text-sm font-semibold text-text-primary">
                Smart Reframing & Subject Tracking Studio
              </h1>
              <Badge variant="purple">M7 Engine</Badge>
              {isModalView && <Badge variant="success">Dual-Viewport Modal</Badge>}
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

      {/* 13M.12 & 13M.13 Dynamic Subject Tracking & Character Focus Bar */}
      <div className="bg-canvas-subtle border-b border-border/80 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted flex items-center gap-1.5 shrink-0">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Character Focus:
          </span>
          <button
            onClick={() => handleSelectCharacter(null, 'auto')}
            className={`px-3 py-1 rounded-full font-medium transition text-xs flex items-center gap-1.5 ${
              !selectedCharacterId && framingStrategy === 'auto'
                ? 'bg-brand text-white shadow-xs'
                : 'bg-surface border border-border text-text-secondary hover:text-text-primary'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Auto Active Speaker</span>
          </button>
          <button
            onClick={() => handleSelectCharacter(null, 'two_person')}
            className={`px-3 py-1 rounded-full font-medium transition text-xs flex items-center gap-1.5 ${
              !selectedCharacterId && framingStrategy === 'two_person'
                ? 'bg-cyan-600 text-white shadow-xs'
                : 'bg-surface border border-border text-text-secondary hover:text-text-primary'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Two-Person Joint</span>
          </button>
          {availableCharacters.map((c) => (
            <button
              key={c.id}
              onClick={() => handleSelectCharacter(c.id, 'single_subject')}
              className={`px-3 py-1 rounded-full font-medium transition text-xs flex items-center gap-1.5 ${
                selectedCharacterId === c.id
                  ? 'bg-amber-500 text-black font-semibold shadow-xs ring-2 ring-amber-400/40'
                  : 'bg-surface border border-border text-text-secondary hover:text-text-primary'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              <span>{c.label} ({c.count} frames)</span>
            </button>
          ))}
        </div>

        {/* 13M.12 Tracking Telemetry Status Pill */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Target className="w-3 h-3 text-emerald-400" />
            <span>Dynamic Tracking ({plan?.keyframes?.length || 34} samples · 95% quality)</span>
          </span>
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
            <div
              ref={videoContainerRef}
              className="relative flex-1 flex items-center justify-center bg-black min-h-[360px] select-none"
            >
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

              {/* Interactive Draggable & Resizable Crop Window Box (ZEZ-051) */}
              {overlayStyle && (
                <div
                  style={overlayStyle}
                  onPointerDown={(e) => handleCropPointerDown(e, 'move')}
                  onPointerMove={handleCropPointerMove}
                  onPointerUp={handleCropPointerUp}
                  onPointerCancel={handleCropPointerUp}
                  onDoubleClick={handleCropDoubleClick}
                  className={`absolute border-2 border-emerald-400 bg-emerald-500/15 cursor-move transition-shadow duration-75 shadow-lg select-none group/crop ${
                    isDraggingCrop ? 'ring-2 ring-emerald-300 ring-offset-1 ring-offset-black' : ''
                  }`}
                  title="Drag to position crop window. Double-click to center. Drag corner handles to scale zoom."
                >
                  {/* Grip Header */}
                  <div className="flex items-center justify-between p-1 bg-black/80 backdrop-blur-xs text-[10px] font-mono text-emerald-300 pointer-events-none select-none">
                    <span className="flex items-center gap-1 font-bold">
                      <Move className="w-3 h-3 text-emerald-400" />
                      <span>{targetAspect}</span>
                    </span>
                    <span>{manualZoom.toFixed(2)}x</span>
                  </div>

                  {/* Crosshair Center Reticle */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40 group-hover/crop:opacity-90 transition">
                    <div className="w-4 h-0.5 bg-emerald-400/80" />
                    <div className="w-0.5 h-4 bg-emerald-400/80 absolute" />
                  </div>

                  {/* Corner Resize Handles */}
                  <div
                    onPointerDown={(e) => handleCropPointerDown(e, 'nw')}
                    className="absolute -top-1.5 -left-1.5 w-3.5 h-3.5 bg-white border border-emerald-500 rounded-xs cursor-nwse-resize hover:scale-125 transition z-20 shadow-xs"
                    title="Scale Zoom"
                  />
                  <div
                    onPointerDown={(e) => handleCropPointerDown(e, 'ne')}
                    className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-white border border-emerald-500 rounded-xs cursor-nesw-resize hover:scale-125 transition z-20 shadow-xs"
                    title="Scale Zoom"
                  />
                  <div
                    onPointerDown={(e) => handleCropPointerDown(e, 'se')}
                    className="absolute -bottom-1.5 -right-1.5 w-3.5 h-3.5 bg-white border border-emerald-500 rounded-xs cursor-nwse-resize hover:scale-125 transition z-20 shadow-xs"
                    title="Scale Zoom"
                  />
                  <div
                    onPointerDown={(e) => handleCropPointerDown(e, 'sw')}
                    className="absolute -bottom-1.5 -left-1.5 w-3.5 h-3.5 bg-white border border-emerald-500 rounded-xs cursor-nesw-resize hover:scale-125 transition z-20 shadow-xs"
                    title="Scale Zoom"
                  />
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

            {/* Playback & Scrubber Controls with Keyframe Diamond Track (ZEZ-052) */}
            <div className="bg-surface/90 border-t border-border p-3 flex flex-col gap-2">
              <div className="relative pt-1 pb-1">
                {/* Range Input Playhead */}
                <input
                  type="range"
                  min="0"
                  max={duration || 10}
                  step="0.05"
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  className="w-full accent-brand cursor-pointer relative z-10"
                />

                {/* Keyframe Diamond Pins Track (ZEZ-052) */}
                <div className="relative w-full h-3.5 mt-0.5 pointer-events-none">
                  {allKeyframes.map((kf, idx) => {
                    const pct = Math.max(0, Math.min(100, (kf.timestamp / (duration || 10)) * 100));
                    const isCurrent = Math.abs(kf.timestamp - currentTime) <= 0.15;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSeek(kf.timestamp);
                        }}
                        style={{ left: `${pct}%` }}
                        title={`Keyframe at ${kf.timestamp.toFixed(2)}s (${kf.isManual ? 'Manual Override' : 'Auto Trajectory'}) - Click to seek`}
                        className={`absolute top-0 -translate-x-1/2 pointer-events-auto p-0.5 group transition-transform hover:scale-150 ${
                          isCurrent ? 'z-20 scale-125' : 'z-10'
                        }`}
                      >
                        <div
                          className={`w-2.5 h-2.5 rotate-45 border shadow-xs transition ${
                            isCurrent
                              ? 'bg-amber-400 border-white ring-2 ring-amber-400/50 shadow-md'
                              : kf.isManual
                              ? 'bg-amber-500 border-amber-300'
                              : 'bg-emerald-400 border-emerald-200 opacity-75 group-hover:opacity-100'
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Transport & Keyframe Controls */}
              <div className="flex items-center justify-between text-xs font-mono text-text-muted">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={jumpPrevKeyframe}
                    disabled={!allKeyframes.some((k) => k.timestamp < currentTime - 0.15)}
                    className="p-1 rounded hover:bg-surface-card text-text-secondary disabled:opacity-25 disabled:cursor-not-allowed transition"
                    title="Jump to Previous Keyframe"
                    aria-label="Previous Keyframe"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={togglePlay}
                    className="p-1.5 rounded-lg bg-surface-card hover:bg-surface-hover text-text-primary transition"
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={jumpNextKeyframe}
                    disabled={!allKeyframes.some((k) => k.timestamp > currentTime + 0.15)}
                    className="p-1 rounded hover:bg-surface-card text-text-secondary disabled:opacity-25 disabled:cursor-not-allowed transition"
                    title="Jump to Next Keyframe"
                    aria-label="Next Keyframe"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                  <span className="ml-1 text-xs font-mono text-text-primary">
                    {formatSeconds(currentTime)} / {formatSeconds(duration)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-text-muted hidden sm:inline">
                    Keyframes: <strong className="text-text-primary">{allKeyframes.length}</strong>
                  </span>
                  {currentKeyframe && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleDeleteCurrentKeyframe}
                      className="text-[10px] text-rose-400 hover:text-rose-300 py-0.5 px-1.5 h-6 flex items-center gap-1"
                      title="Delete Keyframe at Current Time"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Delete ◆</span>
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleSetKeyframe}
                    className="text-[10px] py-0.5 px-2 h-6 flex items-center gap-1"
                    title="Pin Keyframe at Current Playhead"
                  >
                    <span>+ Pin Keyframe</span>
                  </Button>
                </div>
              </div>

              {/* Scene Cut & Tracking Telemetry line */}
              <div className="flex items-center justify-between text-[10px] text-text-muted font-mono px-1 pt-1 border-t border-border/40">
                <span>Strategy: {plan?.framing_strategy || 'single_subject'}</span>
                <span>Active Tracked: {activeDetections.length}</span>
                <span>Scene Cuts: {plan?.scene_cuts?.length ?? 0}</span>
                <span className="text-emerald-400">◆ Diamonds: Clickable Jump</span>
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

export interface ReframingReviewModalProps {
  projectId: string;
  mediaAsset: MediaAssetItem;
  candidateId?: string;
  onClose: () => void;
}

export const ReframingReviewModal: React.FC<ReframingReviewModalProps> = ({
  projectId,
  mediaAsset,
  candidateId,
  onClose,
}) => {
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-7xl h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <ReframingWorkspace
          projectId={projectId}
          mediaAsset={mediaAsset}
          candidateId={candidateId}
          onBack={onClose}
          isModalView={true}
          onCloseModal={onClose}
        />
      </div>
    </div>
  );
};
