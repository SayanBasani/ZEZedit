import React, { useEffect, useRef, useState } from 'react';
import { Cpu, HardDrive, Layers, Pin, ShieldCheck } from 'lucide-react';
import { fetchSystemResources } from '../../services/apiClient';
import { SystemResourceMetrics } from '../../types/system';

export const ResourceInspector: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemResourceMetrics | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const closeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;

    const loadMetrics = async () => {
      try {
        const data = await fetchSystemResources();
        if (isMounted) setMetrics(data);
      } catch {
        // Silently tolerate intermittent sampling blips
      }
    };

    void loadMetrics();
    // 3.5s bounded sampling interval
    const interval = setInterval(() => {
      void loadMetrics();
    }, 3500);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current);
    };
  }, []);

  // Keyboard Escape and Outside Click dismiss
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        setIsPinned(false);
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsPinned(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setIsOpen(true);
  };

  const handleMouseLeave = () => {
    if (isPinned) return;
    closeTimeoutRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 250);
  };

  const togglePin = () => {
    setIsPinned(!isPinned);
  };

  // Determine health color based on thresholds
  const cpuVal = metrics?.cpu_percent ?? 0;
  const memVal = metrics?.memory_percent ?? 0;
  const cpuColor = cpuVal > 85 ? 'text-red-400' : cpuVal > 60 ? 'text-amber-400' : 'text-emerald-400';
  const memColor = memVal > 85 ? 'text-red-400' : memVal > 70 ? 'text-amber-400' : 'text-sky-400';

  return (
    <div
      ref={containerRef}
      className="relative inline-flex items-center"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Compact Default Indicator Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface border border-border text-xs hover:border-border-hover transition select-none"
        title="Hardware & Resource Monitor (Hover or click to inspect)"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-label="Hardware resource monitor"
      >
        <span className="flex items-center gap-1 font-mono text-[11px]">
          <Cpu className={`w-3.5 h-3.5 ${cpuColor}`} />
          <span className="text-text-primary">{cpuVal.toFixed(0)}%</span>
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1 font-mono text-[11px]">
          <HardDrive className={`w-3.5 h-3.5 ${memColor}`} />
          <span className="text-text-secondary">{memVal.toFixed(0)}%</span>
        </span>
        {metrics && metrics.active_workers > 0 && (
          <>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1 text-[11px] text-indigo-400">
              <Layers className="w-3 h-3 animate-pulse" />
              <span>{metrics.active_workers}w</span>
            </span>
          </>
        )}
      </button>

      {/* Floating Hover / Pinned Window */}
      {isOpen && metrics && (
        <div
          role="dialog"
          aria-label="Hardware Resource Inspector"
          className="absolute right-0 top-full mt-2 w-80 rounded-xl bg-surface border border-border shadow-2xl p-4 z-50 text-xs space-y-3.5 backdrop-blur-md animate-in fade-in slide-in-from-top-1 duration-150"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-1.5 font-semibold text-text-primary text-xs uppercase tracking-wider">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>Resource Inspector</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={togglePin}
                className={`p-1 rounded hover:bg-surface-hover transition ${
                  isPinned ? 'text-indigo-400 bg-indigo-500/10' : 'text-text-muted hover:text-text-primary'
                }`}
                title={isPinned ? 'Unpin floating window' : 'Pin window open'}
                aria-label="Pin inspector window"
              >
                <Pin className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* CPU Breakdown */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-text-secondary">
              <span>Host CPU Usage</span>
              <span className={`font-mono font-semibold ${cpuColor}`}>{metrics.cpu_percent.toFixed(1)}%</span>
            </div>
            {/* Progress bar */}
            <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  cpuVal > 85 ? 'bg-red-500' : cpuVal > 60 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(metrics.cpu_percent, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-text-muted font-mono">
              <span>ZezEdit Process: {metrics.process_cpu_percent.toFixed(1)}%</span>
              <span>
                {metrics.cpu_count_physical} Cores / {metrics.cpu_count_logical} Threads
              </span>
            </div>
          </div>

          {/* Memory Breakdown */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-text-secondary">
              <span>System RAM</span>
              <span className={`font-mono font-semibold ${memColor}`}>
                {metrics.memory_percent.toFixed(1)}% ({Math.round(metrics.memory_used_mb / 1024)}GB /{' '}
                {Math.round(metrics.memory_total_mb / 1024)}GB)
              </span>
            </div>
            {/* Progress bar */}
            <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  memVal > 85 ? 'bg-red-500' : memVal > 70 ? 'bg-amber-500' : 'bg-sky-500'
                }`}
                style={{ width: `${Math.min(metrics.memory_percent, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-text-muted font-mono">
              <span>App RSS: {metrics.process_memory_rss_mb.toFixed(0)} MB</span>
              <span>Free: {Math.round(metrics.memory_available_mb / 1024)} GB</span>
            </div>
          </div>

          {/* Worker Concurrency */}
          <div className="pt-1 border-t border-border flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5 text-text-secondary">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>Job Concurrency</span>
            </div>
            <div className="font-mono text-text-primary">
              <span className="text-emerald-400">{metrics.active_workers} Active</span>
              <span className="text-text-muted"> / {metrics.pending_jobs} Queued</span>
              <span className="text-text-muted"> (Max: {metrics.max_concurrent_jobs})</span>
            </div>
          </div>

          {/* Execution Mode Footer */}
          <div className="pt-2 border-t border-border flex items-center justify-between text-[10px] text-text-muted">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>CPU-First Baseline</span>
            </span>
            <span className="font-mono">{metrics.timestamp.slice(11, 19)} UTC</span>
          </div>
        </div>
      )}
    </div>
  );
};
