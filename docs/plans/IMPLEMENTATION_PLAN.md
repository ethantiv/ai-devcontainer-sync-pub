# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 17/20 (85%)

## Goal

Implement the four ROADMAP.md proposals for the Loop system: (P1) task completion summaries with actionable next steps, (P1) live progress notifications during loop execution, (P2) brainstorming session persistence across container restarts, and (P2) loop run summary with post-execution report. These features transform the Telegram bot from a "fire and forget" launcher into a proper feedback loop with real-time visibility and resilient session management.

## Current Phase

Phase 4: Loop Run Summary with Post-Execution Report

## Phases

### Phase 1: Task Completion Summary with Actionable Next Steps (P1)
- **Status:** complete (6/6 tasks)

### Phase 2: Live Progress Notifications During Loop Execution (P1)
- **Status:** complete (5/5 tasks)

### Phase 3: Brainstorming Session Persistence (P2)
- **Status:** complete (6/6 tasks)

### Phase 4: Loop Run Summary with Post-Execution Report (P2)
- [ ] Create `src/lib/summary.js` module with `generateSummary(logDir)` function: find latest `.jsonl` file in `logDir` via `fs.readdirSync` + sort by mtime, parse line-by-line via `readline.createInterface` + `fs.createReadStream`, extract: tool use counts by tool name (from JSON entries where `message.content[].type === "tool_use"`), total input/output tokens (from entries with `type === "result"` containing `usage` field), files modified (from Edit/Write tool `input.file_path` arguments), test results (from Bash tool output containing "PASS"/"FAIL"/"test" patterns)
- [ ] Add `loop summary` subcommand in `cli.js` (`src/bin/cli.js`): import `generateSummary` from `../lib/summary`, add command with `.description('Show summary of last loop run')` and optional `--log-dir` option (default `./loop/logs`), call `generateSummary()` and print formatted report to stdout with sections: Tool Usage, Files Modified, Test Results, Token Usage
- [ ] Integrate summary into `loop.sh` cleanup trap (`src/scripts/loop.sh:22-36`): after `notify-telegram.sh` call (line 31), add `node -e "require('/opt/loop/lib/summary').generateSummary('$LOG_DIR')" > "$LOG_DIR/summary-latest.txt" 2>/dev/null || true` to generate summary file on each run completion
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Should `loop summary` parse JSONL or rely on git? | Both: JSONL for tool/token metrics, git for commit/diff stats |

## Findings & Decisions

### Requirements

**P2 - Loop Run Summary:**
- Parse JSONL log files for tool usage metrics and token counts
- Extract test results from Bash tool output
- Create `loop summary` CLI command
- Auto-generate summary on loop completion via cleanup trap

### Research Findings

- **No tests exist** in the codebase. This is a configuration-first repository with no test framework configured.
- **No `loop summary` command** exists in `cli.js`. JSONL logs are written by `loop.sh` (line 235: `tee -a "$LOG_FILE"`) but never parsed or analyzed programmatically.
- **CLI structure**: `cli.js` uses Commander with `addLoopOptions()`/`addBuildOptions()` helpers. Adding `loop summary` follows the existing pattern at lines 57-65 (standalone command without loop options).
- **Brainstorm sessions now persist** to `PROJECTS_ROOT/.brainstorm_sessions.json` via atomic writes. Sessions are validated on load and stale entries removed.

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| `loop summary` as Node.js (not shell) | JSONL parsing is complex for bash; Node.js has native JSON support and aligns with existing CLI in `src/lib/` |
| Persist brainstorm sessions as JSON file | Simple, no external dependencies; JSON is human-readable for debugging |
| Atomic file writes for session persistence | Write to `.tmp` then `os.replace` prevents corruption from crashes during write |
| `_save_sessions()` in `_cleanup_session()` | Covers both `finish()` and `cancel()` paths without code duplication |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| No test framework to validate changes | ROADMAP doesn't require tests; rely on manual testing via Telegram bot and `loop` CLI |

### Resources
- Node.js: `readline` + `createReadStream` for JSONL parsing line-by-line
- Key files to modify: `cli.js` (summary subcommand), `loop.sh` (cleanup trap)
- Key files to create: `src/lib/summary.js`
