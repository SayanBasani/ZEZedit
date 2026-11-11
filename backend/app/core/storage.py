"""Managed storage directory layout separated cleanly by lifecycle and immutability."""

from dataclasses import dataclass
from pathlib import Path

from app.core.security import validate_storage_root_path


@dataclass(frozen=True)
class StorageLayout:
    """Resolved storage subdirectories under the validated ZEZEDIT_STORAGE_ROOT."""

    root: Path
    db: Path
    media: Path
    proxies: Path
    thumbnails: Path
    analysis: Path
    timelines: Path
    shorts: Path
    exports: Path
    temp: Path
    backups: Path
    logs: Path

    @classmethod
    def from_root(cls, storage_root: Path) -> "StorageLayout":
        validated_root = validate_storage_root_path(storage_root)
        return cls(
            root=validated_root,
            db=validated_root / "db",
            media=validated_root / "media",
            proxies=validated_root / "proxies",
            thumbnails=validated_root / "thumbnails",
            analysis=validated_root / "analysis",
            timelines=validated_root / "timelines",
            shorts=validated_root / "shorts",
            exports=validated_root / "exports",
            temp=validated_root / "temp",
            backups=validated_root / "backups",
            logs=validated_root / "logs",
        )

    def ensure_directories(self) -> None:
        """Create all managed directories if missing."""
        for folder in (
            self.root,
            self.db,
            self.media,
            self.proxies,
            self.thumbnails,
            self.analysis,
            self.timelines,
            self.shorts,
            self.exports,
            self.temp,
            self.backups,
            self.logs,
        ):
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def db_file(self) -> Path:
        return self.db / "zezedit.db"
