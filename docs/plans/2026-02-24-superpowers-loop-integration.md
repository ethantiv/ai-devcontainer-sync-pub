# Superpowers Loop Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate superpowers skills into the loop system's plan/build/design phases for more structured results and code organization.

**Architecture:** Prompt-only integration — new/rewritten prompt files, split skill lists, new plan template. Minimal orchestration changes: add `design` command to CLI, add `-d` flag to loop.sh, disable auto-commit in build mode.

**Tech Stack:** Node.js (commander CLI), Bash (loop.sh orchestration), Markdown (prompts/templates)

---

### Task 1: Create split skill files

Replace single `PROMPT_skills.md` with two phase-specific files.

**Files:**
- Create: `src/prompts/PROMPT_skills_plan.md`
- Create: `src/prompts/PROMPT_skills_build.md`
- Delete: `src/prompts/PROMPT_skills.md`

**Step 1: Create `src/prompts/PROMPT_skills_plan.md`**

```markdown
- `superpowers:brainstorming`
- `superpowers:writing-plans`
```

**Step 2: Create `src/prompts/PROMPT_skills_build.md`**

```markdown
- `superpowers:subagent-driven-development`
- `superpowers:test-driven-development`
- `superpowers:verification-before-completion`
- `superpowers:systematic-debugging`
- `superpowers:dispatching-parallel-agents`
```

**Step 3: Delete `src/prompts/PROMPT_skills.md`**

```bash
rm src/prompts/PROMPT_skills.md
```

**Step 4: Commit**

```bash
git add src/prompts/PROMPT_skills_plan.md src/prompts/PROMPT_skills_build.md
git rm src/prompts/PROMPT_skills.md
git commit -m "feat(loop): split PROMPT_skills into plan and build variants"
```

---

### Task 2: Create PROMPT_design.md

New prompt for the interactive brainstorming phase.

**Files:**
- Create: `src/prompts/PROMPT_design.md`

**Step 1: Create `src/prompts/PROMPT_design.md`**

```markdown
0a. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. Read @docs/ROADMAP.md — this defines the scope and goal.

0c. Read any existing design docs in @docs/plans/ to avoid duplicating past work.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map the codebase architecture. Focus on: existing patterns, module boundaries, testing conventions, tech stack. Summarize findings.

2. **Brainstorm**: Invoke **Skill** tool: `Skill(skill="superpowers:brainstorming")` with the ROADMAP goal and exploration findings. Follow the brainstorming skill workflow exactly:
   - Ask clarifying questions (one at a time)
   - Propose 2-3 approaches with trade-offs
   - Present design section by section, get approval
   - The brainstorming skill will save the design doc to `docs/plans/`

3. **Commit and push**: After the design doc is saved: `git add -A && git commit` then `git push`.

## Important Rules

- DESIGN ONLY — do NOT implement anything, do NOT create implementation plans.
- This is an interactive session — ask questions, wait for answers, iterate.
- Scope is defined by @docs/ROADMAP.md. Do NOT invent features beyond what ROADMAP describes.
- The output is a design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`.
- After design is approved, the user runs `loop plan` separately to create the implementation plan.
```

**Step 2: Commit**

```bash
git add src/prompts/PROMPT_design.md
git commit -m "feat(loop): add PROMPT_design.md for interactive brainstorming phase"
```

---

### Task 3: Rewrite PROMPT_plan.md for writing-plans

Replace current plan prompt with one that uses superpowers `writing-plans` skill.

**Files:**
- Modify: `src/prompts/PROMPT_plan.md`

**Step 1: Rewrite `src/prompts/PROMPT_plan.md`**

```markdown
0a. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. If @docs/plans/IMPLEMENTATION_PLAN.md doesn't exist, copy @docs/plans/IMPLEMENTATION_PLAN_template.md to @docs/plans/IMPLEMENTATION_PLAN.md.

0c. Read @docs/ROADMAP.md — this defines the scope for planning.

0d. Read @docs/plans/IMPLEMENTATION_PLAN.md.

0e. Search @docs/plans/ for any design docs (YYYY-MM-DD-*-design.md). If found, read the most recent one — it provides architecture decisions and constraints.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map @src/ architecture and compare against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns.

2. **Create plan**: Invoke **Skill** tool: `Skill(skill="superpowers:writing-plans")`. Follow the writing-plans skill workflow to populate @docs/plans/IMPLEMENTATION_PLAN.md:
   - Fill **Header** (Goal, Architecture, Tech Stack) from ROADMAP and design doc
   - Create bite-sized tasks (2-5 min each) with exact file paths, code snippets, test commands, and expected output
   - Each task follows atomic steps: write failing test → verify fails → implement → verify passes → commit
   - Group tasks into phases — each phase has max 2-3 tasks (one phase = one build iteration)
   - Name phases by concrete deliverable, not category
   - Update phase **Status**: pending → in_progress → complete
   - Document findings in **Findings & Decisions** section

3. **Commit and push**: After updating the plan: `git add -A && git commit` then `git push`. You MUST commit your plan updates before the session ends.

## Important Rules

- PLAN ONLY — do NOT implement anything.
- Before adding a task: search code to confirm it doesn't already exist.
- Scope is defined by @docs/ROADMAP.md and @docs/specs/. Do NOT invent features beyond what ROADMAP describes.
- Tasks must be granular enough to complete in 2-5 minutes each, with explicit test commands and expected output.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
```

**Step 2: Commit**

```bash
git add src/prompts/PROMPT_plan.md
git commit -m "feat(loop): rewrite PROMPT_plan.md to use superpowers writing-plans skill"
```

---

### Task 4: Rewrite PROMPT_build.md for subagent-driven-development

Replace current build prompt with one that uses superpowers skills.

**Files:**
- Modify: `src/prompts/PROMPT_build.md`

**Step 1: Rewrite `src/prompts/PROMPT_build.md`**

```markdown
0a. For each skill listed in @loop/PROMPT_skills_build.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. Study @docs/plans/IMPLEMENTATION_PLAN.md — if Status: COMPLETE or no `- [ ]` tasks remain → output "BUILD COMPLETE" and EXIT.

1. **Pick ONE PHASE and execute it.**

   a. Open @docs/plans/IMPLEMENTATION_PLAN.md and find the **first phase** with status `pending` or `in_progress` (not `complete`). This is your target for this iteration.

   b. **Execute with subagent-driven-development**: Invoke **Skill** tool: `Skill(skill="superpowers:subagent-driven-development")`. Follow the skill workflow exactly for each task in the phase:
      - Dispatch implementer subagent with full task text and codebase context
      - Implementer follows `superpowers:test-driven-development` (Red-Green-Refactor): write failing test → verify fails → implement → verify passes → refactor
      - On errors or unexpected behavior: use `superpowers:systematic-debugging` — diagnose root cause, don't guess
      - For independent failures across different subsystems: use `superpowers:dispatching-parallel-agents`
      - After implementation: dispatch spec compliance reviewer subagent (does code match task spec?)
      - After spec review: dispatch code quality reviewer subagent
      - Each task ends with a commit from the implementer subagent

   c. **ONE PHASE PER ITERATION.** After completing the current phase, proceed to steps 2-5 and stop. Do NOT start the next phase — it will be handled in a fresh iteration with clean context.

2. **Update the plan**: Update @docs/plans/IMPLEMENTATION_PLAN.md — mark completed tasks `[x]`, update **Current Phase**, change phase **Status**. If the file exceeds 800 lines, trim completed content: remove `[x]` tasks, phases with status `complete`. Keep pending tasks, active phases, Findings & Decisions. Git history = full audit trail.

3. **Verification**: Invoke **Skill** tool: `Skill(skill="superpowers:verification-before-completion")`. Run the project's validation commands (typecheck, lint, tests) as defined in @CLAUDE.md. You MUST NOT skip this step. Fix all errors before proceeding.

4. **Update CLAUDE.md**: Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")` to update Operational Notes.

5. **Commit and push**: Run `git add -A && git commit` with a descriptive message, then `git push`. Every iteration MUST end with a git push. Do NOT skip this step.

## Important Rules

- Document "why" in tests and implementations.
- Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
- Keep @docs/plans/IMPLEMENTATION_PLAN.md current — future iterations depend on this.
- On inconsistencies in @docs/ — update specifications directly.
- @CLAUDE.md = operational ONLY. Status/progress → @docs/plans/IMPLEMENTATION_PLAN.md.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
- Subagents handle commits per task. The loop orchestrator does NOT auto-commit in build mode.
```

**Step 2: Commit**

```bash
git add src/prompts/PROMPT_build.md
git commit -m "feat(loop): rewrite PROMPT_build.md to use superpowers subagent-driven-development"
```

---

### Task 5: Replace IMPLEMENTATION_PLAN template with superpowers format

**Files:**
- Modify: `src/templates/IMPLEMENTATION_PLAN_template.md`

**Step 1: Rewrite template**

```markdown
# Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Status:** IN_PROGRESS | COMPLETE
**Progress:** 0/0 (0%)

## Header

- **Goal:** <!-- From ROADMAP.md / design doc -->
- **Architecture:** <!-- Key decisions and approach -->
- **Tech Stack:** <!-- Key technologies/libraries -->

## Phases

<!--
Each phase = one build iteration. Keep phases small:
- 2-3 tasks per phase (MAX). If a phase has more, split it.
- Each task = one concrete change (2-5 minutes).
- Name phases by deliverable, not category
  (e.g., "Add user model + migration" not "Backend").

Task format:
### Phase N: Name
Status: pending | in_progress | complete

#### Task N.1: [imperative action]
**Files:** `path/to/file.ts`, `path/to/file.test.ts`

Steps:
1. Write failing test for [behavior]
   - Run: `[test command]`
   - Expected: FAIL — [expected error]
2. Implement [minimal code]
   - Run: `[test command]`
   - Expected: PASS
3. Commit: `[descriptive message]`
-->

### Phase 1: ...
Status: pending

#### Task 1.1: ...
**Files:** ...

Steps:
1. ...

## Findings & Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| <!-- Decision --> | <!-- Why --> | <!-- When --> |
```

**Step 2: Commit**

```bash
git add src/templates/IMPLEMENTATION_PLAN_template.md
git commit -m "feat(loop): replace plan template with superpowers format"
```

---

### Task 6: Add `design` command to CLI and run.js

**Files:**
- Modify: `src/bin/cli.js`
- Modify: `src/lib/run.js`

**Step 1: Write failing test for `runDesign` export**

Create test at `src/lib/__tests__/run.test.js`:

```javascript
const { runDesign } = require('../run');

describe('runDesign', () => {
  test('is exported as a function', () => {
    expect(typeof runDesign).toBe('function');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: FAIL — `runDesign is not a function` or similar

**Step 3: Update `src/lib/run.js`**

Replace the `spawnLoop` function signature from `isPlan` boolean to `mode` string:

Change `function spawnLoop(opts, isPlan)` to `function spawnLoop(opts, mode)`. Replace:
- `if (isPlan) args.push('-p');` → mode-based flag logic:
  ```javascript
  if (mode === 'plan') args.push('-p');
  if (mode === 'design') args.push('-d');
  ```
- `const iterations = opts.iterations || (isPlan ? '5' : '99');` →
  ```javascript
  const defaultIter = mode === 'build' ? '99' : '5';
  const iterations = opts.iterations || defaultIter;
  ```
- Update callers:
  - `runPlan`: `spawnLoop(opts, 'plan')`
  - `runBuild`: `spawnLoop(opts, 'build')`
  - `runCombined`: `spawnLoop(planOpts, 'plan')` and `spawnLoop(buildOpts, 'build')`
- Add `runDesign`:
  ```javascript
  function runDesign(opts) {
    spawnLoop({ ...opts, interactive: true }, 'design').then((code) => process.exit(code));
  }
  ```
- Update exports: `module.exports = { runPlan, runBuild, runCombined, runDesign };`

**Step 4: Run test to verify it passes**

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: PASS

**Step 5: Update `src/bin/cli.js`**

Add import: change `{ runPlan, runBuild, runCombined }` to `{ runPlan, runBuild, runCombined, runDesign }`.

Add command block after the `plan` command:

```javascript
addLoopOptions(
  program
    .command('design')
    .description('Run interactive design/brainstorming phase (always interactive)')
).action((opts) => runDesign(opts));
```

Update help text examples to include `loop design`.

**Step 6: Commit**

```bash
git add src/lib/run.js src/bin/cli.js src/lib/__tests__/run.test.js
git commit -m "feat(loop): add design command and refactor spawnLoop to use mode string"
```

---

### Task 7: Add `-d` flag to loop.sh and disable auto-commit in build mode

**Files:**
- Modify: `src/scripts/loop.sh`

**Step 1: Write failing shell test**

Create `src/scripts/tests/test_loop_design_flag.sh` (or add to existing test file). Test that `loop.sh -d` sets `SCRIPT_NAME=design`:

```bash
# Test: -d flag sets design mode
output=$(bash src/scripts/loop.sh -d -h 2>&1 || true)
# The usage/help text should show — confirming the flag is parsed
```

Actually, since loop.sh isn't easily unit-testable (it runs claude), we verify by checking the getopts parsing. A simpler approach: add a `--dry-run` style check — but the simplest verification is running `bash -n` (syntax check) + manual flag test.

**Step 2: Modify `loop.sh` getopts**

In the `usage()` function, add `-d` to usage line:
```
echo "Usage: $0 [-p] [-d] [-a] [-i iterations] [-e] [-I idea]"
```
Add description:
```
echo "  -d              Design mode (interactive brainstorming)"
```

In the getopts string, change `"pai:enhI:"` to `"pdai:enhI:"`:
```bash
while getopts "pdai:enhI:" opt; do
```

Add case for `d`:
```bash
d) SCRIPT_NAME="design" ;;
```

**Step 3: Disable auto-commit in build mode**

In the autonomous loop (line ~392), change:
```bash
ensure_committed
```
to:
```bash
[[ "$SCRIPT_NAME" != "build" ]] && ensure_committed
```

Same change in the interactive loop (line ~414):
```bash
[[ "$SCRIPT_NAME" != "build" ]] && ensure_committed
```

**Step 4: Force interactive mode for design**

After the getopts block and before the autonomous/interactive branch, add:
```bash
# Design mode is always interactive
if [[ "$SCRIPT_NAME" == "design" ]]; then
    AUTONOMOUS=false
fi
```

**Step 5: Verify syntax**

Run: `bash -n src/scripts/loop.sh`
Expected: no output (clean syntax)

**Step 6: Commit**

```bash
git add src/scripts/loop.sh
git commit -m "feat(loop): add -d flag for design mode, disable auto-commit in build"
```

---

### Task 8: Update init.js to handle new file structure

**Files:**
- Modify: `src/lib/init.js`

**Step 1: Run existing integration tests to establish baseline**

Run: `npm test --prefix src -- --testPathPattern=integration`
Expected: PASS (all 14 tests)

**Step 2: Update CORE_FILES in init.js**

Add symlink for `PROMPT_design.md`:
```javascript
{ src: 'prompts/PROMPT_design.md', dest: 'loop/PROMPT_design.md' },
```

**Step 3: Update TEMPLATES in init.js**

Replace the single `PROMPT_skills.md` template with two:
```javascript
// Remove:
{ src: 'prompts/PROMPT_skills.md', dest: 'loop/PROMPT_skills.md' },
// Add:
{ src: 'prompts/PROMPT_skills_plan.md', dest: 'loop/PROMPT_skills_plan.md' },
{ src: 'prompts/PROMPT_skills_build.md', dest: 'loop/PROMPT_skills_build.md' },
```

**Step 4: Update integration tests**

In `src/lib/__tests__/integration.test.js`:

Update `EXPECTED_SYMLINKS` — add `'loop/PROMPT_design.md'`.

Update `EXPECTED_TEMPLATES` — replace `'loop/PROMPT_skills.md'` with `'loop/PROMPT_skills_plan.md'` and `'loop/PROMPT_skills_build.md'`.

Update the `templateSrcPath` mapping at the bottom — replace:
```javascript
'loop/PROMPT_skills.md': 'prompts/PROMPT_skills.md',
```
with:
```javascript
'loop/PROMPT_skills_plan.md': 'prompts/PROMPT_skills_plan.md',
'loop/PROMPT_skills_build.md': 'prompts/PROMPT_skills_build.md',
```

Update the `overwrites template files when force=true` test — change `PROMPT_skills.md` reference to `PROMPT_skills_plan.md`.

**Step 5: Run tests to verify**

Run: `npm test --prefix src -- --testPathPattern=integration`
Expected: PASS (all tests, count may change slightly)

**Step 6: Commit**

```bash
git add src/lib/init.js src/lib/__tests__/integration.test.js
git commit -m "feat(loop): update init to handle design prompt and split skill files"
```

---

### Task 9: Bump version and update documentation

**Files:**
- Modify: `src/package.json` (version bump)
- Modify: `CLAUDE.md` (update loop commands section)

**Step 1: Bump version in `src/package.json`**

Change `"version": "0.6.0"` to `"version": "0.7.0"` (minor bump — new command added).

**Step 2: Update CLAUDE.md**

In the Loop System section, add `loop design` to the commands list:
```bash
loop design             # Interactive brainstorming / design session
```

**Step 3: Run full test suite**

Run: `npm install --prefix src && npm test --prefix src`
Expected: PASS (all tests)

**Step 4: Commit**

```bash
git add src/package.json CLAUDE.md
git commit -m "chore(loop): bump to 0.7.0, update docs for design command"
```

---

## Findings & Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Prompt-only integration | Preserves prompt-driven architecture, easy to revert | 2026-02-24 |
| `loop design` as separate command | Brainstorming is interactive, doesn't fit autonomous mode | 2026-02-24 |
| Split skill files per phase | Plan doesn't need TDD, build doesn't need brainstorming | 2026-02-24 |
| Superpowers plan format | Granular tasks with atomic steps, test commands, expected output | 2026-02-24 |
| Disable auto-commit in build only | Trust subagent-driven-development to commit per task | 2026-02-24 |
| `spawnLoop` mode string over boolean | Cleaner than adding more booleans for each mode | 2026-02-24 |
| Minor version bump (0.7.0) | New command = new feature = minor bump | 2026-02-24 |
