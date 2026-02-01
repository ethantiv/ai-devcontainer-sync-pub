---
description: Analyze autonomous agent loop logs with 5 parallel subagents
argument-hint: <logs-directory>
allowed-tools: Task, Read, Glob, Grep, Write, Bash(ls:*), Bash(wc:*), Bash(jq:*)
---

# Autonomous Agent Loop Analyzer

Analyze JSONL logs from autonomous agent loop sessions in the specified directory.

## Input Validation

Check logs directory: !`ls -la $1/*.jsonl 2>/dev/null | head -5 || echo "NO_LOGS_FOUND"`

If NO_LOGS_FOUND:
- Inform the user that no .jsonl files were found in the specified directory
- Suggest checking the path or providing a different directory
- EXIT without further processing

## Analysis Process

### Step 1: Gather Log Files

Use Glob to find all .jsonl files in `$1` directory.
Use Bash to get basic stats: `ls -la $1/*.jsonl | wc -l` for file count.

### Step 2: Launch 5 Parallel Subagents

<use_parallel_tool_calls>
You MUST call Task tool with ALL 5 subagents in a SINGLE tool_use block.
DO NOT call them sequentially. All 5 must be in ONE message.
</use_parallel_tool_calls>

Launch these 5 agents in PARALLEL using the Task tool:

1. **performance-analyzer** - Analyze token consumption and timing
   - Prompt: "Analyze performance in JSONL logs at $1. Calculate: total input/output tokens, cache hit rates, token efficiency per iteration, timing patterns, bottlenecks. Focus on usage.input_tokens, usage.output_tokens, cache_creation_input_tokens, cache_read_input_tokens fields. IMPORTANT: Calculate and return scores as percentages: token_efficiency_score (0-100%), timing_efficiency_score (0-100%), and overall_performance_score (average of both)."

2. **code-quality-analyzer** - Analyze generated code quality
   - Prompt: "Analyze code quality in JSONL logs at $1. Look for: code patterns in tool_use Write/Edit, error messages, TypeScript/lint failures, code complexity indicators, test quality (coverage, pass/fail ratio, test patterns). IMPORTANT: Calculate and return scores: first_attempt_success_rate (0-100%), error_fix_rate (0-100%), test_coverage_score (0-100%), and overall_code_quality_score (weighted average)."

3. **best-practices-analyzer** - Check adherence to best practices
   - Prompt: "Analyze best practices in JSONL logs at $1. Check: skill loading, parallel subagent usage, proper tool selection, CLAUDE.md adherence, anti-patterns, skills usage (frequency, appropriateness, missed opportunities), agent learning patterns (auto-revise-claude-md usage, CLAUDE.md updates). IMPORTANT: Calculate and return scores: skill_usage_score (0-100%), agent_learning_score (0-100%), tool_selection_score (0-100%), and overall_best_practices_score (weighted average)."

4. **process-analyzer** - Analyze process efficiency
   - Prompt: "Analyze process efficiency in JSONL logs at $1. Check: number of iterations, early exit triggers, task completion rate, blockers encountered, plan vs build ratio, hook execution and cleanup scripts. IMPORTANT: Calculate and return scores: task_completion_score (0-100%), hook_reliability_score (0-100%), and overall_process_score (weighted average)."

5. **tool-usage-analyzer** - Analyze tool usage patterns
   - Prompt: "Analyze tool usage in JSONL logs at $1. Track: which tools used most, tool call parallelism, failed tool calls, tool effectiveness, Read/Write/Edit/Bash patterns, browser testing (agent-browser/playwright), MCP server usage (mcp__* tools). IMPORTANT: Calculate and return scores: parallelism_score (0-100%), mcp_utilization_score (0-100%), browser_testing_score (0-100%), and overall_tool_effectiveness_score (weighted average)."

### Step 3: Synthesize and Compile Report

After all 5 agents complete, synthesize their findings:

1. **Read all agent outputs** - collect findings from each analyzer
2. **Identify patterns** - cross-reference findings across dimensions
3. **Prioritize insights** - rank by impact and actionability
4. **Write report** - compile into `report.md` in current working directory

## Report Format

Write the final report with this structure:

```markdown
# Loop Analysis Report

**Generated:** [timestamp]
**Analyzed:** [number] log files from `$1`
**Sessions:** [list session types: plan/build]

## Executive Summary

[2-3 paragraphs synthesizing key findings across all dimensions]

## Top 5 Strengths

1. [Strength with evidence]
2. ...

## Top 5 Weaknesses

1. [Weakness with impact]
2. ...

## Top 5 Improvement Recommendations

1. [Actionable recommendation]
2. ...

---

## Detailed Analysis

### Performance (Tokens & Timing)
[Findings from performance-analyzer]

### Code Quality
[Findings from code-quality-analyzer]

#### Test Quality
[Test quality findings from code-quality-analyzer: coverage, pass/fail ratio, test patterns]

### Best Practices Adherence
[Findings from best-practices-analyzer]

#### Skills Usage Analysis
[Skills usage findings from best-practices-analyzer: frequency, appropriateness, missed opportunities]

#### Agent Learning Analysis
[Agent learning findings from best-practices-analyzer: auto-revise-claude-md usage, CLAUDE.md updates, learning patterns]

### Process Efficiency
[Findings from process-analyzer]

#### Hook & Cleanup Analysis
[Hook findings from process-analyzer: hook events, cleanup scripts, reliability]

### Tool Usage Patterns
[Findings from tool-usage-analyzer]

#### Browser Testing Analysis
[Browser testing findings from tool-usage-analyzer: agent-browser/playwright usage, UI verification]

#### MCP Server Usage
[MCP server findings from tool-usage-analyzer: mcp__* tools usage, effectiveness]

---

## Quality Scorecard

Aggregate scores from all analyzers into a comprehensive scorecard:

| Category | Score | Assessment |
|----------|-------|------------|
| **Performance** | X% | ████████░░ |
| Token efficiency | X% | [details] |
| Timing efficiency | X% | [details] |
| **Process** | X% | ████████░░ |
| Task completion | X% | [details] |
| Hook reliability | X% | [details] |
| **Code Quality** | X% | ████████░░ |
| First-attempt success | X% | [details] |
| Test coverage | X% | [details] |
| Error resolution | X% | [details] |
| **Best Practices** | X% | ████████░░ |
| Skill usage | X% | [details] |
| Agent learning | X% | [details] |
| Tool selection | X% | [details] |
| **Tool Effectiveness** | X% | ████████░░ |
| Parallelism | X% | [details] |
| MCP utilization | X% | [details] |
| Browser testing | X% | [details] |

### Overall Score: X%
**Grade: A/B/C/D/F**

Grade scale: A (90-100%), B (80-89%), C (70-79%), D (60-69%), F (<60%)

Visual bar legend: █ = 10%, use filled blocks proportional to score

**Top Issues to Address:**
1. [Most impactful issue with lowest score]
2. [Second priority issue]
3. [Third priority issue]

---

## Appendix: Raw Metrics

| Metric | Value |
|--------|-------|
| Total input tokens | X |
| Total output tokens | X |
| Cache hit rate | X% |
| Total iterations | X |
| Early exits | X |
| Failed tool calls | X |
| Test executions | X |
| Test pass rate | X% |
| Skills invoked | X |
| MCP server calls | X |
| Browser tests | X |
| Hook events | X |
```

### Step 4: Output

After writing `report.md`, inform the user:
- Report saved to: `report.md`
- Brief summary of key findings (3-5 bullet points)
