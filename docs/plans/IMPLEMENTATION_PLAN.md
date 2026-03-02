# Remove Telegram Bot Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surgically remove the Telegram bot integration from the project, leaving the loop system and all other components untouched.

**Architecture:** The Telegram bot (`src/telegram_bot/`) is a self-contained Python package with zero reverse dependencies — the loop system never imports from it. Removal is a delete + reference cleanup across Docker, config, init, and docs. One exception: `cleanup.js` has a `--logs` flag that calls `log_rotation.py` from the bot — this flag is removed but the port-killing functionality stays.

**Tech Stack:** Shell (Docker, entrypoint), Node.js (loop CLI), JSON (devcontainer.json)

**Design doc:** `docs/plans/2026-03-02-remove-telegram-bot-design.md`

---

## Findings & Decisions

| Finding | Decision |
|---------|----------|
| `cleanup.js` has TWO modes: default (kill ports via cleanup.sh) and `--logs` (call log_rotation.py from bot) | Keep cleanup.js but remove `--logs` option and `cleanupLogs()` function. Design doc was incorrect in saying "remove cleanup.js entirely" |
| `notify-telegram.sh` is symlinked by init.js but never called by any script | Remove file and symlink entry |
| `cleanup.sh` (port killer) is used by both `cleanup.js` and `loop.sh` | Keep — not telegram-related |
| `python3` and `python3-pip` in Dockerfile runtime | Keep — useful for dev, only remove telegram requirements.txt install |
| `LOOP_*` env vars defined in `src/telegram_bot/config.py` | Removed with the bot — update CLAUDE.md reference |
| `kill-loop.sh` kills `loop-*` tmux sessions — used by bot AND standalone | Keep the logic, update comments only |

---

## Phase 1: Delete Telegram Bot Source Code

**Status:** pending

### Task 1: Delete bot directory, notify script, and refactor cleanup.js

- [ ] Remove src/telegram_bot/, src/scripts/notify-telegram.sh, strip cleanup.js of log rotation

**Files:**
- Delete: `src/telegram_bot/` (entire directory — 17 files, 476 tests)
- Delete: `src/scripts/notify-telegram.sh`
- Modify: `src/lib/cleanup.js`
- Modify: `src/bin/cli.js`

**Step 1: Delete the bot directory and notify script**

```bash
rm -rf src/telegram_bot/
rm src/scripts/notify-telegram.sh
```

**Step 2: Refactor cleanup.js — remove log rotation, keep port killing**

Replace entire `src/lib/cleanup.js` with:

```javascript
const { spawn } = require('child_process');
const fs = require('fs');

function cleanup() {
  const cleanupScript = './loop/cleanup.sh';

  if (!fs.existsSync(cleanupScript)) {
    console.error('Error: loop/cleanup.sh not found. Run "npx loop init" first.');
    process.exit(1);
  }

  const child = spawn(cleanupScript, [], {
    stdio: 'inherit',
    cwd: process.cwd(),
  });

  child.on('close', (code) => {
    process.exit(code ?? 0);
  });
}

module.exports = { cleanup };
```

**Step 3: Update cli.js — remove --logs option and update help text**

In `src/bin/cli.js`:
- Line 6: Change `const { cleanup } = require('../lib/cleanup');` — keep as-is (still valid)
- Lines 65-69: Remove the `--logs` option:

```javascript
program
  .command('cleanup')
  .description('Kill processes on dev server ports (3000, 5173, 8080, etc.)')
  .action(() => cleanup());
```

- Line 96: Remove `$ loop cleanup --logs     Rotate and prune log files` from help text

**Step 4: Run JS tests to verify no regressions**

Run: `npm test --prefix src`
Expected: All tests pass (no test references cleanup.js internals)

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: remove telegram bot source code and log rotation

Delete src/telegram_bot/ (17 files, 476 tests), notify-telegram.sh,
and strip cleanup.js of --logs/cleanupLogs (keeps port-killing)."
```

---

## Phase 2: Update Loop Init and Integration Tests

**Status:** pending

### Task 2: Remove notify-telegram.sh from init.js symlink list

- [ ] Remove notify-telegram.sh entry from CORE_FILES in init.js

**Files:**
- Modify: `src/lib/init.js:13`

**Step 1: Edit init.js — remove notify-telegram.sh from CORE_FILES**

In `src/lib/init.js`, remove line 13:
```javascript
  { src: 'scripts/notify-telegram.sh', dest: 'loop/notify-telegram.sh' },
```

The remaining CORE_FILES array should be:
```javascript
const CORE_FILES = [
  { src: 'scripts/loop.sh', dest: 'loop/loop.sh' },
  { src: 'prompts/PROMPT_design.md', dest: 'loop/PROMPT_design.md' },
  { src: 'prompts/PROMPT_plan.md', dest: 'loop/PROMPT_plan.md' },
  { src: 'prompts/PROMPT_build.md', dest: 'loop/PROMPT_build.md' },
  { src: 'scripts/cleanup.sh', dest: 'loop/cleanup.sh' },
  { src: 'scripts/kill-loop.sh', dest: 'loop/kill-loop.sh' },
];
```

**Step 2: Update integration test — remove notify-telegram.sh from EXPECTED_SYMLINKS**

In `src/lib/__tests__/integration.test.js`, remove line 39:
```javascript
  'loop/notify-telegram.sh',
```

The remaining EXPECTED_SYMLINKS array should be:
```javascript
const EXPECTED_SYMLINKS = [
  'loop/loop.sh',
  'loop/PROMPT_design.md',
  'loop/PROMPT_plan.md',
  'loop/PROMPT_build.md',
  'loop/cleanup.sh',
  'loop/kill-loop.sh',
];
```

**Step 3: Run JS tests to verify**

Run: `npm test --prefix src`
Expected: All tests pass

Run: `npm run test:integration --prefix src`
Expected: All integration tests pass

**Step 4: Commit**

```bash
git add src/lib/init.js src/lib/__tests__/integration.test.js
git commit -m "chore: remove notify-telegram.sh from loop init symlinks"
```

---

## Phase 3: Docker Cleanup

**Status:** pending

### Task 3: Remove telegram-related lines from Dockerfile

- [ ] Remove telegram requirements.txt install and update comment in Dockerfile

**Files:**
- Modify: `docker/Dockerfile:48-50,74`

**Step 1: Remove telegram pip install from Dockerfile**

In `docker/Dockerfile`, remove lines 48-50:
```dockerfile
# Python packages for Telegram bot (job-queue extra includes APScheduler)
COPY src/telegram_bot/requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt
```

**Step 2: Update comment on line 74**

Change:
```dockerfile
# Install loop system (autonomous dev loop + Telegram bot + CLI)
```
To:
```dockerfile
# Install loop system (autonomous dev loop + CLI)
```

**Step 3: Commit**

```bash
git add docker/Dockerfile
git commit -m "chore: remove telegram bot dependencies from Dockerfile"
```

### Task 4: Remove telegram bot from entrypoint.sh

- [ ] Remove start_telegram_bot function and status line from entrypoint.sh

**Files:**
- Modify: `docker/entrypoint.sh:121-149,191`

**Step 1: Remove the TELEGRAM BOT section (lines 121-149)**

Delete these lines from `docker/entrypoint.sh`:
```bash
# =============================================================================
# TELEGRAM BOT (optional, runs in background)
# =============================================================================

start_telegram_bot() {
    # Skip bot in dev mode — prevents dev container from stealing production commands
    if [[ "${DEV_MODE,,}" =~ ^(true|1|yes)$ ]]; then
        echo "  ✔︎ DEV_MODE active — skipping Telegram bot"
        return 0
    fi

    if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
        return 0
    fi

    local BOT_MODULE="/opt/loop/telegram_bot"

    if [[ ! -d "$BOT_MODULE" ]]; then
        echo "  ⚠️  Telegram bot module not found"
        return 0
    fi

    # Start bot in background (PYTHONPATH so imports resolve from /opt/loop parent)
    PYTHONPATH="/opt" PROJECTS_ROOT="$HOME/projects" python3 -m loop.telegram_bot.run &
    echo "  ✔︎ Telegram bot started (PID: $!)"
}

# Start Telegram bot if configured
start_telegram_bot
```

**Step 2: Remove telegram status line (line 191)**

Delete:
```bash
echo "  Telegram bot        : $(if [[ "${DEV_MODE,,}" =~ ^(true|1|yes)$ ]]; then echo 'disabled (DEV_MODE)'; elif [ -n "$TELEGRAM_BOT_TOKEN" ]; then echo 'running'; else echo 'not configured'; fi)"
```

**Step 3: Commit**

```bash
git add docker/entrypoint.sh
git commit -m "chore: remove telegram bot startup from Docker entrypoint"
```

---

## Phase 4: Configuration and Script Cleanup

**Status:** pending

### Task 5: Remove DEV_MODE and Telegram vars from config files

- [ ] Clean up devcontainer.json, .env.example, and kill-loop.sh comment

**Files:**
- Modify: `.devcontainer/devcontainer.json:47`
- Modify: `.devcontainer/.env.example:32-40`
- Modify: `src/scripts/kill-loop.sh:3,42`

**Step 1: Remove DEV_MODE from devcontainer.json**

In `.devcontainer/devcontainer.json`, remove line 47:
```json
    "DEV_MODE": "true"
```

Make sure the preceding line (`"LC_TIME": "pl_PL.UTF-8"`) no longer has a trailing comma issue — JSON requires no trailing comma on the last entry.

**Step 2: Remove Telegram and DEV_MODE sections from .env.example**

In `.devcontainer/.env.example`, remove lines 32-34 (Telegram Bot section):
```
# --- Telegram Bot (optional) ---
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_CHAT_ID=
```

And remove the DEV_MODE comment on line 39:
```
# Set to true/1/yes to disable Telegram bot in dev containers
```
And remove line 40:
```
# DEV_MODE=
```

Keep the Docker Deployment section header and APP_NAME — those are still valid.

**Step 3: Update kill-loop.sh comments**

In `src/scripts/kill-loop.sh`:
- Line 3: Change `# orphaned claude -p processes, and Telegram bot tmux sessions.` to `# and orphaned claude -p processes.`
- Line 42: Change `# Step 4: Kill Telegram bot tmux sessions matching loop-*` to `# Step 4: Kill loop tmux sessions matching loop-*`

**Step 4: Commit**

```bash
git add .devcontainer/devcontainer.json .devcontainer/.env.example src/scripts/kill-loop.sh
git commit -m "chore: remove DEV_MODE and Telegram config from devcontainer and env"
```

---

## Phase 5: Documentation Updates

**Status:** pending

### Task 6: Update CLAUDE.md

- [ ] Remove all telegram bot references from CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update project description (line 5)**

Change:
```
DevContainer for multi-AI agent development with Claude Code and Gemini CLI. Includes configuration, loop system (Node.js CLI + shell scripts), Telegram bot (Python), prompts, and templates.
```
To:
```
DevContainer for multi-AI agent development with Claude Code and Gemini CLI. Includes configuration, loop system (Node.js CLI + shell scripts), prompts, and templates.
```

**Step 2: Remove Python test command (line 19)**

Delete:
```
python3 -m pytest src/telegram_bot/tests/ -v  # Run Telegram bot tests (476 tests)
```

**Step 3: Remove Python single test example (line 27)**

Delete:
```
Single test: `python3 -m pytest src/telegram_bot/tests/test_tasks.py::TestTaskManager::test_start_task -v`
```

**Step 4: Remove TELEGRAM_* and DEV_MODE from env var table (lines 51, 53)**

Delete these rows:
```
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | No | Telegram bot auth |
```
```
| `DEV_MODE` | No | Disable Telegram bot in dev containers (true/1/yes) |
```

**Step 5: Remove LOOP_* env vars reference (line 55)**

Delete:
```
`LOOP_*` env vars (thresholds, timeouts, queue limits) are defined with defaults in `src/telegram_bot/config.py`.
```

**Step 6: Update loop system section (lines 65, 71, 74, 76)**

- Delete line 65: `Telegram bot: /opt/loop/telegram_bot/ with PYTHONPATH="/opt".`
- Line 71: Change `loop summary / cleanup  # Show run stats / clean artifacts` to `loop summary / cleanup  # Show run stats / kill dev server processes`
- Line 74: Change `**Structure**: src/scripts/ (shell), src/prompts/, src/templates/, src/telegram_bot/ (Python bot + handlers/), src/bin/ + src/lib/ (Node.js CLI).` to `**Structure**: `src/scripts/` (shell), `src/prompts/`, `src/templates/`, `src/bin/` + `src/lib/` (Node.js CLI).`
- Delete line 76: `**Telegram bot**: Starts in Docker if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID set.`

**Step 7: Remove codebase pattern references (lines 127-128)**

Delete:
```
- **Python deps**: Add to `src/telegram_bot/requirements.txt` — Dockerfile auto-installs.
```
Delete:
```
- **Test patterns**: pytest + pytest-asyncio. Patch `PROJECTS_ROOT` in module namespace, not via env vars. Fixtures with `with patch(...)` must `yield` not `return`. Bot tests patch `TELEGRAM_CHAT_ID` in the module where the decorated function is defined.
```

**Step 8: Verify CLAUDE.md is valid and well-formatted**

Read the file after edits to confirm no broken formatting or orphan references.

**Step 9: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: remove telegram bot references from CLAUDE.md"
```

### Task 7: Update README.md

- [ ] Remove Telegram Bot section and env vars from README.md

**Files:**
- Modify: `README.md`

**Step 1: Remove "Telegram Bot" from What's Inside (line 9)**

Delete:
```
**Telegram Bot** — remote control for loop tasks and brainstorming sessions
```

**Step 2: Remove DEV_MODE from Coolify section (line 50)**

Remove `DEV_MODE=true` from the env vars mention, if present.

**Step 3: Remove entire Telegram Bot section (lines 84-86)**

Delete:
```
## Telegram Bot

Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .devcontainer/.env to enable. Starts automatically in Docker.
```

**Step 4: Remove TELEGRAM_* and DEV_MODE from env var table (lines 104-105, 110)**

Delete:
```
| TELEGRAM_BOT_TOKEN | No | Telegram bot token for remote control |
| TELEGRAM_CHAT_ID | No | Authorized Telegram chat ID |
```
```
| DEV_MODE | No | Disable Telegram bot (true/1/yes) |
```

**Step 5: Verify README.md is valid and well-formatted**

Read the file after edits to confirm no broken formatting.

**Step 6: Commit**

```bash
git add README.md
git commit -m "docs: remove telegram bot references from README.md"
```

---

## Phase 6: Final Validation

**Status:** pending

### Task 8: Run all remaining test suites

- [ ] Verify all test suites pass with no regressions

**Files:**
- None (read-only validation)

**Step 1: Run JS unit tests**

Run: `npm install --prefix src && npm test --prefix src`
Expected: All tests pass

**Step 2: Run JS integration tests**

Run: `npm run test:integration --prefix src`
Expected: All tests pass

**Step 3: Run shell tests**

Run: `bash src/scripts/tests/test_write_idea.sh`
Expected: All 18 tests pass

Run: `bash src/scripts/tests/test_check_completion.sh`
Expected: All 20 tests pass

Run: `bash src/scripts/tests/test_ensure_playwright.sh`
Expected: All 14 tests pass

**Step 4: Verify no dangling telegram references**

Run: `grep -ri telegram --include='*.js' --include='*.sh' --include='*.json' --include='*.md' . | grep -v node_modules | grep -v '.git/' | grep -v 'docs/plans/'`
Expected: No matches (all references removed except design doc in docs/plans/)

**Step 5: Final commit (if any fixes needed)**

If any test failures required fixes, commit those fixes.

**Step 6: Bump package version**

In `src/package.json`, bump the patch version (e.g., 0.x.Y → 0.x.Y+1) to reflect the removal.

```bash
git add src/package.json
git commit -m "chore: bump loop package version after telegram bot removal"
```
