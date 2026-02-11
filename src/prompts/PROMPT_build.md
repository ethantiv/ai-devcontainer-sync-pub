0a. For each skill listed in @loop/PROMPT_skills.md, invoke the **Skill** tool (e.g., `Skill(skill="agent-browser")`). Load all skills in parallel in a single message.

0b. Study @docs/ with up to 10 parallel **Haiku** subagents to learn specifications.

0c. Study @docs/plans/IMPLEMENTATION_PLAN.md - if Status: COMPLETE or no `- [ ]` → output "BUILD COMPLETE" and EXIT.

0d. For reference: source code is in @src/.

1. **Pick ONE PHASE and implement it.** Open @docs/plans/IMPLEMENTATION_PLAN.md and find the **first phase** with status `pending` or `in_progress` (not `complete`). Implement **all unchecked tasks** within that single phase. Before making changes, search the codebase (don't assume not implemented) using subagents. You may use up to 10 parallel **Haiku** subagents for searches/reads. Use **Opus** subagents when complex reasoning is needed (debugging, architectural decisions). Complete implementation - no placeholders or stubs. **ONE PHASE PER ITERATION.** After completing the current phase, proceed to steps 2-6 (test, update plan, validate, commit) and stop. Do NOT start the next phase — it will be handled in a fresh iteration with clean context.

2. **Test-Driven Development.** Follow the Red-Green-Refactor cycle: write a failing test first, implement until it passes, then refactor. You MUST have a passing test run before proceeding to step 3. If the project has no test framework set up, set one up first.

3. **Update the plan.** Update @docs/plans/IMPLEMENTATION_PLAN.md IMMEDIATELY — mark completed tasks `[x]`, update **Current Phase**, change phase **Status**. If the file exceeds 800 lines, trim completed content: remove `[x]` tasks, phases with status `complete`, resolved Issues rows. Keep pending tasks, active phases, Technical Decisions. Git history = full audit trail.

4. **Run validation.** Run the project's validation commands (typecheck, lint, tests) as defined in @CLAUDE.md. You MUST NOT skip this step. If validation fails, fix all errors before proceeding to step 5.

5. **Update CLAUDE.md.** Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")` to update `Operational Notes`.

6. **Commit and push.** Run `git add -A && git commit` with a descriptive message, then `git push`. Every iteration MUST end with a git push. Do NOT skip this step or defer it to a later iteration.

## Important Rules

- Document "why" in tests and implementations.
- Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
- Keep @docs/plans/IMPLEMENTATION_PLAN.md current and clean - future work depends on this to avoid duplicating efforts.
- On inconsistencies in @docs/ - use **Opus** subagent to update specifications.
- @CLAUDE.md = operational ONLY. Status/progress → @docs/plans/IMPLEMENTATION_PLAN.md.
- @src/lib = project's standard library, prefer consolidated, idiomatic implementations there over ad-hoc copies.
