# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/20 (0%)
**Last updated:** 2026-02-08

## Goal

Replace all slash commands (/cancel, /skip, /done, /save) in Telegram bot conversation states with inline keyboard buttons. Users should be able to cancel, skip, save, etc. by tapping a button instead of typing a slash command. Free text input must remain functional alongside the new buttons.

From ROADMAP.md:
> Przerob wszystkie komunikaty bota telegram ktore wymagaja potwierdzania, anulowania itd na przyciski.

## Current Phase

Phase 1

## Phases

### Phase 1: Add inline Cancel button to text-input states
- [ ] Add `✗ Cancel` inline button to `ENTER_NAME` prompt (MSG_ENTER_WORKTREE_NAME) — send keyboard with `reply_markup` when entering state (bot.py ~line 410)
- [ ] Add `✗ Cancel` inline button to `ENTER_URL` prompt (MSG_ENTER_REPO_URL) — (bot.py ~line 402)
- [ ] Add `✗ Cancel` inline button to `ENTER_PROJECT_NAME` prompt (MSG_ENTER_PROJECT_NAME) — (bot.py ~line 395)
- [ ] Add `✗ Cancel` inline button to `ENTER_BRAINSTORM_PROMPT` prompt (MSG_BRAINSTORM_HEADER) — (bot.py ~line 459)
- [ ] Add `✗ Cancel` inline button to `SELECT_ITERATIONS` custom input prompt (MSG_ENTER_ITERATIONS) — (bot.py ~line 806)
- [ ] Add `CallbackQueryHandler` for new cancel button pattern in each affected state
- [ ] Remove "/cancel" text from message constants in messages.py (MSG_ENTER_WORKTREE_NAME, MSG_ENTER_REPO_URL, MSG_ENTER_PROJECT_NAME, MSG_BRAINSTORM_HEADER, MSG_ENTER_ITERATIONS)
- **Status:** pending

### Phase 2: Add Skip + Cancel buttons to ENTER_IDEA state
- [ ] Add `→ Skip` and `✗ Cancel` inline buttons to `ENTER_IDEA` prompt (MSG_PLAN_ENTER_IDEA) — (bot.py ~line 435)
- [ ] Add `CallbackQueryHandler` for skip/cancel button patterns in ENTER_IDEA state
- [ ] Remove "/skip" and "/cancel" text from MSG_PLAN_ENTER_IDEA in messages.py
- **Status:** pending

### Phase 3: Add Done/Save/Cancel buttons to BRAINSTORMING state
- [ ] Add `✓ Done` and `✗ Cancel` inline buttons to brainstorm reply hints (MSG_BRAINSTORM_REPLY_HINT, MSG_BRAINSTORM_REPLY_HINT_LONG)
- [ ] Add `✓ Save` button alongside `✓ Done` in the long hint variant (which mentions saving to ROADMAP.md)
- [ ] Add buttons to MSG_BRAINSTORM_RESUME message
- [ ] Add `CallbackQueryHandler` for done/save/cancel button patterns in BRAINSTORMING state
- [ ] Remove "/done", "/save", "/cancel" text from MSG_BRAINSTORM_REPLY_HINT, MSG_BRAINSTORM_REPLY_HINT_LONG, MSG_BRAINSTORM_RESUME, MSG_SESSION_ALREADY_ACTIVE, MSG_NO_ACTIVE_BRAINSTORM
- **Status:** pending

### Phase 4: Update tests
- [ ] Add tests for new cancel button callback in text-input states (test_bot.py or extend existing test files)
- [ ] Add tests for skip+cancel buttons in ENTER_IDEA state
- [ ] Add tests for done/save/cancel buttons in BRAINSTORMING state
- [ ] Run `python3 -m pytest src/telegram_bot/tests/ -v` — all tests pass
- [ ] Run `npm test --prefix src` — all tests pass
- **Status:** pending

## Findings & Decisions

### Requirements
- All states that accept free text input AND show "/cancel" (or /skip, /done, /save) text must get equivalent inline buttons
- Free text input must continue to work — users can still type their response
- Slash commands (/cancel, /skip, /done, /save) should remain as fallback handlers for backward compatibility, but the text prompts should no longer advertise them
- Button style must use existing Unicode symbols (✗, →, ✓) consistent with project conventions

### Research Findings

**7 conversation states** accept free text input and reference slash commands:

| State | Current Slash Commands | Button Replacement |
|-------|----------------------|-------------------|
| ENTER_NAME | /cancel | `✗ Cancel` button |
| ENTER_URL | /cancel | `✗ Cancel` button |
| ENTER_PROJECT_NAME | /cancel | `✗ Cancel` button |
| ENTER_BRAINSTORM_PROMPT | /cancel | `✗ Cancel` button |
| SELECT_ITERATIONS (custom) | /cancel | `✗ Cancel` button |
| ENTER_IDEA | /cancel, /skip | `→ Skip` + `✗ Cancel` buttons |
| BRAINSTORMING | /done, /save, /cancel | `✓ Done` + `✓ Save` + `✗ Cancel` buttons |

**Existing pattern to follow:** The `SELECT_ITERATIONS` state already has a `MSG_CANCEL_BTN` inline button with `callback_data="iter:cancel"` in its iteration selection menu (bot.py line 777). The new cancel buttons should follow this same pattern.

**No test_bot.py exists** — bot conversation handler layer has zero test coverage. New tests must be created.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use `callback_data` prefix per state (e.g. `input:cancel`, `idea:skip`) | Consistent with existing patterns (`iter:cancel`, `action:back`), allows state-specific handling |
| Keep /cancel, /skip, /done, /save as CommandHandler fallbacks | Backward compatibility — users who type commands still get expected behavior |
| Remove slash command text from messages but keep commands registered | Buttons become primary UX, commands remain as hidden fallback |
| Send buttons via `reply_markup` on the prompt message itself | Each prompt message gets its own keyboard — no separate message needed |
| Use single `CallbackQueryHandler` per state with pattern matching | Matches existing ConversationHandler state structure |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| InlineKeyboardMarkup on prompt message gets removed when user sends text (Telegram behavior) | Buttons are one-time use — after user types text, the keyboard disappears naturally which is acceptable |
| BRAINSTORMING state sends multiple messages (thinking, response, hint) | Attach buttons to the hint message which is the persistent guidance message |
| No existing test infrastructure for bot handlers | Create test utilities for mocking Update/Context in a new test_bot.py file |
