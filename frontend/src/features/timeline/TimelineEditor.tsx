import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play,
  Pause,
  Scissors,
  Trash2,
  Copy,
  Type,
  Undo2,
  Redo2,
  ZoomIn,
  ZoomOut,
  Film,
  Volume2,
  VolumeX,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Plus,
  Send,
  Sparkles,
  AlertTriangle,
  Clock,
  Layers,
  Sliders,
  Download,
  FileVideo,
} from 'lucide-react';

import {
  fetchTimeline,
  addTimelineTrack,
  updateTimelineTrack,
  deleteTimelineTrack,
  insertTimelineClip,
  splitTimelineClip,
  deleteTimelineClip,
  duplicateTimelineClip,
  updateTimelineClipProps,
  addTimelineTextOverlay,
  fetchTimelineHistory,
  undoTimeline,
  redoTimeline,
  fetchAIConversation,
  sendAIMessage,
  approveAIPlan,
  rejectAIPlan,
  renderTimeline,
  fetchProjectMedia,
} from '../../services/apiClient';

import {
  TimelineRecord,
  TimelineTrack,
  TimelineClip,
  AIConversation,
  TrackType,
} from '../../types/timeline';

import { ProjectItem, MediaAssetItem } from '../../types/projects';

interface TimelineEditorProps {
  currentProject: ProjectItem | null;
}

export const TimelineEditor: React.FC<TimelineEditorProps> = ({ currentProject }) => {
  const [timeline, setTimeline] = useState<TimelineRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Playback & Selection
  const [playheadTime, setPlayheadTime] = useState<number>(0.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '16:9'>('9:16');
  const [zoomLevel, setZoomLevel] = useState<number>(50); // pixels per second
  const [snapping, setSnapping] = useState<boolean>(true);

  // History / Undo / Redo
  const [canUndo, setCanUndo] = useState<boolean>(false);
  const [canRedo, setCanRedo] = useState<boolean>(false);

  // AI Assistant
  const [activeTab, setActiveTab] = useState<'inspector' | 'ai'>('inspector');
  const [aiConversation, setAiConversation] = useState<AIConversation | null>(null);
  const [aiInput, setAiInput] = useState<string>('');
  const [aiLoading, setAiLoading] = useState<boolean>(false);

  // Media picker modal
  const [mediaAssets, setMediaAssets] = useState<MediaAssetItem[]>([]);
  const [showMediaModal, setShowMediaModal] = useState<boolean>(false);
  const [targetTrackForAdd, setTargetTrackForAdd] = useState<string | null>(null);

  // Render modal
  const [renderStatus, setRenderStatus] = useState<string | null>(null);

  const timelineContainerRef = useRef<HTMLDivElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);

  // ---------------------------------------------------------------------------
  // Data Loading
  // ---------------------------------------------------------------------------

  const loadTimelineData = async () => {
    if (!currentProject) return;
    try {
      setLoading(true);
      setError(null);
      const tl = await fetchTimeline(currentProject.id);
      setTimeline(tl);
      await refreshHistory(tl.id);
      await refreshAIConversation(tl.id);

      const mediaRes = await fetchProjectMedia(currentProject.id);
      setMediaAssets(mediaRes.items || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load timeline.');
    } finally {
      setLoading(false);
    }
  };

  const refreshHistory = async (timelineId: string) => {
    if (!currentProject) return;
    try {
      const hist = await fetchTimelineHistory(currentProject.id, timelineId);
      setCanUndo(hist.can_undo);
      setCanRedo(hist.can_redo);
    } catch {
      // non-fatal
    }
  };

  const refreshAIConversation = async (timelineId: string) => {
    if (!currentProject) return;
    try {
      const conv = await fetchAIConversation(currentProject.id, timelineId);
      setAiConversation(conv);
    } catch {
      // non-fatal
    }
  };

  useEffect(() => {
    loadTimelineData();
  }, [currentProject]);

  // ---------------------------------------------------------------------------
  // Playback Loop
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (isPlaying) {
      lastTimeRef.current = performance.now();
      const tick = (now: number) => {
        const delta = (now - lastTimeRef.current) / 1000;
        lastTimeRef.current = now;
        setPlayheadTime((prev) => {
          const next = prev + delta;
          const maxDur = timeline ? Math.max(10, timeline.duration) : 30;
          if (next >= maxDur) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
        animationFrameRef.current = requestAnimationFrame(tick);
      };
      animationFrameRef.current = requestAnimationFrame(tick);
    } else {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    }
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, timeline]);

  const getClipDuration = (c: TimelineClip): number => Math.max(0, c.timeline_end - c.timeline_start);

  // Selected clip object
  const selectedClip = useMemo(() => {
    if (!timeline || !selectedClipId) return null;
    for (const tr of timeline.tracks) {
      const found = tr.clips.find((c) => c.id === selectedClipId);
      if (found) return found;
    }
    return null;
  }, [timeline, selectedClipId]);

  // ---------------------------------------------------------------------------
  // Timeline Operations Handlers
  // ---------------------------------------------------------------------------

  const handleUndo = async () => {
    if (!currentProject || !timeline || !canUndo) return;
    try {
      const updated = await undoTimeline(currentProject.id, timeline.id);
      setTimeline(updated);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Undo failed');
    }
  };

  const handleRedo = async () => {
    if (!currentProject || !timeline || !canRedo) return;
    try {
      const updated = await redoTimeline(currentProject.id, timeline.id);
      setTimeline(updated);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Redo failed');
    }
  };

  const handleSplitAtPlayhead = async () => {
    if (!currentProject || !timeline) return;
    const targetClip = selectedClip || findClipAtPlayhead();
    if (!targetClip) {
      alert('Please select a clip or move playhead over a clip to split.');
      return;
    }
    if (playheadTime <= targetClip.timeline_start + 0.05 || playheadTime >= targetClip.timeline_end - 0.05) {
      alert('Playhead must be strictly within clip duration to split.');
      return;
    }

    try {
      await splitTimelineClip(currentProject.id, timeline.id, {
        clip_id: targetClip.id,
        split_time: playheadTime,
      });
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Split failed');
    }
  };

  const handleDeleteSelected = async () => {
    if (!currentProject || !timeline || !selectedClipId) return;
    try {
      await deleteTimelineClip(currentProject.id, timeline.id, selectedClipId);
      setSelectedClipId(null);
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Delete clip failed');
    }
  };

  const handleDuplicateSelected = async () => {
    if (!currentProject || !timeline || !selectedClipId) return;
    try {
      const dup = await duplicateTimelineClip(currentProject.id, timeline.id, selectedClipId);
      setSelectedClipId(dup.id);
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Duplicate clip failed');
    }
  };

  const handleAddTextOverlay = async () => {
    if (!currentProject || !timeline) return;
    const text = prompt('Enter text for overlay:', 'Highlight Moment');
    if (!text) return;
    try {
      const cl = await addTimelineTextOverlay(currentProject.id, timeline.id, {
        text,
        timeline_start: playheadTime,
        duration: 3.5,
      });
      setSelectedClipId(cl.id);
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Failed to add text overlay');
    }
  };

  const handleAddTrack = async (type: TrackType) => {
    if (!currentProject || !timeline) return;
    const name = prompt(`Enter ${type} track name:`, `${type.toUpperCase()} Track`);
    if (!name) return;
    try {
      await addTimelineTrack(currentProject.id, timeline.id, {
        name,
        track_type: type,
      });
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
    } catch (err: any) {
      alert(err?.message || 'Add track failed');
    }
  };

  const handleToggleTrackMute = async (track: TimelineTrack) => {
    if (!currentProject || !timeline) return;
    try {
      await updateTimelineTrack(currentProject.id, timeline.id, track.id, {
        is_muted: !track.is_muted,
      });
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
    } catch (err: any) {
      alert(err?.message || 'Update track failed');
    }
  };

  const handleToggleTrackLock = async (track: TimelineTrack) => {
    if (!currentProject || !timeline) return;
    try {
      await updateTimelineTrack(currentProject.id, timeline.id, track.id, {
        is_locked: !track.is_locked,
      });
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
    } catch (err: any) {
      alert(err?.message || 'Update track failed');
    }
  };

  const handleToggleTrackVisibility = async (track: TimelineTrack) => {
    if (!currentProject || !timeline) return;
    try {
      await updateTimelineTrack(currentProject.id, timeline.id, track.id, {
        is_visible: !track.is_visible,
      });
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
    } catch (err: any) {
      alert(err?.message || 'Update track failed');
    }
  };

  const handleDeleteTrack = async (trackId: string) => {
    if (!currentProject || !timeline) return;
    if (!confirm('Are you sure you want to delete this track and all its clips?')) return;
    try {
      await deleteTimelineTrack(currentProject.id, timeline.id, trackId);
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
    } catch (err: any) {
      alert(err?.message || 'Delete track failed');
    }
  };

  const handleInsertMediaClip = async (media: MediaAssetItem) => {
    if (!currentProject || !timeline || !targetTrackForAdd) return;
    try {
      const dur = Math.min(10.0, Number(media.duration_seconds) || 5.0);
      await insertTimelineClip(currentProject.id, timeline.id, {
        track_id: targetTrackForAdd,
        source_media_id: media.id,
        name: media.original_filename,
        timeline_start: playheadTime,
        duration: dur,
        source_in: 0.0,
      });
      setShowMediaModal(false);
      const reloaded = await fetchTimeline(currentProject.id);
      setTimeline(reloaded);
      await refreshHistory(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Failed to insert media clip');
    }
  };

  const findClipAtPlayhead = (): TimelineClip | null => {
    if (!timeline) return null;
    for (const tr of timeline.tracks) {
      for (const cl of tr.clips) {
        if (cl.timeline_start <= playheadTime && playheadTime <= cl.timeline_end) {
          return cl;
        }
      }
    }
    return null;
  };

  // ---------------------------------------------------------------------------
  // AI Assistant Handlers
  // ---------------------------------------------------------------------------

  const handleSendAIMessage = async (customPrompt?: string) => {
    if (!currentProject || !timeline) return;
    const msgText = customPrompt || aiInput.trim();
    if (!msgText) return;

    try {
      setAiLoading(true);
      setAiInput('');
      await sendAIMessage(currentProject.id, timeline.id, {
        message: msgText,
        playhead_time: playheadTime,
        selected_clip_id: selectedClipId || undefined,
        selected_track_id: selectedTrackId || undefined,
      });

      await refreshAIConversation(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'AI message failed');
    } finally {
      setAiLoading(false);
    }
  };

  const handleApprovePlan = async (planId: string) => {
    if (!currentProject || !timeline) return;
    try {
      setAiLoading(true);
      const updated = await approveAIPlan(currentProject.id, timeline.id, planId);
      setTimeline(updated);
      await refreshHistory(timeline.id);
      await refreshAIConversation(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Plan approval failed');
    } finally {
      setAiLoading(false);
    }
  };

  const handleRejectPlan = async (planId: string) => {
    if (!currentProject || !timeline) return;
    try {
      await rejectAIPlan(currentProject.id, timeline.id, planId);
      await refreshAIConversation(timeline.id);
    } catch (err: any) {
      alert(err?.message || 'Plan rejection failed');
    }
  };

  // ---------------------------------------------------------------------------
  // Render Execution
  // ---------------------------------------------------------------------------

  const handleRenderTimeline = async () => {
    if (!currentProject || !timeline) return;
    try {
      setRenderStatus('Rendering sequence...');
      const res = await renderTimeline(currentProject.id, timeline.id, {
        preset_id: aspectRatio === '9:16' ? 'shorts_reels_9_16' : 'landscape_16_9',
        title: `${timeline.name} Render`,
      });
      setRenderStatus(`Render job enqueued (${res.job_id}). Inspect in Exports tab.`);
    } catch (err: any) {
      setRenderStatus(`Render failed: ${err?.message || 'Unknown error'}`);
    }
  };

  // ---------------------------------------------------------------------------
  // Timecode formatting helper
  // ---------------------------------------------------------------------------

  const formatTimecode = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 30);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  };

  if (!currentProject) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-neutral-400">
        Please select a project to open the Timeline Editor.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-neutral-400">
        <Clock className="mr-2 h-5 w-5 animate-spin text-amber-500" />
        Loading sequence and multi-track timeline...
      </div>
    );
  }

  if (error || !timeline) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-red-400">
        <AlertTriangle className="mb-2 h-8 w-8" />
        <p className="font-semibold">{error || 'Timeline sequence could not be loaded.'}</p>
        <button
          onClick={loadTimelineData}
          className="mt-4 rounded bg-neutral-800 px-4 py-2 text-sm text-neutral-200 hover:bg-neutral-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const timelineDuration = Math.max(15, timeline.duration);
  const totalRulerWidth = timelineDuration * zoomLevel;

  return (
    <div className="flex h-full flex-col bg-neutral-950 text-neutral-100">
      {/* 1. Header Toolbar */}
      <div className="flex h-14 items-center justify-between border-b border-neutral-800 bg-neutral-900 px-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Layers className="h-5 w-5 text-amber-500" />
            <span className="font-semibold">{timeline.name}</span>
            <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
              Rev {timeline.revision}
            </span>
          </div>

          <div className="h-4 w-px bg-neutral-800" />

          {/* Timecode readout */}
          <div className="flex items-center space-x-1 font-mono text-sm text-amber-400">
            <Clock className="h-4 w-4" />
            <span>{formatTimecode(playheadTime)}</span>
            <span className="text-xs text-neutral-500">/ {formatTimecode(timeline.duration)}</span>
          </div>
        </div>

        {/* Operation buttons */}
        <div className="flex items-center space-x-2">
          {/* Undo / Redo */}
          <button
            onClick={handleUndo}
            disabled={!canUndo}
            title="Undo (Ctrl+Z)"
            className={`rounded p-1.5 transition-colors ${canUndo ? 'text-neutral-200 hover:bg-neutral-800' : 'text-neutral-600 cursor-not-allowed'}`}
          >
            <Undo2 className="h-4 w-4" />
          </button>
          <button
            onClick={handleRedo}
            disabled={!canRedo}
            title="Redo (Ctrl+Y)"
            className={`rounded p-1.5 transition-colors ${canRedo ? 'text-neutral-200 hover:bg-neutral-800' : 'text-neutral-600 cursor-not-allowed'}`}
          >
            <Redo2 className="h-4 w-4" />
          </button>

          <div className="h-4 w-px bg-neutral-800" />

          {/* Edit Actions */}
          <button
            onClick={handleSplitAtPlayhead}
            title="Split Clip at Playhead (S)"
            className="flex items-center space-x-1 rounded bg-neutral-800 px-2.5 py-1 text-xs text-neutral-200 hover:bg-neutral-700"
          >
            <Scissors className="h-3.5 w-3.5 text-amber-400" />
            <span>Split</span>
          </button>
          <button
            onClick={handleDuplicateSelected}
            disabled={!selectedClipId}
            title="Duplicate Selected Clip (D)"
            className={`flex items-center space-x-1 rounded px-2.5 py-1 text-xs transition-colors ${selectedClipId ? 'bg-neutral-800 text-neutral-200 hover:bg-neutral-700' : 'bg-neutral-900 text-neutral-600 cursor-not-allowed'}`}
          >
            <Copy className="h-3.5 w-3.5" />
            <span>Duplicate</span>
          </button>
          <button
            onClick={handleDeleteSelected}
            disabled={!selectedClipId}
            title="Delete Selected Clip (Del)"
            className={`flex items-center space-x-1 rounded px-2.5 py-1 text-xs transition-colors ${selectedClipId ? 'bg-red-950/60 text-red-300 hover:bg-red-900/80' : 'bg-neutral-900 text-neutral-600 cursor-not-allowed'}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Delete</span>
          </button>
          <button
            onClick={handleAddTextOverlay}
            title="Add Text Overlay"
            className="flex items-center space-x-1 rounded bg-amber-600/20 px-2.5 py-1 text-xs text-amber-300 hover:bg-amber-600/30"
          >
            <Type className="h-3.5 w-3.5" />
            <span>Add Text</span>
          </button>

          <div className="h-4 w-px bg-neutral-800" />

          {/* Render Timeline Button */}
          <button
            onClick={handleRenderTimeline}
            className="flex items-center space-x-1.5 rounded bg-gradient-to-r from-amber-500 to-amber-600 px-3 py-1.5 text-xs font-medium text-neutral-950 shadow hover:from-amber-400 hover:to-amber-500"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Render Video</span>
          </button>
        </div>
      </div>

      {/* Render status message */}
      {renderStatus && (
        <div className="flex items-center justify-between bg-amber-950/60 border-b border-amber-900/60 px-4 py-1.5 text-xs text-amber-200">
          <span>{renderStatus}</span>
          <button onClick={() => setRenderStatus(null)} className="hover:text-white">✕</button>
        </div>
      )}

      {/* 2. Main Middle Workspace: Preview Monitor & Side Panel */}
      <div className="flex flex-1 min-h-[300px] border-b border-neutral-800 overflow-hidden">
        {/* Left: Preview Monitor */}
        <div className="flex flex-1 flex-col items-center justify-center bg-neutral-900/60 p-4 relative">
          {/* Aspect Ratio & Controls Overlay */}
          <div className="absolute top-3 left-4 flex items-center space-x-2 z-10">
            <span className="text-xs text-neutral-400">Aspect Ratio:</span>
            <button
              onClick={() => setAspectRatio('9:16')}
              className={`rounded px-2 py-0.5 text-xs ${aspectRatio === '9:16' ? 'bg-amber-500 text-neutral-950 font-bold' : 'bg-neutral-800 text-neutral-400'}`}
            >
              9:16 Portrait
            </button>
            <button
              onClick={() => setAspectRatio('16:9')}
              className={`rounded px-2 py-0.5 text-xs ${aspectRatio === '16:9' ? 'bg-amber-500 text-neutral-950 font-bold' : 'bg-neutral-800 text-neutral-400'}`}
            >
              16:9 Landscape
            </button>
          </div>

          {/* Canvas Box */}
          <div
            className={`border border-neutral-700 bg-black rounded shadow-2xl relative flex flex-col items-center justify-center overflow-hidden transition-all duration-200 ${
              aspectRatio === '9:16' ? 'h-[280px] w-[158px]' : 'h-[220px] w-[391px]'
            }`}
          >
            {/* Visual representation of current playhead frame */}
            <div className="text-center p-2">
              <Film className="mx-auto h-8 w-8 text-neutral-700 mb-1" />
              <p className="text-[10px] text-neutral-400 font-mono">
                {selectedClip ? selectedClip.name : 'Sequence Preview'}
              </p>
              <p className="text-[9px] text-amber-500/80 font-mono mt-0.5">
                {playheadTime.toFixed(2)}s
              </p>
            </div>

            {/* Simulated overlays on canvas */}
            {timeline.tracks
              .filter((tr) => tr.is_visible && tr.track_type === 'overlay')
              .flatMap((tr) => tr.clips)
              .filter((cl) => cl.timeline_start <= playheadTime && playheadTime <= cl.timeline_end)
              .map((ov) => (
                <div
                  key={ov.id}
                  className="absolute bottom-6 left-2 right-2 rounded bg-black/60 px-2 py-1 text-center font-bold shadow text-white border border-amber-500/30 text-xs"
                  style={{ color: ov.content_props.color || '#FFFFFF' }}
                >
                  {ov.content_props.text}
                </div>
              ))}
          </div>

          {/* Transport Controls */}
          <div className="mt-3 flex items-center space-x-3">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500 text-neutral-950 shadow hover:bg-amber-400 transition"
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
            </button>
            <span className="text-xs font-mono text-neutral-400">
              {playheadTime.toFixed(2)}s
            </span>
          </div>
        </div>

        {/* Right Side Panel: Inspector & AI Assistant */}
        <div className="w-80 border-l border-neutral-800 bg-neutral-900 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-neutral-800">
            <button
              onClick={() => setActiveTab('inspector')}
              className={`flex-1 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'inspector'
                  ? 'border-amber-500 text-amber-400 bg-neutral-800/40'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Sliders className="inline mr-1.5 h-3.5 w-3.5" />
              Inspector
            </button>
            <button
              onClick={() => setActiveTab('ai')}
              className={`flex-1 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'ai'
                  ? 'border-amber-500 text-amber-400 bg-neutral-800/40'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Sparkles className="inline mr-1.5 h-3.5 w-3.5" />
              AI Editor
            </button>
          </div>

          {/* Inspector Tab Content */}
          {activeTab === 'inspector' && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {selectedClip ? (
                <>
                  <div>
                    <label className="text-neutral-400 font-semibold block mb-1">Clip Name</label>
                    <input
                      type="text"
                      value={selectedClip.name}
                      onChange={(e) =>
                        updateTimelineClipProps(currentProject.id, timeline.id, selectedClip.id, {
                          name: e.target.value,
                        }).then((up) => {
                          setTimeline((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  tracks: prev.tracks.map((tr) => ({
                                    ...tr,
                                    clips: tr.clips.map((c) => (c.id === up.id ? up : c)),
                                  })),
                                }
                              : null
                          );
                        })
                      }
                      className="w-full rounded bg-neutral-800 border border-neutral-700 px-2 py-1 text-neutral-100 text-xs"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-neutral-400 block mb-0.5">Start Time</span>
                      <span className="font-mono text-neutral-200">{selectedClip.timeline_start.toFixed(2)}s</span>
                    </div>
                    <div>
                      <span className="text-neutral-400 block mb-0.5">Duration</span>
                      <span className="font-mono text-neutral-200">{getClipDuration(selectedClip).toFixed(2)}s</span>
                    </div>
                  </div>

                  {/* Volume Slider */}
                  <div>
                    <div className="flex justify-between text-neutral-400 mb-1">
                      <span>Audio Volume</span>
                      <span>{Math.round(selectedClip.volume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.05"
                      value={selectedClip.volume}
                      onChange={(e) =>
                        updateTimelineClipProps(currentProject.id, timeline.id, selectedClip.id, {
                          volume: parseFloat(e.target.value),
                        }).then((up) => {
                          setTimeline((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  tracks: prev.tracks.map((tr) => ({
                                    ...tr,
                                    clips: tr.clips.map((c) => (c.id === up.id ? up : c)),
                                  })),
                                }
                              : null
                          );
                        })
                      }
                      className="w-full accent-amber-500"
                    />
                  </div>

                  {/* Speed Slider */}
                  <div>
                    <div className="flex justify-between text-neutral-400 mb-1">
                      <span>Playback Speed</span>
                      <span>{selectedClip.speed}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="2"
                      step="0.1"
                      value={selectedClip.speed}
                      onChange={(e) =>
                        updateTimelineClipProps(currentProject.id, timeline.id, selectedClip.id, {
                          speed: parseFloat(e.target.value),
                        }).then((up) => {
                          setTimeline((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  tracks: prev.tracks.map((tr) => ({
                                    ...tr,
                                    clips: tr.clips.map((c) => (c.id === up.id ? up : c)),
                                  })),
                                }
                              : null
                          );
                        })
                      }
                      className="w-full accent-amber-500"
                    />
                  </div>

                  {/* Text Overlay Properties */}
                  {selectedClip.clip_type === 'text' && (
                    <div className="border-t border-neutral-800 pt-3 space-y-3">
                      <span className="font-semibold text-amber-400 block">Text Overlay</span>
                      <div>
                        <label className="text-neutral-400 block mb-1">Text Content</label>
                        <textarea
                          rows={2}
                          value={selectedClip.content_props.text}
                          onChange={(e) =>
                            updateTimelineClipProps(currentProject.id, timeline.id, selectedClip.id, {
                              content_props: { ...selectedClip.content_props, text: e.target.value },
                            }).then((up) => {
                              setTimeline((prev) =>
                                prev
                                  ? {
                                      ...prev,
                                      tracks: prev.tracks.map((tr) => ({
                                        ...tr,
                                        clips: tr.clips.map((c) => (c.id === up.id ? up : c)),
                                      })),
                                    }
                                  : null
                              );
                            })
                          }
                          className="w-full rounded bg-neutral-800 border border-neutral-700 px-2 py-1 text-neutral-100 text-xs"
                        />
                      </div>
                      <div className="flex items-center space-x-2">
                        <label className="text-neutral-400">Color:</label>
                        <input
                          type="color"
                          value={selectedClip.content_props.color || '#FFFFFF'}
                          onChange={(e) =>
                            updateTimelineClipProps(currentProject.id, timeline.id, selectedClip.id, {
                              content_props: { ...selectedClip.content_props, color: e.target.value },
                            }).then((up) => {
                              setTimeline((prev) =>
                                prev
                                  ? {
                                      ...prev,
                                      tracks: prev.tracks.map((tr) => ({
                                        ...tr,
                                        clips: tr.clips.map((c) => (c.id === up.id ? up : c)),
                                      })),
                                    }
                                  : null
                              );
                            })
                          }
                          className="h-6 w-8 rounded border border-neutral-700 bg-transparent cursor-pointer"
                        />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-neutral-500">
                  Select a clip on the timeline to inspect and edit properties.
                </div>
              )}
            </div>
          )}

          {/* AI Editor Tab Content */}
          {activeTab === 'ai' && (
            <div className="flex flex-1 flex-col overflow-hidden">
              {/* Message Feed */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 text-xs">
                {aiConversation?.messages.map((m) => (
                  <div
                    key={m.id}
                    className={`rounded p-2.5 max-w-[90%] ${
                      m.role === 'user'
                        ? 'ml-auto bg-amber-600/30 text-amber-100 border border-amber-500/30'
                        : 'bg-neutral-800/80 text-neutral-200 border border-neutral-700'
                    }`}
                  >
                    <div className="text-[10px] text-neutral-400 mb-0.5 font-semibold">
                      {m.role === 'user' ? 'You' : 'ZezEdit AI'}
                    </div>
                    <div>{m.content}</div>

                    {/* Proposed Plan Box */}
                    {m.plan && m.plan.status === 'proposed' && (
                      <div className="mt-2.5 rounded bg-neutral-900 border border-amber-500/40 p-2.5 space-y-2">
                        <div className="flex items-center text-amber-400 font-semibold text-[11px]">
                          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                          Proposed Editing Plan
                        </div>
                        <p className="text-neutral-300 text-[10px]">{m.plan.explanation}</p>

                        {/* Operations list */}
                        <div className="space-y-1">
                          {m.plan.operations.map((op, idx) => (
                            <div key={idx} className="rounded bg-neutral-800 px-2 py-1 text-[10px] text-neutral-300">
                              • {op.description}
                            </div>
                          ))}
                        </div>

                        {/* Warnings */}
                        {m.plan.warnings.length > 0 && (
                          <div className="flex items-start text-amber-400/90 text-[10px]">
                            <AlertTriangle className="mr-1 h-3.5 w-3.5 shrink-0" />
                            <span>{m.plan.warnings.join(' ')}</span>
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex space-x-2 pt-1">
                          <button
                            onClick={() => handleApprovePlan(m.plan!.id)}
                            className="flex-1 rounded bg-amber-500 py-1 text-center font-semibold text-neutral-950 hover:bg-amber-400"
                          >
                            Approve & Execute
                          </button>
                          <button
                            onClick={() => handleRejectPlan(m.plan!.id)}
                            className="rounded bg-neutral-800 px-3 py-1 text-neutral-400 hover:text-white"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {aiLoading && (
                  <div className="flex items-center space-x-2 text-neutral-400 text-xs py-2">
                    <Sparkles className="h-4 w-4 animate-spin text-amber-400" />
                    <span>ZezEdit AI is analyzing sequence...</span>
                  </div>
                )}
              </div>

              {/* Suggestions Chips */}
              <div className="border-t border-neutral-800 p-2 flex flex-wrap gap-1.5 bg-neutral-900/60">
                <button
                  onClick={() => handleSendAIMessage('Split clip at playhead')}
                  className="rounded-full bg-neutral-800 hover:bg-neutral-700 px-2.5 py-0.5 text-[10px] text-neutral-300"
                >
                  Split at playhead
                </button>
                <button
                  onClick={() => handleSendAIMessage('Add text overlay "Watch this!"')}
                  className="rounded-full bg-neutral-800 hover:bg-neutral-700 px-2.5 py-0.5 text-[10px] text-neutral-300"
                >
                  Add text overlay
                </button>
                <button
                  onClick={() => handleSendAIMessage('Shorten this clip')}
                  className="rounded-full bg-neutral-800 hover:bg-neutral-700 px-2.5 py-0.5 text-[10px] text-neutral-300"
                >
                  Shorten clip
                </button>
              </div>

              {/* Input Area */}
              <div className="border-t border-neutral-800 p-2 flex items-center space-x-2 bg-neutral-900">
                <input
                  type="text"
                  placeholder="Ask AI to trim, split, add text..."
                  value={aiInput}
                  onChange={(e) => setAiInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendAIMessage()}
                  className="flex-1 rounded bg-neutral-800 border border-neutral-700 px-2.5 py-1.5 text-xs text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
                <button
                  onClick={() => handleSendAIMessage()}
                  disabled={aiLoading || !aiInput.trim()}
                  className="rounded bg-amber-500 p-1.5 text-neutral-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. Bottom: Multi-Track Timeline Canvas */}
      <div className="h-64 flex flex-col bg-neutral-950 select-none overflow-hidden">
        {/* Timeline Control Strip */}
        <div className="flex h-8 items-center justify-between border-b border-neutral-800 bg-neutral-900/80 px-4 text-xs text-neutral-400">
          <div className="flex items-center space-x-3">
            <span className="font-semibold text-neutral-300">Tracks ({timeline.tracks.length})</span>
            <button
              onClick={() => handleAddTrack('video')}
              className="hover:text-amber-400 flex items-center space-x-1"
            >
              <Plus className="h-3 w-3" />
              <span>Video</span>
            </button>
            <button
              onClick={() => handleAddTrack('audio')}
              className="hover:text-amber-400 flex items-center space-x-1"
            >
              <Plus className="h-3 w-3" />
              <span>Audio</span>
            </button>
            <button
              onClick={() => handleAddTrack('overlay')}
              className="hover:text-amber-400 flex items-center space-x-1"
            >
              <Plus className="h-3 w-3" />
              <span>Overlay</span>
            </button>
          </div>

          <div className="flex items-center space-x-4">
            {/* Snapping */}
            <button
              onClick={() => setSnapping(!snapping)}
              className={`flex items-center space-x-1 ${snapping ? 'text-amber-400' : 'text-neutral-500'}`}
            >
              <span>Snap</span>
            </button>

            {/* Zoom */}
            <div className="flex items-center space-x-1">
              <ZoomOut
                className="h-3.5 w-3.5 cursor-pointer hover:text-white"
                onClick={() => setZoomLevel((z) => Math.max(20, z - 10))}
              />
              <input
                type="range"
                min="20"
                max="120"
                value={zoomLevel}
                onChange={(e) => setZoomLevel(parseInt(e.target.value))}
                className="w-16 accent-amber-500"
              />
              <ZoomIn
                className="h-3.5 w-3.5 cursor-pointer hover:text-white"
                onClick={() => setZoomLevel((z) => Math.min(120, z + 10))}
              />
            </div>
          </div>
        </div>

        {/* Tracks + Lanes Container */}
        <div className="flex flex-1 overflow-x-auto overflow-y-auto" ref={timelineContainerRef}>
          {/* Track Headers (Fixed left column) */}
          <div className="w-48 shrink-0 border-r border-neutral-800 bg-neutral-900/90 z-20">
            {/* Ruler header spacer */}
            <div className="h-6 border-b border-neutral-800 bg-neutral-900 px-3 flex items-center text-[10px] text-neutral-500">
              TRACKS
            </div>

            {/* Headers for each track */}
            {timeline.tracks.map((tr) => (
              <div
                key={tr.id}
                className="flex h-14 items-center justify-between border-b border-neutral-800 px-3 hover:bg-neutral-800/40"
              >
                <div className="flex items-center space-x-2 truncate">
                  {tr.track_type === 'video' ? (
                    <Film className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                  ) : tr.track_type === 'audio' ? (
                    <Volume2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Type className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                  )}
                  <span className="text-xs font-medium truncate text-neutral-200">{tr.name}</span>
                </div>

                {/* Track control buttons */}
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleToggleTrackMute(tr)}
                    className={`p-1 hover:text-white ${tr.is_muted ? 'text-red-400' : 'text-neutral-500'}`}
                  >
                    {tr.is_muted ? <VolumeX className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
                  </button>
                  <button
                    onClick={() => handleToggleTrackLock(tr)}
                    className={`p-1 hover:text-white ${tr.is_locked ? 'text-amber-400' : 'text-neutral-500'}`}
                  >
                    {tr.is_locked ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                  </button>
                  <button
                    onClick={() => handleToggleTrackVisibility(tr)}
                    className={`p-1 hover:text-white ${tr.is_visible ? 'text-neutral-400' : 'text-neutral-600'}`}
                  >
                    {tr.is_visible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                  </button>
                  <button
                    onClick={() => {
                      setTargetTrackForAdd(tr.id);
                      setShowMediaModal(true);
                    }}
                    title="Add Media to Track"
                    className="p-1 text-neutral-400 hover:text-amber-400"
                  >
                    <Plus className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => handleDeleteTrack(tr.id)}
                    title="Delete Track"
                    className="p-1 text-neutral-500 hover:text-red-400"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Timeline Lanes & Canvas */}
          <div
            className="flex-1 relative bg-neutral-950 overflow-x-visible cursor-pointer"
            style={{ width: `${totalRulerWidth}px` }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - rect.left;
              const newTime = Math.max(0, clickX / zoomLevel);
              setPlayheadTime(newTime);
            }}
          >
            {/* Time Ruler */}
            <div className="h-6 border-b border-neutral-800 bg-neutral-900/50 flex relative">
              {Array.from({ length: Math.ceil(timelineDuration) + 1 }).map((_, sec) => (
                <div
                  key={sec}
                  className="absolute top-0 bottom-0 border-l border-neutral-800 text-[9px] font-mono text-neutral-500 pl-1"
                  style={{ left: `${sec * zoomLevel}px` }}
                >
                  {sec % 5 === 0 ? `${sec}s` : ''}
                </div>
              ))}
            </div>

            {/* Playhead Vertical Line */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-500 z-30 pointer-events-none"
              style={{ left: `${playheadTime * zoomLevel}px` }}
            >
              <div className="w-3 h-3 bg-amber-500 -ml-[5px] rotate-45" />
            </div>

            {/* Track Lanes */}
            {timeline.tracks.map((tr) => (
              <div
                key={tr.id}
                className="h-14 border-b border-neutral-850 relative flex items-center"
              >
                {/* Clips in this track */}
                {tr.clips.map((clip) => {
                  const left = clip.timeline_start * zoomLevel;
                  const width = Math.max(12, getClipDuration(clip) * zoomLevel);
                  const isSelected = clip.id === selectedClipId;

                  let bgColor = 'bg-blue-900/80 border-blue-500/50 text-blue-100';
                  if (clip.clip_type === 'audio') {
                    bgColor = 'bg-emerald-950/80 border-emerald-500/50 text-emerald-100';
                  } else if (clip.clip_type === 'text') {
                    bgColor = 'bg-amber-950/80 border-amber-500/50 text-amber-100';
                  }

                  return (
                    <div
                      key={clip.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedClipId(clip.id);
                        setSelectedTrackId(tr.id);
                      }}
                      className={`absolute top-1 bottom-1 rounded border px-2 flex items-center justify-between text-xs overflow-hidden select-none cursor-pointer transition shadow-sm ${bgColor} ${
                        isSelected ? 'ring-2 ring-white ring-offset-1 ring-offset-neutral-950' : ''
                      }`}
                      style={{ left: `${left}px`, width: `${width}px` }}
                    >
                      <span className="truncate font-medium text-[11px]">{clip.name}</span>
                      <span className="text-[9px] opacity-70 shrink-0 ml-1 font-mono">
                        {getClipDuration(clip).toFixed(1)}s
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Media Picker Modal */}
      {showMediaModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-lg max-w-lg w-full p-4 space-y-4">
            <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
              <span className="font-semibold text-neutral-100">Add Asset to Track</span>
              <button onClick={() => setShowMediaModal(false)} className="text-neutral-400 hover:text-white">✕</button>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {mediaAssets.map((m) => (
                <div
                  key={m.id}
                  onClick={() => handleInsertMediaClip(m)}
                  className="flex items-center justify-between p-2 rounded bg-neutral-800 hover:bg-neutral-700 cursor-pointer text-xs"
                >
                  <div className="flex items-center space-x-2">
                    <FileVideo className="h-4 w-4 text-amber-400" />
                    <span className="text-neutral-200">{m.original_filename}</span>
                  </div>
                  <span className="text-neutral-400 font-mono">{(Number(m.duration_seconds) || 0).toFixed(1)}s</span>
                </div>
              ))}
              {mediaAssets.length === 0 && (
                <p className="text-center text-xs text-neutral-500 py-4">No media assets in project.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
