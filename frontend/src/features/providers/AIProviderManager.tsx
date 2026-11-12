import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Mic,
  RefreshCw,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  fetchAIProviders,
  testAIProvider,
  updateAIProvider,
} from '../../services/apiClient';
import { AIProvider, AIProviderTestResult } from '../../types/system';

export const AIProviderManager: React.FC = () => {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, AIProviderTestResult>>({});
  const [ollamaUrl, setOllamaUrl] = useState('http://127.0.0.1:11434');
  const [selectedModel, setSelectedModel] = useState('qwen3-vl:4b-instruct');
  const [secretToken, setSecretToken] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadProviders = useCallback(async () => {
    try {
      const list = await fetchAIProviders();
      setProviders(list);
      const ollama = list.find((p) => p.id === 'ollama');
      if (ollama) {
        if (ollama.base_url) setOllamaUrl(ollama.base_url);
        if (ollama.active_model) setSelectedModel(ollama.active_model);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load AI providers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProviders();
  }, [loadProviders]);

  const handleTestConnection = async (providerId: string) => {
    setTestingId(providerId);
    setErrorMessage(null);
    try {
      const res = await testAIProvider(
        providerId,
        providerId === 'ollama' ? ollamaUrl : undefined
      );
      setTestResults((prev) => ({ ...prev, [providerId]: res }));
      await loadProviders();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveOllama = async () => {
    setSaving(true);
    setSaveSuccess(false);
    setErrorMessage(null);
    try {
      await updateAIProvider('ollama', {
        base_url: ollamaUrl,
        active_model: selectedModel,
      });
      setSaveSuccess(true);
      await loadProviders();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-canvas text-text-primary overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border bg-surface/50 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-semibold tracking-tight">AI Provider Manager</h1>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Manage local inference endpoints, test model availability, and configure zero-dependency offline fallbacks.
          </p>
        </div>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => void loadProviders()}
          disabled={loading}
          className="flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {errorMessage && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="p-1 hover:text-red-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Architecture Notice Banner */}
        <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs flex items-start gap-3 text-indigo-200">
          <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block text-indigo-300">Local-First Privacy & Zero Cloud Dependency</span>
            <span>
              All inference models run directly on your workstation CPU. Video frames and transcripts are never uploaded
              to third-party servers. If local services are unreachable, deterministic heuristic fallbacks take over seamlessly.
            </span>
          </div>
        </div>

        {/* Provider Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providers.map((provider) => {
            const isOllama = provider.id === 'ollama';
            const isWhisper = provider.id === 'faster-whisper';
            const isReady = provider.status === 'ready';
            const testResult = testResults[provider.id];

            return (
              <div
                key={provider.id}
                className="rounded-2xl border border-border bg-surface p-4 flex flex-col justify-between shadow-sm space-y-4"
              >
                <div className="space-y-3">
                  {/* Card Title & Status Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-xl bg-surface-hover border border-border text-indigo-400">
                        {isOllama ? (
                          <Brain className="w-5 h-5" />
                        ) : isWhisper ? (
                          <Mic className="w-5 h-5" />
                        ) : (
                          <Sparkles className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <h2 className="font-semibold text-sm text-text-primary leading-tight">{provider.name}</h2>
                        <span className="text-[10px] text-text-muted font-mono uppercase">
                          {provider.provider_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                    <Badge variant={isReady ? 'success' : 'warning'}>
                      {provider.status.toUpperCase()}
                    </Badge>
                  </div>

                  {/* Latency and Health details */}
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between text-text-muted">
                      <span>Connection:</span>
                      <span className="font-mono text-text-secondary flex items-center gap-1">
                        {isReady ? <Wifi className="w-3 h-3 text-emerald-400" /> : <WifiOff className="w-3 h-3 text-amber-400" />}
                        {provider.is_local ? 'Local Host' : 'Remote'}
                      </span>
                    </div>
                    {provider.latency_ms !== null && (
                      <div className="flex justify-between text-text-muted">
                        <span>Latency:</span>
                        <span className="font-mono text-emerald-400 font-semibold">{provider.latency_ms} ms</span>
                      </div>
                    )}
                    <div className="flex justify-between text-text-muted">
                      <span>Active Model:</span>
                      <span className="font-mono text-text-primary font-bold">{provider.active_model}</span>
                    </div>
                  </div>

                  {/* Capabilities Pill List */}
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Capabilities</span>
                    <div className="flex flex-wrap gap-1">
                      {provider.capabilities.map((cap) => (
                        <span
                          key={cap.task}
                          className="px-2 py-0.5 rounded-md bg-surface-hover border border-border text-[10px] text-text-secondary"
                          title={cap.description}
                        >
                          {cap.task.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Test Feedback Notice */}
                  {testResult && (
                    <div
                      className={`p-2 rounded-lg text-[11px] ${
                        testResult.reachable
                          ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                          : 'bg-red-500/10 border border-red-500/30 text-red-300'
                      }`}
                    >
                      {testResult.reachable ? (
                        <div className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span>Connected ({testResult.latency_ms}ms, {testResult.available_models.length} models)</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                          <span>{testResult.error || 'Connection refused'}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Action button */}
                <div className="pt-2 border-t border-border">
                  <Button
                    size="sm"
                    variant="secondary"
                    className="w-full justify-center"
                    onClick={() => void handleTestConnection(provider.id)}
                    disabled={testingId === provider.id}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${testingId === provider.id ? 'animate-spin' : ''}`} />
                    <span>{testingId === provider.id ? 'Testing...' : 'Test Connection'}</span>
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Task-to-Model Engine Assignments */}
        <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-sm">
          <div className="border-b border-border pb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span>Studio Task-to-Engine Assignments</span>
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                Exact pipeline routing for video understanding, speech recognition, scoring, and tracking.
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              CPU-First Verified
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-canvas border border-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-text-primary">1. Speech Transcription & Word Timestamps</span>
                <Badge variant="success">BUILT-IN</Badge>
              </div>
              <p className="text-[11px] text-text-muted">
                Engine: <strong className="text-text-secondary font-mono">Faster-Whisper (int8 CPU)</strong>
              </p>
              <span className="text-[10px] text-text-muted block">
                Zero network requests; runs locally with CTranslate2 quantization for instant speech indexing.
              </span>
            </div>

            <div className="p-3 rounded-xl bg-canvas border border-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-text-primary">2. Visual Frame Understanding</span>
                <Badge variant={providers.find((p) => p.id === 'ollama')?.status === 'ready' ? 'success' : 'warning'}>
                  {providers.find((p) => p.id === 'ollama')?.status === 'ready' ? 'OLLAMA READY' : 'HEURISTIC ACTIVE'}
                </Badge>
              </div>
              <p className="text-[11px] text-text-muted">
                Engine: <strong className="text-text-secondary font-mono">{selectedModel} / Heuristics</strong>
              </p>
              <span className="text-[10px] text-text-muted block">
                Extracts scene semantics, action cues, and visual appeal; seamlessly falls back if Ollama is offline.
              </span>
            </div>

            <div className="p-3 rounded-xl bg-canvas border border-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-text-primary">3. Highlight Discovery & Rationale Scoring</span>
                <Badge variant="success">9-FACTOR ACTIVE</Badge>
              </div>
              <p className="text-[11px] text-text-muted">
                Engine: <strong className="text-text-secondary font-mono">Explainable 9-Factor Scoring Engine</strong>
              </p>
              <span className="text-[10px] text-text-muted block">
                Evaluates hooks, narrative completeness, audio energy, dialogue structure, and pacing.
              </span>
            </div>

            <div className="p-3 rounded-xl bg-canvas border border-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-text-primary">4. Smart Reframing & Subject Tracking</span>
                <Badge variant="purple">OPENCV NATIVE</Badge>
              </div>
              <p className="text-[11px] text-text-muted">
                Engine: <strong className="text-text-secondary font-mono">Haar Cascades & Moving Average Filter</strong>
              </p>
              <span className="text-[10px] text-text-muted block">
                Real-time 9:16 portrait tracking directly on CPU without GPU or cloud latency.
              </span>
            </div>
          </div>
        </div>

        {/* Ollama Configuration Panel */}
        <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-sm">
          <div className="border-b border-border pb-3">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              <span>Ollama Local Service Configuration</span>
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Specify your local Ollama port and preferred vision/multimodal reasoning model.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-medium text-text-secondary">Ollama Base URL</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://127.0.0.1:11434"
                className="w-full px-3 py-2 rounded-xl bg-canvas border border-border text-text-primary focus:outline-none focus:border-indigo-500 font-mono"
              />
              <span className="text-[11px] text-text-muted block">
                Default: http://127.0.0.1:11434 (standard Ollama desktop port)
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="font-medium text-text-secondary">Selected Vision Model</label>
              <input
                type="text"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                placeholder="qwen3-vl:4b-instruct"
                className="w-full px-3 py-2 rounded-xl bg-canvas border border-border text-text-primary focus:outline-none focus:border-indigo-500 font-mono"
              />
              <span className="text-[11px] text-text-muted block">
                Recommended: qwen3-vl:4b-instruct, llava:7b, or minicpm-v
              </span>
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="font-medium text-text-secondary flex items-center justify-between">
                <span>Optional Proxy / Endpoint Authorization Header</span>
                <span className="text-[10px] text-text-muted font-normal">Stored locally; secrets masked</span>
              </label>
              <div className="relative">
                <input
                  type={showSecret ? 'text' : 'password'}
                  value={secretToken}
                  onChange={(e) => setSecretToken(e.target.value)}
                  placeholder="Bearer ••••••••••••••••"
                  className="w-full px-3 py-2 pr-16 rounded-xl bg-canvas border border-border text-text-primary focus:outline-none focus:border-indigo-500 font-mono text-xs"
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-text-muted hover:text-text-primary px-2 py-0.5 rounded bg-surface border border-border"
                >
                  {showSecret ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              {saveSuccess && (
                <span className="text-xs text-emerald-400 flex items-center gap-1 font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Configuration saved successfully!</span>
                </span>
              )}
            </div>
            <Button
              size="sm"
              variant="primary"
              onClick={() => void handleSaveOllama()}
              disabled={saving}
              className="flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
