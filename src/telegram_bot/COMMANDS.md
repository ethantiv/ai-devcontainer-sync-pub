# Telegram Bot Commands

## Navigation

| Command | Description |
|---------|-------------|
| `/start` | Show project list and start navigation |
| `/projects` | Same as `/start` - show available projects |
| `/status` | Show status of all active tasks |

## Help

| Command | Description |
|---------|-------------|
| `/help` | Show bot usage instructions and available commands |

## Task Management

| Command | Description |
|---------|-------------|
| `/cancel` | Cancel current operation and return to start |
| `/skip` | Skip optional idea input when starting Plan mode |

## Brainstorming

| Command | Description |
|---------|-------------|
| `/brainstorming <prompt>` | Start interactive brainstorming session with Claude |
| `/done` | Finish brainstorming and save result to `docs/ROADMAP.md` |
| `/save` | Same as `/done` |
| `/history` | Show past brainstorming sessions (filtered by selected project) |

## Interactive Buttons

The bot uses inline keyboard buttons for most interactions:

### Project List
- **▸ Project** - Standalone repo
- **↳ Project** - Worktree
- **◉ Project** - Running task
- **◀ Prev** / **Next ▶** - Page navigation (shown when >5 projects)
- **+ New project** - Create a new project
- **↓ Clone repo** - Clone a git repository

### Project Menu
- **Plan** - Start planning mode
- **Build** - Start build mode
- **Brainstorm** - Start brainstorming session
- **New worktree** - Create new git worktree (any project)
- **Loop init** - Initialize loop in project (shown when loop not configured)
- **Status** - Show task status
- **Attach** - Get tmux attach command for running task
- **Queue** - View queued tasks
- **Sync** - Pull latest changes from remote (shows update count)
- **Back** - Go back to project list

### After Brainstorming
- **Run Plan** - Start Plan mode with saved roadmap
- **Finish** - End session without running Plan

## Conversation State Machine

```mermaid
stateDiagram-v2
    [*] --> SELECT_PROJECT : /start, /projects, /history

    state "SELECT_PROJECT" as SP {
        direction LR
        state "Project list with pagination" as sp_desc
    }
    state "PROJECT_MENU" as PM {
        direction LR
        state "Actions for selected project" as pm_desc
    }
    state "ENTER_IDEA" as EI {
        direction LR
        state "Optional idea text for Plan" as ei_desc
    }
    state "SELECT_ITERATIONS" as SI {
        direction LR
        state "Choose 3/5/10/custom iterations" as si_desc
    }
    state "ENTER_BRAINSTORM_PROMPT" as EBP {
        direction LR
        state "Topic for brainstorming" as ebp_desc
    }
    state "BRAINSTORMING" as BS {
        direction LR
        state "Interactive Claude session" as bs_desc
    }
    state "ENTER_NAME" as EN {
        direction LR
        state "Worktree suffix input" as en_desc
    }
    state "ENTER_URL" as EU {
        direction LR
        state "Git clone URL input" as eu_desc
    }
    state "ENTER_PROJECT_NAME" as EPN {
        direction LR
        state "New project name input" as epn_desc
    }
    state "GITHUB_CHOICE" as GC {
        direction LR
        state "Private / Public / Skip" as gc_desc
    }

    %% Entry points
    [*] --> PM : /status
    [*] --> BS : /brainstorming (with prompt)

    %% SELECT_PROJECT transitions
    SP --> PM : Select project
    SP --> SP : Pagination, export
    SP --> EPN : + New project
    SP --> EU : Clone repo

    %% PROJECT_MENU transitions
    PM --> SP : Back
    PM --> EI : Plan
    PM --> SI : Build
    PM --> EBP : Brainstorm
    PM --> BS : Resume brainstorm
    PM --> EN : New worktree
    PM --> EPN : + New project
    PM --> EU : Clone repo
    PM --> PM : Status, Queue, Sync, Loop init, History log

    %% ENTER_IDEA flow
    EI --> SI : Text / Skip
    EI --> SP : Cancel

    %% SELECT_ITERATIONS flow
    SI --> SP : Start task / Cancel
    SI --> SI : Custom (invalid)

    %% Brainstorm flow
    EBP --> BS : Text / Continue session
    EBP --> SP : Cancel
    BS --> BS : Messages, /done, /save
    BS --> SI : Run Plan
    BS --> SP : End / Cancel

    %% Worktree flow
    EN --> SP : Text (success) / Cancel
    EN --> EN : Invalid name

    %% Clone flow
    EU --> SP : Text (success) / Cancel
    EU --> EU : Clone failure

    %% Project creation flow
    EPN --> GC : Valid name (project created)
    EPN --> EPN : Invalid name
    EPN --> SP : Cancel
    GC --> PM : Private / Public (success)
    GC --> SP : Skip

    %% Global fallbacks (any state)
    note right of SP
        Global fallbacks from any state:
        /cancel, /start -> SELECT_PROJECT
        /help -> no state change
    end note
```

## Usage Examples

### Start a task
```
/start
→ Select project
→ Click "Plan" or "Build"
→ Enter idea (or /skip)
→ Select iterations
```

### Brainstorming session
```
/brainstorming Add user authentication with MFA
→ Answer Claude's questions
→ /done
→ Click "Run Plan" or "Finish"
```

### Check running tasks
```
/status
```

### Attach to running session
```
/start
→ Select running project (◉ icon)
→ Click "Attach"
→ Copy tmux command
```
