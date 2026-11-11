import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Download,
  Eye,
  Film,
  Play,
  RefreshCw,
  Scissors,
  Sparkles,
  Trash2,
  Volume2,
  X,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  cancelExportRender,
  deleteExport,
  fetchExportPresets,
  fetchJob,
  fetchProjectExports,
  fetchProjectHighlights,
  getExportVideoUrl,
  submitExportPreview,
  submitExportRender,
} from '../../services/apiClient';
import {
  AudioConfigItem,
  CaptionConfigItem,
  CaptionMode,
  ExportItem,
  ExportPresetItem,
  RenderExportPayload,
} from '../../types/exports';
import { CandidateItem } from '../../types/highlights';
import { JobItem, MediaAssetItem } from '../../types/projects';

interface ExportStudioProps {
  projectId: string;
  mediaAssets?: MediaAssetItem[];
  preselectedCandidateId?: string;
  onNavigateToHighlights?: () => void;
  onNavigateToReframing?: (assetId: string) => void;
}

const DEFAULT_CAPTION_CONFIG: CaptionConfigItem = {
  mode: 'word_highlight',
  font_family: 'Arial',
  font_size: 24,
  bold: true,
  text_color: '#FFFFFF',
  highlight_color: '#FACC15',
  outline_color: '#000000',
  outline_width: 2.5,
  shadow_depth: 1.5,
  alignment: 2,
  margin_v: 90,
  max_words_per_line: 5,
  max_lines: 2,
  burn_in: true,
};

const DEFAULT_AUDIO_CONFIG: AudioConfigItem = {
  volume: 1.0,
  fade_in_seconds: 0.2,
  fade_out_seconds: 0.2,
  normalize_loudness: false,
  sample_rate: 48000,
  channels: 2,
};

export const ExportStudio: React.FC<ExportStudioProps> = ({
  projectId,
  mediaAssets: _mediaAssets = [],
  preselectedCandidateId,
  onNavigateToHighlights,
  onNavigateToReframing: _onNavigateToReframing,
}) => {
  // State: Candidates & Presets
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>(preselectedCandidateId || '');
  const [presets, setPresets] = useState<ExportPresetItem[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('shorts_reels_9_16');

  // State: Custom Render Config
  const [captionConfig, setCaptionConfig] = useState<CaptionConfigItem>(DEFAULT_CAPTION_CONFIG);
  const [audioConfig, setAudioConfig] = useState<AudioConfigItem>(DEFAULT_AUDIO_CONFIG);
  const [crf, setCrf] = useState<number>(22);
  const [customTitle, setCustomTitle] = useState<string>('');

  // State: Active Job & Exports History
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);
  const [activeExportId, setActiveExportId] = useState<string | null>(null);
  const [exportsList, setExportsList] = useState<ExportItem[]>([]);
  const [selectedExport, setSelectedExport] = useState<ExportItem | null>(null);

  // State: UI Status
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeConfigTab, setActiveConfigTab] = useState<'preset' | 'captions' | 'audio'>('preset');

  // 1. Initial Load: Presets, Candidates, and Past Exports
  const loadStudioData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const [presetsRes, highlightsRes, exportsRes] = await Promise.all([
        fetchExportPresets(projectId).catch(() => []),
        fetchProjectHighlights(projectId).catch(() => ({ total_candidates: 0, candidates: [] } as any)),
        fetchProjectExports(projectId).catch(() => ({ items: [], count: 0 })),
      ]);

      setPresets(presetsRes);
      const cList: CandidateItem[] = highlightsRes?.candidates || [];
      const approvedOrAll = cList.filter(
        (c: CandidateItem) => c.review_status === 'approved' || c.queued_for_render
      );
      setCandidates(approvedOrAll.length > 0 ? approvedOrAll : cList);

      if (!selectedCandidateId && approvedOrAll.length > 0) {
        setSelectedCandidateId(approvedOrAll[0].id);
      } else if (!selectedCandidateId && cList.length > 0) {
        setSelectedCandidateId(cList[0].id);
      }

      setExportsList(exportsRes.items);
      if (exportsRes.items.length > 0 && !selectedExport) {
        setSelectedExport(exportsRes.items[0]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load Export Studio data');
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedCandidateId, selectedExport]);

  useEffect(() => {
    loadStudioData();
  }, [loadStudioData]);

  // 2. Poll Active Job Progress
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed' || activeJob.status === 'cancelled') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await fetchJob(activeJob.id);
        setActiveJob(updated);

        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
          // Refresh exports list to show finished video
          const exportsRes = await fetchProjectExports(projectId);
          setExportsList(exportsRes.items);
          if (activeExportId) {
            const exp = exportsRes.items.find((e) => e.id === activeExportId);
            if (exp) setSelectedExport(exp);
          }
        }
      } catch (err) {
        console.error('Job polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeJob, activeExportId, projectId]);

  // 3. Render Handlers
  const handleStartRender = async (isPreview: boolean = false) => {
    if (!selectedCandidateId) {
      setErrorMessage('Please select an approved candidate to render.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    try {
      const payload: RenderExportPayload = {
        candidate_id: selectedCandidateId,
        preset_id: selectedPresetId,
        caption_config: captionConfig,
        audio_config: audioConfig,
        crf,
        title: customTitle.trim() || undefined,
        is_preview: isPreview,
      };

      const res = isPreview
        ? await submitExportPreview(projectId, payload)
        : await submitExportRender(projectId, payload, false);

      setActiveExportId(res.export_id);

      // Start tracking job
      const initialJob = await fetchJob(res.job_id);
      setActiveJob(initialJob);

      // Refresh list
      const exportsRes = await fetchProjectExports(projectId);
      setExportsList(exportsRes.items);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start export render job');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelRender = async () => {
    if (!activeExportId) return;
    try {
      await cancelExportRender(projectId, activeExportId);
      if (activeJob) {
        const updated = await fetchJob(activeJob.id);
        setActiveJob(updated);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to cancel render');
    }
  };

  const handleDeleteExport = async (exportId: string) => {
    if (!window.confirm('Delete this exported video file permanently?')) return;
    try {
      await deleteExport(projectId, exportId);
      setExportsList((prev) => prev.filter((e) => e.id !== exportId));
      if (selectedExport?.id === exportId) {
        setSelectedExport(null);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete export');
    }
  };

  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);
  const selectedPreset = presets.find((p) => p.preset_id === selectedPresetId);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Header Toolbar */}
      <div className="border-b border-border bg-surface px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Film className="w-5 h-5 text-brand" />
            <h1 className="text-lg font-semibold text-text-primary">Shorts Rendering & Export Studio</h1>
            <Badge variant="purple">Milestone 8</Badge>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Turn approved candidates into high-impact vertical 9:16 Shorts with dynamic crop, styled captions, and audio.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={loadStudioData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {onNavigateToHighlights && (
            <Button variant="outline" size="sm" onClick={onNavigateToHighlights}>
              <Scissors className="w-3.5 h-3.5 mr-1.5" />
              Highlights Studio
            </Button>
          )}
        </div>
      </div>

      {/* Main Workspace Split Layout */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Panel: Render Configuration */}
        <div className="w-full lg:w-[480px] xl:w-[520px] border-r border-border bg-surface flex flex-col h-full overflow-y-auto p-6 space-y-6">
          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button onClick={() => setErrorMessage(null)} className="p-1 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* 1. Candidate Selection */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-text-secondary flex items-center justify-between">
              <span>Select Candidate Clip</span>
              <span className="text-[11px] text-brand">
                {candidates.length} Available
              </span>
            </label>

            <select
              className="w-full text-xs bg-surface-card border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-brand"
              value={selectedCandidateId}
              onChange={(e) => setSelectedCandidateId(e.target.value)}
            >
              {candidates.length === 0 && <option value="">No approved candidates available</option>}
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title || c.suggested_title} ({c.duration.toFixed(1)}s, Score: {Math.round(c.quality_score)})
                </option>
              ))}
            </select>

            {selectedCandidate && (
              <div className="p-3 rounded-lg bg-surface-card/60 border border-border/60 text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text-primary truncate">
                    {selectedCandidate.title || selectedCandidate.suggested_title}
                  </span>
                  <Badge variant={selectedCandidate.review_status === 'approved' ? 'purple' : 'warning'}>
                    {selectedCandidate.review_status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-text-muted font-mono">
                  <span>Interval: {selectedCandidate.start_time.toFixed(1)}s - {selectedCandidate.end_time.toFixed(1)}s</span>
                  <span>Duration: {selectedCandidate.duration.toFixed(1)}s</span>
                  <span>Score: {Math.round(selectedCandidate.quality_score)}/100</span>
                </div>
              </div>
            )}
          </div>

          {/* 2. Configuration Tabs */}
          <div className="border border-border rounded-xl bg-surface-card overflow-hidden">
            <div className="flex border-b border-border bg-surface/50">
              <button
                className={`flex-1 py-2 text-xs font-medium border-b-2 transition ${
                  activeConfigTab === 'preset'
                    ? 'border-brand text-brand bg-brand/5'
                    : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
                onClick={() => setActiveConfigTab('preset')}
              >
                1. Preset & Aspect
              </button>
              <button
                className={`flex-1 py-2 text-xs font-medium border-b-2 transition ${
                  activeConfigTab === 'captions'
                    ? 'border-brand text-brand bg-brand/5'
                    : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
                onClick={() => setActiveConfigTab('captions')}
              >
                2. Captions & Style
              </button>
              <button
                className={`flex-1 py-2 text-xs font-medium border-b-2 transition ${
                  activeConfigTab === 'audio'
                    ? 'border-brand text-brand bg-brand/5'
                    : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
                onClick={() => setActiveConfigTab('audio')}
              >
                3. Audio & Volume
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* TAB 1: Preset & Aspect Ratio */}
              {activeConfigTab === 'preset' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-medium text-text-secondary">Export Profile</label>
                      {selectedPreset && (
                        <span className="text-[11px] font-mono text-brand">
                          {selectedPreset.target_width}x{selectedPreset.target_height} ({selectedPreset.target_aspect_ratio})
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {presets.map((p) => {
                        const isSelected = selectedPresetId === p.preset_id;
                        return (
                          <div
                            key={p.preset_id}
                            onClick={() => setSelectedPresetId(p.preset_id)}
                            className={`p-3 rounded-lg border cursor-pointer transition flex items-center justify-between ${
                              isSelected
                                ? 'bg-brand/10 border-brand text-brand'
                                : 'bg-surface border-border hover:border-border-hover text-text-primary'
                            }`}
                          >
                            <div>
                              <div className="text-xs font-semibold">{p.name}</div>
                              <div className="text-[11px] text-text-muted mt-0.5">
                                {p.target_width}x{p.target_height} ({p.target_aspect_ratio}) • {p.video_codec} • {p.fps} fps
                              </div>
                            </div>
                            {isSelected && <Check className="w-4 h-4 text-brand" />}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Quality CRF */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-text-secondary">Visual Quality (CRF)</span>
                      <span className="font-mono text-brand font-semibold">
                        {crf} {crf <= 18 ? '(Near Lossless)' : crf <= 23 ? '(High Quality)' : '(Compact)'}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={16}
                      max={28}
                      step={1}
                      value={crf}
                      onChange={(e) => setCrf(Number(e.target.value))}
                      className="w-full h-1.5 bg-surface rounded-lg appearance-none cursor-pointer accent-brand"
                    />
                  </div>

                  {/* Custom Title */}
                  <div className="space-y-1.5">
                    <label className="text-xs text-text-secondary">Custom Output Title (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. My_Epic_Moment"
                      value={customTitle}
                      onChange={(e) => setCustomTitle(e.target.value)}
                      className="w-full text-xs bg-surface border border-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-brand"
                    />
                  </div>
                </div>
              )}

              {/* TAB 2: Captions & Style */}
              {activeConfigTab === 'captions' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-text-secondary">Caption Display Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { mode: 'word_highlight', label: 'Word Highlight', desc: 'Modern TikTok karaoke style' },
                        { mode: 'phrase', label: 'Phrase Bursts', desc: '3-5 words at a time' },
                        { mode: 'sentence', label: 'Sentence View', desc: 'Full speech turns' },
                        { mode: 'none', label: 'No Captions', desc: 'Clean video only' },
                      ].map((item) => (
                        <button
                          key={item.mode}
                          onClick={() => setCaptionConfig({ ...captionConfig, mode: item.mode as CaptionMode })}
                          className={`p-2.5 rounded-lg border text-left transition ${
                            captionConfig.mode === item.mode
                              ? 'bg-brand/10 border-brand text-brand'
                              : 'bg-surface border-border hover:border-border-hover text-text-secondary'
                          }`}
                        >
                          <div className="text-xs font-semibold">{item.label}</div>
                          <div className="text-[10px] text-text-muted mt-0.5">{item.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {captionConfig.mode !== 'none' && (
                    <>
                      {/* Font size and family */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] text-text-secondary">Font Family</label>
                          <select
                            value={captionConfig.font_family}
                            onChange={(e) => setCaptionConfig({ ...captionConfig, font_family: e.target.value })}
                            className="w-full text-xs bg-surface border border-border rounded px-2 py-1 text-text-primary"
                          >
                            <option value="Arial">Arial</option>
                            <option value="Impact">Impact</option>
                            <option value="Montserrat">Montserrat</option>
                            <option value="Inter">Inter</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] text-text-secondary">Font Size ({captionConfig.font_size}px)</label>
                          <input
                            type="range"
                            min={16}
                            max={42}
                            value={captionConfig.font_size}
                            onChange={(e) => setCaptionConfig({ ...captionConfig, font_size: Number(e.target.value) })}
                            className="w-full h-1.5 bg-surface rounded appearance-none cursor-pointer accent-brand mt-2"
                          />
                        </div>
                      </div>

                      {/* Colors */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] text-text-secondary">Text Color</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="color"
                              value={captionConfig.text_color}
                              onChange={(e) => setCaptionConfig({ ...captionConfig, text_color: e.target.value })}
                              className="w-7 h-7 rounded border border-border cursor-pointer bg-transparent"
                            />
                            <span className="font-mono text-xs">{captionConfig.text_color}</span>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] text-text-secondary">Highlight Color</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="color"
                              value={captionConfig.highlight_color}
                              onChange={(e) => setCaptionConfig({ ...captionConfig, highlight_color: e.target.value })}
                              className="w-7 h-7 rounded border border-border cursor-pointer bg-transparent"
                            />
                            <span className="font-mono text-xs">{captionConfig.highlight_color}</span>
                          </div>
                        </div>
                      </div>

                      {/* Safe Margin Slider */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-text-secondary">Bottom Margin Safe Offset</span>
                          <span className="font-mono text-text-primary">{captionConfig.margin_v}px</span>
                        </div>
                        <input
                          type="range"
                          min={40}
                          max={240}
                          value={captionConfig.margin_v}
                          onChange={(e) => setCaptionConfig({ ...captionConfig, margin_v: Number(e.target.value) })}
                          className="w-full h-1.5 bg-surface rounded appearance-none cursor-pointer accent-brand"
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* TAB 3: Audio & Volume */}
              {activeConfigTab === 'audio' && (
                <div className="space-y-4">
                  {/* Volume Slider */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-text-secondary flex items-center gap-1.5">
                        <Volume2 className="w-3.5 h-3.5" /> Source Volume
                      </span>
                      <span className="font-mono text-brand font-semibold">
                        {Math.round(audioConfig.volume * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0.0}
                      max={2.0}
                      step={0.05}
                      value={audioConfig.volume}
                      onChange={(e) => setAudioConfig({ ...audioConfig, volume: Number(e.target.value) })}
                      className="w-full h-1.5 bg-surface rounded appearance-none cursor-pointer accent-brand"
                    />
                  </div>

                  {/* Fades */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[11px] text-text-secondary">Fade In: {audioConfig.fade_in_seconds}s</label>
                      <input
                        type="range"
                        min={0.0}
                        max={2.0}
                        step={0.1}
                        value={audioConfig.fade_in_seconds}
                        onChange={(e) => setAudioConfig({ ...audioConfig, fade_in_seconds: Number(e.target.value) })}
                        className="w-full h-1.5 bg-surface rounded appearance-none cursor-pointer accent-brand mt-1"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] text-text-secondary">Fade Out: {audioConfig.fade_out_seconds}s</label>
                      <input
                        type="range"
                        min={0.0}
                        max={2.0}
                        step={0.1}
                        value={audioConfig.fade_out_seconds}
                        onChange={(e) => setAudioConfig({ ...audioConfig, fade_out_seconds: Number(e.target.value) })}
                        className="w-full h-1.5 bg-surface rounded appearance-none cursor-pointer accent-brand mt-1"
                      />
                    </div>
                  </div>

                  {/* Loudness Normalization */}
                  <div className="p-3 rounded-lg bg-surface border border-border flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-text-primary">EBU R128 Loudness Normalization</div>
                      <div className="text-[10px] text-text-muted mt-0.5">
                        Ensures consistent, clear volume across mobile devices
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={audioConfig.normalize_loudness}
                      onChange={(e) => setAudioConfig({ ...audioConfig, normalize_loudness: e.target.checked })}
                      className="w-4 h-4 rounded border-border text-brand focus:ring-0 cursor-pointer"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-2 flex flex-col gap-2">
            <Button
              variant="primary"
              size="lg"
              onClick={() => handleStartRender(false)}
              disabled={submitting || !selectedCandidateId || activeJob?.status === 'running'}
              className="w-full"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Start Full Render Export (1080p)
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStartRender(true)}
              disabled={submitting || !selectedCandidateId || activeJob?.status === 'running'}
              className="w-full text-xs"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" />
              Generate Fast Low-Res Preview (480p)
            </Button>
          </div>
        </div>

        {/* Right Panel: Active Monitor & Export Output Player */}
        <div className="flex-1 flex flex-col h-full overflow-y-auto p-6 space-y-6 bg-background">
          {/* Active Job Monitor Card */}
          {activeJob && (activeJob.status === 'running' || activeJob.status === 'queued') && (
            <div className="p-5 rounded-xl border border-brand/40 bg-brand/5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-brand animate-spin" />
                  <span className="text-sm font-semibold text-text-primary">
                    Rendering Video Export...
                  </span>
                  <Badge variant="purple">{activeJob.current_stage || 'rendering_video'}</Badge>
                </div>
                <Button variant="danger" size="sm" onClick={handleCancelRender}>
                  <X className="w-3.5 h-3.5 mr-1" /> Cancel
                </Button>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-text-muted">Progress</span>
                  <span className="text-brand font-bold">{Math.round(activeJob.progress_pct)}%</span>
                </div>
                <div className="w-full h-2.5 bg-surface-card rounded-full overflow-hidden border border-border">
                  <div
                    className="h-full bg-brand transition-all duration-300 rounded-full"
                    style={{ width: `${Math.max(5, activeJob.progress_pct)}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Video Player Display */}
          <div className="border border-border rounded-xl bg-surface-card overflow-hidden p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Play className="w-4 h-4 text-brand" />
                <h2 className="text-sm font-semibold text-text-primary">
                  {selectedExport ? selectedExport.title : 'Export Preview Player'}
                </h2>
              </div>

              {selectedExport && (
                <div className="flex items-center gap-2">
                  <Badge variant={selectedExport.validation_status === 'valid' ? 'success' : 'warning'}>
                    {selectedExport.validation_status === 'valid' ? 'FFprobe Verified' : 'Unvalidated'}
                  </Badge>
                  <a
                    href={getExportVideoUrl(projectId, selectedExport.id)}
                    download={selectedExport.output_filename}
                    className="p-1.5 rounded-lg border border-border hover:bg-surface text-text-secondary transition text-xs flex items-center gap-1"
                    title="Download exported video"
                  >
                    <Download className="w-3.5 h-3.5" /> Download
                  </a>
                </div>
              )}
            </div>

            {/* Video Viewport Container */}
            <div className="relative bg-black/95 rounded-lg flex items-center justify-center min-h-[360px] max-h-[500px] overflow-hidden">
              {selectedExport && selectedExport.status === 'completed' ? (
                <video
                  key={selectedExport.id}
                  src={getExportVideoUrl(projectId, selectedExport.id)}
                  controls
                  className="max-h-[480px] max-w-full rounded object-contain shadow-lg"
                />
              ) : (
                <div className="text-center p-8 text-text-muted space-y-2">
                  <Film className="w-10 h-10 mx-auto text-text-muted/40" />
                  <p className="text-xs">
                    {activeJob?.status === 'running'
                      ? 'Video is currently rendering...'
                      : 'No export selected. Choose a candidate and start render to preview the final video.'}
                  </p>
                </div>
              )}
            </div>

            {/* Output Metadata Pills */}
            {selectedExport && selectedExport.status === 'completed' && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
                <div className="p-2 rounded bg-surface border border-border">
                  <div className="text-[10px] text-text-muted">Resolution</div>
                  <div className="font-mono font-semibold text-text-primary mt-0.5">
                    {selectedExport.target_width}x{selectedExport.target_height}
                  </div>
                </div>
                <div className="p-2 rounded bg-surface border border-border">
                  <div className="text-[10px] text-text-muted">Duration</div>
                  <div className="font-mono font-semibold text-text-primary mt-0.5">
                    {selectedExport.duration_seconds.toFixed(2)}s
                  </div>
                </div>
                <div className="p-2 rounded bg-surface border border-border">
                  <div className="text-[10px] text-text-muted">File Size</div>
                  <div className="font-mono font-semibold text-text-primary mt-0.5">
                    {(selectedExport.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </div>
                <div className="p-2 rounded bg-surface border border-border">
                  <div className="text-[10px] text-text-muted">Codec</div>
                  <div className="font-mono font-semibold text-text-primary mt-0.5">
                    {selectedExport.video_codec} / {selectedExport.audio_codec}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Export History Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                Export History ({exportsList.length})
              </h3>
            </div>

            {exportsList.length === 0 ? (
              <div className="p-6 rounded-xl border border-dashed border-border text-center text-xs text-text-muted">
                No exports rendered yet for this project.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {exportsList.map((exp) => {
                  const isSelected = selectedExport?.id === exp.id;
                  return (
                    <div
                      key={exp.id}
                      onClick={() => setSelectedExport(exp)}
                      className={`p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between gap-2 ${
                        isSelected
                          ? 'border-brand bg-brand/5'
                          : 'border-border bg-surface-card hover:border-border-hover'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="truncate">
                          <h4 className="text-xs font-semibold text-text-primary truncate">
                            {exp.title}
                          </h4>
                          <span className="text-[10px] font-mono text-text-muted">
                            {exp.target_width}x{exp.target_height} • {exp.duration_seconds.toFixed(1)}s
                          </span>
                        </div>
                        <Badge
                          variant={
                            exp.status === 'completed'
                              ? 'success'
                              : exp.status === 'failed'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {exp.status}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[11px] text-text-muted">
                        <span>{(exp.file_size_bytes / 1024).toFixed(0)} KB</span>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteExport(exp.id);
                            }}
                            className="p-1 rounded hover:text-rose-400 transition"
                            title="Delete export"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
