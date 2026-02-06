# Implementation Plan

**Status:** COMPLETE
**Progress:** 18/18 (100%)

## Goal

Refactor the Telegram bot to remove the single-main-project assumption (`MAIN_PROJECT`). Every repo in `PROJECTS_ROOT` becomes a first-class project that can create worktrees. Add `git clone` capability from Telegram. Auto-run `loop init` after clone.

## Phases

### Phase 1: Config and Data Model Cleanup
- [x] Remove `MAIN_PROJECT` from `loop/telegram_bot/config.py`
- [x] Remove `DEFAULT_ITERATIONS` from `loop/telegram_bot/config.py`
- [x] Update `Project` dataclass in `loop/telegram_bot/projects.py`: replace `is_main: bool` with `is_worktree: bool` and `parent_repo: str | None`
- **Status:** complete

### Phase 2: Rewrite projects.py Core Logic
- [x] Add `_parse_gitdir(git_path)` helper
- [x] Rewrite `list_projects()` to single-mode scan
- [x] Generalize `create_worktree(project_path, suffix)` — naming: `{project_name}-{suffix}`, branch: `{suffix}`, removed `CLAUDE_template.md` copying and `shutil` import
- [x] Add `clone_repo(url)` function with auto `loop init`
- [x] Remove all `MAIN_PROJECT` imports and references from `projects.py`
- **Status:** complete

### Phase 3: Update bot.py UI and Handlers
- [x] Add `ENTER_URL` state to `State` enum
- [x] Update `show_projects()`: icons (📁 standalone, 🔀 worktree, 🔄 running), "➕ Klonuj repo" button
- [x] Unify `show_project_menu()`: removed `if project.is_main` branch, unified menu with Plan/Build/Brainstorm/Nowy worktree for all projects, `loop init` button for unconfigured projects
- [x] Add `handle_clone_url()` handler
- [x] Update `handle_action()`: route `action:clone`, `action:worktree`, `action:loop_init`
- [x] Update `handle_name()`: uses `create_worktree(project.path, suffix)` with project context
- [x] Register `ENTER_URL` state and `action:` handler in `SELECT_PROJECT` state in ConversationHandler
- **Status:** complete

### Phase 4: Documentation and Cleanup
- [x] Remove `MAIN_PROJECT` from env vars table in `CLAUDE.md`
- [x] Remove `MAIN_PROJECT` from env vars section in `README.md`
- [x] Update `COMMANDS.md`: icon legend, unified menu buttons, clone flow
- **Status:** complete

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Single-pass directory scan instead of dual-mode | Simpler code, no MAIN_PROJECT dependency, flat project list |
| Worktree detection via `.git` file parsing | Reliable, works without running git commands for basic detection |
| `create_worktree()` takes `project_path` parameter | Any project can create worktrees, not just one designated "main" |
| Remove `CLAUDE_template.md` copy in worktree creation | Playground-era relic, not relevant in multi-repo model |
| `clone_repo()` runs `loop init` automatically | IDEA.md requires it; seamless UX for cloned repos |
| No changes to `tasks.py` | IDEA.md non-goal; TaskManager/BrainstormManager are independent of project model |
| `_run_loop_init()` resolves loop binary same as tasks.py | Consistent path resolution: `/opt/loop/scripts/loop.sh` first, then project-local |
| `action:` handler added to SELECT_PROJECT state | "Klonuj repo" button lives on project list screen, needs routing before project selection |
