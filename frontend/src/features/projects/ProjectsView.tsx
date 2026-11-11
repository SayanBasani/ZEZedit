import React, { useEffect, useState } from 'react';
import { Archive, FolderPlus, RefreshCw, Trash2 } from 'lucide-react';
import {
  archiveProject,
  createProject,
  deleteProject,
  fetchProjects,
  restoreProject,
} from '../../services/apiClient';
import { ProjectItem } from '../../types/projects';

export const ProjectsView: React.FC = () => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProjects(showArchived);
      setProjects(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProjects();
  }, [showArchived]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsSubmitting(true);
    try {
      await createProject({ name: newName.trim(), description: newDesc.trim() || undefined });
      setNewName('');
      setNewDesc('');
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchiveToggle = async (project: ProjectItem) => {
    try {
      if (project.status === 'active') {
        await archiveProject(project.id);
      } else {
        await restoreProject(project.id);
      }
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleDelete = async (projectId: string) => {
    if (!window.confirm('Delete this project permanently? This cannot be undone.')) return;
    try {
      await deleteProject(projectId);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Project Management</h1>
          <p className="text-xs text-slate-400 mt-1">
            Persistent SQLite-backed projects with activity tracking and archiving.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-300 flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
              className="rounded bg-slate-800 border-border text-indigo-600 focus:ring-0"
            />
            Show Archived
          </label>
          <button
            onClick={() => void loadProjects()}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-border"
            title="Refresh projects"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800/50 rounded-xl text-red-200 text-xs">
          {error}
        </div>
      )}

      {/* Create Project Card */}
      <form onSubmit={handleCreate} className="p-4 bg-surface border border-border rounded-xl space-y-3">
        <span className="text-xs font-semibold text-slate-200 flex items-center gap-2">
          <FolderPlus className="w-4 h-4 text-indigo-400" />
          Create New Project
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            type="text"
            placeholder="Project title (e.g. Vacation Highlights)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="px-3 py-2 text-xs bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            required
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            className="px-3 py-2 text-xs bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 sm:col-span-1"
          />
          <button
            type="submit"
            disabled={isSubmitting || !newName.trim()}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition"
          >
            {isSubmitting ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>

      {/* Projects List */}
      <div className="space-y-3">
        {loading && projects.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No projects found. Create your first project above.
          </div>
        ) : (
          projects.map((proj) => (
            <div
              key={proj.id}
              className="p-4 bg-surface border border-border rounded-xl flex items-center justify-between gap-4 hover:border-slate-700 transition"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-white">{proj.name}</h3>
                  <span
                    className={`px-2 py-0.2 rounded-full text-[10px] font-mono ${
                      proj.status === 'active'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {proj.status}
                  </span>
                </div>
                {proj.description && (
                  <p className="text-xs text-slate-400">{proj.description}</p>
                )}
                <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
                  <span>ID: {proj.id}</span>
                  <span>•</span>
                  <span>Created: {new Date(proj.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>Folder: storage/media/{proj.storage_subdir}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleArchiveToggle(proj)}
                  className="px-2.5 py-1 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-border transition flex items-center gap-1.5"
                  title={proj.status === 'active' ? 'Archive' : 'Restore'}
                >
                  <Archive className="w-3.5 h-3.5" />
                  {proj.status === 'active' ? 'Archive' : 'Restore'}
                </button>
                <button
                  onClick={() => handleDelete(proj.id)}
                  className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-800 transition"
                  title="Delete project"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
