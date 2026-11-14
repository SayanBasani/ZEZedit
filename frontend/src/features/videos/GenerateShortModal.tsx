import React, { useState } from 'react';
import {
  Sparkles,
  Scissors,
  X,
  ChevronDown,
  ChevronUp,
  Sliders,
  Flame,
  MessageSquare,
  Heart,
  BookOpen,
  Eye,
  Smile,
  Maximize2,
  Square,
  Smartphone,
  Check,
  Loader2,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';

export interface GenerateShortsModalConfig {
  targetClipCount: number | null; // null = AI recommended
  creativeDirection: string;
  aspectRatio: string;
  durationPreference: string;
  minDurationSec?: number;
  maxDurationSec?: number;
  noveltyMode: string;
  trackingMode: string;
}

export interface GenerateShortModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (config: GenerateShortsModalConfig) => Promise<void>;
  isGenerating: boolean;
  generationStage: string | null;
  isGenerateMore?: boolean;
}

const CREATIVE_DIRECTIONS = [
  {
    id: 'best_overall',
    label: 'Best Overall',
    desc: 'Balanced hook, dialogue & visual energy',
    icon: Sparkles,
  },
  {
    id: 'action',
    label: 'Action & High Energy',
    desc: 'Intense cuts, dynamic motion & punch',
    icon: Flame,
  },
  {
    id: 'dialogue',
    label: 'Dialogue & Conversational',
    desc: 'Speech turns, reactions & arguments',
    icon: MessageSquare,
  },
  {
    id: 'emotional',
    label: 'Emotional Moments',
    desc: 'Sentiment, pauses & facial reactions',
    icon: Heart,
  },
  {
    id: 'educational',
    label: 'Educational & Explainer',
    desc: 'Structured points & clear insights',
    icon: BookOpen,
  },
  {
    id: 'dramatic',
    label: 'Dramatic Suspense',
    desc: 'Rising tension, cliffhangers & beats',
    icon: Eye,
  },
  {
    id: 'humor',
    label: 'Humor & Entertainment',
    desc: 'Punchlines & comedic timing',
    icon: Smile,
  },
];

const ASPECT_RATIOS = [
  {
    id: '9:16',
    label: '9:16 Vertical',
    sub: 'Shorts, Reels, TikTok',
    icon: Smartphone,
  },
  {
    id: '1:1',
    label: '1:1 Square',
    sub: 'Feed posts & grid',
    icon: Square,
  },
  {
    id: '16:9',
    label: '16:9 Landscape',
    sub: 'Desktop & YouTube',
    icon: Maximize2,
  },
];

const DURATION_PREFERENCES = [
  { id: 'ai_best_duration', label: 'AI Best Duration', desc: 'Natural narrative pacing' },
  { id: '15s', label: '15 Seconds', desc: 'Punchy hook & climax' },
  { id: '30s', label: '30 Seconds', desc: 'Standard short length' },
  { id: '60s', label: '60 Seconds', desc: 'Extended story context' },
  { id: 'custom', label: 'Custom Range', desc: 'User-specified min/max' },
];

export const GenerateShortModal: React.FC<GenerateShortModalProps> = ({
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
  generationStage,
  isGenerateMore = false,
}) => {
  // Quantity Selection (Default: explicit choice 3 or AI recommended)
  const [quantityMode, setQuantityMode] = useState<'preset' | 'ai' | 'custom'>('preset');
  const [selectedPresetCount, setSelectedPresetCount] = useState<number>(3);
  const [customCount, setCustomCount] = useState<number>(5);

  // Creative direction & framing
  const [creativeDirection, setCreativeDirection] = useState('best_overall');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [durationPref, setDurationPref] = useState('ai_best_duration');
  const [minDurationSec, setMinDurationSec] = useState<number>(15);
  const [maxDurationSec, setMaxDurationSec] = useState<number>(45);

  // Advanced Options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [noveltyMode, setNoveltyMode] = useState('strict');
  const [trackingMode, setTrackingMode] = useState('saliency');

  if (!isOpen) return null;

  const getEffectiveClipCount = (): number | null => {
    if (quantityMode === 'ai') return null; // Let backend AI recommend
    if (quantityMode === 'custom') return Math.max(1, Math.min(20, customCount));
    return selectedPresetCount;
  };

  const effectiveCount = getEffectiveClipCount();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating) return;

    await onGenerate({
      targetClipCount: effectiveCount,
      creativeDirection,
      aspectRatio,
      durationPreference: durationPref,
      minDurationSec: durationPref === 'custom' ? minDurationSec : undefined,
      maxDurationSec: durationPref === 'custom' ? maxDurationSec : undefined,
      noveltyMode,
      trackingMode,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-subtle shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Scissors className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                {isGenerateMore ? 'Generate More Unique Shorts' : 'Generate Short Videos'}
              </h2>
              <p className="text-[11px] text-text-muted mt-0.5">
                AI analyzes narrative beats and discovers ready-to-render candidate clips.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isGenerating}
            className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover transition disabled:opacity-50"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body / Scrollable Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Section 1: Explicit Quantity Selection */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-text-primary flex items-center justify-between">
              <span>Shorts to Generate</span>
              <span className="text-[11px] font-normal text-text-muted">
                {quantityMode === 'ai'
                  ? 'AI Recommended Count'
                  : `${effectiveCount} Short${effectiveCount === 1 ? '' : 's'} Selected`}
              </span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[1, 3, 5].map((cnt) => (
                <button
                  type="button"
                  key={cnt}
                  onClick={() => {
                    setQuantityMode('preset');
                    setSelectedPresetCount(cnt);
                  }}
                  className={`h-10 rounded-lg text-xs font-medium border transition flex items-center justify-center gap-1.5 ${
                    quantityMode === 'preset' && selectedPresetCount === cnt
                      ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-400 shadow-2xs'
                      : 'bg-surface-subtle border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                  }`}
                >
                  {quantityMode === 'preset' && selectedPresetCount === cnt && (
                    <Check className="w-3.5 h-3.5 text-indigo-400" />
                  )}
                  <span>{cnt} Short{cnt > 1 ? 's' : ''}</span>
                </button>
              ))}

              {/* AI Recommended Choice */}
              <button
                type="button"
                onClick={() => setQuantityMode('ai')}
                className={`h-10 rounded-lg text-xs font-medium border transition flex items-center justify-center gap-1.5 ${
                  quantityMode === 'ai'
                    ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-400 shadow-2xs'
                    : 'bg-surface-subtle border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }`}
              >
                {quantityMode === 'ai' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>AI Auto</span>
              </button>

              {/* Custom Count Choice */}
              <button
                type="button"
                onClick={() => setQuantityMode('custom')}
                className={`h-10 rounded-lg text-xs font-medium border transition flex items-center justify-center gap-1.5 ${
                  quantityMode === 'custom'
                    ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-400 shadow-2xs'
                    : 'bg-surface-subtle border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }`}
              >
                {quantityMode === 'custom' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                <Sliders className="w-3.5 h-3.5 text-text-muted" />
                <span>Custom</span>
              </button>
            </div>

            {quantityMode === 'custom' && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-subtle border border-border mt-2">
                <span className="text-xs text-text-secondary">Custom Clip Quantity:</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={customCount}
                  onChange={(e) => setCustomCount(parseInt(e.target.value) || 1)}
                  className="w-20 px-2.5 py-1 text-xs rounded-md bg-canvas border border-border text-text-primary focus:outline-hidden focus:border-indigo-500 font-mono"
                />
                <span className="text-[11px] text-text-muted">(1 to 20 clips)</span>
              </div>
            )}
          </div>

          {/* Section 2: Creative Direction (7 Supported Options) */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-text-primary flex items-center justify-between">
              <span>Creative Direction</span>
              <span className="text-[11px] font-normal text-text-muted">7 Styles Supported</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {CREATIVE_DIRECTIONS.map((dir) => {
                const IconComp = dir.icon;
                const isSelected = creativeDirection === dir.id;
                return (
                  <button
                    type="button"
                    key={dir.id}
                    onClick={() => setCreativeDirection(dir.id)}
                    className={`p-3 rounded-xl border text-left transition flex items-start gap-3 ${
                      isSelected
                        ? 'bg-indigo-500/10 border-indigo-500/40 text-text-primary shadow-2xs'
                        : 'bg-surface-subtle border-border text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                    }`}
                  >
                    <div
                      className={`p-2 rounded-lg shrink-0 ${
                        isSelected
                          ? 'bg-indigo-500/20 text-indigo-400'
                          : 'bg-surface border border-border text-text-muted'
                      }`}
                    >
                      <IconComp className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-text-primary">{dir.label}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                      </div>
                      <p className="text-[11px] text-text-muted truncate mt-0.5">{dir.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 3: Target Aspect Ratio */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-text-primary">Target Aspect Ratio</label>
            <div className="grid grid-cols-3 gap-2.5">
              {ASPECT_RATIOS.map((ar) => {
                const IconComp = ar.icon;
                const isSelected = aspectRatio === ar.id;
                return (
                  <button
                    type="button"
                    key={ar.id}
                    onClick={() => setAspectRatio(ar.id)}
                    className={`p-3 rounded-xl border text-center transition flex flex-col items-center gap-1.5 ${
                      isSelected
                        ? 'bg-indigo-500/10 border-indigo-500/40 text-text-primary shadow-2xs'
                        : 'bg-surface-subtle border-border text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                    }`}
                  >
                    <IconComp
                      className={`w-5 h-5 ${isSelected ? 'text-indigo-400' : 'text-text-muted'}`}
                    />
                    <span className="text-xs font-medium text-text-primary">{ar.label}</span>
                    <span className="text-[10px] text-text-muted">{ar.sub}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 4: Duration Preference */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-text-primary">Duration Preference</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {DURATION_PREFERENCES.map((dp) => {
                const isSelected = durationPref === dp.id;
                return (
                  <button
                    type="button"
                    key={dp.id}
                    onClick={() => setDurationPref(dp.id)}
                    className={`p-2.5 rounded-lg border text-left transition ${
                      isSelected
                        ? 'bg-indigo-500/10 border-indigo-500/40 text-text-primary shadow-2xs'
                        : 'bg-surface-subtle border-border text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-text-primary">{dp.label}</span>
                      {isSelected && <Check className="w-3 h-3 text-indigo-400" />}
                    </div>
                    <p className="text-[10px] text-text-muted mt-0.5">{dp.desc}</p>
                  </button>
                );
              })}
            </div>

            {durationPref === 'custom' && (
              <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-surface-subtle border border-border mt-2">
                <div>
                  <span className="text-[11px] text-text-muted block mb-1">Min Duration (seconds)</span>
                  <input
                    type="number"
                    min={5}
                    max={120}
                    value={minDurationSec}
                    onChange={(e) => setMinDurationSec(parseFloat(e.target.value) || 10)}
                    className="w-full px-2.5 py-1 text-xs rounded-md bg-canvas border border-border text-text-primary font-mono"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-text-muted block mb-1">Max Duration (seconds)</span>
                  <input
                    type="number"
                    min={10}
                    max={180}
                    value={maxDurationSec}
                    onChange={(e) => setMaxDurationSec(parseFloat(e.target.value) || 60)}
                    className="w-full px-2.5 py-1 text-xs rounded-md bg-canvas border border-border text-text-primary font-mono"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Section 5: Advanced Options (Collapsible) */}
          <div className="border border-border rounded-xl overflow-hidden bg-surface-subtle">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full px-4 py-3 flex items-center justify-between text-xs font-medium text-text-secondary hover:text-text-primary transition"
            >
              <div className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-text-muted" />
                <span>Advanced Subject Tracking & Novelty Settings</span>
              </div>
              {showAdvanced ? (
                <ChevronUp className="w-4 h-4 text-text-muted" />
              ) : (
                <ChevronDown className="w-4 h-4 text-text-muted" />
              )}
            </button>

            {showAdvanced && (
              <div className="p-4 pt-1 border-t border-border space-y-4 bg-surface text-xs">
                {/* Novelty Mode */}
                <div>
                  <label className="text-[11px] font-semibold text-text-primary block mb-1.5">
                    Non-Repeating Novelty Policy
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'strict', label: 'Strict', sub: 'Zero overlap' },
                      { id: 'balanced', label: 'Balanced', sub: '<25% overlap' },
                      { id: 'relaxed', label: 'Relaxed', sub: 'Highest score' },
                    ].map((mode) => (
                      <button
                        type="button"
                        key={mode.id}
                        onClick={() => setNoveltyMode(mode.id)}
                        className={`p-2 rounded-lg border text-left transition ${
                          noveltyMode === mode.id
                            ? 'bg-indigo-500/10 border-indigo-500/40 text-text-primary'
                            : 'bg-surface-subtle border-border text-text-secondary hover:bg-surface-hover'
                        }`}
                      >
                        <span className="font-medium text-text-primary block">{mode.label}</span>
                        <span className="text-[10px] text-text-muted">{mode.sub}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Subject Tracking Mode */}
                <div>
                  <label className="text-[11px] font-semibold text-text-primary block mb-1.5">
                    Subject Tracking Mode
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'saliency', label: 'Intelligent Saliency', desc: 'Visual attention weights' },
                      { id: 'center', label: 'Fixed Center Crop', desc: 'Standard geometric crop' },
                      { id: 'multi_subject', label: 'Multi-Subject Union', desc: 'Keep all subjects in frame' },
                      { id: 'speaker', label: 'Speaker Focused', desc: 'Dynamic speaker tracking' },
                    ].map((trk) => (
                      <button
                        type="button"
                        key={trk.id}
                        onClick={() => setTrackingMode(trk.id)}
                        className={`p-2 rounded-lg border text-left transition ${
                          trackingMode === trk.id
                            ? 'bg-indigo-500/10 border-indigo-500/40 text-text-primary'
                            : 'bg-surface-subtle border-border text-text-secondary hover:bg-surface-hover'
                        }`}
                      >
                        <span className="font-medium text-text-primary block">{trk.label}</span>
                        <span className="text-[10px] text-text-muted">{trk.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Modal Footer / Actions */}
        <div className="px-6 py-4 border-t border-border bg-surface-subtle flex items-center justify-between shrink-0">
          <div className="text-xs text-text-muted">
            {isGenerating ? (
              <span className="flex items-center gap-2 text-indigo-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{generationStage || 'Discovering highlights...'}</span>
              </span>
            ) : (
              <span>Ready to discover short clips</span>
            )}
          </div>
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isGenerating}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={isGenerating}
              className="text-xs px-4"
              leftIcon={
                isGenerating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Scissors className="w-3.5 h-3.5" />
                )
              }
            >
              {isGenerating
                ? 'Generating...'
                : `Generate ${effectiveCount ? `${effectiveCount} ` : ''}Short${effectiveCount === 1 ? '' : 's'}`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
