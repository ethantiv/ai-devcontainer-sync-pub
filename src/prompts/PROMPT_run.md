0a. <autonomous_mode>You are running in a fully autonomous pipeline with no human available to respond. When information is ambiguous or missing, resolve it yourself using available context and choose the most reasonable option.</autonomous_mode>

0b. For each skill listed in @loop/PROMPT_skills_run.md, invoke the **Skill** tool. Load all skills in parallel.

0c. Read @docs/IDEA.md — this defines the scope.

1. **Plan**: Invoke **Skill** tool: `Skill(skill="superpowers:writing-plans")`. Read any design docs in @docs/ for architecture context.

2. **Build**: Invoke **Skill** tool: `Skill(skill="superpowers:subagent-driven-development")`.

3. **Update CLAUDE.md**: Invoke **Skill** tool: `Skill(skill="auto-revise-claude-md")`.

4. **Commit and push**: `git add -A && git commit` then `git push`.
