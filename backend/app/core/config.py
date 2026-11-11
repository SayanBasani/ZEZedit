"""Application configuration managed via Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Typed application runtime configuration loaded from env and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="ZEZEDIT_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ZezEdit"
    app_version: str = "2.0.0-alpha.1"
    environment: str = "development"
    debug: bool = False

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    storage_root: Path = Field(default_factory=lambda: PROJECT_ROOT / "storage")

    ffmpeg_path: str = ""
    ffprobe_path: str = ""

    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3-vl:4b-instruct"
    ollama_timeout_seconds: float = 8.0

    max_concurrent_jobs: int = 1
    ffmpeg_threads: int = 4
    max_memory_mb: int = 8192

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        """Return trimmed list of permitted CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def migrations_dir(self) -> Path:
        """Return path to numbered SQL migration files."""
        return BACKEND_ROOT / "migrations"


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings instance."""
    return Settings()
