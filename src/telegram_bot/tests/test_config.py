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
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")):
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
            with patch.object(config.shutil, "which", return_value=None), \
                 patch.object(config.Path, "home", return_value=Path("/fake/home")):
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
