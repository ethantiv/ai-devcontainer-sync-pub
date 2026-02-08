# Implementation Plan

**Status:** COMPLETE
**Progress:** 17/17 (100%)
**Last updated:** 2026-02-08
**Line numbers verified:** 2026-02-08 (bot.py line numbers shifted +15 from Phase 2 additions)

## Goal

Replace all slash commands (/cancel, /skip, /done, /save) in Telegram bot conversation states with inline keyboard buttons. Users should be able to cancel, skip, save, etc. by tapping a button instead of typing a slash command. Free text input must remain functional alongside the new buttons.

From ROADMAP.md:
> Przerob wszystkie komunikaty bota telegram ktore wymagaja potwierdzania, anulowania itd na przyciski.

## Current Phase

All phases complete

## Phases

### Phase 1: Add inline Cancel button to text-input states
- [x] Create cancel keyboard helper — `_cancel_keyboard(callback_data)` (bot.py line 216)
- [x] Add cancel button to `ENTER_PROJECT_NAME` prompt (bot.py line 401)
- [x] Add cancel button to `ENTER_URL` prompt (bot.py line 409)
- [x] Add cancel button to `ENTER_NAME` prompt (bot.py line 417)
- [x] Add cancel button to `ENTER_BRAINSTORM_PROMPT` prompt (bot.py line 466)
- [x] Add cancel button to `SELECT_ITERATIONS` custom input prompt (bot.py line 823)
- [x] Add `CallbackQueryHandler(handle_input_cancel, pattern=r"^input:cancel$")` to 5 states
- [x] Remove "/cancel" text from 5 message constants in messages.py
- **Status:** complete

### Phase 2: Add Skip + Cancel buttons to ENTER_IDEA state
- [x] Add `→ Skip` + `✗ Cancel` inline buttons to `ENTER_IDEA` prompt — reused `MSG_GITHUB_SKIP_BTN` (bot.py line 449-455)
- [x] Add `CallbackQueryHandler(handle_idea_button, pattern=r"^idea:")` to ENTER_IDEA state (bot.py line 1382)
- [x] Remove "/skip" and "/cancel" text from MSG_PLAN_ENTER_IDEA (messages.py line 78-80)
- **Status:** complete

### Phase 3: Add Done/Save/Cancel buttons to BRAINSTORMING state
- [x] Create brainstorm button keyboards — `_brainstorm_hint_keyboard()` and `_brainstorm_hint_long_keyboard()` (bot.py)
- [x] Add `MSG_BRAINSTORM_DONE_BTN = "✓ Done"` and `MSG_BRAINSTORM_SAVE_BTN = "✓ Save"` to messages.py
- [x] Pass `reply_markup=_brainstorm_hint_keyboard()` when sending `MSG_BRAINSTORM_REPLY_HINT` after `brainstorm_manager.start()` in button flow
- [x] Pass `reply_markup=_brainstorm_hint_long_keyboard()` when sending `MSG_BRAINSTORM_REPLY_HINT_LONG` after `/brainstorming` command flow
- [x] Pass `reply_markup=_brainstorm_hint_keyboard()` to brainstorm reply messages in `handle_brainstorm_message()` — appends hint text and buttons after Claude's response
- [x] Pass `reply_markup=_brainstorm_hint_keyboard()` when sending `MSG_BRAINSTORM_RESUME`
- [x] Add `CallbackQueryHandler(handle_brainstorm_hint_button, pattern=r"^bs:")` to BRAINSTORMING state
- [x] Remove slash command text from messages: MSG_BRAINSTORM_REPLY_HINT, MSG_BRAINSTORM_REPLY_HINT_LONG, MSG_BRAINSTORM_RESUME, MSG_SESSION_ALREADY_ACTIVE
- **Status:** complete

### Phase 4: Add tests for new button handlers
- [x] Create `src/telegram_bot/tests/test_bot.py` with test utilities — `make_callback_update(chat_id, data)` and `make_context()` helpers
- [x] Add tests for `handle_input_cancel` callback — 3 tests verify answer, edit, return END
- [x] Add tests for `handle_idea_button` callback — 6 tests verify skip (answer, set idea=None, show_iterations_menu) and cancel (answer, edit, return END) + 2 message constant tests
- [x] Add tests for `handle_brainstorm_hint_button` callback — 11 tests verify `bs:done`/`bs:save` trigger finish logic; `bs:cancel` triggers cancel logic; keyboard helpers tested (4 tests); message constants verified (9 tests)
- [x] Run `python3 -m pytest src/telegram_bot/tests/ -v` — all 226 tests pass
- **Status:** complete

## Findings & Decisions

### Requirements
- All states that accept free text input AND show "/cancel" (or /skip, /done, /save) text must get equivalent inline buttons
- Free text input must continue to work — users can still type their response
- Slash commands (/cancel, /skip, /done, /save) should remain as fallback handlers for backward compatibility, but the text prompts should no longer advertise them
- Button style must use existing Unicode symbols (✗, →, ✓) consistent with project conventions

### Research Findings

**7 conversation states** accept free text input and reference slash commands:

| State | Current Slash Commands | Button Replacement | callback_data |
|-------|----------------------|-------------------|---------------|
| ENTER_NAME | /cancel | `✗ Cancel` button | `input:cancel` |
| ENTER_URL | /cancel | `✗ Cancel` button | `input:cancel` |
| ENTER_PROJECT_NAME | /cancel | `✗ Cancel` button | `input:cancel` |
| ENTER_BRAINSTORM_PROMPT | /cancel | `✗ Cancel` button | `input:cancel` |
| SELECT_ITERATIONS (custom) | /cancel | `✗ Cancel` button | `iter:cancel` (existing) |
| ENTER_IDEA | /cancel, /skip | `→ Skip` + `✗ Cancel` buttons | `idea:skip`, `idea:cancel` |
| BRAINSTORMING | /done, /save, /cancel | `✓ Done` + `✓ Save` + `✗ Cancel` buttons | `bs:done`, `bs:save`, `bs:cancel` |

**Existing pattern to follow:** The `SELECT_ITERATIONS` state already has a `MSG_CANCEL_BTN` inline button with `callback_data="iter:cancel"` in its iteration selection menu (bot.py line 777). The new cancel buttons should follow this same pattern.

**10 message constants** reference slash commands and need text updates:

| Constant | File:Line | Slash Commands Referenced |
|----------|-----------|--------------------------|
| MSG_ENTER_REPO_URL | messages.py:60 | /cancel |
| MSG_ENTER_WORKTREE_NAME | messages.py:70 | /cancel |
| MSG_PLAN_ENTER_IDEA | messages.py:82-83 | /skip, /cancel |
| MSG_BRAINSTORM_HEADER | messages.py:94 | /cancel |
| MSG_BRAINSTORM_RESUME | messages.py:102 | /done, /cancel |
| MSG_BRAINSTORM_REPLY_HINT | messages.py:108 | /done, /cancel |
| MSG_BRAINSTORM_REPLY_HINT_LONG | messages.py:110-112 | /done, /save, /cancel |
| MSG_ENTER_ITERATIONS | messages.py:129 | /cancel |
| MSG_SESSION_ALREADY_ACTIVE | messages.py:217 | /done, /cancel |
| MSG_ENTER_PROJECT_NAME | messages.py:242 | /cancel |

Additionally `MSG_NO_ACTIVE_BRAINSTORM` (messages.py:219) references `/brainstorming` command — this stays unchanged as it's a command instruction, not a button-replaceable prompt.

**Brainstorm hint attachment points** (buttons go as `reply_markup` on these messages):

| Code Location | Message | Keyboard Variant |
|---------------|---------|-----------------|
| bot.py:740-744 | `handle_brainstorm_prompt()` button flow response | short (Done + Cancel) |
| bot.py:949-953 | `start_brainstorming()` command flow response | long (Done + Save + Cancel) |
| bot.py:991-994 | `handle_brainstorm_message()` multi-turn response | short (Done + Cancel) |
| bot.py:477-479 | `resume_brainstorm` action | short (Done + Cancel) |

**No test_bot.py exists** — bot conversation handler layer has zero test coverage. New tests must be created.

**2 new message constants needed:** `MSG_BRAINSTORM_DONE_BTN` and `MSG_BRAINSTORM_SAVE_BTN`. Evaluate reusing `MSG_GITHUB_SKIP_BTN` ("→ Skip") for ENTER_IDEA or create a dedicated `MSG_SKIP_BTN`.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use `callback_data` prefix per state (`input:cancel`, `idea:skip`, `bs:done`) | Consistent with existing patterns (`iter:cancel`, `action:back`), allows state-specific handling |
| Reuse `iter:cancel` for SELECT_ITERATIONS custom input | Already handled by `handle_iterations()` — no new handler needed |
| Keep /cancel, /skip, /done, /save as CommandHandler fallbacks | Backward compatibility — users who type commands still get expected behavior |
| Remove slash command text from messages but keep commands registered | Buttons become primary UX, commands remain as hidden fallback |
| Send buttons via `reply_markup` on the prompt message itself | Each prompt message gets its own keyboard — no separate message needed |
| Create `_cancel_keyboard()` helper to avoid repeated keyboard creation | DRY — 5 states use the same cancel-only keyboard pattern |
| Use single `CallbackQueryHandler` per pattern prefix in each state | Matches existing ConversationHandler state structure |
| `bs:` prefix for brainstorm hint buttons (not `brainstorm:`) | Avoids collision with existing `brainstorm:plan` and `brainstorm:end` patterns used for post-finish action buttons |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| InlineKeyboardMarkup on prompt message gets removed when user sends text (Telegram behavior) | Buttons are one-time use — after user types text, the keyboard disappears naturally which is acceptable |
| BRAINSTORMING state sends multiple messages (thinking, response, hint) | Attach buttons to the hint/response message — the last message sent back to user |
| `handle_brainstorm_message()` sends response without hint text (line 991-994) | Need to append `MSG_BRAINSTORM_REPLY_HINT` text and `reply_markup` to the Claude response message |
| No existing test infrastructure for bot handlers | Create test utilities for mocking Update/Context in a new test_bot.py file |
| `finish_brainstorming()` / `cancel_brainstorming()` expect `update.message` (not callback_query) | New `handle_brainstorm_hint_button` handler must reimplement the logic using `query.edit_message_text()` instead of `update.message.reply_text()`, since button callbacks don't have `update.message` |
| Brainstorm hint keyboards need two variants (short vs long) | Short hint (Done + Cancel) for multi-turn replies; long hint (Done + Save + Cancel) only for first response via `/brainstorming` command |
