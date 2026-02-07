"""Configuration from environment variables."""

from os import environ


def _safe_int(value: str | None, default: int) -> int:
    """Safely convert string to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


TELEGRAM_BOT_TOKEN = environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _safe_int(environ.get("TELEGRAM_CHAT_ID"), 0)
PROJECTS_ROOT = environ.get("PROJECTS_ROOT", "/home/developer/projects")
