# Roadmap

## Proposals

### P1 - Critical

#### Full English localization of Telegram bot and application
The Telegram bot UI is entirely in Polish — button labels ("Klonuj repo", "Nowy worktree", "Powrot"), status messages ("W toku", "Wolny", "w kolejce"), error messages ("Brak wybranego projektu"), brainstorming flow ("Claude mysli...", "Zapisuje IDEA..."), help text, and completion summaries. The `notify-telegram.sh` script also has Polish status texts ("Sukces", "Ukonczono iteracje", "Przerwane"). This limits the project to Polish-speaking users and makes error string matching fragile (e.g. `_is_brainstorm_error()` checks for Polish substrings). Translate all user-facing strings in `bot.py`, `tasks.py`, `projects.py`, `notify-telegram.sh`, and `COMMANDS.md` to English. Extract strings to a central location for maintainability.

#### Startup validation for required environment variables
`run.py` now checks for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` presence at startup (lines 12-18), but `config.py` still defaults to empty string and 0 respectively, so other code paths can still silently fail. Complete the validation: exit with clear error messages when values are missing or invalid, validate `PROJECTS_ROOT` is an existing writable directory, and verify Claude CLI is accessible in PATH or at `~/.claude/bin/claude`.

### P2 - Important

#### Unit tests for Telegram bot and summary parser
The Telegram bot (`bot.py` 1,197 LOC, `tasks.py` 742 LOC) and summary parser (`summary.js` 192 LOC) have zero test coverage. Add pytest tests for `git_utils.py` (diff/commit parsing), `projects.py` (worktree detection, `.git` file parsing via `_parse_gitdir()`), `tasks.py` (queue management, session serialization, stale detection), and Jest tests for `summary.js` (JSONL parsing, tool usage counting, test result detection). Focus on unit tests for pure functions first.

#### Move brainstorm temp files from /tmp to PROJECTS_ROOT
`BrainstormManager` writes Claude output files to `/tmp` (`TMP_DIR = Path("/tmp")` in tasks.py). These files are lost on system reboot and could cause data loss for in-progress brainstorming sessions. Move output files to `PROJECTS_ROOT/.brainstorm/` to keep them alongside the already-persisted `brainstorm_sessions.json` and survive container restarts.

#### Add subprocess timeouts to git operations in Telegram bot
`projects.py` calls `subprocess.run()` for git commands (clone, worktree add, branch operations) without timeout parameters (lines 87, 120, 154, 181). On slow networks or large repos, these can hang indefinitely, blocking the bot's async event loop. Add `timeout=30` (or configurable) to all subprocess calls in `projects.py` and handle `subprocess.TimeoutExpired` gracefully, similar to the pattern already used in `git_utils.py`.

### P3 - Nice to Have

#### Configurable timeouts and thresholds via environment variables
Several values are hardcoded: stale detection threshold (300s in bot.py), brainstorm poll interval (0.5s in tasks.py), brainstorm timeout (300s in tasks.py), git diff range (HEAD~5..HEAD). On slow systems like Raspberry Pi, the 5-minute stale threshold may fire during normal long iterations. Extract these to environment variables with sensible defaults so operators can tune behavior without code changes.

#### Task state persistence across container restarts
`TaskManager.active_tasks` dict lives only in memory. If the container restarts while a task is running, the queue and active task state are lost. Orphaned tmux sessions may continue running without bot tracking. Persist task state to disk (similar to the existing `brainstorm_sessions.json` pattern using atomic `os.replace()`) and reconcile with running tmux sessions on startup.

#### Create requirements.txt for Telegram bot Python dependencies
Python dependencies (`python-telegram-bot[job-queue]`) are only specified inline in `docker/Dockerfile` build commands, not in a dedicated requirements file. This makes version pinning difficult and creates inconsistency between Docker and DevContainer builds. Add `src/telegram_bot/requirements.txt` with pinned versions and use it in both Dockerfiles.
