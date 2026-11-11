import React, { useMemo, useState } from 'react';
import {
  Archive,
  FolderOpen,
  Grid,
  List,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { ConfirmDialog, Dialog } from '../../components/ui/Dialog';
import { Input, SearchInput } from '../../components/ui/Input';
import { EmptyState, Skeleton } from '../../components/ui/States';
import { ProjectItem } from '../../types/projects';

export interface ProjectsManagerProps {
  projects: ProjectItem[];
  loading: boolean;
  onRefresh: () => void;
  onCreate: (name: string, description?: string) => Promise<void>;
  onArchiveToggle: (project: ProjectItem) => Promise<void>;
  onDelete: (projectId: string) => Promise<void>;
}

export const ProjectsManager: React.FC<ProjectsManagerProps> = ({
  projects,
  loading,
  onRefresh,
  onCreate,
  onArchiveToggle,
  onDelete,
}) => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('active');
  const [sortBy, setSortBy] = useState<'updated' | 'created' | 'name'>('updated');

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);

  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Filtered & Sorted Projects
  const filteredProjects = useMemo(() => {
    return projects
      .filter((p) => {
        if (statusFilter !== 'all' && p.status !== statusFilter) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          return (
            p.name.toLowerCase().includes(q) ||
            (p.description && p.description.toLowerCase().includes(q))
          );
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'updated') {
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        }
        if (sortBy === 'created') {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        }
        return a.name.localeCompare(b.name);
      });
  }, [projects, statusFilter, searchQuery, sortBy]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim()) return;
    setIsSubmittingCreate(true);
    try {
      await onCreate(createName.trim(), createDesc.trim() || undefined);
      setCreateName('');
      setCreateDesc('');
      setCreateDialogOpen(false);
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await onDelete(deleteTargetId);
      setDeleteTargetId(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Projects</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Manage your local video editing workspaces and projects.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button leftIcon={<Plus className="w-4 h-4" />} onClick={() => setCreateDialogOpen(true)}>
            New Project
          </Button>
          <Button variant="outline" size="md" onClick={onRefresh} disabled={loading} title="Refresh">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Search, Filters, and Layout Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <SearchInput
            placeholder="Search projects by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-3 py-2 text-xs bg-canvas-subtle border border-border rounded-lg text-text-primary focus:outline-none focus:border-brand"
          >
            <option value="active">Active Projects</option>
            <option value="archived">Archived</option>
            <option value="all">All Projects</option>
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 text-xs bg-canvas-subtle border border-border rounded-lg text-text-primary focus:outline-none focus:border-brand"
          >
            <option value="updated">Recently Updated</option>
            <option value="created">Date Created</option>
            <option value="name">Name (A-Z)</option>
          </select>

          {/* View Toggle */}
          <div className="border border-border rounded-lg p-0.5 flex bg-canvas-subtle">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md ${
                viewMode === 'grid'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="Grid View"
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md ${
                viewMode === 'list'
                  ? 'bg-surface text-text-primary shadow-xs'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="List View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Projects Display */}
      {loading && projects.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : filteredProjects.length === 0 ? (
        <Card>
          <EmptyState
            icon={<FolderOpen className="w-8 h-8 text-text-muted" />}
            title="No projects match criteria"
            description="Try adjusting your search query or filter settings."
            actionText={searchQuery ? 'Clear Search' : 'New Project'}
            onAction={searchQuery ? () => setSearchQuery('') : () => setCreateDialogOpen(true)}
          />
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((proj) => (
            <Card key={proj.id} className="flex flex-col justify-between space-y-4">
              <div className="space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-text-primary truncate" title={proj.name}>
                    {proj.name}
                  </h3>
                  <Badge variant={proj.status === 'active' ? 'success' : 'default'}>
                    {proj.status}
                  </Badge>
                </div>
                {proj.description && (
                  <p className="text-xs text-text-secondary line-clamp-2">{proj.description}</p>
                )}
              </div>

              <div className="space-y-3 pt-3 border-t border-border">
                <div className="text-[11px] text-text-muted font-mono flex items-center justify-between">
                  <span>ID: {proj.id}</span>
                  <span>{new Date(proj.updated_at).toLocaleDateString()}</span>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onArchiveToggle(proj)}
                    className="flex-1"
                  >
                    <Archive className="w-3.5 h-3.5 text-text-muted" />
                    {proj.status === 'active' ? 'Archive' : 'Restore'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteTargetId(proj.id)}
                    className="text-red-400 hover:text-red-300"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        /* List View */
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-canvas-subtle text-text-muted border-b border-border">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Storage Subdir</th>
                  <th className="px-4 py-3 font-medium">Last Updated</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-text-primary">
                {filteredProjects.map((proj) => (
                  <tr key={proj.id} className="hover:bg-canvas-subtle transition">
                    <td className="px-4 py-3">
                      <span className="font-semibold block">{proj.name}</span>
                      {proj.description && (
                        <span className="text-text-muted text-[11px] block">{proj.description}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={proj.status === 'active' ? 'success' : 'default'}>
                        {proj.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-text-muted">{proj.storage_subdir}</td>
                    <td className="px-4 py-3 text-text-muted">
                      {new Date(proj.updated_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onArchiveToggle(proj)}
                        title={proj.status === 'active' ? 'Archive' : 'Restore'}
                      >
                        <Archive className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTargetId(proj.id)}
                        className="text-red-400 hover:text-red-300"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create Project Modal */}
      <Dialog
        isOpen={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        title="Create New Project"
        description="Initialize a dedicated SQLite-managed workspace."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCreateDialogOpen(false)}
              disabled={isSubmittingCreate}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleCreateSubmit}
              isLoading={isSubmittingCreate}
              disabled={!createName.trim()}
            >
              Create Project
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreateSubmit} className="space-y-3">
          <Input
            label="Project Name"
            placeholder="e.g. Travel Vlog Episode 1"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            required
            autoFocus
          />
          <Input
            label="Description (Optional)"
            placeholder="Brief project summary or editing goals"
            value={createDesc}
            onChange={(e) => setCreateDesc(e.target.value)}
          />
        </form>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!deleteTargetId}
        onClose={() => setDeleteTargetId(null)}
        onConfirm={handleConfirmDelete}
        title="Delete Project Permanently?"
        message="This action removes the project and its metadata permanently. Note: external source media files are preserved."
        confirmText="Delete Project"
        isLoading={isDeleting}
      />
    </div>
  );
};
