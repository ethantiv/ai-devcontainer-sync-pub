0a. For each skill listed in @loop/PROMPT_skills_plan.md, invoke the **Skill** tool. Load all skills in parallel in a single message.

0b. Read @docs/ROADMAP.md — this defines the scope and goal.

0c. Read any existing design docs in @docs/plans/ to avoid duplicating past work.

1. **Explore**: Launch up to 4 `feature-dev:code-explorer` subagents via **Task** tool to map the codebase architecture. Focus on: existing patterns, module boundaries, testing conventions, tech stack. Summarize findings.

2. **Brainstorm**: Invoke **Skill** tool: `Skill(skill="superpowers:brainstorming")` with the ROADMAP goal and exploration findings. Follow the brainstorming skill workflow exactly:
   - Ask clarifying questions (one at a time)
   - Propose 2-3 approaches with trade-offs
   - Present design section by section, get approval
   - The brainstorming skill will save the design doc to `docs/plans/`

3. **Commit and push**: After the design doc is saved: `git add -A && git commit` then `git push`.

## Important Rules

- DESIGN ONLY — do NOT implement anything, do NOT create implementation plans.
- This is an interactive session — ask questions, wait for answers, iterate.
- Scope is defined by @docs/ROADMAP.md. Do NOT invent features beyond what ROADMAP describes.
- The output is a design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`.
- After design is approved, the user runs `loop plan` separately to create the implementation plan.
