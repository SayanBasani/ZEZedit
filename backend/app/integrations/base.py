"""Protocol interfaces for AI providers (Ollama, VLM, STT, future providers)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class ProviderHealth:
    """Standardized provider availability snapshot."""

    provider_name: str
    reachable: bool
    base_url: Optional[str] = None
    models: List[str] = field(default_factory=list)
    details: Optional[str] = None


class TextLLMProvider(Protocol):
    """Contract for structured local or remote text LLM inference."""

    async def probe_health(self) -> ProviderHealth: ...


class VisionLanguageProvider(Protocol):
    """Contract for sampled video-frame vision-language inference."""

    async def probe_health(self) -> ProviderHealth: ...


class SpeechToTextProvider(Protocol):
    """Contract for local speech transcription engines (e.g., Faster-Whisper)."""

    async def probe_health(self) -> ProviderHealth: ...


@dataclass(frozen=True)
class StructuredPlanResult:
    """Container for schema-validated LLM outputs separating planning from execution."""

    raw_text: str
    parsed_payload: Dict[str, Any]
