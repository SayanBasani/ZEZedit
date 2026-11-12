import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AIProviderManager } from '../features/providers/AIProviderManager';
import * as apiClient from '../services/apiClient';
import { AIProvider } from '../types/system';

const mockProviders: AIProvider[] = [
  {
    id: 'ollama',
    name: 'Ollama (Local LLM & Vision)',
    provider_type: 'local_llm',
    status: 'ready',
    is_local: true,
    base_url: 'http://127.0.0.1:11434',
    active_model: 'qwen3-vl:4b-instruct',
    available_models: ['qwen3-vl:4b-instruct', 'llama3:8b', 'mistral:7b'],
    capabilities: [
      { task: 'video_understanding', supported: true, description: 'Scene understanding' },
      { task: 'highlight_reasoning', supported: true, description: 'Viral moment analysis' },
    ],
    latency_ms: 18.5,
    last_health_check: '2026-11-12T00:00:00Z',
    details: 'Local Ollama running on port 11434',
  },
  {
    id: 'faster_whisper',
    name: 'Faster-Whisper (CPU Speech-to-Text)',
    provider_type: 'local_asr',
    status: 'ready',
    is_local: true,
    base_url: null,
    active_model: 'base.en',
    available_models: ['tiny.en', 'base.en', 'small.en', 'medium.en'],
    capabilities: [
      { task: 'speech_transcription', supported: true, description: 'Word timestamp generation' },
    ],
    latency_ms: 5.2,
    last_health_check: '2026-11-12T00:00:00Z',
    details: 'CTranslate2 INT8 quantization',
  },
  {
    id: 'rule_engine',
    name: 'Built-in Heuristic Engine (Offline)',
    provider_type: 'heuristic',
    status: 'ready',
    is_local: true,
    base_url: null,
    active_model: 'v1.0-deterministic',
    available_models: ['v1.0-deterministic'],
    capabilities: [
      { task: 'heuristic_fallback', supported: true, description: 'Zero dependency rules' },
    ],
    latency_ms: 0.1,
    last_health_check: '2026-11-12T00:00:00Z',
    details: 'Offline rule-based scoring',
  },
];

describe('Milestone 24: AIProviderManager Component Verification (ZEZ-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders provider list and displays latency metrics', async () => {
    vi.spyOn(apiClient, 'fetchAIProviders').mockResolvedValue(mockProviders);

    render(<AIProviderManager />);

    expect(await screen.findByText('AI Provider Manager')).toBeInTheDocument();
    expect(screen.getByText('Ollama (Local LLM & Vision)')).toBeInTheDocument();
    expect(screen.getByText('Faster-Whisper (CPU Speech-to-Text)')).toBeInTheDocument();
    expect(screen.getByText('Built-in Heuristic Engine (Offline)')).toBeInTheDocument();
    expect(screen.getByText('18.5 ms')).toBeInTheDocument();
  });

  it('allows testing provider connection and renders success test result', async () => {
    vi.spyOn(apiClient, 'fetchAIProviders').mockResolvedValue(mockProviders);
    const testSpy = vi.spyOn(apiClient, 'testAIProvider').mockResolvedValue({
      provider_id: 'ollama',
      reachable: true,
      latency_ms: 22.4,
      available_models: ['qwen3-vl:4b-instruct'],
      error: null,
    });

    render(<AIProviderManager />);

    await screen.findByText('Ollama (Local LLM & Vision)');

    const testButtons = screen.getAllByRole('button', { name: /Test Connection/i });
    fireEvent.click(testButtons[0]);

    await waitFor(() => {
      expect(testSpy).toHaveBeenCalledWith('ollama', 'http://127.0.0.1:11434');
      expect(screen.getByText(/Connected \(22\.4ms, 1 models\)/i)).toBeInTheDocument();
    });
  });

  it('allows updating Ollama endpoint configuration and shows save state', async () => {
    vi.spyOn(apiClient, 'fetchAIProviders').mockResolvedValue(mockProviders);
    const updateSpy = vi.spyOn(apiClient, 'updateAIProvider').mockResolvedValue({
      ...mockProviders[0],
      base_url: 'http://127.0.0.1:11435',
    });

    render(<AIProviderManager />);

    await screen.findByText('Ollama (Local LLM & Vision)');

    const urlInput = screen.getByPlaceholderText('http://127.0.0.1:11434') as HTMLInputElement;
    fireEvent.change(urlInput, { target: { value: 'http://127.0.0.1:11435' } });
    expect(urlInput.value).toBe('http://127.0.0.1:11435');

    const saveBtn = screen.getByRole('button', { name: /Save Configuration/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('ollama', {
        base_url: 'http://127.0.0.1:11435',
        active_model: 'qwen3-vl:4b-instruct',
      });
      expect(screen.getByText('Configuration saved successfully!')).toBeInTheDocument();
    });
  });

  it('toggles password visibility on secret token input field', async () => {
    vi.spyOn(apiClient, 'fetchAIProviders').mockResolvedValue(mockProviders);

    render(<AIProviderManager />);

    await screen.findByText('AI Provider Manager');

    const tokenInput = screen.getByPlaceholderText('Bearer ••••••••••••••••') as HTMLInputElement;
    expect(tokenInput.type).toBe('password');

    const toggleBtn = screen.getByRole('button', { name: /^Show$/i });
    fireEvent.click(toggleBtn);
    expect(tokenInput.type).toBe('text');

    fireEvent.click(screen.getByRole('button', { name: /^Hide$/i }));
    expect(tokenInput.type).toBe('password');
  });
});
