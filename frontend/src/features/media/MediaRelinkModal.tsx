import React, { useState, useRef } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  HardDrive,
  RefreshCw,
  Upload,
  FileCheck,
  AlertCircle,
} from 'lucide-react';
import { Dialog } from '../../components/ui/Dialog';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { MediaAssetItem } from '../../types/projects';
import {
  inspectRelinkCandidate,
  relinkMedia,
  relinkMediaWithUpload,
  reconcileMissingMedia,
} from '../../services/apiClient';

interface MediaRelinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: MediaAssetItem | null;
  projectId?: string;
  onSuccess: (relinkedInfo?: any) => void;
}

export const MediaRelinkModal: React.FC<MediaRelinkModalProps> = ({
  isOpen,
  onClose,
  asset,
  projectId = 'default',
  onSuccess,
}) => {
  const [mode, setMode] = useState<'upload' | 'path'>('path');
  const [candidatePath, setCandidatePath] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadStatusText, setUploadStatusText] = useState<string>('');
  const [isInspecting, setIsInspecting] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isReconciling, setIsReconciling] = useState(false);
  const [forceRelink, setForceRelink] = useState(false);
  const [inspectionResult, setInspectionResult] = useState<{
    match_status: 'exact' | 'compatible' | 'mismatch';
    warnings: string[];
    comparison: {
      original_duration?: number;
      candidate_duration?: number;
      original_resolution?: string;
      candidate_resolution?: string;
      original_size_bytes?: number;
      candidate_size_bytes?: number;
      original_sha256?: string;
      candidate_sha256?: string;
      sha256_match?: boolean;
    };
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const resetState = () => {
    setCandidatePath('');
    setSelectedFile(null);
    setUploadProgress(0);
    setUploadStatusText('');
    setIsInspecting(false);
    setIsExecuting(false);
    setIsReconciling(false);
    setForceRelink(false);
    setInspectionResult(null);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleInspectPath = async () => {
    if (!asset || !candidatePath.trim()) return;
    setIsInspecting(true);
    setErrorMessage(null);
    try {
      const res = await inspectRelinkCandidate(
        asset.project_id || projectId,
        asset.id,
        candidatePath.trim()
      );
      setInspectionResult(res);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to inspect candidate path.');
      setInspectionResult(null);
    } finally {
      setIsInspecting(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setErrorMessage(null);
      setInspectionResult(null);
    }
  };

  const handleCheckReconnect = async () => {
    setIsReconciling(true);
    setErrorMessage(null);
    try {
      const res = await reconcileMissingMedia(asset?.project_id || projectId);
      if (res.restored_count > 0) {
        setSuccessMessage(`External media reconnected! Restored ${res.restored_count} media file(s).`);
        setTimeout(() => {
          onSuccess(res);
          handleClose();
        }, 1200);
      } else {
        setErrorMessage(
          `Checked storage paths. The file was not found at its original location. Please specify the new path or upload the file.`
        );
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Reconciliation check failed.');
    } finally {
      setIsReconciling(false);
    }
  };

  const handleExecuteRelink = async () => {
    if (!asset) return;
    setIsExecuting(true);
    setErrorMessage(null);

    try {
      if (mode === 'path') {
        if (!candidatePath.trim()) {
          setErrorMessage('Please provide a valid file path.');
          setIsExecuting(false);
          return;
        }
        const res = await relinkMedia(
          asset.project_id || projectId,
          asset.id,
          candidatePath.trim(),
          forceRelink
        );
        setSuccessMessage(`Successfully relinked "${asset.original_filename}"!`);
        setTimeout(() => {
          onSuccess(res);
          handleClose();
        }, 1000);
      } else {
        // Mode === 'upload'
        if (!selectedFile) {
          setErrorMessage('Please choose a replacement video file.');
          setIsExecuting(false);
          return;
        }
        setUploadStatusText('Uploading replacement video...');
        const res = await relinkMediaWithUpload(
          asset.project_id || projectId,
          asset.id,
          selectedFile,
          forceRelink,
          undefined,
          {
            onProgress: (p) => {
              const pct = p.percentage ?? 0;
              setUploadProgress(pct);
              const loadedMb = (p.loaded / 1024 / 1024).toFixed(1);
              const totalMb = p.total ? (p.total / 1024 / 1024).toFixed(1) : '?';
              setUploadStatusText(`Uploaded ${loadedMb} MB / ${totalMb} MB (${pct}%)`);
            },
          }
        );
        setSuccessMessage(`Replacement uploaded and relinked successfully!`);
        setTimeout(() => {
          onSuccess(res);
          handleClose();
        }, 1000);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Relinking failed. Please verify the candidate file.');
    } finally {
      setIsExecuting(false);
    }
  };

  if (!isOpen || !asset) return null;

  const requiresForce = inspectionResult?.match_status === 'mismatch';
  const canSubmit =
    mode === 'path'
      ? Boolean(candidatePath.trim()) && (!requiresForce || forceRelink)
      : Boolean(selectedFile) && (!requiresForce || forceRelink);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title={
        <div className="flex items-center gap-2 text-text-primary">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>Relink Media File with Integrity Check</span>
        </div>
      }
      maxWidth="max-w-xl"
    >
      <div className="space-y-4 pt-1">
        {/* Missing File Notice */}
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-amber-300">Target Asset: {asset.original_filename}</span>
            <Badge variant="warning">MISSING</Badge>
          </div>
          <p className="text-text-muted font-mono text-[11px] truncate" title={asset.storage_path}>
            Expected Location: {asset.storage_path}
          </p>
          <div className="flex items-center gap-4 text-[11px] text-text-secondary pt-1 font-mono">
            <span>Size: {asset.file_size_bytes ? `${(asset.file_size_bytes / 1024 / 1024).toFixed(1)} MB` : 'N/A'}</span>
            <span>Duration: {asset.duration_seconds ? `${asset.duration_seconds.toFixed(1)}s` : 'N/A'}</span>
            <span>Resolution: {asset.resolution_label || (asset.width && asset.height ? `${asset.width}x${asset.height}` : 'N/A')}</span>
          </div>
        </div>

        {/* Reconnection Quick Check */}
        <div className="flex items-center justify-between p-2.5 bg-surface border border-border rounded-xl text-xs">
          <div>
            <p className="font-medium text-text-primary">External drive reconnected?</p>
            <p className="text-[11px] text-text-muted">Probe original storage paths to restore access automatically.</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCheckReconnect}
            isLoading={isReconciling}
            leftIcon={<HardDrive className="w-3.5 h-3.5 text-indigo-400" />}
          >
            Check Drive Reconnect
          </Button>
        </div>

        {/* Relink Mode Switcher */}
        <div className="flex border-b border-border">
          <button
            type="button"
            className={`pb-2 px-3 text-xs font-medium border-b-2 transition-colors ${
              mode === 'upload'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
            onClick={() => {
              setMode('upload');
              setInspectionResult(null);
              setErrorMessage(null);
            }}
          >
            Upload Replacement File
          </button>
          <button
            type="button"
            className={`pb-2 px-3 text-xs font-medium border-b-2 transition-colors ${
              mode === 'path'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
            onClick={() => {
              setMode('path');
              setInspectionResult(null);
              setErrorMessage(null);
            }}
          >
            Enter Local Disk Path
          </button>
        </div>

        {/* Mode: Upload */}
        {mode === 'upload' && (
          <div className="space-y-3">
            <div
              className={`p-6 border-2 border-dashed rounded-xl flex flex-col items-center justify-center cursor-pointer transition ${
                selectedFile
                  ? 'border-indigo-500/50 bg-indigo-500/5'
                  : 'border-border hover:border-indigo-500/40 bg-canvas-subtle'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*,.mp4,.mov,.mkv,.avi,.webm"
                className="hidden"
                onChange={handleFileSelect}
              />
              {selectedFile ? (
                <div className="flex flex-col items-center text-center space-y-1">
                  <FileCheck className="w-8 h-8 text-indigo-400 mb-1" />
                  <p className="text-sm font-medium text-text-primary">{selectedFile.name}</p>
                  <p className="text-xs text-text-muted font-mono">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB • {selectedFile.type || 'Video'}
                  </p>
                  <span className="text-[11px] text-indigo-400 pt-1">Click to select a different file</span>
                </div>
              ) : (
                <div className="flex flex-col items-center text-center space-y-1 text-text-muted">
                  <Upload className="w-8 h-8 mb-1 text-text-secondary" />
                  <p className="text-sm font-medium text-text-primary">Choose replacement video file</p>
                  <p className="text-xs">Drag and drop or click to browse</p>
                  <p className="text-[10px] font-mono text-zinc-500 pt-1">Supported: MP4, MOV, MKV, AVI, WEBM</p>
                </div>
              )}
            </div>

            {/* Upload Progress Bar */}
            {isExecuting && (
              <div className="space-y-1 p-3 bg-surface border border-border rounded-xl">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-text-primary font-medium">{uploadStatusText || 'Transferring...'}</span>
                  <span className="font-mono text-indigo-400">{uploadProgress}%</span>
                </div>
                <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 transition-all duration-150"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Mode: Local Path */}
        {mode === 'path' && (
          <div className="space-y-3">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  label="New Absolute Path on Disk"
                  value={candidatePath}
                  onChange={(e) => setCandidatePath(e.target.value)}
                  placeholder="e.g. D:\Videos\interview_take_1.mp4"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleInspectPath}
                isLoading={isInspecting}
                disabled={!candidatePath.trim()}
              >
                Verify Candidate
              </Button>
            </div>
            <p className="text-[11px] text-text-muted">
              Inspects candidate video container, verifies readability with FFprobe, and checks technical match.
            </p>
          </div>
        )}

        {/* Inspection Comparison Results (when available) */}
        {inspectionResult && (
          <div className="p-3 bg-canvas-subtle border border-border rounded-xl space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-text-primary">Candidate Verification:</span>
              <Badge
                variant={
                  inspectionResult.match_status === 'exact'
                    ? 'success'
                    : inspectionResult.match_status === 'compatible'
                    ? 'warning'
                    : 'danger'
                }
              >
                {inspectionResult.match_status.toUpperCase()}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div>
                <span className="text-text-muted block">Original Duration:</span>
                <span>{inspectionResult.comparison.original_duration?.toFixed(2) || 'N/A'}s</span>
              </div>
              <div>
                <span className="text-text-muted block">Candidate Duration:</span>
                <span>{inspectionResult.comparison.candidate_duration?.toFixed(2) || 'N/A'}s</span>
              </div>
              <div>
                <span className="text-text-muted block">Original Resolution:</span>
                <span>{inspectionResult.comparison.original_resolution || 'N/A'}</span>
              </div>
              <div>
                <span className="text-text-muted block">Candidate Resolution:</span>
                <span>{inspectionResult.comparison.candidate_resolution || 'N/A'}</span>
              </div>
            </div>

            {inspectionResult.comparison.sha256_match !== undefined && (
              <div className="pt-1 text-[11px] font-mono flex items-center gap-1.5">
                <span className="text-text-muted">Checksum SHA-256:</span>
                {inspectionResult.comparison.sha256_match ? (
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> EXACT CHECKSUM MATCH
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Checksum differs (different file content)
                  </span>
                )}
              </div>
            )}

            {inspectionResult.warnings.length > 0 && (
              <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg space-y-1">
                <span className="text-[11px] font-semibold text-amber-400 block">Discrepancy Warnings:</span>
                {inspectionResult.warnings.map((w, idx) => (
                  <p key={idx} className="text-[10px] text-amber-300 font-mono">
                    • {w}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Force relink checkbox if mismatch or duration differs */}
        {(requiresForce || inspectionResult?.warnings.length) && (
          <label className="flex items-start gap-2 p-2 bg-zinc-900 border border-border rounded-lg text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={forceRelink}
              onChange={(e) => setForceRelink(e.target.checked)}
              className="mt-0.5 rounded border-border text-indigo-500 accent-indigo-500"
            />
            <span className="text-text-secondary">
              Force relink despite duration or format discrepancy (existing clip timestamps may shift).
            </span>
          </label>
        )}

        {/* Feedback Messages */}
        {errorMessage && (
          <div className="p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={isExecuting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleExecuteRelink}
            isLoading={isExecuting}
            disabled={!canSubmit || isExecuting}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Relink &amp; Restore
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
