---
description: Launch parallel code review agents to find bugs, security issues, and code quality problems
argument-hint: [files/dirs] or empty for staged changes
---

# Code Review

<context>
You are performing a systematic code review. High-quality code reviews catch bugs early, improve security, and maintain code quality. Your review ensures code is simple, DRY, elegant, readable, and functionally correct before it reaches production.
</context>

<scope_detection>
Determine review scope based on arguments:
1. If specific files/directories provided as arguments: review those paths
2. If no arguments: review staged changes (`git diff --cached`)
3. If no staged changes: review unstaged changes (`git diff`)
4. If no changes at all: inform user there is nothing to review
</scope_detection>

<parallel_agent_execution>
Launch 3 code-reviewer agents in parallel. Each agent should focus on a distinct aspect to maximize coverage:

Agent 1 - Code Quality Focus:
- Simplicity and readability
- DRY violations and code duplication
- Function/method length and complexity
- Naming conventions and clarity

Agent 2 - Correctness & Security Focus:
- Logic errors and edge cases
- Security vulnerabilities (OWASP top 10)
- Error handling gaps
- Race conditions and concurrency issues

Agent 3 - Architecture & Conventions Focus:
- Consistency with project patterns and abstractions
- API design and interface contracts
- Test coverage gaps
- Documentation accuracy

If you intend to call multiple agents and there are no dependencies between the calls, make all calls in parallel to maximize efficiency.
</parallel_agent_execution>

<consolidation>
After agents complete, consolidate findings:
1. Deduplicate overlapping issues found by multiple agents
2. Group issues by severity (agents provide their own severity ratings)
3. Prioritize issues that multiple agents flagged independently
4. Create a clear, structured summary
</consolidation>

<user_interaction>
Present consolidated findings to user with clear options:
- Which issues to fix immediately
- Which to defer for later
- Which to dismiss as acceptable

Wait for user decision before taking any action. Do not automatically fix issues without explicit approval.
</user_interaction>

<output_format>
Structure your final report as:
1. **Scope**: What was reviewed (files, lines changed)
2. **Summary**: Brief overview of findings
3. **Issues by Severity**: Grouped list with file:line references
4. **Recommendations**: Suggested action for each issue category
</output_format>