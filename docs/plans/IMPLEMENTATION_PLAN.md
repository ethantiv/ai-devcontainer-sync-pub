# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 13/43 (30%)
**Last Verified:** 2026-02-08 — Phase 2 in progress

## Goal

Implement all proposals from docs/ROADMAP.md across three priority tiers: P1 (Critical) log rotation and disk space management, P2 (Important) async test coverage improvements and Commander.js v14 upgrade, and P3 (Nice to Have) queue expiry/retry logic, stale threshold increase, Telegram sync/pull button, and brainstorm history viewer.

## Current Phase

Phase 2: Improve Async Test Coverage (P2-Important)

## Phases

### Phase 1: Log Rotation and Disk Space Management (P1-Critical)
- [x] Add env var constants to `config.py`: `LOG_RETENTION_DAYS` (env `LOOP_LOG_RETENTION_DAYS`, default 7), `LOG_MAX_SIZE_MB` (env `LOOP_LOG_MAX_SIZE_MB`, default 500), `MIN_DISK_MB` (env `LOOP_MIN_DISK_MB`, default 500) — use existing `_safe_int()` helper
- [x] Add `log_rotation.py` module to `src/telegram_bot/` with `rotate_logs(projects_root)`: scan `loop/logs/` directories across all projects in PROJECTS_ROOT, delete JSONL files older than `LOG_RETENTION_DAYS`; if total size exceeds `LOG_MAX_SIZE_MB`, delete oldest files first
- [x] Add `cleanup_brainstorm_files(projects_root)` to `log_rotation.py`: scan `PROJECTS_ROOT/.brainstorm/` for JSONL files not referenced by `.brainstorm_sessions.json`, delete orphaned files
- [x] Add `check_disk_space(path)` to `log_rotation.py`: use `shutil.disk_usage()` to check available space, return `(ok, available_mb)` tuple — warn when below `MIN_DISK_MB`
- [x] Integrate disk space check into `TaskManager.start_task()` — refuse to start tasks when disk is critically low, return `(False, MSG_DISK_LOW)` error
- [x] Add `loop cleanup --logs` subcommand: add `--logs` option to `cleanup` command in `src/bin/cli.js`, spawn Python `log_rotation.py` via subprocess (same pattern as `cleanup.js` spawning `cleanup.sh`)
- [x] Register periodic log rotation job in `bot.py` via `job_queue.run_repeating()` — daily interval (86400s), call `rotate_logs()` + `cleanup_brainstorm_files()`
- [x] Add message constants to `messages.py`: `MSG_DISK_LOW`, `MSG_LOG_ROTATION_COMPLETE`
- [x] Write tests for `log_rotation.py`: retention by age, retention by size, brainstorm cleanup, disk space check, edge cases (empty dirs, missing dirs)
- **Status:** complete

### Phase 2: Improve Async Test Coverage (P2-Important)
- [x] Add tests for `TaskManager.process_completed_tasks()`: completed session detection (tmux gone → task completed), active task removal, queue-next start via `_start_next_in_queue()`, return tuple format `list[(completed_task, next_task)]` — 9 new tests in `TestProcessCompletedTasks`
- [x] Add tests for stale progress detection in `bot.py::check_task_progress()`: iteration tracking via `.progress` file, `last_reported_iteration` updates, stale warning trigger when `stale_seconds > STALE_THRESHOLD`, single-warn behavior (`task.stale_warned` flag), reset on progress — 15 new tests in `TestCheckTaskProgress`
- [x] Add tests for `BrainstormManager.start()` async generator happy path: tmux session creation, initial prompt passing, JSONL output polling, session_id capture from `_parse_stream_json()`, status yields `(error_code, response, is_final)` — 10 new tests in `TestBrainstormManagerStartHappyPath` (happy path 3-tuple flow, session registration, session_id capture, brainstorm prefix, save persistence, tmux failure cleanup, timeout cleanup, no-result cleanup, status transitions, output file path)
- [x] Add tests for `BrainstormManager.respond()` async generator happy path: session continuation with `--resume`, prompt writing to tmux, response polling — 12 new tests in `TestBrainstormManagerRespondHappyPath` (yield format, session_id update, status transitions, last_response, resume_session_id passing, output file per turn, save persistence, tmux failure error+status, timeout error, responding status during wait, session_id preservation when None)
- [ ] Add tests for `BrainstormManager.finish()` unit tests: session lookup, tmux cleanup, `_cleanup_session()` call, return `(success, message, content)` tuple — currently only integration-level tests in `test_bot.py` (mocked in button handlers)
- [ ] Add tests for task persistence round-trip under concurrent scenarios: save during queue operations, load with mixed valid/stale tasks, atomic write verification (`os.replace` pattern), `_queue_lock` behavior
- [ ] Add tests for completion summary edge cases: `None` diff_stats, empty commits list, plan progress `(0, 0)`, `None` plan progress — currently 7 tests covering basic/diff/commits/progress/next_task/mode
- **Status:** in_progress

### Phase 3: Upgrade Commander.js to v14 (P2-Important)
- [ ] Update `src/package.json` dependency from `^12.0.0` to `^14.0.0`
- [ ] Run `npm install --prefix src` and verify no install errors
- [ ] Run `npm test --prefix src` — verify all 20 JS tests pass
- [ ] Manually verify all CLI commands: `loop plan`, `loop build`, `loop run`, `loop init`, `loop cleanup`, `loop summary`, `loop update`
- **Status:** pending

### Phase 4: Task Queue Expiry and Retry Logic (P3-Nice to Have)
- [ ] Add `QUEUE_TTL` configurable threshold to `config.py` (env var `LOOP_QUEUE_TTL`, default 3600 seconds) — use existing `_safe_int()` helper
- [ ] Add `queued_at` timestamp checking in `TaskManager.process_completed_tasks()` — iterate queue, remove tasks where `datetime.now() - task.queued_at > QUEUE_TTL`, leverage existing `QueuedTask.queued_at` field (already persisted to `.tasks.json`)
- [ ] Add expired task notification in `bot.py::check_task_completion()`: send message when queued task is removed due to TTL
- [ ] Add message constants to `messages.py`: `MSG_QUEUE_EXPIRED`
- [ ] Add retry logic with exponential backoff for `clone_repo()` in `projects.py`: max 3 retries, initial delay 2s, for `subprocess.TimeoutExpired` and specific git error patterns (network unreachable, connection reset)
- [ ] Write tests for queue TTL expiry (expired task removal, boundary conditions) and retry logic (success after retry, max retries exceeded)
- **Status:** pending

### Phase 5: Stale Threshold Default Increase (P3-Nice to Have)
- [ ] Change `STALE_THRESHOLD` default from 300 to 1800 in `config.py` (line 44)
- [ ] Update `MSG_STALE_PROGRESS` in `messages.py` (line 171) to use dynamic threshold display: `"! *{project}* — no progress for {minutes} min"` instead of hardcoded `"5 min"`
- [ ] Update `bot.py::check_task_progress()` to pass threshold value to message formatting (compute `minutes = STALE_THRESHOLD // 60`)
- [ ] Update existing tests in `test_config.py` that assert `STALE_THRESHOLD == 300` → `== 1800` (3 tests: `test_stale_threshold_default`, `test_stale_threshold_from_env`, `test_stale_threshold_invalid_falls_back`)
- [ ] Update CLAUDE.md env var table: `LOOP_STALE_THRESHOLD` default from 300 to 1800
- **Status:** pending

### Phase 6: Sync/Pull Button in Telegram Project Menu (P3-Nice to Have)
- [ ] Add `check_remote_updates(project_path)` function to `git_utils.py`: run `git fetch` then `git rev-list HEAD..@{u} --count` to detect new remote commits, return count (int), use 10s timeout — follow existing subprocess pattern
- [ ] Add `pull_project(project_path)` function to `git_utils.py`: run `git pull` with 30s timeout, return `(success, message)` tuple — follow existing `(bool, str)` pattern in `projects.py`
- [ ] Add message constants to `messages.py`: `MSG_SYNC_BTN`, `MSG_SYNC_BTN_WITH_COUNT`, `MSG_SYNC_SUCCESS`, `MSG_SYNC_FAILED`, `MSG_SYNC_NO_UPDATES`
- [ ] Add "Sync" button to project menu in `bot.py::show_project_menu()` with update indicator (e.g. `"^ Sync (3 new)"`)
- [ ] Add `handle_sync()` callback handler in `bot.py` for the `action:sync` callback data — call `pull_project()`, show result, refresh project menu
- [ ] Run background `check_remote_updates()` on project menu open to populate button label — use `asyncio.create_task()` or similar non-blocking approach
- [ ] Write tests for `check_remote_updates()`, `pull_project()`, and sync button handler
- **Status:** pending

### Phase 7: Interactive Brainstorm History Viewer (P3-Nice to Have)
- [ ] Add `list_brainstorm_sessions(projects_root)` function to `tasks.py`: scan `PROJECTS_ROOT/.brainstorm/` for JSONL files, extract metadata from filenames (chat_id, uuid) and file content (first line for topic/prompt), return sorted list with timestamp, topic, message count
- [ ] Add `view_brainstorm_session(session_file)` function to `tasks.py`: read JSONL file, extract `type:result` entries, format as readable transcript
- [ ] Add Telegram command `/brainstorm_history` in `bot.py` with paginated session list using inline keyboard buttons
- [ ] Add message constants to `messages.py`: `MSG_BRAINSTORM_HISTORY_TITLE`, `MSG_BRAINSTORM_HISTORY_EMPTY`, `MSG_BRAINSTORM_SESSION_ENTRY`
- [ ] Write tests for session listing and transcript viewing
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| How many tests does test_tasks.py currently have? | 79 tests (67 + 12 new BrainstormManager.respond() happy path tests) |
| How many total tests exist? | 336 Python (79 test_tasks + 96 test_bot + 62 test_projects + 61 test_config + 20 test_git_utils + 18 test_log_rotation) + 20 JS = 356 total |
| Is there any log rotation mechanism? | Yes — `log_rotation.py` module with `rotate_logs()`, `cleanup_brainstorm_files()`, `check_disk_space()`. Daily periodic job in bot.py. CLI via `loop cleanup --logs` |
| Is there retry logic for git operations? | No — all subprocess calls attempt once, catch TimeoutExpired/OSError, return immediately |
| Is the sync/pull feature started? | No — no git pull/fetch references in telegram_bot code, no MSG_SYNC_* constants |
| Is brainstorm history viewer started? | No — no history-related code or messages exist. Sessions removed from `.brainstorm_sessions.json` after `finish()` — only JSONL files remain |
| What Commander.js version is installed? | ^12.0.0 in package.json (resolved to 12.1.0). All APIs used are stable across v12→v14 |
| Are there any TODOs/FIXMEs in the codebase? | None — codebase is clean with no TODO, FIXME, HACK, XXX comments or skipped tests |
| Does Commander.js upgrade require code changes? | No — only stable APIs used (.command(), .option(), .action(), .parse(), .addHelpText()). All cross-compatible with v14 |

## Findings & Decisions

### Requirements

**P1 — Log Rotation (Critical):**
- Configurable retention by age and size
- Automatic pruning of old JSONL files in loop/logs/
- Cleanup of orphaned brainstorm JSONL files in .brainstorm/
- Disk space checks before starting new tasks or cloning repos
- Integration with `loop cleanup` CLI command

**P2 — Async Test Coverage (Important):**
- Tests for `process_completed_tasks()` (1 existing, needs workflow coverage)
- Tests for stale progress detection (0 existing — highest priority gap)
- Tests for `BrainstormManager.start()` happy path (1 error-path test exists)
- Tests for `BrainstormManager.respond()` happy path (2 error-path tests exist)
- Tests for `BrainstormManager.finish()` unit tests (only integration-level mocks in bot tests)
- Tests for concurrent task persistence (3 basic persistence tests exist, no concurrency)
- Tests for completion summary edge cases (7 tests exist, gaps in None/empty inputs)

**P2 — Commander.js v14 (Important):**
- Update dependency — no code changes required
- Verify all 7 CLI commands and 20 JS tests pass

**P3 — Queue Expiry (Nice to Have):**
- Configurable queue TTL via `LOOP_QUEUE_TTL` env var
- Leverage existing `QueuedTask.queued_at` field (already persisted)
- Exponential backoff retry for `clone_repo()` (network operations only)
- Telegram notification when queued task expires

**P3 — Stale Threshold (Nice to Have):**
- Change default from 300s to 1800s
- Make stale message dynamic (not hardcoded "5 min")
- Update 3 tests in test_config.py + CLAUDE.md env var table

**P3 — Sync/Pull Button (Nice to Have):**
- "Sync" button in project menu with update count indicator
- Background `git fetch` + `git rev-list` on menu open
- `git pull` on button press
- Requires complete ground-up implementation — all infrastructure (subprocess patterns, bot handlers, message framework) is ready to extend

**P3 — Brainstorm History (Nice to Have):**
- List past sessions with timestamps and topics
- View full conversation transcripts
- Key gap: `.brainstorm_sessions.json` only stores ACTIVE sessions — after `finish()`, sessions are removed via `_cleanup_session()`. History must be inferred from JSONL files in `.brainstorm/` directory

### Research Findings

- **test_tasks.py has 46 tests** (not 3 as ROADMAP states) — tests were significantly expanded since ROADMAP was written
- **Total test suite: 310 tests** (290 Python across 6 files + 20 JS in summary.test.js) — all active, no skipped/flaky tests
- **Codebase has zero TODOs/FIXMEs** — all functions fully implemented, no stubs or placeholders
- **MSG_STALE_PROGRESS hardcodes "5 min"** (messages.py:171) — must be made dynamic when threshold changes
- **Commander.js uses only stable cross-compatible APIs** — `.command()`, `.option()`, `.action()`, `.parse()`, `.addHelpText()`, negatable options. No deprecated patterns. Upgrade to v14 is zero-risk
- **No log rotation exists anywhere** — cleanup.sh only kills dev server ports (3000, 5173, etc.), loop.sh cleanup trap only generates summary
- **Brainstorm JSONL files accumulate indefinitely** — new file per turn (`brainstorm_{chat_id}_{uuid}.jsonl`), old files never cleaned
- **All git subprocess calls use single-attempt pattern** — TimeoutExpired caught but no retry, consistent across git_utils.py and projects.py
- **QueuedTask has `queued_at` field** (tasks.py) — timestamp stored and persisted to `.tasks.json` via isoformat() but never checked for expiry
- **Brainstorm session metadata lost on finish** — `_cleanup_session()` removes entry from `_sessions` dict and `.brainstorm_sessions.json`. Only JSONL files survive. Phase 7 must scan JSONL files directly or add a history log
- **Existing test coverage gaps by priority**: (1) ~~check_task_progress() stale detection — 0 direct tests~~ **DONE: 15 tests**, (2) BrainstormManager happy paths — ~~only error-path tests (1 start, 2 respond)~~ **start() DONE: 10 tests, respond() DONE: 12 tests**, (3) ~~process_completed_tasks() workflow — 1 persistence test only~~ **DONE: 9 tests**, (4) concurrent persistence — 0 tests, (5) BrainstormManager.finish() — 0 unit tests (only integration mocks in bot handlers)
- **Per-file test breakdown (336 Python)**: test_tasks.py=79, test_bot.py=96, test_projects.py=62, test_config.py=61, test_git_utils.py=20, test_log_rotation.py=18
- **Commander.js APIs used in cli.js**: `.name()`, `.description()`, `.version()`, `.command()`, `.option()`, `.action()`, `.addHelpText('after')`, `.parse()`, plus one negatable option `--no-early-exit`. No advanced APIs (`.exitOverride()`, `.configureOutput()`, etc.). All stable across v12→v14
- **cli.js helper functions**: `addLoopOptions(cmd)` and `addBuildOptions(cmd)` for DRY option management across plan/build/run commands
- **No skipped or xfail tests** — all 259 Python and 20 JS tests are active and passing
- **cleanup.js spawns `./loop/cleanup.sh`** — the `--logs` option (Phase 1) will extend this pattern, spawning Python log_rotation.py via subprocess

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| New `log_rotation.py` module for log management | Separation of concerns — log rotation is distinct from task/brainstorm management |
| Periodic job in bot.py for automatic rotation | Matches existing pattern (check_task_progress 15s, check_task_completion 30s) |
| `shutil.disk_usage()` for disk checks | Standard library, cross-platform, no external dependencies |
| Extend `loop cleanup` CLI for log pruning | Users expect cleanup to handle all cleanup tasks |
| No code changes for Commander.js v14 | All APIs stable across v12→v14; only dependency version bump needed |
| Dynamic stale message with threshold value | Prevents message/config desynchronization |
| Background git fetch on menu open | Non-blocking UX; user sees update count immediately |
| Retry only for network operations (clone) | Local git ops (init, commit) don't benefit from retry |
| Scan JSONL files for brainstorm history | Sessions metadata removed after finish(); JSONL files are the only persistent record |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| ROADMAP test count outdated ("only 3 tests") | Verified actual count: 46 tests in test_tasks.py, 279 total (259 Python + 20 JS). Plan focuses on remaining gaps |
| MSG_STALE_PROGRESS hardcodes "5 min" | Plan includes dynamic formatting task in Phase 5 |
| QueuedTask.queued_at exists but unused for TTL | Leverage existing field in Phase 4 — no schema change needed |
| Brainstorm sessions not persisted after finish() | Phase 7 must scan JSONL files in `.brainstorm/` for metadata — cannot rely on sessions.json |
| Phase 3 originally had 6 tasks including research | Research completed during planning — Commander.js v14 requires no code changes. Reduced to 4 tasks |
| Independent verification (2026-02-08) confirmed all findings | Test counts (259 Python + 20 JS), zero TODOs/FIXMEs, no log rotation/sync/history code, Commander ^12.0.0, MSG_STALE_PROGRESS hardcoded "5 min" — all match plan |
| Full codebase re-analysis (2026-02-08) — no plan changes needed | Deep analysis of all source files (bot.py 1593 LOC, tasks.py 876 LOC, config.py 129 LOC, messages.py 261 LOC, projects.py 346 LOC, git_utils.py 116 LOC, cli.js 90 LOC, 4 JS libs 409 LOC) confirmed: all 7 phases correctly scoped, task counts accurate (43 tasks), no missing ROADMAP features, no existing implementations overlap with planned work |

### Resources
- ROADMAP.md — 7 proposals across P1/P2/P3 priority tiers
- Commander.js changelog — reviewed: no breaking changes for our API usage between v12→v14
- python-telegram-bot job_queue docs — for Phase 1 periodic rotation job
- shutil.disk_usage() — Python stdlib for disk space checks
