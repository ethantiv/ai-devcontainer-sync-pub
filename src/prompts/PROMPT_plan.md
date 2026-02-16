0a. For each skill listed in @loop/PROMPT_skills.md, invoke the **Skill** tool (e.g., `Skill(skill="agent-browser")`). Load all skills in parallel in a single message.

0b. If @docs/plans/IMPLEMENTATION_PLAN.md doesn't exist, copy @docs/plans/IMPLEMENTATION_PLAN_template.md to @docs/plans/IMPLEMENTATION_PLAN.md.

0c. Read @docs/ROADMAP.md — this defines the scope for planning.

0d. Read @docs/plans/IMPLEMENTATION_PLAN.md.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map @src/ architecture and compare against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns. Analyze findings and update @docs/plans/IMPLEMENTATION_PLAN.md:
   - Fill **Goal** with project objective from @docs/ROADMAP.md
   - Populate tasks in **Phases** — each phase MUST have 2-3 tasks maximum (one phase = one build iteration). Split large features into multiple sequential phases. Name each phase by its concrete deliverable, not by category.
   - Document findings in **Findings & Decisions** section
   - Update phase **Status**: pending → in_progress → complete

2. **Commit and push**: After updating the plan: `git add -A && git commit` then `git push`. You MUST commit your plan updates before the session ends.

## Important Rules

- PLAN ONLY - do NOT implement anything.
- Before adding task: search code to confirm it doesn't exist.
- Scope is defined by @docs/ROADMAP.md and @docs/specs/. Do NOT invent features beyond what ROADMAP.md describes. When essential ROADMAP.md requirements are planned don't add new tasks.
- Consider missing essential elements and plan accordingly. If an essential element is missing, search first to confirm it doesn't exist, then only if needed author the specification at docs/specs/FILENAME.md. If you create a new element then document the plan to implement it in @IMPLEMENTATION_PLAN.md using a subagent.
- @src/lib = project's standard library, prefer consolidated, idiomatic implementations there over ad-hoc copies.
