---
description: Generate short conventional commit messages without detailed descriptions
---

You are creating a concise git commit message based on the current changes.

First, use the Bash tool to gather information about the current git state by running these commands in parallel:
- `git status --short`
- `git diff --stat`
- `git diff --cached --stat`
- `git log --oneline -10`
- `git diff --cached` (or `git diff` if no files are staged)

Then analyze the output following these guidelines:

OBJECTIVE:
Generate ONLY a short, concise conventional commit message. No body, no bullet points, no explanations - just a single line commit message.

COMMIT CONVENTIONS:

**Types:** `feat` | `fix` | `docs` | `style` | `refactor` | `perf` | `test` | `build` | `ci` | `chore`

**Format:** `<type>(<scope>): <subject>` (max 50 chars, imperative mood)

**Analysis:**
1. Review recent commits to identify project conventions
2. Identify change type from modified files
3. Determine scope (component/area)
4. Write clear subject line following detected conventions

EXAMPLES:
- `feat(commands): add git message command`
- `fix(config): correct MCP server path`
- `refactor: simplify setup script`
- `docs: update README`

OUTPUT:
Provide ONLY the commit message - nothing else. No explanations, no commands, just the message text.