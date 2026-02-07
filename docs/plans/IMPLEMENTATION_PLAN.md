# Implementation Plan

**Status:** IN PROGRESS
**Progress:** 7/14 (50%)
**Last updated:** 2026-02-07 — Phase 1, 2, 4 complete; Phase 3 pending

## Goal

Add the ability to create a new project from the Telegram bot when the projects folder is empty (or at any time). The flow should allow the user to:
1. Create a new local project (directory + `git init` + `loop init`)
2. Optionally create a GitHub repository (private or public) and push the initial commit

This addresses the ROADMAP.md requirement: when no projects exist, the bot currently shows "No projects found" and ends the conversation with no action options — enhance this scenario with a project creation option, including optional GitHub integration.

## Current Phase

Phase 3: Bot UI — `bot.py`

## Phases

### Phase 1: Backend — `projects.py`
- [x] Add `validate_project_name(name: str) -> tuple[bool, str]` function
- [x] Add `create_project(name: str) -> tuple[bool, str]` function
- [x] Add `create_github_repo(project_path: Path, name: str, private: bool) -> tuple[bool, str]` function
- **Status:** complete

### Phase 2: Messages — `messages.py`
- [x] Add button label: `MSG_CREATE_PROJECT_BTN`
- [x] Add flow messages: `MSG_ENTER_PROJECT_NAME`, `MSG_CREATING_PROJECT`, `MSG_PROJECT_CREATED`, `MSG_PROJECT_CREATE_FAILED`
- [x] Add GitHub choice messages: `MSG_GITHUB_CHOICE_PROMPT`, `MSG_GITHUB_PRIVATE_BTN`, `MSG_GITHUB_PUBLIC_BTN`, `MSG_GITHUB_SKIP_BTN`, `MSG_GITHUB_CREATING`, `MSG_GITHUB_CREATED`, `MSG_GITHUB_FAILED`, `MSG_GH_NOT_AVAILABLE`
- [x] Add validation error messages: `MSG_INVALID_PROJECT_NAME`, `MSG_PROJECT_EXISTS`, `MSG_RESERVED_NAME`
- **Status:** complete

### Phase 3: Bot UI — `bot.py`
- [ ] Fix empty-state behavior in `show_projects()`: instead of sending plain text and returning `ConversationHandler.END`, show an inline keyboard with "Create project" and "Clone repo" buttons and return `State.SELECT_PROJECT` so the user can proceed
- [ ] Add "Create project" button to the normal (non-empty) project list view, alongside existing "Clone repo" button
- [ ] Add conversation state `ENTER_PROJECT_NAME` to `State` enum
- [ ] Add conversation state `GITHUB_CHOICE` to `State` enum (for post-creation GitHub visibility selection)
- [ ] Add `handle_project_name()` handler for `ENTER_PROJECT_NAME` state: strips and lowercases input, calls `validate_project_name()`, on validation failure stays in `ENTER_PROJECT_NAME`, on success calls `create_project()`, shows progress message, on success shows GitHub choice prompt (3 buttons: Private/Public/Skip), stores created project name in `user_data`
- [ ] Add callback handler for `GITHUB_CHOICE` state: handles `github:private`, `github:public`, `github:skip` callbacks; for private/public calls `create_github_repo()`, for skip navigates directly to project menu; after GitHub operation (success or failure) navigates to the new project's menu via `show_project_menu()`
- [ ] Register new states and handlers in `create_application()`: add `ENTER_PROJECT_NAME` with `MessageHandler` (text input), add `GITHUB_CHOICE` with `CallbackQueryHandler` (button callbacks)
- **Status:** pending

### Phase 4: Tests
- [x] Add tests for `validate_project_name()` in `test_projects.py` (12 tests)
- [x] Add tests for `create_project()` in `test_projects.py` (6 tests)
- [x] Add tests for `create_github_repo()` in `test_projects.py` (5 tests + 6 timeout/OSError tests in TestSubprocessTimeouts)
- **Status:** complete

## Key Questions

| Question | Answer |
|----------|--------|
| Should the "Create project" button appear only when no projects exist? | No — show it always alongside "Clone repo". When the list is empty, the empty-state message should highlight both options. |
| What git initialization should the new project have? | `git init` + empty initial commit (`git commit --allow-empty -m "Initial commit"`) + `loop init` |
| Should project names be normalized to lowercase? | Yes — enforce lowercase with `name.lower()` to match directory naming convention |
| Is `gh` CLI required for this feature? | No — GitHub integration is optional. If `gh` is not available or user selects "Skip", the project is created locally only. |
| What subprocess timeouts to use? | `git init`: 10s, `git commit`: 10s, `loop init`: 30s (matching existing pattern), `gh repo create`: 60s (network, matching `clone_repo`) |
| Should `validate_project_name` be separate from `create_project`? | Yes — separate validation allows bot.py to show specific error messages per validation failure type, and allows reuse in tests. |
| What happens in empty-state? | Currently: plain text + `ConversationHandler.END` (dead end). Fix: show inline keyboard with Create/Clone buttons + return `State.SELECT_PROJECT`. |

## Findings & Decisions

### Requirements

**Functional:**
- FR1: Bot can create a new project directory with `git init`, initial commit, and `loop init`
- FR2: User is prompted for project name with validation (alphanumeric + hyphen, lowercase, no reserved names)
- FR3: After local creation, user can optionally create a GitHub repo (private/public) via `gh` CLI
- FR4: GitHub integration uses `gh` CLI (already installed and authenticated in Docker image)
- FR5: "Create project" button visible in project list view (alongside "Clone repo"), including empty-state
- FR6: After creation, user navigates to the new project's menu
- FR7: Empty-state no longer ends the conversation — provides actionable buttons

**Non-Functional:**
- NFR1: Follow existing patterns (subprocess with timeout + try/except, `(bool, str)` return tuples, message constants in `messages.py`)
- NFR2: All new functions in `projects.py` must have test coverage
- NFR3: No new dependencies required (`gh` CLI already available in Docker image)
- NFR4: Bot.py handlers are not unit-tested (existing convention) — not in scope

### Research Findings

**Existing patterns to follow:**
- `clone_repo()` in `projects.py:150-195`: subprocess with 60s timeout, `(bool, str)` return, auto `_run_loop_init()`, name extraction and validation, pre-flight directory existence check
- `create_worktree()` in `projects.py:115-147`: 30s timeout, directory conflict check, `(bool, str)` return, MSG_DIR_ALREADY_EXISTS error
- `handle_clone_url()` in `bot.py:540-560`: `ENTER_URL` state, input strip/validation, progress message before long operation, success→`start()` / failure→stay in state
- `handle_name()` in `bot.py:510-537`: `ENTER_NAME` state, `name.strip().lower()`, character validation with `replace("-","").replace("_","").isalnum()`, MSG_INVALID_NAME on failure
- Error codes in `messages.py`: `ERR_*` constants decoupled from display strings, `BRAINSTORM_ERROR_CODES` frozenset pattern
- Subprocess error handling: consistent `try/except (subprocess.TimeoutExpired, OSError)` with specific fallback values

**Codebase quality status:**
- Zero TODO/FIXME/HACK comments — implementation is clean
- 151 Python tests + 20 JS tests — good coverage foundation
- All subprocess calls follow timeout + try/except pattern consistently
- `test_projects.py` has `TestSubprocessTimeouts` class with 13 dedicated tests — new functions must follow same pattern
- Fixtures use `yield` with `patch()` context managers (not `return`)
- PROJECTS_ROOT is patched at module namespace level: `patch("src.telegram_bot.projects.PROJECTS_ROOT", ...)`

**GitHub CLI availability:**
- `gh` is installed in Docker image (Dockerfile runtime stage, lines 60-69, official GitHub apt repository)
- `gh auth login --with-token` runs at every container startup via `entrypoint.sh:94-109` (uses `GH_TOKEN`)
- `gh auth setup-git` configures git credential integration
- CLI availability check pattern: `shutil.which("gh")` inline (no `_has_command` helper exists — config.py uses `shutil.which()` directly in `validate()`)

**Empty-state critical issue:**
- `show_projects()` at line 210-212: when `not projects`, sends `MSG_NO_PROJECTS` text and returns `ConversationHandler.END`
- This is a dead end — user has no buttons and no way to proceed
- The "Clone repo" button (line 229) only appears in the non-empty project list
- Fix must change empty-state to show inline keyboard with "Create project" + "Clone repo" and return `State.SELECT_PROJECT`

**Name validation comparison:**
- Current worktree validation in `handle_name()`: `name.replace("-", "").replace("_", "").isalnum()` — allows underscores
- Proposed project validation: stricter `[a-z0-9][a-z0-9-]*` regex — no underscores (GitHub repo naming convention)
- Both normalize to lowercase via `name.strip().lower()`

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use `gh repo create` CLI, not GitHub API | `gh` is already installed and authenticated. No new dependencies needed. Follows existing subprocess pattern. |
| Project name validation: `[a-z0-9][a-z0-9-]*` (no underscores) | Matches GitHub repo naming conventions and filesystem safety. Stricter than worktree validation (which allows underscores) because project names may become GitHub repo names. |
| Separate `validate_project_name()` function | Enables specific error messages per failure type, testable independently, reusable. |
| Show "Create project" button always, not only on empty list | More discoverable. Users might want to create a new project even when others exist. |
| Use `--source=. --remote=origin --push` flags for `gh repo create` | Creates repo from existing local directory, sets up remote, and pushes in one command. |
| Empty initial commit before loop init | Ensures git repo has at least one commit (some tools require HEAD to exist). `loop init` creates symlinks that should be committed separately by the user. |
| Fix empty-state to show buttons instead of ending conversation | Current behavior is a dead end — user cannot proceed. Showing Create/Clone buttons makes the bot usable from a fresh state. |
| Add `GITHUB_CHOICE` state (not reuse `PROJECT_MENU`) | Cleaner state machine — GitHub choice is a distinct step in the creation flow, not part of the project menu. Prevents accidental state mixing. |
| No `gh` availability check in `config.validate()` | `gh` is optional (GitHub integration is opt-in). Adding a warning would be noise for users who don't need GitHub features. Check availability inline in `create_github_repo()` instead. |

### Code Verification (2026-02-07, updated)

| Planned Element | Status |
|-----------------|--------|
| `validate_project_name()` in `projects.py` | Done — regex `[a-z0-9][a-z0-9-]*`, reserved names, PROJECTS_ROOT check |
| `create_project()` in `projects.py` | Done — git init + initial commit + loop init (non-fatal) |
| `create_github_repo()` in `projects.py` | Done — `shutil.which("gh")` + `gh repo create` with 60s timeout |
| `ENTER_PROJECT_NAME` state in `bot.py` | Pending — Phase 3 |
| `GITHUB_CHOICE` state in `bot.py` | Pending — Phase 3 |
| `handle_project_name()` handler in `bot.py` | Pending — Phase 3 |
| GitHub choice callback handler in `bot.py` | Pending — Phase 3 |
| `MSG_CREATE_PROJECT_BTN` and related constants | Done — 16 new constants in `messages.py` |
| Empty-state fix in `show_projects()` | Pending — Phase 3 |
| Tests for `validate_project_name()` | Done — 12 tests in `TestValidateProjectName` |
| Tests for `create_project()` | Done — 6 tests in `TestCreateProject` |
| Tests for `create_github_repo()` | Done — 5 tests in `TestCreateGithubRepo` + 6 in `TestSubprocessTimeouts` |

**Codebase state**: 180 Python + 20 JS tests passing. `test_projects.py` has 62 tests across 9 classes.

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| `_has_command` doesn't exist in config.py | Plan updated: use `shutil.which("gh")` inline in `create_github_repo()` (matches existing pattern in `config.validate()`) |
| Empty-state ends conversation with no action options | Plan updated: Phase 3 includes fixing `show_projects()` to show inline keyboard in empty state |
| `docs/specs/` directory doesn't exist | Not needed — ROADMAP.md is sufficient as the spec for this feature |

### Resources
- Existing `clone_repo()` implementation: `src/telegram_bot/projects.py:150-195`
- Existing `create_worktree()` implementation: `src/telegram_bot/projects.py:115-147`
- Existing `handle_clone_url()` handler: `src/telegram_bot/bot.py:540-560`
- Existing `handle_name()` handler: `src/telegram_bot/bot.py:510-537`
- Empty-state behavior: `src/telegram_bot/bot.py:206-212`
- Name validation pattern: `src/telegram_bot/bot.py:519-521`
- Message constants pattern: `src/telegram_bot/messages.py`
- Subprocess timeout tests: `src/telegram_bot/tests/test_projects.py:247-369`
- Test fixtures: `src/telegram_bot/tests/conftest.py`
- `gh` installation: `docker/Dockerfile:60-69`
- `gh` auth: `docker/entrypoint.sh:94-109`
- `shutil.which` usage: `src/telegram_bot/config.py:100-116`
