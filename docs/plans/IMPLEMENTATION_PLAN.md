# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/20 (0%)

## Goal

Implement the four ROADMAP.md proposals for the Loop system: (P1) task completion summaries with actionable next steps, (P1) live progress notifications during loop execution, (P2) brainstorming session persistence across container restarts, and (P2) loop run summary with post-execution report. These features transform the Telegram bot from a "fire and forget" launcher into a proper feedback loop with real-time visibility and resilient session management.

## Current Phase

Phase 1: Task Completion Summary

## Phases

### Phase 1: Task Completion Summary with Actionable Next Steps (P1)
- [ ] Create `src/telegram_bot/git_utils.py` with functions: `get_commit_hash(project_path: Path) -> str | None` returning current HEAD short hash via `git rev-parse --short HEAD`, `get_diff_stats(project_path: Path, since_commit: str) -> dict` returning `{files_changed: int, insertions: int, deletions: int}` via `git diff --stat --numstat`, `get_recent_commits(project_path: Path, since_commit: str, max_count: int = 5) -> list[str]` returning commit subject lines via `git log --oneline`, `get_plan_progress(project_path: Path) -> tuple[int, int] | None` parsing `docs/plans/IMPLEMENTATION_PLAN.md` checkbox ratio `[x]` vs `[ ]`
- [ ] Add `start_commit: str | None = None` field to `Task` dataclass (`tasks.py:27`, after line 37) to capture HEAD hash when task starts
- [ ] Store `start_commit` in `_start_task_now()` (`tasks.py:146-188`): call `get_commit_hash(project_path)` before the tmux subprocess launch (before line 169), pass result to `Task()` constructor (line 178)
- [ ] Create `_format_completion_summary(task: Task, diff_stats: dict | None, commits: list[str], plan_progress: tuple[int, int] | None) -> str` in `bot.py` that builds a Markdown message with: mode icon (📋/🔨), status emoji (✅ completed / ⚠️ interrupted), iteration count `{completed}/{total}`, duration via `task_manager.get_task_duration(task)`, files changed, lines +/-, commit list (max 5), plan progress percentage
- [ ] Add inline keyboard buttons to completion message: "Podsumowanie zmian" (callback `completion:diff:{project}`, handler calls `get_diff_stats` and shows `git diff --stat`), "Status projektu" (callback `action:back_to_project`, returns to project menu)
- [ ] Update `check_task_completion()` (`bot.py:891-907`): change `for _, next_task in results` to `for completed_task, next_task in results`; when `completed_task` is not None, call `git_utils` functions with `completed_task.start_commit` and `completed_task.project_path`, format via `_format_completion_summary()`, send to `TELEGRAM_CHAT_ID` with `reply_markup` containing action buttons; keep existing queue-start notification logic for `next_task`
- **Status:** pending

### Phase 2: Live Progress Notifications During Loop Execution (P1)
- [ ] Add `last_reported_iteration: int = 0` and `progress_message_id: int | None = None` fields to `Task` dataclass (`tasks.py:27`, after the `start_commit` field added in Phase 1)
- [ ] Create `check_task_progress(context: ContextTypes.DEFAULT_TYPE) -> None` async function in `bot.py`: iterate `task_manager.list_active()`, for each task call `task_manager.get_current_iteration(task)` (reads `loop/logs/.progress` file per `tasks.py:220-226`), compare with `task.last_reported_iteration`; on change: if `progress_message_id` is None send new message and store returned `message.message_id`, else call `context.bot.edit_message_text(chat_id=TELEGRAM_CHAT_ID, message_id=task.progress_message_id, text=...)`; update `task.last_reported_iteration`
- [ ] Register `check_task_progress` as `run_repeating` job (interval=15, first=15) in `create_application()` (`bot.py:971-972`) alongside existing `check_task_completion` job
- [ ] Format progress message: "{mode_icon} *{project}* — Iteracja {current}/{total} ({elapsed})" where elapsed is from `task_manager.get_task_duration(task)`
- [ ] Add crash/stale detection in `check_task_progress`: compute `.progress` file path as `task.project_path / "loop" / "logs" / ".progress"`, check `os.path.getmtime()`, if mtime older than 5 minutes AND `task_manager._is_session_running(task.session_name)` is True, send one-time warning "⚠️ {project} — brak postępu od 5 min" (add `stale_warned: bool = False` field to `Task` to prevent repeated warnings)
- **Status:** pending

### Phase 3: Brainstorming Session Persistence (P2)
- [ ] Create `_sessions_file()` method in `BrainstormManager` returning `Path(PROJECTS_ROOT) / ".brainstorm_sessions.json"` — file survives container restarts because `PROJECTS_ROOT` (`/home/developer/projects`) is a Docker named volume
- [ ] Add `_save_sessions()` method that serializes `self.sessions` dict to JSON: for each `BrainstormSession`, write fields `chat_id`, `project`, `project_path` (as str), `session_id`, `tmux_session`, `initial_prompt`, `started_at` (as ISO string via `.isoformat()`), `status`; write atomically (write to `.tmp` then `os.replace`)
- [ ] Add `_load_sessions()` method: read JSON from `_sessions_file()`, for each entry validate tmux session exists via `tmux has-session -t {tmux_session}` (reuse `_is_session_running()` at line 346), remove stale entries (kill orphaned tmux sessions), restore valid sessions as `BrainstormSession` objects into `self.sessions`
- [ ] Call `_save_sessions()` at end of `start()` (after line 535), `respond()` (after line 591), `finish()` (after line 647), and `cancel()` (after line 658) in `BrainstormManager`
- [ ] Call `_load_sessions()` in `BrainstormManager.__init__()` (`tasks.py:335-336`) after `self.sessions = {}` initialization
- [ ] Add "Wznów sesję" button in `show_project_menu()` (`bot.py:163-233`): check if any session in `brainstorm_manager.sessions.values()` has matching `project` name, if so show button with callback `action:resume_brainstorm`; add handler in `handle_action()` (`bot.py:236-334`) that calls `brainstorm_manager.respond()` with a resume prompt
- **Status:** pending

### Phase 4: Loop Run Summary with Post-Execution Report (P2)
- [ ] Create `src/lib/summary.js` module with `generateSummary(logDir)` function: find latest `.jsonl` file in `logDir` via `fs.readdirSync` + sort by mtime, parse line-by-line via `readline.createInterface` + `fs.createReadStream`, extract: tool use counts by tool name (from JSON entries where `message.content[].type === "tool_use"`), total input/output tokens (from entries with `type === "result"` containing `usage` field), files modified (from Edit/Write tool `input.file_path` arguments), test results (from Bash tool output containing "PASS"/"FAIL"/"test" patterns)
- [ ] Add `loop summary` subcommand in `cli.js` (`src/bin/cli.js`): import `generateSummary` from `../lib/summary`, add command with `.description('Show summary of last loop run')` and optional `--log-dir` option (default `./loop/logs`), call `generateSummary()` and print formatted report to stdout with sections: Tool Usage, Files Modified, Test Results, Token Usage
- [ ] Integrate summary into `loop.sh` cleanup trap (`src/scripts/loop.sh:22-36`): after `notify-telegram.sh` call (line 31), add `node -e "require('/opt/loop/lib/summary').generateSummary('$LOG_DIR')" > "$LOG_DIR/summary-latest.txt" 2>/dev/null || true` to generate summary file on each run completion
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
| How to prevent repeated stale warnings? | Add `stale_warned: bool` field to `Task` dataclass, set True after first warning |
| How to coordinate dual notification paths? | `notify-telegram.sh` sends basic metrics for CLI-only use; `check_task_completion()` sends rich summary with buttons for bot-initiated tasks; both paths coexist independently |

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
- Detect stale progress (>5 min without change) and warn once
- Track `last_reported_iteration`, `progress_message_id`, and `stale_warned` per task

**P2 - Brainstorming Persistence:**
- Serialize session metadata to JSON file in `PROJECTS_ROOT`
- Restore sessions on bot startup, validate tmux sessions exist
- Support "Resume" button in project menu
- Handle orphaned tmux sessions gracefully (kill and remove from JSON)
- Atomic file writes (write to `.tmp` then `os.replace`) to prevent corruption

**P2 - Loop Run Summary:**
- Parse JSONL log files for tool usage metrics and token counts
- Extract test results from Bash tool output
- Create `loop summary` CLI command
- Auto-generate summary on loop completion via cleanup trap

### Research Findings

- **No tests exist** in the codebase. This is a configuration-first repository with no test framework configured. ROADMAP doesn't specify adding tests, so this plan does not include test tasks.
- **No TODO/FIXME/placeholder code** found anywhere in `src/`. All existing functions are fully implemented.
- **No `docs/specs/` directory** exists. All requirements come from ROADMAP.md proposals.
- **Existing infrastructure**: `.progress` file is already written by `loop.sh` (line 233: `echo "$i" > "$LOG_DIR/.progress"`) and read by `tasks.py:get_current_iteration()` (line 220) but only on-demand when UI renders project menu. The 30-second `check_task_completion()` job (bot.py:891) only detects completion and starts queued tasks — it does not track progress or send completion details.
- **Completion notification gap**: `check_task_completion()` (bot.py:891-907) iterates `process_completed_tasks()` results as `for _, next_task in results` — the completed task (`_`) is discarded. Only queue-start messages are sent. No completion summary is ever generated.
- **`notify-telegram.sh`** sends basic metrics (mode, iterations, duration, status) via Telegram API directly (curl). This is the shell-level notification — separate from bot.py's job-based checking. Both paths coexist: shell for CLI-only usage, bot for rich summaries with inline buttons.
- **`BrainstormManager.sessions`** (`tasks.py:336`) is an in-memory dict keyed by `chat_id`. `session_id` from Claude CLI `--resume` is tracked per turn but never persisted to disk. Container restart = all sessions lost.
- **No `loop summary` command** exists in `cli.js`. JSONL logs are written by `loop.sh` (line 235: `tee -a "$LOG_FILE"`) but never parsed or analyzed programmatically.
- **`Task` dataclass** (`tasks.py:26-37`) has 8 fields: `project`, `project_path`, `mode`, `iterations`, `idea`, `session_name`, `started_at`, `status`. Missing: `start_commit`, `last_reported_iteration`, `progress_message_id`, `stale_warned` — all needed for Phase 1-2.
- **`_start_task_now()`** (`tasks.py:146-188`) creates Task and stores in `active_tasks` but captures no git state before launch.
- **`process_completed_tasks()`** (`tasks.py:270-319`) returns `list[tuple[Task | None, Task | None]]` — the completed task is the first element but is currently discarded by `bot.py:895`.
- **`get_current_iteration()`** (`tasks.py:220-226`) reads `.progress` from `task.project_path / "loop" / "logs" / ".progress"` — reusable directly by progress polling job.
- **`create_application()`** (`bot.py:910-980`) registers one `run_repeating` job at line 972. Adding a second job for progress polling follows the same pattern.
- **Code quality**: Minor inconsistencies (missing type hints in `bot.py` helper functions, `run.py` uses `print()` instead of `logger`). These are not in ROADMAP scope.
- **CLI structure**: `cli.js` uses Commander with `addLoopOptions()`/`addBuildOptions()` helpers. Adding `loop summary` follows the existing pattern at lines 57-65 (standalone command without loop options).

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Create `git_utils.py` as separate module | Keeps git operations isolated from bot handlers; reusable by both completion summary and run summary |
| Include `get_plan_progress()` in `git_utils.py` | Plan progress parsing is needed by completion summary; co-locating with other git/project analysis utilities keeps it discoverable |
| Store `start_commit` on Task dataclass | Minimal change; enables accurate diff calculation between task start and end |
| Use message editing for progress updates | Telegram API `edit_message_text` avoids notification spam during long runs |
| Store `progress_message_id` on Task | Needed for `edit_message_text` — Telegram requires `message_id` to edit |
| Add `stale_warned` flag to Task | Prevents repeated stale-progress warnings for the same task |
| Persist brainstorm sessions as JSON file | Simple, no external dependencies; JSON is human-readable for debugging |
| Atomic file writes for session persistence | Write to `.tmp` then `os.replace` prevents corruption from crashes during write |
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
| `.progress` file path depends on project_path | Already handled by `get_current_iteration()` in `tasks.py:220-226`; progress job reuses same logic |

### Resources
- Telegram Bot API: `editMessageText` for progress updates, `InlineKeyboardMarkup` for action buttons
- Claude CLI: `--resume <session_id>` for brainstorm continuation
- Git commands: `git rev-parse --short HEAD`, `git diff --stat {commit}..HEAD`, `git log --oneline {commit}..HEAD`
- Node.js: `readline` + `createReadStream` for JSONL parsing line-by-line
- Key files to modify: `tasks.py` (Task dataclass, _start_task_now), `bot.py` (check_task_completion, create_application, show_project_menu), `cli.js` (summary subcommand), `loop.sh` (cleanup trap)
- Key files to create: `src/telegram_bot/git_utils.py`, `src/lib/summary.js`
