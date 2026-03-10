0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context (files, git history, existing docs) and choose the most reasonable option. Commit to your decision and proceed without interruption.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_build.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0c. Study @docs/plans/IMPLEMENTATION_PLAN.md — check completion:
   - If `**Status:** COMPLETE` (uppercase) exists at document level → output "BUILD COMPLETE" and EXIT.
   - If no `- [ ]` unchecked tasks remain AND no phases with `**Status:** pending` or `**Status:** in_progress` → output "BUILD COMPLETE" and EXIT.
   - Otherwise → continue to step 1.

1. **Pick ONE PHASE and execute it.**

   a. Open @docs/plans/IMPLEMENTATION_PLAN.md and find the **first phase** with `**Status:** pending` or `**Status:** in_progress` (not `complete`). This is your target for this iteration.

   b. **Execute with subagent-driven-development**: Invoke **Skill** tool: `Skill(skill="superpowers:subagent-driven-development")`. Follow the skill workflow exactly for each task in the phase:
      - Dispatch implementer subagent with full task text and codebase context
      - Implementer follows `superpowers:test-driven-development` (Red-Green-Refactor): write failing test → verify fails → implement → verify passes → refactor
      - On errors or unexpected behavior: use `superpowers:systematic-debugging` to diagnose root cause before attempting fixes
      - For independent failures across different subsystems: use `superpowers:dispatching-parallel-agents`
      - After implementation: dispatch spec compliance reviewer subagent (does code match task spec?)
      - After spec review: dispatch code quality reviewer subagent
      - Each task ends with a commit from the implementer subagent

   c. Complete one phase per iteration. After finishing the current phase, proceed to steps 2-5 and stop — the next phase runs in a fresh iteration with clean context.

2. **Update the plan** in @docs/plans/IMPLEMENTATION_PLAN.md:
   - Mark completed task checkboxes: `- [ ]` → `- [x]`
   - Change current phase status: `**Status:** pending` → `**Status:** complete` (lowercase)
   - If ALL phases are now `complete`: add `**Status:** COMPLETE` (UPPERCASE) at the top of the document, below the header
   - If the file exceeds 800 lines, trim completed content: remove `[x]` tasks, phases with status `complete`. Keep pending tasks, active phases, Findings & Decisions. Git history = full audit trail.

3. **Verification**: Invoke **Skill** tool: `Skill(skill="superpowers:verification-before-completion")`. Run the project's validation commands (typecheck, lint, tests) as defined in @CLAUDE.md. Fix all errors before proceeding — the next iteration depends on a clean state.

4. **Update CLAUDE.md**: Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")` to update Operational Notes.

5. **Commit and push**: Run `git add -A && git commit` with a descriptive message, then `git push`. Each iteration ends with a push so the next iteration starts from the latest remote state.

## Important Rules

- Document "why" in tests and implementations.
- Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
- Keep @docs/plans/IMPLEMENTATION_PLAN.md current — future iterations depend on this.
- On inconsistencies in @docs/ — update specifications directly.
- @CLAUDE.md = operational ONLY. Status/progress → @docs/plans/IMPLEMENTATION_PLAN.md.
- @src/lib = project's standard library, prefer consolidated implementations there over ad-hoc copies.
- Subagents handle commits per task. The loop orchestrator does NOT auto-commit in build mode.
