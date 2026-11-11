"""Storage manager service for path validation, storage inspection, and safe operations."""

import os
import shutil
from pathlib import Path
from typing import Dict

from app.core.config import Settings
from app.core.security import resolve_contained_path, validate_storage_root_path
from app.core.storage import StorageLayout


class StorageService:
    """Manages files, disk space, directory validation, and boundary safety."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.layout = StorageLayout.from_root(settings.storage_root)

    def inspect_storage(self) -> Dict[str, any]:
        """Inspect directory accessibility, total/free disk space, and category sizes."""
        root = self.layout.root
        accessible = root.exists() and os.access(root, os.R_OK)
        writable = accessible and os.access(root, os.W_OK)

        total, used, free = 0, 0, 0
        if accessible:
            try:
                usage = shutil.disk_usage(root)
                total, used, free = usage.total, usage.used, usage.free
            except OSError:
                pass

        # Calculate category folder sizes
        category_sizes: Dict[str, int] = {}
        for folder_name in [
            "media",
            "proxies",
            "thumbnails",
            "analysis",
            "timelines",
            "shorts",
            "exports",
            "temp",
            "backups",
            "logs",
            "db",
        ]:
            folder_path: Path = getattr(self.layout, folder_name)
            size = 0
            if folder_path.exists():
                try:
                    for f in folder_path.rglob("*"):
                        if f.is_file() and not f.is_symlink():
                            size += f.stat().st_size
                except OSError:
                    pass
            category_sizes[folder_name] = size

        return {
            "storage_root": str(root),
            "is_accessible": accessible,
            "is_writable": writable,
            "total_space_bytes": total,
            "free_space_bytes": free,
            "used_space_bytes": used,
            "directories": {
                "media": str(self.layout.media),
                "proxies": str(self.layout.proxies),
                "thumbnails": str(self.layout.thumbnails),
                "analysis": str(self.layout.analysis),
                "timelines": str(self.layout.timelines),
                "shorts": str(self.layout.shorts),
                "exports": str(self.layout.exports),
                "temp": str(self.layout.temp),
                "backups": str(self.layout.backups),
                "logs": str(self.layout.logs),
                "db": str(self.layout.db),
            },
            "category_sizes_bytes": category_sizes,
        }

    def validate_external_path(self, path_str: str) -> Path:
        """Validate an external media reference exists and is readable."""
        resolved = Path(path_str).expanduser().resolve(strict=False)
        if not resolved.exists():
            raise FileNotFoundError(f"Media file not found at '{resolved}'.")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Media file at '{resolved}' is not readable.")
        return resolved
