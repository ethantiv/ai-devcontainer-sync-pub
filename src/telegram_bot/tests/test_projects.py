"""Tests for projects module — directory scanning, worktrees, cloning."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


def _make_git_repo(root: Path, name: str, *, worktree_parent: str | None = None, has_loop: bool = False):
    """Create a fake git project directory under root.

    Args:
        worktree_parent: If set, create a .git file (worktree) pointing to parent.
        has_loop: If True, create loop/loop.sh marker file.
    """
    project = root / name
    project.mkdir()
    git_path = project / ".git"
    if worktree_parent:
        git_path.write_text(f"gitdir: /home/dev/projects/{worktree_parent}/.git/worktrees/{name}")
    else:
        git_path.mkdir()
    if has_loop:
        loop_dir = project / "loop"
        loop_dir.mkdir()
        (loop_dir / "loop.sh").touch()
    return project


class TestParseGitdir:
    """Tests for _parse_gitdir() — worktree detection via .git file content."""

    def test_standalone_repo_returns_none(self, tmp_path):
        from src.telegram_bot.projects import _parse_gitdir
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        assert _parse_gitdir(git_dir) is None

    def test_worktree_returns_parent_name(self, tmp_path):
        from src.telegram_bot.projects import _parse_gitdir
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /home/dev/projects/my-repo/.git/worktrees/feature-x")
        assert _parse_gitdir(git_file) == "my-repo"

    def test_malformed_gitdir_returns_none(self, tmp_path):
        from src.telegram_bot.projects import _parse_gitdir
        git_file = tmp_path / ".git"
        git_file.write_text("not a valid gitdir content")
        assert _parse_gitdir(git_file) is None

    def test_missing_file_returns_none(self, tmp_path):
        from src.telegram_bot.projects import _parse_gitdir
        assert _parse_gitdir(tmp_path / "nonexistent") is None

    def test_no_git_in_path_returns_none(self, tmp_path):
        from src.telegram_bot.projects import _parse_gitdir
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /some/path/without/dot-git-component")
        assert _parse_gitdir(git_file) is None


class TestListProjects:
    """Tests for list_projects() — directory scanning with patched PROJECTS_ROOT."""

    def test_empty_root_returns_empty(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import list_projects
            assert list_projects() == []

    def test_finds_standalone_repo(self, tmp_projects_root):
        _make_git_repo(tmp_projects_root, "my-app")
        with (
            patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)),
            patch("src.telegram_bot.projects._get_branch", return_value="main"),
        ):
            from src.telegram_bot.projects import list_projects
            projects = list_projects()
        assert len(projects) == 1
        assert projects[0].name == "my-app"
        assert projects[0].is_worktree is False
        assert projects[0].parent_repo is None

    def test_finds_worktree(self, tmp_projects_root):
        _make_git_repo(tmp_projects_root, "my-app")
        _make_git_repo(tmp_projects_root, "my-app-feature", worktree_parent="my-app")
        with (
            patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)),
            patch("src.telegram_bot.projects._get_branch", return_value="feature"),
        ):
            from src.telegram_bot.projects import list_projects
            projects = list_projects()
        assert len(projects) == 2
        wt = [p for p in projects if p.is_worktree][0]
        assert wt.name == "my-app-feature"
        assert wt.parent_repo == "my-app"

    def test_detects_loop_initialized(self, tmp_projects_root):
        _make_git_repo(tmp_projects_root, "with-loop", has_loop=True)
        _make_git_repo(tmp_projects_root, "without-loop", has_loop=False)
        with (
            patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)),
            patch("src.telegram_bot.projects._get_branch", return_value="main"),
        ):
            from src.telegram_bot.projects import list_projects
            projects = list_projects()
        by_name = {p.name: p for p in projects}
        assert by_name["with-loop"].has_loop is True
        assert by_name["without-loop"].has_loop is False

    def test_ignores_non_git_directories(self, tmp_projects_root):
        (tmp_projects_root / "random-dir").mkdir()
        (tmp_projects_root / "another-file.txt").touch()
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import list_projects
            assert list_projects() == []

    def test_projects_sorted_by_name(self, tmp_projects_root):
        _make_git_repo(tmp_projects_root, "zeta")
        _make_git_repo(tmp_projects_root, "alpha")
        _make_git_repo(tmp_projects_root, "middle")
        with (
            patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)),
            patch("src.telegram_bot.projects._get_branch", return_value="main"),
        ):
            from src.telegram_bot.projects import list_projects
            projects = list_projects()
        names = [p.name for p in projects]
        assert names == ["alpha", "middle", "zeta"]


class TestGetBranch:
    """Tests for _get_branch() — subprocess call."""

    def test_returns_branch_name(self, tmp_path):
        from src.telegram_bot.projects import _get_branch
        mock_result = MagicMock(returncode=0, stdout="feature-branch\n")
        with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result):
            assert _get_branch(tmp_path) == "feature-branch"

    def test_returns_empty_on_failure(self, tmp_path):
        from src.telegram_bot.projects import _get_branch
        mock_result = MagicMock(returncode=128, stdout="")
        with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result):
            assert _get_branch(tmp_path) == ""


class TestCreateWorktree:
    """Tests for create_worktree() — git worktree add."""

    def test_success(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            mock_result = MagicMock(returncode=0, stderr="")
            with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result) as m:
                success, msg = create_worktree(project_path, "feat-x")
            assert success is True
            assert "my-repo-feat-x" in msg
            args = m.call_args[0][0]
            assert args[0:3] == ["git", "worktree", "add"]
            assert "-b" in args
            assert "feat-x" in args

    def test_fails_if_dir_exists(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            (tmp_projects_root / "my-repo-feat-x").mkdir()
            success, msg = create_worktree(project_path, "feat-x")
            assert success is False
            assert "already exists" in msg

    def test_fails_on_git_error(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            mock_result = MagicMock(returncode=128, stderr="fatal: error")
            with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result):
                success, msg = create_worktree(project_path, "feat-x")
            assert success is False
            assert "Failed" in msg


class TestCloneRepo:
    """Tests for clone_repo() — git clone + loop init."""

    def test_success_with_loop_init(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            clone_result = MagicMock(returncode=0)
            init_result = MagicMock(returncode=0)
            with (
                patch("src.telegram_bot.projects.subprocess.run", side_effect=[clone_result, init_result]),
                patch("src.telegram_bot.projects._run_loop_init", return_value=True),
            ):
                success, msg = clone_repo("https://github.com/user/my-repo.git")
            assert success is True
            assert "my-repo" in msg

    def test_strips_dot_git_from_url(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            clone_result = MagicMock(returncode=0)
            with (
                patch("src.telegram_bot.projects.subprocess.run", return_value=clone_result),
                patch("src.telegram_bot.projects._run_loop_init", return_value=True),
            ):
                success, msg = clone_repo("https://github.com/user/repo-name.git")
            assert success is True
            assert "repo-name" in msg

    def test_fails_if_dir_exists(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            (tmp_projects_root / "my-repo").mkdir()
            success, msg = clone_repo("https://github.com/user/my-repo.git")
            assert success is False
            assert "already exists" in msg

    def test_fails_on_clone_error(self, tmp_projects_root):
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            clone_result = MagicMock(returncode=128, stderr="fatal: repo not found")
            with patch("src.telegram_bot.projects.subprocess.run", return_value=clone_result):
                success, msg = clone_repo("https://github.com/user/nonexistent.git")
            assert success is False
            assert "clone failed" in msg.lower() or "fatal" in msg.lower()

    def test_success_with_loop_init_failure(self, tmp_projects_root):
        """Clone succeeds but loop init fails — still returns success with warning."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            clone_result = MagicMock(returncode=0)
            with (
                patch("src.telegram_bot.projects.subprocess.run", return_value=clone_result),
                patch("src.telegram_bot.projects._run_loop_init", return_value=False),
            ):
                success, msg = clone_repo("https://github.com/user/my-repo.git")
            assert success is True
            assert "failed" in msg.lower() or "manually" in msg.lower()


class TestSubprocessTimeouts:
    """Tests for subprocess timeout and OSError handling in projects.py.

    Every subprocess.run() call must have a timeout parameter and handle
    TimeoutExpired and OSError gracefully — matching the pattern in git_utils.py.
    """

    def test_get_branch_has_timeout(self, tmp_path):
        """_get_branch() passes timeout to subprocess.run()."""
        from src.telegram_bot.projects import _get_branch
        mock_result = MagicMock(returncode=0, stdout="main\n")
        with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result) as m:
            _get_branch(tmp_path)
        assert m.call_args.kwargs.get("timeout") is not None, \
            "_get_branch() must pass timeout to subprocess.run()"

    def test_get_branch_timeout_returns_unknown(self, tmp_path):
        """_get_branch() returns 'unknown' when subprocess times out."""
        from src.telegram_bot.projects import _get_branch
        with patch("src.telegram_bot.projects.subprocess.run",
                    side_effect=subprocess.TimeoutExpired("git", 10)):
            result = _get_branch(tmp_path)
        assert result == "unknown"

    def test_get_branch_oserror_returns_unknown(self, tmp_path):
        """_get_branch() returns 'unknown' when subprocess raises OSError."""
        from src.telegram_bot.projects import _get_branch
        with patch("src.telegram_bot.projects.subprocess.run",
                    side_effect=OSError("No such file")):
            result = _get_branch(tmp_path)
        assert result == "unknown"

    def test_create_worktree_has_timeout(self, tmp_projects_root):
        """create_worktree() passes timeout to subprocess.run()."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            mock_result = MagicMock(returncode=0, stderr="")
            with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result) as m:
                create_worktree(project_path, "feat-x")
            assert m.call_args.kwargs.get("timeout") is not None, \
                "create_worktree() must pass timeout to subprocess.run()"

    def test_create_worktree_timeout_returns_failure(self, tmp_projects_root):
        """create_worktree() returns (False, message) on timeout."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            with patch("src.telegram_bot.projects.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("git", 30)):
                success, msg = create_worktree(project_path, "feat-x")
            assert success is False
            assert "timeout" in msg.lower()

    def test_create_worktree_oserror_returns_failure(self, tmp_projects_root):
        """create_worktree() returns (False, message) on OSError."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import create_worktree
            project_path = tmp_projects_root / "my-repo"
            project_path.mkdir()
            with patch("src.telegram_bot.projects.subprocess.run",
                        side_effect=OSError("exec failed")):
                success, msg = create_worktree(project_path, "feat-x")
            assert success is False

    def test_clone_repo_has_timeout(self, tmp_projects_root):
        """clone_repo() passes timeout to subprocess.run()."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            mock_result = MagicMock(returncode=0)
            with (
                patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result) as m,
                patch("src.telegram_bot.projects._run_loop_init", return_value=True),
            ):
                clone_repo("https://github.com/user/my-repo.git")
            assert m.call_args.kwargs.get("timeout") is not None, \
                "clone_repo() must pass timeout to subprocess.run()"

    def test_clone_repo_timeout_returns_failure(self, tmp_projects_root):
        """clone_repo() returns (False, message) on timeout."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            with patch("src.telegram_bot.projects.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("git", 60)):
                success, msg = clone_repo("https://github.com/user/my-repo.git")
            assert success is False
            assert "timeout" in msg.lower()

    def test_clone_repo_oserror_returns_failure(self, tmp_projects_root):
        """clone_repo() returns (False, message) on OSError."""
        with patch("src.telegram_bot.projects.PROJECTS_ROOT", str(tmp_projects_root)):
            from src.telegram_bot.projects import clone_repo
            with patch("src.telegram_bot.projects.subprocess.run",
                        side_effect=OSError("git not found")):
                success, msg = clone_repo("https://github.com/user/my-repo.git")
            assert success is False

    def test_run_loop_init_has_timeout(self, tmp_path):
        """_run_loop_init() passes timeout to subprocess.run()."""
        from src.telegram_bot.projects import _run_loop_init
        mock_result = MagicMock(returncode=0)
        with patch("src.telegram_bot.projects.subprocess.run", return_value=mock_result) as m:
            _run_loop_init(tmp_path)
        assert m.call_args.kwargs.get("timeout") is not None, \
            "_run_loop_init() must pass timeout to subprocess.run()"

    def test_run_loop_init_timeout_returns_false(self, tmp_path):
        """_run_loop_init() returns False on timeout."""
        from src.telegram_bot.projects import _run_loop_init
        with patch("src.telegram_bot.projects.subprocess.run",
                    side_effect=subprocess.TimeoutExpired("loop", 30)):
            result = _run_loop_init(tmp_path)
        assert result is False

    def test_run_loop_init_oserror_returns_false(self, tmp_path):
        """_run_loop_init() returns False when command not found."""
        from src.telegram_bot.projects import _run_loop_init
        with patch("src.telegram_bot.projects.subprocess.run",
                    side_effect=OSError("No such file")):
            result = _run_loop_init(tmp_path)
        assert result is False
