"""Non-blocking Ollama health and dynamic model inventory client."""

import httpx

from app.integrations.base import ProviderHealth


class OllamaProvider:
    """Thin Ollama HTTP probe returning authoritative `/api/tags` inventory."""

    def __init__(self, base_url: str, timeout_seconds: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def probe_health(self) -> ProviderHealth:
        """Check Ollama reachability and list currently installed models dynamically."""
        tags_url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(tags_url)
                response.raise_for_status()
                payload = response.json()

            raw_models = payload.get("models", [])
            model_names = [
                str(item["name"])
                for item in raw_models
                if isinstance(item, dict) and item.get("name")
            ]
            return ProviderHealth(
                provider_name="ollama",
                reachable=True,
                base_url=self.base_url,
                models=model_names,
                details=f"Detected {len(model_names)} installed model(s).",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="ollama",
                reachable=False,
                base_url=self.base_url,
                models=[],
                details=f"Ollama unreachable: {exc}",
            )
