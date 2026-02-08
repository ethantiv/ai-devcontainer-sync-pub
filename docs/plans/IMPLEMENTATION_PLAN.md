# Implementation Plan

**Status:** COMPLETE
**Progress:** 8/8 (100%)
**Last updated:** 2026-02-08

## Goal

Remove remaining emoji from Telegram bot buttons and notifications, replacing them with Unicode symbols consistent with the rest of the project.

The project uses a consistent set of Unicode symbols for UI elements (e.g. `◉` `○` `◎` `◇` `■` `▶` `↺` `←` `↳` `≡` `✓` `✗` `Δ` `▸` `→` `~` `·` `+` `⚙`). However, 11 emoji characters remain across 3 files, breaking visual consistency.

## Phases

### Phase 1: Replace emoji in `messages.py` button labels
- [x] Replace `MSG_GITHUB_PRIVATE_BTN`: `🔒 Private` -> `◆ Private` (filled diamond = closed/private)
- [x] Replace `MSG_GITHUB_PUBLIC_BTN`: `🌐 Public` -> `○ Public` (open circle = public/open)
- [x] Replace `MSG_BACK_BTN`: `⬅️ Back` (`\u2b05\ufe0f`) -> `← Back` (`\u2190`) — remove variation selector to use plain Unicode arrow
- **Status:** complete

### Phase 2: Replace emoji in `notify-telegram.sh`
- [x] Replace status emoji: `✅` (success) -> `✓`, `✔️` (completed) -> `✓`, `⚠️` (interrupted) -> `!`, `❓` (unknown) -> `?`
- [x] Replace mode emoji: `🔨` (build) -> `■`, `📋` (plan) -> `◇`, `🔄` (default) -> `~`
- **Status:** complete

### Phase 3: Replace emoji in `loop.sh`
- [x] Replace `✅` in "Done" message (line 166) -> `✓`
- **Status:** complete

### Phase 4: Verify tests pass
- [x] Run `python3 -m pytest src/telegram_bot/tests/ -v` — 180 passed
- [x] Run `npm test --prefix src` — 20 passed
- **Status:** complete
