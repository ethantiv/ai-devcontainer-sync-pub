# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/18 (0%)
**Last updated:** 2026-02-08

## Goal

Add natural conversation continuation with context-aware inline buttons throughout the Telegram bot. After every operation (task start, cancel, help, brainstorm end, etc.) the user should see relevant follow-up buttons instead of dead-end text messages. This eliminates the need to manually invoke `/start` between operations.

From ROADMAP.md:
> dodaj w telegram bot taką naturalną kontynuację pomiędzy kolejnymi wiadmościami np po planie powinien się pojawić przycisk build i powrót do listy projektów, bo dodaniu zadania do kolejki też powinny się wyświetlić jakieś przyciski np przyciski związane z projektem gdzie jest kolejka albo lista projektów, ma być zachowany natrutrany flow w oknie rozmowy , żebym nie musiał cały czas wywoływać polecenia /start w trakcie pracy z agentem za pośrednictwem bota

## Current Phase

Phase 1

## Phases

### Phase 1: Add follow-up buttons after task start/queue
- [ ] Add `MSG_PROJECTS_LIST_BTN` constant in messages.py (e.g. `"\u2261 Projects"`) — for "go to project list" navigation; reuse existing `MSG_PROJECT_BTN` (`"\u25b8 Project"`) for "view current project" navigation (no new constant needed)
- [ ] In `start_task()` (bot.py line 926): replace plain `reply_text` with `reply_text(..., reply_markup=keyboard)` containing context-aware buttons:
  - When task **started**: "View Project" button (`project:{project.name}`) + "Projects" button (`action:back`)
  - When task **queued**: "Queue" button (`action:queue`) + "View Project" button (`project:{project.name}`) + "Projects" button (`action:back`)
  - When task **failed**: "View Project" button (`project:{project.name}`) + "Projects" button (`action:back`)
- [ ] Change `start_task()` return from `ConversationHandler.END` to `State.SELECT_PROJECT` so button callbacks stay routed within the conversation
- **Status:** pending

### Phase 2: Add follow-up buttons after cancel/end operations
- [ ] In `cancel_brainstorming()` (bot.py line 1131/1133): add inline keyboard with "View Project" + "Projects" buttons after cancel/no-active message; return `State.SELECT_PROJECT` instead of `END`
- [ ] In `handle_input_cancel()` (bot.py line 1144): change `edit_message_text(MSG_CANCELLED)` to include inline keyboard with "Projects" button (`action:back`); return `State.SELECT_PROJECT` instead of `END`
- [ ] In `cancel()` (bot.py line 1211): add inline keyboard with "Projects" button after cancel message; return `State.SELECT_PROJECT` instead of `END`
- [ ] In `handle_idea_button()` idea:cancel path (bot.py line 1162): add inline keyboard with "View Project" + "Projects" buttons; return `State.SELECT_PROJECT` instead of `END`
- [ ] In `handle_brainstorm_action()` `brainstorm:end` path (bot.py line 1118): add inline keyboard with "View Project" + "Projects" buttons; return `State.SELECT_PROJECT` instead of `END`
- [ ] In `handle_brainstorm_action()` `brainstorm:plan` no-project path (bot.py line 1103): add inline keyboard with "Projects" button; return `State.SELECT_PROJECT` instead of `END`
- **Status:** pending

### Phase 3: Add follow-up buttons to help and notification messages
- [ ] In `help_command()` (bot.py line 1222): add inline keyboard with "Projects" button after help text
- [ ] In orphaned queue start message (bot.py line 1334): add `reply_markup` with "View Project" button (`project:{project}`) to `send_message()` call
- **Status:** pending

### Phase 4: Add tests for follow-up buttons
- [ ] Add tests for `start_task()` verifying: reply_markup present with correct buttons for started, queued, and failed cases
- [ ] Add tests for `cancel_brainstorming()` verifying: reply_markup present after cancel, returns SELECT_PROJECT
- [ ] Add tests for `handle_input_cancel()` verifying: reply_markup in edited message, returns SELECT_PROJECT
- [ ] Add tests for `cancel()` verifying: reply_markup present, returns SELECT_PROJECT
- [ ] Add tests for `handle_brainstorm_action()` end/no-project paths verifying: reply_markup present, returns SELECT_PROJECT
- [ ] Add tests for orphaned queue start verifying: reply_markup in send_message call
- [ ] Run `python3 -m pytest src/telegram_bot/tests/ -v` — all tests pass
- **Status:** pending

## Findings & Decisions

### Requirements
- Every bot response that ends a conversation (`ConversationHandler.END`) should include at least one navigation button
- Buttons should be context-aware: show "View Project" when a project is selected, show "Projects" to go to project list
- Background notification messages (orphaned queue start) should include navigation buttons
- Existing button patterns (callback_data namespaces: `project:`, `action:`) must be reused
- `/help` remains stateless (returns `None`, not a conversation state) but should still offer a "Projects" button

### Research Findings

#### Dead-end locations identified in bot.py (no follow-up buttons):
| Location | Line | Current behavior | Fix |
|----------|------|------------------|-----|
| `start_task()` | 926 | `reply_text(text)` → END | Add project/queue/projects buttons |
| `cancel_brainstorming()` | 1131 | `reply_text(MSG_BRAINSTORM_CANCELLED)` → END | Add project/projects buttons |
| `handle_input_cancel()` | 1144 | `edit_message_text(MSG_CANCELLED)` → END | Add projects button |
| `cancel()` | 1211 | `reply_text(MSG_CANCELLED)` → END | Add projects button |
| `handle_idea_button()` idea:cancel | 1162 | `edit_message_text(MSG_CANCELLED)` → END | Add project/projects buttons |
| `handle_brainstorm_action()` end | 1118 | `edit_message_text(MSG_BRAINSTORM_SESSION_ENDED)` → END | Add project/projects buttons |
| `handle_brainstorm_action()` no project | 1103 | `edit_message_text(MSG_NO_PROJECT_SELECTED)` → END | Add projects button |
| `help_command()` | 1222 | `reply_text(MSG_HELP)` → None | Add projects button |
| Orphaned queue start | 1334 | `send_message(text)` — no markup | Add project button |

#### Well-covered locations (already have buttons):
- `show_projects()` — project list + create/clone buttons
- `show_project_menu()` — full action menu
- `show_queue()` — cancel buttons + back
- `show_iterations_menu()` — iteration buttons + cancel
- `check_task_completion()` — diff summary + project buttons
- All brainstorm states — done/save/cancel buttons
- `finish_brainstorming()` — Run Plan / End buttons

#### Locations that appear dead-end but are not:
- `handle_github_choice()` line 725: sends plain text BUT immediately follows with `show_project_menu()` on line 730 — not a dead-end
- `handle_name()` / `handle_clone_url()`: on success call `start()` which shows projects — not a dead-end

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Reuse existing `project:` and `action:` callback namespaces | Existing handlers already process these callbacks; no new handler registration needed |
| Return `State.SELECT_PROJECT` instead of `END` from cancel handlers | Keeps button callbacks routed within the ConversationHandler; `SELECT_PROJECT` already handles both `project:` and `action:` callbacks |
| Keep `help_command()` stateless (return None) | Help is a fallback handler; adding reply_markup is sufficient for navigation without changing state management |
| Add `MSG_PROJECTS_LIST_BTN` as a new constant | Distinct from `MSG_BACK_BTN` ("← Back") — "Projects" better communicates the destination when not in a sub-menu |
| Reuse existing `MSG_PROJECT_BTN` for "View Project" instead of adding `MSG_VIEW_PROJECT_BTN` | Already defined as `"\u25b8 Project"` with the right icon; avoid duplicate constants |
| Add buttons to orphaned queue start but NOT to progress messages | Progress messages use edit-in-place pattern (1 create + N edits); adding buttons would add clutter to frequently-updated messages. Orphaned queue start is a one-time message that benefits from navigation. |
