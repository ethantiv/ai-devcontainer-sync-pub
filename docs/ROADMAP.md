# Roadmap

## Proposals

### P1 - Critical

#### Log rotation and disk space management
Loop JSONL logs in `loop/logs/` grow unbounded — no rotation, no size limits, no automatic cleanup. On resource-constrained hosts like Raspberry Pi this can fill the disk. Brainstorm output files in `PROJECTS_ROOT/.brainstorm/` also accumulate indefinitely. Add configurable log retention (by age and/or size) to `loop cleanup`, automatic pruning of old JSONL files, and disk space checks before starting new tasks or cloning repositories.

### P2 - Important

#### Improve async test coverage for TaskManager and BrainstormManager
`test_tasks.py` has only 3 tests — missing coverage for `process_completed_tasks()`, stale progress detection, task persistence save/load cycle, and completion summary generation. `BrainstormManager` async generators (`start()`, `respond()`) have zero tests for multi-turn conversation flow, timeout handling, or session restoration after container restart. Add pytest-asyncio tests covering these critical paths.

#### Upgrade Commander.js to v14
`commander` in `src/package.json` is pinned to `^12.0.0` — two major versions behind current v14. Review breaking changes between v12 and v14, update the dependency, and verify all CLI commands (`loop plan`, `loop build`, `loop run`, `loop init`, `loop cleanup`, `loop summary`, `loop update`) still work correctly.

### P3 - Nice to Have

#### Task queue expiry and retry logic
Queued tasks have no TTL — a task can sit in the queue indefinitely if earlier tasks keep failing. Git operations in `projects.py` and `git_utils.py` have timeouts but no retry logic for transient network failures. Add configurable queue task expiry (e.g. `LOOP_QUEUE_TTL`) and optional retry with exponential backoff for git clone/push operations.

#### Increase stale task threshold from 5 to 30 minutes
`LOOP_STALE_THRESHOLD` defaults to 300 seconds (5 minutes). In practice, Claude Code iterations — especially on large codebases or with multi-file edits — regularly exceed 5 minutes without producing new log output. This triggers false-positive stale warnings in the Telegram bot. Change the default to 1800 seconds (30 minutes) in `config.py` to better match real-world iteration durations.

#### Interactive brainstorm history viewer
Brainstorm sessions produce JSONL files in `PROJECTS_ROOT/.brainstorm/` but there is no way to review past sessions. Add a `loop brainstorm --history` CLI command (or Telegram `/brainstorm_history` command) that lists past sessions with timestamps and topics, and allows viewing the full conversation transcript.
