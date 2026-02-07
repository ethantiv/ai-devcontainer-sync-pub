# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/12 (0%)

## Goal

Add the ability to create a new project from the Telegram bot when the projects folder is empty (or at any time). The flow should allow the user to:
1. Create a new local project (directory + `git init` + `loop init`)
2. Optionally create a GitHub repository (private or public) and push the initial commit

This addresses the ROADMAP.md requirement: when no projects exist, the bot currently shows "No projects found" — enhance this scenario with a project creation option, including optional GitHub integration.

## Current Phase

Phase 1: Backend — `projects.py`

## Phases

### Phase 1: Backend — `projects.py`
- [ ] Add `create_project(name: str) -> tuple[bool, str]` function that creates `PROJECTS_ROOT/{name}/`, runs `git init`, creates initial commit, and runs `loop init`
- [ ] Add `create_github_repo(project_path: Path, name: str, private: bool) -> tuple[bool, str]` function that runs `gh repo create {name} --private/--public --source=. --remote=origin --push`
- [ ] Add input validation: project name must be `[a-z0-9][a-z0-9-]*` (lowercase, no special chars), reject reserved names (`.git`, `..`, `loop`), reject names that already exist in PROJECTS_ROOT
- [ ] Add `gh` CLI availability check (similar to existing `_has_command` pattern)
- **Status:** pending

### Phase 2: Messages — `messages.py`
- [ ] Add message constants for the new project creation flow: button labels (`MSG_CREATE_PROJECT_BTN`), prompts (`MSG_ENTER_PROJECT_NAME`), success/error messages, GitHub visibility choice labels
- [ ] Add error code constants for validation failures (`ERR_INVALID_NAME`, `ERR_PROJECT_EXISTS`, `ERR_GH_NOT_AVAILABLE`)
- **Status:** pending

### Phase 3: Bot UI — `bot.py`
- [ ] Add "Create project" button to the project list view (alongside existing "Clone repo" button), shown always (not only when list is empty)
- [ ] Add conversation state `ENTER_PROJECT_NAME` for the project name input
- [ ] Add handler for project name input that validates and calls `create_project()`
- [ ] After successful creation, show GitHub integration prompt with 3 buttons: "Private repo", "Public repo", "Skip"
- [ ] Add callback handler for GitHub choice that calls `create_github_repo()` or skips
- [ ] After completion, navigate to the project menu for the newly created project
- **Status:** pending

### Phase 4: Tests
- [ ] Add tests for `create_project()` in `test_projects.py`: success path, name validation (invalid chars, reserved names, existing directory), git init failure, loop init failure
- [ ] Add tests for `create_github_repo()` in `test_projects.py`: success path, `gh` not available, `gh repo create` failure, subprocess timeout
- [ ] Add tests for name validation edge cases: empty string, too long (>100 chars), starts with hyphen, uppercase normalization
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should the "Create project" button appear only when no projects exist? | No — show it always alongside "Clone repo". When the list is empty, the empty-state message should highlight both options. |
| What git initialization should the new project have? | `git init` + empty initial commit (`git commit --allow-empty -m "Initial commit"`) + `loop init` |
| Should project names be normalized to lowercase? | Yes — enforce lowercase with `name.lower()` to match directory naming convention |
| Is `gh` CLI required for this feature? | No — GitHub integration is optional. If `gh` is not available or user selects "Skip", the project is created locally only. |
| What subprocess timeouts to use? | `git init`: 10s, `loop init`: 30s (matching existing pattern), `gh repo create`: 60s (network, matching `clone_repo`) |

## Findings & Decisions

### Requirements

**Functional:**
- FR1: Bot can create a new project directory with `git init` and `loop init`
- FR2: User is prompted for project name with validation
- FR3: After local creation, user can optionally create a GitHub repo (private/public)
- FR4: GitHub integration uses `gh` CLI (already installed in Docker image)
- FR5: "Create project" button visible in project list view (alongside "Clone repo")
- FR6: After creation, user navigates to the new project's menu

**Non-Functional:**
- NFR1: Follow existing patterns (subprocess with timeout, `(bool, str)` return tuples, message constants in `messages.py`)
- NFR2: All new functions must have test coverage
- NFR3: No new dependencies required (`gh` CLI already available in Docker image)

### Research Findings

**Existing patterns to follow:**
- `clone_repo()` in `projects.py`: subprocess with 60s timeout, `(bool, str)` return, auto `loop init`, name extraction and validation
- `create_worktree()` in `projects.py`: 30s timeout, directory conflict check, `(bool, str)` return
- `handle_clone_url()` in `bot.py`: `ENTER_URL` state, input validation, success/error messaging, navigation to project menu
- Error codes in `messages.py`: `ERR_*` constants decoupled from display strings

**Codebase quality status:**
- Zero TODO/FIXME/HACK comments in the codebase — implementation is clean
- 151 Python tests + 20 JS tests — good coverage foundation
- bot.py handlers have no unit tests (async Telegram handlers are hard to test) — not in scope for this feature
- All subprocess calls follow the timeout + try/except pattern consistently

**GitHub CLI availability:**
- `gh` is installed in the Docker image (Dockerfile runtime stage)
- `gh auth login --with-token` runs at container startup via `entrypoint.sh` (uses `GH_TOKEN`)
- `gh` availability can be checked with existing `_has_command()` pattern from `config.py`

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use `gh repo create` CLI, not GitHub API | `gh` is already installed and authenticated. No new dependencies needed. Follows existing subprocess pattern. |
| Project name validation: `[a-z0-9][a-z0-9-]*` | Matches GitHub repo naming conventions and filesystem safety. Auto-lowercase to avoid case sensitivity issues. |
| Show "Create project" button always, not only on empty list | More discoverable. Users might want to create a new project even when others exist. |
| Use `--source=. --remote=origin --push` flags | Creates repo from existing local directory, sets up remote, and pushes in one command. |
| Empty initial commit before loop init | Ensures git repo has at least one commit (some tools require HEAD to exist). `loop init` creates symlinks that should be committed separately by the user. |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| None yet | N/A |

### Resources
- Existing `clone_repo()` implementation: `src/telegram_bot/projects.py:150-195`
- Existing `create_worktree()` implementation: `src/telegram_bot/projects.py:115-147`
- Existing `handle_clone_url()` handler: `src/telegram_bot/bot.py:541-560`
- Message constants pattern: `src/telegram_bot/messages.py`
- `gh repo create` docs: https://cli.github.com/manual/gh_repo_create
