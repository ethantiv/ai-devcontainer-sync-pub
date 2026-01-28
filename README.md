# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, and pre-configured AI tools for software engineering.

## Features

- **Claude Code** — fully configured with plugins, skills, and MCP servers
- **Gemini CLI** — Google's AI assistant ready to use
- **Custom Slash Commands** — `/code-review`, `/design-system`, `/roadmap`, `/git-worktree`
- **MCP Servers** — AWS documentation, Terraform, Context7, Playwright
- **Skills** — React/Next.js best practices, UI/UX guidelines, browser automation

## Getting Started

### Option 1: GitHub Codespaces (Recommended)

1. [Create a Fine-grained personal access token](https://github.com/settings/personal-access-tokens) with `repo` and `workflow` permissions
2. Go to **Settings → Codespaces → Secrets** and add `GH_TOKEN` with your token
3. Click **Code → Codespaces → Create codespace** on this repository
4. Wait for the container to build — everything configures automatically

### Option 2: Local DevContainer

1. Install [Docker](https://www.docker.com/) and [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone this repository
3. Create `.devcontainer/.env` with your token:
   ```bash
   GH_TOKEN=ghp_your_token_here
   ```
4. Open in VS Code and click **Reopen in Container**

### Option 3: Docker Image

Build the image:
```bash
docker build -t claude-terminal:latest -f docker/Dockerfile .
```

Run the container:
```bash
docker run -it -e GH_TOKEN=ghp_your_token claude-terminal:latest
```

## Quick Reference

### Verify Setup

```bash
claude mcp list                    # Check MCP servers
claude plugin marketplace list     # Check installed plugins
```

### Re-sync Configuration

```bash
./.devcontainer/setup-env.sh
```

### Available Slash Commands

| Command | Description |
|---------|-------------|
| `/code-review` | Review git staged changes with multiple agents |
| `/design-system` | Generate HTML design system templates |
| `/roadmap` | Manage ROADMAP.json with features and proposals |
| `/git-worktree:create <name>` | Create git worktree with naming convention |
| `/git-worktree:delete <name>` | Delete git worktree and its branch |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub token for authentication |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git |
| `CONTEXT7_API_KEY` | No | API key for Context7 MCP server |
| `RESET_CLAUDE_CONFIG` | No | Clear Claude config on startup |
| `RESET_GEMINI_CONFIG` | No | Clear Gemini config on startup |

## Customization

Add your own commands, plugins, or scripts in `.devcontainer/` directories:

- **Plugins** — edit `configuration/claude-plugins.txt`
- **Local commands** — add to `plugins/dev-marketplace/`
- **Scripts** — add `.sh` files to `scripts/`

After changes, run `./.devcontainer/setup-env.sh` or rebuild the container.

## Documentation

See [CLAUDE.md](CLAUDE.md) for technical details, architecture, and contribution guidelines.
