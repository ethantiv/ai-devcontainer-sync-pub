# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 1/37 (3%)

## Goal

Implement all features from the project ROADMAP: 4 P2 (Important) features and 2 P3 (Nice to Have) features for the autonomous development loop system and Telegram bot.

## Current Phase

Phase 1

## Phases

### Phase 1: Telegram bot — task history and log viewing
Add a "History" button to the project menu that lists recent completed tasks with their outcomes (success/fail/iterations used), and allow viewing a summary of the last log file directly in Telegram.

- [ ] Add `TaskHistory` dataclass to `src/telegram_bot/tasks.py` with fields: project, mode, iterations_completed, iterations_total, duration_seconds, status (success/fail/interrupted), started_at, finished_at, summary_path
- [ ] Add `_archive_completed_task()` method to `TaskManager` — called from `process_completed_tasks()` to persist completed task data to `.task_history.json` (atomic write, append-only, same pattern as `_archive_session()` in `BrainstormManager` at tasks.py:548-571)
- [ ] Add `list_task_history()` method to `TaskManager` — returns history entries sorted by `finished_at` descending, with optional project filter
- [ ] Add `get_task_log_summary()` method to `TaskManager` — invokes `summary.js:generateSummary(logDir)` via subprocess for a given project's `loop/logs/` directory, returns formatted text summary
- [ ] Add `MSG_TASK_HISTORY_*` constants to `src/telegram_bot/messages.py` — title, empty state, entry format, log summary header (follow existing `MSG_BRAINSTORM_HISTORY_*` pattern at messages.py:224-230)
- [ ] Add `show_task_history()` handler in `src/telegram_bot/handlers/tasks.py` — paginated list of completed tasks with mode icon (◇ plan/▪ build), status emoji, duration, iterations
- [ ] Add "History" button to project menu in `src/telegram_bot/handlers/projects.py` — route `action:task_history` callback via `_handle_task_action()` dispatcher
- [ ] Add `view_task_log` callback handler — when user taps a history entry, show the log summary text (truncated to Telegram 4096 char message limit)
- [ ] Add tests for `_archive_completed_task()`, `list_task_history()`, `get_task_log_summary()` in `src/telegram_bot/tests/test_tasks.py`
- [ ] Add tests for `show_task_history()` and `view_task_log` handlers in `src/telegram_bot/tests/test_bot.py`
- **Status:** pending

### Phase 2: Loop — idea seeding from file and URL sources
Extend `loop plan -I` to accept `@file.md` (read idea from file) and `https://...` (fetch issue/PR body as idea seed) in addition to inline text.

- [ ] Extend `write_idea()` in `src/scripts/loop.sh` (lines 165-175) — detect `@`-prefixed file paths (read file content with `cat`) and `http(s)://` URLs before writing to `docs/ROADMAP.md`; use quoted heredoc (`<< 'EOF'`) to prevent shell expansion of special chars in fetched content
- [ ] Add URL fetching logic in `write_idea()` — for GitHub issue/PR URLs, use `gh issue view --json body -q .body` or `gh pr view --json body -q .body`; for generic URLs, use `curl -sL` with content extraction; emit warning and skip on failure
- [x] Verify `-I` option passthrough in `src/bin/cli.js` (line 12) and `src/lib/run.js` (line 34) — confirmed `@file` and URL values pass through unmodified to `loop.sh` via Commander.js parsing and `args.push('-I', opts.idea)`
- [ ] Add shell tests for file-based idea seeding — create temp file, invoke `write_idea()` with `@path`, verify ROADMAP.md content
- [ ] Add shell tests for URL-based idea seeding — mock `gh`/`curl` commands, verify ROADMAP.md content
- **Status:** pending

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
| Is there existing task history? | No. Only brainstorm history exists (`.brainstorm_history.json`). Tasks have no post-completion archival — `process_completed_tasks()` removes completed tasks from `active_tasks` dict without saving. |
| Does `-I` already support files/URLs? | No. `write_idea()` in `loop.sh` (lines 165-175) writes `$IDEA` directly to `docs/ROADMAP.md` using an unquoted heredoc. No detection for `@` prefix or `http(s)://` URLs. However, `-I` passthrough from cli.js → run.js → loop.sh works correctly and requires no changes. |
| Is brainstorm export implemented? | No. `_archive_session()` stores only truncated data (topic: 100 chars, last_response: 500 chars). Full JSONL output is deleted in `_cleanup_session()`. No Markdown export or post-restart continuation. |
| Is Playwright lazily installed? | No. Builder stage runs `npx playwright install chromium --with-deps` (Dockerfile:25). Runtime copies browsers from builder and installs 16 system deps (lines 48-50). |
| Are there integration tests? | No. Only unit tests: 438 Python + 20 JS. `init.js`, `run.js`, `cleanup.js`, `cli.js` have zero tests. `generateSummary()` is not tested end-to-end. |
| Is there a state diagram? | No. COMMANDS.md documents commands and buttons but has no Mermaid diagram. |
| How many bot states exist? | 10 states in `State` enum (SELECT_PROJECT through GITHUB_CHOICE), 5 entry points, 40+ transitions across 5 handler modules. ROADMAP.md says "9 states" which is outdated — GITHUB_CHOICE was added later. |

## Findings & Decisions

### Requirements

**Functional:**
- P2.1: Task history with paginated list, status/duration/iterations display, log summary viewing via `summary.js`
- P2.2: Idea seeding from local files (`@path`) and URLs (GitHub issues/PRs via `gh`, generic URLs via `curl`)
- P2.3: Brainstorm export to Markdown files in `docs/brainstorms/`, session continuation from archived history after restart
- P2.4: Lazy Playwright installation on first `agent-browser` use instead of at Docker build time

**Non-functional:**
- P3.1: Integration tests for `loop init`, `loop update`, `loop summary` (Jest, longer timeouts)
- P3.2: Mermaid state diagram for bot conversation handler (10 states, 40+ transitions)

**Cross-cutting:**
- All new features must have tests (TDD: write tests first)
- Follow existing patterns: atomic JSON persistence (`os.replace()`), async generators for long ops, `MSG_*` message constants
- Maintain backward compatibility with existing task/brainstorm flows
- Docker image must still work for users who DO use Playwright (lazy install must be reliable)

### Research Findings

- **Brainstorm history pattern** at `tasks.py:548-571` — proven archival pattern with atomic JSON, append-only history, load/save/list methods; replicate for task history
- **`write_idea()` in `loop.sh:165-175`** — simple shell function using unquoted heredoc (`<< EOF`); extending to detect `@file`/URL prefixes is straightforward; current heredoc expands `$` variables which is a risk with fetched content — must switch to `<< 'EOF'`
- **`-I` option passthrough verified** — cli.js (line 12) uses Commander.js `.option('-I, --idea <text>')`, run.js (line 34) passes via `args.push('-I', opts.idea)`, loop.sh (line 195) receives via `getopts "...I:"`. All pass `@file` and URL values unmodified. No changes needed.
- **`gh` CLI** available in Docker image — `gh issue view --json body -q .body` and `gh pr view --json body -q .body` extract issue/PR body cleanly
- **`summary.js:generateSummary(logDir)`** — finds latest JSONL, parses tool usage/tokens/test results, returns formatted report; can be invoked from Python via `subprocess.run(['node', '-e', '...'])`
- **Playwright in Dockerfile** — builder installs with `--with-deps` (line 25), copies to `/opt/playwright` (line 74), user copies to `$HOME/.cache/ms-playwright` (lines 89-91); runtime installs 16 X11/GTK system deps (lines 48-50); `.devcontainer/Dockerfile` has parallel structure (lines 23, 46-61, 70, 80)
- **Bot state machine** — 10 states in `State` enum at `handlers/common.py:25-37` (using `auto()`), 5 entry points in `bot.py:103-109`, 3 action dispatchers (`_handle_project_action`, `_handle_task_action`, `_handle_brainstorm_action_dispatch`), 12 callback data prefixes
- **No TODOs, FIXMEs, or incomplete work** in production code — all 3 `pass` statements in non-test code are legitimate exception handlers (tasks.py:708, git_utils.py:24, git_utils.py:91)
- **No empty test classes, no skipped/flaky tests** — all 68 test classes across 6 Python test files + 1 JS test file contain test methods
- **Test counts** — 438 Python tests across 6 files (test_tasks.py, test_bot.py, test_projects.py, test_git_utils.py, test_config.py, test_log_rotation.py) + 20 JS tests in summary.test.js = 458 total
- **3 orphaned MSG_* constants** in messages.py never imported: `MSG_LOG_ROTATION_COMPLETE`, `MSG_PROJECT_CREATE_FAILED`, `MSG_TASK_QUEUED` (out of scope)
- **1 non-atomic write** — `idea_file.write_text(idea_content)` at tasks.py:948 in `BrainstormManager.finish()` (out of scope — writes to project's docs/ROADMAP.md, not to state files)
- **`handle_completion_diff()` in jobs.py** missing `@authorized_callback` decorator but manually checks chat ID (out of scope — authorization handled inline)

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
| `write_idea()` uses unquoted heredoc | Phase 2 must switch to quoted heredoc (`<< 'EOF'`) to safely handle fetched content with `$` or backticks |
| `.devcontainer/Dockerfile` also has Playwright | Phase 4 only targets `docker/Dockerfile` (production); devcontainer can retain build-time install for development speed |
| 3 orphaned MSG_* constants in messages.py | Out of scope: `MSG_LOG_ROTATION_COMPLETE`, `MSG_PROJECT_CREATE_FAILED`, `MSG_TASK_QUEUED` — existing code works correctly |
| `handle_completion_diff()` missing `@authorized_callback` | Out of scope; manual auth check at jobs.py:264-266 is functionally equivalent |
| ROADMAP.md says "9 states" but code has 10 | GITHUB_CHOICE (state 10) was added after ROADMAP was written; plan correctly uses 10 |
| Phase 2 task 3 already verified | `-I` passthrough works unmodified through cli.js → run.js → loop.sh; marked as complete |

### Resources

- ROADMAP: `docs/ROADMAP.md`
- Task manager: `src/telegram_bot/tasks.py` (976 lines)
- Brainstorm history pattern: `tasks.py:548-571` (`_archive_session`)
- Brainstorm cleanup: `tasks.py:700-709` (`_cleanup_session`)
- Loop shell script: `src/scripts/loop.sh` (278 lines, `write_idea` at 165-175)
- CLI entry point: `src/bin/cli.js` (idea option at line 12, passthrough confirmed)
- Run module: `src/lib/run.js` (spawn at line 34, idea passed via `args.push`)
- Summary module: `src/lib/summary.js` (`generateSummary` at line 182)
- Init module: `src/lib/init.js` (CORE_FILES at 7-14, TEMPLATES at 17-23, DIRS at 25)
- Bot wiring: `src/telegram_bot/bot.py` (entry points at 103-109, states at 110-163)
- State enum: `src/telegram_bot/handlers/common.py` (10 states at lines 25-37, using `auto()`)
- Messages: `src/telegram_bot/messages.py` (136 MSG_* constants, 3 orphaned)
- Dockerfile: `docker/Dockerfile` (Playwright at lines 25, 48-50, 74, 89-91, 113)
- Test files: `src/telegram_bot/tests/` (6 files, 438 tests), `lib/__tests__/summary.test.js` (20 tests)
