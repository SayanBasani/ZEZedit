"""Visual understanding for sampled frames using local Ollama (qwen3-vl:4b-instruct) with heuristic fallback."""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("zezedit.visual_understanding")


@dataclass
class VisualObservation:
    timestamp: float
    frame_id: Optional[str]
    category: str  # scene_setting, subjects, activity, on_screen_text, aesthetic_note
    description: str
    provider_model: str
    confidence: float = 1.0


def _encode_image_b64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


class OllamaVisionAnalyzer:
    """Queries local Ollama qwen3-vl:4b-instruct for frame visual understanding."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3-vl:4b-instruct",
        timeout_seconds: float = 12.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._disabled = False

    def reset(self) -> None:
        """Reset disabled state for a new analysis run."""
        self._disabled = False

    async def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        if self._disabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def analyze_frame(
        self,
        image_path: Path,
        timestamp: float,
        frame_id: Optional[str] = None,
    ) -> List[VisualObservation]:
        """Send frame to Ollama vision model and return structured observations."""
        if not image_path.exists():
            return []

        if self._disabled:
            return self._heuristic_fallback(image_path, timestamp, frame_id)

        prompt = (
            "Analyze this single video frame conservatively and factually. "
            "Report only what is clearly visible without guessing continuous motion or identity. "
            "Respond in 3 brief bullet points:\n"
            "- Scene setting (environment, indoor/outdoor, lighting)\n"
            "- Visible subjects (number of people, general posture)\n"
            "- Prominent objects or visible text"
        )

        b64_img = _encode_image_b64(image_path)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_img],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 150,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "").strip()
                    if response_text:
                        return self._parse_response(response_text, timestamp, frame_id)
        except Exception as exc:
            logger.warning("Ollama vision analysis request failed: %s; using fast heuristic fallback for remaining frames", exc)
            self._disabled = True

        # Graceful fallback when Ollama is offline or errors
        return self._heuristic_fallback(image_path, timestamp, frame_id)

    def _parse_response(
        self,
        text: str,
        timestamp: float,
        frame_id: Optional[str],
    ) -> List[VisualObservation]:
        observations: List[VisualObservation] = []
        lines = [line.strip().lstrip("-*• ") for line in text.splitlines() if line.strip()]

        for line in lines:
            lower = line.lower()
            category = "activity"
            if any(k in lower for k in ("scene", "setting", "environment", "indoor", "outdoor", "room", "lighting")):
                category = "scene_setting"
            elif any(k in lower for k in ("subject", "person", "people", "man", "woman", "face", "posture")):
                category = "subjects"
            elif any(k in lower for k in ("text", "sign", "title", "caption", "word", "letter", "overlay")):
                category = "on_screen_text"

            observations.append(
                VisualObservation(
                    timestamp=timestamp,
                    frame_id=frame_id,
                    category=category,
                    description=line,
                    provider_model=self.model,
                    confidence=0.85,
                )
            )

        if not observations:
            observations.append(
                VisualObservation(
                    timestamp=timestamp,
                    frame_id=frame_id,
                    category="scene_setting",
                    description=text[:200],
                    provider_model=self.model,
                    confidence=0.8,
                )
            )

        return observations

    def _heuristic_fallback(
        self,
        image_path: Path,
        timestamp: float,
        frame_id: Optional[str],
    ) -> List[VisualObservation]:
        """Deterministic heuristic fallback when local AI vision is unavailable."""
        size_kb = image_path.stat().st_size / 1024.0
        return [
            VisualObservation(
                timestamp=timestamp,
                frame_id=frame_id,
                category="scene_setting",
                description=f"Visual frame captured (file size: {size_kb:.1f} KB). AI vision service offline; heuristic baseline applied.",
                provider_model="heuristic_fallback",
                confidence=0.5,
            )
        ]
