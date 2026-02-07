# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 29/31 (94%)
**Verified:** 2026-02-07 (rev.10) — Phase 7 complete

## Goal

Implement all proposals from ROADMAP.md across three priority tiers: P1 (Critical), P2 (Important), P3 (Nice to Have). The work covers English localization of the Telegram bot, startup validation, unit tests, brainstorm temp file relocation, subprocess timeouts, configurable thresholds, task state persistence, and a requirements.txt for Python dependencies.

## Current Phase

Phase 8: Python requirements.txt (P3)

## Phases

### Phase 1: English Localization (P1)

Translate all user-facing Polish strings to English across the Telegram bot and shell scripts. Decouple error detection from language-specific string matching.

- [x] Create `src/telegram_bot/messages.py` — centralized string constants module with all user-facing messages as named constants, plus error code constants (ERR_SESSION_ACTIVE, ERR_START_FAILED, etc.) and BRAINSTORM_ERROR_CODES frozenset
- [x] Translate ~52 unique Polish strings (~65 with duplicates) in `src/telegram_bot/bot.py` — replaced all inline Polish text with imports from `messages.py`
- [x] Translate 13 Polish strings in `src/telegram_bot/tasks.py` — replaced inline Polish with imports from `messages.py`; changed yield signature to `(error_code, status, is_final)` tuples
- [x] Translate 5 Polish strings in `src/telegram_bot/projects.py` — all replaced with message constants
- [x] Translate 10 Polish strings in `src/scripts/notify-telegram.sh` — all status text and labels translated to English
- [x] Translate 7 Polish button labels in `src/telegram_bot/COMMANDS.md` — all translated to English
- [x] Refactor `_is_brainstorm_error()` in `bot.py` — now checks error_code against BRAINSTORM_ERROR_CODES frozenset; BrainstormManager.start()/respond() yield `(error_code, status, is_final)` tuples; `_wait_for_response()` returns `(error_code, response, session_id)`
- **Status:** complete

### Phase 2: Startup Validation (P1)

Add comprehensive environment variable validation at bot startup to fail fast with clear error messages.

- [x] Extend validation in `src/telegram_bot/run.py` — calls `config.validate()` before `create_application()`; prints warnings for non-fatal issues, exits with error messages for fatal ones
- [x] Update `src/telegram_bot/config.py` — added `validate()` function returning `(errors, warnings)` tuple; validates TELEGRAM_BOT_TOKEN (non-empty), TELEGRAM_CHAT_ID (non-zero integer), PROJECTS_ROOT (exists, is directory, writable); checks Claude CLI, tmux, loop as warnings
- [x] Add loop script availability check — verifies `/opt/loop/scripts/loop.sh` or `loop` command exists; warns (not fails) if missing; same for Claude CLI and tmux
- **Status:** complete

### Phase 3: Unit Tests (P2)

Add pytest and Jest test infrastructure and unit tests for pure functions.

- [x] Create `src/telegram_bot/tests/` directory with `__init__.py`, `conftest.py` (shared fixtures for mocking subprocess, temp dirs, PROJECTS_ROOT) — already existed from Phase 2 with test_config.py
- [x] Create `src/telegram_bot/tests/test_git_utils.py` — 20 tests covering all 4 exported functions with mocked subprocess calls; tests timeout handling, malformed output, binary files, case-insensitive checkboxes
- [x] Create `src/telegram_bot/tests/test_projects.py` — 21 tests covering `_parse_gitdir()` with real .git file content, `list_projects()` with patched PROJECTS_ROOT, `_get_branch()` mocked subprocess, `create_worktree()` / `clone_repo()` success and failure paths
- [x] Create `src/telegram_bot/tests/test_tasks.py` — 30 tests covering TaskManager queue management (add, cancel, max size), `_is_session_running()` mocked subprocess, BrainstormManager session persistence (round-trip JSON, stale detection, corrupt JSON), `_parse_stream_json()`, cancel, async start/respond error conditions (requires pytest-asyncio)
- [x] Add Jest config to `src/package.json` — added `"test": "jest"` script and `jest` ^30.0.0 devDependency
- [x] Create `src/lib/__tests__/summary.test.js` — 20 tests covering `parseLog()` with sample JSONL data, `extractTestResults()` regex patterns (Jest/Vitest and pytest formats), `formatSummary()` output structure, `findLatestLog()` file selection by mtime
- [x] Add test commands to project `CLAUDE.md` validation section — `npm test --prefix src` added alongside existing `pytest` command
- **Status:** complete

### Phase 4: Brainstorm Temp Files (P2)

Move brainstorm output files from `/tmp` to a persistent location under `PROJECTS_ROOT`.

- [x] Change `TMP_DIR` in `src/telegram_bot/tasks.py` from `Path("/tmp")` to `Path(PROJECTS_ROOT) / ".brainstorm"`; added `self.TMP_DIR.mkdir(exist_ok=True)` in `BrainstormManager.__init__()` with OSError fallback for missing PROJECTS_ROOT; added 4 unit tests (TestBrainstormManagerTmpDir)
- [x] Add `.brainstorm/` to `.gitignore` via `src/lib/init.js` — `loop init` now adds both `loop/logs/` and `.brainstorm/` entries
- **Status:** complete

### Phase 5: Subprocess Timeouts (P2)

Add timeout parameters to all subprocess calls in `projects.py`, following the existing pattern in `git_utils.py`.

- [x] Add `timeout` to all 4 `subprocess.run()` calls in `src/telegram_bot/projects.py` — `_get_branch()` (timeout=10), `create_worktree()` (timeout=30), `clone_repo()` (timeout=60 for network), `_run_loop_init()` (timeout=30)
- [x] Wrap each call in `try/except (subprocess.TimeoutExpired, OSError)` — `_get_branch()` returns `"unknown"`, `create_worktree()` returns `(False, "Timeout...")`, `clone_repo()` returns `(False, "Timeout...")`, `_run_loop_init()` returns `False`; added 12 new tests in TestSubprocessTimeouts (33 total in test_projects.py)
- **Status:** complete

### Phase 6: Configurable Thresholds (P3)

Extract hardcoded timeout/threshold values to environment variables with sensible defaults.

- [x] Add config constants to `src/telegram_bot/config.py` — `STALE_THRESHOLD = _safe_int(environ.get("LOOP_STALE_THRESHOLD"), 300)`, `BRAINSTORM_POLL_INTERVAL = _safe_float(environ.get("LOOP_BRAINSTORM_POLL_INTERVAL"), 0.5)`, `BRAINSTORM_TIMEOUT = _safe_int(environ.get("LOOP_BRAINSTORM_TIMEOUT"), 300)`, `MAX_QUEUE_SIZE = _safe_int(environ.get("LOOP_MAX_QUEUE_SIZE"), 10)`, `GIT_DIFF_RANGE = environ.get("LOOP_GIT_DIFF_RANGE", "HEAD~5..HEAD")`; added `_safe_float()` helper for float env vars
- [x] Update `src/telegram_bot/bot.py` — replaced hardcoded `300` (line 1091) with `STALE_THRESHOLD`; replaced `"HEAD~5..HEAD"` (line 1156) with `GIT_DIFF_RANGE`; both imported from config
- [x] Update `src/telegram_bot/tasks.py` — `BrainstormManager.POLL_INTERVAL` now reads `BRAINSTORM_POLL_INTERVAL` from config; `BrainstormManager.MAX_WAIT` reads `BRAINSTORM_TIMEOUT`; removed module-level `MAX_QUEUE_SIZE = 10`, now imported from config; all 3 constants are env-var configurable
- [x] Document new env vars in project `CLAUDE.md` environment variables table and `README.md` — added 5 LOOP_* env vars to both files
- **Status:** complete

### Phase 7: Task State Persistence (P3)

Persist active task and queue state to disk, reusing the brainstorm session persistence pattern.

- [x] Add `_tasks_file()`, `_save_tasks()`, `_load_tasks()` methods to `TaskManager` in `src/telegram_bot/tasks.py` — persists to `PROJECTS_ROOT/.tasks.json` using atomic writes (temp file + `os.replace()`), same pattern as `BrainstormManager._save_sessions()`
- [x] Call `_save_tasks()` after state changes — in `_start_task_now()`, `start_task()` (queue add), `process_completed_tasks()`, `cancel_queued_task()`, and `_load_tasks()` (cleanup save)
- [x] Add tmux session reconciliation in `_load_tasks()` — on startup, validates each restored task's tmux session via `_is_session_running()`; removes stale entries; restores queue ordering; logs stale removals and active restorations
- [x] Handle edge case: task completed while bot was down — `_load_tasks()` removes active tasks whose tmux session no longer exists; queues are always restored, enabling `process_completed_tasks()` to pick them up; 12 new tests (131 total Python tests) including deadlock-free `_save_tasks` with `_queue_lock`; also fixed `task_manager` and `brainstorm_manager` fixtures (`return` → `yield`) to keep patches active during tests
- **Status:** complete

### Phase 8: Python requirements.txt (P3)

Create a dedicated requirements file for Telegram bot Python dependencies.

- [ ] Create `src/telegram_bot/requirements.txt` with `python-telegram-bot[job-queue]>=21.0,<22.0`
- [ ] Update `docker/Dockerfile` — line 23 (builder stage): remove `python-telegram-bot` from inline pip install (keep `uv`); line 54 (runtime stage): replace `pip3 install ... 'python-telegram-bot[job-queue]'` with `COPY src/telegram_bot/requirements.txt /tmp/requirements.txt` + `pip3 install --break-system-packages -r /tmp/requirements.txt`
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should localization support multiple languages (i18n framework)? | No. ROADMAP specifies translation to English only. Use a simple `messages.py` constants module, not a full i18n framework. |
| Should startup validation be fatal or warning? | Fatal for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (bot cannot function). Warning for Claude CLI and loop.sh (bot can still receive commands but task execution will fail). Fatal for PROJECTS_ROOT not existing/writable. |
| What test framework for Python? | pytest — standard, no extra config needed, compatible with subprocess mocking via `unittest.mock`. |
| What test framework for JS? | Jest — standard for Node.js, needs to be added as devDependency in src/package.json. |
| Where to move brainstorm temp files? | `PROJECTS_ROOT/.brainstorm/` — same filesystem as session persistence file, survives container restarts. |
| How to decouple error detection from Polish strings? | Replace plain string returns with `(error_code, message)` tuples from BrainstormManager; `_is_brainstorm_error()` checks error_code instead of substring matching. |

## Findings & Decisions

### Requirements

**Functional:**
- All ~100 Polish strings across 5 files translated to English (bot.py, tasks.py, projects.py, notify-telegram.sh, COMMANDS.md)
- Startup validation for 5 environment variables/tools with clear error messages
- Unit tests for 4 modules (git_utils.py, projects.py, tasks.py, summary.js)
- Brainstorm temp files relocated to persistent storage
- Subprocess timeouts on all 4 git operations in projects.py
- 5 hardcoded constants made configurable via env vars
- Task state persisted to disk with tmux reconciliation on startup
- Python dependencies in requirements.txt

**Non-functional:**
- No i18n framework overhead — simple constants module
- Test coverage focused on pure functions first (subprocess mocking for git operations)
- Atomic writes for all persistence (prevent corruption on crash)
- Graceful degradation — missing optional tools produce warnings, not crashes

### Research Findings

| Finding | Details |
|---------|---------|
| Polish string count | ~87 strings across bot.py (~52 unique, ~65 with duplicates like 6x "Powrót", 5x "Brak wybranego projektu"), tasks.py (13), projects.py (5+1 mixed "Projekt {name} already exists"), notify-telegram.sh (10: 4 status + 6 labels), COMMANDS.md (7 button labels in ASCII-only spelling) — re-verified 2026-02-07 |
| Error detection coupling | `_is_brainstorm_error()` at bot.py:98 checks 5 Polish substrings ("Sesja brainstorming już", "Nie udało", "Timeout", "Brak aktywnej", "nie jest gotowa") + "error" (English); used at lines 530, 742, 783 — translation requires coordinated refactor with tasks.py BrainstormManager return values |
| Missing i18n infrastructure | No messages.py, strings.py, or any translation system exists |
| Test coverage | 131 Python tests (pytest) + 20 JS tests (Jest) — full coverage for pure functions including configurable thresholds and task state persistence |
| Env var validation gaps | PROJECTS_ROOT not validated at all; Claude CLI not checked; TELEGRAM_CHAT_ID accepts 0 silently |
| Subprocess timeout gaps | **Resolved Phase 5**: all 4 calls in projects.py now have timeouts (10/30/60/30) and `try/except (TimeoutExpired, OSError)` matching git_utils.py pattern |
| Brainstorm /tmp usage | **Resolved Phase 4**: `TMP_DIR` now uses `PROJECTS_ROOT/.brainstorm/`, created in `__init__()` with OSError fallback |
| Task persistence gap | **Resolved Phase 7**: TaskManager persists to `PROJECTS_ROOT/.tasks.json` with atomic writes; loads on `__init__()` with tmux reconciliation; queues always restored |
| requirements.txt missing | `python-telegram-bot[job-queue]` installed inline in docker/Dockerfile only |
| COMMANDS.md location | `src/telegram_bot/COMMANDS.md` — contains 7 Polish button labels in reference table |
| summary.js exports | `module.exports = { generateSummary, parseLog, findLatestLog, formatSummary }` — `extractTestResults` is private (not exported); test via `parseLog()` or use rewire |
| projects.py language mix | Contains mix of English error messages (line 128, 146) and Polish success messages (lines 130, 152, 166, 168, 170) — all need English translation |
| Dockerfile dual pip install | `python-telegram-bot` installed in builder (line 23, without extras) AND runtime (line 54, with `[job-queue]`); requirements.txt must replace both |
| notify-telegram.sh scope | 10 Polish strings total: 4 status labels (lines 38-41) + 6 message template labels (lines 55-61) |

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Simple `messages.py` over i18n framework | ROADMAP specifies English-only translation; a constants module is minimal, zero-dependency, and easy to maintain |
| Error codes over string matching | Decouples error detection from display language; prevents fragile substring checks breaking on translation |
| pytest over unittest | More concise syntax, better fixture system, standard in modern Python projects |
| `PROJECTS_ROOT/.brainstorm/` over TMPDIR env var | Guarantees same filesystem (no EXDEV), survives restarts, co-located with `.brainstorm_sessions.json` |
| Reuse BrainstormManager persistence pattern for TaskManager | Proven atomic write pattern already in codebase; consistent approach reduces cognitive load |
| Timeout=30 default for git operations (60 for clone) | Clone is network-bound and can be slow; local git operations (branch, worktree) are fast; 30s is generous |
| Version range `>=21.0,<22.0` for python-telegram-bot | Current API uses v21+ patterns (Application builder, job_queue); pin major version to prevent breaking changes |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| `_is_brainstorm_error()` uses Polish substring matching | Plan refactor in Phase 1: return structured `(error_code, message)` from BrainstormManager |
| `config.py` defaults mask missing env vars | Phase 2: add `validate()` function that checks all required vars before bot starts |
| No test infrastructure exists | Phase 3: create test directories, add pytest/jest config, add test commands to CLAUDE.md |
| Cross-filesystem rename risk with /tmp | **Resolved Phase 4**: moved to PROJECTS_ROOT/.brainstorm/ (same volume) |

### Resources

- ROADMAP: `docs/ROADMAP.md` — 8 proposals across P1/P2/P3
- Source: `src/telegram_bot/` — Python bot (bot.py 1197 LOC, tasks.py 743 LOC, projects.py 188 LOC, git_utils.py 116 LOC, config.py 18 LOC, run.py 30 LOC)
- Source: `src/lib/` — Node.js modules (summary.js 193 LOC, init.js, run.js, cleanup.js)
- Source: `src/scripts/` — Shell scripts (loop.sh 285 LOC, notify-telegram.sh 70 LOC, cleanup.sh 12 LOC)
- Existing timeout pattern: `src/telegram_bot/git_utils.py` lines 14-24 (timeout=10, try/except `(TimeoutExpired, OSError)`, return None/[])
- Existing persistence pattern: `src/telegram_bot/tasks.py` lines 351-410 (atomic JSON writes via `os.replace()`)
- git_utils.py exports: `get_commit_hash()`, `get_diff_stats()`, `get_recent_commits()`, `get_plan_progress()` — all with timeout=10
- summary.js exports: `generateSummary`, `parseLog`, `findLatestLog`, `formatSummary` — `extractTestResults` is private (test via `parseLog` or rewire)
