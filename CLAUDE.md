# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Standalone DevContainer environment for multi-AI agent development. Configures Claude Code and Gemini CLI with custom slash commands and local plugin marketplace.

**This is a configuration-only repository** - no build, test, or lint commands exist.

## Architecture

```
.devcontainer/
├── devcontainer.json          # Container definition, features, extensions
├── setup-env.sh               # Main initialization script
├── configuration/
│   ├── settings.devcontainer.json
│   └── CLAUDE.md.memory       # Synced to ~/.claude/CLAUDE.md
├── commands/                  # Synced to ~/.claude/commands/
└── plugins/dev-marketplace/   # Local plugin marketplace
```

### Initialization Flow

`devcontainer.json` → `postCreateCommand` → `setup-env.sh`:
1. Configures SSH and GitHub authentication
2. Copies commands and settings to `~/.claude/`
3. Syncs local marketplace plugins

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub PAT with `repo`, `workflow` permissions |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git auth |

For Codespaces: add as repository secrets. For local: create `.devcontainer/.env`.

## Custom Slash Commands

Commands in `.devcontainer/commands/` are synced to `~/.claude/commands/`:

- `/code-review` - Launch parallel code review agents for bugs, security issues, and code quality
- `/git-message` - Generate short conventional commit messages
- `/polish-correction` - Polish language text correction

## Local Plugin Marketplace

`.devcontainer/plugins/dev-marketplace/` contains plugins for local development and testing. Currently includes `placeholder-plugin` as a template.

### Adding a Plugin

1. Create plugin directory in `.devcontainer/plugins/dev-marketplace/`
2. Add `.claude-plugin/plugin.json` with plugin metadata
3. Update `marketplace.json` with plugin entry
4. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

## Persistent Storage

Docker volumes preserve configuration across container rebuilds:
- `claude-code-config-${devcontainerId}` → `~/.claude`
- `gemini-cli-config-${devcontainerId}` → `~/.gemini`

## Key Commands

```bash
# Verify Claude configuration
claude mcp list
claude plugin marketplace list

# Re-sync configuration after changes
./.devcontainer/setup-env.sh

# GitHub Spec-Kit (manual init per project)
specify init --here --ai claude
```
