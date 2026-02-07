"""Shared fixtures for telegram_bot tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_projects_root(tmp_path):
    """Create a temporary PROJECTS_ROOT directory."""
    projects = tmp_path / "projects"
    projects.mkdir()
    return projects


@pytest.fixture
def env_with_valid_config(tmp_projects_root):
    """Environment dict with all required config values set correctly."""
    return {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
        "TELEGRAM_CHAT_ID": "12345",
        "PROJECTS_ROOT": str(tmp_projects_root),
    }
