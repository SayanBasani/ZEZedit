import React, { useEffect, useState } from 'react';
import {
  Cpu,
  FolderLock,
  Layers,
  Moon,
  RefreshCw,
  Save,
  Server,
  Sun,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { useTheme } from '../../context/ThemeContext';
import { fetchAppSettings, fetchHealth, updateAppSettings } from '../../services/apiClient';
import { HealthResponse } from '../../types/health';
import { AppSettingsData } from '../../types/projects';

export const SettingsManager: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [settings, setSettings] = useState<AppSettingsData | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // Form states
  const [proxyRes, setProxyRes] = useState('480p');
  const [maxThreads, setMaxThreads] = useState(4);
  const [maxJobs, setMaxJobs] = useState(1);
  const [defaultExportRes, setDefaultExportRes] = useState('1080x1920');

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, h] = await Promise.all([fetchAppSettings(), fetchHealth()]);
      setSettings(s);
      setHealth(h);
      setProxyRes(s.proxy_resolution || '480p');
      setMaxThreads(s.cpu_processing_limits?.max_threads || 4);
      setMaxJobs(s.cpu_processing_limits?.max_concurrent_jobs || 1);
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

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorToast(null);
    setSuccessToast(null);
    try {
      const updated = await updateAppSettings({
        proxy_resolution: proxyRes,
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

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Studio Settings</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Configure local hardware limits, theme, storage paths, and AI providers.
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
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs">
          {successToast}
        </div>
      )}
      {errorToast && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs">
          {errorToast}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Appearance & Theme Section */}
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

        {/* Processing & Hardware Limits */}
        <Card className="space-y-4">
          <div className="flex items-center gap-2 border-b border-border pb-2.5">
            <Cpu className="w-4 h-4 text-brand" />
            <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
              CPU-First Hardware Limits
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-text-secondary">
                Max FFmpeg Worker Threads
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
                Recommended: 4 threads for Intel Core i3-1220P to prevent UI freeze.
              </span>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-text-secondary">
                Max Concurrent Heavy Jobs
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
                Proxy Scrub Resolution
              </label>
              <select
                value={proxyRes}
                onChange={(e) => setProxyRes(e.target.value)}
                className="w-full bg-canvas-subtle border border-border rounded-lg text-xs text-text-primary px-3 py-2"
              >
                <option value="360p">360p (Fastest, low memory)</option>
                <option value="480p">480p (Standard balanced)</option>
                <option value="720p">720p (High clarity)</option>
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

        {/* Storage Root Information (Read-Only) */}
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
              ℹ Storage paths are locked to prevent recursive drive root operations.
            </p>
          </div>
        </Card>

        {/* AI Providers & Diagnostics */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Local AI Provider Status
              </h2>
            </div>
            {health && (
              <Badge variant={health.ollama.reachable ? 'success' : 'default'}>
                {health.ollama.reachable ? 'Reachable' : 'Offline'}
              </Badge>
            )}
          </div>

          <div className="text-xs text-text-secondary space-y-1.5">
            <p>
              Endpoint:{' '}
              <span className="font-mono text-text-primary">
                {settings?.ai_provider_config?.ollama_base_url || 'http://127.0.0.1:11434'}
              </span>
            </p>
            <p>
              Installed Models:{' '}
              <span className="font-mono text-text-primary">
                {health?.ollama?.installed_models?.join(', ') || 'None detected'}
              </span>
            </p>
            <p className="text-[11px] text-text-muted">
              Secrets: Stored in .env and redacted in all API responses.
            </p>
          </div>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" isLoading={saving} leftIcon={<Save className="w-4 h-4" />}>
            Save Settings
          </Button>
        </div>
      </form>
    </div>
  );
};
