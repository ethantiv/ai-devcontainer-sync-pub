0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context (files, git history, existing docs) and choose the most reasonable option. Commit to your decision and proceed without interruption.</autonomous_mode>

0b. Load all skills listed in @loop/PROMPT_skills_plan.md.

0c. Read @docs/ROADMAP.md — this defines the scope for planning.

0d. Read @docs/plans/IMPLEMENTATION_PLAN.md (if it exists).

0e. Search @docs/plans/ for any design docs (YYYY-MM-DD-*-design.md). If found, read the most recent one — it provides architecture decisions and constraints.

1. **Explore**: Launch up to 15 `feature-dev:code-explorer` subagents to map @src/ architecture and compare against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns.

2. **Create plan**: Load `superpowers:writing-plans`. The plan will be saved to @docs/plans/IMPLEMENTATION_PLAN.md.

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

- Before adding a task, search the code to confirm the functionality doesn't already exist.
- Scope comes from @docs/ROADMAP.md and @docs/specs/. Stay within that scope.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
