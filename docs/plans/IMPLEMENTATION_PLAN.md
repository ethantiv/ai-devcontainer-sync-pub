# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/35 (0%)

## Goal

Implement all features from the project ROADMAP: 4 P2 (Important) features and 2 P3 (Nice to Have) features for the autonomous development loop system and Telegram bot.

## Current Phase

Phase 1

## Phases

### Phase 1: Telegram bot — task history and log viewing
Add a "History" button to the project menu that lists recent completed tasks with their outcomes (success/fail/iterations used), and allow viewing a summary of the last log file directly in Telegram.

- [ ] Add `TaskHistory` dataclass to `src/telegram_bot/tasks.py` with fields: project, mode, iterations_completed, iterations_total, duration_seconds, status (success/fail/interrupted), started_at, finished_at, summary_path
- [ ] Add `_archive_completed_task()` method to `TaskManager` — called from `process_completed_tasks()` to persist completed task data to `.task_history.json` (atomic write, append-only, same pattern as `_archive_session()` in `BrainstormManager`)
- [ ] Add `list_task_history()` method to `TaskManager` — returns history entries sorted by `finished_at` descending, with optional project filter
- [ ] Add `get_task_log_summary()` method to `TaskManager` — reads the most recent `loop/logs/summary-latest.txt` or calls `summary.js` for a given project to return a text summary
- [ ] Add `MSG_TASK_HISTORY_*` constants to `src/telegram_bot/messages.py` — title, empty state, entry format, log summary header
- [ ] Add `show_task_history()` handler in `src/telegram_bot/handlers/tasks.py` — paginated list of completed tasks with mode icon, status emoji, duration, iterations
- [ ] Add "History" button to project menu in `src/telegram_bot/handlers/projects.py` — route `action:task_history` callback
- [ ] Add `view_task_log` callback handler — when user taps a history entry, show the log summary text (truncated to Telegram message limit)
- [ ] Add tests for `_archive_completed_task()`, `list_task_history()`, `get_task_log_summary()` in `src/telegram_bot/tests/test_tasks.py`
- [ ] Add tests for `show_task_history()` and `view_task_log` handlers in `src/telegram_bot/tests/test_bot.py`
- **Status:** pending

### Phase 2: Loop — idea seeding from file and URL sources
Extend `loop plan -I` to accept `@file.md` (read idea from file) and `https://...` (fetch issue/PR body as idea seed) in addition to inline text.

- [ ] Extend `write_idea()` in `src/scripts/loop.sh` — detect `@`-prefixed file paths (read file content) and `http(s)://` URLs (fetch with `curl`) before writing to `docs/ROADMAP.md`
- [ ] Extend `-I` option handling in `src/bin/cli.js` — pass `@file` and URL values through to `loop.sh` without modification (shell handles resolution)
- [ ] Add URL fetching logic in `loop.sh` — for GitHub issue/PR URLs, use `gh issue view --json body` or `gh pr view --json body` to extract the body; for generic URLs, use `curl -sL` with content extraction
- [ ] Add tests for file-based idea seeding — create temp file, invoke `write_idea()` with `@path`, verify ROADMAP.md content
- [ ] Add tests for URL-based idea seeding — mock `gh`/`curl` commands, verify ROADMAP.md content
- **Status:** pending

### Phase 3: Brainstorm session export and continuation
Add `/brainstorming export` command to save the full brainstorm conversation as Markdown, and allow resuming the last session with `/brainstorming continue` after bot restart.

- [ ] Add `export_session()` method to `BrainstormManager` in `src/telegram_bot/tasks.py` — reads archived session data + JSONL output file, formats as Markdown with timestamps, saves to `docs/brainstorms/{project}_{date}.md`
- [ ] Add `get_resumable_session()` method to `BrainstormManager` — finds the most recent archived session for a project that has a non-empty `last_response` and returns it
- [ ] Add `resume_archived_session()` method to `BrainstormManager` — reconstructs session state from history entry, creates new tmux session with `--resume` flag using the archived conversation
- [ ] Add `MSG_BRAINSTORM_EXPORT_*` and `MSG_BRAINSTORM_CONTINUE_*` constants to `src/telegram_bot/messages.py`
- [ ] Add "Export" button to brainstorm history entries in `src/telegram_bot/handlers/brainstorm.py` — triggers `export_session()` and sends file path confirmation
- [ ] Add "Continue last" button to brainstorm prompt in `src/telegram_bot/handlers/brainstorm.py` — triggers `resume_archived_session()` and enters BRAINSTORMING state
- [ ] Add tests for `export_session()`, `get_resumable_session()`, `resume_archived_session()` in `src/telegram_bot/tests/test_tasks.py`
- **Status:** pending

### Phase 4: Docker ARM build optimization
Move Playwright browser installation from Dockerfile build time to lazy first-use pattern triggered by `agent-browser` skill invocation.

- [ ] Remove `npx playwright install chromium` and Playwright system deps from builder stage in `docker/Dockerfile` — keep only the `PLAYWRIGHT_BROWSERS_PATH` env var
- [ ] Create `src/scripts/ensure-playwright.sh` — idempotent script that checks if Chromium is installed at `$PLAYWRIGHT_BROWSERS_PATH`, installs if missing, exits 0 if already present
- [ ] Integrate `ensure-playwright.sh` into `agent-browser` skill invocation — add a wrapper or hook that runs the script before first browser launch
- [ ] Update `docker/Dockerfile` runtime stage — remove desktop library dependencies that are only needed for Playwright (move to `ensure-playwright.sh` as `apt-get install` if needed)
- [ ] Add verification test — build Docker image, confirm Chromium is NOT present, run `ensure-playwright.sh`, confirm Chromium IS present
- **Status:** pending

### Phase 5: Loop workflow integration tests
Add end-to-end test suite exercising the full loop workflow: init, plan iteration, output artifact verification.

- [ ] Create `src/lib/__tests__/integration.test.js` — integration test file using Jest with longer timeouts
- [ ] Add test: `loop init` creates expected symlinks and directories in a temp project
- [ ] Add test: `loop init` followed by `loop update` refreshes symlinks without errors
- [ ] Add test: verify `loop summary` produces output from a sample JSONL log file
- [ ] Add `integration` npm script to `src/package.json` — runs only integration tests (separate from unit tests)
- **Status:** pending

### Phase 6: Telegram bot handler state machine diagram
Add a Mermaid state diagram to `src/telegram_bot/COMMANDS.md` showing the full conversation flow.

- [ ] Analyze all states and transitions in `src/telegram_bot/bot.py` and `handlers/common.py` — map State enum values to handler transitions
- [ ] Create Mermaid stateDiagram-v2 in `src/telegram_bot/COMMANDS.md` — show SELECT_PROJECT to PROJECT_MENU to each sub-flow (task, brainstorm, clone, create, worktree) with labeled transitions
- [ ] Verify diagram renders correctly using `beautiful-mermaid` skill
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Is there existing task history? | No. Only brainstorm history exists (`.brainstorm_history.json`). Tasks have no post-completion archival. |
| Does `-I` already support files/URLs? | No. It only accepts inline text strings. `write_idea()` in `loop.sh` writes the string directly to ROADMAP.md. |
| Is brainstorm export implemented? | No. Sessions are archived to `.brainstorm_history.json` with truncated data, but there's no Markdown export or post-restart continuation. |
| Is Playwright lazily installed? | No. It's installed during Docker image build (`npx playwright install chromium` + system deps). |
| Are there integration tests? | No. Only unit tests exist (438 Python + 20 JS). |
| Is there a state diagram? | No. COMMANDS.md lists commands but has no visual flow diagram. |

## Findings & Decisions

### Requirements

**Functional:**
- P2.1: Task history with paginated list, status/duration/iterations display, log summary viewing
- P2.2: Idea seeding from local files (`@path`) and URLs (GitHub issues/PRs, generic URLs)
- P2.3: Brainstorm export to Markdown files, session continuation after restart
- P2.4: Lazy Playwright installation on first `agent-browser` use instead of at build time
- P3.1: Integration tests for `loop init`, `loop update`, `loop summary`
- P3.2: Mermaid state diagram for bot conversation handler

**Non-functional:**
- All new features must have tests (TDD: write tests first)
- Follow existing patterns: atomic JSON persistence, async generators for long ops, `MSG_*` message constants
- Maintain backward compatibility with existing task/brainstorm flows
- Docker image must still work for users who DO use Playwright (lazy install must be reliable)

### Research Findings

- **Brainstorm history pattern** already exists and can be replicated for task history — same JSON file, atomic writes, load/save/archive/list methods
- **`loop.sh` `write_idea()`** is a simple shell function (lines 165-175) that writes `$IDEA` to `docs/ROADMAP.md` — extending to handle `@file` and `https://` prefixes is straightforward
- **`gh` CLI** is available in Docker image — can be used for GitHub issue/PR body extraction
- **`summary.js`** already has `generateSummary(logDir)` that finds latest JSONL and formats a report — can be invoked from Python via subprocess
- **Playwright deps in Dockerfile** are ~20 lines of `apt-get install` for X11/GTK libraries — these can be moved to a lazy installer script
- **Bot state machine** has 11 states defined in `handlers/common.py` `State` enum with pattern-based callback routing in `bot.py`
- **No TODOs, FIXMEs, or incomplete work** found in existing codebase — all current features are fully implemented

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse `_archive_session()` pattern for task history | Proven atomic persistence pattern, consistent codebase style |
| Handle `@file` and URL resolution in `loop.sh` (not Node.js) | Shell script already manages idea writing; `gh` CLI and `curl` are native shell tools |
| Use `gh issue view --json body` for GitHub URLs | `gh` is already installed in Docker; avoids custom API parsing |
| Lazy Playwright via idempotent shell script | Simple to integrate as pre-hook; can be run manually or automatically |
| Integration tests in Jest (not pytest) | Tests `loop init`/`update`/`summary` which are Node.js modules; keeps test tooling consistent |
| Mermaid stateDiagram-v2 in COMMANDS.md | Diagram lives next to the command documentation it describes |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| No `docs/specs/` directory exists | ROADMAP.md is sufficiently detailed for all 6 proposals; no separate specs needed |
| Brainstorm "resume" already exists for active sessions | Phase 3 is specifically about resuming ARCHIVED sessions after restart — different from existing in-session resume |

### Resources

- ROADMAP: `docs/ROADMAP.md`
- Task manager: `src/telegram_bot/tasks.py` (976 lines)
- Brainstorm history pattern: `tasks.py:523-587`
- Loop shell script: `src/scripts/loop.sh` (278 lines)
- CLI entry point: `src/bin/cli.js`
- Summary module: `src/lib/summary.js`
- Bot wiring: `src/telegram_bot/bot.py`
- State enum: `src/telegram_bot/handlers/common.py`
- Dockerfile: `docker/Dockerfile`
- Test files: `src/telegram_bot/tests/test_tasks.py`, `test_bot.py`
