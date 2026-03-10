0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context (files, git history, existing docs) and choose the most reasonable option. Commit to your decision and proceed without interruption.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0c. Read @docs/ROADMAP.md — this defines the scope for planning.

0d. Read @docs/plans/IMPLEMENTATION_PLAN.md (if it exists).

0e. Search @docs/plans/ for any design docs (YYYY-MM-DD-*-design.md). If found, read the most recent one — it provides architecture decisions and constraints.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map @src/ architecture and compare against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns.

2. **Create plan**: Invoke **Skill** tool: `Skill(skill="superpowers:writing-plans")`. Follow the writing-plans skill workflow to populate @docs/plans/IMPLEMENTATION_PLAN.md:
   - Fill **Header** (Goal, Architecture, Tech Stack) from ROADMAP and design doc
   - Create bite-sized tasks (2-5 min each) with exact file paths, code snippets, test commands, and expected output
   - Each task follows atomic steps: write failing test → verify fails → implement → verify passes → commit
   - Group tasks into phases — each phase has max 2-3 tasks (one phase = one build iteration)
   - Name phases by concrete deliverable, not category
   - Set initial phase **Status:** `pending` (all phases start pending)
   - Document findings in **Findings & Decisions** section

3. **Commit and push**: After updating the plan: `git add -A && git commit` then `git push`. The build loop reads the plan from the remote, so pushing is essential.

## Plan Format Requirements

<format_rationale>The loop's `check_completion()` function parses the plan file with regex. Deviating from this format breaks automated completion detection and early exit.</format_rationale>

### Phase headers with Status

Each phase needs a status line. Use lowercase for active states:

```markdown
## Phase 1: [Deliverable Name]

**Status:** pending
```

Valid status values: `pending` → `in_progress` → `complete` (lowercase for these three).

### Task checkboxes

Each task starts with a checkbox summary line directly under the task heading:

```markdown
### Task 1: [Component Name]

- [ ] Create foo module with bar functionality

**Files:**
...
```

### Completion marker

The build loop adds `**Status:** COMPLETE` (uppercase) automatically when all phases are done. Leave this to the automation.

### Example structure

```markdown
## Phase 1: Project Skeleton

**Status:** pending

### Task 1: Create directory structure

- [ ] Scaffold directory tree and base config files

**Files:**
- Create: `src/index.html`
...

### Task 2: CSS foundation

- [ ] Write reset.css and variables.css with design tokens

**Files:**
...

---

## Phase 2: Hero Section

**Status:** pending

### Task 3: Hero layout

- [ ] Build hero HTML and CSS with broken-grid positioning

...
```

## Important Rules

- This session produces a plan only — implementation happens in `loop build`.
- Before adding a task, search the code to confirm the functionality doesn't already exist.
- Scope comes from @docs/ROADMAP.md and @docs/specs/. Stay within that scope.
- Tasks should be granular enough to complete in 2-5 minutes each, with explicit test commands and expected output.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
