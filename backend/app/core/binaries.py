"""Media executable discovery and health probing (FFmpeg / FFprobe)."""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BinaryStatus:
    """Status snapshot for an external CLI binary."""

    name: str
    available: bool
    path: Optional[str]
    version: Optional[str]
    details: Optional[str] = None


def probe_media_binary(binary_name: str, configured_path: str = "") -> BinaryStatus:
    """Probe availability and version line for ffmpeg or ffprobe safely without shell=True."""
    resolved = configured_path.strip() or shutil.which(binary_name)
    if not resolved:
        return BinaryStatus(
            name=binary_name,
            available=False,
            path=None,
            version=None,
            details=f"{binary_name} executable not found on PATH or configuration.",
        )

    try:
        proc = subprocess.run(
            [resolved, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        first_line = (proc.stdout or proc.stderr or "").splitlines()[0:1]
        version_text = first_line[0].strip() if first_line else "unknown"
        available = proc.returncode == 0
        return BinaryStatus(
            name=binary_name,
            available=available,
            path=resolved,
            version=version_text if available else None,
            details=None if available else f"Exited with code {proc.returncode}",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return BinaryStatus(
            name=binary_name,
            available=False,
            path=resolved,
            version=None,
            details=str(exc),
        )
