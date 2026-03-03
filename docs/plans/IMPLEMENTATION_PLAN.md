# Loop System Improvements Implementation Plan

**Status:** COMPLETE

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement three ROADMAP proposals: `loop doctor` health-check command, enhanced `loop summary` metrics (file edit frequency, iteration timing, error rates), and expanded test coverage for `run.js`, `cleanup.js/sh`, and `summary.js` edge cases.

**Architecture:** Test coverage tasks come first (Phases 1-4) so new code is validated by tests from the start. The `doctor` command (Phases 5-6) follows the existing pattern: `lib/doctor.js` module + `cli.js` registration. Summary enhancements (Phases 7-8) extend existing `parseLog()` and `formatSummary()` functions in `summary.js` with backward-compatible new fields.

**Tech Stack:** Node.js (>=18), Jest 30, Commander 14, Bash (shell tests)

---

## Findings & Decisions

1. **run.js testability**: `spawnLoop()` mixes argument-building with process spawning, making it untestable without mocking `child_process`. Solution: extract a pure `buildArgs(opts, mode)` function and export it alongside the existing public API. This is the minimal change needed — no refactor of `spawnLoop` itself.

2. **cleanup.js/sh**: Both are thin wrappers. JS module tests mock `child_process.spawn` and `fs.existsSync`. Shell tests mock `lsof`/`fuser` via `$PATH` prepend (same pattern as existing shell tests).

3. **summary.js edge cases**: Current test coverage is solid for happy paths but misses: `unknown` tool name fallback, missing `file_path` in Edit/Write, non-array `content`, empty JSONL file, multiple `testResults` entries, and the `tool_result` block type in test extraction.

4. **loop doctor checks**: Claude CLI binary, loop symlinks (6 files), `.version` match, `jq` binary, git repo status, required env vars (`GH_TOKEN`). MCP connectivity via `claude mcp list` (subprocess, non-fatal). Output: pass/fail checklist with fix suggestions.

5. **Summary enhancements**: `parseLog` already tracks `filesModified` as a Set (unique paths). Extend to `fileEditCounts` Map (path → count). Add timestamp parsing for iteration boundaries (using `result` entries with `usage`). Error rate = count of `result` entries with `is_error: true`.

6. **Version bump**: Final task bumps `src/package.json` from `0.7.3` to `0.8.0` (new `doctor` command = minor bump).

---

## Phases 1–7 (complete — see git history for details)

- Phase 1: run.js Testability Refactor (Tasks 1–2)
- Phase 2: run.js checkLoopScript & cleanup.js Tests (Tasks 3–4)
- Phase 3: Shell Script Tests for cleanup.sh (Tasks 5–6)
- Phase 4: summary.js Edge Case Tests (Tasks 7–8)
- Phase 5: loop doctor — Core Module (Tasks 9–10)
- Phase 6: Enhanced Summary — File Edit Frequency (Tasks 11–12)
- Phase 7: Enhanced Summary — Iteration Timing & Error Rates (Tasks 13–14)

---

## Phase 8: Version Bump & Integration Verification

**Status:** complete

### Task 15: Update integration tests for new summary fields

- [x] Update integration test realistic JSONL to verify new metrics fields

**Files:**
- Modify: `src/lib/__tests__/integration.test.js`

### Task 16: Bump version and run full validation

- [x] Bump package version to 0.8.0 and run all tests

**Files:**
- Modify: `src/package.json:3` (version)
