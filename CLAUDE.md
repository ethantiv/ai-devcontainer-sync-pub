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
- `/git-worktree:create <name>` - create worktree with naming convention `{project}-{name}`
- `/git-worktree:delete <name>` - delete worktree and its branch

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
- `playwright` - browser automation via `@playwright/cli` (requires browser install)

MCP servers require `uvx` (from `uv`). Installed via Dockerfile in DevContainer/Docker paths. Not available in `setup-local.sh` (macOS manual install).

### Gemini CLI

Pre-installed alongside Claude Code. Reset config with `RESET_GEMINI_CONFIG=true`.

### Adding New Global npm Tools

Requires changes in 5 files:
1. `.devcontainer/Dockerfile` — `npm install -g` + symlink in runtime stage
2. `docker/Dockerfile` — `npm install -g` + symlink after COPY
3. `setup-local.sh` — dedicated `install_<tool>()` function + call in `main()`
4. `.devcontainer/configuration/claude-plugins.txt` — if it has a skill/plugin
5. `docker/setup-claude.sh` and `.devcontainer/setup-env.sh` — hardcoded skill entry if applicable

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

Command `.md` files use YAML frontmatter:
```yaml
---
allowed-tools: Bash(git worktree:*), Bash(git branch:*)
description: Short description of the command
argument-hint: <name>
---
```
`allowed-tools` restricts which tools the command can use (glob patterns supported).

### Key Files for Config Changes

Changes to setup/sync logic must be applied in parallel across:
- `.devcontainer/setup-env.sh` — DevContainer/Codespaces setup
- `setup-local.sh` — macOS local setup (no MCP servers — plugins and skills only)
- `docker/Dockerfile` + `docker/entrypoint.sh` + `docker/setup-claude.sh` — Docker image build and runtime
- `README.md` — single documentation file for all deployment options (Codespaces, DevContainer, Docker)

### Setup Flow

**DevContainer/Codespaces**: Container start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins → add MCP servers

**Docker image**: Container start → `entrypoint.sh` → sync config from `/opt/claude-config` to `~/.claude` → first-run setup (`.configured` marker) → `setup-claude.sh` for plugins/MCP

**Docker GitHub auth**: `entrypoint.sh` automatically runs `gh auth login --with-token` using `GH_TOKEN` env var at every container start. No manual login required.

**Docker Claude persistence**: Claude installed to `~/.claude/bin/` (volume) at first container start, not during image build. This preserves updates across `docker compose down && up`. The `CLAUDE_INSTALL_DIR` env var controls install location; fallback moves binary from `~/.local/bin/` if installer ignores it.

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |

### Codebase Patterns

- `~/.claude` is a named Docker volume (ext4), `/tmp` is tmpfs — `rename()` fails cross-device (EXDEV). Setup scripts export `TMPDIR="$CLAUDE_DIR/tmp"` to keep all temp ops on the same filesystem.
- `claude-plugins.txt` external format: `name@type=owner/repo` — `type` matching: `skills` and `github` are special-cased, everything else is treated as external marketplace name.
- **Gotcha**: `setup-env.sh` accepts any `type` as marketplace (fallthrough `*)`), but `setup-local.sh` requires `type` to match `*-marketplace` glob. Always name external marketplace types with `-marketplace` suffix to work in both scripts.
- Playwright: `@playwright/cli` (MCP server binary) ≠ `playwright` (full package for browser install). Use `npx -y playwright install chromium` to install browsers — never call `playwright` directly as a global command. DevContainer sets `PLAYWRIGHT_MCP_BROWSER=chromium`, `PLAYWRIGHT_MCP_VIEWPORT_SIZE=1920x1080`, and `--shm-size=256m`. Docker uses `PLAYWRIGHT_MCP_NO_SANDBOX=true` env var to disable sandbox globally (preferred over `playwright-cli.json` which only works in working directory).
- Shell scripts use `ok()`, `warn()`, `fail()` helpers for status output (colored ANSI with ✔︎/⚠️/❌). Use these instead of raw emoji in `setup-local.sh`, `setup-env.sh`, and `docker/setup-claude.sh`. Section headers with informational emoji (📄, 📦, 🔧, 🔄, 🔐, 🚀, 🌍) remain as plain `echo`.
- `uv`/`uvx`: installed via `pip3 install --break-system-packages uv` in Dockerfiles (builder stage → COPY to runtime). MCP servers `aws-documentation` and `terraform` depend on `uvx`. Ad-hoc install without rebuild: `pip3 install --break-system-packages uv`.
- Skills install syntax: `npx -y skills add "https://github.com/$repo" --skill "$name" -g -y`. The `-g` flag installs globally to `~/.agents/skills/` with symlinks to `~/.claude/skills/`. The `-y` flag skips interactive confirmation prompts.
- **Claude binary in Docker**: Lives at `~/.claude/bin/claude` (volume). Scripts should define wrapper: `CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"; claude() { "$CLAUDE_CMD" "$@"; }` to ensure correct binary is used regardless of PATH.
- **Testing Docker on Raspberry Pi**: `ssh mirek@raspberrypi.local`, then `cd ~/Downloads/ai-devcontainer-sync/docker && git pull && sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d`. Verify with `sudo docker exec claude-dev bash -c 'echo $VAR_NAME'`.
