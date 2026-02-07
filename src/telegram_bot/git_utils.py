"""Git and plan utilities for task completion summaries."""

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_commit_hash(project_path: Path) -> str | None:
    """Return current HEAD short hash, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_diff_stats(project_path: Path, since_commit: str) -> dict | None:
    """Return diff stats {files_changed, insertions, deletions} since a commit.

    Returns None if git command fails or no changes detected.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "--numstat", f"{since_commit}..HEAD"],
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        files_changed = 0
        insertions = 0
        deletions = 0
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    insertions += ins
                    deletions += dels
                    files_changed += 1
                except ValueError:
                    continue

        if files_changed == 0:
            return None

        return {
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        }
    except (subprocess.TimeoutExpired, OSError):
        return None


def get_recent_commits(
    project_path: Path, since_commit: str, max_count: int = 5
) -> list[str]:
    """Return commit subject lines since a commit (newest first)."""
    try:
        result = subprocess.run(
            [
                "git", "log", "--oneline",
                f"--max-count={max_count}",
                f"{since_commit}..HEAD",
            ],
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
    except (subprocess.TimeoutExpired, OSError):
        pass
    return []


def get_plan_progress(project_path: Path) -> tuple[int, int] | None:
    """Parse IMPLEMENTATION_PLAN.md for checkbox ratio [x] vs [ ].

    Returns (completed, total) or None if file not found or no checkboxes.
    """
    plan_file = project_path / "docs" / "plans" / "IMPLEMENTATION_PLAN.md"
    if not plan_file.exists():
        return None

    try:
        content = plan_file.read_text()
    except OSError:
        return None

    checked = len(re.findall(r"- \[x\]", content, re.IGNORECASE))
    unchecked = len(re.findall(r"- \[ \]", content))
    total = checked + unchecked

    if total == 0:
        return None

    return (checked, total)
