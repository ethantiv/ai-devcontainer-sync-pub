0a. For each skill listed in @loop/PROMPT_skills.md, invoke the **Skill** tool (e.g., `Skill(skill="agent-browser")`). Load all skills in parallel in a single message.

0b. Study @docs/plans/IMPLEMENTATION_PLAN.md - if Status: COMPLETE or no `- [ ]` → output "BUILD COMPLETE" and EXIT.

1. **Pick ONE PHASE and implement it.**

   a. Open @docs/plans/IMPLEMENTATION_PLAN.md and find the **first phase** with status `pending` or `in_progress` (not `complete`). This is your target for this iteration.

   b. **Explore**: Launch up to 10 `feature-dev:code-explorer` subagents via **Task** tool. Each should target a different aspect relevant to the phase (similar features, architecture of affected modules, testing patterns). After agents return, read all key files they identified to build deep understanding.

   c. **Design**: Launch up to 10 `feature-dev:code-architect` subagents via **Task** tool with the phase requirements and exploration findings. The agent designs: files to create/modify, component responsibilities, data flow, and build sequence. Pick the best approach autonomously.

   d. **Implement** all unchecked tasks within the phase following the architecture blueprint. Follow Test-Driven Development (Red-Green-Refactor): write a failing test first, implement until it passes, then refactor. Complete implementation - no placeholders or stubs. **ONE PHASE PER ITERATION.** After completing the current phase, proceed to steps 2-8 (test, update plan, simplify, review, validate, commit) and stop. Do NOT start the next phase — it will be handled in a fresh iteration with clean context.

2. **Ensure all tests pass.** Run the full test suite. You MUST have a passing test run before proceeding to step 3. If the project has no test framework set up, set one up first.

3. **Update the plan.** Update @docs/plans/IMPLEMENTATION_PLAN.md IMMEDIATELY — mark completed tasks `[x]`, update **Current Phase**, change phase **Status**. If the file exceeds 800 lines, trim completed content: remove `[x]` tasks, phases with status `complete`, resolved Issues rows. Keep pending tasks, active phases, Technical Decisions. Git history = full audit trail.

4. **Simplify code.** Use the **Task** tool to launch the `code-simplifier:code-simplifier` subagent to simplify and improve readability of code produced in this phase.

5. **Code review.** Launch up to 5 `feature-dev:code-reviewer` subagents via **Task** tool, each with a different focus: simplicity/DRY/elegance, bugs/functional correctness, project conventions/abstractionsm, security. Fix issues with confidence ≥ 75.

6. **Run validation.** Run the project's validation commands (typecheck, lint, tests) as defined in @CLAUDE.md. You MUST NOT skip this step. If validation fails, fix all errors before proceeding to step 7.

7. **Update CLAUDE.md.** Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")` to update `Operational Notes`.

8. **Commit and push.** Run `git add -A && git commit` with a descriptive message, then `git push`. Every iteration MUST end with a git push. Do NOT skip this step or defer it to a later iteration.

## Important Rules

- Document "why" in tests and implementations.
- Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
- Keep @docs/plans/IMPLEMENTATION_PLAN.md current and clean - future work depends on this to avoid duplicating efforts.
- On inconsistencies in @docs/ - update specifications directly.
- @CLAUDE.md = operational ONLY. Status/progress → @docs/plans/IMPLEMENTATION_PLAN.md.
- @src/lib = project's standard library, prefer consolidated, idiomatic implementations there over ad-hoc copies.
