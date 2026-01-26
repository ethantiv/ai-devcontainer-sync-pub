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

## Architecture

```
.devcontainer/
├── setup-env.sh              # Main setup script (runs on container start)
├── devcontainer.json         # Container config, mounts, extensions
├── Dockerfile                # Base image with uv, Node.js, Playwright
├── configuration/
│   ├── CLAUDE.md.memory      # Template for ~/.claude/CLAUDE.md
│   └── claude-plugins.txt    # Plugin/skill manifest
├── commands/                 # Custom slash commands → ~/.claude/commands/
├── scripts/                  # Helper scripts → ~/.claude/scripts/
└── plugins/dev-marketplace/  # Local plugin development
```

**Setup flow**: Container start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins/commands → add MCP servers

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

### Plugin/Skill Configuration

Edit `.devcontainer/configuration/claude-plugins.txt`:
```bash
plugin-name                                    # Official marketplace
plugin-name@marketplace=owner/repo             # External marketplace
skill-name@vercel-skills=vercel-labs/agent-skills  # Vercel skills
skill-name@github=owner/repo/path/SKILL.md     # Direct GitHub skill
```

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `commands/*.md` | `~/.claude/commands/` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |

Run `setup-env.sh` after modifying any source files.
