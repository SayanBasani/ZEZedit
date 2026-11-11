"""Application settings management service with secret redaction and schema persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app.core.config import Settings
from app.db.connection import sqlite_session
from app.schemas.core import AppSettingsDTO

DEFAULT_SETTINGS_KEY = "system_settings"


class SettingsService:
    """Manages application settings in SQLite with secret redaction for API outputs."""

    def __init__(self, settings: Settings, db_path: Path) -> None:
        self.settings = settings
        self.db_path = db_path

    def get_settings(self) -> AppSettingsDTO:
        """Fetch settings from DB or construct sensible defaults."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT value_json FROM app_settings WHERE key = ?",
                (DEFAULT_SETTINGS_KEY,),
            ).fetchone()
            if row and row["value_json"]:
                data = json.loads(row["value_json"])
                return AppSettingsDTO(**data)

        # Fallback to configured defaults
        default_dto = AppSettingsDTO(
            storage_root=str(self.settings.storage_root),
            temporary_storage_location=str(self.settings.storage_root / "temp"),
            proxy_resolution="480p",
            proxy_generate_on_import=True,
            cpu_processing_limits={
                "max_threads": self.settings.ffmpeg_threads,
                "max_concurrent_jobs": self.settings.max_concurrent_jobs,
            },
            memory_limits_mb=self.settings.max_memory_mb,
            ai_provider_config={"ollama_base_url": self.settings.ollama_base_url},
            model_preferences={"default_vision_model": self.settings.default_model},
            default_export_preferences={"resolution": "1080x1920", "codec": "libx264"},
            application_appearance={"theme": "dark"},
        )
        self.save_settings(default_dto)
        return default_dto

    def update_settings(self, updates: Dict[str, Any]) -> AppSettingsDTO:
        """Update individual settings fields safely and redact any secrets."""
        current = self.get_settings()
        curr_dict = current.model_dump()

        for k, v in updates.items():
            if v is not None and k in curr_dict:
                if isinstance(curr_dict[k], dict) and isinstance(v, dict):
                    curr_dict[k].update(v)
                else:
                    curr_dict[k] = v

        # Redact any accidental API key or secret entries from public fields
        self._sanitize_secrets(curr_dict)

        updated_dto = AppSettingsDTO(**curr_dict)
        self.save_settings(updated_dto)
        return updated_dto

    def save_settings(self, dto: AppSettingsDTO) -> None:
        """Persist settings JSON to SQLite app_settings."""
        now = datetime.now(timezone.utc).isoformat()
        payload = dto.model_dump()
        self._sanitize_secrets(payload)

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (DEFAULT_SETTINGS_KEY, json.dumps(payload), now),
            )

    def _sanitize_secrets(self, data: dict) -> None:
        """Ensure no raw password, token, or secret strings are stored in unhashed/plaintext logs."""
        sensitive_keys = {"api_key", "secret", "password", "token", "authorization"}
        for k in list(data.keys()):
            if any(s in k.lower() for s in sensitive_keys):
                data[k] = "[REDACTED]"
            elif isinstance(data[k], dict):
                self._sanitize_secrets(data[k])
