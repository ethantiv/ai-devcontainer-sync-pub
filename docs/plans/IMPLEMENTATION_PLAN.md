# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/20 (0%)
**Last Verified:** 2026-02-08

## Goal

Implement current proposals from docs/ROADMAP.md: P2 (Important) reduce bot.py size by extracting handler modules, and P3 (Nice to Have) pagination for project list in Telegram. P1 (Critical) project creation UI flow is already fully implemented — ROADMAP entry is stale.

## Current Phase

Phase 1: Extract Handler Modules from bot.py

## Phases

### Phase 1: Extract Handler Modules from bot.py (P2-Important)
- [ ] Create `src/telegram_bot/handlers/` package with `__init__.py` that re-exports all handler functions needed by `bot.py`
- [ ] Extract shared helpers to `src/telegram_bot/handlers/common.py`: `State` enum (line 162), `user_data_store` (line 178), `get_user_data()` (line 212), `authorized`/`authorized_callback` decorators (lines 181, 197), `reply_text()` (line 217), `_cancel_keyboard()` (line 235), `_nav_keyboard()` (line 263), `_brainstorm_hint_keyboard()` (line 242), `_brainstorm_hint_long_keyboard()` (line 252), `_is_brainstorm_error()` (line 230). Also include generic handlers: `cancel()` (line 1363), `help_command()` (line 1374), `handle_input_cancel()` (line 1278) — these are shared fallbacks used across all states
- [ ] Extract project handlers to `src/telegram_bot/handlers/projects.py`: `start()` (line 280), `show_projects()` (line 292), `project_selected()` (line 333), `show_project_menu()` (line 353), `handle_name()` (line 662), `handle_clone_url()` (line 692), `handle_project_name()` (line 715), `handle_github_choice()` (line 757), plus project-related action branches from handle_action(): back, back_to_project, create_project, clone, worktree, loop_init, sync (7 of 14 branches)
- [ ] Extract task handlers to `src/telegram_bot/handlers/tasks.py`: `handle_idea()` (line 803), `skip_idea()` (line 871), `handle_idea_button()` (line 1291), `show_iterations_menu()` (line 880), `handle_iterations()` (line 906), `handle_custom_iterations()` (line 933), `start_task()` (line 954), `show_status()` (line 1011), `show_queue()` (line 601), `handle_cancel_queue()` (line 641), plus task-related action branches: status, plan, build, attach, queue (5 of 14 branches)
- [ ] Extract brainstorm handlers to `src/telegram_bot/handlers/brainstorm.py`: `start_brainstorming()` (line 1081), `handle_brainstorm_prompt()` (line 815), `handle_brainstorm_message()` (line 1143), `handle_brainstorm_action()` (line 1217), `handle_brainstorm_hint_button()` (line 1316), `finish_brainstorming()` (line 1183), `cancel_brainstorming()` (line 1258), `show_brainstorm_history()` (line 1034), plus brainstorm-related action branches: brainstorm, resume_brainstorm (2 of 14 branches)
- [ ] Extract background jobs to `src/telegram_bot/handlers/jobs.py`: `_format_completion_summary()` (line 1384), `check_task_completion()` (line 1434), `check_task_progress()` (line 1515), `run_log_rotation()` (line 1574), `handle_completion_diff()` (line 1591)
- [ ] Refactor `handle_action()` mega-dispatcher (lines 443-598, 14 branches): split into `_handle_project_action()` (7 branches), `_handle_task_action()` (5 branches), `_handle_brainstorm_action_dispatch()` (2 branches) in respective handler modules, keep thin `handle_action()` router in `bot.py` that delegates to sub-dispatchers
- [ ] Slim down `bot.py` to thin wiring layer: imports from handler modules, `create_application()` function (currently 90 lines at 1634-1723) with ConversationHandler wiring (10 states, 5 entry points, 3 fallbacks), 1 standalone callback handler, 3 job_queue registrations — target ~150 lines total
- [ ] Update all test imports in `test_bot.py`: 18 unique patched items (`TELEGRAM_CHAT_ID`, `STALE_THRESHOLD`, `PROJECTS_ROOT`, `task_manager`, `brainstorm_manager`, `get_user_data`, `pull_project`, `check_remote_updates`, `get_plan_progress`, `get_diff_stats`, `get_recent_commits`, `rotate_logs`, `cleanup_brainstorm_files`, `show_project_menu`, `show_projects`, `show_iterations_menu`, `get_project`, `os.path.getmtime`) across ~100 patch locations must reference new module paths. No other test files reference bot.py — changes isolated to test_bot.py
- [ ] Run full test suite — all 424 Python tests must pass with zero regressions
- **Status:** pending

### Phase 2: Pagination for Project List (P3-Nice to Have)
- [ ] Add pagination constants to `config.py`: `PROJECTS_PER_PAGE` (default 5, no env var — hardcoded is fine for UI layout)
- [ ] Add message constants to `messages.py`: `MSG_PAGE_PREV_BTN` ("< Prev"), `MSG_PAGE_NEXT_BTN` ("Next >"), `MSG_PAGE_INDICATOR` ("Page {current}/{total}")
- [ ] Add page state to `user_data`: store `projects_page` (int, default 0) in `get_user_data()` dict, reset to 0 on `/start` and `/projects`
- [ ] Refactor `show_projects()` in project handler module: slice `projects[page*5:(page+1)*5]`, add Prev/Next navigation row with `callback_data="page:prev"` and `page:next`, show page indicator in message text, preserve Create/Clone footer on every page
- [ ] Add `handle_page_navigation()` callback handler for `page:prev`/`page:next` patterns — update `user_data["projects_page"]`, call `show_projects()`
- [ ] Register page navigation handler in `State.SELECT_PROJECT` state mapping
- [ ] Write tests for pagination: page boundaries (first/last page), button visibility (no Prev on first, no Next on last), page state reset on /start, empty projects, single page (<=5 projects), multi-page navigation
- [ ] Write tests for page navigation handler: prev/next callbacks, boundary clamping
- [ ] Run full test suite — all tests must pass
- [ ] Update `COMMANDS.md` if project list behavior description needs updating
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Is P1 project creation UI already implemented? | Yes — fully implemented. Backend (validate_project_name, create_project, create_github_repo in projects.py), UI flow (handle_project_name at bot.py:715, handle_github_choice at bot.py:756), states (ENTER_PROJECT_NAME, GITHUB_CHOICE), 16 MSG_* constants (messages.py:256-283), and "Create project" button in project list (bot.py:299,323). ROADMAP entry is stale |
| How big is bot.py? | 1,724 lines — largest file in codebase. Contains 45 functions (41 async + 4 regular), 3 background jobs, 14 action dispatcher branches, all inline |
| Is there a handlers/ directory? | No — flat module layout. No existing handler extraction pattern |
| What modules exist in telegram_bot? | bot.py (1724), tasks.py (976), projects.py (381), messages.py (283), log_rotation.py (174), git_utils.py (172), config.py (134), run.py (38), __init__.py (1) |
| Does show_projects() have pagination? | No — renders all projects in one message with 2-column grid. No page state, no prev/next buttons |
| Is there an existing pagination pattern? | Brainstorm history (bot.py:1034) uses PAGE_SIZE=10 with static "...and N more" text, no interactive navigation buttons |
| How many tests exist? | 424 Python (test_bot=114, test_tasks=123, test_projects=71, test_config=64, test_git_utils=34, test_log_rotation=18) + 20 JS = 444 total |
| Are there tests for project creation handlers? | Only 2 lightweight tests in test_bot.py (cancel keyboard presence at line 162, no /cancel in message at line 197). Backend has 10+ tests in test_projects.py. No direct tests for handle_project_name() or handle_github_choice() handler logic |
| Any TODOs/FIXMEs/skipped tests? | None — codebase is clean |
| How does handle_action() work? | Mega-dispatcher (bot.py:443-598, 155 lines) with exactly 14 if-branches routing callback_data prefixed with "action:" to different flows: 7 project (back, back_to_project, create_project, clone, worktree, loop_init, sync), 5 task (status, plan, build, attach, queue), 2 brainstorm (brainstorm, resume_brainstorm) |
| Are there unaccounted functions? | 3 functions were missing from handler groups: `cancel()` (line 1363), `help_command()` (line 1374), `handle_input_cancel()` (line 1278) — generic fallback handlers, assigned to common.py |
| What patch locations need updating? | test_bot.py has 18 unique patched items across ~100 locations. No other test files reference bot.py — changes fully isolated |
| What does run.py import from bot.py? | Only `create_application` — the single external entry point. No changes needed to run.py after handler extraction |
| Does conftest.py have bot.py fixtures? | No — `make_callback_update` helper and mock patterns are defined inline in test_bot.py (2,129 lines, 114 tests, 23 test classes) |
| Does COMMANDS.md describe pagination? | No — describes project list as flat button grid with status icons. Needs updating after Phase 2 |
| How many handler functions lack tests? | 19 of 45 — mostly core conversation flow handlers (project CRUD, iteration selection, brainstorm start/message/finish). Out of scope for P2/P3 |

## Findings & Decisions

### Requirements

**P1 — Project Creation UI (Critical) — ALREADY COMPLETE:**
- ROADMAP states: "Backend functions are implemented but Telegram bot UI (Phase 3) was never built"
- **Reality**: Full UI flow exists — `handle_project_name()` (bot.py:715-753), `handle_github_choice()` (bot.py:756-799), states `ENTER_PROJECT_NAME` and `GITHUB_CHOICE` in ConversationHandler (bot.py:1682-1689), "Create project" button in project list (bot.py:299,323), and all 16 MSG_* constants (messages.py:256-283)
- **Action**: No implementation needed. ROADMAP entry should be removed in next `/roadmap` update

**P2 — Reduce bot.py Size (Important):**
- Extract handlers into `handlers/` package with 5 modules: `common.py` (shared), `projects.py`, `tasks.py`, `brainstorm.py`, `jobs.py`
- Keep `bot.py` as thin wiring layer (~150 lines) with `create_application()` only
- Split `handle_action()` mega-dispatcher into domain-specific sub-dispatchers
- Update all test imports to reference new module paths

**P3 — Pagination for Project List (Nice to Have):**
- 5 projects per page with Prev/Next inline keyboard buttons
- Page state stored in `user_data["projects_page"]`
- Create/Clone footer preserved on every page
- Page indicator in message text

### Research Findings

- **bot.py is 1,724 lines** with 45 functions (41 async handlers + 4 regular) — the largest file by far
- **handle_action() is a 155-line mega-dispatcher** (lines 443-598) with exactly 14 if-branches: 7 project (back, back_to_project, create_project, clone, worktree, loop_init, sync), 5 task (status, plan, build, attach, queue), 2 brainstorm (brainstorm, resume_brainstorm)
- **Handler groups are cleanly separable** by domain (verified line counts): shared helpers (162-278, 117 lines), projects (280-800, 521 lines), tasks (802-1031, 230 lines), brainstorm (1033-1360, 328 lines), background jobs + generic handlers (1362-1632, 271 lines), create_application wiring (1634-1724, 91 lines)
- **3 functions missing from original handler groups**: `cancel()` (line 1363), `help_command()` (line 1374), `handle_input_cancel()` (line 1278) — generic fallback/cancel handlers used across all states, should go to `common.py`
- **No circular import risk**: bot.py imports from config, messages, tasks, projects, git_utils, log_rotation — all one-way. Extracting handlers won't create circular dependencies as long as `common.py` has shared state/helpers
- **test_bot.py has 18 unique patched items** across ~100 patch locations: module constants (`TELEGRAM_CHAT_ID`, `STALE_THRESHOLD`, `PROJECTS_ROOT`), manager instances (`task_manager`, `brainstorm_manager`), functions imported from other modules (`pull_project`, `check_remote_updates`, `get_plan_progress`, `get_diff_stats`, `get_recent_commits`, `rotate_logs`, `cleanup_brainstorm_files`), UI functions (`show_project_menu`, `show_projects`, `show_iterations_menu`, `get_project`), helpers (`get_user_data`, `os.path.getmtime`). No other test files reference bot.py — test changes fully isolated to test_bot.py
- **`user_data_store` is a module-level dict** shared across all handlers — must live in `common.py`
- **Existing pagination in brainstorm history** (bot.py:1034) is non-interactive (static text "...and N more"), not a reusable pattern
- **Codebase is clean**: zero TODO/FIXME/HACK comments, zero skipped/xfail tests, zero NotImplementedError, only 3 legitimate `# noqa: ARG001` for unused Telegram handler params
- **Per-file test breakdown**: test_bot.py=114, test_tasks.py=123, test_projects.py=71, test_config.py=64, test_git_utils.py=34, test_log_rotation.py=18 (424 total)
- **create_application()** is 90 lines (1634-1723): builds ConversationHandler with 5 entry points, 10 states, 3 fallbacks, 1 standalone callback handler, 3 job_queue registrations. After extraction: ~150 lines for bot.py (imports + create_application)
- **ConversationHandler state machine** (bot.py:1638-1704) maps 10 states to handler functions — must import from handler modules after extraction
- **No pagination infrastructure exists**: no `PROJECTS_PER_PAGE` in config.py, no `MSG_PAGE_*` in messages.py, no page state in user_data, no `handle_page_navigation()`, no `page:prev`/`page:next` callback patterns registered
- **run.py imports only `create_application` from bot.py** — no other external modules reference bot.py internals. Handler extraction is safe as long as `create_application()` stays in bot.py
- **conftest.py has no bot.py fixtures** — `make_callback_update` helper and mock patterns live inside test_bot.py itself, not in shared fixtures
- **COMMANDS.md does not mention pagination** — needs updating after Phase 2 implementation
- **19 of 45 bot.py handler functions have zero direct tests** (start, show_projects, project_selected, handle_name, handle_clone_url, handle_project_name, handle_github_choice, handle_idea, handle_brainstorm_prompt, skip_idea, show_iterations_menu, handle_iterations, handle_custom_iterations, show_status, show_queue, handle_cancel_queue, start_brainstorming, handle_brainstorm_message, finish_brainstorming) — existing test coverage focuses on UI helpers, background jobs, and callback button handlers. Handler test gaps are out of scope for this plan (P2/P3 only)

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 5 handler modules (common, projects, tasks, brainstorm, jobs) | Matches logical handler groupings visible in bot.py. Each module is 100-325 lines — manageable size |
| `common.py` for shared state and helpers | `State` enum, decorators, user_data_store, and keyboard helpers are used by all handler modules — must be in one shared location |
| Split handle_action() into sub-dispatchers | 155-line mega-dispatcher mixes 3 domains. Sub-dispatchers in respective modules keep routing logic close to handler code |
| Keep `bot.py` as thin wiring layer | Preserves existing import patterns — `run.py` imports `create_application` from `bot.py`. No external API changes |
| `handlers/__init__.py` re-exports all handlers | `bot.py` can `from .handlers import start, show_projects, ...` — clean import without deep paths |
| 5 projects per page (hardcoded constant) | ROADMAP specifies 5. No need for env var — UI layout rarely changes |
| Page state in user_data dict | Follows existing pattern (user_data["project"], user_data["mode"]) — no new infrastructure needed |
| Interactive Prev/Next buttons (not static text) | ROADMAP explicitly requests "Next/Previous navigation buttons" — must be inline keyboard buttons |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| ROADMAP P1 says project creation UI not built | Verified: fully implemented (bot.py:715-799, messages.py:256-283). ROADMAP is stale — P1 requires no work |
| handle_action() mixes all domains | Plan splits 14 branches into 3 sub-dispatchers per handler module, thin router in bot.py |
| test_bot.py patches module-level constants | 18 unique patched items across ~100 locations in test_bot.py. Phase 1 task 9 explicitly covers updating all test imports after extraction. No other test files reference bot.py |
| 3 functions missing from handler groups | `cancel()`, `help_command()`, `handle_input_cancel()` are generic fallbacks — assigned to common.py in updated plan |
| Brainstorm history pagination is non-interactive | P3 implements proper interactive pagination with Prev/Next buttons — different from existing brainstorm history pattern |

### Resources
- python-telegram-bot ConversationHandler docs — for state machine wiring
- Telegram Bot API InlineKeyboardMarkup — max 100 buttons, 8 buttons per row practical limit
- Existing codebase patterns for handler decorators and keyboard helpers
