0a. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. Read @docs/ROADMAP.md — this defines the scope for planning.

0c. Read @docs/plans/IMPLEMENTATION_PLAN.md (if it exists).

0d. Search @docs/plans/ for any design docs (YYYY-MM-DD-*-design.md). If found, read the most recent one — it provides architecture decisions and constraints.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map @src/ architecture and compare against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns.

2. **Create plan**: Invoke **Skill** tool: `Skill(skill="superpowers:writing-plans")`. Follow the writing-plans skill workflow to populate @docs/plans/IMPLEMENTATION_PLAN.md:
   - Fill **Header** (Goal, Architecture, Tech Stack) from ROADMAP and design doc
   - Create bite-sized tasks (2-5 min each) with exact file paths, code snippets, test commands, and expected output
   - Each task follows atomic steps: write failing test → verify fails → implement → verify passes → commit
   - Group tasks into phases — each phase has max 2-3 tasks (one phase = one build iteration)
   - Name phases by concrete deliverable, not category
   - Set initial phase **Status:** `pending` (all phases start pending)
   - Document findings in **Findings & Decisions** section

3. **Commit and push**: After updating the plan: `git add -A && git commit` then `git push`. You MUST commit your plan updates before the session ends.

## Plan Format Requirements (CRITICAL for loop automation)

The loop's `check_completion()` function parses the plan file. Your plan MUST follow this format exactly:

### Phase headers with Status

Each phase MUST have a status line. Use **lowercase** for active states:

```markdown
## Phase 1: [Deliverable Name]

**Status:** pending
```

Valid status values: `pending` → `in_progress` → `complete` (lowercase for these three).

### Task checkboxes

Each task MUST have a checkbox summary line as the FIRST line under the task heading:

```markdown
### Task 1: [Component Name]

- [ ] Create foo module with bar functionality

**Files:**
...
```

### Completion marker

Do NOT add a completion marker yourself. The build loop adds `**Status:** COMPLETE` (uppercase) when all phases are done.

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

- PLAN ONLY — do NOT implement anything.
- Before adding a task: search code to confirm it doesn't already exist.
- Scope is defined by @docs/ROADMAP.md and @docs/specs/. Do NOT invent features beyond what ROADMAP describes.
- Tasks must be granular enough to complete in 2-5 minutes each, with explicit test commands and expected output.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
