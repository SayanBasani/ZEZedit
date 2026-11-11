"""Path containment, storage root validation, and anti-root-deletion safety guards."""

import os
import shutil
from pathlib import Path

from app.core.errors import (
    BoundaryViolationError,
    RootDeletionForbiddenError,
    UnsafeStorageRootError,
)

PROTECTED_BUCKET_NAMES = frozenset(
    {
        "db",
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
    }
)


def validate_storage_root_path(storage_root: Path) -> Path:
    """
    Validate that the configured storage root is a dedicated subdirectory
    and never a drive root, OS folder, or home directory root.
    """
    resolved = Path(storage_root).expanduser().resolve(strict=False)

    # Reject drive roots such as C:\, D:\, or POSIX /
    if len(resolved.parts) <= 1 or resolved == Path(resolved.anchor):
        raise UnsafeStorageRootError(
            f"Storage root '{resolved}' cannot be a filesystem or drive root."
        )

    # Reject home directory directly
    home = Path.home().resolve(strict=False)
    if resolved == home:
        raise UnsafeStorageRootError(
            f"Storage root '{resolved}' cannot be the user home directory root."
        )

    # Reject Windows OS protected paths
    lowered = str(resolved).lower().rstrip("\\/")
    forbidden_prefixes = [
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
        "c:\\programdata",
    ]
    for prefix in forbidden_prefixes:
        if lowered == prefix or lowered.startswith(prefix + "\\"):
            raise UnsafeStorageRootError(
                f"Storage root '{resolved}' cannot reside inside protected OS path '{prefix}'."
            )

    return resolved


def resolve_contained_path(base_dir: Path, relative_or_child: str | Path) -> Path:
    """
    Resolve a candidate path and guarantee it resides strictly inside `base_dir`.
    Rejects directory traversal (`..`), NUL bytes, and cross-boundary targets.
    """
    raw = str(relative_or_child)
    if "\x00" in raw or not raw.strip():
        raise BoundaryViolationError("Invalid empty or malformed target path.")

    resolved_base = Path(base_dir).resolve(strict=False)
    candidate_input = Path(relative_or_child)

    if candidate_input.is_absolute():
        resolved_target = candidate_input.resolve(strict=False)
    else:
        resolved_target = (resolved_base / candidate_input).resolve(strict=False)

    if resolved_target == resolved_base:
        raise BoundaryViolationError(
            f"Target path '{resolved_target}' resolves to the container root itself."
        )

    if not resolved_target.is_relative_to(resolved_base):
        raise BoundaryViolationError(
            f"Target path '{resolved_target}' escapes permitted boundary '{resolved_base}'."
        )

    return resolved_target


def is_path_confined(candidate: str | Path, base_dir: str | Path) -> bool:
    """Return True if candidate path resides within base_dir, False otherwise."""
    try:
        resolved_base = Path(base_dir).resolve(strict=False)
        resolved_target = Path(candidate).resolve(strict=False)
        return resolved_target.is_relative_to(resolved_base)
    except (ValueError, OSError):
        return False


def safe_delete_directory(
    target_dir: Path,
    allowed_parent: Path,
    storage_root: Path,
) -> None:
    """
    Recursively delete an owned child subdirectory inside `allowed_parent`.
    Structurally prevents deleting `storage_root`, drive roots, or top-level buckets.
    """
    resolved_root = validate_storage_root_path(storage_root)
    resolved_parent = Path(allowed_parent).resolve(strict=False)
    resolved_target = resolve_contained_path(resolved_parent, target_dir)

    if resolved_target == resolved_root:
        raise RootDeletionForbiddenError("Deleting the storage root is strictly forbidden.")

    # Never permit deleting a top-level bucket (e.g., storage/media or storage/temp)
    if resolved_target.parent == resolved_root and resolved_target.name in PROTECTED_BUCKET_NAMES:
        raise RootDeletionForbiddenError(
            f"Deleting protected storage bucket '{resolved_target.name}' is strictly forbidden."
        )

    if os.path.islink(resolved_target):
        raise RootDeletionForbiddenError(
            f"Refusing recursive deletion across symbolic link '{resolved_target}'."
        )

    if resolved_target.exists() and resolved_target.is_dir():
        shutil.rmtree(resolved_target)
