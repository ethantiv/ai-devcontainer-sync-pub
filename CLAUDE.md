# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

DevContainer for multi-AI agent development with Claude Code and Gemini CLI. Configuration-only repository - no build, test, or lint commands.

## Build & Run

Re-sync configuration after changes:
```bash
./.devcontainer/setup-env.sh
```

## Validation

```bash
claude mcp list                    # Verify MCP servers
claude plugin marketplace list     # List installed plugins
```

## Custom Slash Commands

Available commands synced to `~/.claude/commands/`:
- `/code-review` - parallel code review with multiple agents
- `/git-message` - generate conventional commit messages
- `/design-system` - generate HTML design system templates
- `/roadmap` - manage ROADMAP.json with features and proposals

## Operational Notes

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub PAT with `repo`, `workflow` permissions |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git auth |
| `RESET_CLAUDE_CONFIG` | No | Clear `~/.claude/` on startup |
| `RESET_GEMINI_CONFIG` | No | Clear `~/.gemini/` on startup |

Codespaces: add as repository secrets. Local: create `.devcontainer/.env`.

### MCP Servers (pre-configured)

- `aws-documentation` - AWS docs search and reading
- `terraform` - Terraform/Terragrunt execution, AWS provider docs
- `aws-api` - AWS CLI command execution

### Adding New Plugins/Skills/Commands

1. **Plugins**: Edit `.devcontainer/configuration/claude-plugins.txt` (see file for format examples)
2. **Commands**: Add `.md` files to `.devcontainer/commands/`
3. **Scripts**: Add `.sh` files to `.devcontainer/scripts/`
4. **Run** `./.devcontainer/setup-env.sh` to sync changes

### Setup Flow

Container start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins/commands → add MCP servers

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `commands/*.md` | `~/.claude/commands/` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |
