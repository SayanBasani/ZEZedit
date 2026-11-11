import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  Film,
  FolderLock,
  RefreshCw,
  Server,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { fetchHealth, fetchSystemInfo } from '../../services/apiClient';
import { HealthResponse, SystemInfoResponse } from '../../types/health';

const MODULE_ROADMAP = [
  { name: 'Foundation, Storage Boundary & Migrations', status: 'Implemented', milestone: 'M1' },
  { name: 'Media Library Import, Proxies & Relinking', status: 'Planned', milestone: 'M2' },
  { name: 'Authoritative Single Job Orchestrator & Logs', status: 'Planned', milestone: 'M3' },
  { name: 'AI Provider Inventory & Settings Diagnostics', status: 'Planned', milestone: 'M4' },
  { name: 'Video Analysis & Highlight Discovery', status: 'Planned', milestone: 'M5' },
  { name: 'Smart Reframing & Non-Destructive Revisions', status: 'Planned', milestone: 'M6' },
  { name: 'Multi-Track Timeline Editor & Undo/Redo', status: 'Planned', milestone: 'M7' },
  { name: 'Conversational AI Video Editor (Schema-Gated)', status: 'Planned', milestone: 'M8' },
  { name: 'Independent Character Extraction Studio', status: 'Planned', milestone: 'M9' },
  { name: 'Rendering, Export Validation & Backup/Restore', status: 'Planned', milestone: 'M10' },
] as const;

export const FoundationOverview: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, info] = await Promise.all([fetchHealth(), fetchSystemInfo()]);
      setHealth(h);
      setSysInfo(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-white">ZezEdit 2.0 Foundation</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-indigo-950/90 text-indigo-300 border border-indigo-800/50">
              Milestone 1
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Local-first CPU-ready AI video editing architecture &amp; safe storage workspace.
          </p>
        </div>

        <button
          onClick={() => void loadStatus()}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 disabled:opacity-50 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Backend Probe
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/50 border border-red-800/60 text-red-200 text-xs flex items-start gap-3">
          <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Backend Connection Failed</p>
            <p className="text-red-300/90 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Live Diagnostics Grid */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* API & Runtime */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Backend API
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[11px] font-medium flex items-center gap-1 ${
                  health.status === 'ready'
                    ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50'
                    : 'bg-amber-950/80 text-amber-300 border border-amber-800/50'
                }`}
              >
                <Activity className="w-3 h-3" />
                {health.status.toUpperCase()}
              </span>
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <p>Version: {health.app_version}</p>
              <p>Env: {health.environment}</p>
              {sysInfo && (
                <p>
                  CPU Mode: {sysInfo.execution_mode} ({sysInfo.cpu_count} cores)
                </p>
              )}
            </div>
          </div>

          {/* SQLite & Migrations */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
                <Database className="w-4 h-4 text-sky-400" />
                SQLite WAL &amp; Migrations
              </span>
              {health.database.connected ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <p>Journal: {health.database.journal_mode.toUpperCase()}</p>
              <p>Current Migration: {health.database.current_migration || 'none'}</p>
              <p className="truncate" title={health.database.path}>
                Path: {health.database.path}
              </p>
            </div>
          </div>

          {/* Storage Boundary */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
                <FolderLock className="w-4 h-4 text-emerald-400" />
                Protected Storage Root
              </span>
              {health.storage.writable && health.storage.buckets_ready ? (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <p className="truncate" title={health.storage.root}>
                Root: {health.storage.root}
              </p>
              <p>Writable: {health.storage.writable ? 'Yes' : 'No'}</p>
              <p>Buckets Ready: {health.storage.buckets_ready ? 'All 11 isolated' : 'Incomplete'}</p>
            </div>
          </div>

          {/* Media Binaries */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
                <Film className="w-4 h-4 text-purple-400" />
                Media Engines (FFmpeg / FFprobe)
              </span>
              {health.ffmpeg.available && health.ffprobe.available ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-amber-400" />
              )}
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <p className="truncate" title={health.ffmpeg.version || undefined}>
                FFmpeg: {health.ffmpeg.available ? health.ffmpeg.version : 'Missing'}
              </p>
              <p className="truncate" title={health.ffprobe.version || undefined}>
                FFprobe: {health.ffprobe.available ? health.ffprobe.version : 'Missing'}
              </p>
            </div>
          </div>

          {/* Ollama Local AI */}
          <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5 md:col-span-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-amber-400" />
                Local AI Provider (Ollama Inventory)
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                  health.ollama.reachable
                    ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50'
                    : 'bg-slate-800 text-slate-300 border border-slate-700'
                }`}
              >
                {health.ollama.reachable ? 'Reachable' : 'Offline (Optional)'}
              </span>
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <p>Endpoint: {health.ollama.base_url}</p>
              <p>
                Installed Models:{' '}
                {health.ollama.installed_models.length > 0
                  ? health.ollama.installed_models.join(', ')
                  : 'None detected'}
              </p>
              {health.ollama.details && <p className="text-slate-500">{health.ollama.details}</p>}
            </div>
          </div>
        </div>
      )}

      {/* Module Implementation Roadmap Table */}
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Architecture Module Roadmap</h2>
          <span className="text-[11px] text-slate-400">
            Strict scope honesty: no placeholder sample data
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 text-slate-400 border-b border-border">
              <tr>
                <th className="px-4 py-2.5 font-medium">Milestone</th>
                <th className="px-4 py-2.5 font-medium">Module / Capability</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-slate-300">
              {MODULE_ROADMAP.map((row) => (
                <tr key={row.milestone} className="hover:bg-slate-900/40">
                  <td className="px-4 py-2 font-mono text-slate-400">{row.milestone}</td>
                  <td className="px-4 py-2">{row.name}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        row.status === 'Implemented'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
