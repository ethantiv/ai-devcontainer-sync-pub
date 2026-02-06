# Migrate Loop System from Playground to ai-devcontainer-sync

**Date**: 2026-02-06
**Status**: In Progress

## Goal

Eliminate the dependency on `ethantiv/playground` by migrating the entire loop system (autonomous dev loop, Telegram bot, npm CLI) into this repository.

## Current State

- `playground` is cloned at runtime via `entrypoint.sh` → `setup_playground()`
- `dev-loop` npm package is installed globally from private GH repo via `setup-env.sh`
- Telegram bot runs from `~/projects/playground/loop/telegram_bot`
- Dockerfile has bash `loop()` function pointing to playground paths

## Target Structure

```
loop/
├── package.json              # npm package (dev-loop)
├── bin/cli.js                # CLI entry point
├── lib/
│   ├── init.js               # Project initialization
│   ├── run.js                # Run loop
│   └── cleanup.js            # Cleanup ports
├── scripts/
│   ├── loop.sh               # Main orchestrator
│   ├── cleanup.sh            # Kill dev server ports
│   └── notify-telegram.sh    # Telegram notifications
├── prompts/
│   ├── PROMPT_plan.md
│   ├── PROMPT_build.md
│   └── PROMPT_skills.md
├── templates/
│   ├── CLAUDE_template.md
│   ├── IMPLEMENTATION_PLAN_template.md
│   └── IDEA_template.md
├── telegram_bot/
│   ├── __init__.py
│   ├── run.py
│   ├── bot.py
│   ├── tasks.py
│   ├── projects.py
│   ├── config.py
│   └── COMMANDS.md
└── .claude/
    ├── settings.json
    └── skills/auto-revise-claude-md/SKILL.md
```

## Changes Required

### 1. Copy files from playground → loop/ (new structure)

### 2. Dockerfile
- COPY `loop/` to `/opt/loop/`
- `npm install --omit=dev` in `/opt/loop/`
- Symlink `/usr/bin/loop` → `/opt/loop/bin/cli.js`
- Remove bash `loop()` function from `.bashrc`

### 3. entrypoint.sh
- Remove `setup_playground()` section entirely
- Update `start_telegram_bot()` paths → `/opt/loop/telegram_bot`
- Update startup info section

### 4. setup-env.sh
- Remove `dev-loop` install from `install_global_npm_tools()`

### 5. Code path updates
- `loop.sh`: relative paths for prompts/scripts
- `lib/init.js`: source paths for symlinks/copies
- `telegram_bot/config.py`: remove playground-specific defaults
- `telegram_bot/tasks.py`: loop.sh path

### 6. CLAUDE.md updates
- Loop CLI section: built-in instead of GH install
- Remove playground entrypoint pattern
- Update adding npm tools section
