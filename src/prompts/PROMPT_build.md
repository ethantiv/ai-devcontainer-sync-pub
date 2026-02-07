0a. Load skills: @loop/PROMPT_skills.md

0b. Study @docs/ with up to 10 parallel **Haiku** subagents to learn specifications.

0c. Study @docs/plans/IMPLEMENTATION_PLAN.md - if Status: COMPLETE or no `- [ ]` → output "BUILD COMPLETE" and EXIT.

0d. For reference: source code is in @src/.

1. Your task is to implement functionality per the specifications using parallel subagents. Follow @docs/plans/IMPLEMENTATION_PLAN.md and choose the most important item to address. Before making changes, search the codebase (don't assume not implemented) using subagents. You may use up to 10 parallel **Haiku** subagents for searches/reads. Use **Opus** subagents when complex reasoning is needed (debugging, architectural decisions).

2. Test-Driven Development (following the "Red-Green-Refactor" cycle): Write failing test first → implement → run tests → must pass before step 3. Complete implementation - no placeholders or stubs.

3. After implementing:
   - Update @docs/plans/IMPLEMENTATION_PLAN.md IMMEDIATELY (mark tasks, update **Current Phase**, change phase **Status**).
   - If @docs/plans/IMPLEMENTATION_PLAN.md exceeds 800 lines, trim completed content. Remove: completed tasks `[x]`, phases with status `complete`, resolved Issues rows. Keep: pending tasks `[ ]`, active phases, Technical Decisions. Git history = full audit trail.
   - Run validation (typecheck, lint).
   - If validation fails, fix before proceeding.
   - Load skill `auto-revise-claude-md` to update `Operational Notes`.
   - After completing everything: `git add -A && git commit` then `git push`.

## Important Rules

- Document "why" in tests and implementations.
- Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
- Keep @docs/plans/IMPLEMENTATION_PLAN.md current and clean - future work depends on this to avoid duplicating efforts.
- On inconsistencies in @docs/ - use **Opus** subagent to update specifications.
- @CLAUDE.md = operational ONLY. Status/progress → @docs/plans/IMPLEMENTATION_PLAN.md.
- @src/lib = project's standard library, prefer consolidated, idiomatic implementations there over ad-hoc copies.
