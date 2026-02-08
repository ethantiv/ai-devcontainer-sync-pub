# Implementation Plan

**Status:** COMPLETE
**Progress:** 11/11 (100%)
**Last updated:** 2026-02-08

## Goal

Reduce and consolidate Telegram bot notification messages between task completion and queue start. Currently the user receives 3-4 separate messages in rapid succession (completion summary from notify-telegram.sh, rich completion summary from bot.py, "Started from queue" message, and iteration progress message). Consolidate into minimal, unified messages.

From ROADMAP.md:
> zmniejsz ilość ekranów z podumowaniami, informacjami o zakończniu pracy i starcie kolejki do niezbędnego minimum, teraz między kolejnymi zadaniami z kolejki otrzymuję równolegle 3-4 wiadomości z podsumowanie, inforamcją o zakończniu i starcie nowego, zmniejsz ilość i ujednolić format tych wiadmości

## Current Phase

All phases complete.

## Phases

### Phase 1: Remove duplicate notification from notify-telegram.sh
- [x] Remove `notify-telegram.sh` call from `loop.sh` cleanup trap (loop.sh lines 30-35, 6 lines) — bot.py's `check_task_completion()` already sends a richer summary with diff stats, commits, plan progress, and interactive buttons
- [x] Keep `notify-telegram.sh` file intact for potential standalone use; keep `loop init` symlink in `init.js` line 99
- **Status:** complete

### Phase 2: Consolidate completion summary + queue start into single message
- [x] Add new message constant `MSG_COMPLETION_QUEUE_NEXT` in messages.py (after line 164) for the "next task started" line within the completion message
- [x] Add optional `next_task: Task | None = None` parameter to `_format_completion_summary()` (bot.py); when provided, append `MSG_COMPLETION_QUEUE_NEXT` line to the summary output
- [x] Update `check_task_completion()` (bot.py): when both `completed_task` and `next_task` exist, pass `next_task` to `_format_completion_summary()` and skip the second `send_message()` call (changed `if next_task:` to `elif next_task:`)
- [x] When only `next_task` exists (orphaned queue start, no completed task), keep sending standalone `MSG_STARTED_FROM_QUEUE` message
- [x] Add `MSG_COMPLETION_QUEUE_NEXT` import to bot.py imports
- **Status:** complete

### Phase 3: Add tests for consolidated notifications
- [x] Add tests for `_format_completion_summary()` in `test_bot.py` verifying: basic output, with diff stats, with commits, with plan progress, and with `next_task` appended (queue next line present in output)
- [x] Add tests for `check_task_completion()` in `test_bot.py` verifying: single `send_message` call when task completes with queued next (not two), standalone message for orphaned queue start, no message when no tasks completed
- [x] Add test verifying `notify-telegram.sh` is no longer called from `loop.sh` cleanup trap (grep loop.sh for the call)
- [x] Run `python3 -m pytest src/telegram_bot/tests/ -v` — all tests pass
- **Status:** complete

## Findings & Decisions

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Remove `notify-telegram.sh` from loop.sh cleanup trap instead of disabling bot notification | Bot's notification is richer (diffs, commits, plan, buttons); removing the shell notification eliminates ~70% duplication with zero information loss |
| Keep `notify-telegram.sh` file intact (just stop calling it) | May be useful for standalone loop runs without bot; avoids breaking `loop init` symlinks |
| Merge queue start into completion message (not the reverse) | Completion summary is the primary message; "next task started" is secondary info that fits as an appendix line |
| Keep orphaned queue start as standalone message | When there's no completed task (bot restarted), the queue start notification is the only message — can't merge into nothing |
| Keep iteration progress message (message #4) unchanged | Already optimized with edit-in-place pattern; sends 1 new message + N-1 edits. No consolidation needed |
| Add `MSG_COMPLETION_QUEUE_NEXT` constant instead of reusing `MSG_STARTED_FROM_QUEUE` | Different formatting — inline within summary vs standalone message |
