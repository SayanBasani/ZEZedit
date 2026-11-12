import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  Film,
  LayoutGrid,
  List,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
  Video,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import {
  deleteMediaAssetGlobal,
  fetchAllMedia,
  getGlobalThumbnailUrl,
  uploadMediaFile,
} from '../../services/apiClient';
import { MediaAssetItem } from '../../types/projects';

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
  const [statusFilter, setStatusFilter] = useState<'all' | 'ready' | 'processing' | 'error'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Direct Ingestion State
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgressText, setUploadProgressText] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadVideos = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetchAllMedia();
      setVideos(res.items || []);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to load videos.');
    } finally {
      setLoading(false);
    }
  }, []);

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

  const validateAndUploadFile = async (file: File) => {
    setUploadError(null);
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

    setUploading(true);
    setUploadProgressText(`Uploading "${file.name}" into local intelligence engine...`);

    try {
      // Ingest directly without manual project requirement (auto-assigns to default workspace)
      const asset = await uploadMediaFile('all', file, false, true);
      setUploadProgressText('Video indexed successfully!');
      await loadVideos();
      // Auto-open video dashboard for the newly uploaded video
      onOpenDashboard(asset);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload video. Please try again.');
    } finally {
      setUploading(false);
      setUploadProgressText('');
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    await validateAndUploadFile(files[0]);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await validateAndUploadFile(files[0]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDeleteVideo = async (asset: MediaAssetItem) => {
    const confirmDelete = window.confirm(
      `Are you sure you want to delete "${asset.original_filename}"? Derivative proxies and thumbnails will be removed.`
    );
    if (!confirmDelete) return;

    try {
      await deleteMediaAssetGlobal(asset.id, false);
      await loadVideos();
    } catch (err: any) {
      alert(`Failed to delete: ${err.message || 'Unknown error'}`);
    }
  };

  // Filtering
  const filteredVideos = videos.filter((v) => {
    const title = (v.metadata?.title as string) || v.original_filename;
    const matchesSearch =
      v.original_filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      title.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;

    if (statusFilter === 'ready') return v.availability_status === 'present';
    if (statusFilter === 'processing') return v.proxy_status === 'generating';
    if (statusFilter === 'error') return v.availability_status === 'missing' || v.proxy_status === 'failed';
    return true;
  });

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
            Central video library. Upload or pick any source video to analyze moments, frame scenes, and generate viral shorts.
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

      {/* Direct Video Ingestion Drop Zone (Snapped to 4px/8px scale, Quiet Graphite) */}
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
                Supports movies and videos up to multiple GBs (MP4, MOV, MKV, WebM). No grouping or project setup required.
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

      {/* Video Search & Controls Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Search videos by title or filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-surface border border-border rounded-xl text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-border-focus"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="bg-surface border border-border text-xs text-text-primary rounded-xl px-3 py-1.5 focus:outline-none focus:border-border-focus"
          >
            <option value="all">All Statuses ({videos.length})</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="error">Error</option>
          </select>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-lg border transition ${
              viewMode === 'grid'
                ? 'bg-surface-active border-border-focus text-text-primary'
                : 'bg-surface border-border text-text-muted hover:text-text-primary'
            }`}
            title="Grid View"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-lg border transition ${
              viewMode === 'list'
                ? 'bg-surface-active border-border-focus text-text-primary'
                : 'bg-surface border-border text-text-muted hover:text-text-primary'
            }`}
            title="List View"
          >
            <List className="w-4 h-4" />
          </button>
        </div>
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
      ) : filteredVideos.length === 0 ? (
        <EmptyState
          icon={<Video className="w-10 h-10 text-text-muted" />}
          title={searchQuery ? 'No matching videos found' : 'No videos in your library yet'}
          description={
            searchQuery
              ? 'Try adjusting your search query or status filter.'
              : 'Drop a video file above to start analyzing interesting moments and generating shorts.'
          }
          actionText="Upload First Video"
          onAction={() => fileInputRef.current?.click()}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredVideos.map((video) => {
            const thumbUrl = getGlobalThumbnailUrl(video.id);
            const title = (video.metadata?.title as string) || video.original_filename;
            return (
              <Card
                key={video.id}
                className="group overflow-hidden rounded-2xl border-border bg-surface/60 hover:bg-surface hover:border-border-focus transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  {/* Thumbnail / Video Header */}
                  <div
                    className="relative aspect-video bg-canvas-subtle overflow-hidden cursor-pointer"
                    onClick={() => onOpenDashboard(video)}
                  >
                    <img
                      src={thumbUrl}
                      alt={video.original_filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <div className="w-11 h-11 rounded-full bg-surface-active/90 border border-border text-text-primary flex items-center justify-center shadow-lg">
                        <Play className="w-5 h-5 ml-0.5 fill-current" />
                      </div>
                    </div>

                    <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 font-mono text-[11px] text-white">
                      {formatDuration(video.duration_seconds)}
                    </div>

                    {video.width && video.height && (
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/70 text-[10px] font-mono text-zinc-300">
                        {video.width}x{video.height}
                      </div>
                    )}
                  </div>

                  {/* Metadata Content */}
                  <div className="p-4 space-y-2">
                    <h3
                      className="text-sm font-semibold text-text-primary line-clamp-1 hover:text-text-primary cursor-pointer"
                      onClick={() => onOpenDashboard(video)}
                      title={title}
                    >
                      {title}
                    </h3>
                    <p className="text-[11px] text-text-muted font-mono truncate">
                      {video.original_filename}
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-text-muted pt-1">
                      <span>{formatBytes(video.file_size_bytes)}</span>
                      {video.fps && <span>• {Math.round(video.fps)} fps</span>}
                      {video.video_codec && <span>• {video.video_codec}</span>}
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
                    className="text-text-muted hover:text-red-400 hover:bg-red-500/10 p-2"
                    title="Delete Video"
                    onClick={() => handleDeleteVideo(video)}
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
          {filteredVideos.map((video) => {
            const title = (video.metadata?.title as string) || video.original_filename;
            return (
              <div
                key={video.id}
                className="p-3 bg-surface border border-border rounded-xl flex items-center justify-between gap-4 hover:border-border-focus hover:bg-surface-hover transition"
              >
                <div
                  className="flex items-center gap-3 cursor-pointer min-w-0"
                  onClick={() => onOpenDashboard(video)}
                >
                  <div className="w-20 h-12 bg-canvas-subtle rounded-lg overflow-hidden shrink-0 relative">
                    <img
                      src={getGlobalThumbnailUrl(video.id)}
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
                    <p className="text-xs font-semibold text-text-primary truncate">
                      {title}
                    </p>
                    <p className="text-[10px] text-text-muted font-mono truncate">
                      {video.width}x{video.height} • {formatBytes(video.file_size_bytes)} • {video.video_codec || 'H.264'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => onOpenDashboard(video)}
                    leftIcon={<Film className="w-3.5 h-3.5" />}
                  >
                    Open Dashboard
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteVideo(video)}
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
    </div>
  );
};
