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

## Brainstorming (NEW)

| Command | Description |
|---------|-------------|
| `/brainstorming <prompt>` | Start interactive brainstorming session with Claude |
| `/done` | Finish brainstorming and save result to `docs/ROADMAP.md` |
| `/save` | Same as `/done` |

## Interactive Buttons

The bot uses inline keyboard buttons for most interactions:

### Project List
- **▸ Project** - Standalone repo
- **↳ Project** - Worktree
- **◉ Project** - Running task
- **↓ Klonuj repo** - Clone a git repository

### Project Menu
- **Plan** - Start planning mode
- **Build** - Start build mode
- **Brainstorm** - Start brainstorming session
- **Nowy worktree** - Create new git worktree (any project)
- **Loop init** - Initialize loop in project (shown when loop not configured)
- **Status** - Show task status
- **Podlacz** - Get tmux attach command for running task
- **Kolejka** - View queued tasks
- **Powrot** - Go back to project list

### After Brainstorming
- **Uruchom Plan** - Start Plan mode with saved IDEA
- **Zakoncz** - End session without running Plan

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
→ Click "Uruchom Plan" or "Zakoncz"
```

### Check running tasks
```
/status
```

### Attach to running session
```
/start
→ Select running project (◉ icon)
→ Click "Podlacz"
→ Copy tmux command
```
