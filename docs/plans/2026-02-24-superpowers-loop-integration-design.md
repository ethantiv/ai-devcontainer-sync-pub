# Design: Superpowers Skills Integration into Loop System

## Goal

Integrate superpowers skills (writing-plans, test-driven-development, subagent-driven-development, systematic-debugging, verification-before-completion, dispatching-parallel-agents, brainstorming) into the loop system to produce more structured results and better code organization — without revolutionary changes to the working loop architecture.

## Approach

**Prompt-only integration (Approach A):** Modify prompts, skill files, and templates. Minimal changes to orchestration code (cli.js, run.js, loop.sh). The loop remains prompt-driven — superpowers skills enforce discipline through their own hard gates and checklists.

## Architecture

Three independent commands, three phases:

```
loop design    →  interactive brainstorming with user
                  input: ROADMAP.md + codebase
                  output: docs/plans/YYYY-MM-DD-<topic>-design.md

loop plan      →  autonomous implementation plan creation
                  input: design doc + codebase
                  output: docs/plans/IMPLEMENTATION_PLAN.md (superpowers format)

loop build     →  autonomous plan execution
                  input: plan doc + codebase
                  output: implemented code, tests, commits

loop run       →  plan + build (unchanged, design done separately)
```

## New Files

| File | Purpose |
|------|---------|
| `src/prompts/PROMPT_design.md` | Instructions for interactive design/brainstorming phase |
| `src/prompts/PROMPT_skills_plan.md` | Skills loaded in plan phase (brainstorming, writing-plans) |
| `src/prompts/PROMPT_skills_build.md` | Skills loaded in build phase (subagent-driven-development, TDD, verification, debugging, parallel-agents) |
| `src/templates/IMPLEMENTATION_PLAN_template.md` | New template in superpowers format (replaces old) |

## Modified Files

| File | Change |
|------|--------|
| `src/prompts/PROMPT_plan.md` | Rewritten: loads writing-plans, reads design doc, produces superpowers-format plan |
| `src/prompts/PROMPT_build.md` | Rewritten: loads subagent-driven-development, TDD, verification, debugging skills |
| `src/bin/cli.js` | Add `design` command (interactive, 5 iterations, supports -I and -n) |
| `src/lib/run.js` | Add `runDesign()`, refactor `spawnLoop` to accept mode (design/plan/build) |
| `src/scripts/loop.sh` | Add `-d` flag for design mode, disable auto-commit in build mode |

## Removed Files

| File | Reason |
|------|--------|
| `src/prompts/PROMPT_skills.md` | Replaced by PROMPT_skills_plan.md and PROMPT_skills_build.md |

## Prompt Details

### PROMPT_design.md

- Loads skills from PROMPT_skills_plan.md (including brainstorming)
- Reads `@docs/ROADMAP.md` as scope/goal
- Explores codebase with `feature-dev:code-explorer` subagents
- Invokes `brainstorming` skill — interactive session with user
- Output: design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Commits design doc at end
- Always interactive (ignores `-a` flag)

### PROMPT_plan.md (rewritten)

- Loads skills from PROMPT_skills_plan.md (including writing-plans)
- Reads latest design doc from `docs/plans/` + `ROADMAP.md`
- Invokes `writing-plans` skill — creates plan with bite-sized tasks (2-5 min each)
- Each task: files, snippets, atomic steps (test -> verify -> implement -> verify -> commit)
- Phases = max 2-3 tasks, each phase = one build iteration
- Output: `docs/plans/IMPLEMENTATION_PLAN.md` in superpowers format
- Commit + push at end of each iteration

### PROMPT_build.md (rewritten)

- Loads skills from PROMPT_skills_build.md
- Reads `docs/plans/IMPLEMENTATION_PLAN.md`
- Pre-check: if plan complete -> "BUILD COMPLETE" + EXIT
- Workflow per iteration (one phase):
  1. Invoke `subagent-driven-development` — per task: implement -> spec review -> code quality review
  2. Each subagent implements with `test-driven-development` (red-green-refactor)
  3. On errors: `systematic-debugging` (diagnose, don't guess)
  4. Independent problems: `dispatching-parallel-agents`
  5. Before claiming done: `verification-before-completion`
  6. Update plan (mark tasks `[x]`, update status)
  7. Invoke `auto-revise-claude-md`
  8. No auto-commit from loop.sh — subagents commit per task

### Skill Split

**PROMPT_skills_plan.md:**
- brainstorming (design phase only)
- writing-plans

**PROMPT_skills_build.md:**
- subagent-driven-development
- test-driven-development
- verification-before-completion
- systematic-debugging
- dispatching-parallel-agents

Frontend skills (agent-browser, frontend-design, etc.) removed from defaults — projects add them via their own CLAUDE.md.

## Plan Template (superpowers format)

```markdown
# Implementation Plan

> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

## Header
- **Goal:** [from ROADMAP.md / design doc]
- **Architecture:** [key decisions from design doc]
- **Tech stack:** [relevant technologies]

## Phase 1: [concrete deliverable name]
Status: pending | in_progress | complete

### Task 1.1: [imperative action]
**Files:** `path/to/file.ts`, `path/to/file.test.ts`

Steps:
1. Write failing test for [behavior]
   - Run: `[test command]`
   - Expected: FAIL - [expected error]
2. Implement [minimal code]
   - Run: `[test command]`
   - Expected: PASS
3. Commit: `[descriptive message]`

## Findings & Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
```

## Orchestration Changes

### cli.js

New command: `loop design` (interactive, 5 iterations, supports `-I` and `-n`).

### run.js

New function `runDesign(opts)`. Refactor `spawnLoop` from boolean `isPlan` to mode string (`design`/`plan`/`build`). Design forces interactive mode.

### loop.sh

- New flag `-d` for design mode: sets `PROMPT_FILE=PROMPT_design.md`, forces interactive
- Auto-commit (`ensure_committed()`) called only in plan and design modes, disabled in build mode
- `check_completion()` unchanged — superpowers format uses same `[ ]`/`[x]` checkboxes

## Edge Cases

- **No design doc:** `loop plan` works without it — reads ROADMAP.md directly. Design doc is recommended, not required.
- **No plan:** `loop build` without IMPLEMENTATION_PLAN.md — agent creates plan from template and proceeds.
- **Subagent commit failure:** subagent-driven-development has built-in review loop (3 retries), then logs blocker and moves on.
- **Context window:** One phase per iteration (unchanged). Fresh context each iteration. Tasks are 2-5 min = small footprint.
- **Old plans:** Existing plans in old format still work with check_completion() (same [ ] pattern). No migration needed.

## Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Prompt-only integration | Preserves prompt-driven architecture, easy to revert | 2026-02-24 |
| New `loop design` command | Brainstorming is interactive, doesn't fit autonomous mode | 2026-02-24 |
| Separate skill files per phase | Plan doesn't need TDD, build doesn't need brainstorming | 2026-02-24 |
| Superpowers plan format | Granular tasks with atomic steps, test commands, expected output | 2026-02-24 |
| Disable auto-commit in build | Trust subagent-driven-development to commit per task | 2026-02-24 |
| subagent-driven-development for build | Continuous execution in same session, fresh subagent per task, two-stage review | 2026-02-24 |
| `loop run` unchanged | Design is separate interactive step, run stays plan+build | 2026-02-24 |
