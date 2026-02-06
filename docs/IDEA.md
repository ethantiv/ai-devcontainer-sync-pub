# Telegram Bot Refactor: Adapt to ai-devcontainer-sync Architecture

## Context

The Telegram bot was migrated from `ethantiv/playground` (single-repo + worktrees model) to `ai-devcontainer-sync` (multi-repo model). While imports and paths were updated, the bot's architecture still carries playground-era assumptions:

- `MAIN_PROJECT` config for a single "main" repo with worktrees
- `is_main` flag that splits UI into two modes (main vs worktree)
- `create_worktree()` only works from the main project
- No ability to clone new repos

## Goals

- Remove the single-main-project assumption
- Every repo in `PROJECTS_ROOT` is a first-class project
- Any project can create worktrees
- Add `git clone` capability from Telegram
- Auto-run `loop init` after clone

## Non-Goals

- No persistence layer (queue/tasks stay in-memory)
- No i18n (stays Polish)
- No changes to `tasks.py` (TaskManager/BrainstormManager)

---

## Design

### 1. `config.py` Changes

**Remove:**
- `MAIN_PROJECT` — no longer needed
- `DEFAULT_ITERATIONS` — unused (bot always prompts for iterations)

**Keep:**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PROJECTS_ROOT`

### 2. `projects.py` Changes

#### `Project` Dataclass

```python
@dataclass
class Project:
    name: str
    path: Path
    branch: str
    is_worktree: bool      # True if this is a worktree (not the main checkout)
    parent_repo: str | None  # Name of parent repo if is_worktree, else None
    has_loop: bool
```

Removes `is_main` (playground concept). Adds `is_worktree` and `parent_repo` for worktree awareness.

#### `list_projects()` — Rewrite

Single-mode scan (no `MAIN_PROJECT` branching):

1. Iterate all directories in `PROJECTS_ROOT`
2. For each directory with `.git`:
   - Run `git worktree list --porcelain`
   - If it only lists itself: standalone repo (`is_worktree=False`)
   - If it has other worktrees: they should appear elsewhere in `PROJECTS_ROOT` and will be scanned independently
3. For each directory that is a `.git` file (bare worktree link):
   - Parse to find parent repo
   - Mark as `is_worktree=True`, `parent_repo=<parent_name>`
4. Check `has_loop` via `(path / "loop" / "loop.sh").exists()`

Result: flat list of all projects, worktrees included, each with metadata.

#### `create_worktree(project_path, suffix)` — Generalized

```python
def create_worktree(project_path: Path, suffix: str) -> tuple[bool, str]:
    """Create worktree from any repo.

    Creates: PROJECTS_ROOT/{project}-{suffix}/ with branch {suffix}
    """
```

- Works from any repo in `PROJECTS_ROOT` (not just main)
- Naming: `{project_name}-{suffix}`
- Branch: `{suffix}`
- No `CLAUDE_template.md` copying (playground relic)

#### `clone_repo(url)` — New Function

```python
def clone_repo(url: str) -> tuple[bool, str]:
    """Clone a git repository into PROJECTS_ROOT.

    Extracts repo name from URL, clones, then runs `loop init`.
    Returns (success, message).
    """
```

- Parse repo name from URL (last path segment, strip `.git`)
- `git clone <url> PROJECTS_ROOT/<name>`
- Run `loop init` in the cloned directory
- Return success/failure with message

### 3. `bot.py` Changes

#### New State

```python
class State(IntEnum):
    SELECT_PROJECT = auto()
    PROJECT_MENU = auto()
    ENTER_NAME = auto()      # Worktree name input
    ENTER_IDEA = auto()
    SELECT_ITERATIONS = auto()
    BRAINSTORMING = auto()
    ENTER_BRAINSTORM_PROMPT = auto()
    ENTER_URL = auto()        # NEW: Git clone URL input
```

#### `show_projects()` — Updated Icons

```python
for project in projects:
    if task_manager.check_running(project.path):
        label = f"🔄 {label}"      # Running task
    elif project.is_worktree:
        label = f"🔀 {label}"      # Worktree
    else:
        label = f"📁 {label}"      # Standalone repo
```

Plus a "Clone repo" button at the bottom:

```python
keyboard.append([InlineKeyboardButton("➕ Klonuj repo", callback_data="action:clone")])
```

#### `show_project_menu()` — Unified

Remove the `if project.is_main` branch entirely. Single unified menu for all projects:

- If `has_loop`: Plan, Build, Brainstorm buttons
- Always: "Nowy worktree" button, Status, Back
- If task running: Attach, Queue buttons (as before)
- If no `has_loop`: warning message + option to run `loop init`

#### New Handlers

- `handle_clone_url()`: Receives URL text, calls `clone_repo()`, shows result
- `handle_worktree_name()`: Receives suffix, calls `create_worktree(project.path, suffix)`
- Update `handle_action()` to route `action:clone` → prompt for URL, `action:worktree` → prompt for name

### 4. Cleanup in Other Files

#### `CLAUDE.md`
- Remove `MAIN_PROJECT` from env vars table
- Update Telegram bot documentation if needed

#### `docker/entrypoint.sh`
- Remove `MAIN_PROJECT` from the bot startup command env vars (line ~133)
- Keep `PROJECTS_ROOT` as before

#### `README.md`
- Remove `MAIN_PROJECT` from environment variables section

---

## Data Flow: Clone New Repo

```
User taps "➕ Klonuj repo" on project list
    ↓
Bot prompts: "Podaj URL repozytorium:"
    ↓
User sends: https://github.com/user/repo.git
    ↓
clone_repo(url) → git clone → loop init
    ↓
Bot shows: "✅ Sklonowano repo. Loop zainicjalizowany."
    ↓
Returns to project list (new repo visible)
```

## Data Flow: Create Worktree

```
User selects project "my-app" → menu
    ↓
User taps "🔀 Nowy worktree"
    ↓
Bot prompts: "Podaj nazwę worktree:"
    ↓
User sends: feature-x
    ↓
create_worktree(project_path, "feature-x")
    → git worktree add -b feature-x PROJECTS_ROOT/my-app-feature-x
    ↓
Bot shows: "✅ Utworzono my-app-feature-x na branchu feature-x"
    ↓
Returns to project list (worktree visible with 🔀)
```

---

## Files to Change

| File | Action | Scope |
|------|--------|-------|
| `loop/telegram_bot/config.py` | Edit | Remove `MAIN_PROJECT`, `DEFAULT_ITERATIONS` |
| `loop/telegram_bot/projects.py` | Rewrite | New `list_projects()`, `create_worktree()`, add `clone_repo()`, update `Project` |
| `loop/telegram_bot/bot.py` | Edit | Unified menu, new `ENTER_URL` state, clone/worktree handlers |
| `loop/telegram_bot/tasks.py` | None | No changes needed |
| `CLAUDE.md` | Edit | Remove `MAIN_PROJECT` from env vars |
| `docker/entrypoint.sh` | Edit | Remove `MAIN_PROJECT` from bot env |
| `README.md` | Edit | Remove `MAIN_PROJECT` from env vars |
