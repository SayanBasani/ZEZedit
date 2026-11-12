import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  RefreshCw,
  Search,
  X,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  cancelJob,
  fetchJobLogs,
  fetchJobs,
  fetchQueueStats,
  retryJob,
} from '../../services/apiClient';
import { JobItem, ProjectItem } from '../../types/projects';
import { JobLogs, QueueStats } from '../../types/system';

interface WorkingQueueViewProps {
  projects: ProjectItem[];
  onOpenProject?: (projectId: string) => void;
}

type StatusFilter = 'all' | 'running' | 'queued' | 'completed' | 'failed' | 'cancelled';

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

export const WorkingQueueView: React.FC<WorkingQueueViewProps> = ({
  projects,
  onOpenProject,
}) => {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobLogs, setJobLogs] = useState<JobLogs | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [jobsRes, statsRes] = await Promise.all([
        fetchJobs(),
        fetchQueueStats().catch(() => null),
      ]);
      setJobs(jobsRes.items);
      setStats(statsRes);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
    const interval = setInterval(() => {
      void loadData();
    }, 4000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleOpenLogs = async (jobId: string) => {
    setSelectedJobId(jobId);
    setLogsLoading(true);
    setActionError(null);
    try {
      const logsData = await fetchJobLogs(jobId);
      setJobLogs(logsData);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCancel = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      await loadData();
      if (selectedJobId === jobId) {
        void handleOpenLogs(jobId);
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Cancel failed');
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await retryJob(jobId);
      await loadData();
      if (selectedJobId === jobId) {
        void handleOpenLogs(jobId);
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Retry failed');
    }
  };

  const projectMap = new Map(projects.map((p) => [p.id, p.name]));

  // Filtering
  const filteredJobs = jobs.filter((job) => {
    if (statusFilter !== 'all') {
      if (statusFilter === 'running' && job.status !== 'running') return false;
      if (statusFilter === 'queued' && !['queued', 'pending'].includes(job.status)) return false;
      if (statusFilter === 'completed' && job.status !== 'completed') return false;
      if (statusFilter === 'failed' && !['failed', 'interrupted'].includes(job.status)) return false;
      if (statusFilter === 'cancelled' && !['cancelled', 'cancelling'].includes(job.status)) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const projName = (job.project_id && projectMap.get(job.project_id)) || '';
      return (
        job.id.toLowerCase().includes(q) ||
        job.job_type.toLowerCase().includes(q) ||
        (job.current_stage && job.current_stage.toLowerCase().includes(q)) ||
        projName.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-canvas text-text-primary overflow-hidden">
      {/* Header Bar */}
      <div className="p-4 border-b border-border bg-surface/50 backdrop-blur-sm flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-semibold tracking-tight">Working Queue & Jobs</h1>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Monitor real-time background task execution, worker state machines, and task logs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => void loadData()}
            className="flex items-center gap-1.5"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {actionError && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="p-1 hover:text-red-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Queue Metrics Chart & Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-text-muted uppercase">Total Jobs</div>
            <div className="text-2xl font-bold font-mono mt-1 text-text-primary">
              {stats?.total_jobs ?? jobs.length}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-indigo-400 uppercase flex items-center gap-1">
              <Activity className="w-3 h-3 animate-pulse" />
              <span>Running</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-indigo-400">
              {stats?.running ?? jobs.filter((j) => j.status === 'running').length}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-amber-400 uppercase flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>Pending</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-amber-400">
              {stats?.queued ?? jobs.filter((j) => ['queued', 'pending'].includes(j.status)).length}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-emerald-400 uppercase flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>Completed</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-emerald-400">
              {stats?.completed ?? jobs.filter((j) => j.status === 'completed').length}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-red-400 uppercase flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              <span>Failed</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-red-400">
              {stats?.failed ?? jobs.filter((j) => ['failed', 'interrupted'].includes(j.status)).length}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-surface border border-border">
            <div className="text-[11px] font-medium text-text-muted uppercase flex items-center gap-1">
              <XCircle className="w-3 h-3" />
              <span>Cancelled</span>
            </div>
            <div className="text-2xl font-bold font-mono mt-1 text-text-muted">
              {stats?.cancelled ?? jobs.filter((j) => ['cancelled', 'cancelling'].includes(j.status)).length}
            </div>
          </div>
        </div>

        {/* Visual Queue Bar Distribution */}
        {jobs.length > 0 && (
          <div className="p-3.5 rounded-xl bg-surface border border-border space-y-2.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-text-secondary uppercase tracking-wider text-[10px]">
                Queue Status & Task Type Distribution
              </span>
              <span className="text-text-muted text-[11px] font-mono">
                {jobs.filter((j) => j.status === 'running').length} active worker(s) / {jobs.length} total
              </span>
            </div>
            <div className="h-2.5 w-full bg-border rounded-full flex overflow-hidden">
              <div
                style={{
                  width: `${((stats?.running ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%`,
                }}
                className="bg-indigo-500 transition-all duration-300"
                title={`Running: ${stats?.running ?? 0}`}
              />
              <div
                style={{
                  width: `${((stats?.queued ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%`,
                }}
                className="bg-amber-500 transition-all duration-300"
                title={`Pending: ${stats?.queued ?? 0}`}
              />
              <div
                style={{
                  width: `${((stats?.completed ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%`,
                }}
                className="bg-emerald-500 transition-all duration-300"
                title={`Completed: ${stats?.completed ?? 0}`}
              />
              <div
                style={{
                  width: `${((stats?.failed ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%`,
                }}
                className="bg-red-500 transition-all duration-300"
                title={`Failed: ${stats?.failed ?? 0}`}
              />
              <div
                style={{
                  width: `${((stats?.cancelled ?? 0) / Math.max(stats?.total_jobs ?? 1, 1)) * 100}%`,
                }}
                className="bg-slate-600 transition-all duration-300"
                title={`Cancelled: ${stats?.cancelled ?? 0}`}
              />
            </div>

            {/* Task Type Breakdown Pills */}
            {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/50 text-[11px]">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-text-muted">Task Types:</span>
                {Object.entries(stats.by_type).map(([jtype, count]) => (
                  <span
                    key={jtype}
                    className="px-2 py-0.5 rounded-md bg-canvas border border-border text-text-secondary font-mono flex items-center gap-1.5"
                  >
                    <span>{jtype.replace(/_/g, ' ')}</span>
                    <strong className="text-indigo-400 font-bold">{count}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Filters and Search */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            {(['all', 'running', 'queued', 'completed', 'failed', 'cancelled'] as StatusFilter[]).map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-surface border border-border text-text-secondary hover:text-text-primary hover:border-border-hover'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search jobs by ID, type, or project..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-text-primary focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Jobs Table */}
        <div className="rounded-xl border border-border bg-surface overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-hover/50 text-text-muted uppercase text-[10px] font-semibold tracking-wider">
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Task Type</th>
                  <th className="py-2.5 px-3">Project / Video</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Progress</th>
                  <th className="py-2.5 px-3">Current Stage</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredJobs.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-text-muted">
                      No jobs matching the current filter.
                    </td>
                  </tr>
                ) : (
                  filteredJobs.map((job) => {
                    const projName = job.project_id ? projectMap.get(job.project_id) || job.project_id : '—';
                    const isRunning = job.status === 'running';
                    const isFailed = ['failed', 'interrupted'].includes(job.status);
                    const isCancelled = ['cancelled', 'cancelling'].includes(job.status);
                    const isCompleted = job.status === 'completed';
                    const durationText = formatDuration(job.started_at, job.completed_at);

                    return (
                      <tr key={job.id} className="hover:bg-surface-hover/60 transition group">
                        <td className="py-2.5 px-3 font-mono font-medium text-text-primary">
                          <div className="flex items-center gap-1.5">
                            <span>{job.id}</span>
                            {job.retry_count > 0 && (
                              <span className="px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-400 font-sans">
                                R{job.retry_count}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-text-primary">
                          {job.job_type.replace(/_/g, ' ')}
                        </td>
                        <td className="py-2.5 px-3 text-text-secondary truncate max-w-[160px]">
                          {projName}
                        </td>
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
                        <td className="py-2.5 px-3 w-32">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[10px] text-text-muted font-mono">
                              <span>{Math.round(job.progress_pct)}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all duration-300 ${
                                  isRunning ? 'bg-indigo-500' : isCompleted ? 'bg-emerald-500' : 'bg-slate-500'
                                }`}
                                style={{ width: `${Math.min(job.progress_pct, 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-text-muted text-[11px] truncate max-w-[140px]">
                          {job.current_stage || '—'}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-text-secondary text-[11px] whitespace-nowrap">
                          {durationText}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-text-muted text-[11px] whitespace-nowrap">
                          {job.created_at.slice(11, 19)}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void handleOpenLogs(job.id)}
                              title="Inspect Job Logs"
                              className="p-1.5 h-auto text-xs"
                            >
                              <FileText className="w-3.5 h-3.5" />
                            </Button>

                            {isRunning && (
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => void handleCancel(job.id)}
                                title="Cancel Job"
                                className="p-1.5 h-auto text-xs"
                              >
                                <X className="w-3.5 h-3.5" />
                              </Button>
                            )}

                            {(isFailed || isCancelled) && (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => void handleRetry(job.id)}
                                title="Retry Job"
                                className="p-1.5 h-auto text-xs"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                              </Button>
                            )}

                            {job.project_id && onOpenProject && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => onOpenProject(job.project_id!)}
                                title="Open Associated Project"
                                className="p-1.5 h-auto text-xs"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
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

      {/* Job Execution Logs Modal / Drawer */}
      {selectedJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  <span>Job Details & Execution Timeline</span>
                </h3>
                <span className="font-mono text-xs text-text-muted">{selectedJobId}</span>
              </div>
              <button
                onClick={() => setSelectedJobId(null)}
                className="p-1.5 text-text-muted hover:text-text-primary rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-3 font-mono text-xs">
              {logsLoading ? (
                <div className="py-8 text-center text-text-muted flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Loading execution logs...</span>
                </div>
              ) : jobLogs ? (
                <>
                  <div className="grid grid-cols-2 gap-2 p-3 bg-surface-hover/50 rounded-xl border border-border">
                    <div>
                      <span className="text-text-muted block text-[10px] uppercase">Type</span>
                      <span className="text-text-primary font-bold">{jobLogs.job_type}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px] uppercase">Status</span>
                      <span className="text-text-primary font-bold">{jobLogs.status.toUpperCase()}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px] uppercase">Progress</span>
                      <span className="text-text-primary font-bold">{jobLogs.progress_percent}%</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px] uppercase">Stage</span>
                      <span className="text-text-primary font-bold">{jobLogs.current_stage || '—'}</span>
                    </div>
                  </div>

                  {jobLogs.error_message && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs">
                      <span className="font-bold block text-[10px] uppercase">Error Details:</span>
                      <span>{jobLogs.error_message}</span>
                    </div>
                  )}

                  <div className="space-y-1 pt-2">
                    <span className="text-text-muted block text-[10px] uppercase font-semibold">
                      Timeline Log Trace:
                    </span>
                    <div className="p-3 bg-canvas border border-border rounded-xl space-y-1.5 max-h-60 overflow-y-auto">
                      {jobLogs.logs.map((logLine, idx) => (
                        <div key={idx} className="text-text-secondary leading-relaxed">
                          {logLine}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-8 text-center text-text-muted">No logs recorded.</div>
              )}
            </div>

            <div className="p-3 border-t border-border flex justify-end gap-2 bg-surface/80">
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
