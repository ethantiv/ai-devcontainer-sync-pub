0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context and choose the most reasonable option.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_run.md, invoke the **Skill** tool. Load all skills in parallel.

0c. Read @docs/IDEA.md — this defines the scope.

1. **Plan**: Invoke **Skill** tool: `Skill(skill="writing-plans")`. Read any design docs in @docs/ for architecture context.

2. **Verify spec compliance**: Invoke **Skill** tool: `Skill(skill="spec-compliance-review")`. Pass `docs/IDEA.md` as the spec argument and the plan file just created in `docs/superpowers/plans/` as the target argument. Review the generated gap report — if any **Critical** or **Important** severity gaps are found, update the plan to address them before proceeding to the build step. Minor gaps can be ignored unless obviously relevant.

3. **Build**: Invoke **Skill** tool: `Skill(skill="subagent-driven-development")`.

4. **Update CLAUDE.md**: Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")`.

5. **Commit and push**: `git add -A && git commit` then `git push`.
