# Implementation Plan

**Status:** COMPLETE
**Progress:** 14/14 (100%)
**Last updated:** 2026-02-07 — All phases complete

## Goal

Add the ability to create a new project from the Telegram bot when the projects folder is empty (or at any time). The flow should allow the user to:
1. Create a new local project (directory + `git init` + `loop init`)
2. Optionally create a GitHub repository (private or public) and push the initial commit

This addresses the ROADMAP.md requirement: when no projects exist, the bot currently shows "No projects found" and ends the conversation with no action options — enhance this scenario with a project creation option, including optional GitHub integration.

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
- [x] Fix empty-state behavior in `show_projects()`: shows inline keyboard with "Create project" and "Clone repo" buttons, returns `State.SELECT_PROJECT`
- [x] Add "Create project" button to the normal (non-empty) project list view, alongside existing "Clone repo" button
- [x] Add conversation state `ENTER_PROJECT_NAME` to `State` enum
- [x] Add conversation state `GITHUB_CHOICE` to `State` enum
- [x] Add `handle_project_name()` handler: strips/lowercases input, validates via `validate_project_name()`, calls `create_project()`, shows GitHub choice prompt
- [x] Add `handle_github_choice()` callback handler: handles `github:private`, `github:public`, `github:skip`; calls `create_github_repo()` for private/public; navigates to project menu
- [x] Register new states and handlers in `create_application()`: `ENTER_PROJECT_NAME` with `MessageHandler`, `GITHUB_CHOICE` with `CallbackQueryHandler`
- **Status:** complete

### Phase 4: Tests
- [x] Add tests for `validate_project_name()` in `test_projects.py` (12 tests)
- [x] Add tests for `create_project()` in `test_projects.py` (6 tests)
- [x] Add tests for `create_github_repo()` in `test_projects.py` (5 tests + 6 timeout/OSError tests in TestSubprocessTimeouts)
- **Status:** complete

## Key Questions

| Question | Answer |
|----------|--------|
| Should the "Create project" button appear only when no projects exist? | No — show it always alongside "Clone repo". |
| What git initialization should the new project have? | `git init` + empty initial commit + `loop init` |
| Should project names be normalized to lowercase? | Yes — enforce lowercase with `name.lower()` |
| Is `gh` CLI required for this feature? | No — GitHub integration is optional. |
| What subprocess timeouts to use? | `git init`: 10s, `git commit`: 10s, `loop init`: 30s, `gh repo create`: 60s |
| Should `validate_project_name` be separate from `create_project`? | Yes — separate validation for specific error messages and testability. |
| What happens in empty-state? | Fixed: shows inline keyboard with Create/Clone buttons + returns `State.SELECT_PROJECT`. |

**Codebase state**: 180 Python + 20 JS tests passing. `test_projects.py` has 62 tests across 9 classes.
