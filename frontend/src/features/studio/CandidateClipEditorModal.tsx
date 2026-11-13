import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Save,
  X,
  Crop,
  Sliders,
  Sparkles,
  Check,
  AlertCircle,
  Clock,
  Layers,
  ZoomIn,
  MoveHorizontal,
  MoveVertical,
  Crosshair,
  RefreshCw,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  CandidateItem,
  CandidateClipEdit,
  AspectRatioOption,
  FramingMode,
} from '../../types/highlights';
import { MediaAssetItem } from '../../types/projects';
import {
  fetchCandidateEdit,
  saveCandidateEdit,
  resetCandidateEdit,
  trackCandidateSubjects,
} from '../../services/apiClient';

interface CandidateClipEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: CandidateItem | null;
  mediaAsset: MediaAssetItem;
  projectId: string;
  videoSrc: string;
  onSaveSuccess?: (edit: CandidateClipEdit) => void;
}

const ASPECT_RATIO_OPTIONS: Array<{ value: AspectRatioOption; label: string; ratioW: number; ratioH: number }> = [
  { value: '9:16', label: '9:16 (Vertical Short)', ratioW: 9, ratioH: 16 },
  { value: '1:1', label: '1:1 (Square)', ratioW: 1, ratioH: 1 },
  { value: '16:9', label: '16:9 (Landscape)', ratioW: 16, ratioH: 9 },
  { value: '4:5', label: '4:5 (Social Feed)', ratioW: 4, ratioH: 5 },
  { value: '4:3', label: '4:3 (Standard TV)', ratioW: 4, ratioH: 3 },
  { value: '3:4', label: '3:4 (Portrait Tablet)', ratioW: 3, ratioH: 4 },
];

function formatTimecode(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00.00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

export const CandidateClipEditorModal: React.FC<CandidateClipEditorModalProps> = ({
  isOpen,
  onClose,
  candidate,
  mediaAsset,
  projectId,
  videoSrc,
  onSaveSuccess,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [tracking, setTracking] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Edit state
  const [editState, setEditState] = useState<CandidateClipEdit | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [endTime, setEndTime] = useState<number>(10);
  const [aspectRatio, setAspectRatio] = useState<AspectRatioOption>('9:16');
  const [framingMode, setFramingMode] = useState<FramingMode>('center');
  const [cropXPct, setCropXPct] = useState<number>(50.0);
  const [cropYPct, setCropYPct] = useState<number>(50.0);
  const [cropZoom, setCropZoom] = useState<number>(1.0);

  // Playback state
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);

  const mediaDuration = mediaAsset.duration_seconds || 60.0;
  const currentDuration = useMemo(() => Math.max(0.1, Number((endTime - startTime).toFixed(2))), [startTime, endTime]);

  // Load existing edit or initialize
  const loadEditData = useCallback(async () => {
    if (!candidate) return;
    setLoading(true);
    setStatusMessage(null);
    try {
      const edit = await fetchCandidateEdit(projectId, mediaAsset.id, candidate.id);
      setEditState(edit);
      setStartTime(edit.edited_start_time);
      setEndTime(edit.edited_end_time);
      setAspectRatio(edit.aspect_ratio || '9:16');
      setFramingMode(edit.framing_mode || 'center');
      setCropXPct(edit.manual_crop_x_pct ?? 50.0);
      setCropYPct(edit.manual_crop_y_pct ?? 50.0);
      setCropZoom(edit.manual_crop_zoom ?? 1.0);

      if (videoRef.current) {
        videoRef.current.currentTime = edit.edited_start_time;
      }
      setCurrentTime(edit.edited_start_time);
    } catch (err: unknown) {
      console.error('Failed to load candidate edit state:', err);
      // Fallback to candidate initial bounds
      const initialStart = candidate.start_time;
      const initialEnd = candidate.end_time;
      setStartTime(initialStart);
      setEndTime(initialEnd);
      setAspectRatio('9:16');
      setFramingMode('center');
      setCropXPct(50.0);
      setCropYPct(50.0);
      setCropZoom(1.0);
      if (videoRef.current) {
        videoRef.current.currentTime = initialStart;
      }
      setCurrentTime(initialStart);
    } finally {
      setLoading(false);
    }
  }, [candidate, projectId, mediaAsset.id]);

  useEffect(() => {
    if (isOpen && candidate) {
      void loadEditData();
    }
  }, [isOpen, candidate, loadEditData]);

  // Constrain playback strictly within [startTime, endTime]
  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);

    if (t >= endTime) {
      videoRef.current.currentTime = startTime;
    } else if (t < startTime) {
      videoRef.current.currentTime = startTime;
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      if (videoRef.current.currentTime < startTime || videoRef.current.currentTime >= endTime) {
        videoRef.current.currentTime = startTime;
      }
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  // Adjust Start/End timestamps with validation
  const handleStartTimeChange = (val: number) => {
    const clamped = Math.max(0, Math.min(val, endTime - 1.0));
    setStartTime(Number(clamped.toFixed(2)));
    if (videoRef.current && (videoRef.current.currentTime < clamped || videoRef.current.currentTime > endTime)) {
      videoRef.current.currentTime = clamped;
      setCurrentTime(clamped);
    }
  };

  const handleEndTimeChange = (val: number) => {
    const clamped = Math.min(mediaDuration, Math.max(val, startTime + 1.0));
    setEndTime(Number(clamped.toFixed(2)));
    if (videoRef.current && videoRef.current.currentTime > clamped) {
      videoRef.current.currentTime = startTime;
      setCurrentTime(startTime);
    }
  };

  // Save Edit Handler
  const handleSave = async () => {
    if (!candidate) return;
    setSaving(true);
    setStatusMessage(null);
    try {
      const saved = await saveCandidateEdit(projectId, mediaAsset.id, candidate.id, {
        edited_start_time: startTime,
        edited_end_time: endTime,
        aspect_ratio: aspectRatio,
        framing_mode: framingMode,
        manual_crop_x_pct: cropXPct,
        manual_crop_y_pct: cropYPct,
        manual_crop_zoom: cropZoom,
      });
      setEditState(saved);
      setStatusMessage({ type: 'success', text: 'Clip edits saved successfully! Original candidate discovery data remains preserved.' });
      if (onSaveSuccess) onSaveSuccess(saved);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusMessage({ type: 'error', text: `Failed to save edit: ${msg}` });
    } finally {
      setSaving(false);
    }
  };

  // Reset to Original Handler
  const handleReset = async () => {
    if (!candidate) return;
    setSaving(true);
    setStatusMessage(null);
    try {
      const reset = await resetCandidateEdit(projectId, mediaAsset.id, candidate.id);
      setEditState(reset);
      setStartTime(reset.edited_start_time);
      setEndTime(reset.edited_end_time);
      setAspectRatio(reset.aspect_ratio);
      setFramingMode(reset.framing_mode);
      setCropXPct(reset.manual_crop_x_pct);
      setCropYPct(reset.manual_crop_y_pct);
      setCropZoom(reset.manual_crop_zoom);
      if (videoRef.current) {
        videoRef.current.currentTime = reset.edited_start_time;
      }
      setCurrentTime(reset.edited_start_time);
      setStatusMessage({ type: 'info', text: 'Reverted clip boundaries and framing back to initial discovery state.' });
      if (onSaveSuccess) onSaveSuccess(reset);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusMessage({ type: 'error', text: `Failed to reset: ${msg}` });
    } finally {
      setSaving(false);
    }
  };

  // Run Smart Tracking Handler
  const handleRunTracking = async () => {
    if (!candidate) return;
    setTracking(true);
    setStatusMessage(null);
    try {
      const result = await trackCandidateSubjects(projectId, mediaAsset.id, candidate.id, aspectRatio);
      setEditState(result);
      setFramingMode('smart_tracking');
      setStatusMessage({
        type: 'success',
        text: `Smart subject tracking completed (${result.tracking_status}). Reframing keyframes computed.`,
      });
      if (onSaveSuccess) onSaveSuccess(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusMessage({ type: 'error', text: `Smart tracking error: ${msg}` });
    } finally {
      setTracking(false);
    }
  };

  // Calculate Crop Box overlay styles
  const cropBoxStyle = useMemo(() => {
    const selected = ASPECT_RATIO_OPTIONS.find((o) => o.value === aspectRatio) || ASPECT_RATIO_OPTIONS[0];
    const targetAspect = selected.ratioW / selected.ratioH; // e.g. 9/16 = 0.5625

    // Assume 16:9 source (standard HD)
    const sourceAspect = 16 / 9; // 1.777

    let widthPct = (targetAspect / sourceAspect) * 100;
    let heightPct = 100;

    if (targetAspect > sourceAspect) {
      widthPct = 100;
      heightPct = (sourceAspect / targetAspect) * 100;
    }

    // Apply digital zoom
    const zoomW = widthPct / cropZoom;
    const zoomH = heightPct / cropZoom;

    // Apply manual offset (0% = left/top, 100% = right/bottom)
    let leftPct = (cropXPct / 100) * (100 - zoomW);
    let topPct = (cropYPct / 100) * (100 - zoomH);

    if (framingMode === 'center') {
      leftPct = (100 - zoomW) / 2;
      topPct = (100 - zoomH) / 2;
    }

    return {
      width: `${Math.max(5, Math.min(100, zoomW))}%`,
      height: `${Math.max(5, Math.min(100, zoomH))}%`,
      left: `${Math.max(0, Math.min(100 - zoomW, leftPct))}%`,
      top: `${Math.max(0, Math.min(100 - zoomH, topPct))}%`,
    };
  }, [aspectRatio, framingMode, cropXPct, cropYPct, cropZoom]);

  if (!isOpen || !candidate) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 sm:p-6 overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-[#14171F] border border-[#2D3548] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#2D3548] bg-[#1C202B]/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
              <Crop className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-text-primary tracking-tight">
                  {candidate.title || `Candidate ${candidate.id.slice(0, 8)}`}
                </h3>
                <Badge variant="info" className="text-[10px] font-mono border-primary/30 text-primary">
                  {aspectRatio}
                </Badge>
                <Badge variant="default" className="text-[10px] font-mono border-[#2D3548] text-text-secondary">
                  {currentDuration.toFixed(1)}s
                </Badge>
              </div>
              <p className="text-[11px] text-text-muted">
                Interactive preview, trimming, aspect ratio reframing & subject tracking.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={loading || saving}
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
              className="text-xs border-[#2D3548] hover:bg-[#252C3D] text-text-secondary hover:text-text-primary"
              title="Reset boundaries and framing to initial AI discovery"
            >
              Reset to Original
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={loading || saving}
              leftIcon={saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              className="text-xs font-medium"
            >
              {saving ? 'Saving...' : 'Save Clip Edit'}
            </Button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-[#252C3D] transition-colors"
              title="Close Editor"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div
            className={`px-5 py-2 text-xs flex items-center gap-2 border-b ${
              statusMessage.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-900/50 text-emerald-300'
                : statusMessage.type === 'error'
                ? 'bg-rose-950/40 border-rose-900/50 text-rose-300'
                : 'bg-blue-950/40 border-blue-900/50 text-blue-300'
            }`}
          >
            {statusMessage.type === 'success' ? (
              <Check className="w-3.5 h-3.5 shrink-0" />
            ) : statusMessage.type === 'error' ? (
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 p-5 overflow-y-auto flex-1">
          {/* Left Column: Player & Bounded Preview */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="relative aspect-video bg-black rounded-lg border border-[#2D3548] overflow-hidden flex items-center justify-center group shadow-inner">
              <video
                ref={videoRef}
                src={videoSrc}
                className="w-full h-full object-contain"
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                playsInline
              />

              {/* Dynamic Crop Overlay */}
              <div className="absolute inset-0 pointer-events-none">
                <div
                  className="absolute border-2 border-primary/90 bg-primary/10 transition-all duration-150 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                  style={cropBoxStyle}
                >
                  <div className="absolute top-1 left-1.5 px-1.5 py-0.5 rounded bg-black/80 text-[9px] font-mono text-primary font-bold tracking-wider">
                    {aspectRatio}
                  </div>
                  {framingMode === 'smart_tracking' && (
                    <div className="absolute bottom-1 right-1.5 px-1.5 py-0.5 rounded bg-blue-950/90 text-[9px] font-mono text-blue-300 flex items-center gap-1 border border-blue-800/40">
                      <Crosshair className="w-2.5 h-2.5" />
                      TRACKED
                    </div>
                  )}
                </div>
              </div>

              {/* Play / Pause Center Overlay Button */}
              <button
                onClick={togglePlay}
                className="absolute inset-0 m-auto w-12 h-12 rounded-full bg-black/60 hover:bg-black/80 border border-white/20 text-white flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 hover:scale-105"
                title={isPlaying ? 'Pause' : 'Play candidate clip loop'}
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>
            </div>

            {/* Playback Transport & Timecode Bar */}
            <div className="flex items-center justify-between px-3 py-2 bg-[#1C202B] border border-[#2D3548] rounded-lg text-xs font-mono">
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="p-1 rounded text-text-secondary hover:text-text-primary hover:bg-[#252C3D] transition-colors"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <div className="flex items-center gap-1.5 text-text-muted">
                  <span className="text-text-primary font-semibold">{formatTimecode(currentTime)}</span>
                  <span>/</span>
                  <span>{formatTimecode(endTime)}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] text-text-muted uppercase tracking-wider">Clip Loop Window:</span>
                <span className="px-2 py-0.5 rounded bg-[#14171F] border border-[#2D3548] text-primary font-semibold">
                  {formatTimecode(startTime)} — {formatTimecode(endTime)}
                </span>
              </div>
            </div>

            {/* Interactive Timeline Trimming Control */}
            <div className="bg-[#1C202B] border border-[#2D3548] rounded-lg p-3.5 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-text-secondary flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-text-muted" />
                  Timeline Trimming Handles
                </span>
                <span className="text-text-muted font-mono text-[11px]">
                  Duration: <strong className="text-text-primary">{currentDuration.toFixed(2)}s</strong> (Max {mediaDuration.toFixed(1)}s)
                </span>
              </div>

              {/* Visual Range Bar */}
              <div className="relative w-full h-8 bg-[#14171F] border border-[#2D3548] rounded-md overflow-hidden flex items-center px-1">
                {/* Active Highlight Range */}
                <div
                  className="absolute h-6 bg-primary/25 border-y-2 border-primary rounded"
                  style={{
                    left: `${(startTime / mediaDuration) * 100}%`,
                    width: `${((endTime - startTime) / mediaDuration) * 100}%`,
                  }}
                />
                {/* Current Playhead */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_white] z-10 transition-all"
                  style={{ left: `${(currentTime / mediaDuration) * 100}%` }}
                />
              </div>

              {/* Start & End Numeric Adjusters */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <label className="text-[11px] text-text-muted flex items-center justify-between">
                    <span>Start Timestamp</span>
                    <span className="font-mono text-text-secondary">{formatTimecode(startTime)}</span>
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleStartTimeChange(startTime - 0.5)}
                      className="px-2 py-1 rounded bg-[#14171F] border border-[#2D3548] text-text-secondary hover:text-text-primary hover:bg-[#252C3D] text-xs font-mono"
                    >
                      -0.5s
                    </button>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max={endTime - 1.0}
                      value={startTime}
                      onChange={(e) => handleStartTimeChange(parseFloat(e.target.value) || 0)}
                      className="flex-1 px-2 py-1 bg-[#14171F] border border-[#2D3548] rounded text-center text-xs font-mono text-text-primary focus:outline-none focus:border-primary"
                    />
                    <button
                      onClick={() => handleStartTimeChange(startTime + 0.5)}
                      className="px-2 py-1 rounded bg-[#14171F] border border-[#2D3548] text-text-secondary hover:text-text-primary hover:bg-[#252C3D] text-xs font-mono"
                    >
                      +0.5s
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] text-text-muted flex items-center justify-between">
                    <span>End Timestamp</span>
                    <span className="font-mono text-text-secondary">{formatTimecode(endTime)}</span>
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEndTimeChange(endTime - 0.5)}
                      className="px-2 py-1 rounded bg-[#14171F] border border-[#2D3548] text-text-secondary hover:text-text-primary hover:bg-[#252C3D] text-xs font-mono"
                    >
                      -0.5s
                    </button>
                    <input
                      type="number"
                      step="0.1"
                      min={startTime + 1.0}
                      max={mediaDuration}
                      value={endTime}
                      onChange={(e) => handleEndTimeChange(parseFloat(e.target.value) || startTime + 1.0)}
                      className="flex-1 px-2 py-1 bg-[#14171F] border border-[#2D3548] rounded text-center text-xs font-mono text-text-primary focus:outline-none focus:border-primary"
                    />
                    <button
                      onClick={() => handleEndTimeChange(endTime + 0.5)}
                      className="px-2 py-1 rounded bg-[#14171F] border border-[#2D3548] text-text-secondary hover:text-text-primary hover:bg-[#252C3D] text-xs font-mono"
                    >
                      +0.5s
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Aspect Ratio & Framing Configuration */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            {/* Target Aspect Ratio */}
            <div className="bg-[#1C202B] border border-[#2D3548] rounded-lg p-3.5 space-y-2.5">
              <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-text-muted" />
                Target Aspect Ratio
              </span>
              <div className="grid grid-cols-2 gap-2">
                {ASPECT_RATIO_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setAspectRatio(opt.value)}
                    className={`px-3 py-2 rounded-lg border text-xs font-medium flex flex-col items-start gap-0.5 transition-all ${
                      aspectRatio === opt.value
                        ? 'bg-primary/15 border-primary text-primary shadow-xs'
                        : 'bg-[#14171F] border-[#2D3548] text-text-muted hover:text-text-secondary hover:border-[#3E4861]'
                    }`}
                  >
                    <span className="font-mono font-bold">{opt.value}</span>
                    <span className="text-[10px] text-text-muted">{opt.label.split(' ')[1] || ''}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Framing Mode Selection */}
            <div className="bg-[#1C202B] border border-[#2D3548] rounded-lg p-3.5 space-y-3">
              <span className="text-xs font-medium text-text-secondary flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-text-muted" />
                Framing & Tracking Strategy
              </span>
              <div className="grid grid-cols-3 gap-1.5 bg-[#14171F] p-1 rounded-lg border border-[#2D3548]">
                <button
                  onClick={() => setFramingMode('center')}
                  className={`py-1.5 px-2 rounded text-xs font-medium transition-all ${
                    framingMode === 'center'
                      ? 'bg-[#252C3D] text-text-primary shadow-xs'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  Center Crop
                </button>
                <button
                  onClick={() => setFramingMode('manual')}
                  className={`py-1.5 px-2 rounded text-xs font-medium transition-all ${
                    framingMode === 'manual'
                      ? 'bg-[#252C3D] text-text-primary shadow-xs'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  Manual Offset
                </button>
                <button
                  onClick={() => setFramingMode('smart_tracking')}
                  className={`py-1.5 px-2 rounded text-xs font-medium transition-all flex items-center justify-center gap-1 ${
                    framingMode === 'smart_tracking'
                      ? 'bg-primary/20 text-primary border border-primary/30 shadow-xs'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  <Sparkles className="w-3 h-3" />
                  Smart Tracking
                </button>
              </div>

              {/* Conditional Controls based on Framing Mode */}
              {framingMode === 'center' && (
                <div className="p-3 bg-[#14171F] rounded-lg border border-[#2D3548]/70 text-xs text-text-muted space-y-1">
                  <p className="font-medium text-text-secondary">Symmetrical Center Crop</p>
                  <p className="text-[11px]">
                    The frame is locked dead-center in the source video. Best for centered interviews, stationary hosts, or landscape footage.
                  </p>
                </div>
              )}

              {framingMode === 'manual' && (
                <div className="space-y-3 p-3 bg-[#14171F] rounded-lg border border-[#2D3548]/70">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-text-muted">
                      <span className="flex items-center gap-1">
                        <MoveHorizontal className="w-3 h-3" /> Horizontal Offset (X)
                      </span>
                      <span className="font-mono text-text-primary">{cropXPct.toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={cropXPct}
                      onChange={(e) => setCropXPct(parseFloat(e.target.value))}
                      className="w-full accent-primary h-1.5 bg-[#252C3D] rounded-lg cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-text-muted">
                      <span className="flex items-center gap-1">
                        <MoveVertical className="w-3 h-3" /> Vertical Offset (Y)
                      </span>
                      <span className="font-mono text-text-primary">{cropYPct.toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={cropYPct}
                      onChange={(e) => setCropYPct(parseFloat(e.target.value))}
                      className="w-full accent-primary h-1.5 bg-[#252C3D] rounded-lg cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-text-muted">
                      <span className="flex items-center gap-1">
                        <ZoomIn className="w-3 h-3" /> Digital Zoom
                      </span>
                      <span className="font-mono text-text-primary">{cropZoom.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="1.0"
                      max="2.5"
                      step="0.05"
                      value={cropZoom}
                      onChange={(e) => setCropZoom(parseFloat(e.target.value))}
                      className="w-full accent-primary h-1.5 bg-[#252C3D] rounded-lg cursor-pointer"
                    />
                  </div>
                </div>
              )}

              {framingMode === 'smart_tracking' && (
                <div className="space-y-3 p-3 bg-[#14171F] rounded-lg border border-[#2D3548]/70">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-secondary font-medium">Smart Subject Tracking Engine</span>
                    <Badge
                      variant="default"
                      className={`text-[10px] font-mono ${
                        editState?.tracking_status === 'tracked'
                          ? 'border-emerald-800 text-emerald-400 bg-emerald-950/30'
                          : editState?.tracking_status === 'fallback'
                          ? 'border-amber-800 text-amber-400 bg-amber-950/30'
                          : 'border-[#2D3548] text-text-muted'
                      }`}
                    >
                      {editState?.tracking_status === 'tracked'
                        ? 'TRACKED'
                        : editState?.tracking_status === 'fallback'
                        ? 'SALIENCY FALLBACK'
                        : 'UNTRACKED'}
                    </Badge>
                  </div>

                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Uses OpenCV Haar cascades (face/upper-body) and central visual saliency over frame samples on the clip interval to calculate smoothed portrait crop keyframes.
                  </p>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRunTracking}
                    disabled={tracking || loading}
                    leftIcon={tracking ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Crosshair className="w-3.5 h-3.5 text-primary" />}
                    className="w-full text-xs border-primary/40 hover:bg-primary/10 text-primary"
                  >
                    {tracking ? 'Running Subject Detection...' : 'Run Subject Tracking on Clip'}
                  </Button>
                </div>
              )}
            </div>

            {/* Pristine Discovery Data Confirmation Note */}
            <div className="p-3 bg-[#14171F] border border-[#2D3548] rounded-lg text-[11px] text-text-muted space-y-1">
              <span className="font-semibold text-text-secondary block">Data Integrity Guarantee:</span>
              <p>
                Editing and trimming this clip operates on an isolated edit layer. Original candidate discovery data and persistent novelty exclusion history remain permanently untouched.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
