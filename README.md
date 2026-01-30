# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, and pre-configured AI tools for software engineering.

## Features

- **Claude Code** 
- **Gemini CLI** 
- **Custom Slash Commands** 
- **MCP Servers**
- **Skills**

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

### Option 3: Docker (Raspberry Pi / Standalone)

Optimized for ARM64 (Raspberry Pi 5, Apple Silicon) but works on x86_64.

```bash
cd docker

# Copy and configure environment
cp .env.example .env
# Edit .env with your GH_TOKEN

# Build and run
docker compose up -d

# Attach to container
docker compose exec claude bash
```

The container auto-restarts after reboot (`restart: unless-stopped`).

#### Docker Volumes

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `claude-config` | `~/.claude` | Claude configuration and plugins |
| `gemini-config` | `~/.gemini` | Gemini CLI configuration |
| `projects` | `~/projects` | Persistent project storage |

#### Manual Docker Build

```bash
# Build
docker build -t claude-code:latest -f docker/Dockerfile .

# Run interactively
docker run -it --rm \
    -e GH_TOKEN="ghp_..." \
    -v projects:/home/developer/projects \
    -v claude-config:/home/developer/.claude \
    claude-code:latest
```

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

- **Plugins** — edit `configuration/skills-plugins.txt`
- **Local commands** — add to `plugins/dev-marketplace/`
- **Scripts** — add `.sh` files to `scripts/`

After changes, run `./.devcontainer/setup-env.sh` or rebuild the container.
