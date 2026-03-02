# Remove Telegram Bot Integration — Design Document

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the Telegram bot integration entirely from the project.

**Approach:** Surgical removal — delete only code and configuration directly related to the Telegram bot, leaving the loop system and all other components untouched.

---

## Context

The Telegram bot (`src/telegram_bot/`) is a self-contained Python package that provides remote control for loop tasks and brainstorming sessions via Telegram. The integration is **unidirectional** — the bot reads loop system state (`.progress` files, JSONL logs, tmux sessions), but the loop system has zero dependencies on the bot.

### Current Architecture

```
Telegram Bot (Python, background process)
    |
    |--- starts loop.sh in tmux
    |--- polls tmux session status (every 30s/15s)
    |--- reads .progress file (written by loop.sh)
    |--- reads .tasks.json (own state in PROJECTS_ROOT)
    |--- calls summary.js via node subprocess
    |--- sends Telegram notifications on completion
```

The bot consists of 10 Python modules, 6 test files (476 tests), and one external dependency (`python-telegram-bot[job-queue]`).

---

## Decision Log

| Question | Decision |
|----------|----------|
| Log rotation (`cleanup.js` → `log_rotation.py`) | Remove entirely with the bot |
| `notify-telegram.sh` standalone script | Remove entirely |
| `DEV_MODE` environment variable | Remove — only used to disable the bot |
| `loop cleanup` command (`cleanup.js`) | Remove entirely |
| Python layers in Docker | Clean up (remove pip install, requirements.txt COPY) |

---

## Files to Delete

| Path | Description |
|------|-------------|
| `src/telegram_bot/` | Entire directory — 10 Python modules + 6 test files (476 tests) |
| `src/scripts/notify-telegram.sh` | Standalone curl notifier to Telegram API |
| `src/lib/cleanup.js` | `loop cleanup` command — only calls `log_rotation.py` from the bot |

~17 files, ~4000+ lines of code.

---

## Files to Modify

### Docker

**`docker/Dockerfile`**
- Remove: `COPY src/telegram_bot/requirements.txt /tmp/requirements.txt`
- Remove: `RUN pip install ... -r /tmp/requirements.txt`
- Remove: comments about Telegram bot

**`docker/entrypoint.sh`**
- Remove: `start_telegram_bot()` function (~25 lines)
- Remove: `start_telegram_bot` invocation
- Remove: Telegram status from the status printout (DEV_MODE/TOKEN conditional)

### Loop system

**`src/lib/init.js`**
- Remove: `{ src: 'scripts/notify-telegram.sh', dest: 'loop/notify-telegram.sh' }` from symlink list

**`src/lib/__tests__/integration.test.js`**
- Remove: `'loop/notify-telegram.sh'` from `EXPECTED_SYMLINKS`

**`src/scripts/kill-loop.sh`**
- Remove: comment "and Telegram bot tmux sessions" (line 3). The rest stays — killing `loop-*` sessions is general.

**`src/bin/cli.js`**
- Remove: `cleanup` command registration (since `cleanup.js` is deleted)

### Configuration

**`.devcontainer/devcontainer.json`**
- Remove: `"DEV_MODE": "true"` from `remoteEnv`

**`.devcontainer/.env.example`**
- Remove: Telegram Bot section (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Remove: DEV_MODE section

### Documentation

**`CLAUDE.md`**
- Remove: "Telegram bot (Python)" from project description
- Remove: Python test commands (`python3 -m pytest src/telegram_bot/tests/`)
- Remove: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEV_MODE from env var table
- Remove: `src/telegram_bot/` from structure and operational sections
- Remove: `requirements.txt` mention from codebase patterns
- Update: project description, loop system structure, test counts

**`README.md`**
- Remove: "Telegram Bot" section
- Remove: TELEGRAM_* and DEV_MODE from env var table
- Update: project description

---

## What We Do NOT Touch

- Loop system (`loop.sh`, `cli.js`, `run.js`, `init.js` beyond symlink, `summary.js`)
- Docker compose files (`docker-compose.yml`, `docker-compose.dev.yml`)
- Setup scripts (`setup-env.sh`, `setup-local.sh`, `setup-claude.sh`)
- Skills/plugins configuration
- MCP servers

---

## Validation

After removal, run remaining test suites to confirm no regressions:

```bash
npm install --prefix src && npm test --prefix src     # JS tests (~33 after cleanup removal)
npm run test:integration --prefix src                  # Integration tests (~13)
bash src/scripts/tests/test_write_idea.sh              # Shell tests (18)
bash src/scripts/tests/test_check_completion.sh        # Shell tests (20)
bash src/scripts/tests/test_ensure_playwright.sh       # Shell tests (14)
```

Python tests (`pytest`) are entirely removed — no Python code remains to test.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `cleanup.js` imported elsewhere | Low — registered as CLI command only | Grep for `cleanup` in `cli.js` and `run.js` |
| `requirements.txt` reference in CI | None — no CI pipeline | N/A |
| Existing Docker volumes with bot data | Low — `.tasks.json` etc. are harmless | Files in `PROJECTS_ROOT` can remain — ignored without bot |
| Coolify rebuild without bot | None — bot simply won't start | Rebuild works cleanly |
