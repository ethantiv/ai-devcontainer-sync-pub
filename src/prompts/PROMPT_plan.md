0a. For each skill listed in @loop/PROMPT_skills.md, invoke the **Skill** tool (e.g., `Skill(skill="agent-browser")`). Load all skills in parallel in a single message.

0b. If @docs/plans/IMPLEMENTATION_PLAN.md doesn't exist, copy @docs/plans/IMPLEMENTATION_PLAN_template.md to @docs/plans/IMPLEMENTATION_PLAN.md.

0c. Read @docs/plans/IMPLEMENTATION_PLAN.md.

0d. Study @docs/ with up to 10 parallel **Haiku** subagents to learn specifications.

0e. Study @src/ with up to 10 parallel **Haiku** subagents to understand application source code and shared utilities in @src/lib/.

0f. For reference: source code is in @src/.

1. Use up to 10 parallel **Haiku** subagents to compare @src/ against @docs/. Look for: TODO, placeholders, minimal implementations, missing tests, skipped/flaky tests, inconsistent patterns. Use **Opus** to analyze findings and update @docs/plans/IMPLEMENTATION_PLAN.md:
   - Fill **Goal** with project objective from @docs/ROADMAP.md
   - Populate tasks in **Phases** (number of phases depends on task scope)
   - Document findings in **Findings & Decisions** section
   - Update phase **Status**: pending → in_progress → complete

2. After updating plan: `git add -A && git commit` then `git push`.

## Important Rules

- PLAN ONLY - do NOT implement anything.
- Before adding task: search code to confirm it doesn't exist.
- Scope is defined by @docs/ROADMAP.md and @docs/specs/. Do NOT invent features beyond what ROADMAP.md describes. When essential ROADMAP.md requirements are planned don't add new tasks.
- Consider missing essential elements and plan accordingly. If an essential element is missing, search first to confirm it doesn't exist, then only if needed author the specification at docs/specs/FILENAME.md. If you create a new element then document the plan to implement it in @IMPLEMENTATION_PLAN.md using a subagent.
- @src/lib = project's standard library, prefer consolidated, idiomatic implementations there over ad-hoc copies.
