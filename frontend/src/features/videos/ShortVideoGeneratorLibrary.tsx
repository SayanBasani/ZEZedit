import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Film,
  Info,
  LayoutGrid,
  List,
  Loader2,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Trash2,
  Upload,
  Video,
  X,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import {
  deleteMediaAssetGlobal,
  fetchAllMedia,
  getGlobalThumbnailUrl,
  getStreamMediaUrl,
  isUploadRetryable,
  refreshMediaMetadata,
  regenerateThumbnailGlobal,
  uploadMediaBatch,
  uploadMediaFile,
} from '../../services/apiClient';
import { MediaAssetItem, UploadProgressInfo } from '../../types/projects';
import { UploadProgressPanel, UploadItem } from './UploadProgressPanel';

export interface ShortVideoGeneratorLibraryProps {
  onOpenDashboard: (asset: MediaAssetItem) => void;
}

const SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv', '.wmv'];

export const ShortVideoGeneratorLibrary: React.FC<ShortVideoGeneratorLibraryProps> = ({
  onOpenDashboard,
}) => {
  const [videos, setVideos] = useState<MediaAssetItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Filter & Pagination States
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(12);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [resolutionFilter, setResolutionFilter] = useState<string>('all');
  const [formatFilter, setFormatFilter] = useState<string>('all');
  const [codecFilter, setCodecFilter] = useState<string>('all');
  const [analysisFilter, setAnalysisFilter] = useState<string>('all');
  const [integrityFilter, setIntegrityFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Asset Inspection & Safe Deletion Modals
  const [selectedAssetForDetail, setSelectedAssetForDetail] = useState<MediaAssetItem | null>(null);
  const [assetPendingDelete, setAssetPendingDelete] = useState<MediaAssetItem | null>(null);
  const [deleteConflictError, setDeleteConflictError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [thumbVersion, setThumbVersion] = useState<number>(Date.now());
  const [isRefreshingMetadata, setIsRefreshingMetadata] = useState<boolean>(false);
  const [isRegeneratingThumb, setIsRegeneratingThumb] = useState<boolean>(false);
  const [copiedSha, setCopiedSha] = useState<boolean>(false);

  // Direct Ingestion State
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgressText, setUploadProgressText] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentRunIdRef = useRef<symbol | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleCancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const loadVideos = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetchAllMedia({
        search: debouncedSearch.trim() || undefined,
        resolution: resolutionFilter !== 'all' ? resolutionFilter : undefined,
        format: formatFilter !== 'all' ? formatFilter : undefined,
        video_codec: codecFilter !== 'all' ? codecFilter : undefined,
        analysis_status: analysisFilter !== 'all' ? analysisFilter : undefined,
        integrity_status: integrityFilter !== 'all' ? integrityFilter : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      });
      setVideos(res.items || []);
      setTotalCount(res.total ?? (res.items || []).length);
      setTotalPages(res.total_pages ?? Math.max(1, Math.ceil((res.total ?? (res.items || []).length) / pageSize)));
    } catch (err: any) {
      setFetchError(err.message || 'Failed to load videos.');
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, resolutionFilter, formatFilter, codecFilter, analysisFilter, integrityFilter, sortBy, sortOrder, page, pageSize]);

  useEffect(() => {
    void loadVideos();
  }, [loadVideos]);

  // Handle Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const uploadFiles = async (files: File[]) => {
    if (files.length === 0) return;
    setUploadError(null);

    // Cancel any previous upload in flight
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const runId = Symbol();
    currentRunIdRef.current = runId;

    // Single video upload flow
    if (files.length === 1) {
      const file = files[0];
      const fileName = file.name.toLowerCase();
      const isVideo =
        file.type.startsWith('video/') ||
        SUPPORTED_VIDEO_EXTENSIONS.some((ext) => fileName.endsWith(ext));

      if (!isVideo) {
        setUploadError(
          `"${file.name}" is not a recognized video file. Please upload an MP4, MOV, MKV, or WebM video.`
        );
        return;
      }

      const initialAttemptId = `att_${Date.now()}_0_${Math.random().toString(36).slice(2, 8)}`;
      const item: UploadItem = {
        id: `${Date.now()}_0`,
        file,
        loaded: 0,
        total: file.size > 0 ? file.size : null,
        percentage: file.size > 0 ? 0 : null,
        state: 'uploading',
        error: null,
        attemptId: initialAttemptId,
        attemptCount: 1,
        retryable: true,
      };

      setUploadItems([item]);
      setUploading(true);
      setUploadProgressText(`Uploading "${file.name}"...`);

      try {
        const testDelay = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_DELAY_SECONDS__ : undefined;
        const testFailCode = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAILURE_CODE__ : undefined;
        const testFailReg = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAIL_REGISTRATION__ : undefined;
        const testNetErr = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_NETWORK_ERROR__ : undefined;
        const asset = await uploadMediaFile('all', file, false, true, {
          signal: controller.signal,
          testDelaySeconds: testDelay,
          testFailureCode: testFailCode,
          testFailRegistration: testFailReg,
          testNetworkError: testNetErr,
          attemptId: initialAttemptId,
          attemptCount: 1,
          onProgress: (p: UploadProgressInfo) => {
            if (typeof window !== 'undefined') {
              (window as any).__ZEZ_LAST_PROGRESS__ = p;
            }
            if (currentRunIdRef.current !== runId) return;
            setUploadItems((prev) =>
              prev.map((it) =>
                it.file === file
                  ? {
                      ...it,
                      loaded: p.loaded,
                      total: p.total,
                      percentage: p.percentage,
                      state: p.state,
                      error: p.error,
                      mediaAsset: p.mediaAsset,
                      attemptId: p.attemptId ?? it.attemptId,
                      attemptCount: p.attemptCount ?? it.attemptCount,
                      retryable: p.retryable ?? it.retryable,
                    }
                  : it
              )
            );
            if (p.state === 'processing') {
              setUploadProgressText(`Processing "${file.name}" on server...`);
            } else if (p.percentage !== null) {
              setUploadProgressText(`Uploading "${file.name}" (${p.percentage.toFixed(1)}%)...`);
            }
          },
        });

        if (currentRunIdRef.current !== runId) return;
        setUploadItems((prev) =>
          prev.map((it) =>
            it.file === file
              ? {
                  ...it,
                  state: 'completed',
                  loaded: Math.max(it.loaded, it.total ?? file.size),
                  percentage: 100,
                  mediaAsset: asset,
                  retryable: false,
                }
              : it
          )
        );
        setUploadProgressText('Video indexed successfully!');
        await loadVideos();
        // Auto-open video dashboard for single video upload
        onOpenDashboard(asset);
      } catch (err: any) {
        if (currentRunIdRef.current !== runId) return;
        const isAbort = controller.signal.aborted || err.code === 'ABORTED';
        const retryable = isAbort ? true : isUploadRetryable(err.status ?? null, err.code);
        setUploadItems((prev) =>
          prev.map((it) =>
            it.file === file
              ? {
                  ...it,
                  state: isAbort ? 'cancelled' : 'failed',
                  error: isAbort ? 'Upload cancelled' : (err.message || 'Upload failed'),
                  retryable,
                }
              : it
          )
        );
        setUploadError(isAbort ? 'Upload cancelled.' : (err.message || 'Failed to upload video. Please try again.'));
      } finally {
        if (currentRunIdRef.current === runId) {
          setUploading(false);
          setTimeout(() => setUploadProgressText(''), 3000);
        }
      }
      return;
    }

    // Multiple video batch upload flow (multipart batch request with accurate aggregate progress)
    const initialItems: UploadItem[] = files.map((file, idx) => ({
      id: `${Date.now()}_${idx}`,
      file,
      loaded: 0,
      total: file.size > 0 ? file.size : null,
      percentage: file.size > 0 ? 0 : null,
      state: 'queued',
      error: null,
      attemptId: `att_${Date.now()}_${idx}_${Math.random().toString(36).slice(2, 8)}`,
      attemptCount: 1,
      retryable: true,
    }));

    setUploadItems(initialItems);
    setUploading(true);
    setUploadProgressText(`Uploading ${files.length} videos into media library...`);

    try {
      const testDelay = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_DELAY_SECONDS__ : undefined;
      const testFailCode = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAILURE_CODE__ : undefined;
      const testFailReg = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAIL_REGISTRATION__ : undefined;
      const batchRes = await uploadMediaBatch('all', files, false, true, {
        signal: controller.signal,
        testDelaySeconds: testDelay,
        testFailureCode: testFailCode,
        testFailRegistration: testFailReg,
        onProgress: (p: UploadProgressInfo) => {
          if (typeof window !== 'undefined') {
            (window as any).__ZEZ_LAST_PROGRESS__ = p;
          }
          if (currentRunIdRef.current !== runId) return;
          setUploadItems((prev) =>
            prev.map((it) => ({
              ...it,
              state: p.state === 'processing' ? 'processing' : 'uploading',
            }))
          );
          if (p.state === 'processing') {
            setUploadProgressText(`Processing ${files.length} videos on server...`);
          } else if (p.percentage !== null) {
            setUploadProgressText(`Uploading ${files.length} videos (${p.percentage.toFixed(1)}%)...`);
          }
        },
      });

      if (currentRunIdRef.current !== runId) return;

      setUploadItems((prev) =>
        prev.map((it) => {
          const resItem = batchRes.items.find((bi) => bi.filename === it.file.name);
          if (resItem) {
            const retryable = resItem.success ? false : isUploadRetryable(null, resItem.error_code);
            return {
              ...it,
              state: resItem.success ? 'completed' : 'failed',
              error: resItem.success ? null : (resItem.error || 'Failed'),
              mediaAsset: resItem.asset || null,
              loaded: it.total ?? it.file.size,
              percentage: resItem.success ? 100 : it.percentage,
              retryable,
            };
          }
          return { ...it, state: 'completed', loaded: it.total ?? it.file.size, percentage: 100, retryable: false };
        })
      );

      await loadVideos();

      if (batchRes.failed > 0) {
        const failedItems = batchRes.items.filter((item) => !item.success);
        const errDetails = failedItems
          .map((item) => `"${item.filename}": ${item.error || 'Failed'}`)
          .join(', ');
        setUploadError(
          `Batch completed: ${batchRes.succeeded} uploaded, ${batchRes.failed} failed (${errDetails}).`
        );
      } else {
        setUploadProgressText(`Successfully uploaded all ${batchRes.succeeded} videos!`);
      }
    } catch (err: any) {
      if (currentRunIdRef.current !== runId) return;
      const isAbort = controller.signal.aborted || err.code === 'ABORTED';
      const retryable = isAbort ? true : isUploadRetryable(err.status ?? null, err.code);
      setUploadItems((prev) =>
        prev.map((it) => ({
          ...it,
          state: isAbort ? 'cancelled' : 'failed',
          error: isAbort ? 'Upload cancelled' : (err.message || 'Batch upload failed'),
          retryable,
        }))
      );
      setUploadError(isAbort ? 'Upload cancelled.' : (err.message || 'Batch upload failed. Please try again.'));
    } finally {
      if (currentRunIdRef.current === runId) {
        setUploading(false);
        setTimeout(() => setUploadProgressText(''), 3500);
      }
    }
  };

  const handleRetryItem = async (itemId: string) => {
    // Duplicate submission guard: if already uploading or completed, do nothing
    const targetItem = uploadItems.find((it) => it.id === itemId);
    if (!targetItem) return;
    if (
      targetItem.state === 'uploading' ||
      targetItem.state === 'retrying' ||
      targetItem.state === 'processing' ||
      targetItem.state === 'completed'
    ) {
      return;
    }

    // Check if the in-memory File object is present
    if (!targetItem.file || !(targetItem.file instanceof File)) {
      setUploadItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? {
                ...it,
                state: 'failed',
                error: 'File reference was lost on page reload. Please re-select the file.',
                retryable: false,
              }
            : it
        )
      );
      return;
    }

    const nextAttemptCount = (targetItem.attemptCount || 1) + 1;
    const nextAttemptId = `att_${Date.now()}_retry_${Math.random().toString(36).slice(2, 8)}`;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const runId = Symbol();
    currentRunIdRef.current = runId;

    setUploadItems((prev) =>
      prev.map((it) =>
        it.id === itemId
          ? {
              ...it,
              state: 'retrying',
              loaded: 0,
              percentage: 0,
              error: null,
              attemptId: nextAttemptId,
              attemptCount: nextAttemptCount,
              retryable: true,
            }
          : it
      )
    );
    setUploading(true);
    setUploadProgressText(`Retrying upload for "${targetItem.file.name}" (Attempt ${nextAttemptCount})...`);

    try {
      const testDelay = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_DELAY_SECONDS__ : undefined;
      const testFailCode = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAILURE_CODE__ : undefined;
      const testFailReg = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_FAIL_REGISTRATION__ : undefined;
      const testNetErr = typeof window !== 'undefined' ? (window as any).__ZEZ_TEST_NETWORK_ERROR__ : undefined;
      const asset = await uploadMediaFile('all', targetItem.file, false, true, {
        signal: controller.signal,
        testDelaySeconds: testDelay,
        testFailureCode: testFailCode,
        testFailRegistration: testFailReg,
        testNetworkError: testNetErr,
        attemptId: nextAttemptId,
        attemptCount: nextAttemptCount,
        onProgress: (p: UploadProgressInfo) => {
          if (typeof window !== 'undefined') {
            (window as any).__ZEZ_LAST_PROGRESS__ = p;
          }
          if (currentRunIdRef.current !== runId) return;
          setUploadItems((prev) =>
            prev.map((it) =>
              it.id === itemId
                ? {
                    ...it,
                    loaded: p.loaded,
                    total: p.total,
                    percentage: p.percentage,
                    state: p.state,
                    error: p.error,
                    mediaAsset: p.mediaAsset,
                    retryable: p.retryable ?? it.retryable,
                  }
                : it
            )
          );
          if (p.state === 'processing') {
            setUploadProgressText(`Processing "${targetItem.file.name}" on server...`);
          } else if (p.percentage !== null) {
            setUploadProgressText(`Uploading "${targetItem.file.name}" (${p.percentage.toFixed(1)}%)...`);
          }
        },
      });

      if (currentRunIdRef.current !== runId) return;
      setUploadItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? {
                ...it,
                state: 'completed',
                loaded: Math.max(it.loaded, it.total ?? targetItem.file.size),
                percentage: 100,
                mediaAsset: asset,
                retryable: false,
              }
            : it
        )
      );
      setUploadProgressText('Video indexed successfully!');
      await loadVideos();
      if (uploadItems.length === 1) {
        onOpenDashboard(asset);
      }
    } catch (err: any) {
      if (currentRunIdRef.current !== runId) return;
      const isAbort = controller.signal.aborted || err.code === 'ABORTED';
      const retryable = isAbort ? true : isUploadRetryable(err.status ?? null, err.code);
      setUploadItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? {
                ...it,
                state: isAbort ? 'cancelled' : 'failed',
                error: isAbort ? 'Upload cancelled' : (err.message || 'Upload failed'),
                retryable,
              }
            : it
        )
      );
      setUploadError(isAbort ? 'Upload cancelled.' : (err.message || 'Failed to upload video. Please try again.'));
    } finally {
      if (currentRunIdRef.current === runId) {
        setUploading(false);
        setTimeout(() => setUploadProgressText(''), 3000);
      }
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    await uploadFiles(files);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length === 0) return;
    await uploadFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleInitiateDelete = (asset: MediaAssetItem) => {
    setAssetPendingDelete(asset);
    setDeleteConflictError(null);
  };

  const handleConfirmDelete = async (forceWithExports = false) => {
    if (!assetPendingDelete) return;
    setIsDeleting(true);
    try {
      await deleteMediaAssetGlobal(assetPendingDelete.id, false, forceWithExports);
      setAssetPendingDelete(null);
      setDeleteConflictError(null);
      await loadVideos();
    } catch (err: any) {
      setDeleteConflictError(err.message || 'Failed to delete asset.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRefreshMetadata = async (asset: MediaAssetItem) => {
    setIsRefreshingMetadata(true);
    try {
      const updated = await refreshMediaMetadata(asset.id);
      setSelectedAssetForDetail(updated);
      setVideos((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    } catch (err: any) {
      alert(`Metadata refresh failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsRefreshingMetadata(false);
    }
  };

  const handleRegenerateThumbnail = async (asset: MediaAssetItem) => {
    setIsRegeneratingThumb(true);
    try {
      const updated = await regenerateThumbnailGlobal(asset.id);
      setThumbVersion(Date.now());
      setSelectedAssetForDetail(updated);
      setVideos((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    } catch (err: any) {
      alert(`Thumbnail generation failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsRegeneratingThumb(false);
    }
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setDebouncedSearch('');
    setResolutionFilter('all');
    setFormatFilter('all');
    setCodecFilter('all');
    setAnalysisFilter('all');
    setIntegrityFilter('all');
    setSortBy('created_at');
    setSortOrder('desc');
    setPage(1);
  };

  const formatDuration = (sec?: number | null) => {
    if (!sec || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    resolutionFilter !== 'all' ||
    formatFilter !== 'all' ||
    codecFilter !== 'all' ||
    analysisFilter !== 'all' ||
    integrityFilter !== 'all' ||
    sortBy !== 'created_at' ||
    sortOrder !== 'desc';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-text-muted" />
            <h1 className="text-lg font-semibold text-text-primary tracking-tight">
              Short Video Generator
            </h1>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Central video library. Discover, inspect, organize, and manage source videos with verified technical metadata and playback seeking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadVideos}
            isLoading={loading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            leftIcon={<Upload className="w-3.5 h-3.5" />}
          >
            Upload New Video
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mp4,.mov,.mkv,.avi,.webm"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </div>

      {fetchError && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{fetchError}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={loadVideos}>Retry</Button>
        </div>
      )}

      {/* Real Byte-Accurate Upload Progress Panel */}
      {uploadItems.length > 0 && (
        <UploadProgressPanel
          items={uploadItems}
          isUploading={uploading}
          onCancel={handleCancelUpload}
          onDismiss={() => setUploadItems([])}
          onRetryItem={handleRetryItem}
        />
      )}

      {/* Direct Video Ingestion Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-6 transition-all duration-200 text-center ${
          isDragging
            ? 'border-text-primary bg-surface-active'
            : 'border-border bg-surface hover:bg-surface-hover'
        }`}
      >
        {uploading ? (
          <div className="py-6 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-text-primary">{uploadProgressText}</p>
              <p className="text-xs text-text-muted">
                Extracting metadata, creating proxy, and registering into video dashboard...
              </p>
            </div>
          </div>
        ) : (
          <div className="py-4 flex flex-col items-center justify-center space-y-3">
            <div className="w-10 h-10 rounded-lg bg-surface-hover border border-border flex items-center justify-center text-text-muted">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">
                Drag and drop your video file here, or{' '}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-text-primary underline underline-offset-2 hover:text-text-secondary font-medium"
                >
                  browse files
                </button>
              </p>
              <p className="text-xs text-text-muted mt-1">
                Supports MP4, MOV, MKV, and WebM videos up to multiple GBs.
              </p>
            </div>
          </div>
        )}

        {uploadError && (
          <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Video Search & Filtering Bar */}
      <div className="space-y-3 p-4 bg-surface/40 border border-border rounded-xl">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Search by title, filename, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-8 py-1.5 bg-surface border border-border rounded-lg text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-border-focus"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 text-text-muted hover:text-text-primary"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick Stats & View Mode Toggle */}
          <div className="flex items-center justify-between lg:justify-end gap-3 shrink-0">
            <span className="text-xs text-text-muted">
              {loading ? 'Loading...' : `Showing ${videos.length} of ${totalCount} videos`}
            </span>
            <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded transition ${
                  viewMode === 'grid'
                    ? 'bg-surface-active text-text-primary shadow-sm'
                    : 'text-text-muted hover:text-text-primary'
                }`}
                title="Grid View"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded transition ${
                  viewMode === 'list'
                    ? 'bg-surface-active text-text-primary shadow-sm'
                    : 'text-text-muted hover:text-text-primary'
                }`}
                title="List View"
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-xs">
          {/* Resolution Filter */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Resolution</label>
            <select
              value={resolutionFilter}
              onChange={(e) => {
                setResolutionFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="all">All Resolutions</option>
              <option value="4k">4K (2160p)</option>
              <option value="1440p">1440p</option>
              <option value="1080p">1080p (Full HD)</option>
              <option value="720p">720p (HD)</option>
              <option value="480p">480p (SD)</option>
            </select>
          </div>

          {/* Container Format Filter */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Format</label>
            <select
              value={formatFilter}
              onChange={(e) => {
                setFormatFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="all">All Formats</option>
              <option value="mp4">MP4</option>
              <option value="mkv">MKV</option>
              <option value="mov">MOV</option>
              <option value="webm">WebM</option>
            </select>
          </div>

          {/* Codec Filter */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Video Codec</label>
            <select
              value={codecFilter}
              onChange={(e) => {
                setCodecFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="all">All Codecs</option>
              <option value="h264">H.264 / AVC</option>
              <option value="hevc">HEVC / H.265</option>
              <option value="vp9">VP9</option>
              <option value="av1">AV1</option>
            </select>
          </div>

          {/* Analysis Status */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Analysis</label>
            <select
              value={analysisFilter}
              onChange={(e) => {
                setAnalysisFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="all">All Analysis</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="none">Not Started</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* Integrity Status */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Integrity</label>
            <select
              value={integrityFilter}
              onChange={(e) => {
                setIntegrityFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="all">All Integrity</option>
              <option value="verified">Verified</option>
              <option value="online">Online</option>
              <option value="missing">Missing</option>
              <option value="corrupted">Corrupted</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-[10px] text-text-muted font-medium mb-1">Sort Order</label>
            <select
              value={`${sortBy}:${sortOrder}`}
              onChange={(e) => {
                const [sb, so] = e.target.value.split(':');
                setSortBy(sb);
                setSortOrder(so as any);
                setPage(1);
              }}
              className="w-full bg-surface border border-border text-text-primary rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-border-focus"
            >
              <option value="created_at:desc">Newest First</option>
              <option value="created_at:asc">Oldest First</option>
              <option value="original_filename:asc">Filename (A-Z)</option>
              <option value="original_filename:desc">Filename (Z-A)</option>
              <option value="file_size_bytes:desc">Size (Largest)</option>
              <option value="file_size_bytes:asc">Size (Smallest)</option>
              <option value="duration_seconds:desc">Duration (Longest)</option>
              <option value="duration_seconds:asc">Duration (Shortest)</option>
              <option value="resolution:desc">Highest Resolution</option>
            </select>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="flex items-center justify-between pt-1 text-[11px]">
            <span className="text-text-muted">Filters active</span>
            <button
              onClick={handleResetFilters}
              className="text-text-secondary hover:text-text-primary underline underline-offset-2"
            >
              Reset All Filters
            </button>
          </div>
        )}
      </div>

      {/* Videos List / Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="p-4 space-y-3">
              <Skeleton className="h-40 w-full rounded-xl" />
              <Skeleton className="h-4 w-3/4 rounded" />
              <Skeleton className="h-3 w-1/2 rounded" />
            </Card>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <EmptyState
          icon={<Video className="w-10 h-10 text-text-muted" />}
          title={hasActiveFilters ? 'No matching videos found' : 'No videos in your library yet'}
          description={
            hasActiveFilters
              ? 'Try adjusting your search query or relaxing your filter selections.'
              : 'Upload or drop a video file above to start analyzing interesting moments and generating shorts.'
          }
          actionText={hasActiveFilters ? 'Reset Filters' : 'Upload First Video'}
          onAction={hasActiveFilters ? handleResetFilters : () => fileInputRef.current?.click()}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {videos.map((video) => {
            const thumbUrl = `${getGlobalThumbnailUrl(video.id)}?v=${thumbVersion}`;
            const title = (video.metadata?.title as string) || video.original_filename;
            const resLabel = video.resolution_label || (video.width && video.height ? `${video.width}x${video.height}` : null);
            const containerFmt = video.container_format?.toUpperCase() || video.file_extension?.replace('.', '').toUpperCase();

            return (
              <Card
                key={video.id}
                className="group overflow-hidden rounded-2xl border-border bg-surface/60 hover:bg-surface hover:border-border-focus transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  {/* Thumbnail / Video Header */}
                  <div
                    className="relative aspect-video bg-canvas-subtle overflow-hidden cursor-pointer"
                    onClick={() => setSelectedAssetForDetail(video)}
                  >
                    <img
                      src={thumbUrl}
                      alt={video.original_filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />

                    {/* Fallback film placeholder if thumbnail missing */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/40 text-text-muted pointer-events-none -z-0">
                      <Film className="w-8 h-8 opacity-40" />
                    </div>

                    {/* Hover Play / Inspect overlay */}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-surface-active/90 border border-border text-text-primary flex items-center justify-center shadow-lg">
                        <Play className="w-5 h-5 ml-0.5 fill-current" />
                      </div>
                    </div>

                    {/* Duration badge */}
                    <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 font-mono text-[11px] text-white">
                      {formatDuration(video.duration_seconds)}
                    </div>

                    {/* Resolution badge */}
                    {resLabel && (
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/75 text-[10px] font-mono text-zinc-200 font-medium">
                        {resLabel}
                      </div>
                    )}

                    {/* Container badge */}
                    {containerFmt && (
                      <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-black/75 text-[10px] font-mono text-zinc-300">
                        {containerFmt}
                      </div>
                    )}
                  </div>

                  {/* Metadata Content */}
                  <div className="p-4 space-y-2">
                    <h3
                      className="text-sm font-semibold text-text-primary line-clamp-1 hover:text-text-primary cursor-pointer"
                      onClick={() => setSelectedAssetForDetail(video)}
                      title={title}
                    >
                      {title}
                    </h3>
                    <p className="text-[11px] text-text-muted font-mono truncate">
                      {video.original_filename}
                    </p>

                    {/* Technical Badges Row */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[10px]">
                      <span className="px-2 py-0.5 rounded bg-surface border border-border font-mono text-text-secondary">
                        {formatBytes(video.file_size_bytes)}
                      </span>
                      {video.video_codec && (
                        <span className="px-2 py-0.5 rounded bg-surface border border-border font-mono text-text-secondary">
                          {video.video_codec}
                        </span>
                      )}
                      {video.fps && (
                        <span className="px-2 py-0.5 rounded bg-surface border border-border font-mono text-text-secondary">
                          {Math.round(video.fps)} fps
                        </span>
                      )}
                      {video.integrity_status && (
                        <span
                          className={`px-2 py-0.5 rounded font-mono capitalize ${
                            video.integrity_status === 'verified'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : video.integrity_status === 'missing'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                              : video.integrity_status === 'corrupted'
                              ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                              : 'bg-surface border border-border text-text-muted'
                          }`}
                        >
                          {video.integrity_status}
                        </span>
                      )}
                      {video.analysis_status && video.analysis_status !== 'none' && (
                        <span
                          className={`px-2 py-0.5 rounded font-mono capitalize ${
                            video.analysis_status === 'completed'
                              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                              : video.analysis_status === 'processing'
                              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
                              : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                          }`}
                        >
                          {video.analysis_status}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="px-4 pb-4 pt-2 border-t border-border/60 flex items-center justify-between gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="flex-1"
                    onClick={() => onOpenDashboard(video)}
                    leftIcon={<Film className="w-3.5 h-3.5" />}
                  >
                    Open Video Dashboard
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-text-muted hover:text-text-primary p-2"
                    title="Inspect Technical Specs"
                    onClick={() => setSelectedAssetForDetail(video)}
                  >
                    <Info className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-text-muted hover:text-red-400 hover:bg-red-500/10 p-2"
                    title="Delete Video"
                    onClick={() => handleInitiateDelete(video)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        /* List View */
        <div className="space-y-2">
          {videos.map((video) => {
            const title = (video.metadata?.title as string) || video.original_filename;
            const resLabel = video.resolution_label || (video.width && video.height ? `${video.width}x${video.height}` : null);
            return (
              <div
                key={video.id}
                className="p-3 bg-surface border border-border rounded-xl flex items-center justify-between gap-4 hover:border-border-focus hover:bg-surface-hover transition"
              >
                <div
                  className="flex items-center gap-3 cursor-pointer min-w-0 flex-1"
                  onClick={() => setSelectedAssetForDetail(video)}
                >
                  <div className="w-20 h-12 bg-canvas-subtle rounded-lg overflow-hidden shrink-0 relative">
                    <img
                      src={`${getGlobalThumbnailUrl(video.id)}?v=${thumbVersion}`}
                      alt=""
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <span className="absolute bottom-1 right-1 px-1 text-[9px] font-mono bg-black/80 rounded text-white">
                      {formatDuration(video.duration_seconds)}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-semibold text-text-primary truncate">
                        {title}
                      </p>
                      {resLabel && (
                        <span className="px-1.5 py-0.2 rounded bg-black/60 text-[9px] font-mono text-zinc-300">
                          {resLabel}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-text-muted font-mono truncate mt-0.5">
                      {video.original_filename} • {formatBytes(video.file_size_bytes)} • {video.video_codec || 'H.264'}
                      {video.fps ? ` • ${Math.round(video.fps)}fps` : ''}
                      {video.integrity_status ? ` • ${video.integrity_status}` : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedAssetForDetail(video)}
                    leftIcon={<Info className="w-3.5 h-3.5" />}
                  >
                    Inspect
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => onOpenDashboard(video)}
                    leftIcon={<Film className="w-3.5 h-3.5" />}
                  >
                    Open Video Dashboard
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleInitiateDelete(video)}
                    className="p-1.5 text-text-muted hover:text-red-400 hover:bg-red-500/10 transition"
                    title="Delete Video"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border pt-4 text-xs text-text-muted">
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="bg-surface border border-border text-text-primary rounded px-2 py-1 focus:outline-none"
            >
              <option value="12">12</option>
              <option value="24">24</option>
              <option value="48">48</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <span>
              Page {page} of {totalPages} ({totalCount} total)
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1.5"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Media Detail & Playback Inspection Modal */}
      {selectedAssetForDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-surface border border-border rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
            {/* Modal Header */}
            <div className="p-4 border-b border-border flex items-center justify-between sticky top-0 bg-surface/95 backdrop-blur z-10">
              <div className="min-w-0 pr-4">
                <h2 className="text-sm font-semibold text-text-primary truncate">
                  {selectedAssetForDetail.original_filename}
                </h2>
                <p className="text-[11px] text-text-muted font-mono truncate">
                  ID: {selectedAssetForDetail.id}
                </p>
              </div>
              <button
                onClick={() => setSelectedAssetForDetail(null)}
                className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 flex-1">
              {/* HTML5 Native Video Player with HTTP 206 Byte-Range Seeking */}
              <div className="relative aspect-video rounded-xl overflow-hidden bg-black border border-border shadow-inner">
                <video
                  key={`${selectedAssetForDetail.id}-${thumbVersion}`}
                  src={getStreamMediaUrl(selectedAssetForDetail.id)}
                  controls
                  preload="metadata"
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Stream Topology Grid */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Stream Topology & Technical Specifications
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Resolution & Aspect</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5">
                      {selectedAssetForDetail.resolution_label ||
                        (selectedAssetForDetail.width && selectedAssetForDetail.height
                          ? `${selectedAssetForDetail.width}x${selectedAssetForDetail.height}`
                          : 'Unknown')}
                      {selectedAssetForDetail.aspect_ratio ? ` (${selectedAssetForDetail.aspect_ratio})` : ''}
                    </p>
                  </div>

                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Video Codec</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5">
                      {selectedAssetForDetail.video_codec || 'Unknown'}
                    </p>
                  </div>

                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Audio Codec & Channels</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5">
                      {selectedAssetForDetail.audio_codec || 'None'}
                      {selectedAssetForDetail.audio_stream_count
                        ? ` (${selectedAssetForDetail.audio_stream_count} stream${
                            selectedAssetForDetail.audio_stream_count > 1 ? 's' : ''
                          })`
                        : ''}
                    </p>
                  </div>

                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Duration & Framerate</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5">
                      {formatDuration(selectedAssetForDetail.duration_seconds)}
                      {selectedAssetForDetail.fps ? ` • ${Math.round(selectedAssetForDetail.fps)} fps` : ''}
                    </p>
                  </div>

                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Container Format</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5 uppercase">
                      {selectedAssetForDetail.container_format ||
                        selectedAssetForDetail.file_extension?.replace('.', '') ||
                        'MP4'}
                    </p>
                  </div>

                  <div className="p-3 bg-surface-active/50 border border-border rounded-xl">
                    <p className="text-[10px] text-text-muted">Pixel Format / Bitrate</p>
                    <p className="text-xs font-mono font-medium text-text-primary mt-0.5">
                      {selectedAssetForDetail.pixel_format || 'yuv420p'}
                      {selectedAssetForDetail.bitrate
                        ? ` • ${(selectedAssetForDetail.bitrate / 1000000).toFixed(1)} Mbps`
                        : ''}
                    </p>
                  </div>
                </div>

                {/* Subtitles & Audio Languages if present */}
                {(selectedAssetForDetail.audio_languages?.length || selectedAssetForDetail.subtitle_languages?.length) ? (
                  <div className="p-3 bg-surface-active/40 border border-border rounded-xl text-xs space-y-1">
                    {selectedAssetForDetail.audio_languages?.length ? (
                      <p className="text-text-muted">
                        <strong className="text-text-secondary">Audio Languages:</strong>{' '}
                        {selectedAssetForDetail.audio_languages.join(', ')}
                      </p>
                    ) : null}
                    {selectedAssetForDetail.subtitle_languages?.length ? (
                      <p className="text-text-muted">
                        <strong className="text-text-secondary">Subtitles:</strong>{' '}
                        {selectedAssetForDetail.subtitle_languages.join(', ')}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>

              {/* Integrity & File Contract */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Integrity & Persistence Contract
                </h3>
                <div className="space-y-2 text-xs font-mono bg-surface-active/30 border border-border rounded-xl p-3">
                  <div className="flex items-center justify-between py-1 border-b border-border/50">
                    <span className="text-text-muted">File Size:</span>
                    <span className="text-text-primary">
                      {formatBytes(selectedAssetForDetail.file_size_bytes)} (
                      {selectedAssetForDetail.file_size_bytes?.toLocaleString()} bytes)
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-border/50">
                    <span className="text-text-muted">SHA-256 Checksum:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-text-primary truncate max-w-xs" title={selectedAssetForDetail.sha256 || ''}>
                        {selectedAssetForDetail.sha256 || 'Pending check'}
                      </span>
                      {selectedAssetForDetail.sha256 && (
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(selectedAssetForDetail.sha256 || '');
                            setCopiedSha(true);
                            setTimeout(() => setCopiedSha(false), 2000);
                          }}
                          className="p-1 hover:text-text-primary text-text-muted"
                          title="Copy SHA-256"
                        >
                          {copiedSha ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-border/50">
                    <span className="text-text-muted">Upload Attempt ID:</span>
                    <span className="text-text-primary">
                      {selectedAssetForDetail.upload_attempt_id || 'N/A'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-border/50">
                    <span className="text-text-muted">Integrity Status:</span>
                    <span className="text-text-primary capitalize">
                      {selectedAssetForDetail.integrity_status || 'verified'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1">
                    <span className="text-text-muted">Physical Storage Path:</span>
                    <span className="text-text-primary truncate max-w-sm" title={selectedAssetForDetail.storage_path}>
                      {selectedAssetForDetail.storage_path}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border bg-surface flex flex-wrap items-center justify-between gap-3 sticky bottom-0">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRefreshMetadata(selectedAssetForDetail)}
                  isLoading={isRefreshingMetadata}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Refresh Metadata
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRegenerateThumbnail(selectedAssetForDetail)}
                  isLoading={isRegeneratingThumb}
                  leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                >
                  Regenerate Thumbnail
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    const asset = selectedAssetForDetail;
                    setSelectedAssetForDetail(null);
                    onOpenDashboard(asset);
                  }}
                  leftIcon={<Film className="w-3.5 h-3.5" />}
                >
                  Open Video Edit Dashboard
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedAssetForDetail(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dependency-Safe Delete Confirmation Modal */}
      {assetPendingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-surface border border-border rounded-2xl max-w-md w-full shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <ShieldAlert className="w-6 h-6 shrink-0" />
              <h2 className="text-base font-semibold text-text-primary">Delete Media Asset</h2>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Are you sure you want to permanently delete{' '}
              <strong className="text-text-primary font-mono">{assetPendingDelete.original_filename}</strong>?
              This will reclaim its managed storage and delete associated proxies and thumbnails.
            </p>

            {deleteConflictError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 space-y-2">
                <p className="font-medium flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Dependency Conflict</span>
                </p>
                <p className="text-[11px] leading-relaxed">{deleteConflictError}</p>
              </div>
            )}

            <div className="flex flex-col gap-2 pt-2">
              {deleteConflictError && deleteConflictError.includes('export') ? (
                <Button
                  variant="danger"
                  size="sm"
                  className="w-full"
                  isLoading={isDeleting}
                  onClick={() => handleConfirmDelete(true)}
                >
                  Force Delete Video & Dependent Exports
                </Button>
              ) : (
                <Button
                  variant="danger"
                  size="sm"
                  className="w-full"
                  isLoading={isDeleting}
                  onClick={() => handleConfirmDelete(false)}
                >
                  Confirm Delete
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={isDeleting}
                onClick={() => {
                  setAssetPendingDelete(null);
                  setDeleteConflictError(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
