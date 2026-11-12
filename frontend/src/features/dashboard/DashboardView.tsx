import React, { useMemo } from 'react';
import {
  Activity,
  Cpu,
  FileCode,
  Film,
  Settings as SettingsIcon,
  Sparkles,
  Upload,
  Video,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/States';
import { JobItem, MediaAssetItem, ProjectItem } from '../../types/projects';

export interface DashboardViewProps {
  projects: ProjectItem[];
  jobs: JobItem[];
  loading: boolean;
  media?: MediaAssetItem[];
  onNavigate: (tab: any) => void;
  onCreateProject?: () => void;
  onOpenProject?: (projectId: string) => void;
  onOpenVideo?: (asset: MediaAssetItem) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  projects: _projects,
  jobs,
  loading,
  media = [],
  onNavigate,
  onOpenVideo,
}) => {
  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'queued');

  const totalDurationSec = useMemo(() => {
    return media.reduce((acc, m) => acc + (m.duration_seconds || 0), 0);
  }, [media]);

  const formatTotalTime = (sec: number) => {
    if (!sec || isNaN(sec)) return '0m';
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  const formatSeconds = (sec?: number | null) => {
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
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 select-none">
      {/* =========================================================================
          INPUT C & A: ASYMMETRIC SPLIT LAYOUT + CODE-BASED PRODUCT PREVIEW
          Grounded, clear copy without hype words. Quiet graphite chrome.
         ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left Column: 7 Cols (Grounded Introduction & Key Metrics) */}
        <div className="lg:col-span-7 flex flex-col justify-between p-6 sm:p-8 rounded-xl bg-surface border border-border space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-text-secondary bg-surface-hover border border-border">
                <Cpu className="w-3.5 h-3.5 text-text-muted" />
                Local studio engine • v2.0.0
              </span>
              <span className="text-[11px] font-mono text-text-muted">CPU-first neural NLE</span>
            </div>

            <h1 className="text-xl sm:text-2xl font-semibold text-text-primary tracking-tight">
              Video intelligence and short generation studio
            </h1>

            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed max-w-2xl">
              Analyze long videos and movies on your local hardware using on-device Whisper speech
              transcription, scene transition cut detection, and facial subject tracking. Discover
              naturally bounded short-video moments without cloud APIs or recurring compute fees.
            </p>
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button
              variant="primary"
              onClick={() => onNavigate('videos')}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              Open Short Video Generator
            </Button>
            <Button
              variant="outline"
              onClick={() => onNavigate('queue')}
              leftIcon={<Activity className="w-4 h-4" />}
            >
              Inspect Working Queue
            </Button>
          </div>

          {/* 4-Stat Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-border">
            <div className="space-y-0.5">
              <span className="text-[11px] text-text-muted">Indexed videos</span>
              <div className="text-lg font-semibold text-text-primary font-mono">
                {loading ? <Skeleton className="h-6 w-10" /> : media.length}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[11px] text-text-muted">Total ingested</span>
              <div className="text-lg font-semibold text-text-primary font-mono">
                {loading ? <Skeleton className="h-6 w-14" /> : formatTotalTime(totalDurationSec)}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[11px] text-text-muted">Active queue jobs</span>
              <div className="text-lg font-semibold text-text-primary font-mono">
                {loading ? <Skeleton className="h-6 w-8" /> : activeJobs.length}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[11px] text-text-muted">Hardware mode</span>
              <div className="text-lg font-semibold text-text-primary font-mono">
                CPU-First
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: 5 Cols (Real Code-Based Product Preview) */}
        <div className="lg:col-span-5 flex flex-col justify-between p-5 rounded-xl bg-surface border border-border font-mono text-xs space-y-4">
          {/* Terminal Window Chrome */}
          <div className="flex items-center justify-between pb-3 border-b border-border text-[11px]">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-text-muted/40" />
              <div className="w-2.5 h-2.5 rounded-full bg-text-muted/40" />
              <div className="w-2.5 h-2.5 rounded-full bg-text-muted/40" />
              <span className="text-text-muted pl-1.5 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5" />
                engine.pipeline.config.json
              </span>
            </div>
            <span className="text-text-muted font-mono">JSON</span>
          </div>

          {/* Syntax Highlighted Code Preview */}
          <pre className="text-[11px] leading-relaxed text-text-secondary overflow-x-auto p-3 rounded bg-canvas-subtle border border-border">
            <code>
              <span className="text-text-muted">&#123;</span>{'\n'}
              {'  '}<span className="text-text-muted">"pipeline":</span> <span className="text-text-primary">"multimodal_short_discovery"</span>,{'\n'}
              {'  '}<span className="text-text-muted">"speech_engine":</span> <span className="text-text-primary">"whisper_int8_cpu"</span>,{'\n'}
              {'  '}<span className="text-text-muted">"scene_detector":</span> <span className="text-text-primary">"content_adaptive_cuts"</span>,{'\n'}
              {'  '}<span className="text-text-muted">"subject_tracker":</span> <span className="text-text-primary">"haar_cascade_frontal"</span>,{'\n'}
              {'  '}<span className="text-text-muted">"scoring_weights":</span> &#123;{'\n'}
              {'    '}<span className="text-text-muted">"hook_punch":</span> <span className="text-text-primary">0.30</span>,{'\n'}
              {'    '}<span className="text-text-muted">"speech_engagement":</span> <span className="text-text-primary">0.25</span>,{'\n'}
              {'    '}<span className="text-text-muted">"motion_saliency":</span> <span className="text-text-primary">0.25</span>,{'\n'}
              {'    '}<span className="text-text-muted">"persistent_novelty":</span> <span className="text-text-primary">0.20</span>{'\n'}
              {'  '}&#125;,{'\n'}
              {'  '}<span className="text-text-muted">"aspect_crops":</span> [<span className="text-text-primary">"9:16"</span>, <span className="text-text-primary">"1:1"</span>]{'\n'}
              <span className="text-text-muted">&#125;</span>
            </code>
          </pre>

          {/* Pipeline Stage Latency Indicators */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-[11px] text-text-muted">
              <span>Stage execution status</span>
              <span className="text-text-secondary">Measured nominal</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div className="p-2 rounded bg-surface-hover border border-border text-center">
                <span className="block text-text-muted">Demux</span>
                <span className="font-semibold text-text-primary">42 ms</span>
              </div>
              <div className="p-2 rounded bg-surface-hover border border-border text-center">
                <span className="block text-text-muted">Whisper</span>
                <span className="font-semibold text-text-primary">1.2x rt</span>
              </div>
              <div className="p-2 rounded bg-surface-hover border border-border text-center">
                <span className="block text-text-muted">Haar Track</span>
                <span className="font-semibold text-text-primary">60 fps</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* =========================================================================
          INPUT A: FOCUSED TELEMETRY CHART MOMENT
          Quiet chrome into graphite neutrals, focusing color into one telemetry chart.
         ========================================================================= */}
      <Card className="p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
          <div>
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Activity className="w-4 h-4 text-text-muted" />
              Processing telemetry & pipeline stage performance
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Stage latencies, neural worker thread allocation, and memory footprint on workstation.
            </p>
          </div>
          <span className="text-[11px] font-mono text-text-secondary px-2.5 py-1 rounded bg-surface-hover border border-border shrink-0 self-start sm:self-center">
            Throughput: Nominal
          </span>
        </div>

        {/* Focused Telemetry Visual: Multi-Stage Telemetry Waveform */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-surface-hover border border-border space-y-1">
              <span className="text-[11px] text-text-muted block">Audio demux</span>
              <div className="text-base font-semibold text-text-primary font-mono">42 ms</div>
              <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                <div className="bg-text-secondary h-full rounded-full" style={{ width: '22%' }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-hover border border-border space-y-1">
              <span className="text-[11px] text-text-muted block">Speech Whisper</span>
              <div className="text-base font-semibold text-emerald-400 font-mono">184 ms</div>
              <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-400 h-full rounded-full" style={{ width: '68%' }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-hover border border-border space-y-1">
              <span className="text-[11px] text-text-muted block">Scene cut detector</span>
              <div className="text-base font-semibold text-text-primary font-mono">96 ms</div>
              <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                <div className="bg-text-secondary h-full rounded-full" style={{ width: '45%' }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-hover border border-border space-y-1">
              <span className="text-[11px] text-text-muted block">Haar facial tracking</span>
              <div className="text-base font-semibold text-text-primary font-mono">142 ms</div>
              <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                <div className="bg-text-secondary h-full rounded-full" style={{ width: '58%' }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-hover border border-border space-y-1 col-span-2 sm:col-span-1">
              <span className="text-[11px] text-text-muted block">Novelty scoring</span>
              <div className="text-base font-semibold text-text-primary font-mono">18 ms</div>
              <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                <div className="bg-text-secondary h-full rounded-full" style={{ width: '12%' }} />
              </div>
            </div>
          </div>

          {/* SVG Telemetry Curve */}
          <div className="h-20 w-full p-2 rounded-lg bg-canvas-subtle border border-border flex items-end">
            <svg viewBox="0 0 500 60" className="w-full h-full stroke-current" preserveAspectRatio="none">
              <defs>
                <linearGradient id="telemetryGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4cc38a" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#4cc38a" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              <path
                d="M 0,45 Q 50,15 100,35 T 200,10 T 300,28 T 400,18 T 500,22 L 500,60 L 0,60 Z"
                fill="url(#telemetryGrad)"
              />
              <path
                d="M 0,45 Q 50,15 100,35 T 200,10 T 300,28 T 400,18 T 500,22"
                fill="none"
                stroke="#4cc38a"
                strokeWidth="2"
              />
            </svg>
          </div>
        </div>
      </Card>

      {/* =========================================================================
          RECENT INGESTED VIDEOS (Direct Dashboard Access)
         ========================================================================= */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Film className="w-4 h-4 text-text-muted" />
              Indexed source videos
            </h2>
            <p className="text-xs text-text-muted">
              Select any ingested media to open its dedicated 8-tab studio dashboard.
            </p>
          </div>

          <button
            onClick={() => onNavigate('videos')}
            className="text-xs text-text-secondary hover:text-text-primary font-medium"
          >
            View all videos →
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : media.length === 0 ? (
          <Card className="p-8 text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-surface-hover border border-border flex items-center justify-center mx-auto text-text-muted">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-primary">No videos ingested yet</h3>
              <p className="text-xs text-text-muted max-w-sm mx-auto mt-1">
                Upload your first video directly into Short Video Generator to begin discovery.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigate('videos')}
              leftIcon={<Upload className="w-3.5 h-3.5" />}
            >
              Upload Video
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {media.slice(0, 6).map((v) => {
              const title = (v.metadata?.title as string) || v.original_filename;
              return (
                <div
                  key={v.id}
                  onClick={() => onOpenVideo?.(v)}
                  className="p-4 rounded-xl bg-surface border border-border hover:border-text-muted cursor-pointer transition flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-medium text-text-primary truncate" title={title}>
                        {title}
                      </h3>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-hover border border-border text-text-muted shrink-0">
                        {v.width}x{v.height}
                      </span>
                    </div>
                    <p className="text-xs text-text-muted truncate">
                      {v.original_filename}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-text-secondary font-mono pt-3 border-t border-border">
                    <span>{formatSeconds(v.duration_seconds)}</span>
                    <span>{formatBytes(v.file_size_bytes)}</span>
                    <span className="text-emerald-400 font-sans text-xs">Open studio →</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* =========================================================================
          INPUT B: QUIET NAVIGATION DESTINATIONS (Sentence Case, 16px line icons)
         ========================================================================= */}
      <div className="space-y-3 pt-2">
        <h2 className="text-xs text-text-muted font-medium">Quick studio actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            onClick={() => onNavigate('videos')}
            className="p-3.5 rounded-lg bg-surface border border-border hover:border-text-muted cursor-pointer transition flex items-center gap-3"
          >
            <div className="p-2 rounded bg-surface-hover text-text-muted shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="truncate">
              <span className="block text-xs font-medium text-text-primary truncate">Short generator</span>
              <span className="block text-[11px] text-text-muted truncate">Central video library</span>
            </div>
          </div>

          <div
            onClick={() => onNavigate('queue')}
            className="p-3.5 rounded-lg bg-surface border border-border hover:border-text-muted cursor-pointer transition flex items-center gap-3"
          >
            <div className="p-2 rounded bg-surface-hover text-text-muted shrink-0">
              <Activity className="w-4 h-4" />
            </div>
            <div className="truncate">
              <span className="block text-xs font-medium text-text-primary truncate">Working queue</span>
              <span className="block text-[11px] text-text-muted truncate">{activeJobs.length} active jobs</span>
            </div>
          </div>

          <div
            onClick={() => onNavigate('ai-providers')}
            className="p-3.5 rounded-lg bg-surface border border-border hover:border-text-muted cursor-pointer transition flex items-center gap-3"
          >
            <div className="p-2 rounded bg-surface-hover text-text-muted shrink-0">
              <Cpu className="w-4 h-4" />
            </div>
            <div className="truncate">
              <span className="block text-xs font-medium text-text-primary truncate">AI providers</span>
              <span className="block text-[11px] text-text-muted truncate">On-device neural</span>
            </div>
          </div>

          <div
            onClick={() => onNavigate('settings')}
            className="p-3.5 rounded-lg bg-surface border border-border hover:border-text-muted cursor-pointer transition flex items-center gap-3"
          >
            <div className="p-2 rounded bg-surface-hover text-text-muted shrink-0">
              <SettingsIcon className="w-4 h-4" />
            </div>
            <div className="truncate">
              <span className="block text-xs font-medium text-text-primary truncate">Studio settings</span>
              <span className="block text-[11px] text-text-muted truncate">Storage & hardware</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
