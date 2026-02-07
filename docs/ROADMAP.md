# Roadmap

## Proposals

### P1 - Critical

#### Full English localization of Telegram bot and application
The Telegram bot UI is entirely in Polish — button labels ("Klonuj repo", "Nowy worktree", "Powrot"), status messages ("W toku", "Wolny", "w kolejce"), error messages ("Brak wybranego projektu"), brainstorming flow ("Claude mysli...", "Zapisuje IDEA..."), help text, and completion summaries. The `notify-telegram.sh` script also has Polish status texts ("Sukces", "Ukonczono iteracje", "Przerwane"). This limits the project to Polish-speaking users and makes error string matching fragile (e.g. `_is_brainstorm_error()` checks for Polish substrings). Translate all user-facing strings in `bot.py`, `tasks.py`, `projects.py`, `notify-telegram.sh`, and `COMMANDS.md` to English. Extract strings to a central location for maintainability.

#### Startup validation for required environment variables
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` default to empty string and 0 respectively, causing silent runtime failures later. Add validation at bot startup that exits with clear error messages when required variables are missing or invalid. Also validate `PROJECTS_ROOT` is writable and Claude CLI is accessible.

### P2 - Important

#### Unit tests for Telegram bot and summary parser
The Telegram bot (`bot.py` 1,200 LOC, `tasks.py` 735 LOC) and summary parser (`summary.js` 192 LOC) have zero test coverage. Add pytest tests for `git_utils.py` (diff/commit parsing), `projects.py` (worktree detection, project listing), `tasks.py` (queue management, session serialization), and Jest tests for `summary.js` (JSONL parsing, tool usage counting, test result detection). Focus on unit tests for pure functions first.

#### Move brainstorm temp files from /tmp to PROJECTS_ROOT
`BrainstormManager` writes Claude output files to `/tmp` (line 345: `TMP_DIR = Path("/tmp")`). These files are lost on system reboot and could cause data loss for in-progress brainstorming sessions. Move output files to `PROJECTS_ROOT/.brainstorm/` to keep them alongside session metadata and survive container restarts.

### P3 - Nice to Have

#### Configurable timeouts and thresholds via environment variables
Several values are hardcoded: stale detection threshold (300s), brainstorm poll interval (0.5s), brainstorm timeout (300s), git diff range (HEAD~5..HEAD). On slow systems like Raspberry Pi, the 5-minute stale threshold may fire during normal long iterations. Extract these to environment variables with sensible defaults so operators can tune behavior without code changes.

#### Task state persistence across container restarts
`TaskManager.active_tasks` dict lives only in memory. If the container restarts while a task is running, the queue and active task state are lost. Orphaned tmux sessions may continue running without bot tracking. Persist task state to disk (similar to brainstorm sessions) and reconcile with running tmux sessions on startup.
