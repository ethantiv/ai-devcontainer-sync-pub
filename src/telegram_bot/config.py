"""Configuration from environment variables."""

import shutil
from os import environ
from pathlib import Path


def _safe_int(value: str | None, default: int) -> int:
    """Safely convert string to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _safe_float(value: str | None, default: float) -> float:
    """Safely convert string to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


TELEGRAM_BOT_TOKEN = environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _safe_int(environ.get("TELEGRAM_CHAT_ID"), 0)
PROJECTS_ROOT = environ.get("PROJECTS_ROOT", "/home/developer/projects")

# Configurable thresholds — override via environment variables
STALE_THRESHOLD = _safe_int(environ.get("LOOP_STALE_THRESHOLD"), 300)
BRAINSTORM_POLL_INTERVAL = _safe_float(
    environ.get("LOOP_BRAINSTORM_POLL_INTERVAL"), 0.5
)
BRAINSTORM_TIMEOUT = _safe_int(environ.get("LOOP_BRAINSTORM_TIMEOUT"), 300)
MAX_QUEUE_SIZE = _safe_int(environ.get("LOOP_MAX_QUEUE_SIZE"), 10)
GIT_DIFF_RANGE = environ.get("LOOP_GIT_DIFF_RANGE", "HEAD~5..HEAD")


def validate() -> tuple[list[str], list[str]]:
    """Validate environment configuration at startup.

    Returns:
        (errors, warnings) — errors are fatal (bot cannot start),
        warnings are informational (some features may not work).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- Fatal checks ---

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set or empty")

    raw_chat_id = environ.get("TELEGRAM_CHAT_ID")
    if raw_chat_id is None:
        errors.append("TELEGRAM_CHAT_ID is not set")
    else:
        try:
            chat_id_val = int(raw_chat_id)
            if chat_id_val == 0:
                errors.append("TELEGRAM_CHAT_ID must be a non-zero integer")
        except ValueError:
            errors.append(
                f"TELEGRAM_CHAT_ID is not a valid integer: {raw_chat_id!r}"
            )

    projects_path = Path(PROJECTS_ROOT)
    if not projects_path.exists():
        errors.append(f"PROJECTS_ROOT does not exist: {PROJECTS_ROOT}")
    elif not projects_path.is_dir():
        errors.append(f"PROJECTS_ROOT is not a directory: {PROJECTS_ROOT}")
    elif not _is_writable(projects_path):
        errors.append(f"PROJECTS_ROOT is not writable: {PROJECTS_ROOT}")

    # --- Warning checks (non-fatal) ---

    claude_home = Path.home() / ".claude" / "bin" / "claude"
    if not shutil.which("claude") and not claude_home.exists():
        warnings.append(
            "Claude CLI not found in PATH or at ~/.claude/bin/claude "
            "— task execution will not work"
        )

    if not shutil.which("tmux"):
        warnings.append(
            "tmux not found in PATH — task execution will not work"
        )

    loop_docker = Path("/opt/loop/scripts/loop.sh")
    if not shutil.which("loop") and not loop_docker.exists():
        warnings.append(
            "Loop script not found (/opt/loop/scripts/loop.sh or `loop` in PATH) "
            "— loop commands will not work, brainstorming still available"
        )

    return errors, warnings


def _is_writable(path: Path) -> bool:
    """Check if a directory is writable by attempting a temp file."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            return True
    except OSError:
        return False
