0a. For each skill listed in @loop/PROMPT_skills_design.md, invoke the **Skill** tool. Load all skills in parallel.

0b. Read @docs/IDEA.md — this defines the scope and goal.

0c. Read any existing design docs in @docs/ to avoid duplicating past work.

1. **Brainstorm**: Invoke **Skill** tool: `Skill(skill="brainstorming")` with the IDEA.md goal.

2. **Commit and push**: After the design doc is saved: `git add -A && git commit` then `git push`.

---

Design ends here. The user runs `loop run` separately to plan and implement.
Do NOT invoke writing-plans or any implementation skill.
