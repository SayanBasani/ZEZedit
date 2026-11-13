import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
  Video,
  X,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  cancelJob,
  deleteJob,
  deleteJobHistory,
  fetchJobLogs,
  fetchJobs,
  fetchQueueStats,
  retryJob,
} from '../../services/apiClient';
import { JobItem, ProjectItem } from '../../types/projects';
import { JobLogs, QueueStats } from '../../types/system';

export interface WorkingQueueViewProps {
  projects?: ProjectItem[];
  onOpenProject?: (projectId: string) => void;
  onOpenVideo?: (assetId: string) => void;
  filterMediaAssetId?: string;
}

type StatusFilter = 'all' | 'running' | 'queued' | 'completed' | 'failed' | 'cancelled';

type CategoryFilter =
  | 'all'
  | 'media'
  | 'analysis'
  | 'generation'
  | 'rendering'
  | 'storage';

function categorizeJobType(jobType: string): CategoryFilter {
  const jt = (jobType || '').toLowerCase();
  if (jt.includes('upload') || jt.includes('proxy') || jt.includes('thumbnail') || jt.includes('validate') || jt.includes('ingest')) {
    return 'media';
  }
  if (jt.includes('analysis') || jt.includes('whisper') || jt.includes('scene') || jt.includes('frame') || jt.includes('audio') || jt.includes('speech')) {
    return 'analysis';
  }
  if (jt.includes('highlight') || jt.includes('candidate') || jt.includes('short') || jt.includes('script')) {
    return 'generation';
  }
  if (jt.includes('export') || jt.includes('render') || jt.includes('reframe') || jt.includes('transcode')) {
    return 'rendering';
  }
  if (jt.includes('cleanup') || jt.includes('storage') || jt.includes('clear') || jt.includes('backup')) {
    return 'storage';
  }
  return 'all';
}

function formatDuration(startedAt?: string | null, completedAt?: string | null): string {
  if (!startedAt) return '—';
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diffSec = Math.max(0, Math.round((end - start) / 1000));
  if (diffSec < 60) return `${diffSec}s`;
  const mins = Math.floor(diffSec / 60);
  const remSec = diffSec % 60;
  return `${mins}m ${remSec}s`;
}

function formatTimeOnly(isoString?: string | null): string {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoString.slice(11, 19);
  }
}

export const WorkingQueueView: React.FC<WorkingQueueViewProps> = ({
  projects: _projects = [],
  onOpenProject: _onOpenProject,
  onOpenVideo: _onOpenVideo,
  filterMediaAssetId,
}) => {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
  const [selectedVideoId, setSelectedVideoId] = useState<string>(filterMediaAssetId || 'all');
  const [searchQuery, setSearchQuery] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Selected process details
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobItem | null>(null);
  const [jobLogs, setJobLogs] = useState<JobLogs | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);

  // Action status feedback
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [actionPendingId, setActionPendingId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [jobsRes, statsRes] = await Promise.all([
        fetchJobs({
          mediaAssetId: selectedVideoId !== 'all' ? selectedVideoId : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          search: searchQuery.trim() || undefined,
        }),
        fetchQueueStats().catch(() => null),
      ]);
      setJobs(jobsRes.items || []);
      setStats(statsRes);
    } catch {
      // ignore network errors on poll
    } finally {
      setLoading(false);
    }
  }, [selectedVideoId, statusFilter, searchQuery]);

  useEffect(() => {
    void loadData();
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      void loadData();
    }, 3000);
    return () => clearInterval(interval);
  }, [loadData, autoRefresh]);

  // Keep selectedJob synced with updated list
  useEffect(() => {
    if (selectedJobId) {
      const found = jobs.find((j) => j.id === selectedJobId);
      if (found) setSelectedJob(found);
    }
  }, [jobs, selectedJobId]);

  const handleOpenDetails = async (job: JobItem) => {
    setSelectedJobId(job.id);
    setSelectedJob(job);
    setLogsLoading(true);
    setActionMessage(null);
    try {
      const logsData = await fetchJobLogs(job.id);
      setJobLogs(logsData);
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load process logs',
      });
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCancel = async (jobId: string) => {
    setActionPendingId(jobId);
    try {
      await cancelJob(jobId);
      setActionMessage({ type: 'success', text: `Process ${jobId} cancellation requested.` });
      await loadData();
      if (selectedJobId === jobId) {
        const logsData = await fetchJobLogs(jobId).catch(() => null);
        if (logsData) setJobLogs(logsData);
      }
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Cancellation failed',
      });
    } finally {
      setActionPendingId(null);
    }
  };

  const handleRetry = async (jobId: string, newAttempt = true) => {
    setActionPendingId(jobId);
    try {
      const res = await retryJob(jobId, newAttempt);
      setActionMessage({
        type: 'success',
        text: newAttempt
          ? `Created new attempt process ${res.id} (linked to ${jobId}).`
          : `Restarted process ${jobId}.`,
      });
      await loadData();
      if (selectedJobId === jobId) {
        setSelectedJobId(res.id);
        void handleOpenDetails(res);
      }
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Retry failed',
      });
    } finally {
      setActionPendingId(null);
    }
  };

  const handleDeleteRecord = async (jobId: string) => {
    if (!window.confirm(`Delete record for process ${jobId}? Associated video media will NOT be deleted.`)) {
      return;
    }
    setActionPendingId(jobId);
    try {
      await deleteJob(jobId);
      setActionMessage({ type: 'success', text: `Process record ${jobId} deleted.` });
      if (selectedJobId === jobId) {
        setSelectedJobId(null);
        setSelectedJob(null);
        setJobLogs(null);
      }
      await loadData();
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to delete process record',
      });
    } finally {
      setActionPendingId(null);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Delete all completed and cancelled process records? Active jobs will remain unaffected.')) {
      return;
    }
    setLoading(true);
    try {
      const res = await deleteJobHistory('completed');
      setActionMessage({
        type: 'success',
        text: `Cleared ${res.deleted_count} finished process records from history.`,
      });
      await loadData();
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to clear process history',
      });
    } finally {
      setLoading(false);
    }
  };

  // Video Options Map
  const videoOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const j of jobs) {
      if (j.media_asset_id) {
        map.set(j.media_asset_id, j.video_title || `Video ${j.media_asset_id.slice(0, 8)}...`);
      }
    }
    return Array.from(map.entries()).map(([id, title]) => ({ id, title }));
  }, [jobs]);

  // Filtering
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      // Category filter
      if (categoryFilter !== 'all') {
        const cat = categorizeJobType(job.job_type);
        if (cat !== categoryFilter) return false;
      }
      // Status filter
      if (statusFilter !== 'all') {
        if (statusFilter === 'running' && job.status !== 'running') return false;
        if (statusFilter === 'queued' && !['queued', 'pending'].includes(job.status)) return false;
        if (statusFilter === 'completed' && job.status !== 'completed') return false;
        if (statusFilter === 'failed' && !['failed', 'interrupted'].includes(job.status)) return false;
        if (statusFilter === 'cancelled' && !['cancelled', 'cancelling'].includes(job.status)) return false;
      }
      // Video filter
      if (selectedVideoId !== 'all') {
        if (job.media_asset_id !== selectedVideoId) return false;
      }
      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesId = job.id.toLowerCase().includes(q);
        const matchesType = job.job_type.toLowerCase().includes(q);
        const matchesStage = (job.current_stage || '').toLowerCase().includes(q);
        const matchesVideo = (job.video_title || '').toLowerCase().includes(q);
        const matchesAssetId = (job.media_asset_id || '').toLowerCase().includes(q);
        if (!matchesId && !matchesType && !matchesStage && !matchesVideo && !matchesAssetId) {
          return false;
        }
      }
      return true;
    });
  }, [jobs, categoryFilter, statusFilter, selectedVideoId, searchQuery]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#141415] text-[#ededed] overflow-hidden select-none">
      {/* Top Header */}
      <div className="p-4 border-b border-[#27272a] bg-[#19191b] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-semibold tracking-tight text-white">Processes</h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#232325] border border-[#27272a] text-[#a1a1aa]">
              Central Process Manager
            </span>
            <span className="sr-only">Working Queue &amp; Jobs</span>
          </div>
          <p className="text-xs text-[#a1a1aa] mt-0.5">
            Monitor real-time task execution, control lifecycle (cancel, retry, clean), and trace worker logs across all videos.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`text-xs ${autoRefresh ? 'text-indigo-400' : 'text-[#a1a1aa]'}`}
            title={autoRefresh ? 'Live updates active (polling every 3s)' : 'Live updates paused'}
          >
            <Clock className="w-3.5 h-3.5 mr-1" />
            <span>{autoRefresh ? 'Live' : 'Paused'}</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => void loadData()}
            className="flex items-center gap-1.5 text-xs text-[#a1a1aa] hover:text-white"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleClearHistory}
            className="flex items-center gap-1.5 text-xs text-[#a1a1aa] hover:text-white hover:border-red-500/50"
            title="Remove completed and cancelled process records"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Completed History</span>
          </Button>
        </div>
      </div>

      {/* Action Message Alert */}
      {actionMessage && (
        <div
          className={`px-4 py-2 text-xs flex items-center justify-between shrink-0 border-b ${
            actionMessage.type === 'error'
              ? 'bg-red-500/10 border-red-500/30 text-red-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === 'error' ? (
              <AlertCircle className="w-4 h-4 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="p-1 hover:opacity-75 transition"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Metric Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div
            onClick={() => setStatusFilter('all')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'all' ? 'border-indigo-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-[#a1a1aa] uppercase tracking-wider">Total Processes</div>
            <div className="text-2xl font-bold font-mono mt-1 text-white">
              {stats?.total_jobs ?? jobs.length}
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('running')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'running' ? 'border-indigo-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 animate-pulse" />
              <span>Running</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-indigo-400">
              {stats?.running ?? jobs.filter((j) => j.status === 'running').length}
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('queued')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'queued' ? 'border-amber-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Queued</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-amber-400">
              {stats?.queued ?? jobs.filter((j) => ['queued', 'pending'].includes(j.status)).length}
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('completed')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'completed' ? 'border-emerald-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Completed</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-emerald-400">
              {stats?.completed ?? jobs.filter((j) => j.status === 'completed').length}
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('failed')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'failed' ? 'border-red-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-red-400 uppercase tracking-wider flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Failed</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-red-400">
              {stats?.failed ?? jobs.filter((j) => ['failed', 'interrupted'].includes(j.status)).length}
            </div>
          </div>

          <div
            onClick={() => setStatusFilter('cancelled')}
            className={`p-3 rounded-xl bg-[#19191b] border cursor-pointer transition ${
              statusFilter === 'cancelled' ? 'border-slate-500 shadow-sm' : 'border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="text-[11px] font-medium text-[#a1a1aa] uppercase tracking-wider flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5" />
              <span>Cancelled</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-[#a1a1aa]">
              {stats?.cancelled ?? jobs.filter((j) => ['cancelled', 'cancelling'].includes(j.status)).length}
            </div>
          </div>
        </div>

        {/* Visual Queue Bar Distribution & Task Types */}
        {jobs.length > 0 && (
          <div className="p-3 rounded-xl bg-[#19191b] border border-[#27272a] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-[#a1a1aa] uppercase tracking-wider text-[10px]">
                Queue Status &amp; Task Type Distribution
              </span>
              <span className="text-[#71717a] text-[11px] font-mono">
                {jobs.filter((j) => j.status === 'running').length} active worker(s) / {jobs.length} total
              </span>
            </div>

            <div className="h-2 w-full bg-[#27272a] rounded-full flex overflow-hidden">
              <div
                style={{ width: `${((stats?.running ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%` }}
                className="bg-indigo-500 transition-all duration-300"
                title={`Running: ${stats?.running ?? 0}`}
              />
              <div
                style={{ width: `${((stats?.queued ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%` }}
                className="bg-amber-500 transition-all duration-300"
                title={`Queued: ${stats?.queued ?? 0}`}
              />
              <div
                style={{ width: `${((stats?.completed ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%` }}
                className="bg-emerald-500 transition-all duration-300"
                title={`Completed: ${stats?.completed ?? 0}`}
              />
              <div
                style={{ width: `${((stats?.failed ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%` }}
                className="bg-red-500 transition-all duration-300"
                title={`Failed: ${stats?.failed ?? 0}`}
              />
              <div
                style={{ width: `${((stats?.cancelled ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%` }}
                className="bg-[#52525b] transition-all duration-300"
                title={`Cancelled: ${stats?.cancelled ?? 0}`}
              />
            </div>

            {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-[#27272a] text-[11px]">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-[#71717a]">Task Types:</span>
                {Object.entries(stats.by_type).map(([jtype, count]) => (
                  <span
                    key={jtype}
                    className="px-2 py-0.5 rounded-md bg-[#141415] border border-[#27272a] text-[#a1a1aa] font-mono flex items-center gap-1.5"
                  >
                    <span>{jtype.replace(/_/g, ' ')}</span>
                    <strong className="text-indigo-400 font-bold">{count}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Filters, Categories & Search Toolbar */}
        <div className="space-y-3 pt-1">
          {/* Category Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-medium text-[#71717a] uppercase tracking-wider mr-1">
                Category:
              </span>
              {(
                [
                  { id: 'all', label: 'All' },
                  { id: 'media', label: 'Media' },
                  { id: 'analysis', label: 'Analysis' },
                  { id: 'generation', label: 'Generation' },
                  { id: 'rendering', label: 'Rendering' },
                  { id: 'storage', label: 'Storage' },
                ] as Array<{ id: CategoryFilter; label: string }>
              ).map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setCategoryFilter(cat.id)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                    categoryFilter === cat.id
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-[#19191b] border border-[#27272a] text-[#a1a1aa] hover:text-white hover:border-[#3f3f46]'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Video Selector */}
            {videoOptions.length > 0 && (
              <div className="flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-[#71717a]" />
                <select
                  value={selectedVideoId}
                  onChange={(e) => setSelectedVideoId(e.target.value)}
                  className="bg-[#19191b] border border-[#27272a] rounded-lg text-xs text-[#ededed] px-2.5 py-1 focus:outline-none focus:border-indigo-500 max-w-[220px] truncate"
                >
                  <option value="all">All Videos ({videoOptions.length})</option>
                  {videoOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.title}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Status Tabs and Search Input */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-medium text-[#71717a] uppercase tracking-wider mr-1">
                Status:
              </span>
              {(['all', 'running', 'queued', 'completed', 'failed', 'cancelled'] as StatusFilter[]).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition ${
                    statusFilter === st
                      ? 'bg-[#27272a] text-white border border-[#3f3f46]'
                      : 'bg-[#19191b] border border-[#27272a] text-[#a1a1aa] hover:text-white'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <div className="relative w-72">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID, type, video, or stage..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[#19191b] border border-[#27272a] text-xs text-[#ededed] focus:outline-none focus:border-indigo-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#71717a] hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Processes Table */}
        <div className="rounded-xl border border-[#27272a] bg-[#19191b] overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#27272a] bg-[#232325] text-[#a1a1aa] uppercase text-[10px] font-semibold tracking-wider">
                  <th className="py-2.5 px-3">Process ID</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Video / Scope</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Progress</th>
                  <th className="py-2.5 px-3">Current Stage</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272a]">
                {filteredJobs.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-[#71717a]">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Activity className="w-6 h-6 text-[#3f3f46]" />
                        <span>No processes found matching the selected filters.</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredJobs.map((job) => {
                    const isRunning = job.status === 'running';
                    const isFailed = ['failed', 'interrupted'].includes(job.status);
                    const isCancelled = ['cancelled', 'cancelling'].includes(job.status);
                    const isCompleted = job.status === 'completed';
                    const isQueued = ['queued', 'pending'].includes(job.status);
                    const durationText = formatDuration(job.started_at, job.completed_at);

                    return (
                      <tr
                        key={job.id}
                        onClick={() => void handleOpenDetails(job)}
                        className={`hover:bg-[#232325] transition cursor-pointer group ${
                          selectedJobId === job.id ? 'bg-[#232325]' : ''
                        }`}
                      >
                        {/* Process ID & Lineage */}
                        <td className="py-2.5 px-3 font-mono font-medium text-white">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate max-w-[120px]" title={job.id}>
                              {job.id}
                            </span>
                            {job.retry_count > 0 && (
                              <span
                                className="px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-400 font-sans"
                                title={`Retry attempt #${job.retry_count}`}
                              >
                                R{job.retry_count}
                              </span>
                            )}
                            {job.parent_job_id && (
                              <span
                                className="px-1.5 py-0.2 rounded bg-indigo-500/10 border border-indigo-500/30 text-[10px] text-indigo-400 font-sans truncate max-w-[60px]"
                                title={`Parent process: ${job.parent_job_id}`}
                              >
                                child
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Process Type */}
                        <td className="py-2.5 px-3 font-medium text-[#ededed]">
                          <span className="capitalize">
                            {job.job_type.replace(/_/g, ' ')}
                          </span>
                        </td>

                        {/* Video / Scope */}
                        <td className="py-2.5 px-3 text-[#a1a1aa] truncate max-w-[180px]">
                          {job.video_title ? (
                            <span className="text-white hover:underline" title={job.video_title}>
                              {job.video_title}
                            </span>
                          ) : job.media_asset_id ? (
                            <span className="font-mono text-[11px] text-[#71717a]">
                              {job.media_asset_id.slice(0, 8)}...
                            </span>
                          ) : (
                            <span className="text-[#71717a]">System</span>
                          )}
                        </td>

                        {/* Status */}
                        <td className="py-2.5 px-3">
                          <Badge
                            variant={
                              isRunning
                                ? 'purple'
                                : isCompleted
                                ? 'success'
                                : isFailed
                                ? 'danger'
                                : isCancelled
                                ? 'default'
                                : 'warning'
                            }
                          >
                            {job.status.toUpperCase()}
                          </Badge>
                        </td>

                        {/* Progress */}
                        <td className="py-2.5 px-3 w-32">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[10px] text-[#a1a1aa] font-mono">
                              <span>{Math.round(job.progress_pct)}%</span>
                              {job.estimated_remaining_seconds ? (
                                <span>~{Math.round(job.estimated_remaining_seconds)}s</span>
                              ) : null}
                            </div>
                            <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all duration-300 ${
                                  isRunning
                                    ? 'bg-indigo-500'
                                    : isCompleted
                                    ? 'bg-emerald-500'
                                    : isFailed
                                    ? 'bg-red-500'
                                    : 'bg-[#52525b]'
                                }`}
                                style={{ width: `${Math.min(job.progress_pct, 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Current Stage */}
                        <td className="py-2.5 px-3 font-mono text-[#a1a1aa] text-[11px] truncate max-w-[140px]">
                          {job.current_stage || '—'}
                        </td>

                        {/* Duration */}
                        <td className="py-2.5 px-3 font-mono text-[#a1a1aa] text-[11px] whitespace-nowrap">
                          {durationText}
                        </td>

                        {/* Created At */}
                        <td className="py-2.5 px-3 font-mono text-[#71717a] text-[11px] whitespace-nowrap">
                          {formatTimeOnly(job.created_at)}
                        </td>

                        {/* Actions */}
                        <td className="py-2.5 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            {/* Inspect Logs Button */}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void handleOpenDetails(job)}
                              title="Inspect Details & Logs"
                              className="p-1.5 h-auto text-xs text-[#a1a1aa] hover:text-white"
                            >
                              <FileText className="w-3.5 h-3.5" />
                            </Button>

                            {/* Cancel Process Button */}
                            {(isRunning || isQueued) && (
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => void handleCancel(job.id)}
                                disabled={actionPendingId === job.id}
                                title="Stop / Cancel Process (Terminates worker subprocess tree)"
                                className="p-1.5 h-auto text-xs"
                              >
                                <X className="w-3.5 h-3.5" />
                              </Button>
                            )}

                            {/* Retry Process Button */}
                            {(isFailed || isCancelled) && (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => void handleRetry(job.id, true)}
                                disabled={actionPendingId === job.id}
                                title="Retry Process (Creates new attempt linked to this run)"
                                className="p-1.5 h-auto text-xs text-[#a1a1aa] hover:text-white"
                              >
                                <RotateCcw className="w-3.5 h-3.5" />
                              </Button>
                            )}

                            {/* Delete Record Button */}
                            {(isCompleted || isFailed || isCancelled) && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => void handleDeleteRecord(job.id)}
                                disabled={actionPendingId === job.id}
                                title="Delete Process Record (Does not delete source video or media)"
                                className="p-1.5 h-auto text-xs text-[#71717a] hover:text-red-400"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Process Details & Logs Drawer */}
      {selectedJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-3xl bg-[#19191b] border border-[#27272a] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            {/* Drawer Header */}
            <div className="p-4 border-b border-[#27272a] flex items-center justify-between bg-[#232325]">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-400" />
                  <span>Process Details & Execution Trace</span>
                </h3>
                <div className="flex items-center gap-2 mt-0.5 font-mono text-xs text-[#a1a1aa]">
                  <span>ID: {selectedJobId}</span>
                  {selectedJob?.parent_job_id && (
                    <span className="text-indigo-400">
                      (retry of {selectedJob.parent_job_id})
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setSelectedJobId(null)}
                className="p-1.5 text-[#a1a1aa] hover:text-white rounded-lg transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-4 overflow-y-auto flex-1 space-y-4 text-xs font-mono">
              {logsLoading ? (
                <div className="py-12 text-center text-[#a1a1aa] flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Loading process execution logs...</span>
                </div>
              ) : (
                <>
                  {/* Metadata Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-[#232325] rounded-xl border border-[#27272a]">
                    <div>
                      <span className="text-[#71717a] block text-[10px] uppercase font-sans font-semibold">
                        Task Type
                      </span>
                      <span className="text-white font-medium capitalize mt-0.5 block truncate">
                        {(selectedJob?.job_type || jobLogs?.job_type || '—').replace(/_/g, ' ')}
                      </span>
                    </div>

                    <div>
                      <span className="text-[#71717a] block text-[10px] uppercase font-sans font-semibold">
                        Status
                      </span>
                      <div className="mt-0.5">
                        <Badge
                          variant={
                            (selectedJob?.status || jobLogs?.status) === 'running'
                              ? 'purple'
                              : (selectedJob?.status || jobLogs?.status) === 'completed'
                              ? 'success'
                              : ['failed', 'interrupted'].includes(selectedJob?.status || jobLogs?.status || '')
                              ? 'danger'
                              : 'default'
                          }
                        >
                          {(selectedJob?.status || jobLogs?.status || 'UNKNOWN').toUpperCase()}
                        </Badge>
                      </div>
                    </div>

                    <div>
                      <span className="text-[#71717a] block text-[10px] uppercase font-sans font-semibold">
                        Progress
                      </span>
                      <span className="text-white font-medium mt-0.5 block">
                        {Math.round(selectedJob?.progress_pct ?? jobLogs?.progress_percent ?? 0)}%
                      </span>
                    </div>

                    <div>
                      <span className="text-[#71717a] block text-[10px] uppercase font-sans font-semibold">
                        Stage
                      </span>
                      <span className="text-white font-medium mt-0.5 block truncate">
                        {selectedJob?.current_stage || jobLogs?.current_stage || '—'}
                      </span>
                    </div>
                  </div>

                  {/* Video & Timestamps Card */}
                  <div className="p-3 bg-[#141415] rounded-xl border border-[#27272a] space-y-2 text-[11px]">
                    {selectedJob?.video_title && (
                      <div className="flex items-center justify-between pb-1.5 border-b border-[#27272a]">
                        <span className="text-[#71717a] font-sans font-medium">Video Title:</span>
                        <span className="text-white font-sans font-medium">{selectedJob.video_title}</span>
                      </div>
                    )}
                    {selectedJob?.media_asset_id && (
                      <div className="flex items-center justify-between pb-1.5 border-b border-[#27272a]">
                        <span className="text-[#71717a] font-sans font-medium">Media Asset ID:</span>
                        <span className="text-[#a1a1aa] font-mono">{selectedJob.media_asset_id}</span>
                      </div>
                    )}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 font-mono text-[10px] text-[#a1a1aa]">
                      <div>
                        <span className="text-[#71717a] block">Created:</span>
                        <span>{selectedJob?.created_at || '—'}</span>
                      </div>
                      <div>
                        <span className="text-[#71717a] block">Started:</span>
                        <span>{selectedJob?.started_at || '—'}</span>
                      </div>
                      <div>
                        <span className="text-[#71717a] block">Completed:</span>
                        <span>{selectedJob?.completed_at || '—'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Error Details if any */}
                  {(selectedJob?.error_message || jobLogs?.error_message) && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs font-sans">
                      <span className="font-bold block text-[10px] uppercase tracking-wider text-red-300">
                        Error Information:
                      </span>
                      <p className="mt-1 font-mono text-[11px] leading-relaxed">
                        {selectedJob?.error_message || jobLogs?.error_message}
                      </p>
                    </div>
                  )}

                  {/* Result Metadata / Outputs if any */}
                  {selectedJob?.result_metadata && Object.keys(selectedJob.result_metadata).length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[#71717a] block text-[10px] uppercase font-sans font-semibold">
                        Result Outputs & Metadata:
                      </span>
                      <pre className="p-3 bg-[#141415] border border-[#27272a] rounded-xl text-[11px] text-[#a1a1aa] overflow-x-auto">
                        {JSON.stringify(selectedJob.result_metadata, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Log Trace Viewer */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-sans text-[#71717a]">
                      <span className="uppercase font-semibold">Execution Log Trace:</span>
                      <span>{jobLogs?.logs?.length || 0} entries</span>
                    </div>
                    <div className="p-3 bg-[#141415] border border-[#27272a] rounded-xl space-y-1 max-h-56 overflow-y-auto text-[11px]">
                      {jobLogs?.logs && jobLogs.logs.length > 0 ? (
                        jobLogs.logs.map((logLine, idx) => (
                          <div key={idx} className="text-[#a1a1aa] leading-relaxed font-mono">
                            {logLine}
                          </div>
                        ))
                      ) : (
                        <div className="py-4 text-center text-[#71717a]">No log lines recorded.</div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Drawer Footer Controls */}
            <div className="p-3 border-t border-[#27272a] flex items-center justify-between bg-[#232325]">
              <div className="flex items-center gap-2">
                {selectedJob && (selectedJob.status === 'running' || selectedJob.status === 'queued') && (
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => void handleCancel(selectedJob.id)}
                    disabled={actionPendingId === selectedJob.id}
                    leftIcon={<X className="w-3.5 h-3.5" />}
                  >
                    Cancel Process
                  </Button>
                )}

                {selectedJob && (['failed', 'interrupted', 'cancelled'].includes(selectedJob.status)) && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void handleRetry(selectedJob.id, true)}
                    disabled={actionPendingId === selectedJob.id}
                    leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                  >
                    Retry Attempt
                  </Button>
                )}

                {selectedJob && (['completed', 'failed', 'cancelled'].includes(selectedJob.status)) && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void handleDeleteRecord(selectedJob.id)}
                    disabled={actionPendingId === selectedJob.id}
                    className="text-[#71717a] hover:text-red-400"
                    leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                  >
                    Delete Record
                  </Button>
                )}
              </div>

              <Button size="sm" variant="secondary" onClick={() => setSelectedJobId(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Parity alias export
export const ProcessesManagerView = WorkingQueueView;
