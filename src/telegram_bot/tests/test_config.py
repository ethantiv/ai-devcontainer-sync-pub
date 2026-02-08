"""Tests for config.py — startup validation.

Tests the validate() function that checks environment variables and tool
availability at bot startup. Fatal errors prevent bot start; warnings are
logged but don't block startup.
"""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _reload_and_validate(env: dict):
    """Reload config with patched env, call validate() in same context.

    Both module-level constants and validate()'s runtime environ reads
    see the patched environment because we stay inside the context manager.
    """
    with patch.dict(os.environ, env, clear=True):
        from src.telegram_bot import config
        importlib.reload(config)
        return config.validate()


def _reload_config(env: dict):
    """Reload config with patched env and return the module.

    Caller must be inside the patch.dict context.
    """
    from src.telegram_bot import config
    importlib.reload(config)
    return config


class TestValidateToken:
    """TELEGRAM_BOT_TOKEN validation — fatal if missing."""

    def test_missing_token_is_fatal(self, tmp_projects_root):
        env = {
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert any("TELEGRAM_BOT_TOKEN" in e for e in errors)

    def test_empty_token_is_fatal(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert any("TELEGRAM_BOT_TOKEN" in e for e in errors)

    def test_valid_token_passes(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert not any("TELEGRAM_BOT_TOKEN" in e for e in errors)


class TestValidateChatId:
    """TELEGRAM_CHAT_ID validation — fatal if missing/invalid/zero."""

    def test_missing_chat_id_is_fatal(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert any("TELEGRAM_CHAT_ID" in e for e in errors)

    def test_zero_chat_id_is_fatal(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "0",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert any("TELEGRAM_CHAT_ID" in e for e in errors)

    def test_non_numeric_chat_id_is_fatal(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "abc",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert any("TELEGRAM_CHAT_ID" in e for e in errors)

    def test_valid_chat_id_passes(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "12345",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert not any("TELEGRAM_CHAT_ID" in e for e in errors)

    def test_negative_chat_id_passes(self, tmp_projects_root):
        """Negative chat IDs are valid (group chats)."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "-100123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert not any("TELEGRAM_CHAT_ID" in e for e in errors)


class TestValidateProjectsRoot:
    """PROJECTS_ROOT validation — fatal if not existing/writable."""

    def test_nonexistent_dir_is_fatal(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": "/nonexistent/path/xyz",
        }
        errors, _ = _reload_and_validate(env)
        assert any("PROJECTS_ROOT" in e for e in errors)

    def test_file_instead_of_dir_is_fatal(self, tmp_path):
        a_file = tmp_path / "notadir"
        a_file.write_text("hello")
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(a_file),
        }
        errors, _ = _reload_and_validate(env)
        assert any("PROJECTS_ROOT" in e for e in errors)

    def test_valid_dir_passes(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        errors, _ = _reload_and_validate(env)
        assert not any("PROJECTS_ROOT" in e for e in errors)


class TestValidateTools:
    """Tool availability checks — warnings only, not fatal."""

    def test_missing_claude_cli_is_warning(self, tmp_projects_root):
        """When claude is not in PATH and not at ~/.claude/bin/claude, warn."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")):
                errors, warnings = config.validate()
        assert any("claude" in w.lower() for w in warnings)
        # Tool checks are warnings, not errors
        assert not any("claude" in e.lower() for e in errors)

    def test_claude_in_path_no_warning(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            with patch.object(config.shutil, "which",
                              side_effect=lambda x: "/usr/bin/claude" if x == "claude" else None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")):
                errors, warnings = config.validate()
        assert not any("claude" in w.lower() for w in warnings)

    def test_missing_tmux_is_warning(self, tmp_projects_root):
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")):
                errors, warnings = config.validate()
        assert any("tmux" in w.lower() for w in warnings)
        assert not any("tmux" in e.lower() for e in errors)

    def test_missing_loop_is_warning(self, tmp_projects_root):
        """Loop script missing should warn, not fail."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            # Mock Path.home (for claude check) and loop_docker.exists()
            # so the loop warning triggers even when /opt/loop exists on host
            orig_exists = Path.exists
            def fake_exists(self):
                if str(self) == "/opt/loop/scripts/loop.sh":
                    return False
                return orig_exists(self)
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")), \
                 patch.object(Path, "exists", fake_exists):
                errors, warnings = config.validate()
        assert any("loop" in w.lower() for w in warnings)
        assert not any("loop" in e.lower() for e in errors)

    def test_tools_are_never_fatal(self, tmp_projects_root):
        """Even when all tools are missing, no errors — only warnings."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            orig_exists = Path.exists
            def fake_exists(self):
                if str(self) == "/opt/loop/scripts/loop.sh":
                    return False
                return orig_exists(self)
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")), \
                 patch.object(Path, "exists", fake_exists):
                errors, warnings = config.validate()
        assert errors == []
        assert len(warnings) == 3  # claude, tmux, loop


class TestValidateReturnType:
    """validate() returns (errors: list[str], warnings: list[str])."""

    def test_all_valid_returns_empty(self, env_with_valid_config):
        """When all config is valid and all tools are available, no issues."""
        with patch.dict(os.environ, env_with_valid_config, clear=True):
            config = _reload_config(env_with_valid_config)
            with patch.object(config.shutil, "which",
                              side_effect=lambda x: f"/usr/bin/{x}"), \
                 patch.object(Path, "exists", return_value=True):
                errors, warnings = config.validate()
        assert errors == []
        assert warnings == []

    def test_multiple_errors(self):
        """Missing token AND chat_id AND bad PROJECTS_ROOT = 3 errors."""
        env = {"PROJECTS_ROOT": "/nonexistent/xyz"}
        errors, _ = _reload_and_validate(env)
        assert len(errors) >= 3


class TestConfigurableThresholds:
    """Configurable threshold constants parsed from environment variables.

    Each threshold reads an env var with a sensible default. Invalid values
    (non-numeric strings) fall back to the default silently.
    """

    def test_stale_threshold_default(self, tmp_projects_root):
        """STALE_THRESHOLD defaults to 1800 when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.STALE_THRESHOLD == 1800

    def test_stale_threshold_from_env(self, tmp_projects_root):
        """STALE_THRESHOLD reads LOOP_STALE_THRESHOLD env var."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_STALE_THRESHOLD": "600",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.STALE_THRESHOLD == 600

    def test_stale_threshold_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_STALE_THRESHOLD falls back to 1800."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_STALE_THRESHOLD": "not_a_number",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.STALE_THRESHOLD == 1800

    def test_brainstorm_poll_interval_default(self, tmp_projects_root):
        """BRAINSTORM_POLL_INTERVAL defaults to 0.5."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_POLL_INTERVAL == 0.5

    def test_brainstorm_poll_interval_from_env(self, tmp_projects_root):
        """BRAINSTORM_POLL_INTERVAL reads LOOP_BRAINSTORM_POLL_INTERVAL."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_BRAINSTORM_POLL_INTERVAL": "1.5",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_POLL_INTERVAL == 1.5

    def test_brainstorm_poll_interval_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_BRAINSTORM_POLL_INTERVAL falls back to 0.5."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_BRAINSTORM_POLL_INTERVAL": "abc",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_POLL_INTERVAL == 0.5

    def test_brainstorm_timeout_default(self, tmp_projects_root):
        """BRAINSTORM_TIMEOUT defaults to 300."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_TIMEOUT == 300

    def test_brainstorm_timeout_from_env(self, tmp_projects_root):
        """BRAINSTORM_TIMEOUT reads LOOP_BRAINSTORM_TIMEOUT."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_BRAINSTORM_TIMEOUT": "120",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_TIMEOUT == 120

    def test_brainstorm_timeout_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_BRAINSTORM_TIMEOUT falls back to 300."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_BRAINSTORM_TIMEOUT": "",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.BRAINSTORM_TIMEOUT == 300

    def test_max_queue_size_default(self, tmp_projects_root):
        """MAX_QUEUE_SIZE defaults to 10."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MAX_QUEUE_SIZE == 10

    def test_max_queue_size_from_env(self, tmp_projects_root):
        """MAX_QUEUE_SIZE reads LOOP_MAX_QUEUE_SIZE."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_MAX_QUEUE_SIZE": "20",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MAX_QUEUE_SIZE == 20

    def test_max_queue_size_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_MAX_QUEUE_SIZE falls back to 10."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_MAX_QUEUE_SIZE": "lots",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MAX_QUEUE_SIZE == 10

    def test_queue_ttl_default(self, tmp_projects_root):
        """QUEUE_TTL defaults to 3600 when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.QUEUE_TTL == 3600

    def test_queue_ttl_from_env(self, tmp_projects_root):
        """QUEUE_TTL reads LOOP_QUEUE_TTL env var."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_QUEUE_TTL": "7200",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.QUEUE_TTL == 7200

    def test_queue_ttl_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_QUEUE_TTL falls back to 3600."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_QUEUE_TTL": "forever",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.QUEUE_TTL == 3600

    def test_git_diff_range_default(self, tmp_projects_root):
        """GIT_DIFF_RANGE defaults to 'HEAD~5..HEAD'."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.GIT_DIFF_RANGE == "HEAD~5..HEAD"

    def test_git_diff_range_from_env(self, tmp_projects_root):
        """GIT_DIFF_RANGE reads LOOP_GIT_DIFF_RANGE."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_GIT_DIFF_RANGE": "HEAD~10..HEAD",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.GIT_DIFF_RANGE == "HEAD~10..HEAD"


class TestIsTruthy:
    """_is_truthy() helper — parses boolean env var values.

    Accepts 'true', '1', 'yes' (case-insensitive) as True.
    Everything else (including empty string and None) is False.
    """

    def test_true_lowercase(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("true") is True

    def test_true_uppercase(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("TRUE") is True

    def test_true_mixed_case(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("True") is True

    def test_one(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("1") is True

    def test_yes_lowercase(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("yes") is True

    def test_yes_mixed_case(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("Yes") is True

    def test_false_lowercase(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("false") is False

    def test_zero(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("0") is False

    def test_empty_string(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("") is False

    def test_none(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy(None) is False

    def test_random_string(self):
        from src.telegram_bot.config import _is_truthy
        assert _is_truthy("banana") is False


class TestDevMode:
    """DEV_MODE config variable — disables Telegram bot in dev containers.

    When DEV_MODE is set to a truthy value (true/1/yes), the bot should
    not start. validate() should include a warning about dev mode.
    """

    def test_dev_mode_default_false(self, tmp_projects_root):
        """DEV_MODE defaults to False when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.DEV_MODE is False

    def test_dev_mode_true_from_env(self, tmp_projects_root):
        """DEV_MODE is True when DEV_MODE=true is set."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "DEV_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.DEV_MODE is True

    def test_dev_mode_one_from_env(self, tmp_projects_root):
        """DEV_MODE is True when DEV_MODE=1 is set."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "DEV_MODE": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.DEV_MODE is True

    def test_dev_mode_false_from_env(self, tmp_projects_root):
        """DEV_MODE is False when DEV_MODE=false is set."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "DEV_MODE": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.DEV_MODE is False

    def test_dev_mode_validate_warning(self, tmp_projects_root):
        """validate() returns a warning when DEV_MODE is active."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
            "DEV_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            with patch.object(config.shutil, "which",
                              side_effect=lambda x: f"/usr/bin/{x}"), \
                 patch.object(Path, "exists", return_value=True):
                errors, warnings = config.validate()
        assert any("DEV_MODE" in w for w in warnings)
        # Dev mode is a warning, not an error
        assert not any("DEV_MODE" in e for e in errors)

    def test_dev_mode_off_no_warning(self, tmp_projects_root):
        """validate() has no DEV_MODE warning when it's not set."""
        env = {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "123",
            "PROJECTS_ROOT": str(tmp_projects_root),
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            with patch.object(config.shutil, "which",
                              side_effect=lambda x: f"/usr/bin/{x}"), \
                 patch.object(Path, "exists", return_value=True):
                errors, warnings = config.validate()
        assert not any("DEV_MODE" in w for w in warnings)


class TestLogRotationConfig:
    """Log rotation config constants parsed from environment variables.

    Three constants for log management: retention by age, max total size,
    and minimum free disk space threshold.
    """

    def test_log_retention_days_default(self, tmp_projects_root):
        """LOG_RETENTION_DAYS defaults to 7 when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_RETENTION_DAYS == 7

    def test_log_retention_days_from_env(self, tmp_projects_root):
        """LOG_RETENTION_DAYS reads LOOP_LOG_RETENTION_DAYS env var."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_LOG_RETENTION_DAYS": "14",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_RETENTION_DAYS == 14

    def test_log_retention_days_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_LOG_RETENTION_DAYS falls back to 7."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_LOG_RETENTION_DAYS": "forever",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_RETENTION_DAYS == 7

    def test_log_max_size_mb_default(self, tmp_projects_root):
        """LOG_MAX_SIZE_MB defaults to 500 when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_MAX_SIZE_MB == 500

    def test_log_max_size_mb_from_env(self, tmp_projects_root):
        """LOG_MAX_SIZE_MB reads LOOP_LOG_MAX_SIZE_MB env var."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_LOG_MAX_SIZE_MB": "1000",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_MAX_SIZE_MB == 1000

    def test_log_max_size_mb_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_LOG_MAX_SIZE_MB falls back to 500."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_LOG_MAX_SIZE_MB": "big",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.LOG_MAX_SIZE_MB == 500

    def test_min_disk_mb_default(self, tmp_projects_root):
        """MIN_DISK_MB defaults to 500 when env var is not set."""
        env = {"PROJECTS_ROOT": str(tmp_projects_root)}
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MIN_DISK_MB == 500

    def test_min_disk_mb_from_env(self, tmp_projects_root):
        """MIN_DISK_MB reads LOOP_MIN_DISK_MB env var."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_MIN_DISK_MB": "1000",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MIN_DISK_MB == 1000

    def test_min_disk_mb_invalid_falls_back(self, tmp_projects_root):
        """Non-numeric LOOP_MIN_DISK_MB falls back to 500."""
        env = {
            "PROJECTS_ROOT": str(tmp_projects_root),
            "LOOP_MIN_DISK_MB": "plenty",
        }
        with patch.dict(os.environ, env, clear=True):
            config = _reload_config(env)
            assert config.MIN_DISK_MB == 500


class TestRequirementsTxt:
    """requirements.txt exists and declares python-telegram-bot dependency.

    Ensures the requirements file used by Dockerfile is present and pins
    the correct version range for python-telegram-bot with job-queue extra.
    """

    REQUIREMENTS_PATH = (
        Path(__file__).resolve().parent.parent / "requirements.txt"
    )

    def test_file_exists(self):
        """requirements.txt must exist alongside the telegram_bot package."""
        assert self.REQUIREMENTS_PATH.is_file(), (
            f"Missing {self.REQUIREMENTS_PATH}"
        )

    def test_contains_python_telegram_bot(self):
        """requirements.txt must declare python-telegram-bot[job-queue]."""
        content = self.REQUIREMENTS_PATH.read_text()
        assert "python-telegram-bot[job-queue]" in content

    def test_version_pinned(self):
        """Version must be pinned to >=21.0,<22.0 to match v21 API."""
        content = self.REQUIREMENTS_PATH.read_text()
        assert ">=21.0" in content
        assert "<22.0" in content
