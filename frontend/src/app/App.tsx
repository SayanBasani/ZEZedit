import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Camera,
  ChevronLeft,
  ChevronRight,
  Film,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Moon,
  Scissors,
  Settings as SettingsIcon,
  Shield,
  Sparkles,
  Sun,
  Users,
  Video,
  X,
} from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useTheme } from '../context/ThemeContext';
import { DashboardView } from '../features/dashboard/DashboardView';
import { FoundationOverview } from '../features/dashboard/FoundationOverview';
import { MediaLibraryView } from '../features/media/MediaLibraryView';
import { AnalysisWorkspace } from '../features/analysis/AnalysisWorkspace';
import { HighlightsWorkspace } from '../features/highlights/HighlightsWorkspace';
import { ReframingWorkspace } from '../features/reframing/ReframingWorkspace';
import { ProjectsManager } from '../features/projects/ProjectsManager';
import { SettingsManager } from '../features/settings/SettingsManager';
import {
  archiveProject,
  createProject,
  deleteProject,
  fetchHealth,
  fetchJobs,
  fetchMediaStats,
  fetchProjectMedia,
  fetchProjects,
  restoreProject,
} from '../services/apiClient';
import { HealthResponse } from '../types/health';
import { JobItem, MediaAssetItem, MediaStorageStats, ProjectItem } from '../types/projects';

export type NavSection =
  | 'dashboard'
  | 'projects'
  | 'media'
  | 'analysis'
  | 'highlights'
  | 'reframing'
  | 'timeline'
  | 'ai-editor'
  | 'characters'
  | 'exports'
  | 'settings'
  | 'diagnostics';

export const App: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<NavSection>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Global Centralized State (avoiding repeated duplicate polling)
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [projectMedia, setProjectMedia] = useState<MediaAssetItem[]>([]);
  const [analysisAsset, setAnalysisAsset] = useState<MediaAssetItem | null>(null);
  const [mediaStats, setMediaStats] = useState<MediaStorageStats | null>(null);
  const [mediaLoading, setMediaLoading] = useState<boolean>(false);

  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const loadProjectMedia = useCallback(async (pid: string) => {
    if (!pid) return;
    setMediaLoading(true);
    try {
      const [mediaRes, statsRes] = await Promise.all([
        fetchProjectMedia(pid),
        fetchMediaStats(pid).catch(() => null),
      ]);
      setProjectMedia(mediaRes.items);
      setMediaStats(statsRes);
    } catch {
      // ignore
    } finally {
      setMediaLoading(false);
    }
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
      setHealth(healthRes);

      const activeList = projRes.items.filter((p) => p.status === 'active');
      const targetPid = selectedProjectId || (activeList[0]?.id || projRes.items[0]?.id);
      if (targetPid) {
        setSelectedProjectId(targetPid);
        void loadProjectMedia(targetPid);
      }
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Backend unreachable');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId, loadProjectMedia]);

  useEffect(() => {
    if (selectedProjectId) {
      void loadProjectMedia(selectedProjectId);
    }
  }, [selectedProjectId, loadProjectMedia]);

  useEffect(() => {
    void loadGlobalData();
    // Poll jobs & health every 15s gently without high-frequency spam
    const interval = setInterval(() => {
      void fetchJobs().then((r) => setJobs(r.items)).catch(() => {});
      void fetchHealth().then((h) => setHealth(h)).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [loadGlobalData]);

  // Project handlers
  const handleCreateProject = async (name: string, description?: string) => {
    await createProject({ name, description });
    await loadGlobalData();
  };

  const handleArchiveToggle = async (project: ProjectItem) => {
    if (project.status === 'active') {
      await archiveProject(project.id);
    } else {
      await restoreProject(project.id);
    }
    await loadGlobalData();
  };

  const handleDeleteProject = async (projectId: string) => {
    await deleteProject(projectId);
    await loadGlobalData();
  };

  const activeJobsCount = jobs.filter((j) => j.status === 'running').length;

  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden flex bg-canvas text-text-primary">
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
            <div className="p-1.5 rounded-lg bg-indigo-600/15 border border-indigo-500/30 text-indigo-400 shrink-0">
              <Film className="w-5 h-5" />
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

        {/* Navigation Items */}
        <nav className="flex-1 min-h-0 overflow-y-auto p-2.5 space-y-1">
          {/* Main items */}
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

          <SidebarNavButton
            active={activeTab === 'projects'}
            collapsed={sidebarCollapsed}
            icon={<FolderKanban className="w-4 h-4" />}
            label="Projects"
            badge={projects.length ? String(projects.length) : undefined}
            onClick={() => {
              setActiveTab('projects');
              setMobileMenuOpen(false);
            }}
          />

          {/* Upcoming Milestone Stubs with Clear Labels */}
          <div className="pt-3 pb-1">
            {!sidebarCollapsed && (
              <span className="px-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Studio Tools
              </span>
            )}
          </div>

          <SidebarNavButton
            active={activeTab === 'media'}
            collapsed={sidebarCollapsed}
            icon={<Video className="w-4 h-4" />}
            label="Media Library"
            badge={projectMedia.length ? String(projectMedia.length) : undefined}
            onClick={() => {
              setActiveTab('media');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'analysis'}
            collapsed={sidebarCollapsed}
            icon={<Activity className="w-4 h-4 text-sky-400" />}
            label="Video Analysis"
            badge="M5"
            onClick={() => {
              setActiveTab('analysis');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'highlights'}
            collapsed={sidebarCollapsed}
            icon={<Sparkles className="w-4 h-4 text-amber-400" />}
            label="AI Highlights"
            badge="M6"
            onClick={() => {
              setActiveTab('highlights');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'reframing'}
            collapsed={sidebarCollapsed}
            icon={<Camera className="w-4 h-4 text-emerald-400" />}
            label="Smart Reframing"
            badge="M7"
            onClick={() => {
              setActiveTab('reframing');
              setMobileMenuOpen(false);
            }}
          />

          <SidebarNavButton
            active={activeTab === 'timeline'}
            collapsed={sidebarCollapsed}
            icon={<Scissors className="w-4 h-4" />}
            label="Timeline Editor"
            badge="M7"
            disabled
            title="Scheduled for Milestone 7 (Multi-Track NLE)"
          />

          <SidebarNavButton
            active={activeTab === 'ai-editor'}
            collapsed={sidebarCollapsed}
            icon={<Sparkles className="w-4 h-4 text-purple-400" />}
            label="AI Video Editor"
            badge="M8"
            disabled
            title="Scheduled for Milestone 8 (Conversational AI Assistant)"
          />

          <SidebarNavButton
            active={activeTab === 'characters'}
            collapsed={sidebarCollapsed}
            icon={<Users className="w-4 h-4" />}
            label="Character Studio"
            badge="M9"
            disabled
            title="Scheduled for Milestone 9 (Independent 2D Extraction)"
          />

          {/* System & Diagnostics */}
          <div className="pt-3 pb-1">
            {!sidebarCollapsed && (
              <span className="px-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
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
            className="hidden md:flex p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover ml-auto"
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
              className="md:hidden p-1.5 rounded-lg text-text-muted hover:text-text-primary"
              aria-label="Open mobile navigation"
            >
              <Menu className="w-4 h-4" />
            </button>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
              {activeTab === 'dashboard'
                ? 'Dashboard'
                : activeTab === 'projects'
                ? 'Projects Manager'
                : activeTab === 'media'
                ? 'Media Library'
                : activeTab === 'analysis'
                ? 'Video Analysis Workspace'
                : activeTab === 'highlights'
                ? 'AI Highlights & Shorts Studio'
                : activeTab === 'reframing'
                ? 'Smart Reframing & Subject Tracking Studio'
                : activeTab === 'settings'
                ? 'Studio Settings'
                : 'Diagnostics & Health'}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Active Job Activity Pill */}
            {activeJobsCount > 0 && (
              <Badge variant="purple" icon={<Activity className="w-3 h-3 animate-pulse" />}>
                {activeJobsCount} Task Running
              </Badge>
            )}

            {/* Backend Health Badge */}
            <Badge
              variant={health?.status === 'ready' ? 'success' : 'warning'}
              icon={<Shield className="w-3 h-3" />}
            >
              {health?.status ? health.status.toUpperCase() : 'CONNECTING'}
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
              onNavigate={(tab) => setActiveTab(tab)}
              onCreateProject={() => setActiveTab('projects')}
              onOpenProject={(pid) => {
                setSelectedProjectId(pid);
                setActiveTab('media');
              }}
            />
          )}

          {activeTab === 'projects' && (
            <ProjectsManager
              projects={projects}
              loading={loading}
              onRefresh={() => void loadGlobalData()}
              onCreate={handleCreateProject}
              onArchiveToggle={handleArchiveToggle}
              onDelete={handleDeleteProject}
            />
          )}

          {activeTab === 'media' && (
            <MediaLibraryView
              projects={projects}
              currentProjectId={selectedProjectId || (projects[0]?.id || '')}
              onSelectProject={(id) => {
                setSelectedProjectId(id);
                void loadProjectMedia(id);
              }}
              media={projectMedia}
              stats={mediaStats}
              loading={mediaLoading}
              onRefresh={() => void loadProjectMedia(selectedProjectId || (projects[0]?.id || ''))}
              onOpenAnalysis={(asset) => {
                setAnalysisAsset(asset);
                setActiveTab('analysis');
              }}
            />
          )}

          {activeTab === 'analysis' && (
            analysisAsset ? (
              <AnalysisWorkspace
                projectId={selectedProjectId || (projects[0]?.id || '')}
                mediaAsset={analysisAsset}
                onBack={() => setActiveTab('media')}
                onNavigateToHighlights={() => setActiveTab('highlights')}
              />
            ) : (
              <div className="p-8 text-center text-text-muted">
                <p>Select a video asset from the Media Library to open the Analysis Workspace.</p>
                <Button className="mt-4" size="sm" onClick={() => setActiveTab('media')}>
                  Go to Media Library
                </Button>
              </div>
            )
          )}

          {activeTab === 'highlights' && (
            <HighlightsWorkspace
              projectId={selectedProjectId || (projects[0]?.id || '')}
              mediaAssets={projectMedia}
              preselectedAssetId={analysisAsset?.id}
              onNavigateToAnalysis={(aid) => {
                const found = projectMedia.find((m) => m.id === aid);
                if (found) setAnalysisAsset(found);
                setActiveTab('analysis');
              }}
            />
          )}

          {activeTab === 'reframing' && (
            (analysisAsset || projectMedia[0]) ? (
              <ReframingWorkspace
                projectId={selectedProjectId || (projects[0]?.id || '')}
                mediaAsset={analysisAsset || projectMedia[0]}
                onBack={() => setActiveTab('highlights')}
              />
            ) : (
              <div className="p-8 text-center text-text-muted">
                <p>Please import or select a video asset to open the Smart Reframing Studio.</p>
                <Button className="mt-4" size="sm" onClick={() => setActiveTab('media')}>
                  Go to Media Library
                </Button>
              </div>
            )
          )}

          {activeTab === 'settings' && <SettingsManager />}

          {activeTab === 'diagnostics' && <FoundationOverview />}
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
      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition select-none ${
        disabled
          ? 'opacity-40 cursor-not-allowed text-text-muted'
          : active
          ? 'bg-brand/15 text-brand border border-brand/30 shadow-xs'
          : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
      } ${collapsed ? 'justify-center px-0' : ''}`}
    >
      <span className="shrink-0">{icon}</span>
      {!collapsed && <span className="truncate flex-1 text-left">{label}</span>}
      {!collapsed && badge && (
        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface border border-border text-text-muted shrink-0">
          {badge}
        </span>
      )}
    </button>
  );
};

export default App;
