0a. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. Read @docs/ROADMAP.md — this defines the scope and goal.

0c. Read any existing design docs in @docs/plans/ to avoid duplicating past work.

1. **Explore**: Launch up to 15 `feature-dev:code-explorer` subagents via **Task** tool to map the codebase architecture. Focus on: existing patterns, module boundaries, testing conventions, tech stack. Summarize findings.

2. **Brainstorm**: Invoke **Skill** tool: `Skill(skill="superpowers:brainstorming")` with the ROADMAP goal and exploration findings. The brainstorming skill will save the design doc to `docs/plans/`.

3. **Commit and push**: After the design doc is saved: `git add -A && git commit` then `git push`.

## Important Rules

- This session produces a design doc only — implementation plans come from `loop plan`.
- This is an interactive session — ask questions, wait for answers, iterate.
- Scope comes from @docs/ROADMAP.md. Stay within that scope.
- After design is approved, the user runs `loop plan` separately to create the implementation plan.
