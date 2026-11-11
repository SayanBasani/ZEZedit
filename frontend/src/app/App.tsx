import React, { useState } from 'react';
import { Film, FolderKanban, Menu, Shield, X } from 'lucide-react';
import { FoundationOverview } from '../features/dashboard/FoundationOverview';
import { ProjectsView } from '../features/projects/ProjectsView';

type NavTab = 'health' | 'projects';

export const App: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<NavTab>('health');

  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden flex bg-canvas text-slate-100">
      {/* Stationary Left Sidebar */}
      <aside
        className={`${
          mobileMenuOpen ? 'fixed inset-y-0 left-0 z-40 flex' : 'hidden md:flex'
        } w-64 h-full shrink-0 flex-col bg-surface border-r border-border overflow-hidden`}
      >
        <div className="px-4 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
              <Film className="w-5 h-5" />
            </div>
            <div>
              <span className="font-semibold text-sm text-white tracking-tight">ZezEdit 2.0</span>
              <span className="block text-[10px] text-slate-400 font-mono">Local-First Studio</span>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="md:hidden p-1 text-slate-400 hover:text-white"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="flex-1 min-h-0 overflow-y-auto p-3 space-y-1">
          <button
            onClick={() => {
              setActiveTab('health');
              setMobileMenuOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition ${
              activeTab === 'health'
                ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Shield className="w-4 h-4 text-indigo-400" />
            System Health &amp; Diagnostics
          </button>

          <button
            onClick={() => {
              setActiveTab('projects');
              setMobileMenuOpen(false);
            }}
            className={`w-full px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition ${
              activeTab === 'projects'
                ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <FolderKanban className="w-4 h-4 text-sky-400" />
            Projects (Milestone 2)
          </button>

          <div className="pt-4 px-3 text-[11px] text-slate-500 leading-relaxed">
            Upcoming modules (Media Importer, Timeline, AI Editor, Reframing, Characters) arrive in Milestones 3–10.
          </div>
        </nav>

        <div className="px-4 py-3 border-t border-border text-[11px] text-slate-500 shrink-0 font-mono">
          CPU-First · SQLite WAL
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
        <header className="h-12 shrink-0 border-b border-border bg-surface/60 px-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 rounded-lg text-slate-300 hover:bg-slate-800"
              aria-label="Open navigation"
            >
              <Menu className="w-4 h-4" />
            </button>
            <span className="text-xs font-medium text-slate-300">
              {activeTab === 'health' ? 'System Health & Diagnostics' : 'Project Management Workspace'}
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            API: /api/v1
          </span>
        </header>

        <main className="flex-1 min-h-0 min-w-0 overflow-y-auto overscroll-contain">
          {activeTab === 'health' ? <FoundationOverview /> : <ProjectsView />}
        </main>
      </div>
    </div>
  );
};

export default App;
