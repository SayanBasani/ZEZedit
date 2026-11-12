import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Archive,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  Download,
  FolderLock,
  HardDrive,
  Layers,
  Moon,
  RefreshCw,
  RotateCcw,
  Save,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sun,
  Trash2,
  Wrench,
  Zap,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import { useTheme } from '../../context/ThemeContext';
import {
  clearAllData,
  createBackup,
  executeCacheCleanup,
  fetchAppSettings,
  fetchBackups,
  fetchDbIntegrity,
  fetchHealth,
  fetchRecoveryStatus,
  fetchStorageBreakdown,
  previewCacheCleanup,
  restoreBackup,
  updateAppSettings,
} from '../../services/apiClient';
import { HealthResponse } from '../../types/health';
import { AppSettingsData } from '../../types/projects';
import {
  BackupItem,
  CleanupPreview,
  DbIntegrityReport,
  RecoveryStatus,
  StorageBreakdown,
} from '../../types/system';

type SettingsTab = 'general' | 'performance' | 'storage' | 'backups' | 'providers' | 'diagnostics';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

export const SettingsManager: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [settings, setSettings] = useState<AppSettingsData | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [storageData, setStorageData] = useState<StorageBreakdown | null>(null);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [recoveryStatus, setRecoveryStatus] = useState<RecoveryStatus | null>(null);
  const [dbIntegrity, setDbIntegrity] = useState<DbIntegrityReport | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // Form states
  const [proxyRes, setProxyRes] = useState('480p');
  const [maxThreads, setMaxThreads] = useState(4);
  const [maxJobs, setMaxJobs] = useState(1);
  const [memoryLimitMb, setMemoryLimitMb] = useState(8192);
  const [defaultExportRes, setDefaultExportRes] = useState('1080x1920');

  // Storage Cleanup states
  const [cleanupPreview, setCleanupPreview] = useState<CleanupPreview | null>(null);
  const [tokenInput, setTokenInput] = useState('');
  const [cleaning, setCleaning] = useState(false);

  // Clear All Data states
  const [clearAllModalOpen, setClearAllModalOpen] = useState(false);
  const [clearAllInput, setClearAllInput] = useState('');
  const [clearingAll, setClearingAll] = useState(false);

  // Backup states
  const [backupLabel, setBackupLabel] = useState('manual');
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [restoringFilename, setRestoringFilename] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setErrorToast(null);
    try {
      const [s, h, st, bk, rec, dbi] = await Promise.all([
        fetchAppSettings(),
        fetchHealth().catch(() => null),
        fetchStorageBreakdown().catch(() => null),
        fetchBackups().catch(() => []),
        fetchRecoveryStatus().catch(() => null),
        fetchDbIntegrity().catch(() => null),
      ]);
      setSettings(s);
      setHealth(h);
      setStorageData(st);
      setBackups(bk);
      setRecoveryStatus(rec);
      setDbIntegrity(dbi);

      setProxyRes(s.proxy_resolution || '480p');
      setMaxThreads(s.cpu_processing_limits?.max_threads || 4);
      setMaxJobs(s.cpu_processing_limits?.max_concurrent_jobs || 1);
      setMemoryLimitMb(s.memory_limits_mb || 8192);
      setDefaultExportRes(s.default_export_preferences?.resolution || '1080x1920');
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorToast(null);
    setSuccessToast(null);
    try {
      const updated = await updateAppSettings({
        proxy_resolution: proxyRes,
        memory_limits_mb: Number(memoryLimitMb),
        cpu_processing_limits: {
          max_threads: Number(maxThreads),
          max_concurrent_jobs: Number(maxJobs),
        },
        default_export_preferences: {
          resolution: defaultExportRes,
          codec: 'libx264',
        },
      });
      setSettings(updated);
      setSuccessToast('Settings saved successfully.');
      setTimeout(() => setSuccessToast(null), 3000);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handlePreviewCleanup = async () => {
    setErrorToast(null);
    try {
      const prev = await previewCacheCleanup();
      setCleanupPreview(prev);
      setTokenInput('');
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to preview cache cleanup');
    }
  };

  const handleExecuteCleanup = async () => {
    if (!cleanupPreview) return;
    if (tokenInput.trim() !== cleanupPreview.confirmation_token) {
      setErrorToast('Confirmation token does not match preview.');
      return;
    }
    setCleaning(true);
    setErrorToast(null);
    try {
      const res = await executeCacheCleanup(cleanupPreview.confirmation_token);
      setSuccessToast(`Cache cleaned: ${res.deleted_files_count} files removed, freed ${formatBytes(res.freed_bytes)}.`);
      setCleanupPreview(null);
      void loadData();
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to execute cache cleanup');
    } finally {
      setCleaning(false);
    }
  };

  const handleExecuteClearAll = async () => {
    if (clearAllInput.trim().toUpperCase() !== 'DELETE') {
      setErrorToast("Please type 'DELETE' in all caps to confirm total wipeout.");
      return;
    }
    setClearingAll(true);
    setErrorToast(null);
    try {
      const res = await clearAllData('DELETE');
      setClearAllModalOpen(false);
      setClearAllInput('');
      setSuccessToast(`Total Data Wipe Successful: ${res.deleted_files_count} files deleted (${formatBytes(res.freed_bytes)} freed).`);
      void loadData();
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to clear all data');
    } finally {
      setClearingAll(false);
    }
  };

  const handleCreateBackup = async () => {
    setCreatingBackup(true);
    setErrorToast(null);
    try {
      const res = await createBackup(backupLabel || 'manual');
      setSuccessToast(`Backup snapshot '${res.backup_filename}' created and verified.`);
      setBackupLabel('manual');
      void loadData();
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to create backup');
    } finally {
      setCreatingBackup(false);
    }
  };

  const handleRestoreBackup = async (filename: string) => {
    if (!window.confirm(`Are you sure you want to restore '${filename}'? An automatic safety snapshot will be created before restoring.`)) {
      return;
    }
    setRestoringFilename(filename);
    setErrorToast(null);
    try {
      const res = await restoreBackup(filename);
      setSuccessToast(`Restored successfully from '${res.restored_from}'. Pre-restore safety copy saved to '${res.safety_snapshot}'.`);
      void loadData();
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to restore backup');
    } finally {
      setRestoringFilename(null);
    }
  };

  const handleRefreshIntegrity = async () => {
    try {
      const dbi = await fetchDbIntegrity();
      setDbIntegrity(dbi);
      setSuccessToast('Database diagnostics refreshed.');
      setTimeout(() => setSuccessToast(null), 2500);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to check database integrity');
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Studio Settings &amp; Operations</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Configure local hardware limits, theme, storage paths, backups, and recovery operations.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void loadData()}
          disabled={loading}
          leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
        >
          Refresh
        </Button>
      </div>

      {/* Notifications */}
      {successToast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successToast}</span>
        </div>
      )}
      {errorToast && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorToast}</span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex items-center gap-1.5 border-b border-border pb-2 overflow-x-auto">
        {[
          { id: 'general', label: 'General', icon: Sun },
          { id: 'performance', label: 'Processing & Performance', icon: Cpu },
          { id: 'storage', label: 'Storage Management', icon: HardDrive },
          { id: 'backups', label: 'Backups & Recovery', icon: Archive },
          { id: 'providers', label: 'AI Providers', icon: Server },
          { id: 'diagnostics', label: 'Diagnostics', icon: Wrench },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition whitespace-nowrap ${
                isActive
                  ? 'border border-brand bg-brand-subtle text-text-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-canvas-subtle'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT 1: GENERAL */}
      {activeTab === 'general' && (
        <form onSubmit={handleSaveSettings} className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Sun className="w-4 h-4 text-brand" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Appearance &amp; Theme
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {(['dark', 'light', 'system'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t)}
                  className={`p-3.5 rounded-xl border text-left transition flex items-center justify-between ${
                    theme === t
                      ? 'border-brand bg-brand-subtle text-text-primary'
                      : 'border-border bg-canvas-subtle hover:border-border-focus text-text-secondary'
                  }`}
                >
                  <div>
                    <span className="text-xs font-semibold block capitalize">{t} Theme</span>
                    <span className="text-[10px] text-text-muted">
                      {t === 'system' ? 'Follows OS preference' : `${t} interface mode`}
                    </span>
                  </div>
                  {t === 'dark' ? (
                    <Moon className="w-4 h-4 text-indigo-400" />
                  ) : t === 'light' ? (
                    <Sun className="w-4 h-4 text-amber-400" />
                  ) : (
                    <Layers className="w-4 h-4 text-sky-400" />
                  )}
                </button>
              ))}
            </div>
          </Card>

          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Zap className="w-4 h-4 text-brand" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Video Workspace Defaults
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-medium text-text-secondary">
                  Proxy Scrub Resolution
                </label>
                <select
                  value={proxyRes}
                  onChange={(e) => setProxyRes(e.target.value)}
                  className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                >
                  <option value="360p">360p (Fastest, lowest memory)</option>
                  <option value="480p">480p (Standard balanced)</option>
                  <option value="720p">720p (High clarity preview)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-text-secondary">
                  Default Export Preset
                </label>
                <select
                  value={defaultExportRes}
                  onChange={(e) => setDefaultExportRes(e.target.value)}
                  className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                >
                  <option value="1080x1920">1080x1920 (9:16 Vertical Short)</option>
                  <option value="1920x1080">1920x1080 (16:9 Landscape Video)</option>
                  <option value="1080x1080">1080x1080 (1:1 Square)</option>
                </select>
              </div>
            </div>
          </Card>

          <Card className="space-y-3">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <FolderLock className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Protected Storage Boundary
              </h2>
            </div>
            <div className="text-xs space-y-1.5 font-mono text-text-muted">
              <p className="truncate">Storage Root: {settings?.storage_root || 'Loading...'}</p>
              <p className="truncate">Temp Path: {settings?.temporary_storage_location || 'Loading...'}</p>
              <p className="text-text-secondary text-[11px] pt-1">
                ℹ Storage root is restricted to prevent directory traversal and accidental drive root writes.
              </p>
            </div>
          </Card>

          <div className="flex justify-end">
            <Button type="submit" isLoading={saving} leftIcon={<Save className="w-4 h-4" />}>
              Save General Settings
            </Button>
          </div>
        </form>
      )}

      {/* TAB CONTENT 2: PROCESSING & PERFORMANCE */}
      {activeTab === 'performance' && (
        <form onSubmit={handleSaveSettings} className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Cpu className="w-4 h-4 text-brand" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                CPU-First Hardware Limits
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-medium text-text-secondary">
                  Max FFmpeg Threads
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={maxThreads}
                  onChange={(e) => setMaxThreads(Number(e.target.value))}
                  className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                />
                <span className="text-[10px] text-text-muted">
                  Default: 4 threads for Intel Core i3-1220P to prevent UI freeze.
                </span>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-text-secondary">
                  Max Concurrent Jobs
                </label>
                <input
                  type="number"
                  min="1"
                  max="4"
                  value={maxJobs}
                  onChange={(e) => setMaxJobs(Number(e.target.value))}
                  className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                />
                <span className="text-[10px] text-text-muted">
                  Default: 1 (single-job queue prevents CPU thermal throttling).
                </span>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-text-secondary">
                  RAM Budget (MB)
                </label>
                <input
                  type="number"
                  min="2048"
                  max="32768"
                  step="1024"
                  value={memoryLimitMb}
                  onChange={(e) => setMemoryLimitMb(Number(e.target.value))}
                  className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                />
                <span className="text-[10px] text-text-muted">
                  Default: 8192 MB bounded buffer budget.
                </span>
              </div>
            </div>
          </Card>

          <Card className="space-y-3">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Zap className="w-4 h-4 text-indigo-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Priority Dispatch Rules &amp; Resource Guard
              </h2>
            </div>
            <div className="text-xs text-text-secondary space-y-2">
              <p>The persistent job orchestrator executes tasks according to strict CPU-first priorities:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="p-2.5 bg-canvas-subtle rounded-lg border border-border">
                  <span className="text-brand font-semibold block">1. Timeline &amp; Preview (Priority 200)</span>
                  <span className="text-text-muted">Interactive scrub, proxy streaming, waveform generation.</span>
                </div>
                <div className="p-2.5 bg-canvas-subtle rounded-lg border border-border">
                  <span className="text-indigo-400 font-semibold block">2. Shorts Export &amp; Render (Priority 150)</span>
                  <span className="text-text-muted">High-priority batch video transcoding and burn-in.</span>
                </div>
                <div className="p-2.5 bg-canvas-subtle rounded-lg border border-border">
                  <span className="text-amber-400 font-semibold block">3. Video Analysis &amp; AI (Priority 100)</span>
                  <span className="text-text-muted">Scene detection, Whisper speech-to-text, frame sampling.</span>
                </div>
                <div className="p-2.5 bg-canvas-subtle rounded-lg border border-border">
                  <span className="text-emerald-400 font-semibold block">4. Background &amp; Relink (Priority 50)</span>
                  <span className="text-text-muted">Integrity checks, metadata sync, pre-cache generation.</span>
                </div>
              </div>
              <p className="text-[11px] text-text-muted pt-1">
                Resource Pressure Guard: Automatically halts dispatch of new heavy tasks if CPU usage exceeds 95% or RAM usage exceeds 92%.
              </p>
            </div>
          </Card>

          <div className="flex justify-end">
            <Button type="submit" isLoading={saving} leftIcon={<Save className="w-4 h-4" />}>
              Save Performance Settings
            </Button>
          </div>
        </form>
      )}

      {/* TAB CONTENT 3: STORAGE MANAGEMENT */}
      {activeTab === 'storage' && (
        <div className="space-y-6">
          {storageData?.is_low_storage && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Low Storage Warning: Less than 5 GB Free</p>
                <p className="text-text-muted mt-0.5">
                  Your system has {formatBytes(storageData.free_disk_space_bytes)} available. Run safe cache cleanup below or move exports to free disk space.
                </p>
              </div>
            </div>
          )}

          {/* Disk Overview */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-brand" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Disk Space Overview
                </h2>
              </div>
              <Badge variant={storageData?.is_low_storage ? 'warning' : 'success'}>
                {storageData?.is_low_storage ? 'Storage Low' : 'Storage Healthy'}
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-3 bg-canvas-subtle rounded-xl border border-border">
                <span className="text-[10px] text-text-muted uppercase tracking-wider block">Total Disk Capacity</span>
                <span className="text-sm font-semibold font-mono text-text-primary">
                  {formatBytes(storageData?.total_disk_space_bytes || 0)}
                </span>
              </div>
              <div className="p-3 bg-canvas-subtle rounded-xl border border-border">
                <span className="text-[10px] text-text-muted uppercase tracking-wider block">Free Disk Space</span>
                <span className="text-sm font-semibold font-mono text-emerald-400">
                  {formatBytes(storageData?.free_disk_space_bytes || 0)}
                </span>
              </div>
              <div className="p-3 bg-canvas-subtle rounded-xl border border-border">
                <span className="text-[10px] text-text-muted uppercase tracking-wider block">Used Disk Space</span>
                <span className="text-sm font-semibold font-mono text-text-secondary">
                  {formatBytes(storageData?.used_disk_space_bytes || 0)}
                </span>
              </div>
            </div>
          </Card>

          {/* Categorized Breakdown */}
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Managed Storage Category Breakdown
              </h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { label: 'Source Media', bytes: storageData?.categories.source_media_bytes || 0, desc: 'Original imported videos' },
                { label: 'Proxies', bytes: storageData?.categories.proxies_bytes || 0, desc: 'Scrub preview transcodes' },
                { label: 'Thumbnails', bytes: storageData?.categories.thumbnails_bytes || 0, desc: 'Video & candidate images' },
                { label: 'Extracted Frames', bytes: storageData?.categories.extracted_frames_bytes || 0, desc: 'Sampled analysis frames' },
                { label: 'Temporary Cache', bytes: storageData?.categories.temp_cache_bytes || 0, desc: 'Disposable render & audio chunks' },
                { label: 'Rendered Exports', bytes: storageData?.categories.exports_bytes || 0, desc: 'Finished short videos' },
                { label: 'Database (WAL)', bytes: storageData?.categories.database_bytes || 0, desc: 'SQLite DB & WAL log' },
                { label: 'Backups', bytes: storageData?.categories.backups_bytes || 0, desc: 'Verified snapshots' },
                { label: 'System Logs', bytes: storageData?.categories.logs_bytes || 0, desc: 'Application event logs' },
              ].map((c) => (
                <div key={c.label} className="p-3 bg-canvas-subtle rounded-xl border border-border">
                  <span className="text-xs font-semibold text-text-primary block">{c.label}</span>
                  <span className="text-sm font-mono text-brand font-medium block mt-0.5">
                    {formatBytes(c.bytes)}
                  </span>
                  <span className="text-[10px] text-text-muted block mt-1">{c.desc}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Safe Disposable Cache Cleanup */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-amber-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Safe Disposable Cache Cleanup
                </h2>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handlePreviewCleanup}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Preview Cleanup
              </Button>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Safe cache cleanup strictly targets temporary files in the <span className="font-mono text-text-primary">temp/</span> folder.
              It <strong className="text-text-primary">never touches</strong> source videos, project timelines, rendered exports, or the database.
            </p>

            {cleanupPreview && (
              <div className="p-4 bg-canvas-subtle border border-amber-500/30 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-text-primary">Cleanup Preview Assessment</span>
                  <Badge variant="warning">
                    {cleanupPreview.eligible_files_count} files ({formatBytes(cleanupPreview.total_bytes_to_free)})
                  </Badge>
                </div>

                <div className="text-[11px] text-text-muted space-y-1">
                  <p>Eligible for removal: {cleanupPreview.eligible_files_count} transient files.</p>
                  <p className="text-emerald-400">
                    Protected rules: {cleanupPreview.protected_categories.join(', ')}.
                  </p>
                </div>

                {cleanupPreview.eligible_files_count > 0 ? (
                  <div className="space-y-3 pt-2 border-t border-border">
                    <p className="text-xs text-text-secondary">
                      To confirm deletion of {formatBytes(cleanupPreview.total_bytes_to_free)}, enter the confirmation token below:
                    </p>
                    <div className="flex items-center gap-3">
                      <div className="font-mono text-xs bg-canvas px-3 py-1.5 rounded-lg border border-border select-all text-text-primary">
                        {cleanupPreview.confirmation_token}
                      </div>
                      <input
                        type="text"
                        placeholder="Enter token to confirm"
                        value={tokenInput}
                        onChange={(e) => setTokenInput(e.target.value.toUpperCase())}
                        className="bg-canvas border border-border rounded-lg text-xs font-mono text-text-primary px-3 py-1.5 w-44"
                      />
                      <Button
                        variant="danger"
                        size="sm"
                        isLoading={cleaning}
                        onClick={handleExecuteCleanup}
                        disabled={tokenInput.trim() !== cleanupPreview.confirmation_token}
                        leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                      >
                        Execute Safe Cleanup
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-emerald-400">No disposable cache files found. Storage is clean.</p>
                )}
              </div>
            )}
          </Card>

          {/* CLEAR ALL DATA / FACTORY RESET */}
          <Card className="space-y-4 border-red-500/30 bg-red-500/5">
            <div className="flex items-center justify-between border-b border-red-500/20 pb-2.5">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-400" />
                <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider">
                  Clear All Application Data (Single Button Total Reset)
                </h2>
              </div>
              <Badge variant="danger">High Impact</Badge>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Permanently erase all stored videos, thumbnails, proxies, extracted audio, visual keyframes, cache, candidate clips, scripts, and database records. Restores ZezEdit to a clean, fresh initial state. Original files on your computer outside the managed storage folder are never touched.
            </p>

            <div className="pt-2 flex items-center justify-between">
              <div className="text-[11px] text-text-muted">
                Requires typing confirmation: <span className="font-mono text-red-400 font-semibold">DELETE</span>
              </div>
              <Button
                variant="danger"
                size="sm"
                onClick={() => {
                  setClearAllInput('');
                  setClearAllModalOpen(true);
                }}
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Clear All Data...
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* CLEAR ALL DATA CONFIRMATION MODAL */}
      <Dialog
        isOpen={clearAllModalOpen}
        onClose={() => !clearingAll && setClearAllModalOpen(false)}
        title="Confirm Total Data Deletion"
      >
        <div className="space-y-4 p-4 text-text-primary">
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
            <AlertOctagon className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-red-400">Warning: This action cannot be undone.</p>
              <p className="text-text-secondary">
                This will permanently delete all managed videos, audio, keyframes, candidate clips, scripts, and project database tables.
              </p>
            </div>
          </div>

          <div className="text-xs space-y-2">
            <label className="block text-text-secondary">
              To proceed, please type <span className="font-mono text-red-400 font-bold">DELETE</span> in capital letters:
            </label>
            <input
              type="text"
              value={clearAllInput}
              onChange={(e) => setClearAllInput(e.target.value)}
              placeholder="Type DELETE to confirm"
              className="w-full bg-canvas border border-border focus:border-red-500 rounded-lg text-sm font-mono text-text-primary px-3 py-2 outline-none"
              autoFocus
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-border">
            <Button
              variant="ghost"
              size="sm"
              disabled={clearingAll}
              onClick={() => setClearAllModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={clearingAll}
              disabled={clearAllInput.trim().toUpperCase() !== 'DELETE'}
              onClick={handleExecuteClearAll}
              leftIcon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Permanently Clear All Data
            </Button>
          </div>
        </div>
      </Dialog>

      {/* TAB CONTENT 4: BACKUPS & RECOVERY */}
      {activeTab === 'backups' && (
        <div className="space-y-6">
          {/* Create Backup */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Archive className="w-4 h-4 text-brand" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Create Database Backup Snapshot
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Backup label (e.g. milestone_edit, pre_render)"
                value={backupLabel}
                onChange={(e) => setBackupLabel(e.target.value)}
                className="bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2 flex-1"
              />
              <Button
                variant="primary"
                size="sm"
                isLoading={creatingBackup}
                onClick={handleCreateBackup}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Create Backup
              </Button>
            </div>
            <p className="text-[11px] text-text-muted">
              Creates a consistent, hot SQLite WAL backup verified with <span className="font-mono">PRAGMA integrity_check</span>.
            </p>
          </Card>

          {/* Recovery Overview */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-indigo-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Crash Recovery &amp; Project Health
                </h2>
              </div>
              <Badge variant={recoveryStatus?.recovery_ready ? 'success' : 'default'}>
                {recoveryStatus?.recovery_ready ? 'Recovery Ready' : 'Inspecting'}
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Last Verified Backup</span>
                <span className="font-medium text-text-primary block truncate">
                  {recoveryStatus?.last_backup?.backup_filename || 'No backups yet'}
                </span>
                <span className="text-[10px] text-text-muted">
                  {recoveryStatus?.last_backup ? formatBytes(recoveryStatus.last_backup.file_size_bytes) : ''}
                </span>
              </div>

              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Interrupted In-Flight Jobs</span>
                <span className="font-medium font-mono text-text-primary block">
                  {recoveryStatus?.interrupted_jobs_count || 0}
                </span>
                <span className="text-[10px] text-text-muted">
                  Checkpoints preserved for resume.
                </span>
              </div>

              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Missing Media Assets</span>
                <span className="font-medium font-mono text-text-primary block">
                  {recoveryStatus?.missing_media_count || 0}
                </span>
                <span className="text-[10px] text-text-muted">
                  Use Relink Media in Media Library.
                </span>
              </div>
            </div>
          </Card>

          {/* Existing Backups Table */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Existing Backups ({backups.length})
                </h2>
              </div>
            </div>

            {backups.length === 0 ? (
              <p className="text-xs text-text-muted py-4 text-center">No backups recorded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border text-text-muted text-[10px] uppercase">
                      <th className="py-2 px-3">Filename</th>
                      <th className="py-2 px-3">Size</th>
                      <th className="py-2 px-3">Created</th>
                      <th className="py-2 px-3">Integrity</th>
                      <th className="py-2 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {backups.map((b) => (
                      <tr key={b.backup_filename} className="hover:bg-canvas-subtle/50 transition">
                        <td className="py-2 px-3 font-mono text-text-primary text-[11px] truncate max-w-xs">
                          {b.backup_filename}
                          {b.is_safety_snapshot && (
                            <span className="ml-2 text-[10px] text-amber-400 font-sans font-normal">(Safety)</span>
                          )}
                        </td>
                        <td className="py-2 px-3 font-mono text-text-muted">{formatBytes(b.file_size_bytes)}</td>
                        <td className="py-2 px-3 text-text-muted">{new Date(b.created_at).toLocaleString()}</td>
                        <td className="py-2 px-3">
                          <Badge variant={b.integrity_verified ? 'success' : 'danger'}>
                            {b.integrity_verified ? 'Verified OK' : 'Check Failed'}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            isLoading={restoringFilename === b.backup_filename}
                            onClick={() => handleRestoreBackup(b.backup_filename)}
                            leftIcon={<RotateCcw className="w-3 h-3" />}
                          >
                            Restore
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TAB CONTENT 5: AI PROVIDERS */}
      {activeTab === 'providers' && (
        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Local AI Provider Status
                </h2>
              </div>
              {health && (
                <Badge variant={health.ollama.reachable ? 'success' : 'default'}>
                  {health.ollama.reachable ? 'Ollama Reachable' : 'Offline'}
                </Badge>
              )}
            </div>

            <div className="text-xs text-text-secondary space-y-3">
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Ollama Endpoint</span>
                <span className="font-mono text-text-primary">
                  {settings?.ai_provider_config?.ollama_base_url || 'http://127.0.0.1:11434'}
                </span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Installed Ollama Models</span>
                <span className="font-mono text-text-primary">
                  {health?.ollama?.installed_models?.join(', ') || 'None detected'}
                </span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Active Vision Model</span>
                <span className="font-mono text-brand">
                  {settings?.model_preferences?.default_vision_model || 'qwen3-vl:4b-instruct'}
                </span>
              </div>

              <div className="p-3 bg-canvas-subtle rounded-xl border border-border text-[11px] text-text-muted space-y-1">
                <p>Speech Recognition Engine: Faster-Whisper CPU (16kHz mono PCM).</p>
                <p>Multimodal Vision: Bounded frames via FFmpeg seeking to protect RAM.</p>
                <p>Secrets Protection: All API keys and environment variables are strictly masked in logs and client DTOs.</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB CONTENT 6: DIAGNOSTICS */}
      {activeTab === 'diagnostics' && (
        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Database Diagnostics &amp; PRAGMA Verification
                </h2>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshIntegrity}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Re-check
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Integrity Check</span>
                <Badge variant={dbIntegrity?.integrity_check === 'ok' ? 'success' : 'danger'}>
                  PRAGMA: {dbIntegrity?.integrity_check || 'checking...'}
                </Badge>
              </div>

              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Foreign Key Integrity</span>
                <Badge variant={dbIntegrity?.foreign_key_check === 'ok' ? 'success' : 'danger'}>
                  {dbIntegrity?.foreign_key_check === 'ok' ? 'FK Valid (0 violations)' : 'FK Violations'}
                </Badge>
              </div>

              <div className="p-3 bg-canvas-subtle rounded-xl border border-border space-y-1">
                <span className="text-[10px] text-text-muted uppercase block">Journal Mode</span>
                <Badge variant="default">
                  {dbIntegrity?.journal_mode || 'WAL'}
                </Badge>
              </div>
            </div>

            {dbIntegrity?.issues && dbIntegrity.issues.length > 0 && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl space-y-1">
                <span className="text-xs font-semibold text-red-400 block">Issues Detected:</span>
                {dbIntegrity.issues.map((iss, idx) => (
                  <p key={idx} className="text-xs text-red-300 font-mono">• {iss}</p>
                ))}
              </div>
            )}
          </Card>

          {/* Database Table Row Counts */}
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Database className="w-4 h-4 text-indigo-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Database Table Row Counts
              </h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {dbIntegrity?.table_counts &&
                Object.entries(dbIntegrity.table_counts).map(([tbl, cnt]) => (
                  <div key={tbl} className="p-2.5 bg-canvas-subtle rounded-lg border border-border">
                    <span className="text-[10px] text-text-muted block truncate font-mono">{tbl}</span>
                    <span className="text-sm font-semibold font-mono text-text-primary">{cnt}</span>
                  </div>
                ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
