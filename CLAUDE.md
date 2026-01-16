# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Standalone DevContainer environment for multi-AI agent development. Configures Claude Code and Gemini CLI with custom slash commands, MCP servers, and local plugin marketplace.

**This is a configuration-only repository** - no build, test, or lint commands exist.

## Architecture

`devcontainer.json` → `postCreateCommand` → `setup-env.sh`:
1. Configures SSH and GitHub authentication
2. Syncs commands and settings to `~/.claude/`
3. Installs plugins from official and local marketplaces
4. Configures MCP servers

Key directories:
- `.devcontainer/configuration/CLAUDE.md.memory` → synced to `~/.claude/CLAUDE.md` (behavioral rules)
- `.devcontainer/commands/` → synced to `~/.claude/commands/`
- `.devcontainer/plugins/dev-marketplace/` → local plugin marketplace

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub PAT with `repo`, `workflow` permissions |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git auth |

For Codespaces: add as repository secrets. For local: create `.devcontainer/.env`.

## Custom Slash Commands

- `/code-review` - Launch parallel code review agents
- `/git-message` - Generate conventional commit messages
- `/design-system` - Generate self-contained HTML design system templates with embedded CSS and theming

## MCP Servers

Configured automatically by `setup-env.sh`:
- `aws-documentation` - AWS docs search and reading
- `terraform` - Terraform/Terragrunt workflow and AWS provider docs
- `aws-api` - Execute AWS CLI commands

## Vercel Skills

Installed automatically to `~/.claude/skills/` from [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills):
- `vercel-react-best-practices` - 45 rules for React/Next.js optimization (waterfalls, bundle size, re-renders, SSR)
- `web-design-guidelines` - 100+ UI/UX rules (accessibility, forms, animation, dark mode, i18n)

### Adding New Skills

Use [add-skill](https://github.com/vercel-labs/add-skill) CLI:
```bash
npx add-skill -g vercel-labs/agent-skills -s <skill-name>
```

## Local Plugin Marketplace

`.devcontainer/plugins/dev-marketplace/` contains plugins for development and testing.

### Adding a Plugin

1. Create plugin directory in `.devcontainer/plugins/dev-marketplace/`
2. Add `.claude-plugin/plugin.json` with plugin metadata
3. Add entry to `.claude-plugin/marketplace.json`
4. Run `.devcontainer/setup-env.sh` or rebuild DevContainer

### Updating a Plugin

Bump version in `.claude-plugin/plugin.json` after modifying plugin files.

## Installed Tools

- **agent-browser** - CLI browser automation for AI agents
- **specify-cli** - GitHub Spec-Kit (`specify init --here --ai claude`)
- **openspec** - OpenAPI spec generation

## Key Commands

```bash
# Verify configuration
claude mcp list
claude plugin marketplace list

# Re-sync after changes
./.devcontainer/setup-env.sh
```
