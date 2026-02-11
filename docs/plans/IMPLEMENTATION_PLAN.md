# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 34/37 (92%)

## Goal

Implement all features from the project ROADMAP: 4 P2 (Important) features and 2 P3 (Nice to Have) features for the autonomous development loop system and Telegram bot.

## Current Phase

Phase 6

## Phases

### Phase 1: Telegram bot — task history and log viewing
- **Status:** complete

### Phase 2: Loop — idea seeding from file and URL sources
- **Status:** complete

### Phase 3: Brainstorm session export and continuation
- **Status:** complete

### Phase 4: Docker ARM build optimization
- **Status:** complete

### Phase 5: Loop workflow integration tests
Add end-to-end test suite exercising the full loop workflow: init, plan iteration, output artifact verification.

- [x] Create `src/lib/__tests__/integration.test.js` — 14 integration tests in 3 describe blocks (`loop init`, `loop update`, `loop summary`) with 30s timeouts
- [x] Add test: `loop init` creates expected symlinks (6 core files), directories (3), templates (5 copied files), `.version` file, and `.gitignore` entries in a temp project — 7 tests covering symlinks, dirs, templates, version, gitignore creation/append, skip-existing behavior
- [x] Add test: `loop update` (force=true) refreshes symlinks, overwrites templates, and updates `.version` file — 3 tests
- [x] Add test: `generateSummary()` end-to-end produces formatted output from realistic JSONL log with tool usage, files modified, tokens, and test results — 4 tests including empty dir, realistic log, multi-file selection, minimal log
- [x] Add `test:integration` npm script to `src/package.json` — runs `jest lib/__tests__/integration.test.js` separately from unit `test` script
- **Status:** complete

### Phase 6: Telegram bot handler state machine diagram
Add a Mermaid state diagram to `src/telegram_bot/COMMANDS.md` showing the full conversation flow.

- [ ] Analyze all 10 states and 40+ transitions in `src/telegram_bot/bot.py` and `handlers/common.py` — map State enum values (SELECT_PROJECT=1 through GITHUB_CHOICE=10) to handler transitions across all 5 handler modules
- [ ] Create Mermaid stateDiagram-v2 in `src/telegram_bot/COMMANDS.md` — show entry points (/start, /projects, /status, /brainstorming, /history), SELECT_PROJECT → PROJECT_MENU → each sub-flow (task with ENTER_IDEA→SELECT_ITERATIONS, brainstorm with ENTER_BRAINSTORM_PROMPT→BRAINSTORMING, clone ENTER_URL, create ENTER_PROJECT_NAME→GITHUB_CHOICE, worktree ENTER_NAME), self-loops, and fallback transitions
- [ ] Verify diagram renders correctly using `beautiful-mermaid` skill
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Are there integration tests? | **Yes (Phase 5 complete).** 14 integration tests in `src/lib/__tests__/integration.test.js` cover `init()`, `init({ force: true })`, and `generateSummary()` end-to-end. Total: 476 Python + 34 JS + 32 shell = 542 tests. |
| Is there a state diagram? | No. COMMANDS.md documents commands and buttons but has no Mermaid diagram. |

## Findings & Decisions

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Integration tests in Jest (not pytest) | Tests `loop init`/`update`/`summary` which are Node.js modules; keeps test tooling consistent with existing `summary.test.js` |
| Separate `test:integration` npm script | Allows running integration tests independently; unit tests (`npm test`) still run both suites via default `jest` |
| Tests use real temp dirs with `useTempProject()` helper | Exercises actual fs operations (symlinks, copies, directory creation) rather than mocking, catching real edge cases like overlayfs ghost entries |
| Scope limited to ROADMAP.md proposals only | No new features beyond the 6 documented proposals |

### Resources

- ROADMAP: `docs/ROADMAP.md`
- Test files: `src/telegram_bot/tests/` (476 tests), `lib/__tests__/summary.test.js` (20 unit), `lib/__tests__/integration.test.js` (14 integration), `src/scripts/tests/test_write_idea.sh` (18 tests), `src/scripts/tests/test_ensure_playwright.sh` (14 tests)
