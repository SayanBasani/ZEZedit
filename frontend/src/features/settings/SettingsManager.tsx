import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Archive,
  CheckCircle2,
  CheckSquare,
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
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Square,
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
  clearAllUserData,
  createBackup,
  executeCacheCleanup,
  executeMaintenanceCleanup,
  fetchAppSettings,
  fetchBackups,
  fetchCleanupHistory,
  fetchDbIntegrity,
  fetchHealth,
  fetchRecoveryStatus,
  fetchStorageBreakdown,
  fetchStorageQuotas,
  fetchUserDataCleanupPreview,
  previewCacheCleanup,
  previewMaintenanceCleanup,
  recoverStaleArtifacts,
  restoreBackup,
  updateAppSettings,
  updateStorageQuotas,
} from '../../services/apiClient';
import { HealthResponse } from '../../types/health';
import { AppSettingsData } from '../../types/projects';
import {
  BackupItem,
  CleanupAuditItem,
  CleanupPreview,
  DbIntegrityReport,
  MaintenanceCleanupExecution,
  MaintenanceCleanupPreview,
  RecoveryStatus,
  StorageBreakdown,
  StorageQuotaStatus,
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

  // P1.9 Storage Quota states
  const [quotaStatus, setQuotaStatus] = useState<StorageQuotaStatus | null>(null);
  const [storageLimitGb, setStorageLimitGb] = useState<string>('');
  const [genVideoLimitGb, setGenVideoLimitGb] = useState<string>('');
  const [tempStorageLimitGb, setTempStorageLimitGb] = useState<string>('');
  const [warningThresholdPct, setWarningThresholdPct] = useState<number>(85);
  const [autoPruneEnabled, setAutoPruneEnabled] = useState<boolean>(false);
  const [autoPruneRetentionHours, setAutoPruneRetentionHours] = useState<number>(24);
  const [savingQuotas, setSavingQuotas] = useState<boolean>(false);

  // P1.9 Maintenance Cleanup & Candidate states
  const [maintPreview, setMaintPreview] = useState<MaintenanceCleanupPreview | null>(null);
  const [selectedCleanupCategories, setSelectedCleanupCategories] = useState<string[]>([
    'orphaned_uploads',
    'abandoned_ffmpeg',
    'failed_renders',
    'expired_temp_files',
  ]);
  const [maintCleaning, setMaintCleaning] = useState<boolean>(false);
  const [maintResult, setMaintResult] = useState<MaintenanceCleanupExecution | null>(null);
  const [cleanupHistory, setCleanupHistory] = useState<CleanupAuditItem[]>([]);
  const [recoveringStale, setRecoveringStale] = useState<boolean>(false);

  // Clear All Data states
  const [clearAllModalOpen, setClearAllModalOpen] = useState(false);
  const [clearAllInput, setClearAllInput] = useState('');
  const [clearingAll, setClearingAll] = useState(false);
  const [userDataPreview, setUserDataPreview] = useState<any>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Backup states
  const [backupLabel, setBackupLabel] = useState('manual');
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [restoringFilename, setRestoringFilename] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setErrorToast(null);
    try {
      const [s, h, st, bk, rec, dbi, q, hist] = await Promise.all([
        fetchAppSettings(),
        fetchHealth().catch(() => null),
        fetchStorageBreakdown().catch(() => null),
        fetchBackups().catch(() => []),
        fetchRecoveryStatus().catch(() => null),
        fetchDbIntegrity().catch(() => null),
        fetchStorageQuotas().catch(() => null),
        fetchCleanupHistory(20).catch(() => []),
      ]);
      setSettings(s);
      setHealth(h);
      setStorageData(st);
      setBackups(bk);
      setRecoveryStatus(rec);
      setDbIntegrity(dbi);
      if (q && q.quota_settings) {
        setQuotaStatus(q);
        const qs = q.quota_settings;
        setStorageLimitGb(qs.storage_limit_bytes ? (qs.storage_limit_bytes / (1024 * 1024 * 1024)).toString() : '');
        setGenVideoLimitGb(qs.generated_video_limit_bytes ? (qs.generated_video_limit_bytes / (1024 * 1024 * 1024)).toString() : '');
        setTempStorageLimitGb(qs.temp_storage_limit_bytes ? (qs.temp_storage_limit_bytes / (1024 * 1024 * 1024)).toString() : '');
        setWarningThresholdPct(qs.warning_threshold_percent || 85);
        setAutoPruneEnabled(qs.auto_prune_enabled || false);
        setAutoPruneRetentionHours(qs.auto_prune_retention_hours || 24);
      }
      setCleanupHistory(hist);
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

  const handleSaveQuotas = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSavingQuotas(true);
    setErrorToast(null);
    try {
      const storageBytes = storageLimitGb.trim() ? Math.round(parseFloat(storageLimitGb) * 1024 * 1024 * 1024) : null;
      const genBytes = genVideoLimitGb.trim() ? Math.round(parseFloat(genVideoLimitGb) * 1024 * 1024 * 1024) : null;
      const tempBytes = tempStorageLimitGb.trim() ? Math.round(parseFloat(tempStorageLimitGb) * 1024 * 1024 * 1024) : null;

      await updateStorageQuotas({
        storage_limit_bytes: storageBytes,
        generated_video_limit_bytes: genBytes,
        temp_storage_limit_bytes: tempBytes,
        warning_threshold_percent: warningThresholdPct,
        auto_prune_enabled: autoPruneEnabled,
        auto_prune_retention_hours: autoPruneRetentionHours,
        auto_prune_categories: selectedCleanupCategories,
      });

      const [updatedStatus, updatedBreakdown] = await Promise.all([
        fetchStorageQuotas().catch(() => null),
        fetchStorageBreakdown().catch(() => null),
      ]);
      if (updatedStatus) setQuotaStatus(updatedStatus);
      if (updatedBreakdown) setStorageData(updatedBreakdown);
      setSuccessToast('Storage quotas and pruning policies saved successfully');
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to save storage quotas');
    } finally {
      setSavingQuotas(false);
    }
  };

  const handlePreviewMaintenanceCleanup = async () => {
    setMaintCleaning(true);
    setErrorToast(null);
    try {
      const prev = await previewMaintenanceCleanup(selectedCleanupCategories);
      setMaintPreview(prev);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to preview maintenance cleanup');
    } finally {
      setMaintCleaning(false);
    }
  };

  const handleExecuteMaintenanceCleanup = async () => {
    if (!maintPreview) return;
    setMaintCleaning(true);
    setErrorToast(null);
    try {
      const eligibleCandidateIds = maintPreview.candidates
        .filter((c) => !c.is_blocked && selectedCleanupCategories.includes(c.category))
        .map((c) => c.candidate_id);

      const res = await executeMaintenanceCleanup(
        eligibleCandidateIds,
        selectedCleanupCategories
      );

      setMaintResult(res);
      setMaintPreview(null);
      const [updatedSt, updatedHist] = await Promise.all([
        fetchStorageBreakdown().catch(() => null),
        fetchCleanupHistory(20).catch(() => []),
      ]);
      if (updatedSt) setStorageData(updatedSt);
      setCleanupHistory(updatedHist);
      setSuccessToast(`Safely deleted ${res.deleted_count} files, reclaiming ${formatBytes(res.bytes_reclaimed)}.`);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to execute maintenance cleanup');
    } finally {
      setMaintCleaning(false);
    }
  };

  const handleRecoverStale = async () => {
    setRecoveringStale(true);
    setErrorToast(null);
    try {
      const res = await recoverStaleArtifacts();
      const [updatedSt, updatedHist] = await Promise.all([
        fetchStorageBreakdown().catch(() => null),
        fetchCleanupHistory(20).catch(() => []),
      ]);
      if (updatedSt) setStorageData(updatedSt);
      setCleanupHistory(updatedHist);
      setSuccessToast(`Recovered ${res.recovered_files_count} stale artifacts (${res.formatted_bytes_reclaimed} reclaimed).`);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to recover stale artifacts');
    } finally {
      setRecoveringStale(false);
    }
  };

  const handleOpenClearAllModal = async () => {
    setClearAllInput('');
    setClearAllModalOpen(true);
    setLoadingPreview(true);
    try {
      const prev = await fetchUserDataCleanupPreview();
      setUserDataPreview(prev);
    } catch {
      setUserDataPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleExecuteClearAll = async () => {
    const trimmed = clearAllInput.trim().toUpperCase();
    if (trimmed !== 'DELETE ALL USER DATA' && trimmed !== 'DELETE') {
      setErrorToast("Please type 'DELETE ALL USER DATA' or 'DELETE' to confirm total reset.");
      return;
    }
    setClearingAll(true);
    setErrorToast(null);
    try {
      const res = await clearAllUserData(clearAllInput.trim());
      setClearAllModalOpen(false);
      setClearAllInput('');
      setUserDataPreview(null);
      const freedText = res.formatted_reclaimed_space || `${res.actual_reclaimed_bytes ?? 0} B`;
      const tablesText = res.purged_tables_count !== undefined ? `${res.purged_tables_count} database tables purged` : 'tables cleared';
      setSuccessToast(
        `Total Storage Reclamation Complete: Reclaimed ${freedText} (${res.deleted_files_count} files removed, ${tablesText}).`
      );
      void loadData();
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : 'Failed to clear user data');
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

          {/* Low Storage or Quota Warning Banners */}
          {storageData?.is_low_storage && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Low Physical Disk Storage Warning: Less than 5 GB Free</p>
                <p className="text-text-muted mt-0.5">
                  Your system has {formatBytes(storageData.free_disk_space_bytes)} available. Run safe maintenance cleanup below to free disk space.
                </p>
              </div>
            </div>
          )}

          {quotaStatus?.is_exceeded && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Storage Quota Exceeded</p>
                <ul className="list-disc pl-4 mt-0.5 space-y-0.5 text-text-secondary">
                  {quotaStatus.warning_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {quotaStatus?.is_warning && !quotaStatus?.is_exceeded && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Storage Quota Warning Threshold Reached</p>
                <ul className="list-disc pl-4 mt-0.5 space-y-0.5 text-text-secondary">
                  {quotaStatus.warning_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
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
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    const [st, q] = await Promise.all([
                      fetchStorageBreakdown().catch(() => null),
                      fetchStorageQuotas().catch(() => null),
                    ]);
                    if (st) setStorageData(st);
                    if (q) setQuotaStatus(q);
                  }}
                  className="text-xs h-7 px-2"
                  leftIcon={<RefreshCw className="w-3 h-3" />}
                >
                  Refresh Storage Usage
                </Button>
                <Badge variant={storageData?.is_low_storage ? 'warning' : 'success'}>
                  {storageData?.is_low_storage ? 'Storage Low' : 'Storage Healthy'}
                </Badge>
              </div>
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

            {/* Quota Progress Bars */}
            {quotaStatus && quotaStatus.quota_settings && (
              <div className="pt-2 border-t border-border space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-text-secondary">Storage Quota Tracking &amp; Utilization</span>
                  {quotaStatus.quota_settings.storage_limit_bytes && (
                    <span className="font-mono text-text-muted">
                      {formatBytes(quotaStatus.total_usage_bytes)} / {formatBytes(quotaStatus.quota_settings.storage_limit_bytes)} ({quotaStatus.total_utilization_pct || 0}%)
                    </span>
                  )}
                </div>

                {quotaStatus.quota_settings.storage_limit_bytes && (
                  <div className="space-y-1">
                    <div className="w-full bg-border/40 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          (quotaStatus.total_utilization_pct || 0) >= 100
                            ? 'bg-red-500'
                            : (quotaStatus.total_utilization_pct || 0) >= quotaStatus.quota_settings.warning_threshold_percent
                            ? 'bg-amber-500'
                            : 'bg-brand'
                        }`}
                        style={{ width: `${Math.min(quotaStatus.total_utilization_pct || 0, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* Categorized Breakdown */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Managed Storage Category Breakdown
                </h2>
              </div>
              {Boolean(storageData?.categories?.canonical_shared_media_bytes) && (
                <Badge variant="purple">
                  Deduplication Active
                </Badge>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Source Media', bytes: storageData?.categories.source_media_bytes || 0, desc: 'Original imported video assets' },
                { label: 'Canonical Shared Media', bytes: storageData?.categories.canonical_shared_media_bytes || 0, desc: 'Deduplicated physical assets' },
                { label: 'Logical Assets (Virtual)', bytes: storageData?.categories.logical_media_assets_bytes || 0, desc: 'Total references across projects' },
                { label: 'Generated Shorts', bytes: storageData?.categories.generated_video_bytes || 0, desc: 'AI-generated vertical clips' },
                { label: 'Rendered Exports', bytes: storageData?.categories.rendered_exports_bytes || storageData?.categories.exports_bytes || 0, desc: 'Completed burn-in exports' },
                { label: 'Extracted Audio', bytes: storageData?.categories.extracted_audio_bytes || 0, desc: '16kHz mono Whisper tracks' },
                { label: 'Keyframes & Thumbs', bytes: storageData?.categories.keyframes_and_thumbnails_bytes || storageData?.categories.thumbnails_bytes || 0, desc: 'Thumbnails & sampled frames' },
                { label: 'Analysis & Transcripts', bytes: storageData?.categories.transcripts_and_analysis_bytes || storageData?.categories.extracted_frames_bytes || 0, desc: 'AI scenes & dialogue data' },
                { label: 'Temporary Uploads', bytes: storageData?.categories.temporary_uploads_bytes || 0, desc: 'Staged chunk buffers' },
                { label: 'Temporary Renders', bytes: storageData?.categories.temporary_rendering_bytes || 0, desc: 'FFmpeg scratch & sub workspaces' },
                { label: 'Database & Backups', bytes: storageData?.categories.database_and_backups_bytes || storageData?.categories.database_bytes || 0, desc: 'SQLite DB & snapshots' },
                { label: 'Proxies & Cache', bytes: storageData?.categories.proxies_bytes || 0, desc: 'Fast scrub transcodes' },
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

          {/* Section: Storage Quotas & Automatic Pruning Configuration Form */}
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-2.5">
              <Sliders className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Storage Quotas &amp; Automatic Pruning Policies
              </h2>
            </div>

            <form onSubmit={handleSaveQuotas} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Overall Storage Limit (GB)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    placeholder="Unlimited"
                    value={storageLimitGb}
                    onChange={(e) => setStorageLimitGb(e.target.value)}
                    className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                  />
                  <span className="text-[10px] text-text-muted mt-0.5 block">Leave blank for unlimited.</span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Generated Video Limit (GB)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    placeholder="Unlimited"
                    value={genVideoLimitGb}
                    onChange={(e) => setGenVideoLimitGb(e.target.value)}
                    className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                  />
                  <span className="text-[10px] text-text-muted mt-0.5 block">AI shorts &amp; clips quota.</span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Temporary Storage Limit (GB)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    placeholder="Unlimited"
                    value={tempStorageLimitGb}
                    onChange={(e) => setTempStorageLimitGb(e.target.value)}
                    className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                  />
                  <span className="text-[10px] text-text-muted mt-0.5 block">Uploads &amp; render staging buffer.</span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-border">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Warning Threshold Percentage ({warningThresholdPct}%)
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    step="5"
                    value={warningThresholdPct}
                    onChange={(e) => setWarningThresholdPct(Number(e.target.value))}
                    className="w-full accent-brand cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-text-muted mt-1">
                    <span>50%</span>
                    <span>80%</span>
                    <span>85% (Default)</span>
                    <span>95%</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Automatic Pruning Retention (Hours)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="720"
                    value={autoPruneRetentionHours}
                    onChange={(e) => setAutoPruneRetentionHours(Number(e.target.value))}
                    className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
                  />
                  <span className="text-[10px] text-text-muted mt-0.5 block">
                    Stale temporary files older than this will be eligible for pruning.
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-border">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoPruneEnabled}
                    onChange={(e) => setAutoPruneEnabled(e.target.checked)}
                    className="rounded border-border text-brand focus:ring-brand"
                  />
                  <span className="text-xs font-medium text-text-primary">
                    Enable Automatic Pruning of Stale Temporary Files
                  </span>
                </label>
                <p className="text-[11px] text-text-muted mt-1 pl-6">
                  Disabled by default. When enabled, only transient files exceeding the retention window are safely removed. Original source media and active projects are strictly protected.
                </p>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  type="submit"
                  size="sm"
                  onClick={handleSaveQuotas}
                  isLoading={savingQuotas}
                  leftIcon={<Save className="w-3.5 h-3.5" />}
                >
                  Save Quotas &amp; Policies
                </Button>
              </div>
            </form>
          </Card>

          {/* Section: Granular Maintenance Cleanup & Stale Artifacts */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-amber-400" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Safe Maintenance Cleanup &amp; Crash Recovery
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  isLoading={recoveringStale}
                  onClick={handleRecoverStale}
                  leftIcon={<Shield className="w-3.5 h-3.5 text-brand" />}
                >
                  Recover Stale Artifacts
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePreviewMaintenanceCleanup}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Scan Cleanup Candidates
                </Button>
              </div>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Scan for orphaned upload chunks, abandoned FFmpeg temporary files, and failed renders.
              Original source media and canonical shared assets with active references are <strong className="text-text-primary">strictly protected</strong>.
            </p>

            {/* Category selection filters */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
              {[
                { id: 'orphaned_uploads', label: 'Orphaned Uploads (.part, .uploading)' },
                { id: 'abandoned_ffmpeg', label: 'Abandoned Render Workspaces' },
                { id: 'failed_renders', label: 'Failed Render Outputs' },
                { id: 'expired_temp_files', label: 'Expired Temp Files' },
              ].map((cat) => {
                const isSelected = selectedCleanupCategories.includes(cat.id);
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      setSelectedCleanupCategories((prev) =>
                        isSelected ? prev.filter((c) => c !== cat.id) : [...prev, cat.id]
                      );
                    }}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition ${
                      isSelected
                        ? 'border-brand bg-brand-subtle text-text-primary'
                        : 'border-border bg-canvas-subtle text-text-muted hover:border-border-focus'
                    }`}
                  >
                    {isSelected ? <CheckSquare className="w-3.5 h-3.5 text-brand" /> : <Square className="w-3.5 h-3.5" />}
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Candidates Preview Table */}
            {maintPreview && (
              <div className="p-4 bg-canvas-subtle border border-amber-500/30 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text-primary block">
                      Discovered Cleanup Candidates ({maintPreview.total_candidates} total)
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Eligible: {maintPreview.eligible_candidates_count} ({formatBytes(maintPreview.total_eligible_bytes)}) |
                      Protected/Blocked: {maintPreview.blocked_candidates_count} ({formatBytes(maintPreview.total_blocked_bytes)})
                    </span>
                  </div>
                  <Badge variant="warning">
                    {formatBytes(maintPreview.total_eligible_bytes)} Reclaimable
                  </Badge>
                </div>

                {maintPreview.candidates && maintPreview.candidates.length > 0 ? (
                  <div className="space-y-3 pt-2 border-t border-border">
                    <div className="overflow-x-auto max-h-60 overflow-y-auto">
                      <table className="w-full text-left text-xs font-mono">
                        <thead>
                          <tr className="border-b border-border text-text-muted text-[10px] uppercase">
                            <th className="py-2 px-2">Path</th>
                            <th className="py-2 px-2">Category</th>
                            <th className="py-2 px-2">Size</th>
                            <th className="py-2 px-2">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {maintPreview.candidates.map((c) => (
                            <tr key={c.candidate_id} className="hover:bg-surface/50">
                              <td className="py-1.5 px-2 text-text-primary truncate max-w-xs" title={c.relative_path}>
                                {c.relative_path}
                              </td>
                              <td className="py-1.5 px-2 text-text-secondary">{c.category}</td>
                              <td className="py-1.5 px-2 font-semibold text-text-primary">{formatBytes(c.size_bytes)}</td>
                              <td className="py-1.5 px-2">
                                {c.is_blocked ? (
                                  <Badge variant="danger" size="sm">
                                    Protected: {c.protection_reason || 'Active reference'}
                                  </Badge>
                                ) : (
                                  <Badge variant="success" size="sm">
                                    Eligible
                                  </Badge>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border">
                      <span className="text-[11px] text-text-muted">
                        Preview generated at {new Date(maintPreview.generated_at).toLocaleTimeString()}.
                      </span>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={handleExecuteMaintenanceCleanup}
                        isLoading={maintCleaning}
                        disabled={maintPreview.eligible_candidates_count === 0}
                        leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                      >
                        Execute Safe Cleanup ({formatBytes(maintPreview.total_eligible_bytes)})
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-emerald-400">No removable files found. Storage is clean.</p>
                )}
              </div>
            )}

            {/* Execution Result Banner */}
            {maintResult && (
              <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs space-y-1 text-emerald-400">
                <div className="flex items-center gap-2 font-semibold">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Cleanup Completed Successfully</span>
                </div>
                <p className="text-text-secondary">
                  Deleted {maintResult.deleted_count} files, reclaiming {formatBytes(maintResult.bytes_reclaimed)}.
                  {maintResult.skipped_count > 0 && ` (${maintResult.skipped_count} items skipped/protected)`}
                </p>
              </div>
            )}
          </Card>

          {/* Section: Cleanup Audit History */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand" />
                <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Recent Storage Cleanup Audit History
                </h2>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  const hist = await fetchCleanupHistory(20).catch(() => []);
                  setCleanupHistory(hist);
                }}
                className="text-xs h-7 px-2"
                leftIcon={<RefreshCw className="w-3 h-3" />}
              >
                Refresh Log
              </Button>
            </div>

            {cleanupHistory && cleanupHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border text-text-muted text-[10px] uppercase">
                      <th className="py-2 px-2">Operation ID</th>
                      <th className="py-2 px-2">Timestamp</th>
                      <th className="py-2 px-2">Category</th>
                      <th className="py-2 px-2">Files Deleted</th>
                      <th className="py-2 px-2">Bytes Reclaimed</th>
                      <th className="py-2 px-2">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {cleanupHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-canvas-subtle/50">
                        <td className="py-2 px-2 text-text-primary font-medium">{item.operation_id}</td>
                        <td className="py-2 px-2 text-text-muted font-sans text-[11px]">
                          {new Date(item.timestamp).toLocaleString()}
                        </td>
                        <td className="py-2 px-2 text-text-secondary">{item.cleanup_category}</td>
                        <td className="py-2 px-2 text-text-primary">{item.files_deleted}</td>
                        <td className="py-2 px-2 text-emerald-400 font-semibold">{formatBytes(item.bytes_reclaimed)}</td>
                        <td className="py-2 px-2">
                          <Badge variant={item.is_automatic ? 'purple' : 'default'} size="sm">
                            {item.is_automatic ? 'Automatic' : 'Manual'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-text-muted italic py-2">No storage cleanup operations recorded yet.</p>
            )}
          </Card>

          {/* CLEAR ALL DATA / TOTAL STORAGE RECLAMATION */}
          <Card className="space-y-4 border-red-500/30 bg-red-500/5">
            <div className="flex items-center justify-between border-b border-red-500/20 pb-2.5">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-400" />
                <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider">
                  Complete User Data Deletion &amp; Storage Reclamation
                </h2>
              </div>
              <Badge variant="danger">High Impact</Badge>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Permanently stop all running background tasks, delete all managed videos, proxies, thumbnails, extracted frames, candidate clips, scripts, timelines, exports, and temporary files, purge user database tables, and compact the SQLite database file to reclaim physical disk space. External original videos on your drive outside the managed storage directory are safely preserved.
            </p>

            <div className="pt-2 flex items-center justify-between">
              <div className="text-[11px] text-text-muted">
                Requires typing confirmation: <span className="font-mono text-red-400 font-semibold">DELETE ALL USER DATA</span>
              </div>
              <Button
                variant="danger"
                size="sm"
                onClick={handleOpenClearAllModal}
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Clear All Data...
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* CLEAR ALL DATA CONFIRMATION MODAL WITH PREVIEW */}
      <Dialog
        isOpen={clearAllModalOpen}
        onClose={() => !clearingAll && setClearAllModalOpen(false)}
        title="Confirm Complete User Data Deletion & Storage Reclamation"
      >
        <div className="space-y-4 p-4 text-text-primary">
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
            <AlertOctagon className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-red-400">Warning: This action permanently wipes all user data.</p>
              <p className="text-text-secondary">
                All managed videos, proxies, thumbnails, frames, short clips, timelines, exports, and database records will be erased. The SQLite database will be truncated and compacted (VACUUM).
              </p>
            </div>
          </div>

          {/* Cleanup Assessment Preview */}
          {loadingPreview ? (
            <div className="p-4 bg-canvas-subtle rounded-xl border border-border text-center text-xs text-text-muted flex items-center justify-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand" />
              <span>Inspecting storage usage &amp; counting files...</span>
            </div>
          ) : userDataPreview ? (
            <div className="p-3.5 bg-canvas-subtle rounded-xl border border-border space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                <span>Storage Cleanup Assessment</span>
                <span className="text-emerald-400 font-mono">
                  ~{userDataPreview.formatted_reclaimable_space} reclaimable
                </span>
              </div>

              {userDataPreview.active_jobs_count > 0 && (
                <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>
                    Warning: {userDataPreview.active_jobs_count} running process(es) will be stopped and terminated immediately.
                  </span>
                </div>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 bg-surface rounded-lg border border-border">
                  <span className="text-text-muted text-[10px] uppercase block">Videos</span>
                  <span className="font-mono font-bold text-text-primary mt-0.5 block">
                    {userDataPreview.video_count}
                  </span>
                </div>
                <div className="p-2 bg-surface rounded-lg border border-border">
                  <span className="text-text-muted text-[10px] uppercase block">Short Clips</span>
                  <span className="font-mono font-bold text-text-primary mt-0.5 block">
                    {userDataPreview.clip_count}
                  </span>
                </div>
                <div className="p-2 bg-surface rounded-lg border border-border">
                  <span className="text-text-muted text-[10px] uppercase block">Frames</span>
                  <span className="font-mono font-bold text-text-primary mt-0.5 block">
                    {userDataPreview.frame_count}
                  </span>
                </div>
                <div className="p-2 bg-surface rounded-lg border border-border">
                  <span className="text-text-muted text-[10px] uppercase block">Temp Files</span>
                  <span className="font-mono font-bold text-text-primary mt-0.5 block">
                    {userDataPreview.temp_file_count}
                  </span>
                </div>
              </div>
            </div>
          ) : null}

          <div className="text-xs space-y-2">
            <label className="block text-text-secondary">
              To proceed, please type <span className="font-mono text-red-400 font-bold">DELETE ALL USER DATA</span> in capital letters:
            </label>
            <input
              type="text"
              value={clearAllInput}
              onChange={(e) => setClearAllInput(e.target.value)}
              placeholder="Type DELETE ALL USER DATA to confirm"
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
              disabled={
                clearAllInput.trim().toUpperCase() !== 'DELETE ALL USER DATA' &&
                clearAllInput.trim().toUpperCase() !== 'DELETE'
              }
              onClick={handleExecuteClearAll}
              leftIcon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Permanently Reclaim All User Data
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
