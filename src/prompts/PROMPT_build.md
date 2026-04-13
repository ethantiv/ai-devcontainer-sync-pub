0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context and choose the most reasonable option.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_run.md, invoke the **Skill** tool. Load all skills in parallel.

1. **Build**: Find the current plan in `docs/superpowers/plans/` (most recent .md file). Invoke **Skill** tool: `Skill(skill="subagent-driven-development")`.

2. **Simplify**: Invoke **Skill** tool: `Skill(skill="simplify")`.

3. **Update CLAUDE.md**: Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")`.

4. **Commit and push**: `git add -A && git commit` then `git push`. Commit message MUST be written in English.
