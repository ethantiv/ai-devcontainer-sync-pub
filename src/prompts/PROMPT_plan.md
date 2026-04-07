0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context and choose the most reasonable option.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_run.md, invoke the **Skill** tool. Load all skills in parallel.

1. **Plan**: Invoke **Skill** tool: `Skill(skill="writing-plans")`. Read any design docs in @docs/ for architecture context.

2. **Verify spec compliance**: Invoke **Skill** tool: `Skill(skill="spec-compliance-review")`. Pass the design doc from `docs/superpowers/specs/` as the spec argument and the plan file just created in `docs/superpowers/plans/` as the target argument. Review the generated gap report — if any **Critical** or **Important** severity gaps are found, update the plan to address them before proceeding. Minor gaps can be ignored unless obviously relevant.

3. **Commit and push**: `git add -A && git commit` then `git push`. Commit message MUST be written in English.

---

Plan ends here. Agent runs `loop run --build` separately to apply the plan.
Do not take any implementation steps.