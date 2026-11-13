import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BookOpen,
  Brain,
  ChevronLeft,
  ChevronRight,
  Film,
  LayoutDashboard,
  Menu,
  Moon,
  Settings as SettingsIcon,
  Shield,
  Sparkles,
  Sun,
  X,
} from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ResourceInspector } from '../components/system/ResourceInspector';
import { useToast } from '../components/system/ToastNotificationCenter';
import { useTheme } from '../context/ThemeContext';
import { DashboardView } from '../features/dashboard/DashboardView';
import { SettingsManager } from '../features/settings/SettingsManager';
import { WorkingQueueView } from '../features/queue/WorkingQueueView';
import { AIProviderManager } from '../features/providers/AIProviderManager';
import { DocumentationView } from '../features/docs/DocumentationView';
import { ShortVideoGeneratorLibrary } from '../features/videos/ShortVideoGeneratorLibrary';
import { VideoEditDashboard } from '../features/videos/VideoEditDashboard';
import {
  fetchHealth,
  fetchJobs,
  fetchProjectMedia,
  fetchProjects,
} from '../services/apiClient';
import { HealthResponse } from '../types/health';
import { JobItem, MediaAssetItem, ProjectItem } from '../types/projects';

export type NavSection =
  | 'dashboard'
  | 'videos'
  | 'video-dashboard'
  | 'projects'
  | 'media'
  | 'studio'
  | 'workspace'
  | 'analysis'
  | 'highlights'
  | 'reframing'
  | 'timeline'
  | 'ai-editor'
  | 'queue'
  | 'ai-providers'
  | 'docs'
  | 'characters'
  | 'exports'
  | 'settings'
  | 'diagnostics';

export const App: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<NavSection>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Global Centralized State (avoiding repeated duplicate polling)
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  const [projectMedia, setProjectMedia] = useState<MediaAssetItem[]>([]);
  const [selectedMediaAsset, setSelectedMediaAsset] = useState<MediaAssetItem | null>(null);
  const [studioAssetId, setStudioAssetId] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const prevJobsRef = React.useRef<Map<string, string>>(new Map());

  const checkJobTransitions = useCallback(
    (newJobs: JobItem[]) => {
      const prevMap = prevJobsRef.current;
      if (prevMap.size > 0) {
        for (const job of newJobs) {
          const prevStatus = prevMap.get(job.id);
          if (prevStatus === 'running' || prevStatus === 'queued') {
            const friendlyType = (job.job_type || 'Background job').replace(/_/g, ' ');
            if (job.status === 'completed') {
              toast.success(`${friendlyType} finished successfully.`, {
                title: 'Operation Completed',
                action: {
                  label: 'View Queue',
                  onClick: () => setActiveTab('queue'),
                },
              });
            } else if (job.status === 'failed') {
              toast.error(`${friendlyType} failed: ${job.error_message || 'Unknown error'}`, {
                title: 'Operation Failed',
                action: {
                  label: 'Inspect Queue',
                  onClick: () => setActiveTab('queue'),
                },
              });
            }
          }
        }
      }
      const nextMap = new Map<string, string>();
      for (const job of newJobs) {
        nextMap.set(job.id, job.status);
      }
      prevJobsRef.current = nextMap;
    },
    [toast]
  );

  const loadProjectMedia = useCallback(async (pid: string) => {
    if (!pid) return;
    try {
      const mediaRes = await fetchProjectMedia(pid);
      setProjectMedia(mediaRes.items);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path.startsWith('/videos/')) {
        const aid = path.slice('/videos/'.length).split('/')[0];
        if (aid) {
          setStudioAssetId(aid);
          setActiveTab('video-dashboard');
          return;
        }
      }
      if (path.startsWith('/studio/')) {
        const aid = path.slice('/studio/'.length).split('/')[0];
        if (aid) {
          setStudioAssetId(aid);
          setActiveTab('video-dashboard');
          return;
        }
      }
      if (path === '/videos' || path === '/media') setActiveTab('videos');
      else if (path === '/queue') setActiveTab('queue');
      else if (path === '/ai-providers') setActiveTab('ai-providers');
      else if (path === '/settings') setActiveTab('settings');
      else if (path === '/' || path === '/dashboard') setActiveTab('dashboard');
    };

    window.addEventListener('popstate', handlePopState);
    handlePopState();
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const loadGlobalData = useCallback(async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const [projRes, jobsRes, healthRes] = await Promise.all([
        fetchProjects(true),
        fetchJobs(),
        fetchHealth(),
      ]);
      setProjects(projRes.items);
      setJobs(jobsRes.items);
      checkJobTransitions(jobsRes.items);
      setHealth(healthRes);

      setSelectedProjectId((currentPid) => {
        if (currentPid === 'all') return 'all';
        if (currentPid && projRes.items.some((p) => p.id === currentPid)) {
          return currentPid;
        }
        return 'all';
      });
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Backend unreachable');
    } finally {
      setLoading(false);
    }
  }, [checkJobTransitions]);

  useEffect(() => {
    if (selectedProjectId) {
      void loadProjectMedia(selectedProjectId);
    }
  }, [selectedProjectId, loadProjectMedia]);

  useEffect(() => {
    void loadGlobalData();
    // Poll jobs & health every 15s gently without high-frequency spam
    const interval = setInterval(() => {
      void fetchJobs()
        .then((r) => {
          setJobs(r.items);
          checkJobTransitions(r.items);
        })
        .catch(() => {});
      void fetchHealth()
        .then((h) => setHealth(h))
        .catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [loadGlobalData, checkJobTransitions]);

  const activeJobsCount = jobs.filter((j) => j.status === 'running').length;

  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden flex bg-canvas text-text-primary">
      {/* Mobile Backdrop Overlay */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs md:hidden"
          aria-hidden="true"
        />
      )}

      {/* Sidebar (Desktop Collapsible + Mobile Slide-over) */}
      <aside
        className={`${
          mobileMenuOpen ? 'fixed inset-y-0 left-0 z-50 flex shadow-2xl' : 'hidden md:flex'
        } ${
          sidebarCollapsed ? 'w-16' : 'w-60'
        } h-full shrink-0 flex-col bg-surface border-r border-border transition-all duration-200 select-none`}
      >
        {/* Sidebar Brand Header */}
        <div className="h-14 px-3.5 border-b border-border flex items-center justify-between shrink-0">
          <div
            onClick={() => setActiveTab('dashboard')}
            className="flex items-center gap-2.5 cursor-pointer truncate"
          >
            <div className="p-1.5 rounded-md bg-surface-hover border border-border text-text-primary shrink-0">
              <Film className="w-4 h-4" />
            </div>
            {!sidebarCollapsed && (
              <div className="truncate">
                <span className="font-semibold text-sm text-text-primary tracking-tight">
                  ZezEdit 2.0
                </span>
                <span className="block text-[10px] text-text-muted font-mono truncate">
                  Studio NLE
                </span>
              </div>
            )}
          </div>

          {/* Mobile close button */}
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="md:hidden p-1 text-text-muted hover:text-text-primary"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Items: 34px rows with 2px gaps */}
        <nav className="flex-1 min-h-0 overflow-y-auto p-2 space-y-0.5">
          {/* 1. Dashboard */}
          <SidebarNavButton
            active={activeTab === 'dashboard'}
            collapsed={sidebarCollapsed}
            icon={<LayoutDashboard className="w-4 h-4" />}
            label="Dashboard"
            onClick={() => {
              setActiveTab('dashboard');
              setMobileMenuOpen(false);
            }}
          />

          {/* 2. Short Video Generator (Central Video Library) */}
          <SidebarNavButton
            active={activeTab === 'videos' || activeTab === 'video-dashboard'}
            collapsed={sidebarCollapsed}
            icon={<Sparkles className="w-4 h-4" />}
            label="Short Video Generator"
            badge={projectMedia.length ? String(projectMedia.length) : undefined}
            onClick={() => {
              setActiveTab('videos');
              setMobileMenuOpen(false);
            }}
          />

          {/* 3. Operations & Queue */}
          <div className="pt-2.5 pb-0.5">
            {!sidebarCollapsed && (
              <span className="px-2 text-[11px] font-medium text-text-muted">
                Operations
              </span>
            )}
          </div>

          <SidebarNavButton
            active={activeTab === 'queue'}
            collapsed={sidebarCollapsed}
            icon={<Activity className="w-4 h-4" />}
            label="Working Queue"
            badge={activeJobsCount > 0 ? String(activeJobsCount) : undefined}
            onClick={() => {
              setActiveTab('queue');
              setMobileMenuOpen(false);
            }}
          />

          {/* 4. AI Providers */}
          <SidebarNavButton
            active={activeTab === 'ai-providers'}
            collapsed={sidebarCollapsed}
            icon={<Brain className="w-4 h-4" />}
            label="AI Providers"
            onClick={() => {
              setActiveTab('ai-providers');
              setMobileMenuOpen(false);
            }}
          />

          {/* 5. System & Settings */}
          <div className="pt-2.5 pb-0.5">
            {!sidebarCollapsed && (
              <span className="px-2 text-[11px] font-medium text-text-muted">
                System
              </span>
            )}
          </div>

          <SidebarNavButton
            active={activeTab === 'settings'}
            collapsed={sidebarCollapsed}
            icon={<SettingsIcon className="w-4 h-4" />}
            label="Settings"
            onClick={() => {
              setActiveTab('settings');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'docs'}
            collapsed={sidebarCollapsed}
            icon={<BookOpen className="w-4 h-4" />}
            label="Documentation"
            onClick={() => {
              setActiveTab('docs');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'diagnostics'}
            collapsed={sidebarCollapsed}
            icon={<Shield className="w-4 h-4" />}
            label="Diagnostics"
            onClick={() => {
              setActiveTab('diagnostics');
              setMobileMenuOpen(false);
            }}
          />
        </nav>

        {/* Sidebar Footer with Collapse Toggle */}
        <div className="p-2 border-t border-border flex items-center justify-between shrink-0">
          {!sidebarCollapsed && (
            <span className="text-[10px] font-mono text-text-muted pl-2">CPU-First</span>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden md:flex p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover ml-auto"
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>
      </aside>

      {/* Main Viewport Container */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-14 shrink-0 border-b border-border bg-surface/50 backdrop-blur-sm px-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover"
              aria-label="Open mobile navigation"
            >
              <Menu className="w-4 h-4" />
            </button>
            <h2 className="text-sm font-medium text-text-primary">
              {activeTab === 'dashboard'
                ? 'Dashboard'
                : activeTab === 'videos'
                ? 'Short Video Generator'
                : activeTab === 'video-dashboard'
                ? 'Video Edit Dashboard'
                : activeTab === 'projects'
                ? 'Projects Manager'
                : activeTab === 'media'
                ? 'Short Video Generator'
                : activeTab === 'studio' || activeTab === 'workspace'
                ? 'Video Edit Dashboard'
                : activeTab === 'analysis'
                ? 'Video Analysis Workspace'
                : activeTab === 'highlights'
                ? 'AI Highlights & Shorts Studio'
                : activeTab === 'reframing'
                ? 'Smart Reframing & Subject Tracking Studio'
                : activeTab === 'exports'
                ? 'Shorts Rendering & Export Studio'
                : activeTab === 'queue'
                ? 'Working Queue & Job Orchestration'
                : activeTab === 'ai-providers'
                ? 'AI Provider Manager'
                : activeTab === 'docs'
                ? 'Studio Documentation'
                : activeTab === 'settings'
                ? 'Studio Settings'
                : 'Diagnostics & Health'}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Live CPU & RAM Resource Inspector Hover Window */}
            <ResourceInspector />

            {/* Backend Health Badge */}
            <Badge
              variant={health?.status === 'ready' ? 'success' : 'warning'}
              icon={<Shield className="w-3 h-3" />}
            >
              {health?.status === 'ready' ? 'Ready' : health?.status || 'Connecting'}
            </Badge>

            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface transition"
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-indigo-500" />
              )}
            </button>
          </div>
        </header>

        {/* Global Error Banner */}
        {globalError && (
          <div className="px-4 py-2.5 bg-red-500/10 border-b border-red-500/30 text-red-400 text-xs flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>Backend Connection Error: {globalError}</span>
            </div>
            <Button size="sm" variant="ghost" onClick={() => void loadGlobalData()}>
              Retry
            </Button>
          </div>
        )}

        {/* Scrollable View Body */}
        <main className="flex-1 min-h-0 min-w-0 overflow-y-auto overscroll-contain">
          {activeTab === 'dashboard' && (
            <DashboardView
              projects={projects}
              jobs={jobs}
              loading={loading}
              media={projectMedia}
              onNavigate={(tab) => {
                if (tab === 'media' || tab === 'projects') {
                  setActiveTab('videos');
                } else {
                  setActiveTab(tab);
                }
              }}
              onCreateProject={() => setActiveTab('videos')}
              onOpenProject={(pid) => {
                setSelectedProjectId(pid);
                setActiveTab('videos');
              }}
              onOpenVideo={(asset) => {
                setSelectedMediaAsset(asset);
                setStudioAssetId(asset.id);
                setActiveTab('video-dashboard');
                window.history.pushState(null, '', `/videos/${asset.id}`);
              }}
            />
          )}

          {(activeTab === 'videos' || activeTab === 'media') && (
            <ShortVideoGeneratorLibrary
              onOpenDashboard={(asset) => {
                setSelectedMediaAsset(asset);
                setStudioAssetId(asset.id);
                setActiveTab('video-dashboard');
                window.history.pushState(null, '', `/videos/${asset.id}`);
              }}
            />
          )}

          {(activeTab === 'video-dashboard' || activeTab === 'studio') && (
            (studioAssetId || selectedMediaAsset?.id || projectMedia[0]?.id) ? (
              <VideoEditDashboard
                assetId={studioAssetId || selectedMediaAsset?.id || projectMedia[0]?.id || ''}
                projectId={selectedMediaAsset?.project_id || 'default'}
                onBack={() => {
                  setActiveTab('videos');
                  window.history.pushState(null, '', '/videos');
                }}
              />
            ) : (
              <ShortVideoGeneratorLibrary
                onOpenDashboard={(asset) => {
                  setSelectedMediaAsset(asset);
                  setStudioAssetId(asset.id);
                  setActiveTab('video-dashboard');
                  window.history.pushState(null, '', `/videos/${asset.id}`);
                }}
              />
            )
          )}

          {activeTab === 'queue' && (
            <WorkingQueueView
              projects={projects}
              onOpenProject={() => setActiveTab('videos')}
            />
          )}

          {activeTab === 'ai-providers' && <AIProviderManager />}

          {activeTab === 'docs' && <DocumentationView />}

          {(activeTab === 'settings' || activeTab === 'diagnostics') && <SettingsManager />}
        </main>
      </div>
    </div>
  );
};

// Sub-component for individual sidebar items
interface SidebarNavButtonProps {
  active: boolean;
  collapsed: boolean;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  disabled?: boolean;
  title?: string;
  onClick?: () => void;
}

const SidebarNavButton: React.FC<SidebarNavButtonProps> = ({
  active,
  collapsed,
  icon,
  label,
  badge,
  disabled = false,
  title,
  onClick,
}) => {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={title || (collapsed ? label : undefined)}
      className={`w-full h-[34px] flex items-center gap-2 px-2.5 rounded-md text-xs font-medium transition select-none ${
        disabled
          ? 'opacity-40 cursor-not-allowed text-text-muted'
          : active
          ? 'bg-surface-active text-text-primary border border-border shadow-2xs'
          : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
      } ${collapsed ? 'justify-center px-0' : ''}`}
    >
      <span className={`shrink-0 ${active ? 'text-text-primary' : 'text-text-muted'}`}>
        {icon}
      </span>
      {!collapsed && <span className="truncate flex-1 text-left">{label}</span>}
      {!collapsed && badge && (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-hover border border-border text-text-muted shrink-0">
          {badge}
        </span>
      )}
    </button>
  );
};

export default App;
