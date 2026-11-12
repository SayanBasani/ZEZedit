import React, { useState } from 'react';
import { AlertCircle, CheckCircle, Download, Loader2, X } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { submitBatchExport } from '../../services/apiClient';
import { CandidateItem } from '../../types/highlights';
import { BatchExportPayload, BatchExportResponse } from '../../types/system';

export interface BatchExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  candidates: CandidateItem[];
  onSuccess?: (response: BatchExportResponse) => void;
  onNavigateToQueue?: () => void;
}

export const BatchExportModal: React.FC<BatchExportModalProps> = ({
  isOpen,
  onClose,
  projectId,
  candidates,
  onSuccess,
  onNavigateToQueue,
}) => {
  // Filter for approved or queued candidates by default, or all candidates if none approved
  const approvedCandidates = candidates.filter(
    (c) => c.review_status === 'approved' || c.queued_for_render
  );
  const eligibleCandidates = approvedCandidates.length > 0 ? approvedCandidates : candidates;

  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(eligibleCandidates.map((c) => c.id))
  );
  const [preset, setPreset] = useState<string>('vertical_9_16');
  const [captionMode, setCaptionMode] = useState<string>('word_highlight');
  const [normalizeAudio, setNormalizeAudio] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchExportResponse | null>(null);

  if (!isOpen) return null;

  const toggleCandidate = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(eligibleCandidates.map((c) => c.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const handleBatchExport = async () => {
    if (selectedIds.size === 0) {
      setError('Please select at least one short to export.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setBatchResult(null);

    try {
      const payload: BatchExportPayload = {
        candidate_ids: Array.from(selectedIds),
        preset,
        caption_mode: captionMode,
        normalize_audio: normalizeAudio,
      };

      const response = await submitBatchExport(projectId, payload);
      setBatchResult(response);
      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit batch export.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between bg-surface/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <span>Batch Export Multiple Shorts</span>
                <Badge variant="purple" size="sm">Milestone 18</Badge>
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Enqueue parallel 9:16 rendering jobs for all selected approved shorts.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-text-muted hover:text-text-primary rounded-lg hover:bg-surface-hover transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-5 overflow-y-auto flex-1 space-y-5">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {batchResult ? (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                <CheckCircle className="w-5 h-5" />
                <span>Batch Render Successfully Queued!</span>
              </div>
              <p className="text-xs text-text-secondary">
                Submitted <strong>{batchResult.total_submitted}</strong> jobs (Batch ID:{' '}
                <span className="font-mono">{batchResult.batch_id}</span>). Jobs are now rendering in the background queue.
              </p>
              <div className="max-h-40 overflow-y-auto space-y-1.5 pt-2">
                {batchResult.items.map((item) => (
                  <div
                    key={item.candidate_id}
                    className="p-2 rounded bg-surface/80 border border-border/60 text-xs flex items-center justify-between font-mono"
                  >
                    <span className="truncate max-w-[280px] text-text-primary">{item.output_filename}</span>
                    <Badge variant="success" size="sm">Queued ({item.job_id.slice(0, 10)})</Badge>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Presets and Options Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Target Aspect Ratio</label>
                  <select
                    value={preset}
                    onChange={(e) => setPreset(e.target.value)}
                    className="w-full text-xs bg-canvas border border-border rounded-lg px-2.5 py-2 text-text-primary focus:outline-none focus:border-indigo-500"
                  >
                    <option value="vertical_9_16">9:16 Vertical (Shorts/Reels)</option>
                    <option value="square_1_1">1:1 Square (Feed)</option>
                    <option value="landscape_16_9">16:9 Original Landscape</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Caption Style</label>
                  <select
                    value={captionMode}
                    onChange={(e) => setCaptionMode(e.target.value)}
                    className="w-full text-xs bg-canvas border border-border rounded-lg px-2.5 py-2 text-text-primary focus:outline-none focus:border-indigo-500"
                  >
                    <option value="word_highlight">Animated Word Highlight</option>
                    <option value="subtitles">Static Subtitles</option>
                    <option value="none">No Captions (Clean Video)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Audio Mastering</label>
                  <div className="flex items-center h-9">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-text-primary">
                      <input
                        type="checkbox"
                        checked={normalizeAudio}
                        onChange={(e) => setNormalizeAudio(e.target.checked)}
                        className="rounded border-border text-indigo-500 focus:ring-indigo-500"
                      />
                      <span>Normalize Loudness</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Candidate Selection List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-text-primary">
                    Select Shorts to Render ({selectedIds.size} of {eligibleCandidates.length})
                  </span>
                  <div className="flex items-center gap-2 text-[11px] text-indigo-400">
                    <button type="button" onClick={selectAll} className="hover:underline">
                      Select All
                    </button>
                    <span>•</span>
                    <button type="button" onClick={deselectAll} className="hover:underline">
                      Deselect All
                    </button>
                  </div>
                </div>

                <div className="border border-border rounded-xl divide-y divide-border/60 max-h-56 overflow-y-auto bg-canvas/50">
                  {eligibleCandidates.length === 0 ? (
                    <div className="p-4 text-center text-xs text-text-muted">
                      No candidate shorts available. Run AI Highlights discovery first.
                    </div>
                  ) : (
                    eligibleCandidates.map((cand) => {
                      const isSelected = selectedIds.has(cand.id);
                      return (
                        <div
                          key={cand.id}
                          onClick={() => toggleCandidate(cand.id)}
                          className={`p-2.5 flex items-center justify-between gap-3 text-xs cursor-pointer transition ${
                            isSelected ? 'bg-indigo-500/10 text-text-primary' : 'hover:bg-surface-hover text-text-secondary'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleCandidate(cand.id)}
                              className="rounded border-border text-indigo-500 focus:ring-indigo-500"
                              onClick={(e) => e.stopPropagation()}
                            />
                            <div className="min-w-0">
                              <span className="font-medium text-text-primary block truncate">
                                {cand.title || 'Untitled Candidate'}
                              </span>
                              <span className="text-[10px] text-text-muted font-mono">
                                {cand.duration.toFixed(1)}s • Score: {Math.round(cand.quality_score * 100)}/100 • {cand.category}
                              </span>
                            </div>
                          </div>
                          <Badge
                            variant={cand.review_status === 'approved' ? 'success' : 'default'}
                            size="sm"
                          >
                            {cand.review_status}
                          </Badge>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border flex items-center justify-between bg-surface/90">
          <div className="text-[11px] text-text-muted font-mono">
            {batchResult ? (
              <span className="text-emerald-400">Rendering queued</span>
            ) : (
              <span>Ready: {selectedIds.size} shorts queued for render</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {batchResult ? (
              <>
                {onNavigateToQueue && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      onClose();
                      onNavigateToQueue();
                    }}
                  >
                    View Working Queue
                  </Button>
                )}
                <Button size="sm" variant="primary" onClick={onClose}>
                  Done
                </Button>
              </>
            ) : (
              <>
                <Button size="sm" variant="ghost" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={handleBatchExport}
                  disabled={submitting || selectedIds.size === 0}
                  leftIcon={submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                >
                  {submitting ? 'Submitting Jobs...' : `Render ${selectedIds.size} Shorts`}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
