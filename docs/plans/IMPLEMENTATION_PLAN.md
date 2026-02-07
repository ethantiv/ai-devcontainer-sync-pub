# Implementation Plan

**Status:** COMPLETE
**Progress:** 10/10 (100%)

## Goal

Add a developer mode (`DEV_MODE` environment variable) that disables the Telegram bot in development containers. The user runs two Coolify deployments: `claude-code` (main branch) and `dev-claude-code` (develop branch). Both share the same `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, so the bot in the dev container could receive and execute commands meant for production — potentially running tasks in the wrong container.

## Phases

### Phase 1: Implementation
- [x] Add `_is_truthy()` helper and `DEV_MODE` config variable to `src/telegram_bot/config.py`
- [x] Add dev mode warning to `validate()` in `src/telegram_bot/config.py`
- [x] Add `MSG_DEV_MODE_SKIP` message constant to `src/telegram_bot/messages.py`
- [x] Add dev mode check to `src/telegram_bot/run.py` — early exit with code 0 when `DEV_MODE` is active
- [x] Add `DEV_MODE` check to `docker/entrypoint.sh` `start_telegram_bot()` — shell-level check before token check
- [x] Document `DEV_MODE` env var in `CLAUDE.md` environment variables table
- [x] Document `DEV_MODE` env var in `README.md` environment variables section
- **Status:** complete

### Phase 2: Testing
- [x] Add tests for `_is_truthy()` in `test_config.py` — 11 tests covering true/1/yes/TRUE/Yes/false/0/empty/None
- [x] Add tests for `DEV_MODE` in `test_config.py` — 4 tests for default, true, 1, false via `importlib.reload()` pattern
- [x] Add tests for `validate()` with DEV_MODE — 2 tests for warning present/absent
- **Status:** complete

## Key Questions

| Question | Answer |
|----------|--------|
| Where should `DEV_MODE` block the bot? | Two layers: `entrypoint.sh` (prevents process spawn) and `run.py` (graceful exit if called directly). Defense in depth. |
| Should it be a warning or error in validate()? | Warning — `DEV_MODE` is intentional behavior, not a misconfiguration. Print info message and exit 0 (not error exit 1). |
| What values should `DEV_MODE` accept? | `true`, `1`, `yes` (case-insensitive) = enabled. Anything else or unset = disabled. Standard boolean env var pattern. |
| Should `DEV_MODE` affect anything besides the Telegram bot? | No. ROADMAP.md scope is specifically about disabling the Telegram bot. Loop CLI, scripts, and all other functionality remain unaffected. |
| Where to add the env var for dev-claude-code on Coolify? | User sets `DEV_MODE=true` in the Coolify environment variables for the `dev-claude-code` app only. |

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use `DEV_MODE` name (not `DISABLE_TELEGRAM_BOT`) | Matches ROADMAP.md intent ("tryb developerski"). Semantically describes the container's role, not a specific feature toggle. Clearer for Coolify UI. |
| Check in both `entrypoint.sh` AND `run.py` | Defense in depth. `entrypoint.sh` prevents process spawn (saves resources). `run.py` handles direct invocation. |
| Exit with code 0 (not 1) in run.py | Dev mode is intentional, not an error. Exit 0 = clean shutdown. |
| Add `_is_truthy()` helper to config.py | Reusable boolean env var parser. Accepts `true/1/yes` (case-insensitive). Follows common convention. |
| Add as warning in validate() | Inform the user that bot is disabled, but don't treat it as an error that prevents startup (since startup is intentionally skipped). |
| Do NOT add `DEV_MODE` to docker/.env | The `.env` file is for production. Dev mode should be set per-deployment in Coolify UI. |
