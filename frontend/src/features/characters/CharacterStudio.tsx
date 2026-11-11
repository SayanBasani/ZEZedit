import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Download,
  Edit2,
  FileJson,
  Info,
  Layers,
  Merge,
  RefreshCw,
  Search,
  Split,
  Tag,
  Trash2,
  UserCheck,
  Users,
  X,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  confirmCharacterCandidate,
  detachCharacterObservation,
  exportCharacterJson,
  getCharacterCandidates,
  getCharacterLibrary,
  mergeCharacterCandidates,
  rejectCharacterCandidate,
  renameCharacterCandidate,
  runCharacterExtraction,
  splitCharacterCandidate,
} from '../../services/apiClient';
import {
  CharacterCandidate,
  CharacterExportPayload,
  CharacterProfile,
} from '../../types/character';
import { MediaAssetItem } from '../../types/projects';

interface CharacterStudioProps {
  projectId: string;
  mediaAssets?: MediaAssetItem[];
}

export const CharacterStudio: React.FC<CharacterStudioProps> = ({
  projectId,
  mediaAssets = [],
}) => {
  const [activeTab, setActiveTab] = useState<'review' | 'library'>('review');
  const [selectedMediaId, setSelectedMediaId] = useState<string>(
    mediaAssets[0]?.id || ''
  );
  const [sampleInterval, setSampleInterval] = useState<number>(1.0);
  const [candidates, setCandidates] = useState<CharacterCandidate[]>([]);
  const [libraryProfiles, setLibraryProfiles] = useState<CharacterProfile[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Review interaction state
  const [editingLabelId, setEditingLabelId] = useState<string | null>(null);
  const [newLabelText, setNewLabelText] = useState<string>('');

  // Confirm Modal state
  const [confirmModalCand, setConfirmModalCand] = useState<CharacterCandidate | null>(null);
  const [charName, setCharName] = useState<string>('');
  const [charBio, setCharBio] = useState<string>('');
  const [charTags, setCharTags] = useState<string>('');

  // Merge Modal state
  const [mergeModalCand, setMergeModalCand] = useState<CharacterCandidate | null>(null);
  const [selectedMergeTargetId, setSelectedMergeTargetId] = useState<string>('');

  // Split Modal state
  const [splitModalCand, setSplitModalCand] = useState<CharacterCandidate | null>(null);
  const [selectedObsToSplit, setSelectedObsToSplit] = useState<string[]>([]);
  const [splitCandidateLabel, setSplitCandidateLabel] = useState<string>('');

  // JSON Export Modal state
  const [exportedJsonData, setExportedJsonData] = useState<CharacterExportPayload | null>(null);

  // Library search
  const [librarySearchQuery, setLibrarySearchQuery] = useState<string>('');

  // Load candidates
  const loadCandidates = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getCharacterCandidates(projectId);
      setCandidates(data);
      if (data.length > 0 && !selectedCandidateId) {
        setSelectedCandidateId(data[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load character candidates.');
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedCandidateId]);

  // Load library
  const loadLibrary = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await getCharacterLibrary(projectId, librarySearchQuery);
      setLibraryProfiles(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load character library.');
    }
  }, [projectId, librarySearchQuery]);

  useEffect(() => {
    loadCandidates();
    loadLibrary();
  }, [loadCandidates, loadLibrary]);

  useEffect(() => {
    if (mediaAssets.length > 0 && !selectedMediaId) {
      setSelectedMediaId(mediaAssets[0].id);
    }
  }, [mediaAssets, selectedMediaId]);

  const handleStartExtraction = async () => {
    if (!selectedMediaId) {
      setError('Please select a media asset to analyze.');
      return;
    }
    setIsExtracting(true);
    setError(null);
    try {
      await runCharacterExtraction(projectId, {
        media_asset_id: selectedMediaId,
        sample_interval_sec: sampleInterval,
        min_face_size: 25,
      });
      setSuccessMessage('Character extraction completed successfully.');
      await loadCandidates();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Extraction failed.');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleRename = async (candidateId: string) => {
    if (!newLabelText.trim()) return;
    try {
      await renameCharacterCandidate(projectId, candidateId, newLabelText.trim());
      setEditingLabelId(null);
      await loadCandidates();
    } catch (err: any) {
      setError(err?.message || 'Failed to rename candidate.');
    }
  };

  const handleConfirmToLibrary = async () => {
    if (!confirmModalCand) return;
    try {
      const tags = charTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await confirmCharacterCandidate(projectId, confirmModalCand.id, {
        name: charName.trim() || confirmModalCand.label,
        biography: charBio.trim(),
        appearance_tags: tags,
      });
      setConfirmModalCand(null);
      setSuccessMessage(`Character confirmed to persistent Library!`);
      await loadCandidates();
      await loadLibrary();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Failed to confirm character.');
    }
  };

  const handleMerge = async () => {
    if (!mergeModalCand || !selectedMergeTargetId) return;
    try {
      await mergeCharacterCandidates(projectId, {
        source_candidate_ids: [mergeModalCand.id],
        target_candidate_id: selectedMergeTargetId,
      });
      setMergeModalCand(null);
      setSuccessMessage('Candidates merged successfully.');
      await loadCandidates();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Failed to merge candidates.');
    }
  };

  const handleSplit = async () => {
    if (!splitModalCand || selectedObsToSplit.length === 0 || !splitCandidateLabel.trim()) return;
    try {
      await splitCharacterCandidate(projectId, splitModalCand.id, {
        observation_ids_to_split: selectedObsToSplit,
        new_candidate_label: splitCandidateLabel.trim(),
      });
      setSplitModalCand(null);
      setSelectedObsToSplit([]);
      setSplitCandidateLabel('');
      setSuccessMessage('Candidate split into new grouping.');
      await loadCandidates();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Failed to split candidate.');
    }
  };

  const handleDetachObservation = async (candidateId: string, obsId: string) => {
    try {
      await detachCharacterObservation(projectId, candidateId, obsId);
      await loadCandidates();
    } catch (err: any) {
      setError(err?.message || 'Failed to detach observation.');
    }
  };

  const handleRejectCandidate = async (candidateId: string) => {
    try {
      await rejectCharacterCandidate(projectId, candidateId);
      await loadCandidates();
    } catch (err: any) {
      setError(err?.message || 'Failed to reject candidate.');
    }
  };

  const handleExportJson = async (characterId: string) => {
    try {
      const payload = await exportCharacterJson(projectId, characterId);
      setExportedJsonData(payload);
    } catch (err: any) {
      setError(err?.message || 'Failed to export character data.');
    }
  };

  const activeCandidates = candidates.filter((c) => c.review_status !== 'merged');
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId) || activeCandidates[0];

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight">Character Extraction Studio</h1>
              <Badge variant="purple" className="text-xs">
                Milestone 10
              </Badge>
            </div>
            <p className="text-xs text-slate-400">
              Human-in-the-loop face & person clustering, appearances, and persistent Character Library.
            </p>
          </div>
        </div>

        {/* Studio Tabs */}
        <div className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
          <button
            onClick={() => setActiveTab('review')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === 'review'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Candidate Review ({activeCandidates.length})
          </button>
          <button
            onClick={() => setActiveTab('library')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === 'library'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Character Library ({libraryProfiles.length})
          </button>
        </div>
      </div>

      {/* Audit & Transparency Disclaimer Banner */}
      <div className="bg-amber-950/40 border-b border-amber-900/40 px-6 py-2 flex items-center gap-2 text-xs text-amber-300">
        <Info className="w-4 h-4 flex-shrink-0 text-amber-400" />
        <span>
          <strong>Transparency Notice:</strong> Automated clusters are provisional visual candidate
          groupings, not confirmed biometric identity recognition. Dialogue overlap indicates temporal
          transcript intersection, not verified speaker identification.
        </span>
      </div>

      {/* Error & Success Toasts */}
      {error && (
        <div className="mx-6 mt-3 p-3 bg-red-950/60 border border-red-800 text-red-200 text-xs rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {successMessage && (
        <div className="mx-6 mt-3 p-3 bg-emerald-950/60 border border-emerald-800 text-emerald-200 text-xs rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-400" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Workspace */}
      {activeTab === 'review' ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Left Column: Extraction Trigger & Candidate Roster */}
          <div className="w-80 border-r border-slate-800 bg-slate-900/30 flex flex-col">
            {/* Extraction Trigger Panel */}
            <div className="p-4 border-b border-slate-800/80 bg-slate-900/40">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Extract Characters
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Target Media</label>
                  <select
                    value={selectedMediaId}
                    onChange={(e) => setSelectedMediaId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    {mediaAssets.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.original_filename} ({(m.duration_seconds ?? 0).toFixed(0)}s)
                      </option>
                    ))}
                    {mediaAssets.length === 0 && (
                      <option value="">No media assets available</option>
                    )}
                  </select>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <div className="flex-1">
                    <label className="text-[11px] text-slate-400 block mb-1">Sampling Interval</label>
                    <select
                      value={sampleInterval}
                      onChange={(e) => setSampleInterval(parseFloat(e.target.value))}
                      className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value={0.5}>0.5s (Dense)</option>
                      <option value={1.0}>1.0s (Balanced)</option>
                      <option value={2.0}>2.0s (Fast)</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <Button
                      onClick={handleStartExtraction}
                      disabled={isExtracting || !selectedMediaId}
                      className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5"
                    >
                      {isExtracting ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1" />
                          Sampling...
                        </>
                      ) : (
                        'Extract'
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Candidate List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              <div className="flex items-center justify-between px-1 mb-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Candidates ({activeCandidates.length})
                </span>
                <button
                  onClick={loadCandidates}
                  className="text-slate-400 hover:text-slate-200 p-1"
                  title="Refresh"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
                </button>
              </div>

              {activeCandidates.map((c) => {
                const isSelected = selectedCandidate?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCandidateId(c.id)}
                    className={`p-2.5 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/60 text-slate-100 shadow-sm'
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {/* Avatar preview */}
                      <div className="w-10 h-10 rounded bg-slate-800 flex items-center justify-center overflow-hidden flex-shrink-0 border border-slate-700/60">
                        {c.representative_thumbnail_path ? (
                          <div className="w-full h-full bg-slate-800 flex items-center justify-center text-[10px] text-slate-500 font-mono">
                            Thumb
                          </div>
                        ) : (
                          <Users className="w-4 h-4 text-slate-600" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-semibold text-xs truncate">{c.label}</span>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                              c.review_status === 'confirmed'
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                                : c.review_status === 'rejected'
                                ? 'bg-red-950 text-red-400 border border-red-800/60'
                                : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                            }`}
                          >
                            {c.review_status}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-1">
                          <span>{c.observation_count} obs</span>
                          <span>•</span>
                          <span>{c.sampled_screen_time_seconds.toFixed(1)}s screen</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {activeCandidates.length === 0 && (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No candidates extracted yet. Select a video and click "Extract".
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Selected Candidate Inspector & Human Review Controls */}
          <div className="flex-1 flex flex-col overflow-y-auto bg-slate-950 p-6 space-y-6">
            {selectedCandidate ? (
              <>
                {/* Candidate Overview Card */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-500 font-mono overflow-hidden">
                        {selectedCandidate.representative_thumbnail_path ? (
                          <span>Preview</span>
                        ) : (
                          <Users className="w-8 h-8 text-slate-600" />
                        )}
                      </div>
                      <div>
                        {editingLabelId === selectedCandidate.id ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={newLabelText}
                              onChange={(e) => setNewLabelText(e.target.value)}
                              className="bg-slate-800 border border-indigo-500 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none"
                              placeholder="Enter character name..."
                              autoFocus
                            />
                            <Button
                              onClick={() => handleRename(selectedCandidate.id)}
                              className="text-xs bg-indigo-600 text-white px-2 py-1"
                            >
                              Save
                            </Button>
                            <Button
                              onClick={() => setEditingLabelId(null)}
                              variant="outline"
                              className="text-xs px-2 py-1"
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <h2 className="text-base font-bold text-slate-100">
                              {selectedCandidate.label}
                            </h2>
                            <button
                              onClick={() => {
                                setEditingLabelId(selectedCandidate.id);
                                setNewLabelText(selectedCandidate.label);
                              }}
                              className="text-slate-400 hover:text-slate-200 p-1"
                              title="Rename candidate"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}

                        <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                          <span>Status: <strong className="text-slate-200 capitalize">{selectedCandidate.review_status}</strong></span>
                          <span>•</span>
                          <span>Method: <code className="text-slate-300 font-mono text-[11px]">{selectedCandidate.detection_methodology}</code></span>
                          <span>•</span>
                          <span>Confidence: <strong>{(selectedCandidate.clustering_confidence * 100).toFixed(0)}%</strong></span>
                        </div>
                      </div>
                    </div>

                    {/* Review Action Buttons */}
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                      <Button
                        onClick={() => {
                          setConfirmModalCand(selectedCandidate);
                          setCharName(selectedCandidate.label);
                        }}
                        className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        Confirm to Library
                      </Button>

                      <Button
                        onClick={() => {
                          setMergeModalCand(selectedCandidate);
                          const others = activeCandidates.filter((c) => c.id !== selectedCandidate.id);
                          setSelectedMergeTargetId(others[0]?.id || '');
                        }}
                        disabled={activeCandidates.length < 2}
                        variant="outline"
                        className="text-xs border-slate-700 text-slate-300 hover:text-white gap-1.5"
                      >
                        <Merge className="w-3.5 h-3.5" />
                        Merge With...
                      </Button>

                      <Button
                        onClick={() => {
                          setSplitModalCand(selectedCandidate);
                          setSelectedObsToSplit([]);
                          setSplitCandidateLabel(`${selectedCandidate.label} (Split)`);
                        }}
                        disabled={selectedCandidate.observation_count < 2}
                        variant="outline"
                        className="text-xs border-slate-700 text-slate-300 hover:text-white gap-1.5"
                      >
                        <Split className="w-3.5 h-3.5" />
                        Split
                      </Button>

                      <Button
                        onClick={() => handleRejectCandidate(selectedCandidate.id)}
                        variant="outline"
                        className="text-xs border-red-900/60 text-red-400 hover:bg-red-950/40 gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Reject
                      </Button>
                    </div>
                  </div>

                  {/* Screen Time Metrics Breakdown */}
                  <div className="grid grid-cols-3 gap-4 mt-5 pt-4 border-t border-slate-800/80">
                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <div className="text-[11px] text-slate-400">Sampled Frames Screen Time</div>
                      <div className="text-base font-bold text-indigo-400 mt-0.5">
                        {selectedCandidate.sampled_screen_time_seconds.toFixed(1)}s
                      </div>
                      <div className="text-[10px] text-slate-500">Based on {selectedCandidate.observation_count} sampled frames</div>
                    </div>

                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <div className="text-[11px] text-slate-400">Continuous Screen Time (Est.)</div>
                      <div className="text-base font-bold text-teal-400 mt-0.5">
                        {selectedCandidate.estimated_screen_time_seconds.toFixed(1)}s
                      </div>
                      <div className="text-[10px] text-slate-500">Span from first to last observation</div>
                    </div>

                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <div className="text-[11px] text-slate-400">Observations Count</div>
                      <div className="text-base font-bold text-amber-400 mt-0.5">
                        {selectedCandidate.observation_count}
                      </div>
                      <div className="text-[10px] text-slate-500">Non-destructive frame evidence</div>
                    </div>
                  </div>
                </div>

                {/* Observation Gallery */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <Layers className="w-4 h-4 text-indigo-400" />
                      Observations & Dialogue Evidence ({selectedCandidate.observations.length})
                    </h3>
                    <span className="text-xs text-slate-500">
                      Detach false positives non-destructively
                    </span>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {selectedCandidate.observations.map((obs) => (
                      <div
                        key={obs.id}
                        className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex flex-col justify-between space-y-2 group hover:border-slate-700 transition-all"
                      >
                        <div className="relative aspect-video bg-slate-950 rounded border border-slate-800/80 flex items-center justify-center overflow-hidden">
                          <span className="text-[10px] font-mono text-slate-600">
                            t={obs.timestamp.toFixed(2)}s
                          </span>
                          <span className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur text-[9px] font-mono text-slate-200">
                            {obs.detection_type} ({Math.round(obs.confidence * 100)}%)
                          </span>
                          <button
                            onClick={() => handleDetachObservation(selectedCandidate.id, obs.id)}
                            className="absolute top-1.5 right-1.5 p-1 rounded bg-red-950/80 text-red-400 hover:text-red-200 hover:bg-red-900/90 transition-all opacity-0 group-hover:opacity-100"
                            title="Detach observation (retains disk evidence)"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>

                        {/* Associated dialogue snippet */}
                        {obs.unverified_dialogue ? (
                          <div className="p-2 rounded bg-indigo-950/30 border border-indigo-900/40 text-[10px] text-indigo-300 line-clamp-2">
                            {obs.unverified_dialogue}
                          </div>
                        ) : (
                          <div className="text-[10px] text-slate-600 italic">
                            No temporal dialogue overlap
                          </div>
                        )}

                        <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-800/60">
                          <span>Box: {obs.bounding_box.width}x{obs.bounding_box.height}</span>
                          <span>t={obs.timestamp.toFixed(1)}s</span>
                        </div>
                      </div>
                    ))}

                    {selectedCandidate.observations.length === 0 && (
                      <div className="col-span-full p-8 text-center text-slate-500 text-xs bg-slate-900/20 rounded-lg border border-dashed border-slate-800">
                        No active observations for this candidate.
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs">
                <Users className="w-12 h-12 text-slate-700 mb-3" />
                Select a candidate from the roster to inspect observations and review.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Persistent Character Library Tab */
        <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-100">Persistent Character Library</h2>
              <p className="text-xs text-slate-400">
                Confirmed characters saved across projects with screen-time history and JSON export.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Search characters or tags..."
                  value={librarySearchQuery}
                  onChange={(e) => setLibrarySearchQuery(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-64"
                />
              </div>
              <Button
                onClick={loadLibrary}
                variant="outline"
                className="text-xs border-slate-700 text-slate-300 gap-1.5"
              >
                <RefreshCw className="w-3 h-3" />
                Refresh
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {libraryProfiles.map((p) => (
              <div
                key={p.id}
                className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3 hover:border-slate-700 transition-all shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-lg bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-400 font-bold text-sm overflow-hidden flex-shrink-0">
                    {p.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-sm text-slate-100 truncate">{p.name}</h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-0.5">
                      {p.biography || 'No biography provided.'}
                    </p>
                  </div>
                </div>

                {/* Appearance Tags */}
                {p.appearance_tags && p.appearance_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {p.appearance_tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700/60 flex items-center gap-1"
                      >
                        <Tag className="w-2.5 h-2.5 text-slate-500" />
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Stats */}
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/80">
                  <span>Appearances: <strong className="text-slate-200">{p.total_appearances}</strong></span>
                  <span>Screen time: <strong className="text-slate-200">{p.total_screen_time_seconds.toFixed(1)}s</strong></span>
                </div>

                <div className="pt-1 flex items-center justify-end gap-2">
                  <Button
                    onClick={() => handleExportJson(p.id)}
                    variant="outline"
                    className="text-xs border-indigo-900/60 text-indigo-400 hover:bg-indigo-950/40 gap-1.5 py-1 px-2.5"
                  >
                    <FileJson className="w-3.5 h-3.5" />
                    Export JSON
                  </Button>
                </div>
              </div>
            ))}

            {libraryProfiles.length === 0 && (
              <div className="col-span-full p-12 text-center text-slate-500 text-xs bg-slate-900/20 rounded-xl border border-dashed border-slate-800">
                No confirmed character profiles yet. Confirm provisional candidates from the review tab.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirm Candidate Modal */}
      {confirmModalCand && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-emerald-400" />
                Confirm to Character Library
              </h3>
              <button
                onClick={() => setConfirmModalCand(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Confirming assigns this provisional candidate group to a verified character profile in
              your project library.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Character Name</label>
                <input
                  type="text"
                  value={charName}
                  onChange={(e) => setCharName(e.target.value)}
                  placeholder="e.g. Host Alex"
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Biography / Role Notes</label>
                <textarea
                  rows={3}
                  value={charBio}
                  onChange={(e) => setCharBio(e.target.value)}
                  placeholder="Key notes about this speaker or character..."
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Appearance Tags (comma separated)</label>
                <input
                  type="text"
                  value={charTags}
                  onChange={(e) => setCharTags(e.target.value)}
                  placeholder="glasses, dark jacket, host"
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setConfirmModalCand(null)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmToLibrary}
                className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                Confirm Character
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Modal */}
      {mergeModalCand && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Merge className="w-4 h-4 text-indigo-400" />
                Merge Candidate Group
              </h3>
              <button
                onClick={() => setMergeModalCand(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Merge observations from <strong>{mergeModalCand.label}</strong> into another candidate
              group. The source candidate will be archived as merged.
            </p>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Target Candidate</label>
              <select
                value={selectedMergeTargetId}
                onChange={(e) => setSelectedMergeTargetId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                {activeCandidates
                  .filter((c) => c.id !== mergeModalCand.id)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label} ({c.observation_count} obs)
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setMergeModalCand(null)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                onClick={handleMerge}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Confirm Merge
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Split Modal */}
      {splitModalCand && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Split className="w-4 h-4 text-indigo-400" />
                Split Candidate Group
              </h3>
              <button
                onClick={() => setSplitModalCand(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Select which observations belong to a distinct person and move them into a new candidate.
            </p>

            <div>
              <label className="text-xs text-slate-400 block mb-1">New Candidate Label</label>
              <input
                type="text"
                value={splitCandidateLabel}
                onChange={(e) => setSplitCandidateLabel(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                placeholder="e.g. Guest Speaker"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1.5">
                Select Observations to Move ({selectedObsToSplit.length} selected):
              </label>
              <div className="max-h-48 overflow-y-auto space-y-1.5 border border-slate-800 rounded p-2 bg-slate-950/60">
                {splitModalCand.observations.map((obs) => {
                  const checked = selectedObsToSplit.includes(obs.id);
                  return (
                    <label
                      key={obs.id}
                      className="flex items-center gap-2.5 p-1.5 rounded hover:bg-slate-850 cursor-pointer text-xs text-slate-300"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          if (checked) {
                            setSelectedObsToSplit(selectedObsToSplit.filter((id) => id !== obs.id));
                          } else {
                            setSelectedObsToSplit([...selectedObsToSplit, obs.id]);
                          }
                        }}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      <span className="font-mono text-[11px] text-slate-400">
                        t={obs.timestamp.toFixed(2)}s
                      </span>
                      <span className="truncate flex-1 text-slate-400 text-[11px]">
                        {obs.unverified_dialogue || 'No dialogue'}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setSplitModalCand(null)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSplit}
                disabled={selectedObsToSplit.length === 0 || !splitCandidateLabel.trim()}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Confirm Split
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* JSON Export Viewer Modal */}
      {exportedJsonData && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-xl w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <FileJson className="w-4 h-4 text-indigo-400" />
                Character Export JSON ({exportedJsonData.profile.name})
              </h3>
              <button
                onClick={() => setExportedJsonData(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-indigo-300 max-h-72 overflow-y-auto">
              <pre>{JSON.stringify(exportedJsonData, null, 2)}</pre>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[10px] text-slate-500">
                Verified schema version {exportedJsonData.export_version}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(exportedJsonData, null, 2)], {
                      type: 'application/json',
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `character_${exportedJsonData.profile.name.toLowerCase().replace(/\s+/g, '_')}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download File
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setExportedJsonData(null)}
                  className="text-xs"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
