# Roadmap

## Completed Features

## Proposals

### P1 - Critical

#### Telegram: Task completion summary with actionable next steps
When a loop task finishes, the bot sends only a generic "done" message. The user has no idea what changed — files modified, tests passing, commits made. They must SSH in or `tmux attach` to find out. Add a completion summary that parses the last run's git diff and test output, then sends a Telegram message with key metrics (files changed, commits created, test results) and inline buttons for next actions (View Diff, Start Review, Deploy). This turns the bot from a "fire and forget" launcher into a proper feedback loop.

#### Telegram: Live progress notifications during loop execution
A 5-iteration build can run 30+ minutes with zero feedback. The user sees "task started" and then nothing until it finishes (or silently fails). Poll the `.progress` file and tmux output at each iteration boundary. Send a short notification per iteration: "2/5 complete — updated auth module, 12 tests passing". Include error alerts if the loop crashes mid-run, so the user knows immediately instead of discovering it later.

### P2 - Important

#### Brainstorming session persistence across container restarts
Brainstorming sessions live only in memory (`BrainstormManager.sessions` dict). If the container restarts or the bot crashes, all active sessions are lost with no way to resume. Save session metadata to disk (session ID, project, Claude `--resume` session ref) so sessions survive restarts. Add a "Resume session" option in the Telegram bot that lists recent sessions for the current project.

#### Loop run summary with post-execution report
After `loop run` finishes, the only output is the log file path. The user must manually check git diff, read JSONL logs, and inspect the implementation plan to understand what happened. Generate a human-readable summary at the end of each run: files modified, tests run (pass/fail), plan progress percentage, commits created, and a suggested next step ("Plan complete — run `loop run` to start building"). Also add `loop summary` CLI command to view the last run's report on demand.

#### Telegram: Formatted log viewer without terminal access
Reading loop logs requires `tmux attach` or parsing raw JSONL files — impossible from a phone. Add a "View Logs" button in the project menu that fetches the last N lines of the current or most recent run, formats them as readable Telegram messages (tool calls, errors, git operations), and sends them in a paginated view. This enables full remote monitoring without SSH access.

### P3 - Nice to Have

#### Multi-project parallel task execution
The bot runs one task per project, but projects are strictly sequential in practice. For multi-repo workflows (frontend + backend), the user queues tasks and waits for each to complete before the next starts. Allow configurable parallel tmux sessions (default: 2) so multiple projects can run simultaneously. Add a global status view in Telegram showing all running tasks across projects.

#### Setup health check command
After setup (Docker, DevContainer, or local), there is no way to verify everything works. Skills may have silently failed to install, MCP servers may not be responding, or the GitHub token may lack permissions. Add `loop doctor` that checks: Claude CLI installed, skills loaded, MCP servers responding, GitHub token valid, Telegram bot connected. Output a clear pass/fail checklist so users can fix issues before starting real work.
