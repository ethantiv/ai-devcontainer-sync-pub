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
