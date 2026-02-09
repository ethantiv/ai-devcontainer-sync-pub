"""Centralized user-facing string constants for the Telegram bot.

All translatable strings live here. Import by name in bot.py, tasks.py, projects.py.
Error codes for BrainstormManager are also defined here to decouple
error detection from display language.
"""

# --- Error codes for BrainstormManager (used by _is_brainstorm_error) ---

ERR_SESSION_ACTIVE = "session_active"
ERR_START_FAILED = "start_failed"
ERR_TIMEOUT = "timeout"
ERR_NO_SESSION = "no_session"
ERR_NOT_READY = "not_ready"
ERR_NO_RESULT = "no_result"
ERR_CLAUDE_ERROR = "claude_error"

BRAINSTORM_ERROR_CODES = frozenset({
    ERR_SESSION_ACTIVE,
    ERR_START_FAILED,
    ERR_TIMEOUT,
    ERR_NO_SESSION,
    ERR_NOT_READY,
    ERR_NO_RESULT,
    ERR_CLAUDE_ERROR,
})

# --- Dev mode ---

MSG_DEV_MODE_SKIP = "DEV_MODE is active — skipping Telegram bot startup"

# --- bot.py strings ---

MSG_UNAUTHORIZED = "Unauthorized"
MSG_NO_PROJECTS = "No projects found. Check PROJECTS_ROOT configuration."
MSG_PROJECT_NOT_FOUND = "Project not found"
MSG_AVAILABLE_PROJECTS = "*Available projects:*"
MSG_CLONE_REPO_BTN = "\u2193 Clone repo"
MSG_STATUS_RUNNING = "\u25c9 Running"
MSG_STATUS_FREE = "\u25cb Free"
MSG_IN_QUEUE = "{count} in queue"
MSG_ACTIVE_BRAINSTORM = "\n~ Active brainstorming session"
MSG_RESUME_SESSION_BTN = "\u21ba Resume session"
MSG_ATTACH_BTN = "\u25b6 Attach"
MSG_STATUS_BTN = "\u25ce Status"
MSG_QUEUE_BTN = "\u2261 Queue ({count})"
MSG_PLAN_BTN = "\u25c7 Plan"
MSG_BUILD_BTN = "\u25a0 Build"
MSG_BRAINSTORM_BTN = "~ Brainstorm"
MSG_BACK_BTN = "\u2190 Back"
MSG_PAGE_PREV_BTN = "\u25c0 Prev"
MSG_PAGE_NEXT_BTN = "Next \u25b6"
MSG_PAGE_INDICATOR = "Page {current}/{total}"
MSG_PROJECTS_LIST_BTN = "\u2261 Projects"
MSG_NEW_WORKTREE_BTN = "\u21b3 New worktree"
MSG_LOOP_INIT_BTN = "\u2699 Loop init"
MSG_LOOP_NOT_INITIALIZED = "\n\n! Loop not initialized (loop/loop.sh not found)"
MSG_ITERATION_LABEL = "Iteration"

# Clone flow
MSG_ENTER_REPO_URL = (
    "*Enter repository URL:*\n\n"
    "E.g. `https://github.com/user/repo.git`"
)
MSG_ENTER_REPO_URL_EMPTY = "\u2717 Enter repository URL."
MSG_CLONING_REPO = "\u2026 Cloning repository..."

# Worktree flow
MSG_ENTER_WORKTREE_NAME = (
    "*Enter worktree name:*\n\n"
    "Will create: `{project}-{{name}}`\n"
    "Branch: `{{name}}`"
)
MSG_INVALID_NAME = "Invalid name. Use letters, digits, hyphens and underscores."
MSG_NO_PROJECT_SELECTED = "\u2717 No project selected."

# Loop init
MSG_LOOP_INIT_OK = "\u2713 Loop initialized in {name}"
MSG_LOOP_INIT_FAIL = "\u2717 Loop init failed in {name}"

# Plan flow
MSG_PLAN_ENTER_IDEA = (
    "*Plan: Describe idea*\n\n"
    "Enter a feature description or tap Skip."
)

# Attach
MSG_ATTACH_SESSION = "\u25b6 *Attach to session:*\n\n`tmux attach -t {session}`"

# Brainstorm flow
MSG_BRAINSTORM_HEADER = (
    "~ *Brainstorming*\n\n"
    "Project: `{project}`\n\n"
    "Describe a topic/idea to discuss:"
)
MSG_BRAINSTORM_ENTER_TOPIC = "\u2717 Enter a brainstorming topic."
MSG_BRAINSTORM_NO_SESSION = "\u2717 No active brainstorming session for this project."
MSG_BRAINSTORM_RESUME = (
    "~ *Resuming brainstorming session*\n\n"
    "Project: `{project}`\n"
    "Started: {time}\n\n"
    "_Continue the discussion or tap a button below._"
)
MSG_BRAINSTORM_THINKING = "~ *Brainstorming*\n\nProject: `{project}`\n_{status}_"
MSG_BRAINSTORM_STARTING = "Starting Claude..."
MSG_BRAINSTORM_CLAUDE_THINKING = "Claude thinking..."
MSG_BRAINSTORM_REPLY_HINT = (
    "_Reply to continue or tap a button below._"
)
MSG_BRAINSTORM_REPLY_HINT_LONG = (
    "_Reply to continue or tap a button below._"
)
MSG_BRAINSTORM_SAVING = "\u2026 _Saving IDEA..._"
MSG_BRAINSTORM_DONE_BTN = "\u2713 Done"
MSG_BRAINSTORM_SAVE_BTN = "\u2713 Save"
MSG_BRAINSTORM_RUN_PLAN_BTN = "\u25c7 Run Plan"
MSG_BRAINSTORM_END_BTN = "\u00b7 Finish"
MSG_BRAINSTORM_WHAT_NEXT = "\u2713 *{message}*\n\nWhat would you like to do next?"
MSG_BRAINSTORM_STARTING_PLAN = "\u25b6 *Starting Plan for {project}...*"
MSG_BRAINSTORM_SESSION_ENDED = "\u2713 Brainstorming session ended."
MSG_BRAINSTORM_CANCELLED = "\u2717 Brainstorming cancelled."
MSG_BRAINSTORM_NO_ACTIVE = "No active brainstorming session."

# Iterations
MSG_CUSTOM_AMOUNT_BTN = "Custom amount..."
MSG_CANCEL_BTN = "\u2717 Cancel"
MSG_SELECT_ITERATIONS = "# *Select number of iterations:*\n\nProject: `{project}`\nMode: {mode}"
MSG_ENTER_ITERATIONS = "# *Enter number of iterations:*"

# Task started / queued
MSG_TASK_STARTED = "{icon} *Task started*\n\n"
MSG_TASK_QUEUED = "\u2261 *{message}*\n\n"
MSG_TASK_ERROR = "\u2717 *Error*\n\n{message}"
MSG_PROJECT_LABEL = "Project: `{project}`\n"
MSG_MODE_LABEL = "Mode: {mode}\n"
MSG_ITERATIONS_LABEL = "Iterations: {iterations}\n"
MSG_IDEA_LABEL = "Idea: {idea}\n"
MSG_SESSION_LABEL = "\nSession: `loop-{project}`"
MSG_CANCELLED = "Cancelled."

# Queue
MSG_QUEUE_TITLE = "\u2261 *Queue for {project}*\n\n"
MSG_QUEUE_EMPTY = "Queue is empty."
MSG_CANCEL_QUEUE_ITEM = "\u2717 Cancel #{num}"
MSG_REMOVED_FROM_QUEUE = "Removed from queue"
MSG_TASK_NOT_FOUND = "Task not found"

# Status
MSG_STATUS_TITLE = "\u25ce *Status*\n\nNo active tasks."
MSG_ACTIVE_TASKS_TITLE = "\u25ce *Active tasks:*\n\n"

# Completion summary
MSG_COMPLETION_TITLE = "{icon} *{project}* \u2014 {mode} completed\n\n"
MSG_COMPLETION_ITERATIONS = "Iterations: {iterations}\n"
MSG_COMPLETION_TIME = "Time: {duration}\n"
MSG_COMPLETION_CHANGES = (
    "\n\u0394 *Changes:*\n"
    "  Files: {files}\n"
    "  Lines: +{ins} / -{dels}\n"
)
MSG_COMPLETION_COMMITS = "\n\u2192 *Commits:*\n"
MSG_COMPLETION_PLAN = "\n\u25c7 *Plan:* {done}/{total} ({pct}%)\n  {bar}\n"
MSG_DIFF_SUMMARY_BTN = "\u0394 Change summary"
MSG_PROJECT_BTN = "\u25b8 Project"
MSG_STARTED_FROM_QUEUE = (
    "\u25b6 *Started from queue:*\n"
    "{icon} {project} - {mode} \u2022 {iterations} iterations"
)
MSG_COMPLETION_QUEUE_NEXT = (
    "\n\u25b6 *Next:* {icon} {project} - {mode} \u2022 {iterations} iterations"
)

# Sync / Pull
MSG_SYNC_BTN = "^ Sync"
MSG_SYNC_BTN_WITH_COUNT = "^ Sync ({count} new)"
MSG_SYNC_SUCCESS = "\u2713 *Sync complete*\n\n{message}"
MSG_SYNC_FAILED = "\u2717 *Sync failed*\n\n{message}"
MSG_SYNC_NO_UPDATES = "\u2713 Already up to date."
MSG_SYNC_PULLING = "\u2026 Pulling changes..."

# Stale progress
MSG_STALE_PROGRESS = "! *{project}* \u2014 no progress for {minutes} min"

# Disk space and log rotation
MSG_DISK_LOW = "\u26a0 *Disk space low* \u2014 {available_mb} MB free (minimum: {min_mb} MB). Cannot start task."
MSG_LOG_ROTATION_COMPLETE = "\u2713 Log rotation complete: {deleted} files removed, {freed_mb:.1f} MB freed"

# Diff
MSG_DIFF_TITLE = "\u0394 *Changes in {project}:*\n\n```\n{diff}\n```"
MSG_NO_DATA = "No data"
MSG_TRUNCATED = "\n... (truncated)"

# Help
MSG_HELP = (
    "How does the bot work?\n"
    "\n"
    "1. Select a project from the list (/start)\n"
    "2. Choose action: Plan, Build, or view queue\n"
    "3. Enter task description (optional in Plan mode)\n"
    "4. Select number of iterations\n"
    "5. Bot will run Claude in background \u2014 track progress via /status\n"
    "\n"
    "You can also start a brainstorming session with /brainstorming.\n"
    "\n"
    "Commands:\n"
    "\n"
    "/start \u2014 Show project list and select a project\n"
    "/status \u2014 Show active tasks and their progress\n"
    "/brainstorming <topic> \u2014 Start brainstorming session with Claude\n"
    "/history \u2014 Show past brainstorming sessions\n"
    "/cancel \u2014 Cancel current operation\n"
    "/skip \u2014 Skip task description (Plan mode)\n"
    "/done \u2014 Finish brainstorming and save result\n"
    "/save \u2014 Alias for /done"
)

MSG_BRAINSTORM_CMD_USAGE = (
    "\u2717 Select a project first with /projects"
)
MSG_BRAINSTORM_CMD_PROMPT_REQUIRED = (
    "\u2717 Enter a brainstorming topic:\n`/brainstorming <idea description>`"
)

# Brainstorm history
MSG_BRAINSTORM_HISTORY_TITLE = "~ *Brainstorm history*\n\n"
MSG_BRAINSTORM_HISTORY_EMPTY = "No brainstorm sessions recorded yet."
MSG_BRAINSTORM_SESSION_ENTRY = (
    "{num}. *{project}* — {topic}\n"
    "   {date} \u2022 {turns} turn(s)\n"
)

# --- tasks.py strings ---

MSG_QUEUE_FULL = "Queue full ({max_size} tasks)"
MSG_QUEUE_EXPIRED = "⏰ *Queue expired* — {project} {mode} ({iterations} iter) removed after {minutes} min in queue"
MSG_QUEUED_AT = "Queued #{position}"
MSG_CLAUDE_ENDED_NO_RESULT = "Claude ended without result:\n{tail}"
MSG_CLAUDE_ENDED_NO_RESPONSE = "Claude ended without response"
MSG_TIMEOUT_WAITING = "Timeout waiting for Claude response"
MSG_SESSION_ALREADY_ACTIVE = "Brainstorming session already active. Finish or cancel the current one first."
MSG_FAILED_TO_START_CLAUDE = "Failed to start Claude"
MSG_NO_ACTIVE_BRAINSTORM = "No active brainstorming session. Use /brainstorming <prompt>."
MSG_SESSION_NOT_READY = "Brainstorming session is not ready."
MSG_IDEA_SAVED = "Roadmap saved to {path}"
MSG_SUMMARY_PROMPT = (
    "Summarize our brainstorming session. "
    "Write a clear project description with goals and key decisions. "
    "Write only the summary content, no extra text."
)

# --- projects.py strings ---

MSG_WORKTREE_CREATED = "Created {name} on branch {suffix}"
MSG_DIR_ALREADY_EXISTS = "{name} already exists"
MSG_CLONED = "Cloned {name}"
MSG_LOOP_INITIALIZED = "Loop initialized."
MSG_LOOP_INIT_FAILED = "Loop init failed \u2014 run `loop init` manually."

# Project creation flow
MSG_CREATE_PROJECT_BTN = "+ New project"
MSG_ENTER_PROJECT_NAME = (
    "*Enter project name:*\n\n"
    "Use lowercase letters, digits and hyphens (e.g. `my-app`).\n"
    "Must start with a letter or digit."
)
MSG_CREATING_PROJECT = "\u2026 Creating project..."
MSG_PROJECT_CREATED = "\u2713 Project *{name}* created"
MSG_PROJECT_CREATE_FAILED = "\u2717 Failed to create project: {message}"

# Project name validation errors
MSG_INVALID_PROJECT_NAME = (
    "\u2717 Invalid project name.\n"
    "Use lowercase letters, digits and hyphens. Must start with a letter or digit."
)
MSG_PROJECT_EXISTS = "\u2717 Project *{name}* already exists."
MSG_RESERVED_NAME = "\u2717 *{name}* is a reserved name."

# GitHub repo creation flow
MSG_GITHUB_CHOICE_PROMPT = "\u2713 Project created locally.\n\nCreate a GitHub repository?"
MSG_GITHUB_PRIVATE_BTN = "\u25c6 Private"
MSG_GITHUB_PUBLIC_BTN = "\u25cb Public"
MSG_GITHUB_SKIP_BTN = "\u2192 Skip"
MSG_GITHUB_CREATING = "\u2026 Creating GitHub repository..."
MSG_GITHUB_CREATED = "\u2713 GitHub repository *{name}* created"
MSG_GITHUB_FAILED = "\u2717 GitHub repo creation failed: {message}"
MSG_GH_NOT_AVAILABLE = "\u2717 `gh` CLI not available \u2014 skipping GitHub integration."
