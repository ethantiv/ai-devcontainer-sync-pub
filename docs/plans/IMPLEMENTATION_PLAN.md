# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/10 (0%)

## Goal

Add a developer mode (`DEV_MODE` environment variable) that disables the Telegram bot in development containers. The user runs two Coolify deployments: `claude-code` (main branch) and `dev-claude-code` (develop branch). Both share the same `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, so the bot in the dev container could receive and execute commands meant for production — potentially running tasks in the wrong container.

## Current Phase

Phase 1: Implementation

## Phases

### Phase 1: Implementation
- [ ] Add `_is_truthy()` helper and `DEV_MODE` config variable to `src/telegram_bot/config.py` (after line 39, alongside other env vars)
- [ ] Add dev mode warning to `validate()` in `src/telegram_bot/config.py` (in warning checks section, after line 97)
- [ ] Add `MSG_DEV_MODE_SKIP` message constant to `src/telegram_bot/messages.py` (new section after error codes, ~line 27)
- [ ] Add dev mode check to `src/telegram_bot/run.py` — after `validate()` call (line 12), before `create_application()` (line 25): if `DEV_MODE` is true, print info message and `return 0`
- [ ] Add `DEV_MODE` check to `docker/entrypoint.sh` `start_telegram_bot()` — at top of function (after line 130), before token check: if `DEV_MODE` matches `true|1|yes` (case-insensitive), print skip message and `return 0`
- [ ] Document `DEV_MODE` env var in `CLAUDE.md` environment variables table (line ~53, after `TELEGRAM_CHAT_ID`)
- [ ] Document `DEV_MODE` env var in `README.md` environment variables section (line ~170, after `TELEGRAM_CHAT_ID`)
- **Status:** pending

### Phase 2: Testing
- [ ] Add tests for `_is_truthy()` in `test_config.py` — verify `true`/`1`/`yes`/`TRUE`/`Yes` return True; `false`/`0`/empty/unset return False
- [ ] Add tests for `DEV_MODE` in `test_config.py` — verify the variable is read correctly via `importlib.reload()` pattern (matching existing `TestConfigurableThresholds` style, line 249+)
- [ ] Add test in `test_config.py` — verify `validate()` returns a warning (not error) when `DEV_MODE` is active
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
1. `docker/entrypoint.sh:130-145` → `start_telegram_bot()` — checks TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (line 131), spawns `python3 -m loop.telegram_bot.run &` (line 143)
2. `src/telegram_bot/run.py:10-28` → `main()` — calls `validate()` (line 12), prints warnings (14-15), exits on errors (17-20), creates application (25), starts polling (26)

**Current code has zero dev mode handling:**
- No `DEV_MODE`, `DEBUG`, `DEVELOPER_MODE` variables anywhere in codebase (confirmed via full codebase grep)
- Only references exist in `docs/plans/IMPLEMENTATION_PLAN.md` (this file)
- 134 Python + 20 JS = 154 tests, all passing, none skipped

**Existing env var patterns in `config.py` (110 lines):**
- String vars: `environ.get("VAR", default)` — lines 28, 30, 39
- Int vars: `_safe_int(environ.get("VAR"), default)` — lines 29, 33, 37, 38
- Float vars: `_safe_float(environ.get("VAR"), default)` — lines 34-36
- Boolean pattern not yet used — will add `_is_truthy()` helper
- `validate()` at lines 42-99 returns `(errors, warnings)` tuple
- Warning checks section starts at line 78

**Existing message patterns in `messages.py` (231 lines):**
- All constants use `MSG_` prefix
- Error codes use `ERR_` prefix (lines 8-26)
- Messages grouped by module: bot.py (28-204), tasks.py (206-222), projects.py (224-230)
- New `MSG_DEV_MODE_SKIP` should go in a dedicated section

**Existing test patterns in `test_config.py` (409 lines, 34 tests, 7 classes):**
- Uses `_reload_and_validate()` helper (lines 16-25) with `patch.dict(os.environ)` + `importlib.reload()`
- `TestConfigurableThresholds` (lines 249-380) tests env var parsing with 3 tests per var: default, from env, invalid fallback
- Fixtures: `tmp_projects_root`, `env_with_valid_config` (in conftest.py)

**Files requiring changes (7 files, 10 tasks):**
1. `src/telegram_bot/config.py` — add `_is_truthy()` helper + `DEV_MODE` variable + warning in `validate()`
2. `src/telegram_bot/run.py` — add dev mode early exit between validate() and create_application()
3. `src/telegram_bot/messages.py` — add `MSG_DEV_MODE_SKIP` constant
4. `docker/entrypoint.sh` — add `DEV_MODE` check at top of `start_telegram_bot()`
5. `CLAUDE.md` — add `DEV_MODE` row to env vars table (line ~53)
6. `README.md` — add `DEV_MODE` row to env vars table (line ~170)
7. `src/telegram_bot/tests/test_config.py` — add `_is_truthy()` tests + `DEV_MODE` parsing tests + `validate()` warning test

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
