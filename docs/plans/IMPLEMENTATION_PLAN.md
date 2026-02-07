# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/8 (0%)

## Goal

Add a developer mode (`DEV_MODE` environment variable) that disables the Telegram bot in development containers. The user runs two Coolify deployments: `claude-code` (main branch) and `dev-claude-code` (develop branch). Both share the same `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, so the bot in the dev container could receive and execute commands meant for production — potentially running tasks in the wrong container.

## Current Phase

Phase 1: Implementation

## Phases

### Phase 1: Implementation
- [ ] Add `DEV_MODE` config variable to `src/telegram_bot/config.py`
- [ ] Add dev mode check to `src/telegram_bot/run.py` — exit gracefully with info message when `DEV_MODE=true`
- [ ] Add `DEV_MODE` check to `docker/entrypoint.sh` `start_telegram_bot()` — skip bot startup with info message
- [ ] Add `MSG_DEV_MODE_SKIP` message constant to `src/telegram_bot/messages.py`
- [ ] Document `DEV_MODE` env var in `CLAUDE.md` environment variables table
- [ ] Document `DEV_MODE` env var in `README.md` environment variables section
- **Status:** pending

### Phase 2: Testing
- [ ] Add tests for `DEV_MODE` in `test_config.py` — verify the variable is read correctly (true/false/unset/invalid values)
- [ ] Add test in `test_config.py` — verify `validate()` returns a warning when `DEV_MODE` is active
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Where should `DEV_MODE` block the bot? | Two layers: `entrypoint.sh` (prevents process spawn) and `run.py` (graceful exit if called directly). Defense in depth. |
| Should it be a warning or error in validate()? | Warning — `DEV_MODE` is intentional behavior, not a misconfiguration. Print info message and exit 0 (not error exit 1). |
| What values should `DEV_MODE` accept? | `true`, `1`, `yes` (case-insensitive) = enabled. Anything else or unset = disabled. Standard boolean env var pattern. |
| Should `DEV_MODE` affect anything besides the Telegram bot? | No. ROADMAP.md scope is specifically about disabling the Telegram bot. Loop CLI, scripts, and all other functionality remain unaffected. |
| Where to add the env var for dev-claude-code on Coolify? | User sets `DEV_MODE=true` in the Coolify environment variables for the `dev-claude-code` app only. |

## Findings & Decisions

### Requirements

**Functional:**
1. New env var `DEV_MODE` (default: unset/false) disables Telegram bot startup
2. Bot must not start in either `entrypoint.sh` (process level) or `run.py` (application level)
3. Clear log message when bot is skipped due to dev mode
4. No impact on any other functionality (loop CLI, scripts, prompts)

**Non-functional:**
1. Zero breaking changes — existing deployments without `DEV_MODE` work identically
2. Follows existing patterns: env var in `config.py`, message in `messages.py`, check in `run.py`

### Research Findings

**Current bot startup flow (two entry points):**
1. `docker/entrypoint.sh` → `start_telegram_bot()` — checks TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, spawns `python3 -m loop.telegram_bot.run &`
2. `src/telegram_bot/run.py` → `main()` — calls `config.validate()`, creates application, starts polling

**Current code has zero dev mode handling:**
- No `DEV_MODE`, `DEBUG`, `DEVELOPER_MODE` variables anywhere in codebase
- No TODO/FIXME/HACK comments in any analyzed file
- 134 Python + 20 JS = 154 tests, all passing, none skipped

**Existing env var patterns in `config.py`:**
- String vars: `environ.get("VAR", default)`
- Int vars: `_safe_int(environ.get("VAR"), default)`
- Boolean pattern not yet used — will add `_is_truthy()` helper

**Files requiring changes:**
1. `src/telegram_bot/config.py` — add `DEV_MODE` variable + `_is_truthy()` helper
2. `src/telegram_bot/run.py` — add dev mode check before `create_application()`
3. `src/telegram_bot/messages.py` — add `MSG_DEV_MODE_SKIP` constant
4. `docker/entrypoint.sh` — add `DEV_MODE` check in `start_telegram_bot()`
5. `CLAUDE.md` — document env var
6. `README.md` — document env var
7. `src/telegram_bot/tests/test_config.py` — add dev mode tests

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use `DEV_MODE` name (not `DISABLE_TELEGRAM_BOT`) | Matches ROADMAP.md intent ("tryb developerski"). Semantically describes the container's role, not a specific feature toggle. Clearer for Coolify UI. |
| Check in both `entrypoint.sh` AND `run.py` | Defense in depth. `entrypoint.sh` prevents process spawn (saves resources). `run.py` handles direct invocation. |
| Exit with code 0 (not 1) in run.py | Dev mode is intentional, not an error. Exit 0 = clean shutdown. |
| Add `_is_truthy()` helper to config.py | Reusable boolean env var parser. Accepts `true/1/yes` (case-insensitive). Follows common convention. |
| Add as warning in validate() | Inform the user that bot is disabled, but don't treat it as an error that prevents startup (since startup is intentionally skipped). |
| Do NOT add `DEV_MODE` to docker/.env | The `.env` file is for production. Dev mode should be set per-deployment in Coolify UI. |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| No existing boolean env var pattern in config.py | Create `_is_truthy()` helper following standard convention (true/1/yes) |
| `entrypoint.sh` uses shell, config.py uses Python | Check `DEV_MODE` in both places independently — shell check is simple string comparison |

### Resources

- `src/telegram_bot/config.py` — config module with env var handling
- `src/telegram_bot/run.py` — bot entry point with validation
- `src/telegram_bot/messages.py` — all user-facing strings
- `docker/entrypoint.sh` — container startup, bot process spawn
- `CLAUDE.md` — env vars documentation table
- `README.md` — user-facing documentation
