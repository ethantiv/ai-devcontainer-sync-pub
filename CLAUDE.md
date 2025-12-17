# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Standalone DevContainer environment for multi-AI agent development. Configures Claude Code and Gemini CLI with custom slash commands, specialized agents, local plugin marketplace, and GitHub Spec-Kit integration.

**This is a configuration-only repository** - no build, test, or lint commands exist.

## Architecture

```
.devcontainer/
├── devcontainer.json              # Container definition, features, extensions
├── setup-env.sh                   # Main initialization script
├── configuration/
│   ├── settings.devcontainer.json # Claude Code UI/behavior settings
│   └── CLAUDE.md.memory           # User memory sync file
├── commands/                      # Custom slash commands → ~/.claude/commands/
├── agents/                        # Specialized agents → ~/.claude/agents/
└── plugins/dev-marketplace/       # Local plugin marketplace
```

## Key Commands

```bash
# Plugin management
claude plugin marketplace list
claude plugin marketplace update

# GitHub Spec-Kit (requires manual init per project)
specify init --here --ai claude

# GitHub operations
gh pr create --title "feat: description" --body "PR description"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub PAT with `repo`, `workflow` permissions |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git auth |

For Codespaces: add as repository secrets. For local: create `.devcontainer/.env`.

## Custom Slash Commands

Commands in `.devcontainer/commands/` are synced to `~/.claude/commands/`:

- `/git-message` - Generate short conventional commit messages
- `/polish-correction` - Polish language text correction

**Note:** GitHub Spec-Kit provides additional `/speckit.*` commands after `specify init`.

## Custom Agents

Agents in `.devcontainer/agents/` are synced to `~/.claude/agents/`:

- **architecture-analyzer** - Analyzes project structure, dependencies, and architecture
- **code-explainer** - Explains code without making modifications

## Installed Plugins

### Local Marketplace (`.devcontainer/plugins/dev-marketplace/`)

Contains `placeholder-plugin` template. Create custom plugins here for local development and testing before publishing.

## Persistent Storage

Docker volumes preserve AI agent configuration across container rebuilds:
- `claude-code-config-${devcontainerId}` → `~/.claude`
- `gemini-cli-config-${devcontainerId}` → `~/.gemini`
- `google-gemini-auth-${devcontainerId}` → `~/.cache/google-vscode-extension/auth`

## Modifying Configuration

### Add Custom Command/Agent
1. Create `.md` file in `.devcontainer/commands/` or `.devcontainer/agents/`
2. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Plugin to Local Marketplace
1. Create plugin directory in `.devcontainer/plugins/dev-marketplace/`
2. Update `.devcontainer/plugins/dev-marketplace/.claude-plugin/marketplace.json`
3. Rebuild DevContainer or run `.devcontainer/setup-env.sh`