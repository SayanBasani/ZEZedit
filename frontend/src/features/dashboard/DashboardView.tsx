import React from 'react';
import {
  Activity,
  Film,
  FolderOpen,
  FolderPlus,
  Plus,
  Scissors,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState, Skeleton } from '../../components/ui/States';
import { JobItem, ProjectItem } from '../../types/projects';

export interface DashboardViewProps {
  projects: ProjectItem[];
  jobs: JobItem[];
  loading: boolean;
  onNavigate: (tab: any) => void;
  onCreateProject: () => void;
  onOpenProject: (projectId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  projects,
  jobs,
  loading,
  onNavigate,
  onCreateProject,
  onOpenProject,
}) => {
  const activeProjects = projects.filter((p) => p.status === 'active');
  const recentProjects = [...activeProjects]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 4);

  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'queued');
  const recentJobs = jobs.slice(0, 5);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Hero Welcome / Studio Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-950/40 via-surface to-surface border border-border p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <div className="flex items-center gap-2">
            <Badge variant="purple" icon={<Sparkles className="w-3 h-3 text-indigo-400" />}>
              Studio Workspace
            </Badge>
            <span className="text-[11px] font-mono text-text-muted">v2.0.0-alpha.1</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-text-primary tracking-tight">
            Local-First AI Video Editor
          </h1>
          <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
            CPU-first video processing, context-aware vertical reframing, and multi-track timeline editing right on your workstation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <Button leftIcon={<Plus className="w-4 h-4" />} onClick={onCreateProject}>
            New Project
          </Button>
          <Button variant="outline" onClick={() => onNavigate('projects')}>
            All Projects
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="space-y-1">
          <span className="text-xs text-text-muted font-medium">Active Projects</span>
          <p className="text-2xl font-bold text-text-primary">
            {loading ? <Skeleton className="h-7 w-12" /> : activeProjects.length}
          </p>
        </Card>

        <Card className="space-y-1">
          <span className="text-xs text-text-muted font-medium">Total Projects</span>
          <p className="text-2xl font-bold text-text-primary">
            {loading ? <Skeleton className="h-7 w-12" /> : projects.length}
          </p>
        </Card>

        <Card className="space-y-1">
          <span className="text-xs text-text-muted font-medium">Active Jobs</span>
          <p className="text-2xl font-bold text-indigo-400">
            {loading ? <Skeleton className="h-7 w-12" /> : activeJobs.length}
          </p>
        </Card>

        <Card className="space-y-1">
          <span className="text-xs text-text-muted font-medium">Total Background Tasks</span>
          <p className="text-2xl font-bold text-text-primary">
            {loading ? <Skeleton className="h-7 w-12" /> : jobs.length}
          </p>
        </Card>
      </div>

      {/* Main Grid: Recent Projects + Quick Actions & Processing Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Projects */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-indigo-400" />
              Recent Projects
            </h2>
            <button
              onClick={() => onNavigate('projects')}
              className="text-xs text-brand hover:underline font-medium"
            >
              View all
            </button>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-28 w-full" />
            </div>
          ) : recentProjects.length === 0 ? (
            <Card>
              <EmptyState
                icon={<FolderPlus className="w-8 h-8 text-text-muted" />}
                title="No projects yet"
                description="Create your first video project to begin editing."
                actionText="Create Project"
                onAction={onCreateProject}
              />
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {recentProjects.map((p) => (
                <Card
                  key={p.id}
                  interactive
                  onClick={() => onOpenProject(p.id)}
                  className="flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold text-text-primary truncate" title={p.name}>
                        {p.name}
                      </h3>
                      <Badge variant="success">Active</Badge>
                    </div>
                    {p.description && (
                      <p className="text-xs text-text-secondary line-clamp-2 mt-1">
                        {p.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-text-muted font-mono pt-2 border-t border-border/50">
                    <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                    <span>storage/media/{p.storage_subdir}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Studio Quick Actions */}
          <div className="pt-2 space-y-3">
            <h2 className="text-sm font-semibold text-text-primary">Studio Workspaces</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div
                onClick={() => onNavigate('projects')}
                className="p-3.5 rounded-xl bg-surface border border-border hover:border-brand cursor-pointer transition flex flex-col items-center text-center space-y-2"
              >
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <Film className="w-4 h-4" />
                </div>
                <span className="text-xs font-medium text-text-primary">Projects</span>
                <span className="text-[10px] text-emerald-400 font-mono">Ready</span>
              </div>

              <div
                onClick={() => onNavigate('settings')}
                className="p-3.5 rounded-xl bg-surface border border-border hover:border-brand cursor-pointer transition flex flex-col items-center text-center space-y-2"
              >
                <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                  <Activity className="w-4 h-4" />
                </div>
                <span className="text-xs font-medium text-text-primary">Settings</span>
                <span className="text-[10px] text-emerald-400 font-mono">Ready</span>
              </div>

              <div
                onClick={() => onNavigate('timeline')}
                className="p-3.5 rounded-xl bg-surface border border-border opacity-75 hover:opacity-100 cursor-pointer transition flex flex-col items-center text-center space-y-2"
              >
                <div className="p-2 rounded-lg bg-slate-500/10 text-slate-400">
                  <Scissors className="w-4 h-4" />
                </div>
                <span className="text-xs font-medium text-text-primary">Timeline</span>
                <span className="text-[10px] text-amber-400 font-mono">Milestone 7</span>
              </div>

              <div
                onClick={() => onNavigate('ai-editor')}
                className="p-3.5 rounded-xl bg-surface border border-border opacity-75 hover:opacity-100 cursor-pointer transition flex flex-col items-center text-center space-y-2"
              >
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <span className="text-xs font-medium text-text-primary">AI Editor</span>
                <span className="text-[10px] text-amber-400 font-mono">Milestone 8</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Background Processing Status & Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              Background Tasks
            </h2>
            <span className="text-xs text-text-muted font-mono">{activeJobs.length} running</span>
          </div>

          <Card className="space-y-3">
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : recentJobs.length === 0 ? (
              <p className="text-xs text-text-muted py-6 text-center">No recent background jobs.</p>
            ) : (
              <div className="space-y-2.5">
                {recentJobs.map((j) => (
                  <div
                    key={j.id}
                    className="p-2.5 rounded-lg bg-canvas-subtle border border-border/60 flex items-center justify-between gap-3"
                  >
                    <div className="space-y-0.5 truncate">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-text-primary truncate">
                          {j.job_type}
                        </span>
                      </div>
                      <span className="text-[10px] text-text-muted font-mono block">
                        ID: {j.id} • {j.current_stage || j.status}
                      </span>
                    </div>

                    <Badge
                      variant={
                        j.status === 'completed'
                          ? 'success'
                          : j.status === 'running'
                          ? 'info'
                          : j.status === 'failed' || j.status === 'interrupted'
                          ? 'danger'
                          : 'default'
                      }
                    >
                      {j.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
