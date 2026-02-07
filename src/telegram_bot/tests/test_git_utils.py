"""Tests for git_utils module — mocked subprocess calls."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.telegram_bot.git_utils import (
    get_commit_hash,
    get_diff_stats,
    get_plan_progress,
    get_recent_commits,
)


class TestGetCommitHash:
    """Tests for get_commit_hash()."""

    def test_returns_short_hash(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="abc1234\n")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result) as m:
            result = get_commit_hash(tmp_path)
        assert result == "abc1234"
        m.assert_called_once_with(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=10,
        )

    def test_returns_none_on_nonzero_exit(self, tmp_path):
        mock_result = MagicMock(returncode=128, stdout="")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            assert get_commit_hash(tmp_path) is None

    def test_returns_none_on_timeout(self, tmp_path):
        with patch(
            "src.telegram_bot.git_utils.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            assert get_commit_hash(tmp_path) is None

    def test_returns_none_on_oserror(self, tmp_path):
        with patch(
            "src.telegram_bot.git_utils.subprocess.run",
            side_effect=OSError("no such file"),
        ):
            assert get_commit_hash(tmp_path) is None


class TestGetDiffStats:
    """Tests for get_diff_stats()."""

    def test_parses_numstat_output(self, tmp_path):
        # numstat format: insertions\tdeletions\tfilename
        stdout = "10\t3\tsrc/foo.py\n5\t0\tsrc/bar.py\n"
        mock_result = MagicMock(returncode=0, stdout=stdout)
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            result = get_diff_stats(tmp_path, "abc1234")
        assert result == {"files_changed": 2, "insertions": 15, "deletions": 3}

    def test_handles_binary_files(self, tmp_path):
        # Binary files show as "-\t-\tfilename"
        stdout = "10\t3\tsrc/foo.py\n-\t-\timage.png\n"
        mock_result = MagicMock(returncode=0, stdout=stdout)
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            result = get_diff_stats(tmp_path, "abc1234")
        # Binary file counted as 0 insertions/deletions but still a changed file
        assert result == {"files_changed": 2, "insertions": 10, "deletions": 3}

    def test_returns_none_on_no_changes(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="\n")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            assert get_diff_stats(tmp_path, "abc1234") is None

    def test_returns_none_on_git_failure(self, tmp_path):
        mock_result = MagicMock(returncode=128, stdout="")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            assert get_diff_stats(tmp_path, "abc1234") is None

    def test_returns_none_on_timeout(self, tmp_path):
        with patch(
            "src.telegram_bot.git_utils.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            assert get_diff_stats(tmp_path, "abc1234") is None

    def test_malformed_numstat_lines_skipped(self, tmp_path):
        # Lines that don't have 3 tab-separated parts are skipped
        stdout = "not a valid line\n10\t3\tsrc/foo.py\n"
        mock_result = MagicMock(returncode=0, stdout=stdout)
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            result = get_diff_stats(tmp_path, "abc1234")
        assert result == {"files_changed": 1, "insertions": 10, "deletions": 3}


class TestGetRecentCommits:
    """Tests for get_recent_commits()."""

    def test_returns_commit_lines(self, tmp_path):
        stdout = "abc1234 Fix bug\ndef5678 Add feature\n"
        mock_result = MagicMock(returncode=0, stdout=stdout)
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            result = get_recent_commits(tmp_path, "abc1234")
        assert result == ["abc1234 Fix bug", "def5678 Add feature"]

    def test_returns_empty_on_no_commits(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            assert get_recent_commits(tmp_path, "abc1234") == []

    def test_returns_empty_on_failure(self, tmp_path):
        mock_result = MagicMock(returncode=128, stdout="")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result):
            assert get_recent_commits(tmp_path, "abc1234") == []

    def test_returns_empty_on_timeout(self, tmp_path):
        with patch(
            "src.telegram_bot.git_utils.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            assert get_recent_commits(tmp_path, "abc1234") == []

    def test_max_count_passed_to_git(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="abc Fix\n")
        with patch("src.telegram_bot.git_utils.subprocess.run", return_value=mock_result) as m:
            get_recent_commits(tmp_path, "abc1234", max_count=3)
        args = m.call_args[0][0]
        assert "--max-count=3" in args


class TestGetPlanProgress:
    """Tests for get_plan_progress() — reads real files, no subprocess."""

    def test_counts_checkboxes(self, tmp_path):
        plan_dir = tmp_path / "docs" / "plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(
            "# Plan\n\n"
            "- [x] Task one\n"
            "- [x] Task two\n"
            "- [ ] Task three\n"
            "- [ ] Task four\n"
        )
        assert get_plan_progress(tmp_path) == (2, 4)

    def test_returns_none_when_no_file(self, tmp_path):
        assert get_plan_progress(tmp_path) is None

    def test_returns_none_when_no_checkboxes(self, tmp_path):
        plan_dir = tmp_path / "docs" / "plans"
        plan_dir.mkdir(parents=True)
        (plan_dir / "IMPLEMENTATION_PLAN.md").write_text("# Plan\n\nNo tasks yet.\n")
        assert get_plan_progress(tmp_path) is None

    def test_case_insensitive_checked(self, tmp_path):
        """[X] (uppercase) should also be counted as checked."""
        plan_dir = tmp_path / "docs" / "plans"
        plan_dir.mkdir(parents=True)
        (plan_dir / "IMPLEMENTATION_PLAN.md").write_text(
            "- [X] Done task\n- [ ] Pending task\n"
        )
        assert get_plan_progress(tmp_path) == (1, 2)

    def test_returns_none_on_read_error(self, tmp_path):
        plan_dir = tmp_path / "docs" / "plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("- [x] Done\n")
        # Make unreadable
        plan_file.chmod(0o000)
        result = get_plan_progress(tmp_path)
        # Restore for cleanup
        plan_file.chmod(0o644)
        assert result is None
