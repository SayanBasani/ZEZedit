import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Eye,
  FileAudio,
  FileImage,
  Film,
  Grid,
  List,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
  Video,
  Zap,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import { Input, SearchInput } from '../../components/ui/Input';
import { EmptyState, Skeleton } from '../../components/ui/States';
import {
  deleteMediaAsset,
  generateProxy,
  getProxyUrl,
  getThumbnailUrl,
  importLocalMedia,
  regenerateThumbnail,
  relinkMedia,
  uploadMediaFile,
} from '../../services/apiClient';
import { MediaAssetItem, MediaStorageStats, ProjectItem } from '../../types/projects';

export interface MediaLibraryViewProps {
  projects: ProjectItem[];
  currentProjectId: string;
  onSelectProject: (projectId: string) => void;
  media: MediaAssetItem[];
  stats: MediaStorageStats | null;
  loading: boolean;
  onRefresh: () => void;
}

export const MediaLibraryView: React.FC<MediaLibraryViewProps> = ({
  projects,
  currentProjectId,
  onSelectProject,
  media,
  stats,
  loading,
  onRefresh,
}) => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'video' | 'audio' | 'image'>('all');
  const [availFilter, setAvailFilter] = useState<'all' | 'present' | 'missing'>('all');
  const [proxyFilter, setProxyFilter] = useState<'all' | 'ready' | 'generating' | 'none'>('all');
  const [sortBy, setSortBy] = useState<'recent' | 'name' | 'duration' | 'size'>('recent');

  // Modals & Panels
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importTab, setImportTab] = useState<'local' | 'upload'>('local');
  const [localPath, setLocalPath] = useState('');
  const [copyToStorage, setCopyToStorage] = useState(false);
  const [generateProxyNow, setGenerateProxyNow] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const [selectedAsset, setSelectedAsset] = useState<MediaAssetItem | null>(null);
  const [relinkTargetAsset, setRelinkTargetAsset] = useState<MediaAssetItem | null>(null);
  const [relinkNewPath, setRelinkNewPath] = useState('');
  const [isRelinking, setIsRelinking] = useState(false);

  const [deleteTargetAsset, setDeleteTargetAsset] = useState<MediaAssetItem | null>(null);
  const [deleteSourceFile, setDeleteSourceFile] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Filtered & Sorted Media
  const filteredMedia = useMemo(() => {
    return media
      .filter((item) => {
        if (typeFilter !== 'all' && item.media_type !== typeFilter) return false;
        if (availFilter !== 'all' && item.availability_status !== availFilter) return false;
        if (proxyFilter !== 'all') {
          if (proxyFilter === 'ready' && item.proxy_status !== 'ready') return false;
          if (proxyFilter === 'generating' && item.proxy_status !== 'generating') return false;
          if (proxyFilter === 'none' && item.proxy_status !== 'none') return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          return item.original_filename.toLowerCase().includes(q);
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'name') return a.original_filename.localeCompare(b.original_filename);
        if (sortBy === 'duration') return (b.duration_seconds || 0) - (a.duration_seconds || 0);
        if (sortBy === 'size') return (b.file_size_bytes || 0) - (a.file_size_bytes || 0);
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [media, typeFilter, availFilter, proxyFilter, searchQuery, sortBy]);

  // Format Helpers
  const formatBytes = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDuration = (seconds?: number | null): string => {
    if (!seconds || seconds <= 0) return '--:--';
    const totalSecs = Math.floor(seconds);
    const m = Math.floor(totalSecs / 60);
    const s = totalSecs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Handlers
  const handleLocalImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localPath.trim()) return;
    setIsImporting(true);
    setImportError(null);
    try {
      await importLocalMedia(currentProjectId, {
        file_path: localPath.trim(),
        copy_to_storage: copyToStorage,
        generate_proxy: generateProxyNow,
        generate_thumbnail: true,
      });
      setImportDialogOpen(false);
      setLocalPath('');
      onRefresh();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Local media import failed');
    } finally {
      setIsImporting(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setIsImporting(true);
    setImportError(null);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadMediaFile(currentProjectId, files[i], generateProxyNow, true);
      }
      setImportDialogOpen(false);
      onRefresh();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsImporting(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleGenerateProxy = async (asset: MediaAssetItem) => {
    try {
      await generateProxy(currentProjectId, asset.id, '480p');
      onRefresh();
      if (selectedAsset && selectedAsset.id === asset.id) {
        setSelectedAsset({ ...selectedAsset, proxy_status: 'ready' });
      }
    } catch (err) {
      alert(`Proxy generation failed: ${err instanceof Error ? err.message : 'Error'}`);
    }
  };

  const handleRegenerateThumb = async (asset: MediaAssetItem) => {
    try {
      await regenerateThumbnail(currentProjectId, asset.id);
      onRefresh();
    } catch (err) {
      alert(`Thumbnail regeneration failed: ${err instanceof Error ? err.message : 'Error'}`);
    }
  };

  const handleRelinkConfirm = async () => {
    if (!relinkTargetAsset || !relinkNewPath.trim()) return;
    setIsRelinking(true);
    try {
      await relinkMedia(currentProjectId, relinkTargetAsset.id, relinkNewPath.trim());
      setRelinkTargetAsset(null);
      setRelinkNewPath('');
      onRefresh();
    } catch (err) {
      alert(`Relinking failed: ${err instanceof Error ? err.message : 'File not found'}`);
    } finally {
      setIsRelinking(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTargetAsset) return;
    setIsDeleting(true);
    try {
      await deleteMediaAsset(currentProjectId, deleteTargetAsset.id, deleteSourceFile);
      setDeleteTargetAsset(null);
      if (selectedAsset && selectedAsset.id === deleteTargetAsset.id) {
        setSelectedAsset(null);
      }
      onRefresh();
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : 'Error'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Top Header & Project Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
            <Video className="w-5 h-5 text-brand" />
            Media Library
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Ingest, inspect, organize, and create proxies for video, audio, and image assets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {projects.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">Project:</span>
              <select
                value={currentProjectId}
                onChange={(e) => onSelectProject(e.target.value)}
                className="px-3 py-1.5 text-xs bg-surface border border-border rounded-lg text-text-primary focus:outline-none focus:border-brand"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            title="Refresh media"
          >
            Refresh
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setImportDialogOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Import Media
          </Button>
        </div>
      </div>

      {/* Storage and Metrics Summary Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="p-3 space-y-1">
            <span className="text-[10px] uppercase font-semibold text-text-muted">Total Assets</span>
            <div className="text-lg font-bold text-text-primary">{stats.total_media_count}</div>
            <span className="text-[10px] text-text-secondary">
              {stats.managed_files_count} managed • {stats.external_files_count} external
            </span>
          </Card>

          <Card className="p-3 space-y-1">
            <span className="text-[10px] uppercase font-semibold text-text-muted">Media Footprint</span>
            <div className="text-lg font-bold text-text-primary">{formatBytes(stats.total_media_bytes)}</div>
            <span className="text-[10px] text-text-secondary font-mono">Original source files</span>
          </Card>

          <Card className="p-3 space-y-1">
            <span className="text-[10px] uppercase font-semibold text-text-muted">Proxy Cache</span>
            <div className="text-lg font-bold text-sky-400">{formatBytes(stats.total_proxy_bytes)}</div>
            <span className="text-[10px] text-text-secondary font-mono">Optimized 480p scrubs</span>
          </Card>

          <Card className="p-3 space-y-1">
            <span className="text-[10px] uppercase font-semibold text-text-muted">Thumbnails</span>
            <div className="text-lg font-bold text-emerald-400">{formatBytes(stats.total_thumbnail_bytes)}</div>
            <span className="text-[10px] text-text-secondary font-mono">Cached preview frames</span>
          </Card>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-surface p-3 rounded-xl border border-border">
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
          <div className="w-64">
            <SearchInput
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClear={() => setSearchQuery('')}
              placeholder="Search media by filename..."
            />
          </div>

          {/* Media Type Tabs */}
          <div className="flex items-center gap-1 bg-canvas-subtle p-0.5 rounded-lg border border-border">
            {(['all', 'video', 'audio', 'image'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium capitalize transition ${
                  typeFilter === t
                    ? 'bg-surface text-text-primary shadow-xs'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                {t === 'all' ? 'All' : `${t}s`}
              </button>
            ))}
          </div>

          {/* Availability filter */}
          <select
            value={availFilter}
            onChange={(e) => setAvailFilter(e.target.value as any)}
            className="px-2.5 py-1 text-xs bg-canvas-subtle border border-border rounded-lg text-text-primary focus:outline-none"
          >
            <option value="all">All Status</option>
            <option value="present">Present on Disk</option>
            <option value="missing">Missing / Moved</option>
          </select>

          {/* Proxy filter */}
          <select
            value={proxyFilter}
            onChange={(e) => setProxyFilter(e.target.value as any)}
            className="px-2.5 py-1 text-xs bg-canvas-subtle border border-border rounded-lg text-text-primary focus:outline-none"
          >
            <option value="all">All Proxies</option>
            <option value="ready">Proxy Ready</option>
            <option value="generating">Generating...</option>
            <option value="none">No Proxy</option>
          </select>
        </div>

        {/* Sort & View Mode */}
        <div className="flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-2.5 py-1 text-xs bg-canvas-subtle border border-border rounded-lg text-text-primary focus:outline-none"
          >
            <option value="recent">Recently Added</option>
            <option value="name">Filename (A-Z)</option>
            <option value="duration">Duration (Longest)</option>
            <option value="size">Size (Largest)</option>
          </select>

          <div className="flex items-center gap-0.5 bg-canvas-subtle p-0.5 rounded-lg border border-border">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md transition ${
                viewMode === 'grid'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="Grid View"
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition ${
                viewMode === 'list'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="List View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {loading && media.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : filteredMedia.length === 0 ? (
        <EmptyState
          title={searchQuery || typeFilter !== 'all' ? 'No matching media files' : 'No media imported yet'}
          description={
            searchQuery || typeFilter !== 'all'
              ? 'Try adjusting your search query or status filter.'
              : 'Import videos, audio recordings, or image assets to begin editing in this project.'
          }
          actionText={searchQuery ? 'Clear Filters' : 'Import Media'}
          onAction={() => {
            if (searchQuery || typeFilter !== 'all') {
              setSearchQuery('');
              setTypeFilter('all');
              setAvailFilter('all');
              setProxyFilter('all');
            } else {
              setImportDialogOpen(true);
            }
          }}
        />
      ) : viewMode === 'grid' ? (
        /* GRID VIEW */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredMedia.map((asset) => (
            <Card
              key={asset.id}
              className="flex flex-col justify-between overflow-hidden p-0 border border-border group hover:border-brand/50 transition-all shadow-xs"
            >
              {/* Media Preview Box */}
              <div
                onClick={() => setSelectedAsset(asset)}
                className="relative aspect-video bg-black/40 flex items-center justify-center cursor-pointer overflow-hidden border-b border-border/40"
              >
                {asset.thumbnail_reference_path ? (
                  <img
                    src={getThumbnailUrl(currentProjectId, asset.id)}
                    alt={asset.original_filename}
                    className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                    loading="lazy"
                  />
                ) : asset.media_type === 'audio' ? (
                  <div className="flex flex-col items-center justify-center space-y-1 text-brand">
                    <FileAudio className="w-8 h-8" />
                    <span className="text-[10px] font-mono text-text-muted">Audio Clip</span>
                  </div>
                ) : asset.media_type === 'image' ? (
                  <FileImage className="w-8 h-8 text-amber-400" />
                ) : (
                  <Film className="w-8 h-8 text-text-muted" />
                )}

                {/* Duration Badge */}
                {asset.duration_seconds && (
                  <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded bg-black/80 backdrop-blur-xs text-[10px] font-mono text-white">
                    {formatDuration(asset.duration_seconds)}
                  </span>
                )}

                {/* Media Type Badge */}
                <div className="absolute top-1.5 left-1.5 flex items-center gap-1">
                  <span className="px-1.5 py-0.5 rounded bg-black/80 backdrop-blur-xs text-[9px] font-semibold uppercase tracking-wider text-text-primary">
                    {asset.media_type}
                  </span>
                  {asset.is_external && (
                    <span className="px-1.5 py-0.5 rounded bg-sky-950/80 border border-sky-500/30 text-[9px] font-mono text-sky-400">
                      External
                    </span>
                  )}
                </div>

                {/* Missing Status Alert Overlay */}
                {asset.availability_status === 'missing' && (
                  <div className="absolute inset-0 bg-red-950/80 backdrop-blur-xs flex flex-col items-center justify-center text-red-400 p-2 text-center space-y-1">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                    <span className="text-xs font-semibold">Missing from Disk</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setRelinkTargetAsset(asset);
                        setRelinkNewPath(asset.storage_path);
                      }}
                      className="px-2 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white text-[10px] font-medium mt-1"
                    >
                      Relink File
                    </button>
                  </div>
                )}
              </div>

              {/* Card Meta & Controls */}
              <div className="p-3.5 space-y-2.5">
                <div>
                  <h3
                    className="text-xs font-semibold text-text-primary truncate"
                    title={asset.original_filename}
                  >
                    {asset.original_filename}
                  </h3>
                  <div className="flex items-center gap-2 text-[10px] text-text-muted font-mono mt-0.5">
                    <span>{formatBytes(asset.file_size_bytes)}</span>
                    {asset.width && asset.height && (
                      <>
                        <span>•</span>
                        <span>
                          {asset.width}x{asset.height}
                        </span>
                      </>
                    )}
                    {asset.fps && (
                      <>
                        <span>•</span>
                        <span>{Math.round(asset.fps)}fps</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Proxy Status Pill */}
                {asset.media_type === 'video' && (
                  <div className="flex items-center justify-between text-[11px] pt-1 border-t border-border/40">
                    <span className="text-[10px] text-text-muted">Proxy Scrub:</span>
                    {asset.proxy_status === 'ready' ? (
                      <Badge variant="success" size="sm">
                        480p Ready
                      </Badge>
                    ) : asset.proxy_status === 'generating' ? (
                      <Badge variant="warning" size="sm">
                        <Loader2 className="w-2.5 h-2.5 animate-spin mr-1" />
                        Generating
                      </Badge>
                    ) : (
                      <button
                        onClick={() => handleGenerateProxy(asset)}
                        className="text-[10px] text-brand hover:underline font-medium"
                      >
                        + Create Proxy
                      </button>
                    )}
                  </div>
                )}

                {/* Card Actions Footer */}
                <div className="flex items-center justify-between pt-2 border-t border-border/50 gap-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedAsset(asset)}
                    leftIcon={<Eye className="w-3.5 h-3.5" />}
                    className="flex-1 text-[11px]"
                  >
                    Details
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteTargetAsset(asset)}
                    className="text-red-400 hover:text-red-300 px-2"
                    title="Remove from project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* LIST VIEW */
        <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-canvas-subtle border-b border-border text-[11px] text-text-muted font-medium uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Asset</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Format / Codec</th>
                  <th className="py-2.5 px-3">Size</th>
                  <th className="py-2.5 px-3">Storage</th>
                  <th className="py-2.5 px-3">Proxy Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredMedia.map((asset) => (
                  <tr key={asset.id} className="hover:bg-surface-hover transition">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-10 h-6 bg-black/40 rounded overflow-hidden shrink-0 flex items-center justify-center border border-border/40">
                          {asset.thumbnail_reference_path ? (
                            <img
                              src={getThumbnailUrl(currentProjectId, asset.id)}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          ) : asset.media_type === 'audio' ? (
                            <FileAudio className="w-3.5 h-3.5 text-brand" />
                          ) : (
                            <Film className="w-3.5 h-3.5 text-text-muted" />
                          )}
                        </div>
                        <div className="truncate max-w-xs">
                          <span className="font-semibold text-text-primary block truncate" title={asset.original_filename}>
                            {asset.original_filename}
                          </span>
                          <span className="text-[10px] text-text-muted font-mono">{asset.id}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant="default" size="sm">
                        {asset.media_type}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono">{formatDuration(asset.duration_seconds)}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-text-secondary">
                      {asset.video_codec || asset.audio_codec || 'unknown'}
                      {asset.width && asset.height ? ` (${asset.width}x${asset.height})` : ''}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-text-secondary">
                      {formatBytes(asset.file_size_bytes)}
                    </td>
                    <td className="py-2.5 px-3">
                      {asset.is_external ? (
                        <span className="text-[10px] text-sky-400 font-mono">External</span>
                      ) : (
                        <span className="text-[10px] text-emerald-400 font-mono">Managed</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {asset.media_type === 'video' ? (
                        asset.proxy_status === 'ready' ? (
                          <Badge variant="success" size="sm">
                            Ready
                          </Badge>
                        ) : asset.proxy_status === 'generating' ? (
                          <Badge variant="warning" size="sm">
                            Generating
                          </Badge>
                        ) : (
                          <button
                            onClick={() => handleGenerateProxy(asset)}
                            className="text-[11px] text-brand hover:underline"
                          >
                            + Generate
                          </button>
                        )
                      ) : (
                        <span className="text-text-muted text-[11px]">N/A</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedAsset(asset)}
                          className="px-2"
                          title="View details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTargetAsset(asset)}
                          className="text-red-400 hover:text-red-300 px-2"
                          title="Delete asset"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Import Modal */}
      <Dialog
        isOpen={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        title="Import Media to Project"
        maxWidth="max-w-lg"
      >
        <div className="space-y-4">
          {/* Tab selector */}
          <div className="flex items-center gap-1 bg-canvas-subtle p-1 rounded-xl border border-border">
            <button
              onClick={() => setImportTab('local')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                importTab === 'local' ? 'bg-surface text-text-primary shadow-xs' : 'text-text-muted'
              }`}
            >
              Local Filesystem Path
            </button>
            <button
              onClick={() => setImportTab('upload')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                importTab === 'upload' ? 'bg-surface text-text-primary shadow-xs' : 'text-text-muted'
              }`}
            >
              Stream Upload
            </button>
          </div>

          {importError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs">
              {importError}
            </div>
          )}

          {importTab === 'local' ? (
            <form onSubmit={handleLocalImport} className="space-y-4">
              <Input
                label="Absolute File Path on Disk"
                placeholder="e.g. D:\Videos\interview_take_1.mp4"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
                helperText="Supports large 1-2 GB+ video, audio, or image files."
                required
              />

              <div className="space-y-2 bg-canvas-subtle p-3 rounded-xl border border-border/60">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={copyToStorage}
                    onChange={(e) => setCopyToStorage(e.target.checked)}
                    className="mt-0.5 rounded border-border"
                  />
                  <div className="text-xs">
                    <span className="font-semibold text-text-primary block">
                      Copy into Managed Storage
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Unchecked keeps external reference (no duplication). Checked copies file into
                      dedicated project folder.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-2.5 cursor-pointer pt-2 border-t border-border/40">
                  <input
                    type="checkbox"
                    checked={generateProxyNow}
                    onChange={(e) => setGenerateProxyNow(e.target.checked)}
                    className="mt-0.5 rounded border-border"
                  />
                  <div className="text-xs">
                    <span className="font-semibold text-text-primary block">
                      Generate 480p Proxy Immediately
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Creates downscaled H.264 scrub proxy for smooth editing on CPU-limited hardware.
                    </span>
                  </div>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" type="button" onClick={() => setImportDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" isLoading={isImporting}>
                  Import File
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-border hover:border-brand rounded-2xl p-6 text-center space-y-3 bg-canvas-subtle transition">
                <UploadCloud className="w-10 h-10 text-brand mx-auto" />
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-text-primary">
                    Select video, audio, or image files to upload
                  </p>
                  <p className="text-[11px] text-text-muted">
                    Streams directly in 1 MB chunks without buffering into memory.
                  </p>
                </div>
                <input
                  type="file"
                  id="media-file-upload-input"
                  className="hidden"
                  onChange={handleFileUpload}
                  multiple
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => document.getElementById('media-file-upload-input')?.click()}
                  isLoading={isImporting}
                >
                  Choose Media Files
                </Button>
              </div>

              <label className="flex items-start gap-2.5 cursor-pointer bg-canvas-subtle p-3 rounded-xl border border-border/60">
                <input
                  type="checkbox"
                  checked={generateProxyNow}
                  onChange={(e) => setGenerateProxyNow(e.target.checked)}
                  className="mt-0.5 rounded border-border"
                />
                <div className="text-xs">
                  <span className="font-semibold text-text-primary block">
                    Generate 480p Scrub Proxies
                  </span>
                  <span className="text-[11px] text-text-muted">
                    Automatically transcode uploaded videos for optimal preview performance.
                  </span>
                </div>
              </label>
            </div>
          )}
        </div>
      </Dialog>

      {/* Asset Details Drawer / Modal */}
      {selectedAsset && (
        <Dialog
          isOpen={true}
          onClose={() => setSelectedAsset(null)}
          title={selectedAsset.original_filename}
          maxWidth="max-w-2xl"
        >
          <div className="space-y-4 text-xs">
            {/* Preview player or thumbnail */}
            <div className="aspect-video bg-black rounded-xl overflow-hidden flex items-center justify-center border border-border">
              {selectedAsset.proxy_status === 'ready' ? (
                <video
                  src={getProxyUrl(currentProjectId, selectedAsset.id)}
                  controls
                  className="w-full h-full object-contain"
                />
              ) : selectedAsset.thumbnail_reference_path ? (
                <img
                  src={getThumbnailUrl(currentProjectId, selectedAsset.id)}
                  alt=""
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-text-muted flex flex-col items-center gap-1">
                  <Film className="w-8 h-8" />
                  <span>Preview not available</span>
                </div>
              )}
            </div>

            {/* Technical Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-canvas-subtle p-3.5 rounded-xl border border-border font-mono text-[11px]">
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Media Type</span>
                <span className="font-semibold text-text-primary capitalize">{selectedAsset.media_type}</span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Duration</span>
                <span className="font-semibold text-text-primary">
                  {formatDuration(selectedAsset.duration_seconds)} ({selectedAsset.duration_seconds?.toFixed(2)}s)
                </span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px] uppercase">File Size</span>
                <span className="font-semibold text-text-primary">
                  {formatBytes(selectedAsset.file_size_bytes)}
                </span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Resolution</span>
                <span className="font-semibold text-text-primary">
                  {selectedAsset.width ? `${selectedAsset.width}x${selectedAsset.height}` : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Video Codec / FPS</span>
                <span className="font-semibold text-text-primary">
                  {selectedAsset.video_codec || 'N/A'} {selectedAsset.fps ? `@ ${Math.round(selectedAsset.fps)}fps` : ''}
                </span>
              </div>
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Audio Codec</span>
                <span className="font-semibold text-text-primary">{selectedAsset.audio_codec || 'None'}</span>
              </div>
            </div>

            {/* Storage Path Details */}
            <div className="p-3 bg-canvas-subtle rounded-xl border border-border/60 space-y-1 font-mono text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Storage Path:</span>
                <Badge variant={selectedAsset.is_external ? 'info' : 'success'} size="sm">
                  {selectedAsset.is_external ? 'External Reference' : 'Managed Copy'}
                </Badge>
              </div>
              <p className="text-text-primary truncate" title={selectedAsset.storage_path}>
                {selectedAsset.storage_path}
              </p>
              {selectedAsset.proxy_reference_path && (
                <p className="text-[10px] text-sky-400 truncate pt-1">
                  Proxy: {selectedAsset.proxy_reference_path}
                </p>
              )}
            </div>

            {/* Actions Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border">
              <div className="flex items-center gap-2">
                {selectedAsset.media_type === 'video' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleGenerateProxy(selectedAsset)}
                    leftIcon={<Zap className="w-3.5 h-3.5 text-amber-400" />}
                  >
                    {selectedAsset.proxy_status === 'ready' ? 'Regenerate Proxy' : 'Generate 480p Proxy'}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRegenerateThumb(selectedAsset)}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Regenerate Thumbnail
                </Button>
              </div>

              <Button
                variant="danger"
                size="sm"
                onClick={() => {
                  setDeleteTargetAsset(selectedAsset);
                  setSelectedAsset(null);
                }}
              >
                Delete Asset
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Relink Modal */}
      <Dialog
        isOpen={!!relinkTargetAsset}
        onClose={() => setRelinkTargetAsset(null)}
        title="Relink Missing Media File"
      >
        <div className="space-y-4">
          <p className="text-xs text-text-secondary leading-relaxed">
            The media file <strong>{relinkTargetAsset?.original_filename}</strong> was moved or could not be found
            at its previous path. Provide its new location on disk to restore access without losing project metadata.
          </p>

          <Input
            label="New Absolute Path on Disk"
            value={relinkNewPath}
            onChange={(e) => setRelinkNewPath(e.target.value)}
            placeholder="e.g. D:\Videos\interview_take_1.mp4"
            required
          />

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setRelinkTargetAsset(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleRelinkConfirm} isLoading={isRelinking}>
              Relink & Restore
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        isOpen={!!deleteTargetAsset}
        onClose={() => {
          setDeleteTargetAsset(null);
          setDeleteSourceFile(false);
        }}
        title={`Delete '${deleteTargetAsset?.original_filename}'?`}
      >
        <div className="space-y-4 text-xs">
          <p className="text-text-secondary leading-relaxed">
            {deleteTargetAsset?.is_external
              ? 'Removing this external reference will unlink it from the project. Your original source file on disk will NOT be touched or deleted.'
              : 'Removing this asset unlinks it from the project and purges generated thumbnails and proxies.'}
          </p>

          {!deleteTargetAsset?.is_external && (
            <label className="flex items-center gap-2 cursor-pointer p-2.5 rounded-lg bg-canvas-subtle border border-border">
              <input
                type="checkbox"
                checked={deleteSourceFile}
                onChange={(e) => setDeleteSourceFile(e.target.checked)}
                className="rounded border-border"
              />
              <span className="text-text-primary">Also delete managed file copy from project storage</span>
            </label>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDeleteTargetAsset(null);
                setDeleteSourceFile(false);
              }}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteConfirm}
              isLoading={isDeleting}
            >
              Remove Media
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
