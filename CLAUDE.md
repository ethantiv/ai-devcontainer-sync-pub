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

Available as local marketplace plugins (`dev-marketplace`):
- `/code-review` - parallel code review with multiple agents
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
| `CONTEXT7_API_KEY` | No | API key for Context7 MCP server |

Codespaces: add as repository secrets. Local: create `.devcontainer/.env`.

### MCP Servers (pre-configured)

- `aws-documentation` - AWS docs search and reading
- `terraform` - Terraform/Terragrunt execution, AWS provider docs
- `context7` - Context7 documentation search (requires `CONTEXT7_API_KEY`)

### Adding New Plugins/Skills/Commands

1. **Plugins**: Edit `.devcontainer/configuration/claude-plugins.txt` (see file for format examples)
2. **Local plugins**: Add to `.devcontainer/plugins/dev-marketplace/` and register in `marketplace.json`
3. **Scripts**: Add `.sh` files to `.devcontainer/scripts/`
4. **Run** `./.devcontainer/setup-env.sh` to sync changes

### Local Plugin Structure

```
plugins/dev-marketplace/<plugin-name>/
  .claude-plugin/plugin.json    # name, version, description, author
  commands/<command>.md          # slash command (with YAML frontmatter)
  hooks/                        # optional hooks
```

Register in `plugins/dev-marketplace/.claude-plugin/marketplace.json`.

### Key Files for Config Changes

Changes to setup/sync logic must be applied in parallel across:
- `.devcontainer/setup-env.sh` — DevContainer/Codespaces setup
- `setup-local.sh` — macOS local setup
- `docker/Dockerfile` + `docker/entrypoint.sh` + `docker/setup-claude.sh` — Docker image build and runtime

### Setup Flow

Container start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins → add MCP servers

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |

### Codebase Patterns

- `~/.claude` is a named Docker volume (ext4), `/tmp` is tmpfs — `rename()` fails cross-device (EXDEV). Setup scripts export `TMPDIR="$CLAUDE_DIR/tmp"` to keep all temp ops on the same filesystem.
- `claude-plugins.txt` external format: `name@type=owner/repo` — `type` matching: `vercel-skills` and `github` are special-cased, everything else is treated as external marketplace name.
