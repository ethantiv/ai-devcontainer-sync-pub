# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 15/37 (41%)

## Goal

Implement all features from the project ROADMAP: 4 P2 (Important) features and 2 P3 (Nice to Have) features for the autonomous development loop system and Telegram bot.

## Current Phase

Phase 3

## Phases

### Phase 1: Telegram bot — task history and log viewing
Add a "History" button to the project menu that lists recent completed tasks with their outcomes (success/fail/iterations used), and allow viewing a summary of the last log file directly in Telegram.

- [x] Add `TaskHistory` dataclass to `src/telegram_bot/tasks.py` with fields: project, mode, iterations_completed, iterations_total, duration_seconds, status (success/fail/interrupted), started_at, finished_at, log_dir
- [x] Add `_archive_completed_task()` method to `TaskManager` — called from `process_completed_tasks()` to persist completed task data to `.task_history.json` (atomic write, append-only, same pattern as `_archive_session()`)
- [x] Add `list_task_history()` method to `TaskManager` — returns history entries sorted by `finished_at` descending, with optional project filter
- [x] Add `get_task_log_summary()` method to `TaskManager` — invokes `summary.js:generateSummary(logDir)` via subprocess, returns formatted text summary
- [x] Add `MSG_TASK_HISTORY_*` constants to `src/telegram_bot/messages.py` — title, empty state, entry format, log summary header, view log button, no log message
- [x] Add `show_task_history()` handler in `src/telegram_bot/handlers/tasks.py` — list of last 10 completed tasks with mode icon, status emoji, duration, iterations
- [x] Add "History" button to project menu in `src/telegram_bot/handlers/projects.py` — route `action:task_history` callback via `_handle_task_action()` dispatcher
- [x] Add `handle_task_history_log` callback handler — when user taps a history entry, show the log summary text (truncated to Telegram 4096 char message limit)
- [x] Add tests for `_archive_completed_task()`, `list_task_history()`, `get_task_log_summary()` in `src/telegram_bot/tests/test_tasks.py` (11 tests)
- [x] Add tests for `show_task_history()` and `handle_task_history_log` handlers in `src/telegram_bot/tests/test_bot.py` (7 tests)
- **Status:** complete

### Phase 2: Loop — idea seeding from file and URL sources
Extend `loop plan -I` to accept `@file.md` (read idea from file) and `https://...` (fetch issue/PR body as idea seed) in addition to inline text.

- [x] Extend `write_idea()` in `src/scripts/loop.sh` — added `resolve_idea()` helper that detects `@`-prefixed file paths (reads with `cat`) and `http(s)://` URLs; `write_idea()` uses quoted heredoc (`<< 'IDEA_EOF'`) to prevent shell expansion
- [x] Add URL fetching logic in `resolve_idea()` — GitHub issue URLs use `gh issue view --json body -q .body`, PR URLs use `gh pr view --json body -q .body`, generic URLs use `curl -sL` with HTML tag stripping; all emit warnings and return 1 on failure
- [x] Verify `-I` option passthrough in `src/bin/cli.js` (line 12) and `src/lib/run.js` (line 34) — confirmed `@file` and URL values pass through unmodified to `loop.sh` via Commander.js parsing and `args.push('-I', opts.idea)`
- [x] Add shell tests for file-based idea seeding — 18 tests in `src/scripts/tests/test_write_idea.sh` covering @file, inline text, special chars
- [x] Add shell tests for URL-based idea seeding — mock `gh`/`curl` commands in same test file, verify ROADMAP.md content for GitHub issues, PRs, and generic URLs
- **Status:** complete

### Phase 3: Brainstorm session export and continuation
Add export command to save the full brainstorm conversation as Markdown, and allow resuming the last archived session after bot restart.

- [ ] Preserve full conversation on session finish — before `_cleanup_session()` deletes the JSONL output file (tasks.py:706), copy/read its content for archival; extend `_archive_session()` to store full conversation text (not just 500-char truncation)
- [ ] Add `export_session()` method to `BrainstormManager` — reads archived session data with full conversation, formats as Markdown with timestamps and turn separators, saves to `docs/brainstorms/{project}_{date}.md`
- [ ] Add `get_resumable_session()` method to `BrainstormManager` — finds the most recent archived session for a project that has non-empty conversation data and returns it
- [ ] Add `resume_archived_session()` method to `BrainstormManager` — reconstructs session state from history entry, creates new tmux session with `--resume` flag using the archived conversation as context seed
- [ ] Add `MSG_BRAINSTORM_EXPORT_*` and `MSG_BRAINSTORM_CONTINUE_*` constants to `src/telegram_bot/messages.py`
- [ ] Add "Export" button to brainstorm history entries in `src/telegram_bot/handlers/brainstorm.py` (show_brainstorm_history at lines 104-147) — triggers `export_session()` and sends file path confirmation
- [ ] Add "Continue last" button to brainstorm prompt in `src/telegram_bot/handlers/brainstorm.py` — triggers `resume_archived_session()` and enters BRAINSTORMING state
- [ ] Add tests for `export_session()`, `get_resumable_session()`, `resume_archived_session()` in `src/telegram_bot/tests/test_tasks.py`
- **Status:** pending

### Phase 4: Docker ARM build optimization
Move Playwright browser installation from Dockerfile build time to lazy first-use pattern triggered by `agent-browser` skill invocation.

- [ ] Remove `npx playwright install chromium --with-deps` from builder stage in `docker/Dockerfile` (line 25) — keep only the `PLAYWRIGHT_BROWSERS_PATH` env var (line 113)
- [ ] Create `src/scripts/ensure-playwright.sh` — idempotent script that: checks if Chromium exists at `$PLAYWRIGHT_BROWSERS_PATH`, installs system deps via `apt-get` if needed (libnss3, libnspr4, libatk1.0-0, libatk-bridge2.0-0, libcups2, libdrm2, libxkbcommon0, libxcomposite1, libxdamage1, libxfixes3, libxrandr2, libgbm1, libasound2, libpango-1.0-0, libcairo2, libatspi2.0-0), runs `npx playwright install chromium`, exits 0 if already present
- [ ] Remove Playwright system deps from runtime stage apt-get in `docker/Dockerfile` (lines 48-50) — these will be installed lazily by `ensure-playwright.sh`
- [ ] Remove Playwright browser copy chain from Dockerfile — remove builder COPY at line 74 (`/root/.cache/ms-playwright` → `/opt/playwright`) and user copy at lines 89-91 (`mkdir`, `cp -r`, `chown`)
- [ ] Integrate `ensure-playwright.sh` into `agent-browser` skill — add as PreToolUse hook or wrapper that runs the script before first browser launch
- [ ] Add verification test — build Docker image, confirm Chromium is NOT present, run `ensure-playwright.sh`, confirm Chromium IS present and `agent-browser` works
- **Status:** pending

### Phase 5: Loop workflow integration tests
Add end-to-end test suite exercising the full loop workflow: init, plan iteration, output artifact verification.

- [ ] Create `src/lib/__tests__/integration.test.js` — integration test file using Jest with longer timeouts (30s+)
- [ ] Add test: `loop init` creates expected symlinks (`loop/loop.sh`, `loop/PROMPT_plan.md`, `loop/PROMPT_build.md`, `loop/cleanup.sh`, `loop/notify-telegram.sh`, `loop/kill-loop.sh`) and directories (`docs/plans/`, `loop/logs/`, `.claude/skills/`) in a temp project
- [ ] Add test: `loop init` followed by `loop update` (force=true) refreshes symlinks without errors and updates `.version` file
- [ ] Add test: verify `loop summary` produces formatted output from a sample JSONL log file (test `generateSummary()` end-to-end, currently only component functions are unit-tested)
- [ ] Add `test:integration` npm script to `src/package.json` — runs only integration tests (separate from unit `test` script)
- **Status:** pending

### Phase 6: Telegram bot handler state machine diagram
Add a Mermaid state diagram to `src/telegram_bot/COMMANDS.md` showing the full conversation flow.

- [ ] Analyze all 10 states and 40+ transitions in `src/telegram_bot/bot.py` and `handlers/common.py` — map State enum values (SELECT_PROJECT=1 through GITHUB_CHOICE=10) to handler transitions across all 5 handler modules
- [ ] Create Mermaid stateDiagram-v2 in `src/telegram_bot/COMMANDS.md` — show entry points (/start, /projects, /status, /brainstorming, /history), SELECT_PROJECT → PROJECT_MENU → each sub-flow (task with ENTER_IDEA→SELECT_ITERATIONS, brainstorm with ENTER_BRAINSTORM_PROMPT→BRAINSTORMING, clone ENTER_URL, create ENTER_PROJECT_NAME→GITHUB_CHOICE, worktree ENTER_NAME), self-loops, and fallback transitions
- [ ] Verify diagram renders correctly using `beautiful-mermaid` skill
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Is there existing task history? | **Yes (Phase 1 complete).** `TaskManager` now archives completed tasks to `.task_history.json` with atomic writes. History is viewable in Telegram via "History" button. |
| Does `-I` already support files/URLs? | **Yes (Phase 2 complete).** `resolve_idea()` in `loop.sh` handles `@file` paths, GitHub issue/PR URLs (via `gh`), and generic URLs (via `curl`). Quoted heredoc prevents shell expansion. 18 shell tests in `src/scripts/tests/test_write_idea.sh`. |
| Is brainstorm export implemented? | No. `_archive_session()` stores only truncated data (topic: 100 chars, last_response: 500 chars). Full JSONL output is deleted in `_cleanup_session()`. No Markdown export or post-restart continuation. |
| Is Playwright lazily installed? | No. Builder stage runs `npx playwright install chromium --with-deps` (Dockerfile:25). Runtime copies browsers from builder and installs 16 system deps (lines 48-50). |
| Are there integration tests? | Partial. 456 Python + 20 JS + 18 shell tests. Shell tests cover `resolve_idea()`/`write_idea()`. `init.js`, `run.js`, `cleanup.js`, `cli.js` have zero tests. `generateSummary()` is not tested end-to-end. |
| Is there a state diagram? | No. COMMANDS.md documents commands and buttons but has no Mermaid diagram. |
| How many bot states exist? | 10 states in `State` enum (SELECT_PROJECT through GITHUB_CHOICE), 5 entry points, 40+ transitions across 5 handler modules. ROADMAP.md says "9 states" which is outdated — GITHUB_CHOICE was added later. |

## Findings & Decisions

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse `_archive_session()` pattern for task history | Proven atomic persistence pattern at tasks.py:548-571, consistent codebase style |
| Handle `@file` and URL resolution in `loop.sh` (not Node.js) | Shell script already manages idea writing; `gh` CLI and `curl` are native shell tools |
| Use `gh issue view --json body -q .body` for GitHub URLs | `gh` is already installed in Docker; avoids custom API parsing; `-q .body` extracts cleanly |
| Use quoted heredoc (`<< 'EOF'`) for fetched content | Prevents shell expansion of `$`, backticks in fetched issue/PR bodies |
| Preserve full JSONL before cleanup for brainstorm export | Current `_cleanup_session()` deletes output file; must read before delete |
| Lazy Playwright via idempotent `ensure-playwright.sh` | Simple to integrate as pre-hook; can be run manually or automatically; exits 0 if already present |
| Integration tests in Jest (not pytest) | Tests `loop init`/`update`/`summary` which are Node.js modules; keeps test tooling consistent with existing `summary.test.js` |
| Mermaid stateDiagram-v2 in COMMANDS.md | Diagram lives next to the command documentation it describes; `beautiful-mermaid` skill for rendering |
| Scope limited to ROADMAP.md proposals only | No new features beyond the 6 documented proposals; pattern fixes (orphaned MSG_*, missing decorator) are out of scope |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| No `docs/specs/` directory exists | ROADMAP.md is sufficiently detailed for all 6 proposals; no separate specs needed |
| Brainstorm "resume" already exists for active sessions | Phase 3 is specifically about resuming ARCHIVED sessions after restart — different from existing in-session resume at brainstorm.py:409-437 |
| `_archive_session()` truncates data (500 chars) | Phase 3 must preserve full conversation before `_cleanup_session()` deletes output file |
| `write_idea()` uses unquoted heredoc | Resolved: switched to `<< 'IDEA_EOF'` quoted heredoc in Phase 2 |
| `.devcontainer/Dockerfile` also has Playwright | Phase 4 only targets `docker/Dockerfile` (production); devcontainer can retain build-time install for development speed |

### Resources

- ROADMAP: `docs/ROADMAP.md`
- Task manager: `src/telegram_bot/tasks.py`
- Loop shell script: `src/scripts/loop.sh`
- Summary module: `src/lib/summary.js` (`generateSummary` at line 182)
- Bot wiring: `src/telegram_bot/bot.py`
- Messages: `src/telegram_bot/messages.py`
- Dockerfile: `docker/Dockerfile`
- Test files: `src/telegram_bot/tests/` (456 tests), `lib/__tests__/summary.test.js` (20 tests), `src/scripts/tests/test_write_idea.sh` (18 tests)
