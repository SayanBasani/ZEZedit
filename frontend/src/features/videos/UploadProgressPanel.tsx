import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Film,
  Loader2,
  RotateCw,
  X,
  XCircle,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { formatBytes } from '../../services/apiClient';
import { MediaAssetItem, UploadTransferState } from '../../types/projects';

export interface UploadItem {
  id: string;
  file: File;
  loaded: number;
  total: number | null;
  percentage: number | null;
  state: UploadTransferState;
  error?: string | null;
  mediaAsset?: MediaAssetItem | null;
  attemptId?: string;
  attemptCount?: number;
  retryable?: boolean;
  lastError?: string | null;
}

export interface UploadProgressPanelProps {
  items: UploadItem[];
  isUploading: boolean;
  onCancel?: () => void;
  onDismiss?: () => void;
  onRetryItem?: (itemId: string) => void;
}

export const UploadProgressPanel: React.FC<UploadProgressPanelProps> = ({
  items,
  isUploading,
  onCancel,
  onDismiss,
  onRetryItem,
}) => {
  if (items.length === 0) return null;

  // Calculate overall progress across all items
  let totalBytes = 0;
  let loadedBytes = 0;
  let hasUnknownTotal = false;
  let completedCount = 0;
  let failedCount = 0;

  for (const item of items) {
    if (item.state === 'completed') {
      completedCount++;
      const s = item.total ?? (item.file.size > 0 ? item.file.size : item.loaded);
      totalBytes += s;
      loadedBytes += s;
    } else if (
      item.state === 'error' ||
      item.state === 'failed' ||
      item.state === 'aborted' ||
      item.state === 'cancelled'
    ) {
      failedCount++;
    } else {
      // queued, waiting, uploading, retrying, processing
      if (item.total === null) {
        hasUnknownTotal = true;
        loadedBytes += item.loaded;
      } else {
        totalBytes += item.total;
        loadedBytes += Math.min(item.total, item.loaded);
      }
    }
  }

  const overallTotal = hasUnknownTotal ? null : totalBytes;
  let overallPercentage: number | null = null;
  if (overallTotal !== null && overallTotal > 0) {
    overallPercentage = Math.min(100, Math.max(0, (loadedBytes / overallTotal) * 100));
  }

  const isAllFinished =
    !isUploading &&
    items.every(
      (i) =>
        i.state === 'completed' ||
        i.state === 'error' ||
        i.state === 'failed' ||
        i.state === 'aborted' ||
        i.state === 'cancelled'
    );

  return (
    <Card className="p-4 mb-4 border border-border/80 bg-surface/90 shadow-sm space-y-3">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-2 border-b border-border/50">
        <div className="flex items-center gap-2">
          {isUploading ? (
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
          ) : isAllFinished && failedCount === 0 ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          )}
          <span className="text-xs font-semibold text-text-primary">
            {items.length === 1 ? (
              isUploading
                ? items[0].state === 'processing'
                  ? 'Processing video on server...'
                  : items[0].state === 'retrying'
                    ? 'Retrying upload...'
                    : 'Uploading video...'
                : isAllFinished
                  ? items[0].state === 'completed'
                    ? 'Upload complete'
                    : items[0].state === 'cancelled' || items[0].state === 'aborted'
                      ? 'Upload cancelled'
                      : 'Upload failed'
                  : 'Upload Status'
            ) : (
              isUploading
                ? `Uploading ${items.length} videos (${completedCount} of ${items.length} finished)...`
                : isAllFinished
                  ? `Batch finished: ${completedCount} succeeded, ${failedCount} failed`
                  : `Batch Upload (${items.length} files)`
            )}
          </span>
        </div>

        {/* Global Progress Metrics & Actions */}
        <div className="flex items-center gap-3 text-xs font-mono self-end sm:self-auto">
          {overallTotal !== null ? (
            <span className="text-text-muted">
              {formatBytes(loadedBytes)} / {formatBytes(overallTotal)}
              {overallPercentage !== null && (
                <span className="ml-1 text-text-primary font-medium">
                  ({overallPercentage.toFixed(1)}%)
                </span>
              )}
            </span>
          ) : (
            <span className="text-text-muted">
              {formatBytes(loadedBytes)} transferred
            </span>
          )}

          {isUploading && onCancel && (
            <Button
              size="sm"
              variant="ghost"
              title="Cancel active upload"
              className="text-xs text-text-muted hover:text-red-400 h-6 px-2"
              onClick={onCancel}
            >
              Cancel
            </Button>
          )}

          {isAllFinished && onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-surface-hover"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Aggregate Progress Bar for Batch / Single */}
      <div className="w-full bg-surface-hover rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-150 rounded-full ${
            failedCount > 0 && isAllFinished && completedCount === 0
              ? 'bg-red-500'
              : isAllFinished && failedCount === 0
                ? 'bg-emerald-500'
                : items.some((i) => i.state === 'processing')
                  ? 'bg-amber-500'
                  : 'bg-indigo-600'
          }`}
          style={{ width: `${overallPercentage ?? (isUploading ? 50 : 0)}%` }}
        />
      </div>

      {/* Itemized File List */}
      <div className="divide-y divide-border/40 max-h-56 overflow-y-auto space-y-2 pt-1 pr-1">
        {items.map((item) => {
          const isFailed = item.state === 'error' || item.state === 'failed';
          const isCancelled = item.state === 'aborted' || item.state === 'cancelled';
          const canRetry = (isFailed && item.retryable !== false) || isCancelled;

          return (
            <div key={item.id} className="pt-2 first:pt-0 space-y-1">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs gap-1.5">
                {/* File Name, Icon & Attempt Badge */}
                <div className="flex items-center gap-2 min-w-0 max-w-full sm:max-w-[55%]">
                  <Film className="w-3.5 h-3.5 text-text-muted shrink-0" />
                  <span className="font-medium text-text-primary truncate" title={item.file.name}>
                    {item.file.name}
                  </span>
                  {item.attemptCount !== undefined && item.attemptCount > 1 && (
                    <span
                      data-testid={`attempt-badge-${item.id}`}
                      className="px-1.5 py-0.2 rounded text-[10px] bg-surface-hover text-text-muted border border-border/40 font-mono shrink-0"
                    >
                      Attempt {item.attemptCount}
                    </span>
                  )}
                </div>

                {/* Status Badge, Byte Counter & Retry Button */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto font-mono text-[11px]">
                  {(item.state === 'waiting' || item.state === 'queued') && (
                    <span className="flex items-center gap-1 text-text-muted">
                      <Clock className="w-3 h-3" /> Queued
                    </span>
                  )}
                  {item.state === 'uploading' && (
                    <span className="flex items-center gap-1.5 text-indigo-400 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {item.total !== null ? (
                        <span>
                          {formatBytes(item.loaded)} / {formatBytes(item.total)} (
                          {item.percentage !== null ? `${item.percentage.toFixed(1)}%` : '--'})
                        </span>
                      ) : (
                        <span>{formatBytes(item.loaded)} sent</span>
                      )}
                    </span>
                  )}
                  {item.state === 'retrying' && (
                    <span className="flex items-center gap-1.5 text-amber-400 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span>Retrying upload...</span>
                    </span>
                  )}
                  {item.state === 'processing' && (
                    <span className="flex items-center gap-1.5 text-amber-400 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {item.total !== null ? (
                        <span>
                          {formatBytes(item.total)} / {formatBytes(item.total)} (100.0%) — Processing on server...
                        </span>
                      ) : (
                        <span>Processing on server...</span>
                      )}
                    </span>
                  )}
                  {item.state === 'completed' && (
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>
                        {formatBytes(item.total ?? item.file.size)} • Completed
                      </span>
                    </span>
                  )}
                  {isFailed && (
                    <div className="flex items-center gap-2">
                      <span
                        className="flex items-center gap-1 text-red-400 max-w-xs truncate"
                        title={item.error || 'Upload failed'}
                      >
                        <XCircle className="w-3 h-3 shrink-0" />
                        <span>{item.error || 'Failed'}</span>
                      </span>
                      {item.retryable === false && (
                        <span className="text-[10px] text-text-muted">(Non-retryable)</span>
                      )}
                      {canRetry && onRetryItem && !isUploading && (
                        <button
                          type="button"
                          data-testid={`retry-button-${item.id}`}
                          onClick={() => onRetryItem(item.id)}
                          className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-sans font-medium bg-surface-hover hover:bg-surface-active text-text-primary border border-border/60 transition-colors"
                          title="Retry upload from beginning"
                        >
                          <RotateCw className="w-3 h-3 text-text-muted" />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  )}
                  {isCancelled && (
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 text-text-muted">
                        <XCircle className="w-3 h-3" />
                        <span>Cancelled</span>
                      </span>
                      {canRetry && onRetryItem && !isUploading && (
                        <button
                          type="button"
                          data-testid={`retry-button-${item.id}`}
                          onClick={() => onRetryItem(item.id)}
                          className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-sans font-medium bg-surface-hover hover:bg-surface-active text-text-primary border border-border/60 transition-colors"
                          title="Retry upload from beginning"
                        >
                          <RotateCw className="w-3 h-3 text-text-muted" />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Individual Item Progress Bar (Visible while uploading, retrying or processing) */}
              {(item.state === 'uploading' || item.state === 'retrying' || item.state === 'processing') && (
                <div className="w-full bg-surface-hover rounded-full h-1 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-150 rounded-full ${
                      item.state === 'processing'
                        ? 'bg-amber-400'
                        : item.state === 'retrying'
                          ? 'bg-amber-500'
                          : 'bg-indigo-500'
                    }`}
                    style={{ width: `${item.percentage ?? 100}%` }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
};
