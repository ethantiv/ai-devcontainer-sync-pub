# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/8 (0%)
**Last updated:** 2026-02-08

## Goal

Remove remaining emoji from Telegram bot buttons and notifications, replacing them with Unicode symbols consistent with the rest of the project.

The project uses a consistent set of Unicode symbols for UI elements (e.g. `◉` `○` `◎` `◇` `■` `▶` `↺` `←` `↳` `≡` `✓` `✗` `Δ` `▸` `→` `~` `·` `+` `⚙`). However, 11 emoji characters remain across 3 files, breaking visual consistency.

## Phases

### Phase 1: Replace emoji in `messages.py` button labels
- [ ] Replace `MSG_GITHUB_PRIVATE_BTN`: `🔒 Private` -> `◆ Private` (filled diamond = closed/private)
- [ ] Replace `MSG_GITHUB_PUBLIC_BTN`: `🌐 Public` -> `○ Public` (open circle = public/open)
- [ ] Replace `MSG_BACK_BTN`: `⬅️ Back` (`\u2b05\ufe0f`) -> `← Back` (`\u2190`) — remove variation selector to use plain Unicode arrow
- **Status:** pending

### Phase 2: Replace emoji in `notify-telegram.sh`
- [ ] Replace status emoji: `✅` (success) -> `✓`, `✔️` (completed) -> `✓`, `⚠️` (interrupted) -> `!`, `❓` (unknown) -> `?`
- [ ] Replace mode emoji: `🔨` (build) -> `■`, `📋` (plan) -> `◇`, `🔄` (default) -> `~`
- **Status:** pending

### Phase 3: Replace emoji in `loop.sh`
- [ ] Replace `✅` in "Done" message (line 166) -> `✓`
- **Status:** pending

### Phase 4: Verify tests pass
- [ ] Run `python3 -m pytest src/telegram_bot/tests/ -v` — tests should pass unchanged (no direct emoji assertions found)
- [ ] Run `npm test --prefix src` — JS tests unaffected
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Which characters are emoji vs Unicode symbols? | Emoji: U+1F000+ range (🔒🌐🔨📋🔄) and emoji-presentation sequences (✅✔️⚠️❓⬅️). Unicode symbols: U+2000-U+2BFF range without variation selectors (✓✗◉○◎◇■▶↺←↳≡Δ▸→⚙). |
| What replaces `🔒` (Private)? | `◆` (U+25C6, Black Diamond) — filled shape suggests "closed/private", matches project's diamond vocabulary (`◇` for Plan). |
| What replaces `🌐` (Public)? | `○` (U+25CB, White Circle) — open shape suggests "public/open". `◎` considered but already used for Status button. |
| What replaces `⬅️` (Back)? | `←` (U+2190, Leftwards Arrow) — standard arrow without variation selector, matches project's arrow vocabulary (`→` `↳` `↺`). |
| Do tests need updating? | No — test assertions use generic string matching (e.g. `assert success is True`, `assert "Queued" in msg`), not emoji comparisons. |
| Is `notify-telegram.sh` in scope? | Yes — ROADMAP says "buttons" but the shell script also sends messages to Telegram with emoji, and the project's CLAUDE.md documents `ok()`/`warn()`/`fail()` helpers using non-emoji symbols. |
| Should `bot.py` inline symbols be centralized to `messages.py`? | Out of scope — `bot.py` uses consistent Unicode symbols (◇■◉↳▸✓✗█░≡), not emoji. Centralizing them is a separate refactoring task. |

## Findings & Decisions

### Requirements
- Replace 11 emoji instances across 3 files with Unicode symbols
- Maintain visual meaning (private=closed, public=open, success=check, error=warning, etc.)
- All replacements must use symbols from the project's existing vocabulary where possible
- Tests must pass without changes

### Research Findings

**Emoji locations (11 instances across 3 files):**

| File | Line | Current | Replacement | Rationale |
|------|------|---------|-------------|-----------|
| `src/telegram_bot/messages.py` | 50 | `⬅️ Back` (`\u2b05\ufe0f`) | `← Back` (`\u2190`) | Remove variation selector, use plain arrow |
| `src/telegram_bot/messages.py` | 258 | `🔒 Private` | `◆ Private` | Filled diamond = closed/private |
| `src/telegram_bot/messages.py` | 259 | `🌐 Public` | `○ Public` | Open circle = public/open |
| `src/scripts/notify-telegram.sh` | 38 | `✅` (success) | `✓` | Matches project's check mark |
| `src/scripts/notify-telegram.sh` | 39 | `✔️` (completed) | `✓` | Matches project's check mark |
| `src/scripts/notify-telegram.sh` | 40 | `⚠️` (interrupted) | `!` | Matches project's exclamation pattern |
| `src/scripts/notify-telegram.sh` | 41 | `❓` (unknown) | `?` | Simple question mark |
| `src/scripts/notify-telegram.sh` | 46 | `🔨` (build) | `■` | Matches `MSG_BUILD_BTN` symbol |
| `src/scripts/notify-telegram.sh` | 47 | `📋` (plan) | `◇` | Matches `MSG_PLAN_BTN` symbol |
| `src/scripts/notify-telegram.sh` | 48 | `🔄` (default) | `~` | Matches `MSG_BRAINSTORM_BTN` symbol |
| `src/scripts/loop.sh` | 166 | `✅` | `✓` | Matches project's check mark |

**Test impact analysis:**
- `test_projects.py`: Tests `create_github_repo()` and `validate_project_name()` — assertions check return tuples `(bool, str)` with generic string content, not emoji characters
- `test_tasks.py`: Tests queue/persistence — no emoji in assertions
- `test_config.py`: Tests env var parsing — no emoji
- `test_git_utils.py`: Tests git operations — no emoji

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use `◆` for Private (not `⊗`) | Consistent with diamond vocabulary in project (`◇` Plan, `◆` Private) |
| Use `○` for Public (not `◎`) | `◎` already used for Status button — avoid visual confusion |
| Use `←` for Back (not `⬅️`) | `\u2b05\ufe0f` has variation selector forcing emoji-presentation; `\u2190` is a plain arrow matching `→` `↳` `↺` vocabulary |
| Use `✓` for success/completed (not `+`) | `✓` (U+2713) already used extensively in messages.py for success states |
| Use `!` for interrupted (not `⚡`) | `!` already used in `MSG_STALE_PROGRESS` for warnings |
| Use `■`/`◇`/`~` for mode icons | Direct match with existing button labels in messages.py |
| Keep `notify-telegram.sh` in scope | Telegram notifications are part of the bot's user-facing output |
