# Roadmap

## Proposals

#### Add `loop doctor` command for environment health checks
Users setting up the environment across 4 deployment targets (DevContainer, Docker, Coolify, macOS) have no quick way to verify everything is working. A `loop doctor` command should check: Claude CLI availability, MCP server connectivity, required env vars, loop symlink integrity, Git config, and plugin installation status. Output a clear pass/fail checklist with actionable fix suggestions.

#### Improve `loop summary` output with structured metrics
The summary command parses JSONL logs for basic stats but doesn't surface key insights like: which files were most edited, tool usage breakdown, time per iteration, or error rates. Richer summary output helps users understand what the loop accomplished and where it spent time, making it easier to tune iteration counts and prompts.

#### Expand test coverage for run modes and cleanup
`run.js` spawn logic has minimal testing (only export validation). `cleanup.sh` and `kill-loop.sh` have no tests at all. `summary.js` edge cases (malformed JSONL, missing fields, empty logs) are partially covered. Adding tests for these areas would improve confidence during refactoring and loop system updates.
