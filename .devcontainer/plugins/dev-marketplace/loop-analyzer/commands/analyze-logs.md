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
   - Prompt: "Analyze performance in JSONL logs at $1. Calculate: total input/output tokens, cache hit rates, token efficiency per iteration, timing patterns, bottlenecks. Focus on usage.input_tokens, usage.output_tokens, cache_creation_input_tokens, cache_read_input_tokens fields."

2. **code-quality-analyzer** - Analyze generated code quality
   - Prompt: "Analyze code quality in JSONL logs at $1. Look for: code patterns in tool_use Write/Edit, error messages, TypeScript/lint failures, code complexity indicators."

3. **best-practices-analyzer** - Check adherence to best practices
   - Prompt: "Analyze best practices in JSONL logs at $1. Check: skill loading, parallel subagent usage, proper tool selection, CLAUDE.md adherence, anti-patterns."

4. **process-analyzer** - Analyze process efficiency
   - Prompt: "Analyze process efficiency in JSONL logs at $1. Check: number of iterations, early exit triggers, task completion rate, blockers encountered, plan vs build ratio."

5. **tool-usage-analyzer** - Analyze tool usage patterns
   - Prompt: "Analyze tool usage in JSONL logs at $1. Track: which tools used most, tool call parallelism, failed tool calls, tool effectiveness, Read/Write/Edit/Bash patterns."

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

### Best Practices Adherence
[Findings from best-practices-analyzer]

### Process Efficiency
[Findings from process-analyzer]

### Tool Usage Patterns
[Findings from tool-usage-analyzer]

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
```

### Step 4: Output

After writing `report.md`, inform the user:
- Report saved to: `report.md`
- Brief summary of key findings (3-5 bullet points)
