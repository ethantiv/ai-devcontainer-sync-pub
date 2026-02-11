# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 23/37 (62%)

## Goal

Implement all features from the project ROADMAP: 4 P2 (Important) features and 2 P3 (Nice to Have) features for the autonomous development loop system and Telegram bot.

## Current Phase

Phase 4

## Phases

### Phase 1: Telegram bot — task history and log viewing
- **Status:** complete

### Phase 2: Loop — idea seeding from file and URL sources
- **Status:** complete

### Phase 3: Brainstorm session export and continuation
Add export command to save the full brainstorm conversation as Markdown, and allow resuming the last archived session after bot restart.

- [x] Preserve full conversation on session finish — added `conversation` field to `BrainstormSession` dataclass to accumulate user/assistant turns during `start()` and `respond()`; `_archive_session()` stores full conversation list and session_id in history (not just 500-char truncation)
- [x] Add `export_session()` method to `BrainstormManager` — reads archived session data with full conversation, formats as Markdown with timestamps and turn separators, saves to `docs/brainstorms/{project}_{date}.md`
- [x] Add `get_resumable_session()` method to `BrainstormManager` — finds the most recent archived session for a project that has non-empty conversation data and a session_id
- [x] Add `resume_archived_session()` method to `BrainstormManager` — reconstructs session state from history entry, creates new tmux session with `--resume` flag using the archived session_id
- [x] Add `MSG_BRAINSTORM_EXPORT_*` and `MSG_BRAINSTORM_CONTINUE_*` constants to `src/telegram_bot/messages.py`
- [x] Add "Export" button to brainstorm history entries in `src/telegram_bot/handlers/brainstorm.py` — `handle_brainstorm_export()` callback handler triggered via `bs:export:{index}` pattern, registered in SELECT_PROJECT state
- [x] Add "Continue last" button to brainstorm prompt in `src/telegram_bot/handlers/brainstorm.py` — `handle_brainstorm_continue()` callback handler triggered via `bs:continue` pattern in ENTER_BRAINSTORM_PROMPT state; button shown only when `get_resumable_session()` finds a match
- [x] Add tests for `export_session()`, `get_resumable_session()`, `resume_archived_session()`, conversation accumulation in `src/telegram_bot/tests/test_tasks.py` (20 tests across 4 new test classes)
- **Status:** complete

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
| Is brainstorm export implemented? | **Yes (Phase 3 complete).** `BrainstormSession` now has a `conversation` field that accumulates turns. `_archive_session()` stores full conversation + session_id. `export_session()` writes Markdown to `docs/brainstorms/`. `resume_archived_session()` uses `--resume` with archived session_id. |
| Is Playwright lazily installed? | No. Builder stage runs `npx playwright install chromium --with-deps` (Dockerfile:25). Runtime copies browsers from builder and installs 16 system deps (lines 48-50). |
| Are there integration tests? | Partial. 476 Python + 20 JS + 18 shell tests. Shell tests cover `resolve_idea()`/`write_idea()`. `init.js`, `run.js`, `cleanup.js`, `cli.js` have zero tests. `generateSummary()` is not tested end-to-end. |
| Is there a state diagram? | No. COMMANDS.md documents commands and buttons but has no Mermaid diagram. |

## Findings & Decisions

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Accumulate conversation in `BrainstormSession.conversation` field | JSONL output files are per-turn and deleted; in-memory list survives across turns and is persisted to sessions JSON |
| Store full conversation + session_id in archive | Enables both Markdown export (full text) and session resumption (--resume with session_id) |
| Export to `docs/brainstorms/{project}_{date}.md` | Per-project organization, date-based filenames for uniqueness |
| Resume via `--resume` with archived session_id | Claude CLI supports resuming by session_id; no need to re-inject conversation as prompt |
| Lazy Playwright via idempotent `ensure-playwright.sh` | Simple to integrate as pre-hook; can be run manually or automatically; exits 0 if already present |
| Integration tests in Jest (not pytest) | Tests `loop init`/`update`/`summary` which are Node.js modules; keeps test tooling consistent with existing `summary.test.js` |
| Scope limited to ROADMAP.md proposals only | No new features beyond the 6 documented proposals |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| Brainstorm "resume" already exists for active sessions | Phase 3 is specifically about resuming ARCHIVED sessions after restart — different from existing in-session resume at brainstorm.py:409-437 |
| `_archive_session()` truncated data (500 chars) | Resolved: added `conversation` list and `session_id` to archive entries; last_response still truncated for display but full data in conversation field |
| No single JSONL file with full conversation | Resolved: accumulate turns in `BrainstormSession.conversation` field during `start()` and `respond()`, persist via `_save_sessions()` |
| `.devcontainer/Dockerfile` also has Playwright | Phase 4 only targets `docker/Dockerfile` (production); devcontainer can retain build-time install for development speed |

### Resources

- ROADMAP: `docs/ROADMAP.md`
- Task manager: `src/telegram_bot/tasks.py`
- Loop shell script: `src/scripts/loop.sh`
- Summary module: `src/lib/summary.js` (`generateSummary` at line 182)
- Bot wiring: `src/telegram_bot/bot.py`
- Messages: `src/telegram_bot/messages.py`
- Dockerfile: `docker/Dockerfile`
- Test files: `src/telegram_bot/tests/` (476 tests), `lib/__tests__/summary.test.js` (20 tests), `src/scripts/tests/test_write_idea.sh` (18 tests)
