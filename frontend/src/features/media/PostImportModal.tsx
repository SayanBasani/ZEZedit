import React, { useEffect, useState } from 'react';
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Film,
  Layers,
  Loader2,
  Plus,
  AlertTriangle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import {
  fetchJob,
  getThumbnailUrl,
  startMediaAnalysis,
} from '../../services/apiClient';
import { JobItem, MediaAssetItem } from '../../types/projects';

export interface PostImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  asset: MediaAssetItem | null;
  onOpenWorkspace: (asset: MediaAssetItem, subTab?: string) => void;
  onImportAnother: () => void;
}

export const PostImportModal: React.FC<PostImportModalProps> = ({
  isOpen,
  onClose,
  projectId,
  asset,
  onOpenWorkspace,
  onImportAnother,
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [profile, setProfile] = useState<'fast' | 'balanced' | 'detailed'>('balanced');
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisCompleted, setAnalysisCompleted] = useState(false);

  // Reset state when a new asset is opened
  useEffect(() => {
    if (isOpen) {
      setAnalyzing(false);
      setActiveJob(null);
      setAnalysisError(null);
      setAnalysisCompleted(false);
    }
  }, [isOpen, asset?.id]);

  // Poll running job
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed' || activeJob.status === 'cancelled') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await fetchJob(activeJob.id);
        setActiveJob(updated);
        if (updated.status === 'completed') {
          setAnalysisCompleted(true);
          setAnalyzing(false);
        } else if (updated.status === 'failed') {
          setAnalysisError(updated.error_message || 'Video analysis failed');
          setAnalyzing(false);
        }
      } catch {
        // network retry
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob]);

  if (!isOpen || !asset) return null;

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '--';
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const handleStartAnalysis = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      await startMediaAnalysis(projectId, asset.id, profile, {}, false);
      setAnalysisCompleted(true);
      setAnalyzing(false);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : 'Failed to start analysis');
      setAnalyzing(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Media Ingested Successfully"
    >
      <div className="space-y-6 select-none">
        {/* Asset Header Summary */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-surface p-4 rounded-xl border border-border">
          <div className="relative aspect-video w-full sm:w-44 bg-black/60 rounded-lg overflow-hidden shrink-0 border border-border/60 flex items-center justify-center">
            {asset.thumbnail_reference_path ? (
              <img
                src={getThumbnailUrl(projectId, asset.id)}
                alt={asset.original_filename}
                className="w-full h-full object-cover"
              />
            ) : (
              <Film className="w-8 h-8 text-text-muted" />
            )}
            {asset.duration_seconds && (
              <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/85 text-[10px] font-mono text-white">
                {formatDuration(asset.duration_seconds)}
              </span>
            )}
          </div>

          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-2">
              <Badge variant="success" size="sm">
                Ready for Editing
              </Badge>
              <span className="text-[11px] font-mono text-text-muted uppercase">
                {asset.media_type}
              </span>
            </div>

            <h3 className="text-sm font-semibold text-text-primary truncate" title={asset.original_filename}>
              {asset.original_filename}
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] font-mono text-text-muted">
              <div>
                <span className="text-[10px] block text-text-secondary">Resolution</span>
                {asset.width && asset.height ? `${asset.width}x${asset.height}` : 'Audio Only'}
              </div>
              <div>
                <span className="text-[10px] block text-text-secondary">Frame Rate</span>
                {asset.fps ? `${Math.round(asset.fps)} fps` : '--'}
              </div>
              <div>
                <span className="text-[10px] block text-text-secondary">File Size</span>
                {formatBytes(asset.file_size_bytes)}
              </div>
              <div>
                <span className="text-[10px] block text-text-secondary">Storage</span>
                {asset.is_external ? 'External' : 'Managed'}
              </div>
            </div>
          </div>
        </div>

        {/* Persistent Job Tracker if Analysis Triggered */}
        {activeJob && (
          <Card className="bg-canvas border border-border space-y-3 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {activeJob.status === 'running' || activeJob.status === 'queued' ? (
                  <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                ) : activeJob.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                )}
                <span className="text-xs font-semibold text-text-primary capitalize">
                  {activeJob.job_type.replace('_', ' ')}: {activeJob.status}
                </span>
              </div>
              <span className="text-xs font-mono text-text-muted">
                {activeJob.progress_pct}%
              </span>
            </div>

            <div className="w-full bg-surface-hover rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  activeJob.status === 'completed'
                    ? 'bg-emerald-500'
                    : activeJob.status === 'failed'
                    ? 'bg-rose-500'
                    : 'bg-indigo-500'
                }`}
                style={{ width: `${Math.max(5, activeJob.progress_pct)}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-text-muted font-mono">
              <span className="truncate max-w-[280px]">
                {activeJob.current_stage || 'Processing pipeline stages...'}
              </span>
              <span>Task ID: {activeJob.id.slice(0, 12)}</span>
            </div>

            {analysisCompleted && (
              <div className="pt-2">
                <Button
                  variant="primary"
                  size="sm"
                  className="w-full"
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                  onClick={() => {
                    onClose();
                    onOpenWorkspace(asset, 'analysis');
                  }}
                >
                  View Completed Analysis in Workspace
                </Button>
              </div>
            )}
          </Card>
        )}

        {/* Error Notice */}
        {analysisError && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{analysisError}</span>
            </div>
            <button
              onClick={handleStartAnalysis}
              className="text-[11px] font-semibold text-rose-200 underline hover:text-white"
            >
              Retry
            </button>
          </div>
        )}

        {/* Action Flow Cards */}
        {!activeJob && (
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Choose Next Action
            </h4>

            {/* Option 1: Analyze Video */}
            <div className="p-4 bg-surface hover:bg-surface-hover/80 border border-border hover:border-indigo-500/40 rounded-xl transition space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-text-primary">
                      Analyze Video Now
                    </h4>
                    <p className="text-[11px] text-text-muted">
                      Extract audio, transcribe speech with Whisper, detect scene cuts, and extract candidate highlights.
                    </p>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="primary"
                  isLoading={analyzing}
                  onClick={handleStartAnalysis}
                >
                  Start Analysis
                </Button>
              </div>

              {/* Profile Selector */}
              <div className="flex items-center gap-3 pt-2 border-t border-border/50 text-xs">
                <span className="text-text-muted font-medium text-[11px]">Analysis Depth:</span>
                <div className="flex items-center gap-1.5">
                  {(['fast', 'balanced', 'detailed'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setProfile(p)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize transition ${
                        profile === p
                          ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300'
                          : 'text-text-muted hover:text-text-primary border border-transparent'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Option 2: Open Video Workspace Without Analysis */}
            <button
              onClick={() => {
                onClose();
                onOpenWorkspace(asset, 'overview');
              }}
              className="w-full text-left p-3.5 bg-surface hover:bg-surface-hover/80 border border-border hover:border-border/80 rounded-xl transition flex items-center justify-between group"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-canvas-subtle border border-border text-text-secondary group-hover:text-text-primary">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-text-primary">
                    Open Video Workspace
                  </h4>
                  <p className="text-[11px] text-text-muted">
                    Inspect raw video, preview playback, view metadata, or manually edit in Timeline.
                  </p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-primary group-hover:translate-x-0.5 transition" />
            </button>

            {/* Option 3: Import Another Video */}
            <button
              onClick={() => {
                onClose();
                onImportAnother();
              }}
              className="w-full text-left p-3.5 bg-surface hover:bg-surface-hover/80 border border-border hover:border-border/80 rounded-xl transition flex items-center justify-between group"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-canvas-subtle border border-border text-text-secondary group-hover:text-text-primary">
                  <Plus className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-text-primary">
                    Import Another Video
                  </h4>
                  <p className="text-[11px] text-text-muted">
                    Add additional footage or audio tracks to this project.
                  </p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-primary group-hover:translate-x-0.5 transition" />
            </button>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Back to Media Library
          </Button>
          {!activeJob && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                onClose();
                onOpenWorkspace(asset, 'overview');
              }}
            >
              Continue to Workspace
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
};

