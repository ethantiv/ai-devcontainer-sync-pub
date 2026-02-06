# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **Loop System** — autonomous plan/build cycles powered by Claude CLI (`loop` command)
- **Telegram Bot** — remote control for loop tasks and brainstorming sessions
- **MCP Servers** — AWS docs, Terraform, Context7, Coolify
- **Custom Slash Commands** — code review, design system, roadmap, git worktrees
- **Skills & Plugins** — auto-installed from `skills-plugins.txt`

## Getting Started

### Option 1: Local DevContainer

1. Install [Docker](https://www.docker.com/) and [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone this repository
3. Create `.devcontainer/.env`:

   ```bash
   GH_TOKEN=ghp_your_token_here
   ```

4. Open in VS Code and click **Reopen in Container**

### Option 2: Docker (Raspberry Pi / Standalone)

Works on ARM64 (Raspberry Pi 5, Apple Silicon) and x86_64.

```bash
cd docker
cp .env.example .env
# Edit .env — at minimum set GH_TOKEN

docker compose up -d
docker exec -it claude-code bash
```

The container auto-restarts after reboot.

### Option 3: Coolify (Self-hosted PaaS)

Deploy as a Docker Compose application on a server managed by [Coolify](https://coolify.io/).

1. In Coolify, create a new **Docker Compose** resource pointing to this repository
2. Set **Base Directory** to `/docker` and **Docker Compose Location** to `/docker-compose.yml`
3. Add environment variables (same as `docker/.env`) in the Coolify app settings
4. Deploy — Coolify builds the image from `docker/Dockerfile` with `context: ..` resolving to the repo root

The container runs headless with auto-restart. Manage it through Coolify UI or API.

## Using the Loop System

The `loop` command runs Claude CLI in autonomous plan/build cycles against any project.

```bash
# First, initialize loop in your project
cd ~/projects/my-project
loop init

# Run planning (analyzes code, creates IMPLEMENTATION_PLAN.md)
loop run --plan -i 5

# Run build (implements tasks from the plan)
loop run -i 3

# Clean up dev server ports
loop cleanup
```

To control loops remotely, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in your `.env`. The bot starts automatically and lets you manage tasks from your phone.

## Environment Variables

Set these in `.devcontainer/.env` (DevContainer) or `docker/.env` (Docker).

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub token for authentication and repo access |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git |
| `CONTEXT7_API_KEY` | No | API key for Context7 MCP server |
| `COOLIFY_BASE_URL` | No | URL of Coolify instance for deployment management |
| `COOLIFY_ACCESS_TOKEN` | No | Coolify API access token |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for remote loop control |
| `TELEGRAM_CHAT_ID` | No | Authorized Telegram chat ID |
| `MAIN_PROJECT` | No | Main project name for Telegram bot worktree management |
| `GIT_USER_NAME` | No | Git global user.name |
| `GIT_USER_EMAIL` | No | Git global user.email |
| `RESET_CLAUDE_CONFIG` | No | Set to `true` to clear Claude config on startup |
| `RESET_GEMINI_CONFIG` | No | Set to `true` to clear Gemini config on startup |

## Customization

Edit files in `.devcontainer/`, then run `./.devcontainer/setup-env.sh` to apply:

- **Plugins & skills** — `configuration/skills-plugins.txt`
- **Local slash commands** — `plugins/dev-marketplace/`
- **Scripts** — `scripts/` (synced to `~/.claude/scripts/`)
- **Claude memory** — `configuration/CLAUDE.md.memory` (synced to `~/.claude/CLAUDE.md`)

## Docker Volumes

Data persists across container rebuilds:

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `claude-config` | `~/.claude` | Claude binary, settings, credentials, plugins |
| `agents-skills` | `~/.agents` | Globally installed skills |
| `gemini-config` | `~/.gemini` | Gemini CLI configuration |
| `projects` | `~/projects` | Your working projects |
