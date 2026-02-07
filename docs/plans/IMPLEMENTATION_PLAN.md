# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/20 (0%)

## Goal

Implement the four ROADMAP.md proposals for the Loop system: (P1) task completion summaries with actionable next steps, (P1) live progress notifications during loop execution, (P2) brainstorming session persistence across container restarts, and (P2) loop run summary with post-execution report. These features transform the Telegram bot from a "fire and forget" launcher into a proper feedback loop with real-time visibility and resilient session management.

## Current Phase

Phase 1: Task Completion Summary

## Phases

### Phase 1: Task Completion Summary with Actionable Next Steps (P1)
- [ ] Create `src/telegram_bot/git_utils.py` with functions: `get_commit_hash(project_path) -> str | None` returning current HEAD short hash via `git rev-parse --short HEAD`, `get_diff_stats(project_path, since_commit) -> dict` returning `{files_changed: int, insertions: int, deletions: int}` via `git diff --stat --numstat`, `get_recent_commits(project_path, since_commit, max_count=5) -> list[str]` returning commit subject lines via `git log --oneline`
- [ ] Add `start_commit: str | None = None` field to `Task` dataclass (`tasks.py:26`) to capture HEAD hash when task starts
- [ ] Store `start_commit` in `_start_task_now()` (`tasks.py:146`) by calling `get_commit_hash(project_path)` before launching tmux session
- [ ] Create `_format_completion_summary(task, diff_stats, commits)` in `bot.py` that builds a Markdown message with: mode icon (📋/🔨), status emoji, iteration count, duration, files changed, lines +/-, commit list (max 5), plan progress percentage (parsed from `docs/plans/IMPLEMENTATION_PLAN.md` checkbox ratio)
- [ ] Add inline keyboard buttons to completion message: "Podsumowanie zmian" (callback `completion:diff:{project}`, shows `git diff --stat`), "Status projektu" (callback `action:back_to_project`, returns to project menu)
- [ ] Update `check_task_completion()` (`bot.py:891`) to use `completed_task` from `process_completed_tasks()` results (currently ignored: `for _, next_task`), call `git_utils` functions with `task.start_commit`, and send detailed completion summary instead of only queue-next notification
- **Status:** pending

### Phase 2: Live Progress Notifications During Loop Execution (P1)
- [ ] Add `last_reported_iteration: int = 0` and `progress_message_id: int | None = None` fields to `Task` dataclass (`tasks.py:26`)
- [ ] Create `check_task_progress()` async function in `bot.py` that iterates `task_manager.list_active()`, calls `get_current_iteration(task)`, compares with `task.last_reported_iteration`, and on change either sends new message (first update) or edits previous via `context.bot.edit_message_text()` using `task.progress_message_id`
- [ ] Register `check_task_progress` as a separate `run_repeating` job (interval=15s, first=15) in `create_application()` (`bot.py:971`) alongside existing `check_task_completion` job
- [ ] Format progress message: "{mode_icon} *{project}* - Iteracja {current}/{total} ({elapsed})" and store returned `message_id` on `task.progress_message_id` for subsequent edits
- [ ] Add crash/stale detection: if `.progress` file mtime unchanged for >5 minutes (via `os.path.getmtime()`) and tmux session still active (`_is_session_running()`), send warning: "⚠️ {project} - brak postępu od 5 min"
- **Status:** pending

### Phase 3: Brainstorming Session Persistence (P2)
- [ ] Create `_sessions_file()` method in `BrainstormManager` returning `Path(PROJECTS_ROOT) / ".brainstorm_sessions.json"`
- [ ] Add `_save_sessions()` method that serializes active sessions dict to JSON (fields: chat_id, project, project_path, session_id, tmux_session, initial_prompt, started_at as ISO string, status)
- [ ] Add `_load_sessions()` method that deserializes sessions from JSON on startup, validates tmux sessions still exist via `tmux has-session`, removes stale entries, and restores valid sessions to `self.sessions` dict
- [ ] Call `_save_sessions()` after `start()`, `respond()`, `finish()`, and `cancel()` in `BrainstormManager` — at end of each method after state changes
- [ ] Call `_load_sessions()` in `BrainstormManager.__init__()` (`tasks.py:335`) to restore sessions on bot restart
- [ ] Add "Wznów sesję" button in `show_project_menu()` (`bot.py`) visible when saved session exists for project (check via `brainstorm_manager.sessions`), that calls `respond()` with restored session context
- **Status:** pending

### Phase 4: Loop Run Summary with Post-Execution Report (P2)
- [ ] Create `src/lib/summary.js` module with `generateSummary(logDir)` function that finds latest `.jsonl` log file, parses line-by-line via `readline`, extracts: tool use counts by type (from `type: "tool_use"` entries), total input/output tokens (from `type: "result"` entry), files modified (from Edit/Write tool `path` arguments), test results (from Bash tool output containing "PASS"/"FAIL"/"test")
- [ ] Add `loop summary` subcommand in `cli.js` (`src/bin/cli.js`) that calls `generateSummary()` and prints human-readable report to stdout with sections: Tool Usage, Files Modified, Test Results, Token Usage
- [ ] Integrate summary generation into `loop.sh` cleanup trap (`src/scripts/loop.sh:22-36`): after `notify-telegram.sh` call, invoke `node -e "require('/opt/loop/lib/summary').generateSummary('$LOG_DIR')"` and write output to `loop/logs/summary-latest.txt`
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should completion summary include full git diff or just stats? | Just `--stat` (files + lines); full diff via button on demand |
| Should progress notifications edit previous message or send new? | Edit previous to avoid notification spam; first iteration sends new message, subsequent edits it |
| Where to store brainstorm session persistence file? | `PROJECTS_ROOT/.brainstorm_sessions.json` (survives container restarts if PROJECTS_ROOT is volume-mounted) |
| Should `loop summary` parse JSONL or rely on git? | Both: JSONL for tool/token metrics, git for commit/diff stats |
| How to detect stale/crashed tasks? | Check `.progress` file mtime via `os.path.getmtime()` — unchanged >5min while tmux session alive triggers warning |
| How to handle completion summary for tasks without start_commit? | Graceful fallback: show only duration/iterations/status when `start_commit` is None |

## Findings & Decisions

### Requirements

**P1 - Task Completion Summary:**
- Parse git diff stats (files changed, lines +/-) between task start and end commits
- Count and list commits created during the run (max 5 shown)
- Parse IMPLEMENTATION_PLAN.md for plan progress percentage (checkbox ratio)
- Display inline buttons for detailed views
- Must work with both plan and build modes
- Graceful degradation when no git changes occurred

**P1 - Live Progress Notifications:**
- Poll `.progress` file every 15 seconds for active tasks
- Edit existing Telegram message (not new messages) to avoid spam
- Detect stale progress (>5 min without change) and warn
- Track `last_reported_iteration` and `progress_message_id` per task

**P2 - Brainstorming Persistence:**
- Serialize session metadata to JSON file in `PROJECTS_ROOT`
- Restore sessions on bot startup, validate tmux sessions exist
- Support "Resume" button in project menu
- Handle orphaned tmux sessions gracefully (kill and remove from JSON)

**P2 - Loop Run Summary:**
- Parse JSONL log files for tool usage metrics and token counts
- Extract test results from Bash tool output
- Create `loop summary` CLI command
- Auto-generate summary on loop completion via cleanup trap

### Research Findings

- **No tests exist** in the codebase. This is a configuration-first repository with no test framework configured. ROADMAP doesn't specify adding tests, so this plan does not include test tasks.
- **No TODO/FIXME/placeholder code** found anywhere in `src/`. All existing functions are fully implemented.
- **Existing infrastructure**: `.progress` file is already written by `loop.sh` (line 233: `echo "$i" > "$LOG_DIR/.progress"`) and read by `tasks.py:get_current_iteration()` (line 220) but only on-demand when UI renders project menu. The 30-second `check_task_completion()` job (bot.py:891) only detects completion and starts queued tasks — it does not track progress or send completion details.
- **Completion notification gap**: `check_task_completion()` (bot.py:891-907) iterates `process_completed_tasks()` results as `for _, next_task in results` — the completed task (`_`) is discarded. Only queue-start messages are sent. No completion summary is ever generated.
- **`notify-telegram.sh`** sends basic metrics (mode, iterations, duration, status) via Telegram API directly (curl). This is the shell-level notification — separate from bot.py's job-based checking. Both paths need to be coordinated to avoid duplicate notifications.
- **`BrainstormManager.sessions`** (`tasks.py:336`) is an in-memory dict keyed by `chat_id`. `session_id` from Claude CLI `--resume` is tracked per turn but never persisted to disk. Container restart = all sessions lost.
- **No `loop summary` command** exists in `cli.js`. JSONL logs are written by `loop.sh` (line 235: `tee -a "$LOG_FILE"`) but never parsed or analyzed programmatically.
- **`Task` dataclass** (`tasks.py:26-37`) has 8 fields: `project`, `project_path`, `mode`, `iterations`, `idea`, `session_name`, `started_at`, `status`. Missing: `start_commit`, `last_reported_iteration`, `progress_message_id` — all needed for Phase 1-2.
- **`_start_task_now()`** (`tasks.py:146-188`) creates Task and stores in `active_tasks` but captures no git state before launch.
- **Code quality**: Minor inconsistencies (missing type hints in `bot.py` helper functions, `run.py` uses `print()` instead of `logger`). These are not in ROADMAP scope.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Create `git_utils.py` as separate module | Keeps git operations isolated from bot handlers; reusable by both completion summary and run summary |
| Store `start_commit` on Task dataclass | Minimal change; enables accurate diff calculation between task start and end |
| Use message editing for progress updates | Telegram API `edit_message_text` avoids notification spam during long runs |
| Store `progress_message_id` on Task | Needed for `edit_message_text` — Telegram requires `message_id` to edit |
| Persist brainstorm sessions as JSON file | Simple, no external dependencies; JSON is human-readable for debugging |
| `loop summary` as Node.js (not shell) | JSONL parsing is complex for bash; Node.js has native JSON support and aligns with existing CLI in `src/lib/` |
| 15-second polling interval for progress | Balance between responsiveness and API rate limits; iterations typically take minutes |
| Stale detection at 5-minute threshold | Single iteration can take 2-3 minutes; 5 min avoids false positives |
| Coordinate `notify-telegram.sh` with bot completion | Shell notification covers non-bot scenarios (manual CLI use); bot summary adds rich formatting and buttons for bot-initiated tasks |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| No test framework to validate changes | ROADMAP doesn't require tests; rely on manual testing via Telegram bot and `loop` CLI |
| Brainstorm sessions use ephemeral tmux names | Persist tmux session name in JSON; validate on load with `tmux has-session` |
| `check_task_completion` discards completed task info | Refactor loop to use both `completed_task` and `next_task` from tuples |
| Dual notification paths (shell + bot) | Shell notification for CLI-only usage; bot notification for bot-initiated tasks with rich formatting |

### Resources
- Telegram Bot API: `editMessageText` for progress updates, `InlineKeyboardMarkup` for action buttons
- Claude CLI: `--resume <session_id>` for brainstorm continuation
- Git commands: `git rev-parse --short HEAD`, `git diff --stat {commit}..HEAD`, `git log --oneline {commit}..HEAD`
- Node.js: `readline` + `createReadStream` for JSONL parsing line-by-line
- Key files to modify: `tasks.py` (Task dataclass, _start_task_now), `bot.py` (check_task_completion, create_application, show_project_menu), `cli.js` (summary subcommand), `loop.sh` (cleanup trap)
