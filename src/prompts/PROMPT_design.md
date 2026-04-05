0a. <interactive_mode>You are running in INTERACTIVE design mode. A human user IS available and IS waiting to answer your questions. You MUST NOT jump straight to writing a design document. The `brainstorming` skill drives the conversation — ask clarifying questions first, explore the problem space together with the user, and only write the design doc after reaching alignment. If the user's intent is ambiguous, ASK instead of assuming.</interactive_mode>

0b. For each skill listed in @loop/PROMPT_skills_design.md, invoke the **Skill** tool. Load all skills in parallel.

0c. Read @docs/IDEA.md — this defines the scope and goal.

0d. Read any existing design docs in @docs/ to avoid duplicating past work.

1. **Brainstorm**: Invoke **Skill** tool: `Skill(skill="brainstorming")` with the IDEA.md goal.

2. **Commit and push**: After the design doc is saved: `git add -A && git commit` then `git push`.

---

Design ends here. The user runs `loop run` separately to plan and implement.
Do NOT invoke writing-plans or any implementation skill.
