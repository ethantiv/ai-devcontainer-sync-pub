"""Project and worktree management."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import PROJECTS_ROOT
from .messages import (
    MSG_CLONED,
    MSG_DIR_ALREADY_EXISTS,
    MSG_LOOP_INIT_FAILED,
    MSG_LOOP_INITIALIZED,
    MSG_WORKTREE_CREATED,
)


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
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


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

    result = subprocess.run(
        ["git", "worktree", "add", "-b", suffix, str(new_path)],
        cwd=project_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, f"Failed to create worktree: {result.stderr}"

    return True, MSG_WORKTREE_CREATED.format(name=new_name, suffix=suffix)


def clone_repo(url: str) -> tuple[bool, str]:
    """Clone a git repository into PROJECTS_ROOT.

    Extracts repo name from URL, clones, then runs `loop init`.

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

    result = subprocess.run(
        ["git", "clone", url, str(target)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, f"git clone failed: {result.stderr}"

    # Auto-run loop init in the cloned repo
    loop_init = _run_loop_init(target)

    msg = MSG_CLONED.format(name=name)
    if loop_init:
        msg += ". " + MSG_LOOP_INITIALIZED
    else:
        msg += ". " + MSG_LOOP_INIT_FAILED

    return True, msg


def _run_loop_init(project_path: Path) -> bool:
    """Run `loop init` in a project directory. Returns True on success."""
    loop_cli = "/usr/bin/loop"
    if not Path(loop_cli).exists():
        loop_cli = "loop"  # fall back to PATH

    result = subprocess.run(
        [loop_cli, "init"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
