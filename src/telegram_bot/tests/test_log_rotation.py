"""Tests for log_rotation.py — log file cleanup and disk space management.

Tests cover three main functions:
- rotate_logs(): delete JSONL files older than retention period or exceeding size limit
- cleanup_brainstorm_files(): remove orphaned brainstorm JSONL files
- check_disk_space(): verify available disk space meets minimum threshold
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


class TestRotateLogs:
    """rotate_logs() scans loop/logs/ dirs and removes old JSONL files."""

    def test_deletes_files_older_than_retention(self, tmp_path):
        """JSONL files older than LOG_RETENTION_DAYS are deleted."""
        from src.telegram_bot.log_rotation import rotate_logs

        # Create a project with log files
        project = tmp_path / "my-project" / "loop" / "logs"
        project.mkdir(parents=True)

        old_file = project / "run-2026-01-01.jsonl"
        old_file.write_text('{"type":"test"}\n')
        # Set mtime to 30 days ago
        old_time = time.time() - (30 * 86400)
        os.utime(old_file, (old_time, old_time))

        new_file = project / "run-2026-02-07.jsonl"
        new_file.write_text('{"type":"test"}\n')

        result = rotate_logs(tmp_path, retention_days=7)

        assert not old_file.exists(), "Old file should be deleted"
        assert new_file.exists(), "Recent file should be kept"
        assert result["deleted"] >= 1

    def test_deletes_oldest_when_size_exceeded(self, tmp_path):
        """When total size exceeds LOG_MAX_SIZE_MB, oldest files are deleted first."""
        from src.telegram_bot.log_rotation import rotate_logs

        project = tmp_path / "my-project" / "loop" / "logs"
        project.mkdir(parents=True)

        # Create files with known sizes — 3 files, each ~100 bytes
        for i, name in enumerate(["a.jsonl", "b.jsonl", "c.jsonl"]):
            f = project / name
            f.write_text("x" * 100)
            # Stagger mtime so oldest is deterministic
            os.utime(f, (time.time() - (3 - i) * 100, time.time() - (3 - i) * 100))

        # Set max size to 0.0002 MB (~200 bytes) — should delete at least one file
        result = rotate_logs(tmp_path, retention_days=365, max_size_mb=0.0002)

        remaining = list(project.glob("*.jsonl"))
        assert len(remaining) < 3, "At least one file should be deleted to fit size limit"
        assert result["deleted"] >= 1

    def test_ignores_non_jsonl_files(self, tmp_path):
        """Only .jsonl files are considered for rotation."""
        from src.telegram_bot.log_rotation import rotate_logs

        project = tmp_path / "my-project" / "loop" / "logs"
        project.mkdir(parents=True)

        progress = project / ".progress"
        progress.write_text("3")
        old_time = time.time() - (30 * 86400)
        os.utime(progress, (old_time, old_time))

        txt_file = project / "notes.txt"
        txt_file.write_text("some notes")
        os.utime(txt_file, (old_time, old_time))

        rotate_logs(tmp_path, retention_days=7)

        assert progress.exists(), ".progress should not be deleted"
        assert txt_file.exists(), "Non-JSONL files should not be deleted"

    def test_handles_empty_logs_dir(self, tmp_path):
        """No crash when loop/logs/ exists but is empty."""
        from src.telegram_bot.log_rotation import rotate_logs

        project = tmp_path / "my-project" / "loop" / "logs"
        project.mkdir(parents=True)

        result = rotate_logs(tmp_path, retention_days=7)
        assert result["deleted"] == 0

    def test_handles_missing_logs_dir(self, tmp_path):
        """No crash when project has no loop/logs/ directory."""
        from src.telegram_bot.log_rotation import rotate_logs

        project = tmp_path / "my-project"
        project.mkdir()

        result = rotate_logs(tmp_path, retention_days=7)
        assert result["deleted"] == 0

    def test_handles_no_projects(self, tmp_path):
        """No crash when projects_root is empty."""
        from src.telegram_bot.log_rotation import rotate_logs

        result = rotate_logs(tmp_path, retention_days=7)
        assert result["deleted"] == 0

    def test_scans_multiple_projects(self, tmp_path):
        """Rotation scans all project directories under projects_root."""
        from src.telegram_bot.log_rotation import rotate_logs

        old_time = time.time() - (30 * 86400)
        for proj_name in ["proj-a", "proj-b"]:
            logs = tmp_path / proj_name / "loop" / "logs"
            logs.mkdir(parents=True)
            f = logs / "old.jsonl"
            f.write_text('{"test": true}\n')
            os.utime(f, (old_time, old_time))

        result = rotate_logs(tmp_path, retention_days=7)
        assert result["deleted"] == 2

    def test_returns_freed_bytes(self, tmp_path):
        """Result includes total bytes freed from deleted files."""
        from src.telegram_bot.log_rotation import rotate_logs

        project = tmp_path / "my-project" / "loop" / "logs"
        project.mkdir(parents=True)

        f = project / "old.jsonl"
        f.write_text("x" * 500)
        old_time = time.time() - (30 * 86400)
        os.utime(f, (old_time, old_time))

        result = rotate_logs(tmp_path, retention_days=7)
        assert result["freed_bytes"] >= 500


class TestCleanupBrainstormFiles:
    """cleanup_brainstorm_files() removes orphaned brainstorm JSONL files."""

    def test_deletes_orphaned_files(self, tmp_path):
        """JSONL files not referenced by sessions.json are deleted."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        brainstorm_dir = tmp_path / ".brainstorm"
        brainstorm_dir.mkdir()

        # Create orphaned file (no matching session)
        orphan = brainstorm_dir / "brainstorm_123_abc12345.jsonl"
        orphan.write_text('{"type":"result"}\n')

        # Create sessions file with no active sessions
        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_file.write_text("[]")

        result = cleanup_brainstorm_files(tmp_path)
        assert not orphan.exists(), "Orphaned file should be deleted"
        assert result["deleted"] >= 1

    def test_keeps_referenced_files(self, tmp_path):
        """Files referenced by active sessions in sessions.json are kept."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        brainstorm_dir = tmp_path / ".brainstorm"
        brainstorm_dir.mkdir()

        # Active session file
        active = brainstorm_dir / "brainstorm_123_abc12345.jsonl"
        active.write_text('{"type":"result"}\n')

        # sessions.json references the file's chat_id pattern
        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_data = [{
            "chat_id": 123,
            "project": "test",
            "project_path": "/tmp/test",
            "session_id": "sid",
            "tmux_session": "brainstorm-123",
            "initial_prompt": "test",
            "started_at": "2026-02-08T00:00:00",
            "status": "ready",
        }]
        sessions_file.write_text(json.dumps(sessions_data))

        result = cleanup_brainstorm_files(tmp_path)
        assert active.exists(), "Active session file should be kept"
        assert result["deleted"] == 0

    def test_handles_missing_brainstorm_dir(self, tmp_path):
        """No crash when .brainstorm/ directory doesn't exist."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        result = cleanup_brainstorm_files(tmp_path)
        assert result["deleted"] == 0

    def test_handles_missing_sessions_file(self, tmp_path):
        """When sessions.json is missing, all brainstorm files are orphaned."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        brainstorm_dir = tmp_path / ".brainstorm"
        brainstorm_dir.mkdir()

        orphan = brainstorm_dir / "brainstorm_123_abc12345.jsonl"
        orphan.write_text('{"type":"result"}\n')

        result = cleanup_brainstorm_files(tmp_path)
        assert not orphan.exists()
        assert result["deleted"] == 1

    def test_handles_corrupt_sessions_file(self, tmp_path):
        """When sessions.json is corrupt, treat all files as orphaned."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        brainstorm_dir = tmp_path / ".brainstorm"
        brainstorm_dir.mkdir()

        orphan = brainstorm_dir / "brainstorm_123_abc12345.jsonl"
        orphan.write_text('{"type":"result"}\n')

        sessions_file = tmp_path / ".brainstorm_sessions.json"
        sessions_file.write_text("not valid json{{{")

        result = cleanup_brainstorm_files(tmp_path)
        assert not orphan.exists()
        assert result["deleted"] == 1

    def test_ignores_non_jsonl_in_brainstorm_dir(self, tmp_path):
        """Only .jsonl files in .brainstorm/ are candidates for cleanup."""
        from src.telegram_bot.log_rotation import cleanup_brainstorm_files

        brainstorm_dir = tmp_path / ".brainstorm"
        brainstorm_dir.mkdir()

        readme = brainstorm_dir / "README.md"
        readme.write_text("# Brainstorm files")

        result = cleanup_brainstorm_files(tmp_path)
        assert readme.exists()
        assert result["deleted"] == 0


class TestCheckDiskSpace:
    """check_disk_space() checks available disk space against threshold."""

    def test_returns_ok_when_enough_space(self, tmp_path):
        """Returns (True, available_mb) when disk has enough space."""
        from src.telegram_bot.log_rotation import check_disk_space

        # Real filesystem should have > 1 MB free
        ok, available_mb = check_disk_space(tmp_path, min_mb=1)
        assert ok is True
        assert available_mb > 0

    def test_returns_not_ok_with_huge_threshold(self, tmp_path):
        """Returns (False, available_mb) when threshold is impossibly high."""
        from src.telegram_bot.log_rotation import check_disk_space

        # No filesystem has 999999999 MB free
        ok, available_mb = check_disk_space(tmp_path, min_mb=999_999_999)
        assert ok is False
        assert available_mb > 0

    def test_returns_available_mb_as_float(self, tmp_path):
        """available_mb is a float representing megabytes."""
        from src.telegram_bot.log_rotation import check_disk_space

        _, available_mb = check_disk_space(tmp_path)
        assert isinstance(available_mb, float)

    def test_handles_nonexistent_path(self):
        """Returns (False, 0) for a path that doesn't exist."""
        from src.telegram_bot.log_rotation import check_disk_space

        ok, available_mb = check_disk_space(Path("/nonexistent/path/xyz"))
        assert ok is False
        assert available_mb == 0
