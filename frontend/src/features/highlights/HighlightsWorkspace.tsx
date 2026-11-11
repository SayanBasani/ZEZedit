import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowUpDown,
  Check,
  CheckCircle,
  Clock,
  Eye,
  Flame,
  Layers,
  RefreshCw,
  RotateCcw,
  Search,
  Sliders,
  Sparkles,
  Video,
  X,
  XCircle,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  approveCandidate,
  bulkReviewCandidates,
  discoverHighlights,
  fetchCandidateAlternatives,
  fetchProjectHighlights,
  queueCandidateRender,
  rejectCandidate,
  restoreCandidate,
  updateCandidate,
} from '../../services/apiClient';
import { CandidateItem, HighlightsOverview, ReviewStatus } from '../../types/highlights';
import { MediaAssetItem } from '../../types/projects';

interface HighlightsWorkspaceProps {
  projectId: string;
  mediaAssets?: MediaAssetItem[];
  preselectedAssetId?: string;
  onNavigateToAnalysis?: (assetId: string) => void;
}

export const HighlightsWorkspace: React.FC<HighlightsWorkspaceProps> = ({
  projectId,
  mediaAssets = [],
  preselectedAssetId,
  onNavigateToAnalysis: _onNavigateToAnalysis,
}) => {
  // Selection and filter state
  const [selectedAssetId, setSelectedAssetId] = useState<string>(preselectedAssetId || 'all');
  const [reviewFilter, setReviewFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'score' | 'duration' | 'start'>('score');

  // Highlights state
  const [overview, setOverview] = useState<HighlightsOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Selected candidate for details modal/drawer
  const [inspectCandidate, setInspectCandidate] = useState<CandidateItem | null>(null);
  const [alternatives, setAlternatives] = useState<CandidateItem[]>([]);
  const [_loadingAlternatives, setLoadingAlternatives] = useState<boolean>(false);

  // Boundary editing state inside inspector
  const [editStartTime, setEditStartTime] = useState<number>(0);
  const [editEndTime, setEditEndTime] = useState<number>(0);
  const [editTitle, setEditTitle] = useState<string>('');
  const [boundaryDirty, setBoundaryDirty] = useState<boolean>(false);

  // Multi-select for bulk actions
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Discovery options modal state
  const [showDiscoveryModal, setShowDiscoveryModal] = useState<boolean>(false);
  const [discTargetCount, setDiscTargetCount] = useState<number>(10);
  const [discMinDuration, setDiscMinDuration] = useState<number>(12);
  const [discMaxDuration, setDiscMaxDuration] = useState<number>(60);
  const [discUseAI, setDiscUseAI] = useState<boolean>(true);

  // Load highlights overview
  const loadHighlights = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectHighlights(
        projectId,
        reviewFilter === 'all' ? undefined : reviewFilter,
        categoryFilter === 'all' ? undefined : categoryFilter,
        searchQuery ? searchQuery : undefined
      );
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load highlights.');
    } finally {
      setLoading(false);
    }
  }, [projectId, reviewFilter, categoryFilter, searchQuery]);

  useEffect(() => {
    void loadHighlights();
  }, [loadHighlights]);

  // Open candidate inspector
  const handleInspect = async (candidate: CandidateItem) => {
    setInspectCandidate(candidate);
    setEditStartTime(candidate.start_time);
    setEditEndTime(candidate.end_time);
    setEditTitle(candidate.title || candidate.suggested_title);
    setBoundaryDirty(false);

    if (candidate.overlap_group_id) {
      setLoadingAlternatives(true);
      try {
        const alts = await fetchCandidateAlternatives(projectId, candidate.id);
        setAlternatives(alts);
      } catch {
        setAlternatives([]);
      } finally {
        setLoadingAlternatives(false);
      }
    } else {
      setAlternatives([]);
    }
  };

  // Run Highlight Discovery
  const handleRunDiscovery = async (assetIdToRun: string) => {
    if (!projectId || !assetIdToRun || assetIdToRun === 'all') return;
    setDiscovering(true);
    setError(null);
    try {
      await discoverHighlights(projectId, assetIdToRun, {
        target_clip_count: discTargetCount,
        min_duration: discMinDuration,
        max_duration: discMaxDuration,
        use_ai_explanations: discUseAI,
        run_synchronously: true,
      });
      setShowDiscoveryModal(false);
      await loadHighlights();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery run failed.');
    } finally {
      setDiscovering(false);
    }
  };

  // Status Action Handlers
  const handleApprove = async (candidateId: string) => {
    setActionInProgress(candidateId);
    try {
      const updated = await approveCandidate(projectId, candidateId);
      updateLocalCandidate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve candidate.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (candidateId: string, reason?: string) => {
    setActionInProgress(candidateId);
    try {
      const updated = await rejectCandidate(projectId, candidateId, reason || 'User rejected');
      updateLocalCandidate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject candidate.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleRestore = async (candidateId: string) => {
    setActionInProgress(candidateId);
    try {
      const updated = await restoreCandidate(projectId, candidateId);
      updateLocalCandidate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore candidate.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleToggleQueueRender = async (candidate: CandidateItem) => {
    setActionInProgress(candidate.id);
    try {
      const updated = await queueCandidateRender(projectId, candidate.id, !candidate.queued_for_render);
      updateLocalCandidate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update render queue.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleSaveBoundaries = async () => {
    if (!inspectCandidate) return;
    if (editStartTime >= editEndTime) {
      setError('Start time must precede end time.');
      return;
    }
    setActionInProgress(inspectCandidate.id);
    try {
      const updated = await updateCandidate(projectId, inspectCandidate.id, {
        start_time: editStartTime,
        end_time: editEndTime,
        title: editTitle,
      });
      setInspectCandidate(updated);
      setBoundaryDirty(false);
      updateLocalCandidate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update boundaries.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleBulkAction = async (action: 'approve' | 'reject' | 'restore') => {
    if (selectedIds.size === 0) return;
    setActionInProgress('bulk');
    try {
      await bulkReviewCandidates(projectId, Array.from(selectedIds), action);
      setSelectedIds(new Set());
      await loadHighlights();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} selected candidates.`);
    } finally {
      setActionInProgress(null);
    }
  };

  const updateLocalCandidate = (updated: CandidateItem) => {
    setOverview((prev) => {
      if (!prev) return null;
      const newCandidates = prev.candidates.map((c) => (c.id === updated.id ? updated : c));
      return { ...prev, candidates: newCandidates };
    });
    if (inspectCandidate && inspectCandidate.id === updated.id) {
      setInspectCandidate(updated);
    }
  };

  // Filtered and sorted candidate list
  const filteredCandidates = useMemo(() => {
    if (!overview) return [];
    let list = [...overview.candidates];

    if (selectedAssetId !== 'all') {
      list = list.filter((c) => c.media_asset_id === selectedAssetId);
    }

    if (reviewFilter !== 'all') {
      list = list.filter((c) => c.review_status === reviewFilter);
    }

    if (categoryFilter !== 'all') {
      list = list.filter((c) => c.category === categoryFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (c) =>
          c.title?.toLowerCase().includes(q) ||
          c.suggested_title?.toLowerCase().includes(q) ||
          c.description?.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      if (sortBy === 'score') return b.quality_score - a.quality_score;
      if (sortBy === 'duration') return b.duration - a.duration;
      return a.start_time - b.start_time;
    });

    return list;
  }, [overview, selectedAssetId, reviewFilter, categoryFilter, searchQuery, sortBy]);

  const toggleSelectCandidate = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredCandidates.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredCandidates.map((c) => c.id)));
    }
  };

  const formatTimestamp = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (score >= 50) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
  };

  const getStatusBadgeVariant = (status: ReviewStatus) => {
    switch (status) {
      case 'recommended':
        return 'success';
      case 'approved':
        return 'purple';
      case 'needs_review':
        return 'warning';
      case 'rejected':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Top Controls Header */}
      <div className="border-b border-border bg-surface px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h1 className="text-lg font-semibold text-text-primary">Shorts Highlights Studio</h1>
            <Badge variant="purple">M6 Engine</Badge>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Contextual clip discovery, multi-signal scoring, and candidate review for high-impact Shorts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Media Asset Picker */}
          <select
            className="text-xs bg-surface-card border border-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-brand"
            value={selectedAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value)}
          >
            <option value="all">All Media Assets</option>
            {mediaAssets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.original_filename} ({asset.duration_seconds ? `${Math.round(asset.duration_seconds)}s` : 'Unknown'})
              </option>
            ))}
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={loadHighlights}
            disabled={loading}
            title="Refresh candidate list"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowDiscoveryModal(true)}
            disabled={discovering || mediaAssets.length === 0}
            title="Run AI Highlight Discovery"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5" />
            Discover Highlights
          </Button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-6 border-b border-border bg-surface/30">
        <div className="bg-surface border border-border rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">Total Found</span>
          <span className="text-2xl font-bold text-text-primary mt-1">
            {overview?.total_candidates ?? 0}
          </span>
        </div>

        <div className="bg-surface border border-emerald-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Recommended
          </span>
          <span className="text-2xl font-bold text-emerald-400 mt-1">
            {overview?.recommended_count ?? 0}
          </span>
        </div>

        <div className="bg-surface border border-amber-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-amber-400 uppercase tracking-wider flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Needs Review
          </span>
          <span className="text-2xl font-bold text-amber-400 mt-1">
            {overview?.needs_review_count ?? 0}
          </span>
        </div>

        <div className="bg-surface border border-purple-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-purple-400 uppercase tracking-wider flex items-center gap-1">
            <Flame className="w-3 h-3" /> Approved
          </span>
          <span className="text-2xl font-bold text-purple-400 mt-1">
            {overview?.approved_count ?? 0}
          </span>
        </div>

        <div className="bg-surface border border-rose-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider flex items-center gap-1">
            <XCircle className="w-3 h-3" /> Rejected
          </span>
          <span className="text-2xl font-bold text-rose-400 mt-1">
            {overview?.rejected_count ?? 0}
          </span>
        </div>
      </div>

      {/* Toolbar: Search, Filters, Bulk Actions */}
      <div className="px-6 py-3 border-b border-border bg-surface-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          {/* Search box */}
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search highlights by title or text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 bg-surface border border-border rounded-lg text-text-primary focus:outline-none focus:border-brand"
            />
          </div>

          {/* Status filter tabs */}
          <div className="flex items-center bg-surface border border-border rounded-lg p-0.5">
            {['all', 'recommended', 'needs_review', 'approved', 'rejected'].map((st) => (
              <button
                key={st}
                onClick={() => setReviewFilter(st)}
                className={`text-[11px] font-medium px-2.5 py-1 rounded capitalize transition ${
                  reviewFilter === st
                    ? 'bg-brand text-white shadow-xs'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="text-xs bg-surface border border-border rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none"
          >
            <option value="all">All Categories</option>
            <option value="dialogue">Dialogue</option>
            <option value="insightful">Insightful</option>
            <option value="humor">Humor</option>
            <option value="dramatic">Dramatic</option>
            <option value="visual">Visual</option>
            <option value="general">General</option>
          </select>
        </div>

        {/* Right side: Sort & Bulk operations */}
        <div className="flex items-center gap-3">
          {filteredCandidates.length > 0 && (
            <button
              onClick={toggleSelectAll}
              className="text-xs text-text-muted hover:text-text-primary px-2.5 py-1 rounded bg-surface border border-border"
            >
              {selectedIds.size === filteredCandidates.length ? 'Deselect All' : 'Select All'}
            </button>
          )}

          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <ArrowUpDown className="w-3.5 h-3.5" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="text-xs bg-surface border border-border rounded-lg px-2 py-1 text-text-primary"
            >
              <option value="score">Sort: Quality Score</option>
              <option value="duration">Sort: Duration</option>
              <option value="start">Sort: Start Time</option>
            </select>
          </div>

          {/* Bulk Action Controls */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-1.5 bg-brand/10 border border-brand/30 rounded-lg px-2.5 py-1">
              <span className="text-xs font-semibold text-brand mr-1">
                {selectedIds.size} Selected
              </span>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[11px] px-2"
                onClick={() => handleBulkAction('approve')}
              >
                Approve
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[11px] px-2 text-rose-400 hover:text-rose-300"
                onClick={() => handleBulkAction('reject')}
              >
                Reject
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[11px] px-2"
                onClick={() => handleBulkAction('restore')}
              >
                Restore
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="mx-6 mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Workspace Body: Candidate Cards Grid */}
      <div className="flex-1 overflow-y-auto p-6 min-h-0">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="h-56 rounded-xl border border-border bg-surface animate-pulse p-4"
              />
            ))}
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-text-muted">
            <Sparkles className="w-12 h-12 text-text-muted mb-3 opacity-30" />
            <h3 className="text-sm font-semibold text-text-primary">No highlight candidates found</h3>
            <p className="text-xs max-w-sm mt-1">
              Run highlight discovery on an analyzed video asset or adjust your filters above.
            </p>
            {mediaAssets.length > 0 && (
              <Button
                size="sm"
                variant="primary"
                className="mt-4"
                onClick={() => setShowDiscoveryModal(true)}
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Run Discovery Now
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCandidates.map((c) => {
              const isSelected = selectedIds.has(c.id);
              const scoreClass = getScoreColor(c.quality_score);

              return (
                <div
                  key={c.id}
                  className={`group relative rounded-xl border transition-all flex flex-col bg-surface hover:shadow-lg ${
                    c.queued_for_render
                      ? 'border-brand/60 ring-1 ring-brand/30'
                      : isSelected
                      ? 'border-brand/80'
                      : 'border-border hover:border-border-hover'
                  }`}
                >
                  {/* Card Header */}
                  <div className="p-4 border-b border-border/50 flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectCandidate(c.id)}
                        className="rounded border-border text-brand focus:ring-0 cursor-pointer"
                      />
                      <Badge variant={getStatusBadgeVariant(c.review_status)}>
                        {c.review_status.replace('_', ' ')}
                      </Badge>
                      {c.is_user_modified && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
                          Trimmed
                        </span>
                      )}
                      {c.overlap_group_id && (
                        <span
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center gap-1"
                          title="Has alternative cuts"
                        >
                          <Layers className="w-2.5 h-2.5" /> Alt Cuts
                        </span>
                      )}
                    </div>

                    {/* Quality score badge */}
                    <div
                      className={`px-2 py-0.5 rounded-full text-xs font-bold border ${scoreClass}`}
                      title={`Scoring Version: ${c.scoring_version}`}
                    >
                      {Math.round(c.quality_score)}
                    </div>
                  </div>

                  {/* Card Body */}
                  <div className="p-4 flex-1 flex flex-col gap-2">
                    <h3 className="text-sm font-semibold text-text-primary line-clamp-2 leading-snug">
                      {c.title || c.suggested_title}
                    </h3>

                    {/* Timestamp & Category details */}
                    <div className="flex items-center gap-2 text-xs text-text-muted mt-0.5">
                      <span className="flex items-center gap-1 font-mono text-[11px] bg-surface-card px-2 py-0.5 rounded border border-border">
                        <Clock className="w-3 h-3 text-text-muted" />
                        {formatTimestamp(c.start_time)} - {formatTimestamp(c.end_time)}
                      </span>
                      <span className="font-mono text-[11px] font-medium text-text-secondary">
                        {c.duration.toFixed(1)}s
                      </span>
                      <span className="capitalize px-1.5 py-0.5 rounded bg-surface-card border border-border text-[10px] text-text-muted">
                        {c.category}
                      </span>
                    </div>

                    {/* Excerpt / AI Hook Preview */}
                    <p className="text-xs text-text-secondary line-clamp-3 mt-1.5 italic bg-surface-card/60 p-2.5 rounded-lg border border-border/40">
                      "{c.ai_explanation?.hook || c.description || 'Speech highlight dialogue'}"
                    </p>

                    {/* Missing evidence or warnings pills */}
                    {c.warnings && c.warnings.length > 0 && (
                      <div className="flex items-center gap-1 text-[11px] text-amber-400 mt-1">
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        <span className="truncate">{c.warnings[0]}</span>
                      </div>
                    )}
                  </div>

                  {/* Card Footer / Quick Review Buttons */}
                  <div className="p-3 bg-surface-card/70 border-t border-border flex items-center justify-between gap-1.5">
                    <div className="flex items-center gap-1">
                      {c.review_status !== 'approved' && (
                        <button
                          onClick={() => handleApprove(c.id)}
                          disabled={actionInProgress === c.id}
                          className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition"
                          title="Approve candidate"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}

                      {c.review_status !== 'rejected' && (
                        <button
                          onClick={() => handleReject(c.id)}
                          disabled={actionInProgress === c.id}
                          className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 transition"
                          title="Reject candidate"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}

                      {(c.review_status === 'approved' || c.review_status === 'rejected') && (
                        <button
                          onClick={() => handleRestore(c.id)}
                          disabled={actionInProgress === c.id}
                          className="p-1.5 rounded-lg text-amber-400 hover:bg-amber-500/10 transition"
                          title="Restore to recommended"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Render Queue Switch */}
                      <button
                        onClick={() => handleToggleQueueRender(c)}
                        disabled={actionInProgress === c.id}
                        className={`text-[11px] font-medium px-2 py-1 rounded transition border flex items-center gap-1 ${
                          c.queued_for_render
                            ? 'bg-brand text-white border-brand'
                            : 'bg-surface text-text-muted border-border hover:text-text-primary'
                        }`}
                        title="Include in final Shorts render queue"
                      >
                        <Video className="w-3 h-3" />
                        {c.queued_for_render ? 'Queued' : 'Queue'}
                      </button>

                      {/* Inspect Detail Button */}
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs px-2.5"
                        onClick={() => handleInspect(c)}
                      >
                        <Eye className="w-3 h-3 mr-1" /> Inspect
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Candidate Detail Modal / Drawer */}
      {inspectCandidate && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-5 border-b border-border flex items-center justify-between bg-surface-card">
              <div className="flex items-center gap-3">
                <Badge variant={getStatusBadgeVariant(inspectCandidate.review_status)}>
                  {inspectCandidate.review_status.toUpperCase()}
                </Badge>
                <div
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getScoreColor(
                    inspectCandidate.quality_score
                  )}`}
                >
                  Score: {Math.round(inspectCandidate.quality_score)}/100
                </div>
                <span className="text-xs font-mono text-text-muted">
                  ID: {inspectCandidate.id}
                </span>
              </div>
              <button
                onClick={() => setInspectCandidate(null)}
                className="p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Scrollable Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {/* Title Edit */}
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1 uppercase tracking-wider">
                  Highlight Title
                </label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => {
                    setEditTitle(e.target.value);
                    setBoundaryDirty(true);
                  }}
                  className="w-full text-sm font-semibold px-3 py-2 bg-surface-card border border-border rounded-lg text-text-primary focus:outline-none focus:border-brand"
                />
              </div>

              {/* Boundary Fine-Tuning Section */}
              <div className="p-4 rounded-xl border border-border bg-surface-card/50 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-text-primary flex items-center gap-1.5 uppercase tracking-wider">
                    <Sliders className="w-3.5 h-3.5 text-brand" /> Boundary Fine-Tuning & Snapping
                  </h4>
                  {inspectCandidate.is_user_modified && (
                    <span className="text-xs text-blue-400 font-mono">User Trimmed</span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Start Time Fine-Tuning */}
                  <div className="bg-surface p-3 rounded-lg border border-border">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-text-muted">Start Boundary</span>
                      <span className="font-mono text-brand font-bold">{editStartTime.toFixed(2)}s</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setEditStartTime((v) => Math.max(0, +(v - 0.5).toFixed(2)));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        -0.5s
                      </button>
                      <button
                        onClick={() => {
                          setEditStartTime((v) => Math.max(0, +(v - 0.1).toFixed(2)));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        -0.1s
                      </button>
                      <input
                        type="range"
                        min="0"
                        max={editEndTime - 1}
                        step="0.1"
                        value={editStartTime}
                        onChange={(e) => {
                          setEditStartTime(parseFloat(e.target.value));
                          setBoundaryDirty(true);
                        }}
                        className="flex-1 accent-brand cursor-pointer"
                      />
                      <button
                        onClick={() => {
                          setEditStartTime((v) => Math.min(editEndTime - 1, +(v + 0.1).toFixed(2)));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        +0.1s
                      </button>
                    </div>
                    <div className="text-[10px] text-text-muted mt-1 font-mono">
                      Suggested AI Start: {inspectCandidate.suggested_start_time.toFixed(2)}s
                    </div>
                  </div>

                  {/* End Time Fine-Tuning */}
                  <div className="bg-surface p-3 rounded-lg border border-border">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-text-muted">End Boundary</span>
                      <span className="font-mono text-brand font-bold">{editEndTime.toFixed(2)}s</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setEditEndTime((v) => Math.max(editStartTime + 1, +(v - 0.5).toFixed(2)));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        -0.5s
                      </button>
                      <button
                        onClick={() => {
                          setEditEndTime((v) => Math.max(editStartTime + 1, +(v - 0.1).toFixed(2)));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        -0.1s
                      </button>
                      <input
                        type="range"
                        min={editStartTime + 1}
                        max={Math.max(editEndTime + 30, 120)}
                        step="0.1"
                        value={editEndTime}
                        onChange={(e) => {
                          setEditEndTime(parseFloat(e.target.value));
                          setBoundaryDirty(true);
                        }}
                        className="flex-1 accent-brand cursor-pointer"
                      />
                      <button
                        onClick={() => {
                          setEditEndTime((v) => +(v + 0.1).toFixed(2));
                          setBoundaryDirty(true);
                        }}
                        className="px-2 py-1 bg-surface-card border border-border rounded text-xs text-text-secondary hover:text-text-primary"
                      >
                        +0.1s
                      </button>
                    </div>
                    <div className="text-[10px] text-text-muted mt-1 font-mono">
                      Suggested AI End: {inspectCandidate.suggested_end_time.toFixed(2)}s
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="text-xs text-text-muted">
                    New Duration: <span className="font-mono font-bold text-text-primary">{(editEndTime - editStartTime).toFixed(2)}s</span>
                  </div>
                  {boundaryDirty && (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={handleSaveBoundaries}
                      disabled={actionInProgress === inspectCandidate.id}
                    >
                      Save Boundary Changes
                    </Button>
                  )}
                </div>
              </div>

              {/* 9-Component Score Breakdown */}
              <div>
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
                  Explainable Score Breakdown (Scoring Version: {inspectCandidate.scoring_version})
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {inspectCandidate.score_breakdown &&
                    Object.entries(inspectCandidate.score_breakdown)
                      .filter(([k]) => k !== 'total_score')
                      .map(([key, val]) => (
                        <div
                          key={key}
                          className="bg-surface-card border border-border p-2.5 rounded-lg flex items-center justify-between text-xs"
                        >
                          <span className="text-text-muted capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span
                            className={`font-mono font-bold ${
                              Number(val) < 0 ? 'text-rose-400' : 'text-text-primary'
                            }`}
                          >
                            {Number(val) > 0 ? `+${val}` : val}
                          </span>
                        </div>
                      ))}
                </div>
              </div>

              {/* AI Explanation & Why It Works */}
              <div className="p-4 rounded-xl border border-border bg-surface-card/40 space-y-2">
                <h4 className="text-xs font-semibold text-text-primary flex items-center gap-1.5 uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" /> AI Content Analysis & Viral Thesis
                </h4>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {inspectCandidate.ai_explanation?.why_it_works ||
                    'Strong conversational punchline supported by distinct audio cue and continuous speech coherence.'}
                </p>

                {inspectCandidate.ai_explanation?.strengths && (
                  <div className="pt-2">
                    <span className="text-[11px] font-semibold text-text-muted uppercase">Strengths:</span>
                    <ul className="list-disc list-inside text-xs text-text-muted mt-1 space-y-0.5">
                      {inspectCandidate.ai_explanation.strengths.map((str, i) => (
                        <li key={i}>{str}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Alternative Cuts (Overlap clustering) */}
              {alternatives.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-purple-400" /> Alternative Temporal Cuts (IoU ≥ 0.65)
                  </h4>
                  <div className="space-y-2">
                    {alternatives.map((alt) => (
                      <div
                        key={alt.id}
                        className="p-3 bg-surface-card border border-border rounded-lg flex items-center justify-between gap-3 text-xs"
                      >
                        <div>
                          <div className="font-medium text-text-primary">{alt.title}</div>
                          <div className="text-[11px] font-mono text-text-muted mt-0.5">
                            {formatTimestamp(alt.start_time)} - {formatTimestamp(alt.end_time)} ({alt.duration.toFixed(1)}s)
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-text-secondary">
                            Score: {Math.round(alt.quality_score)}
                          </span>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleInspect(alt)}
                          >
                            Switch To
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Actions Footer */}
            <div className="p-4 border-t border-border bg-surface-card flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleApprove(inspectCandidate.id)}
                  disabled={inspectCandidate.review_status === 'approved'}
                >
                  <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" /> Approve Candidate
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-rose-400 hover:text-rose-300"
                  onClick={() => handleReject(inspectCandidate.id)}
                  disabled={inspectCandidate.review_status === 'rejected'}
                >
                  <X className="w-3.5 h-3.5 mr-1" /> Reject
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleToggleQueueRender(inspectCandidate)}
                >
                  <Video className="w-3.5 h-3.5 mr-1" />
                  {inspectCandidate.queued_for_render ? 'Remove from Queue' : 'Queue for Render'}
                </Button>
              </div>

              <Button size="sm" variant="secondary" onClick={() => setInspectCandidate(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Discovery Configuration Modal */}
      {showDiscoveryModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand" /> Discover Shorts Highlights
              </h3>
              <button
                onClick={() => setShowDiscoveryModal(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-text-muted leading-relaxed">
              Scans analyzed scenes, speech transcripts, and visual signals to surface the most engaging moments.
            </p>

            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">
                  Target Media Asset
                </label>
                <select
                  value={selectedAssetId === 'all' && mediaAssets.length > 0 ? mediaAssets[0].id : selectedAssetId}
                  onChange={(e) => setSelectedAssetId(e.target.value)}
                  className="w-full text-xs bg-surface-card border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none"
                >
                  {mediaAssets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.original_filename}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-text-muted mb-1">
                    Min Duration (sec)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="60"
                    value={discMinDuration}
                    onChange={(e) => setDiscMinDuration(Number(e.target.value))}
                    className="w-full text-xs bg-surface-card border border-border rounded-lg px-3 py-1.5 text-text-primary"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-muted mb-1">
                    Max Duration (sec)
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="180"
                    value={discMaxDuration}
                    onChange={(e) => setDiscMaxDuration(Number(e.target.value))}
                    className="w-full text-xs bg-surface-card border border-border rounded-lg px-3 py-1.5 text-text-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">
                  Target Clip Count
                </label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={discTargetCount}
                  onChange={(e) => setDiscTargetCount(Number(e.target.value))}
                  className="w-full text-xs bg-surface-card border border-border rounded-lg px-3 py-1.5 text-text-primary"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="ai-expl"
                  checked={discUseAI}
                  onChange={(e) => setDiscUseAI(e.target.checked)}
                  className="rounded border-border text-brand focus:ring-0 cursor-pointer"
                />
                <label htmlFor="ai-expl" className="text-xs text-text-secondary cursor-pointer">
                  Use Local AI (Ollama qwen3-vl) for Explanations
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-4 border-t border-border">
              <Button variant="secondary" size="sm" onClick={() => setShowDiscoveryModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={discovering}
                onClick={() =>
                  handleRunDiscovery(
                    selectedAssetId === 'all' && mediaAssets.length > 0
                      ? mediaAssets[0].id
                      : selectedAssetId
                  )
                }
              >
                {discovering ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Discovering...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Start Discovery
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
