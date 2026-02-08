# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/44 (0%)

## Goal

Implement all proposals from docs/ROADMAP.md across three priority tiers: P1 (Critical) log rotation and disk space management, P2 (Important) async test coverage improvements and Commander.js v14 upgrade, and P3 (Nice to Have) queue expiry/retry logic, stale threshold increase, Telegram sync/pull button, and brainstorm history viewer.

## Current Phase

Phase 1: Log Rotation and Disk Space Management (P1-Critical)

## Phases

### Phase 1: Log Rotation and Disk Space Management (P1-Critical)
- [ ] Add `log_rotation.py` module to `src/telegram_bot/` with configurable retention by age (env var `LOOP_LOG_RETENTION_DAYS`, default 7) and max total size (env var `LOOP_LOG_MAX_SIZE_MB`, default 500)
- [ ] Implement JSONL log pruning in `log_rotation.py`: scan `loop/logs/` directories across all projects in PROJECTS_ROOT, delete files older than retention threshold
- [ ] Implement `.brainstorm/` output file pruning: scan `PROJECTS_ROOT/.brainstorm/` for orphaned JSONL files not referenced by `.brainstorm_sessions.json`
- [ ] Add disk space check function to `log_rotation.py`: use `shutil.disk_usage()` to check available space, return warning when below threshold (env var `LOOP_MIN_DISK_MB`, default 500)
- [ ] Integrate disk space check into `TaskManager.start_task()` — refuse to start tasks when disk is critically low
- [ ] Add `loop cleanup --logs` subcommand: extend `src/lib/cleanup.js` and `src/scripts/cleanup.sh` to call log rotation
- [ ] Register periodic log rotation job in `bot.py` (e.g. daily via `job_queue.run_repeating`)
- [ ] Add env var constants to `config.py`: `LOG_RETENTION_DAYS`, `LOG_MAX_SIZE_MB`, `MIN_DISK_MB`
- [ ] Write tests for `log_rotation.py`: retention by age, retention by size, brainstorm cleanup, disk space check
- **Status:** pending

### Phase 2: Improve Async Test Coverage (P2-Important)
- [ ] Add tests for `TaskManager.process_completed_tasks()`: completed session detection, active task removal, queue-next start, return tuple format
- [ ] Add tests for stale progress detection in `bot.py::check_task_progress()`: iteration tracking, `last_reported_iteration` updates, stale warning trigger at STALE_THRESHOLD, single-warn behavior
- [ ] Add tests for `BrainstormManager.start()` async generator: multi-turn conversation flow, status yields, error code propagation
- [ ] Add tests for `BrainstormManager.respond()` async generator: session continuation, ERR_NO_SESSION/ERR_NOT_READY error paths
- [ ] Add tests for `BrainstormManager.finish()`: ROADMAP save logic, session cleanup, return tuple format
- [ ] Add tests for task persistence round-trip under concurrent scenarios: save during queue operations, load with mixed valid/stale tasks
- [ ] Add tests for completion summary generation edge cases: no diff data, no commits, truncation at 3500 chars, plan progress with 0/0
- **Status:** pending

### Phase 3: Upgrade Commander.js to v14 (P2-Important)
- [ ] Research Commander.js breaking changes v12→v13→v14 (changelogs and migration guides)
- [ ] Update `src/package.json` dependency from `^12.0.0` to `^14.0.0`
- [ ] Review and update `src/bin/cli.js` for any deprecated APIs (`.command()`, `.option()`, `.action()`, `.addHelpText()`, `.parse()`)
- [ ] Run `npm install --prefix src` and verify no install errors
- [ ] Run `npm test --prefix src` — verify all 20 JS tests pass
- [ ] Manually verify all CLI commands: `loop plan`, `loop build`, `loop run`, `loop init`, `loop cleanup`, `loop summary`, `loop update`
- **Status:** pending

### Phase 4: Task Queue Expiry and Retry Logic (P3-Nice to Have)
- [ ] Add `QUEUE_TTL` configurable threshold to `config.py` (env var `LOOP_QUEUE_TTL`, default 3600 seconds / 1 hour)
- [ ] Add `queued_at` timestamp checking in `TaskManager.process_completed_tasks()` — remove expired queued tasks and log a warning
- [ ] Add expired task notification in `bot.py`: send message when queued task is removed due to TTL
- [ ] Add message constants to `messages.py`: `MSG_QUEUE_EXPIRED`
- [ ] Add retry logic with exponential backoff for `clone_repo()` in `projects.py`: max 3 retries, initial delay 2s, for `subprocess.TimeoutExpired` and specific git error patterns (network unreachable, connection reset)
- [ ] Write tests for queue TTL expiry and retry logic
- **Status:** pending

### Phase 5: Stale Threshold Default Increase (P3-Nice to Have)
- [ ] Change `STALE_THRESHOLD` default from 300 to 1800 in `config.py` (line 44)
- [ ] Update `MSG_STALE_PROGRESS` in `messages.py` to use dynamic threshold display instead of hardcoded "5 min" — format as `{minutes} min`
- [ ] Update `bot.py::check_task_progress()` to pass threshold value to message formatting
- [ ] Update existing tests in `test_config.py` that assert default STALE_THRESHOLD value
- **Status:** pending

### Phase 6: Sync/Pull Button in Telegram Project Menu (P3-Nice to Have)
- [ ] Add `check_remote_updates(project_path)` function to `git_utils.py`: run `git fetch --dry-run` or `git rev-list HEAD..@{u} --count` to detect new remote commits, return count
- [ ] Add `pull_project(project_path)` function to `git_utils.py`: run `git pull` with timeout, return `(success, message)` tuple
- [ ] Add message constants to `messages.py`: `MSG_SYNC_BTN`, `MSG_SYNC_BTN_WITH_COUNT`, `MSG_SYNC_SUCCESS`, `MSG_SYNC_FAILED`, `MSG_SYNC_NO_UPDATES`
- [ ] Add "Sync" button to project menu in `bot.py::show_project_menu()` with update indicator (e.g. `"^ Sync (3 new)"`)
- [ ] Add `handle_sync()` callback handler in `bot.py` for the sync button action
- [ ] Run background `check_remote_updates()` on project menu open to populate button label
- [ ] Write tests for `check_remote_updates()`, `pull_project()`, and sync button handler
- **Status:** pending

### Phase 7: Interactive Brainstorm History Viewer (P3-Nice to Have)
- [ ] Add `list_brainstorm_sessions(project_path)` function to `tasks.py` or new `brainstorm_history.py`: parse JSONL files in `PROJECTS_ROOT/.brainstorm/`, extract session metadata (timestamp, topic, message count)
- [ ] Add `view_brainstorm_session(session_file)` function: read and format JSONL transcript for display
- [ ] Add Telegram command `/brainstorm_history` in `bot.py` with paginated session list
- [ ] Add message constants to `messages.py`: `MSG_BRAINSTORM_HISTORY_TITLE`, `MSG_BRAINSTORM_HISTORY_EMPTY`, `MSG_BRAINSTORM_SESSION_ENTRY`
- [ ] Write tests for session listing and transcript viewing
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| How many tests does test_tasks.py currently have? | 46 tests (ROADMAP says "only 3" — this is outdated; tests were significantly expanded) |
| Is there any log rotation mechanism? | None — confirmed by codebase search. No rotation, pruning, or disk checks exist |
| Is there retry logic for git operations? | No — all subprocess calls attempt once, catch TimeoutExpired/OSError, return immediately |
| Is the sync/pull feature started? | No — no git pull/fetch references in telegram_bot code, no MSG_SYNC_* constants |
| Is brainstorm history viewer started? | No — no history-related code or messages exist |
| What Commander.js version is installed? | ^12.0.0 in package.json (resolved to 12.1.0 in lock file) |

## Findings & Decisions

### Requirements

**P1 — Log Rotation (Critical):**
- Configurable retention by age and size
- Automatic pruning of old JSONL files in loop/logs/
- Cleanup of orphaned brainstorm JSONL files in .brainstorm/
- Disk space checks before starting new tasks or cloning repos
- Integration with `loop cleanup` CLI command

**P2 — Async Test Coverage (Important):**
- Tests for `process_completed_tasks()`, stale progress detection, task persistence
- Tests for `BrainstormManager.start()`, `respond()`, `finish()` async generators
- Tests for completion summary edge cases

**P2 — Commander.js v14 (Important):**
- Review v12→v14 breaking changes
- Update dependency and verify all 7 CLI commands
- Ensure 20 existing JS tests pass

**P3 — Queue Expiry (Nice to Have):**
- Configurable queue TTL via `LOOP_QUEUE_TTL` env var
- Exponential backoff retry for git clone/push (network operations)
- Telegram notification when queued task expires

**P3 — Stale Threshold (Nice to Have):**
- Change default from 300s to 1800s
- Make stale message dynamic (not hardcoded "5 min")

**P3 — Sync/Pull Button (Nice to Have):**
- "Sync" button in project menu with update count indicator
- Background `git fetch --dry-run` on menu open
- `git pull` on button press

**P3 — Brainstorm History (Nice to Have):**
- List past sessions with timestamps and topics
- View full conversation transcripts
- Telegram command or button interface

### Research Findings

- **test_tasks.py has 46 tests** (not 3 as ROADMAP states) — tests were significantly expanded since ROADMAP was written. Coverage gaps remain for `process_completed_tasks()` core logic, stale progress detection flow, and `BrainstormManager.finish()`
- **MSG_STALE_PROGRESS hardcodes "5 min"** (messages.py:171) — must be made dynamic when threshold changes
- **Commander.js uses stable cross-compatible APIs** — `.command()`, `.option()`, `.action()`, `.parse()` — likely low-risk upgrade
- **No log rotation exists anywhere** — confirmed by exhaustive grep across src/. cleanup.sh only kills server ports, loop.sh cleanup trap only generates summary
- **Brainstorm JSONL files accumulate indefinitely** — new file created per turn, old files never cleaned up
- **All git subprocess calls use single-attempt pattern** — TimeoutExpired caught but no retry, consistent across git_utils.py and projects.py
- **QueuedTask has `queued_at` field** (tasks.py) — timestamp already stored but never checked for expiry

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| New `log_rotation.py` module for log management | Separation of concerns — log rotation is distinct from task/brainstorm management |
| Periodic job in bot.py for automatic rotation | Matches existing pattern (check_task_progress 15s, check_task_completion 30s) |
| `shutil.disk_usage()` for disk checks | Standard library, cross-platform, no external dependencies |
| Extend `loop cleanup` CLI for log pruning | Users expect cleanup to handle all cleanup tasks |
| Dynamic stale message with threshold value | Prevents message/config desynchronization |
| Background git fetch on menu open | Non-blocking UX; user sees update count immediately |
| Retry only for network operations (clone/push) | Local git ops (init, commit) don't benefit from retry |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| ROADMAP test count outdated ("only 3 tests") | Verified actual count: 46 tests in test_tasks.py. Plan focuses on remaining gaps |
| MSG_STALE_PROGRESS hardcodes "5 min" | Plan includes dynamic formatting task in Phase 5 |
| QueuedTask.queued_at exists but unused for TTL | Leverage existing field in Phase 4 — no schema change needed |

### Resources
- ROADMAP.md — 7 proposals across P1/P2/P3 priority tiers
- Commander.js changelog — required for Phase 3 migration review
- python-telegram-bot job_queue docs — for Phase 1 periodic rotation job
- shutil.disk_usage() — Python stdlib for disk space checks
