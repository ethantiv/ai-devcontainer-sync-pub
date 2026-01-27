---
description: Generate or update ROADMAP.json with completed features and future proposals
---

# ROADMAP.json Generator

<context>
You are managing a project roadmap file that tracks completed features and proposes future development directions. The ROADMAP.json file serves as a living document for project planning and progress visibility.

This command operates in two modes:
- **CREATE**: When ROADMAP.json doesn't exist, analyze the project and generate initial proposals
- **UPDATE**: When ROADMAP.json exists, optionally add a completed feature and refresh proposals
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
First, check if ROADMAP.json exists in the current working directory:

```bash
test -f ROADMAP.json && echo "EXISTS" || echo "NOT_EXISTS"
```

- If **NOT_EXISTS** → Execute CREATE flow
- If **EXISTS** → Execute UPDATE flow
</flow_detection>

<create_flow>
When creating a new ROADMAP.json:

1. Analyze the project using steps from `<project_analysis>`
2. Generate 3-5 proposals across different time horizons
3. Create ROADMAP.json with empty `completedFeatures` array
4. Display summary of generated proposals
</create_flow>

<update_flow>
When updating an existing ROADMAP.json:

1. Read the current ROADMAP.json file
2. Ask the user: "Would you like to mark a feature as completed? If yes, describe the feature. If no, just press Enter."
3. If user provides a feature description:
   - Generate a unique ID (increment from highest existing ID, or start at "001")
   - Add to `completedFeatures` with current ISO timestamp
   - Remove any related proposal if it matches the completed feature
4. Re-analyze the project to refresh proposals based on current state
5. Update proposals while preserving any that are still relevant
6. Save updated ROADMAP.json
</update_flow>

<proposal_generation>
Generate 3-5 proposals distributed across categories:

| Category | Timeframe | Characteristics |
|----------|-----------|-----------------|
| `short-term` | 1-2 weeks | Quick wins, bug fixes, small improvements |
| `medium-term` | 1-2 months | New features, integrations, moderate effort |
| `long-term` | 3-6 months | Major features, architecture changes, strategic initiatives |

**Guidelines:**
- Each proposal should be specific and actionable
- Align with project's existing direction and technology stack
- Consider dependencies and prerequisites
- Avoid vague or overly broad suggestions
- Base proposals on actual project analysis, not generic ideas
</proposal_generation>

<output_format>
The ROADMAP.json must follow this exact structure:

```json
{
  "completedFeatures": [
    {
      "id": "001",
      "title": "Short descriptive title",
      "description": "Detailed description of what was implemented",
      "completedAt": "2024-01-15T10:30:00Z"
    }
  ],
  "proposals": [
    {
      "category": "short-term",
      "title": "Proposal title",
      "description": "Clear description of what should be done and why"
    },
    {
      "category": "medium-term",
      "title": "Another proposal",
      "description": "Description with context and expected benefits"
    },
    {
      "category": "long-term",
      "title": "Strategic initiative",
      "description": "Long-term vision with rationale"
    }
  ]
}
```

**Validation rules:**
- `id` must be zero-padded 3-digit string ("001", "002", etc.)
- `category` must be exactly: "short-term", "medium-term", or "long-term"
- `completedAt` must be ISO 8601 format with timezone
- All fields are required, no empty strings
</output_format>

<execution>
Execute in this order:

1. **Detect mode**: Check if ROADMAP.json exists
2. **Basic analysis**: Gather context from package.json, README, git log, directory structure
3. **Deep exploration**: Launch 2-3 Explore agents in parallel to analyze architecture, features, and tech stack
4. **Synthesize findings**: Combine agent results into actionable insights
5. **Execute appropriate flow**:
   - CREATE: Generate fresh proposals based on exploration, create file
   - UPDATE: Ask about completed feature, refresh proposals using exploration insights, update file
6. **Write ROADMAP.json**: Use the Write tool to save the file
7. **Display summary**: Show what was created/updated in a concise format

After completion, display:
- Mode executed (CREATE or UPDATE)
- Number of completed features (total)
- Number of proposals by category
- File path where ROADMAP.json was saved
</execution>
