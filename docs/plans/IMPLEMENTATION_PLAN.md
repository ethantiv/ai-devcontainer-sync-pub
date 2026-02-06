# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/18 (0%)

## Goal

Refactor the Telegram bot to remove the single-main-project assumption (`MAIN_PROJECT`). Every repo in `PROJECTS_ROOT` becomes a first-class project that can create worktrees. Add `git clone` capability from Telegram. Auto-run `loop init` after clone.

## Current Phase

Phase 1: config.py + Project dataclass cleanup

## Phases

### Phase 1: Config and Data Model Cleanup
- [ ] Remove `MAIN_PROJECT` from `loop/telegram_bot/config.py`
- [ ] Remove `DEFAULT_ITERATIONS` from `loop/telegram_bot/config.py`
- [ ] Update `Project` dataclass in `loop/telegram_bot/projects.py`: replace `is_main: bool` with `is_worktree: bool` and `parent_repo: str | None`
- **Status:** pending

### Phase 2: Rewrite projects.py Core Logic
- [ ] Add `_parse_gitdir(git_path)` helper: read `.git` file content, parse `gitdir:` path, extract parent repo name. Return `str | None`
- [ ] Rewrite `list_projects()` to single-mode scan: iterate `PROJECTS_ROOT` dirs, use `_parse_gitdir()` to detect `.git` directory (standalone, `is_worktree=False`) vs `.git` file (worktree link, `is_worktree=True`, `parent_repo` from gitdir), check `has_loop`
- [ ] Generalize `create_worktree(project_path, suffix)` to work from any repo (not just MAIN_PROJECT). Naming: `{project_name}-{suffix}`, branch: `{suffix}`. Remove `CLAUDE_template.md` copying (lines 139-144). Remove `shutil` import
- [ ] Add `clone_repo(url)` function: parse repo name from URL (last path segment, strip `.git`), `git clone`, run `loop init`, return (success, message)
- [ ] Remove all `MAIN_PROJECT` imports and references from `projects.py` (line 8 import, lines 26/45/79/123 usage)
- **Status:** pending

### Phase 3: Update bot.py UI and Handlers
- [ ] Add `ENTER_URL` state to `State` enum
- [ ] Update `show_projects()`: change icons (📁 standalone, 🔀 worktree, 🔄 running), add "➕ Klonuj repo" button at bottom
- [ ] Unify `show_project_menu()`: remove `if project.is_main` branch, show Plan/Build/Brainstorm for all projects with `has_loop`, show "🔀 Nowy worktree" for all projects, show warning + `loop init` option for projects without `has_loop`
- [ ] Add `handle_clone_url()` handler: receive URL text, call `clone_repo()`, show result, return to project list
- [ ] Update `handle_action()`: route `action:clone` → prompt for URL (→ ENTER_URL state), route `action:worktree` → prompt for name (→ ENTER_NAME state, any project)
- [ ] Update `handle_name()`: call `create_worktree(project.path, suffix)` instead of `create_worktree(suffix)`
- [ ] Register new states and handlers in `create_application()` ConversationHandler
- **Status:** pending

### Phase 4: Documentation and Cleanup
- [ ] Remove `MAIN_PROJECT` from env vars table in `CLAUDE.md` (line 47)
- [ ] Remove `MAIN_PROJECT` from env vars section in `README.md` (line 88)
- [ ] Update `COMMANDS.md`: replace "Nowy projekt - Create new git worktree (main repo only)" with "Nowy worktree" for all projects, add clone flow documentation, add icon legend (📁 🔀 🔄)
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should `tasks.py` be modified? | No — IDEA.md explicitly lists it as "No changes needed" |
| How to detect worktrees vs standalone repos? | `.git` directory = standalone; `.git` file (contains `gitdir:` path) = worktree |
| What about `CLAUDE_template.md` copying in `create_worktree`? | Remove it — IDEA.md marks it as "playground relic" |
| Should `entrypoint.sh` be modified? | No — `MAIN_PROJECT` is not currently passed to bot startup (confirmed in code). The env var just won't exist anymore |
| What happens if `loop init` fails after clone? | Return success with warning message; user can run `loop init` manually later |

## Findings & Decisions

### Requirements

**From IDEA.md — Functional Requirements:**
1. Remove `MAIN_PROJECT` config variable and all code paths depending on it
2. Remove `DEFAULT_ITERATIONS` config variable (unused)
3. Every repo in `PROJECTS_ROOT` is a first-class project
4. Any project can create worktrees (not just "main" project)
5. Add `git clone` capability from Telegram with auto `loop init`
6. New `Project` dataclass: `is_worktree` + `parent_repo` replace `is_main`
7. Unified project menu (no `is_main` branching in UI)

**From IDEA.md — Non-Goals:**
- No persistence layer (queue/tasks stay in-memory)
- No i18n (stays Polish)
- No changes to `tasks.py` (TaskManager/BrainstormManager)

### Research Findings

**Current code state (confirmed by analysis):**

| File | Current State | Required Change |
|------|---------------|-----------------|
| `config.py` | Has `MAIN_PROJECT` (line 19), `DEFAULT_ITERATIONS` (line 20) | Remove both |
| `projects.py` | `Project` has `is_main: bool`; dual-mode `list_projects()`; `create_worktree()` depends on MAIN_PROJECT | Rewrite dataclass, list_projects(), create_worktree(); add clone_repo() |
| `bot.py` | State enum lacks `ENTER_URL`; `show_project_menu()` branches on `is_main`; no clone UI | Add ENTER_URL state, clone handler, unify menu |
| `tasks.py` | No MAIN_PROJECT references | No changes needed |
| `CLAUDE.md` | `MAIN_PROJECT` in env vars table (line 47) | Remove row |
| `README.md` | `MAIN_PROJECT` in env vars (line 88) | Remove row |
| `entrypoint.sh` | Does NOT pass MAIN_PROJECT to bot (line 143) | No changes needed |

**Worktree detection approach:**
- Standalone repo: directory contains `.git/` (directory) → `is_worktree=False`, `parent_repo=None`
- Worktree: directory contains `.git` (file) with content like `gitdir: /path/to/parent/.git/worktrees/name` → `is_worktree=True`, `parent_repo` extracted from path
- Parent extracted by finding `.git` in gitdir path parts and taking the directory name before it
- No need for `git worktree list --porcelain` — simple file parsing is sufficient and faster

**MAIN_PROJECT references (complete list from codebase scan):**
- `config.py:19` — definition
- `projects.py:8` — import
- `projects.py:26,45,79,123` — usage in list_projects() and create_worktree()
- `CLAUDE.md:47` — env vars table row
- `README.md:88` — env vars table row
- `COMMANDS.md:37` — "(main repo only)" text
- `docker/.env` — NOT present
- `.devcontainer/setup-env.sh` — NOT present
- `entrypoint.sh:143` — NOT passed to bot
- `tasks.py` — NOT referenced
- `bot.py` — NOT imported directly (uses `is_main` field from Project dataclass)

**Icon mapping (from IDEA.md):**
- 📁 Standalone repo (replaces current 📂 for main)
- 🔀 Worktree (replaces current 📁)
- 🔄 Running task (unchanged)

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Single-pass directory scan instead of dual-mode | Simpler code, no MAIN_PROJECT dependency, flat project list |
| Worktree detection via `.git` file parsing | Reliable, works without running git commands for basic detection |
| `create_worktree()` takes `project_path` parameter | Any project can create worktrees, not just one designated "main" |
| Remove `CLAUDE_template.md` copy in worktree creation | Playground-era relic, not relevant in multi-repo model |
| `clone_repo()` runs `loop init` automatically | IDEA.md requires it; seamless UX for cloned repos |
| No changes to `tasks.py` | IDEA.md non-goal; TaskManager/BrainstormManager are independent of project model |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| `entrypoint.sh` listed in IDEA.md as needing changes | Confirmed it does NOT pass MAIN_PROJECT to bot (line 143). No entrypoint changes needed |
| `DEFAULT_ITERATIONS` usage unclear | Confirmed unused — never imported anywhere in codebase. Bot always shows iteration selection UI. Safe to remove |
| `config.py` also imported by `projects.py` | After removing MAIN_PROJECT, update import on line 8: `from .config import PROJECTS_ROOT` (remove MAIN_PROJECT) |
| `COMMANDS.md` not in IDEA.md file list | Line 37 says "(main repo only)" — must be updated to match unified menu |
| No `.git` file parser exists in codebase | Need to add `_parse_gitdir()` helper to projects.py for worktree detection |
| `show_project_menu()` missing `loop init` button | Line 225 only shows warning text, IDEA.md requires actionable button to run `loop init` |
| `help_command()` text | Already generic, no MAIN_PROJECT references — no changes needed |
| `bot.py` has `(main)` label in project menu | Line 167: `text = f"📁 *{project.name}* (main)\n"` — remove after unifying menu |

### Resources

- Source: `loop/telegram_bot/` (bot.py, projects.py, config.py, tasks.py, run.py)
- Design: `docs/IDEA.md`
- Data flows: Clone repo flow and Create worktree flow documented in IDEA.md
- Commands reference: `loop/telegram_bot/COMMANDS.md`
