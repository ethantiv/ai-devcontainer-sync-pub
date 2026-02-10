---
description: Generate or update docs/ROADMAP.md with future proposals
---

# docs/ROADMAP.md Generator

<context>
You are managing a project roadmap file that proposes future development directions. The docs/ROADMAP.md file serves as a living document for project planning.

This command operates in two modes:
- **CREATE**: When docs/ROADMAP.md doesn't exist, analyze the project and generate initial proposals
- **UPDATE**: When docs/ROADMAP.md exists, remove implemented proposals and refresh remaining ones
</context>

<project_analysis>
Before generating or updating the roadmap, gather basic project context:

1. **Detect project manifests** - Search recursively for project definition files:
   ```bash
   # Find all manifest files (exclude node_modules, vendor, .git)
   find . -type f \( \
     -name "package.json" -o \
     -name "pyproject.toml" -o \
     -name "Cargo.toml" -o \
     -name "go.mod" -o \
     -name "pom.xml" \
   \) -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/vendor/*" 2>/dev/null
   ```
   - For each found manifest, extract project name, description, and dependencies
   - If multiple manifests found (monorepo), analyze the structure and relationships

2. **Read README.md** - Check both root and subdirectory READMEs for context

3. **Review git log** - `git log --oneline -20` to see recent development activity

4. **Scan directory structure** - `ls -la` and key subdirectories to understand architecture

This provides baseline context before deep codebase exploration.
</project_analysis>

<codebase_exploration>
For comprehensive project understanding, launch 2-3 Explore agents in parallel using the Task tool with `subagent_type="Explore"`.

**Agent 1 - Architecture & Structure:**
- Prompt: "Map the project architecture, main modules, and design patterns. Identify key abstractions, entry points, and how components interact. Focus on understanding the overall structure and code organization."
- Thoroughness: "medium"

**Agent 2 - Features & Development:**
- Prompt: "Analyze existing features and recent development activity. Identify completed work, work in progress, and areas needing attention. Look for TODOs, FIXMEs, and partially implemented features."
- Thoroughness: "medium"

**Agent 3 - Tech Stack & Integrations (for larger projects):**
- Prompt: "Examine dependencies, external integrations, and technology choices. Identify upgrade opportunities, deprecated packages, or technical debt."
- Thoroughness: "quick"

**Execution guidelines:**
- Launch all agents in a single message with multiple Task tool calls
- For small/config-only projects, 2 agents may be sufficient
- After agents complete, synthesize findings to inform proposals

The insights from exploration should directly inform the proposals - suggesting improvements based on actual codebase state rather than generic ideas.
</codebase_exploration>

<flow_detection>
First, check if docs/ROADMAP.md exists:

```bash
test -f docs/ROADMAP.md && echo "EXISTS" || echo "NOT_EXISTS"
```

- If **NOT_EXISTS** → Execute CREATE flow
- If **EXISTS** → Execute UPDATE flow
</flow_detection>

<create_flow>
When creating a new docs/ROADMAP.md:

1. Analyze the project using steps from `<project_analysis>`
2. Generate 3-5 proposals across different priorities
3. Create docs/ROADMAP.md with proposals
4. Display summary of generated proposals
</create_flow>

<update_flow>
When updating an existing docs/ROADMAP.md:

1. Read the current docs/ROADMAP.md file
2. Ask the user: "Which proposals have been implemented? List them, or press Enter to skip."
3. If user identifies implemented proposals:
   - Delete those proposals from docs/ROADMAP.md
4. Re-analyze the project to refresh proposals based on current state
5. Update proposals while preserving any that are still relevant
6. Save updated docs/ROADMAP.md
</update_flow>

<proposal_generation>
Generate 3-5 proposals distributed across priorities:

| Priority | Meaning | Characteristics |
|----------|---------|-----------------|
| `P1` | Critical | Blockers, critical bugs, security issues, must-have features |
| `P2` | Important | Significant improvements, new features, performance gains |
| `P3` | Nice to Have | Polish, minor improvements, ideas for future consideration |

**Proposal ordering — user value first:**
- Prioritize proposals that directly improve the **user experience**: quality of life improvements, workflow enhancements, new useful features, better defaults, reduced friction
- Then propose **new capabilities** that extend what the project can do
- Place **purely technical changes** (refactoring, tech debt, dependency upgrades, internal restructuring) last within each priority level
- A user-facing bug fix or UX improvement at P2 should appear before a refactoring item at P2

**Guidelines:**
- Each proposal should be specific and actionable
- Align with project's existing direction and technology stack
- Consider dependencies and prerequisites
- Avoid vague or overly broad suggestions
- Base proposals on actual project analysis, not generic ideas
- When in doubt whether something is user-facing or technical, ask: "Would a user notice this change?" If yes, rank it higher
</proposal_generation>

<output_format>
The docs/ROADMAP.md must follow this exact structure:

```markdown
# Roadmap

## Proposals

### P1 - Critical

#### {title}
{description}

### P2 - Important

#### {title}
{description}

### P3 - Nice to Have

#### {title}
{description}
```

**Validation rules:**
- Proposals grouped by priority with H3 headers (P1, P2, P3)
- Each proposal has H4 title followed by description paragraph
- Empty priority sections may be omitted
</output_format>

<execution>
Execute in this order:

1. **Detect mode**: Check if docs/ROADMAP.md exists
2. **Basic analysis**: Gather context from package.json, README, git log, directory structure
3. **Deep exploration**: Launch 2-3 Explore agents in parallel to analyze architecture, features, and tech stack
4. **Synthesize findings**: Combine agent results into actionable insights
5. **Execute appropriate flow**:
   - CREATE: Generate fresh proposals based on exploration, create file
   - UPDATE: Ask about implemented proposals, remove them, refresh remaining proposals using exploration insights, update file
6. **Write docs/ROADMAP.md**: Use the Write tool to save the file
7. **Display summary**: Show what was created/updated in a concise format

After completion, display:
- Mode executed (CREATE or UPDATE)
- Number of removed proposals (UPDATE mode only)
- Number of proposals by priority
- File path where docs/ROADMAP.md was saved
</execution>
