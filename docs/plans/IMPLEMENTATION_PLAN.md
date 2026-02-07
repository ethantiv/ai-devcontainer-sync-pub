# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/31 (0%)

## Goal

Implement all proposals from ROADMAP.md across three priority tiers: P1 (Critical), P2 (Important), P3 (Nice to Have). The work covers English localization of the Telegram bot, startup validation, unit tests, brainstorm temp file relocation, subprocess timeouts, configurable thresholds, task state persistence, and a requirements.txt for Python dependencies.

## Current Phase

Phase 1: English Localization (P1)

## Phases

### Phase 1: English Localization (P1)

Translate all user-facing Polish strings to English across the Telegram bot and shell scripts. Decouple error detection from language-specific string matching.

- [ ] Create `src/telegram_bot/messages.py` — centralized string constants module with all user-facing messages as named constants (e.g. `MSG_NO_ACTIVE_SESSION = "No active brainstorming session."`)
- [ ] Translate ~60 Polish strings in `src/telegram_bot/bot.py` — replace inline Polish text with imports from `messages.py`; includes button labels ("Klonuj repo" -> "Clone repo", "Powrót" -> "Back", "Kolejka" -> "Queue", "Nowy worktree" -> "New worktree", "Podłącz" -> "Attach"), status messages ("W toku" -> "Running", "Wolny" -> "Free"), help text (lines 899-917), brainstorm flow text ("Claude myśli..." -> "Claude thinking...", "Zapisuję IDEA..." -> "Saving IDEA..."), error messages ("Brak wybranego projektu" -> "No project selected"), task completion messages (lines 934-955)
- [ ] Translate 18 Polish strings in `src/telegram_bot/tasks.py` — replace inline Polish with imports from `messages.py`; includes queue messages ("Kolejka pełna" -> "Queue full", line 140), brainstorm status messages ("Claude myśli..." -> "Claude thinking...", lines 595/639, "Uruchamiam Claude..." -> "Starting Claude...", lines 578/733), timeout and error messages ("Nie udało się uruchomić Claude" -> "Failed to start Claude", lines 591/650/705), session messages ("Sesja brainstorming już aktywna" -> "Brainstorming session already active", line 559), IDEA save prompt (lines 689-692)
- [ ] Translate 5 Polish strings in `src/telegram_bot/projects.py` — "Utworzono {name} na branchu {suffix}" (line 130), "Katalog {name} already exists" (line 152), "Sklonowano {name}" (line 166), "Loop zainicjalizowany" (line 168), "Loop init nie powiodlo sie" (line 170)
- [ ] Translate 10 Polish strings in `src/scripts/notify-telegram.sh` — status text: "Sukces" -> "Success" (line 38), "Ukończono iteracje" -> "Iterations completed" (line 39), "Przerwane" -> "Interrupted" (line 40), "Nieznany" -> "Unknown" (line 41); labels: "Zadanie zakończone" -> "Task completed" (line 55), "Tryb:" -> "Mode:" (line 57), "Status:" (line 58, keep), "Iteracje:" -> "Iterations:" (line 59), "Czas:" -> "Time:" (line 60), "Projekt:" -> "Project:" (line 61)
- [ ] Translate 7 Polish button labels in `src/telegram_bot/COMMANDS.md` — "Klonuj repo" -> "Clone repo", "Nowy worktree" -> "New worktree", "Podłącz" -> "Attach", "Kolejka" -> "Queue", "Powrót" -> "Back", "Uruchom Plan" -> "Run Plan", "Zakończ" -> "Finish"
- [ ] Refactor `_is_brainstorm_error()` in `bot.py` — replace Polish substring matching with error type constants or a structured return from `BrainstormManager` (e.g. return `(error_code, message)` tuples instead of plain Polish strings); update all 3 call sites (lines 530, 742, 783)
- **Status:** pending

### Phase 2: Startup Validation (P1)

Add comprehensive environment variable validation at bot startup to fail fast with clear error messages.

- [ ] Extend validation in `src/telegram_bot/run.py` — add checks for: `PROJECTS_ROOT` exists and is a writable directory, `claude` CLI is in PATH or at `~/.claude/bin/claude` (via `shutil.which`), `tmux` is available (via `shutil.which`), `TELEGRAM_CHAT_ID` is a non-zero integer
- [ ] Update `src/telegram_bot/config.py` — remove silent defaults (empty string for token, 0 for chat_id); add a `validate()` function that returns list of error strings, called from `run.py` before `create_application()`
- [ ] Add loop script availability check — verify either `/opt/loop/scripts/loop.sh` or `loop` command exists; warn (not fail) if missing since bot can still function for brainstorming without loop
- **Status:** pending

### Phase 3: Unit Tests (P2)

Add pytest and Jest test infrastructure and unit tests for pure functions.

- [ ] Create `src/telegram_bot/tests/` directory with `__init__.py`, `conftest.py` (shared fixtures for mocking subprocess, temp dirs, PROJECTS_ROOT)
- [ ] Create `src/telegram_bot/tests/test_git_utils.py` — test `get_commit_hash()`, `get_diff_stats()`, `get_recent_commits()`, `get_plan_progress()` with mocked subprocess calls; test timeout handling, malformed output
- [ ] Create `src/telegram_bot/tests/test_projects.py` — test `_parse_gitdir()` with real `.git` file content, `list_projects()` with mocked directory structure, `_get_branch()` with mocked subprocess, `create_worktree()` / `clone_repo()` success and failure paths
- [ ] Create `src/telegram_bot/tests/test_tasks.py` — test `TaskManager` queue management (add, cancel, max queue size), `_is_session_running()` with mocked subprocess, `BrainstormManager` session serialization/deserialization (round-trip JSON), stale session detection
- [ ] Add Jest config to `src/package.json` — add `"test"` script and jest dev dependency
- [ ] Create `src/lib/__tests__/summary.test.js` — test `parseLog()` with sample JSONL data, `extractTestResults()` regex patterns (Jest/Vitest and pytest formats), `formatSummary()` output structure, `findLatestLog()` file selection by mtime
- [ ] Add test commands to project `CLAUDE.md` validation section — `pytest src/telegram_bot/tests/` and `npm test --prefix src`
- **Status:** pending

### Phase 4: Brainstorm Temp Files (P2)

Move brainstorm output files from `/tmp` to a persistent location under `PROJECTS_ROOT`.

- [ ] Change `TMP_DIR` in `src/telegram_bot/tasks.py` (line 345) from `Path("/tmp")` to `Path(PROJECTS_ROOT) / ".brainstorm"`; add `self.TMP_DIR.mkdir(exist_ok=True)` in `BrainstormManager.__init__()`
- [ ] Add `.brainstorm/` to `.gitignore` template in `src/templates/` if projects are initialized under PROJECTS_ROOT
- **Status:** pending

### Phase 5: Subprocess Timeouts (P2)

Add timeout parameters to all subprocess calls in `projects.py`, following the existing pattern in `git_utils.py`.

- [ ] Add `timeout=30` to all 4 `subprocess.run()` calls in `src/telegram_bot/projects.py` — `_get_branch()` (line 87, use `timeout=10`), `create_worktree()` (line 120, use `timeout=30`), `clone_repo()` (line 154, use `timeout=60` for network operation), `_run_loop_init()` (line 181, use `timeout=30`)
- [ ] Wrap each call in `try/except (subprocess.TimeoutExpired, OSError)` — return appropriate failure values: `_get_branch()` returns `"unknown"`, `create_worktree()` returns `(False, "Timeout...")`, `clone_repo()` returns `(False, "Timeout...")`, `_run_loop_init()` returns `False`
- **Status:** pending

### Phase 6: Configurable Thresholds (P3)

Extract hardcoded timeout/threshold values to environment variables with sensible defaults.

- [ ] Add config constants to `src/telegram_bot/config.py` — `STALE_THRESHOLD = _safe_int(environ.get("LOOP_STALE_THRESHOLD"), 300)`, `BRAINSTORM_POLL_INTERVAL = float(environ.get("LOOP_BRAINSTORM_POLL_INTERVAL", "0.5"))`, `BRAINSTORM_TIMEOUT = _safe_int(environ.get("LOOP_BRAINSTORM_TIMEOUT"), 300)`, `MAX_QUEUE_SIZE = _safe_int(environ.get("LOOP_MAX_QUEUE_SIZE"), 10)`, `GIT_DIFF_RANGE = environ.get("LOOP_GIT_DIFF_RANGE", "HEAD~5..HEAD")`
- [ ] Update `src/telegram_bot/bot.py` — replace hardcoded `300` (line 1038) with `config.STALE_THRESHOLD`; replace `"HEAD~5..HEAD"` (line 1103) with `config.GIT_DIFF_RANGE`
- [ ] Update `src/telegram_bot/tasks.py` — replace `POLL_INTERVAL = 0.5` (line 343) with `config.BRAINSTORM_POLL_INTERVAL`; replace `MAX_WAIT = 300` (line 344) with `config.BRAINSTORM_TIMEOUT`; replace `MAX_QUEUE_SIZE = 10` (line 82) with `config.MAX_QUEUE_SIZE`
- [ ] Document new env vars in project `CLAUDE.md` environment variables table and `README.md`
- **Status:** pending

### Phase 7: Task State Persistence (P3)

Persist active task and queue state to disk, reusing the brainstorm session persistence pattern.

- [ ] Add `_tasks_file()`, `_save_tasks()`, `_load_tasks()` methods to `TaskManager` in `src/telegram_bot/tasks.py` — persist to `PROJECTS_ROOT/.tasks.json` using atomic writes (temp file + `os.replace()`), same pattern as `BrainstormManager._save_sessions()`
- [ ] Call `_save_tasks()` after state changes — in `_start_task_now()`, `process_completed_tasks()`, `cancel_queued_task()`, and queue operations
- [ ] Add tmux session reconciliation in `_load_tasks()` — on startup, validate each restored task's tmux session exists via `_is_session_running()`; remove stale entries; restore queue ordering
- [ ] Handle edge case: task completed while bot was down — if tmux session no longer exists for a tracked task, mark it as completed and trigger queue processing
- **Status:** pending

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
| Polish string count | ~100 strings across bot.py (~60), tasks.py (18), projects.py (5), notify-telegram.sh (10), COMMANDS.md (7 button labels) |
| Error detection coupling | `_is_brainstorm_error()` at bot.py:98 checks 5 Polish substrings ("Sesja brainstorming już", "Nie udało", "Timeout", "Brak aktywnej", "nie jest gotowa") + "error" (English); used at lines 530, 742, 783 — translation requires coordinated refactor with tasks.py BrainstormManager return values |
| Missing i18n infrastructure | No messages.py, strings.py, or any translation system exists |
| Test coverage | Zero — no test files, no pytest/jest config, no test scripts in package.json |
| Env var validation gaps | PROJECTS_ROOT not validated at all; Claude CLI not checked; TELEGRAM_CHAT_ID accepts 0 silently |
| Subprocess timeout gaps | 4 calls in projects.py lack timeouts (lines 87, 120, 154, 181); git_utils.py has correct pattern (timeout=10, `except (subprocess.TimeoutExpired, OSError)`, return None/[]) |
| Brainstorm /tmp usage | Single reference: `TMP_DIR = Path("/tmp")` in tasks.py line 345; used only for brainstorm output JSONL files |
| Task persistence gap | TaskManager is memory-only; BrainstormManager has full persistence with atomic writes — pattern ready to reuse |
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
| Cross-filesystem rename risk with /tmp | Phase 4: move to PROJECTS_ROOT/.brainstorm/ (same volume) |

### Resources

- ROADMAP: `docs/ROADMAP.md` — 8 proposals across P1/P2/P3
- Source: `src/telegram_bot/` — Python bot (bot.py 1198 LOC, tasks.py 743 LOC, projects.py 188 LOC, git_utils.py 117 LOC, config.py 19 LOC, run.py 31 LOC)
- Source: `src/lib/` — Node.js modules (summary.js 192 LOC, init.js, run.js, cleanup.js)
- Source: `src/scripts/` — Shell scripts (loop.sh 286 LOC, notify-telegram.sh 70 LOC, cleanup.sh 13 LOC)
- Existing timeout pattern: `src/telegram_bot/git_utils.py` lines 14-24 (timeout=10, try/except)
- Existing persistence pattern: `src/telegram_bot/tasks.py` lines 351-410 (atomic JSON writes)
