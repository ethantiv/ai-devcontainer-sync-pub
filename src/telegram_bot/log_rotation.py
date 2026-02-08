"""Log rotation and disk space management for loop projects.

Provides automatic cleanup of:
- JSONL log files in project loop/logs/ directories (by age and total size)
- Orphaned brainstorm JSONL files in PROJECTS_ROOT/.brainstorm/
- Disk space checks before starting new tasks
"""

import json
import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def rotate_logs(
    projects_root: Path | str,
    retention_days: int = 7,
    max_size_mb: float = 500,
) -> dict:
    """Delete old JSONL log files across all projects.

    Scans each project's loop/logs/ directory and removes JSONL files that
    are older than retention_days. Then, if total remaining size exceeds
    max_size_mb, deletes oldest files first until under the limit.

    Args:
        projects_root: Root directory containing project directories.
        retention_days: Delete JSONL files older than this many days.
        max_size_mb: Maximum total JSONL size in MB across all projects.

    Returns:
        {"deleted": int, "freed_bytes": int} summary of cleanup.
    """
    projects_root = Path(projects_root)
    deleted = 0
    freed_bytes = 0
    cutoff = time.time() - (retention_days * 86400)

    # Collect all JSONL log files across projects
    all_files: list[tuple[Path, float, int]] = []  # (path, mtime, size)

    for project_dir in _iter_project_dirs(projects_root):
        logs_dir = project_dir / "loop" / "logs"
        if not logs_dir.is_dir():
            continue
        for f in logs_dir.glob("*.jsonl"):
            try:
                stat = f.stat()
                all_files.append((f, stat.st_mtime, stat.st_size))
            except OSError:
                continue

    # Phase 1: delete files older than retention period
    remaining: list[tuple[Path, float, int]] = []
    for path, mtime, size in all_files:
        if mtime < cutoff:
            try:
                path.unlink()
                deleted += 1
                freed_bytes += size
                logger.info("Deleted old log: %s", path)
            except OSError:
                remaining.append((path, mtime, size))
        else:
            remaining.append((path, mtime, size))

    # Phase 2: if total size still exceeds limit, delete oldest first
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    total_size = sum(size for _, _, size in remaining)

    if total_size > max_size_bytes:
        # Sort by mtime ascending (oldest first)
        remaining.sort(key=lambda x: x[1])
        for path, _, size in remaining:
            if total_size <= max_size_bytes:
                break
            try:
                path.unlink()
                deleted += 1
                freed_bytes += size
                total_size -= size
                logger.info("Deleted log (size limit): %s", path)
            except OSError:
                continue

    return {"deleted": deleted, "freed_bytes": freed_bytes}


def cleanup_brainstorm_files(projects_root: Path | str) -> dict:
    """Remove orphaned brainstorm JSONL files not referenced by active sessions.

    Reads .brainstorm_sessions.json to find active chat_ids, then deletes
    any JSONL files in .brainstorm/ whose filename doesn't match an active session.

    Args:
        projects_root: Root directory containing .brainstorm/ and .brainstorm_sessions.json.

    Returns:
        {"deleted": int, "freed_bytes": int} summary of cleanup.
    """
    projects_root = Path(projects_root)
    brainstorm_dir = projects_root / ".brainstorm"
    deleted = 0
    freed_bytes = 0

    if not brainstorm_dir.is_dir():
        return {"deleted": 0, "freed_bytes": 0}

    # Load active chat_ids from sessions file
    active_chat_ids: set[str] = set()
    sessions_file = projects_root / ".brainstorm_sessions.json"
    if sessions_file.exists():
        try:
            data = json.loads(sessions_file.read_text())
            for entry in data:
                chat_id = entry.get("chat_id")
                if chat_id is not None:
                    active_chat_ids.add(str(chat_id))
        except (json.JSONDecodeError, OSError):
            # Corrupt file — treat all files as orphaned
            logger.warning("Corrupt brainstorm sessions file: %s", sessions_file)

    # Delete JSONL files not matching active sessions
    for f in brainstorm_dir.glob("*.jsonl"):
        # Filename format: brainstorm_{chat_id}_{uuid}.jsonl
        parts = f.stem.split("_")
        file_chat_id = parts[1] if len(parts) >= 3 else None

        if file_chat_id not in active_chat_ids:
            try:
                size = f.stat().st_size
                f.unlink()
                deleted += 1
                freed_bytes += size
                logger.info("Deleted orphaned brainstorm file: %s", f)
            except OSError:
                continue

    return {"deleted": deleted, "freed_bytes": freed_bytes}


def check_disk_space(
    path: Path | str,
    min_mb: int = 500,
) -> tuple[bool, float]:
    """Check if available disk space meets minimum threshold.

    Args:
        path: Path on the filesystem to check.
        min_mb: Minimum required free space in megabytes.

    Returns:
        (ok, available_mb) — ok is True when available >= min_mb.
    """
    try:
        usage = shutil.disk_usage(path)
        available_mb = usage.free / (1024 * 1024)
        return available_mb >= min_mb, available_mb
    except OSError:
        return False, 0.0


def _iter_project_dirs(projects_root: Path):
    """Yield immediate subdirectories of projects_root (project directories)."""
    if not projects_root.is_dir():
        return
    for entry in projects_root.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            yield entry
