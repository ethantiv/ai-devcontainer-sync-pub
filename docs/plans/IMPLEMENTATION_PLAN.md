# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/20 (0%)

## Goal

Implement the four ROADMAP.md proposals for the Loop system: (P1) task completion summaries with actionable next steps, (P1) live progress notifications during loop execution, (P2) brainstorming session persistence across container restarts, and (P2) loop run summary with post-execution report. These features transform the Telegram bot from a "fire and forget" launcher into a proper feedback loop with real-time visibility and resilient session management.

## Current Phase

Phase 1: Task Completion Summary

## Phases

### Phase 1: Task Completion Summary with Actionable Next Steps (P1)
- [ ] Create `src/telegram_bot/git_utils.py` with functions: `get_diff_stats(project_path, since_commit)` returning files changed / lines added / deleted, `get_recent_commits(project_path, since_commit)` returning list of commit messages, `get_commit_hash(project_path)` returning current HEAD hash
- [ ] Extend `Task` dataclass in `tasks.py` with `start_commit: str | None` field to capture HEAD hash when task starts
- [ ] Store `start_commit` in `_start_task_now()` by calling `get_commit_hash()` before launching tmux session
- [ ] Create `_format_completion_summary(task, diff_stats, commits)` in `bot.py` that builds a Markdown message with: mode icon, status, iteration count, duration, files changed, lines +/-, commit list (max 5), plan progress percentage (parsed from IMPLEMENTATION_PLAN.md)
- [ ] Add inline keyboard buttons to completion message: "Podsumowanie zmian" (shows `git diff --stat`), "Status projektu" (returns to project menu)
- [ ] Update `check_task_completion()` in `bot.py` to call `git_utils` functions and send detailed completion message instead of minimal notification
- **Status:** pending

### Phase 2: Live Progress Notifications During Loop Execution (P1)
- [ ] Add `last_reported_iteration: int` field to `Task` dataclass in `tasks.py`
- [ ] Create `check_task_progress()` async function in `bot.py` that polls `.progress` file for each active task, detects iteration changes, and sends Telegram update
- [ ] Register `check_task_progress` as a separate `run_repeating` job (interval=15s) in `create_application()`
- [ ] Format progress message: "{mode_icon} {project} - Iteracja {current}/{total} ({elapsed})" with edit of previous progress message (avoid spam)
- [ ] Add crash/stale detection: if `.progress` file unchanged for >5 minutes and tmux session still active, send warning notification
- **Status:** pending

### Phase 3: Brainstorming Session Persistence (P2)
- [ ] Create `_sessions_file()` method in `BrainstormManager` returning `Path(PROJECTS_ROOT) / ".brainstorm_sessions.json"`
- [ ] Add `_save_sessions()` method that serializes active sessions dict to JSON (fields: chat_id, project, project_path, session_id, tmux_session, initial_prompt, started_at, status)
- [ ] Add `_load_sessions()` method that deserializes sessions from JSON on startup, validates tmux sessions still exist, removes stale entries
- [ ] Call `_save_sessions()` after `start()`, `respond()`, `finish()`, and `cancel()` in `BrainstormManager`
- [ ] Call `_load_sessions()` in `BrainstormManager.__init__()` to restore sessions on bot restart
- [ ] Add "Wznow sesje" button in project menu (visible when saved session exists for project) that calls `respond()` with restored session
- **Status:** pending

### Phase 4: Loop Run Summary with Post-Execution Report (P2)
- [ ] Create `src/lib/summary.js` module with `generateSummary(logDir)` function that parses latest JSONL log, extracts: tool use counts by type, total tokens used, files modified (from Edit/Write tool calls), test results (from Bash output containing "test"/"PASS"/"FAIL")
- [ ] Add `loop summary` subcommand in `cli.js` that calls `generateSummary()` and prints human-readable report to stdout
- [ ] Integrate summary generation into `loop.sh` cleanup trap: after notify-telegram.sh, call summary and write to `loop/logs/summary-latest.txt`
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should completion summary include full git diff or just stats? | Just `--stat` (files + lines); full diff via button on demand |
| Should progress notifications edit previous message or send new? | Edit previous to avoid notification spam |
| Where to store brainstorm session persistence file? | `PROJECTS_ROOT/.brainstorm_sessions.json` (survives container restarts if volume-mounted) |
| Should `loop summary` parse JSONL or rely on git? | Both: JSONL for tool/token metrics, git for commit/diff stats |
| How to detect stale/crashed tasks? | Check if `.progress` file timestamp unchanged >5min while tmux session alive |

## Findings & Decisions

### Requirements

**P1 - Task Completion Summary:**
- Parse git diff stats (files changed, lines +/-) between task start and end commits
- Count and list commits created during the run (max 5 shown)
- Parse IMPLEMENTATION_PLAN.md for plan progress percentage
- Display inline buttons for detailed views
- Must work with both plan and build modes

**P1 - Live Progress Notifications:**
- Poll `.progress` file every 15 seconds for active tasks
- Edit existing Telegram message (not new messages) to avoid spam
- Detect stale progress (>5 min without change) and warn
- Track `last_reported_iteration` per task

**P2 - Brainstorming Persistence:**
- Serialize session metadata to JSON file in `PROJECTS_ROOT`
- Restore sessions on bot startup, validate tmux sessions exist
- Support "Resume" button in project menu
- Handle orphaned tmux sessions gracefully

**P2 - Loop Run Summary:**
- Parse JSONL log files for tool usage metrics
- Extract test results from Bash tool output
- Create `loop summary` CLI command
- Auto-generate summary on loop completion

### Research Findings

- **No tests exist** in the codebase. This is a configuration-first repository with no test framework configured. ROADMAP doesn't specify adding tests, so this plan does not include test tasks.
- **No TODO/FIXME/placeholder code** found anywhere in `src/`. All existing functions are fully implemented.
- **Existing infrastructure**: `.progress` file is already written by `loop.sh` (line 233) and read by `tasks.py:get_current_iteration()` but only on-demand (not polled). The 30-second `check_task_completion()` job only detects completion, not progress.
- **`notify-telegram.sh`** sends basic metrics (mode, iterations, duration, status) but no git info.
- **`BrainstormManager.sessions`** is an in-memory dict keyed by `chat_id`. `session_id` from Claude CLI `--resume` is tracked but never persisted to disk.
- **No `loop summary` command** exists. JSONL logs are written but never parsed/analyzed.
- **Code quality**: Minor inconsistencies found (missing type hints in `bot.py:163,81`, `run.py` uses `print()` instead of `logger`, subprocess error handling varies). These are not in ROADMAP scope and should not be addressed in this plan.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Create `git_utils.py` as separate module | Keeps git operations isolated from bot handlers; reusable by both completion summary and run summary |
| Store `start_commit` on Task dataclass | Minimal change; enables accurate diff calculation between task start and end |
| Use message editing for progress updates | Telegram API `edit_message_text` avoids notification spam during long runs |
| Persist brainstorm sessions as JSON file | Simple, no external dependencies; JSON is human-readable for debugging |
| `loop summary` as Node.js (not shell) | JSONL parsing is complex for bash; Node.js has native JSON support and aligns with existing CLI |
| 15-second polling interval for progress | Balance between responsiveness and API rate limits; iterations typically take minutes |
| Stale detection at 5-minute threshold | Single iteration can take 2-3 minutes; 5 min avoids false positives |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| No test framework to validate changes | ROADMAP doesn't require tests; rely on manual testing via Telegram bot and `loop` CLI |
| Brainstorm sessions use ephemeral tmux names | Persist tmux session name in JSON; validate on load with `tmux has-session` |

### Resources
- Telegram Bot API: `editMessageText` for progress updates, `InlineKeyboardMarkup` for action buttons
- Claude CLI: `--resume <session_id>` for brainstorm continuation
- Git commands: `git diff --stat HEAD~N..HEAD`, `git log --oneline`
- Node.js: `readline` for JSONL parsing line-by-line
