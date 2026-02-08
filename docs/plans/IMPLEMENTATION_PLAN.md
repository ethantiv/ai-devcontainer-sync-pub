# Implementation Plan

**Status:** COMPLETE
**Progress:** 20/20 (100%)
**Last updated:** 2026-02-08

## Goal

Add natural conversation continuation with context-aware inline buttons throughout the Telegram bot. After every operation (task start, cancel, help, brainstorm end, etc.) the user should see relevant follow-up buttons instead of dead-end text messages. This eliminates the need to manually invoke `/start` between operations.

From ROADMAP.md:
> dodaj w telegram bot taką naturalną kontynuację pomiędzy kolejnymi wiadmościami np po planie powinien się pojawić przycisk build i powrót do listy projektów, bo dodaniu zadania do kolejki też powinny się wyświetlić jakieś przyciski np przyciski związane z projektem gdzie jest kolejka albo lista projektów, ma być zachowany natrutrany flow w oknie rozmowy , żebym nie musiał cały czas wywoływać polecenia /start w trakcie pracy z agentem za pośrednictwem bota

## Phases

### Phase 1: Add follow-up buttons after task start/queue
- [x] Add `MSG_PROJECTS_LIST_BTN` constant in messages.py (`"\u2261 Projects"`)
- [x] In `start_task()`: replace plain `reply_text` with `reply_text(..., reply_markup=keyboard)` containing context-aware buttons (started/queued/failed)
- [x] Change `start_task()` return from `ConversationHandler.END` to `State.SELECT_PROJECT`
- **Status:** complete

### Phase 2: Add follow-up buttons after cancel/end operations
- [x] In `cancel_brainstorming()`: add inline keyboard with "View Project" + "Projects" buttons; return `State.SELECT_PROJECT`
- [x] In `handle_input_cancel()`: add inline keyboard with "Projects" button; return `State.SELECT_PROJECT`
- [x] In `cancel()`: add inline keyboard with "Projects" button; return `State.SELECT_PROJECT`
- [x] In `handle_idea_button()` idea:cancel path: add "View Project" + "Projects" buttons; return `State.SELECT_PROJECT`
- [x] In `handle_brainstorm_hint_button()` bs:cancel path: add "View Project" + "Projects" buttons; return `State.SELECT_PROJECT`
- [x] In `handle_brainstorm_action()` `brainstorm:end` path: add "View Project" + "Projects" buttons; return `State.SELECT_PROJECT`
- [x] In `handle_brainstorm_action()` `brainstorm:plan` no-project path: add "Projects" button; return `State.SELECT_PROJECT`
- **Status:** complete

### Phase 3: Add follow-up buttons to help and notification messages
- [x] In `help_command()`: add inline keyboard with "Projects" button after help text
- [x] In orphaned queue start message: add `reply_markup` with "View Project" + "Projects" buttons
- **Status:** complete

### Phase 4: Add tests for follow-up buttons
- [x] Add tests for `start_task()` — reply_markup with correct buttons for started, queued, failed; returns `State.SELECT_PROJECT`
- [x] Add tests for `cancel_brainstorming()` — reply_markup present, returns `State.SELECT_PROJECT`
- [x] Add tests for `handle_input_cancel()` — reply_markup in edited message, returns `State.SELECT_PROJECT`
- [x] Add tests for `cancel()` — reply_markup present, returns `State.SELECT_PROJECT`
- [x] Add tests for `handle_brainstorm_hint_button()` bs:cancel — reply_markup present, returns `State.SELECT_PROJECT`
- [x] Add tests for `handle_brainstorm_action()` end/no-project paths — reply_markup present, returns `State.SELECT_PROJECT`
- [x] Add tests for orphaned queue start — reply_markup in send_message call
- [x] Update 3 existing tests from `ConversationHandler.END` to `State.SELECT_PROJECT`
- [x] All 259 tests pass (`python3 -m pytest src/telegram_bot/tests/ -v`)
- **Status:** complete

## Implementation Summary

### What was added
- `MSG_PROJECTS_LIST_BTN` constant in `messages.py` — `"\u2261 Projects"` for navigating to project list
- `_nav_keyboard(project_name=None)` helper in `bot.py` — reusable navigation keyboard builder that includes optional "View Project" and always-present "Projects" buttons
- 21 new tests (79 total in test_bot.py, 259 across all test files)

### What was changed
- 10 dead-end locations in bot.py now include follow-up navigation buttons
- 7 cancel/end handlers return `State.SELECT_PROJECT` instead of `ConversationHandler.END`
- 3 existing tests updated to assert `State.SELECT_PROJECT`

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Reuse existing `project:` and `action:` callback namespaces | Existing handlers already process these callbacks; no new handler registration needed |
| Return `State.SELECT_PROJECT` instead of `END` from cancel handlers | Keeps button callbacks routed within the ConversationHandler; `SELECT_PROJECT` already handles both `project:` and `action:` callbacks |
| Keep `help_command()` stateless (return None) | Help is a fallback handler; adding reply_markup is sufficient for navigation without changing state management |
| Add `_nav_keyboard()` helper | DRY — reused across 10 locations instead of duplicating keyboard construction |
| Add buttons to orphaned queue start but NOT to progress messages | Progress messages use edit-in-place pattern; buttons would add clutter to frequently-updated messages |
