# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/12 (0%)
**Last updated:** 2026-02-08

## Goal

Reduce and consolidate Telegram bot notification messages between task completion and queue start. Currently the user receives 3-4 separate messages in rapid succession (completion summary from notify-telegram.sh, rich completion summary from bot.py, "Started from queue" message, and iteration progress message). Consolidate into minimal, unified messages.

From ROADMAP.md:
> zmniejsz ilość ekranów z podumowaniami, informacjami o zakończniu pracy i starcie kolejki do niezbędnego minimum, teraz między kolejnymi zadaniami z kolejki otrzymuję równolegle 3-4 wiadomości z podsumowanie, inforamcją o zakończniu i starcie nowego, zmniejsz ilość i ujednolić format tych wiadmości

## Current Phase

Phase 1: Remove duplicate notification from notify-telegram.sh

## Phases

### Phase 1: Remove duplicate notification from notify-telegram.sh
- [ ] Remove `notify-telegram.sh` call from `loop.sh` cleanup trap (loop.sh line 30-35) — bot.py's `check_task_completion()` already sends a richer summary with diff stats, commits, plan progress, and interactive buttons
- [ ] Keep `notify-telegram.sh` file for potential standalone use but stop calling it from the cleanup trap
- [ ] Update loop.sh cleanup function: remove the 6 lines calling notify-telegram.sh (lines 30-35)
- **Status:** pending

### Phase 2: Consolidate completion summary + queue start into single message
- [ ] Merge "Started from queue" info into the completion summary message — append queue start line to `_format_completion_summary()` output instead of sending a separate `send_message()` call (bot.py lines 1310-1322)
- [ ] Add new message constant `MSG_COMPLETION_QUEUE_NEXT` in messages.py for the "next task started" line within the completion message
- [ ] Update `check_task_completion()` (bot.py line 1261-1323): when both `completed_task` and `next_task` exist, include queue start info in the summary message instead of a second `send_message()`
- [ ] When only `next_task` exists (orphaned queue start, no completed task), keep sending a standalone message
- **Status:** pending

### Phase 3: Add tests for consolidated notifications
- [ ] Add tests for `_format_completion_summary()` verifying: basic output, with diff stats, with commits, with plan progress, and with queue next task appended
- [ ] Add tests for `check_task_completion()` verifying: single message sent when task completes with queued next (not two), standalone message for orphaned queue start, no message when no tasks completed
- [ ] Add test verifying `notify-telegram.sh` is no longer called from loop.sh cleanup trap
- [ ] Run `python3 -m pytest src/telegram_bot/tests/ -v` — all tests pass
- **Status:** pending

## Findings & Decisions

### Requirements
- Reduce the number of separate Telegram messages between task completion and next queue task start from 3-4 to 1-2
- Preserve all useful information (diff stats, commits, plan progress, interactive buttons)
- Maintain the unified visual style (mode icons ◇/■, markdown formatting)
- Keep the iteration progress message as-is (already uses edit-in-place pattern, sends only 1 new message + edits)

### Research Findings

**Current notification flow when a task completes and queue has next task:**

| # | Source | Timing | Message | Type |
|---|--------|--------|---------|------|
| 1 | `notify-telegram.sh` via loop.sh cleanup trap | Immediate on script exit | Basic summary: mode, status, iterations/total, time, project | NEW message |
| 2 | `check_task_completion()` in bot.py (line 1302-1307) | Within 30s (job poll) | Rich summary: iterations, time, diff stats, commits, plan progress + buttons | NEW message |
| 3 | `check_task_completion()` in bot.py (line 1318-1322) | Same job run as #2 | "▶ Started from queue: {project} - {mode} • {iterations} iterations" | NEW message |
| 4 | `check_task_progress()` in bot.py (line 1364-1369) | Within 15s of new task starting | "◇/■ {project} — Iteration 1/N (elapsed)" | NEW message (then edits for subsequent iterations) |

**Result: User sees 4 separate messages within ~30 seconds of a task completing.**

**Problem breakdown:**
- Message #1 (notify-telegram.sh) **duplicates** message #2 (bot.py) — 70% content overlap, bot.py version is strictly richer
- Message #3 (queue start) could be appended to message #2 instead of sent separately
- Message #4 (iteration progress) is already optimized (1 new message, subsequent edits) and should remain as-is

**After consolidation: 2 messages** (1 completion+queue summary, 1 iteration progress)

**Key code locations:**

| File | Lines | Function | Change Needed |
|------|-------|----------|---------------|
| `src/scripts/loop.sh` | 30-35 | `cleanup()` trap | Remove `notify-telegram.sh` call |
| `src/telegram_bot/bot.py` | 1225-1258 | `_format_completion_summary()` | Add optional `next_task` parameter |
| `src/telegram_bot/bot.py` | 1261-1323 | `check_task_completion()` | Merge queue start into summary |
| `src/telegram_bot/messages.py` | 161-164 | `MSG_STARTED_FROM_QUEUE` | Keep for orphaned queue; add `MSG_COMPLETION_QUEUE_NEXT` |

**notify-telegram.sh vs bot.py comparison:**

| Field | notify-telegram.sh | bot.py check_task_completion() |
|-------|-------------------|-------------------------------|
| Mode icon (◇/■) | ✓ | ✓ |
| Project name | ✓ | ✓ |
| Mode (plan/build) | ✓ | ✓ (in title) |
| Status (success/completed/interrupted) | ✓ | ✗ (always "completed") |
| Iterations | ✓ (completed/total) | ✓ (just total) |
| Duration | ✓ | ✓ |
| Diff stats (files, +/- lines) | ✗ | ✓ |
| Recent commits | ✗ | ✓ |
| Plan progress | ✗ | ✓ |
| Interactive buttons | ✗ | ✓ |

**Conclusion:** bot.py's notification is strictly superior. The only field lost is "Status" (success/completed/interrupted distinction), but this is low-value since the bot always treats task end as completion.

**Coordination between paths:** Zero. No deduplication flag, no shared state, no timing guarantee. Both paths always fire independently when bot is running.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Remove `notify-telegram.sh` from loop.sh cleanup trap instead of disabling bot notification | Bot's notification is richer (diffs, commits, plan, buttons); removing the shell notification eliminates ~70% duplication with zero information loss |
| Keep `notify-telegram.sh` file intact (just stop calling it) | May be useful for standalone loop runs without bot; avoids breaking `loop init` symlinks |
| Merge queue start into completion message (not the reverse) | Completion summary is the primary message; "next task started" is secondary info that fits as an appendix line |
| Keep orphaned queue start as standalone message | When there's no completed task (bot restarted), the queue start notification is the only message — can't merge into nothing |
| Keep iteration progress message (message #4) unchanged | Already optimized with edit-in-place pattern; sends 1 new message + N-1 edits. No consolidation needed |
| Add `MSG_COMPLETION_QUEUE_NEXT` constant instead of reusing `MSG_STARTED_FROM_QUEUE` | Different formatting — inline within summary vs standalone message |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| notify-telegram.sh sends via direct curl to Telegram API; bot.py sends via python-telegram-bot library | Two independent notification paths with zero coordination — solved by removing the shell path |
| Removing notify-telegram.sh call means no immediate notification (bot polls every 30s) | Acceptable trade-off: user waits up to 30s but gets a single, richer notification instead of 2 spammy ones |
| `_format_completion_summary()` currently takes only task data, not queue info | Extend function signature to accept optional `next_task: Task` parameter |
| `MSG_STARTED_FROM_QUEUE` is used both for standalone and merged contexts | Create separate `MSG_COMPLETION_QUEUE_NEXT` for merged context; keep `MSG_STARTED_FROM_QUEUE` for orphaned queue starts |
