# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Standalone DevContainer environment for multi-AI agent development. Configures Claude Code and Gemini CLI with shared MCP servers, custom slash commands, specialized agents, and GitHub Spec-Kit integration.

**This is a configuration-only repository** - no build, test, or lint commands exist.

## Architecture

```
.devcontainer/
├── devcontainer.json              # Container definition, features, extensions
├── setup-env.sh                   # Main initialization script
├── configuration/
│   ├── mcp-servers.json           # Shared MCP server definitions (Claude + Gemini)
│   ├── settings.devcontainer.json # Claude Code UI/behavior settings
│   └── CLAUDE.md.memory           # User memory sync file
├── commands/                      # Custom slash commands → ~/.claude/commands/
├── agents/                        # Specialized agents → ~/.claude/agents/
└── plugins/dev-marketplace/       # Local plugin marketplace (priority over official)
```

## Key Commands

```bash
# Verify MCP configuration
claude mcp list
gemini mcp list

# Plugin management
claude plugin marketplace list
claude plugin marketplace update

# GitHub Spec-Kit (requires manual init per project)
specify init --here --ai claude

# GitHub operations (use gh CLI, not MCP)
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

### Anthropic Official Marketplace

Configured in `setup-env.sh` (`PLUGINS` array):

1. **commit-commands** - `/commit`, `/commit-push-pr`
2. **pr-review-toolkit** - 6 specialized review agents
3. **feature-dev** - 7-phase feature development workflow
4. **plugin-dev** - Plugin development toolkit
5. **frontend-design** - Production-grade UI generation
6. **agent-sdk-dev** - Claude Agent SDK development

## MCP Servers

Defined in `.devcontainer/configuration/mcp-servers.json`, synced to both Claude and Gemini:

- **aws-docs** - AWS documentation search and recommendations
- **aws-terraform** - Terraform/Terragrunt execution, Checkov scanning
- **context7** - Library documentation from public registries
- **terraform** - Terraform Registry (modules, providers, policies)

**GitHub operations use `gh` CLI, not MCP servers.**

## Persistent Storage

Docker volumes preserve AI agent configuration across container rebuilds:
- `claude-code-config-${devcontainerId}` → `~/.claude`
- `gemini-cli-config-${devcontainerId}` → `~/.gemini`
- `google-gemini-auth-${devcontainerId}` → `~/.cache/google-vscode-extension/auth`

## Modifying Configuration

### Add MCP Server
1. Edit `.devcontainer/configuration/mcp-servers.json`
2. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Custom Command/Agent
1. Create `.md` file in `.devcontainer/commands/` or `.devcontainer/agents/`
2. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Plugin to Local Marketplace
1. Create plugin directory in `.devcontainer/plugins/dev-marketplace/`
2. Update `.devcontainer/plugins/dev-marketplace/.claude-plugin/marketplace.json`
3. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Plugin from Anthropic Marketplace
Edit `PLUGINS` array in `.devcontainer/setup-env.sh` (lines 339-346)