"""Project and worktree management."""

import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from .config import PROJECTS_ROOT
from .messages import (
    MSG_CLONED,
    MSG_DIR_ALREADY_EXISTS,
    MSG_GH_NOT_AVAILABLE,
    MSG_GITHUB_CREATED,
    MSG_GITHUB_FAILED,
    MSG_INVALID_PROJECT_NAME,
    MSG_LOOP_INIT_FAILED,
    MSG_LOOP_INITIALIZED,
    MSG_PROJECT_CREATED,
    MSG_PROJECT_EXISTS,
    MSG_RESERVED_NAME,
    MSG_WORKTREE_CREATED,
)

_PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RESERVED_NAMES = frozenset({".git", "..", "loop"})


@dataclass
class Project:
    """Represents a git project (standalone repo or worktree)."""

    name: str
    path: Path
    branch: str
    is_worktree: bool
    parent_repo: str | None
    has_loop: bool


def _parse_gitdir(git_path: Path) -> str | None:
    """Parse a .git file to extract the parent repo name.

    Worktrees have a .git *file* (not directory) containing:
        gitdir: /path/to/parent/.git/worktrees/<name>

    Returns the parent repo directory name, or None if not a worktree.
    """
    if not git_path.is_file():
        return None
    try:
        content = git_path.read_text().strip()
    except OSError:
        return None
    if not content.startswith("gitdir:"):
        return None
    gitdir = content.split("gitdir:", 1)[1].strip()
    # gitdir looks like: /path/to/parent/.git/worktrees/<name>
    # Find ".git" in path parts and take the parent directory name
    parts = Path(gitdir).parts
    for i, part in enumerate(parts):
        if part == ".git" and i > 0:
            return parts[i - 1]
    return None


def list_projects() -> list[Project]:
    """List all git projects under PROJECTS_ROOT.

    Scans all directories — detects standalone repos (.git directory)
    and worktrees (.git file with gitdir: link).
    """
    projects_root = Path(PROJECTS_ROOT)
    if not projects_root.exists():
        return []

    projects = []
    for child in sorted(projects_root.iterdir()):
        if not child.is_dir():
            continue
        git_path = child / ".git"
        if not git_path.exists():
            continue

        parent_repo = _parse_gitdir(git_path)
        is_worktree = parent_repo is not None
        branch = _get_branch(child)
        has_loop = (child / "loop" / "loop.sh").exists()

        projects.append(
            Project(
                name=child.name,
                path=child,
                branch=branch,
                is_worktree=is_worktree,
                parent_repo=parent_repo,
                has_loop=has_loop,
            )
        )

    return projects


def _get_branch(path: Path) -> str:
    """Get current branch name for a git repository."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return "unknown"


def get_project(name: str) -> Project | None:
    """Get a project by name."""
    for project in list_projects():
        if project.name == name:
            return project
    return None


def create_worktree(project_path: Path, suffix: str) -> tuple[bool, str]:
    """Create a new worktree from any repo.

    Creates: PROJECTS_ROOT/{project_name}-{suffix}/ with branch {suffix}

    Returns:
        (success, message)
    """
    projects_root = Path(PROJECTS_ROOT)
    project_name = project_path.name
    new_name = f"{project_name}-{suffix}"
    new_path = projects_root / new_name

    if new_path.exists():
        return False, MSG_DIR_ALREADY_EXISTS.format(name=new_name)

    try:
        result = subprocess.run(
            ["git", "worktree", "add", "-b", suffix, str(new_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout creating worktree"
    except OSError as e:
        return False, f"Failed to create worktree: {e}"

    if result.returncode != 0:
        return False, f"Failed to create worktree: {result.stderr}"

    return True, MSG_WORKTREE_CREATED.format(name=new_name, suffix=suffix)


_RETRYABLE_GIT_ERRORS = ("network unreachable", "connection reset", "could not resolve host")
_CLONE_MAX_RETRIES = 3
_CLONE_INITIAL_DELAY = 2  # seconds


def _is_retryable_clone_error(result: subprocess.CompletedProcess) -> bool:
    """Check if a failed git clone error is transient and worth retrying."""
    stderr = (result.stderr or "").lower()
    return any(pattern in stderr for pattern in _RETRYABLE_GIT_ERRORS)


def clone_repo(url: str) -> tuple[bool, str]:
    """Clone a git repository into PROJECTS_ROOT with retry on transient errors.

    Retries up to 3 times with exponential backoff (2s, 4s) on
    TimeoutExpired and transient git network errors. Non-retryable
    errors (e.g. repo not found) fail immediately.

    Returns:
        (success, message)
    """
    # Parse repo name from URL (last path segment, strip .git)
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        return False, "Could not parse repository name from URL"

    projects_root = Path(PROJECTS_ROOT)
    target = projects_root / name

    if target.exists():
        return False, MSG_DIR_ALREADY_EXISTS.format(name=name)

    last_error = ""
    for attempt in range(_CLONE_MAX_RETRIES):
        if attempt > 0:
            delay = _CLONE_INITIAL_DELAY * (2 ** (attempt - 1))
            logger.info(f"Retrying clone (attempt {attempt + 1}/{_CLONE_MAX_RETRIES}) after {delay}s")
            time.sleep(delay)
            # Clean up partial clone from previous attempt
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)

        try:
            result = subprocess.run(
                ["git", "clone", url, str(target)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            last_error = "Timeout cloning repository"
            continue  # retryable
        except OSError as e:
            return False, f"git clone failed: {e}"  # not retryable

        if result.returncode == 0:
            # Success — run loop init
            loop_init = _run_loop_init(target)
            msg = MSG_CLONED.format(name=name)
            if loop_init:
                msg += ". " + MSG_LOOP_INITIALIZED
            else:
                msg += ". " + MSG_LOOP_INIT_FAILED
            return True, msg

        # Clone failed — check if retryable
        if _is_retryable_clone_error(result):
            last_error = f"git clone failed: {result.stderr}"
            continue

        # Non-retryable error — fail immediately
        return False, f"git clone failed: {result.stderr}"

    return False, last_error


def validate_project_name(name: str) -> tuple[bool, str]:
    """Validate a project name for creation.

    Rules: lowercase alphanumeric + hyphens, must start with alphanumeric,
    no reserved names, no duplicates in PROJECTS_ROOT.
    Auto-lowercases input.

    Returns:
        (valid, message) — message explains the rejection reason on failure.
    """
    name = name.strip().lower()
    if not name or len(name) > 100:
        return False, MSG_INVALID_PROJECT_NAME
    if name in _RESERVED_NAMES:
        return False, MSG_RESERVED_NAME.format(name=name)
    if not _PROJECT_NAME_RE.match(name):
        return False, MSG_INVALID_PROJECT_NAME
    target = Path(PROJECTS_ROOT) / name
    if target.exists():
        return False, MSG_PROJECT_EXISTS.format(name=name)
    return True, name


def create_project(name: str) -> tuple[bool, str]:
    """Create a new project: directory + git init + initial commit + loop init.

    Returns:
        (success, message)
    """
    valid, result = validate_project_name(name)
    if not valid:
        return False, result
    name = result  # normalized name from validation

    projects_root = Path(PROJECTS_ROOT)
    project_path = projects_root / name
    project_path.mkdir(parents=True, exist_ok=True)

    try:
        git_init = subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout during git init"
    except OSError as e:
        return False, f"git init failed: {e}"

    if git_init.returncode != 0:
        return False, f"git init failed: {git_init.stderr}"

    try:
        git_commit = subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial commit"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout during initial commit"
    except OSError as e:
        return False, f"Initial commit failed: {e}"

    if git_commit.returncode != 0:
        return False, f"Initial commit failed: {git_commit.stderr}"

    loop_init = _run_loop_init(project_path)

    msg = MSG_PROJECT_CREATED.format(name=name)
    if loop_init:
        msg += ". " + MSG_LOOP_INITIALIZED
    else:
        msg += ". " + MSG_LOOP_INIT_FAILED

    return True, msg


def create_github_repo(
    project_path: Path, name: str, private: bool
) -> tuple[bool, str]:
    """Create a GitHub repository from an existing local project.

    Uses `gh repo create` with --source=. --remote=origin --push.

    Returns:
        (success, message)
    """
    if not shutil.which("gh"):
        return False, MSG_GH_NOT_AVAILABLE

    visibility = "--private" if private else "--public"
    try:
        result = subprocess.run(
            [
                "gh", "repo", "create", name,
                visibility,
                "--source=.",
                "--remote=origin",
                "--push",
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout creating GitHub repository"
    except OSError as e:
        return False, f"gh repo create failed: {e}"

    if result.returncode != 0:
        return False, MSG_GITHUB_FAILED.format(message=result.stderr.strip())

    return True, MSG_GITHUB_CREATED.format(name=name)


def _run_loop_init(project_path: Path) -> bool:
    """Run `loop init` in a project directory. Returns True on success."""
    loop_cli = "/usr/bin/loop"
    if not Path(loop_cli).exists():
        loop_cli = "loop"  # fall back to PATH

    try:
        result = subprocess.run(
            [loop_cli, "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
