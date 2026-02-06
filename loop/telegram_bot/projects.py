"""Project and worktree management."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import MAIN_PROJECT, PROJECTS_ROOT


@dataclass
class Project:
    """Represents a git worktree project."""

    name: str
    path: Path
    branch: str
    is_main: bool
    has_loop: bool


def list_projects() -> list[Project]:
    """List all git worktree projects under PROJECTS_ROOT."""
    projects_root = Path(PROJECTS_ROOT)

    if not MAIN_PROJECT:
        # No main project configured — list all directories with .git
        projects = []
        if projects_root.exists():
            for child in sorted(projects_root.iterdir()):
                if child.is_dir() and (child / ".git").exists():
                    branch = _get_branch(child)
                    has_loop = (child / "loop" / "loop.sh").exists()
                    projects.append(
                        Project(
                            name=child.name,
                            path=child,
                            branch=branch,
                            is_main=False,
                            has_loop=has_loop,
                        )
                    )
        return projects

    main_project_path = projects_root / MAIN_PROJECT

    if not main_project_path.exists():
        return []

    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=main_project_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    projects = []
    lines = result.stdout.strip().split("\n")
    i = 0

    while i < len(lines):
        if not lines[i].startswith("worktree "):
            i += 1
            continue

        path = Path(lines[i].replace("worktree ", ""))
        branch = ""

        i += 1
        while i < len(lines) and lines[i] and not lines[i].startswith("worktree "):
            if lines[i].startswith("branch "):
                branch = lines[i].replace("branch refs/heads/", "")
            i += 1

        name = path.name
        is_main = name == MAIN_PROJECT
        has_loop = (path / "loop" / "loop.sh").exists()

        projects.append(
            Project(
                name=name,
                path=path,
                branch=branch,
                is_main=is_main,
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


def create_worktree(suffix: str) -> tuple[bool, str]:
    """Create a new worktree with the given suffix.

    Creates: {suffix}/ with branch {suffix}

    Returns:
        (success, message)
    """
    projects_root = Path(PROJECTS_ROOT)
    main_project_path = projects_root / MAIN_PROJECT
    new_path = projects_root / suffix

    if new_path.exists():
        return False, f"Project {new_path.name} already exists"

    result = subprocess.run(
        ["git", "worktree", "add", "-b", suffix, str(new_path)],
        cwd=main_project_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, f"Failed to create worktree: {result.stderr}"

    # Copy CLAUDE_template.md as CLAUDE.md in new worktree
    template_path = main_project_path / "CLAUDE_template.md"
    target_path = new_path / "CLAUDE.md"

    if template_path.exists():
        shutil.copy(template_path, target_path)

    return True, f"Created {new_path.name} on branch {suffix}"
