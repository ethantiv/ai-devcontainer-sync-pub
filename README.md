# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **dev-loop** — autonomous plan/build cycles powered by Claude CLI (`loop` command)
- **Telegram Bot** — remote control for loop tasks and brainstorming sessions
- **MCP Servers** — AWS docs, Terraform, Context7, Coolify, Stitch
- **Slash Commands** — `/code-review`, `/roadmap`, `/git-worktree`, `/loop-analyzer`
- **Skills & Plugins** — auto-installed from `skills-plugins.txt`

## Getting Started

### Option 1: Local DevContainer

1. Install [Docker](https://www.docker.com/) and [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone this repository
3. Create `.devcontainer/.env`:

   ```bash
   cp .devcontainer/.env.example .devcontainer/.env
   # Edit .devcontainer/.env — at minimum set GH_TOKEN
   ```

4. Open in VS Code and click **Reopen in Container**

### Option 2: Docker (Raspberry Pi / Standalone)

Works on ARM64 (Raspberry Pi 5, Apple Silicon) and x86_64.

```bash
cp .devcontainer/.env.example .devcontainer/.env
# Edit .devcontainer/.env — at minimum set GH_TOKEN

docker compose -f docker/docker-compose.yml up -d
docker exec -it claude-code bash
```

### Option 3: Coolify

Deploy as a Docker Compose app on a [Coolify](https://coolify.io/)-managed server.

1. Create a new **Docker Compose** resource pointing to this repository
2. Set **Base Directory** to `/docker` and **Docker Compose Location** to `/docker-compose.yml`
3. Add environment variables (same as `.devcontainer/.env`) in app settings
4. Deploy

For dual dev+prod setup, create a second app on `develop` branch with compose location `/docker-compose.dev.yml` and env vars `DEV_MODE=true`, `APP_NAME=dev-claude-code`.

### Option 4: macOS (Local)

No Docker required. Installs plugins, skills, and the loop CLI directly.

```bash
./setup-local.sh
```

## Using the Loop System

The `loop` command runs Claude CLI in autonomous plan/build cycles against any project.

```bash
cd ~/projects/my-project
loop init                          # Set up loop in your project

loop plan                          # Planning phase (5 iterations)
loop build                         # Build phase (99 iterations)
loop run                           # Plan + build combined

loop plan -I "Add authentication"  # Seed an idea before planning
loop build -i 20                   # Custom iteration count
loop run -i 20                     # -i applies to build phase only
loop build --interactive           # Manual Claude session
loop build --no-early-exit         # Run all iterations

loop update                        # Refresh symlinks after package update
loop summary                       # Show stats from last run
loop cleanup                       # Kill dev server ports
```

## Telegram Bot

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.devcontainer/.env` to enable. Starts automatically in Docker.

- Project list with status (standalone, worktree, running task)
- Plan/Build mode selection with iteration count
- Multi-turn brainstorming sessions with Claude
- Repository cloning, worktree creation, project creation
- Task queue (up to 10 queued tasks)

Commands: `/projects`, `/status`, `/brainstorming <prompt>`, `/history`, `/help`

## Environment Variables

Set in `.devcontainer/.env` (copy from `.devcontainer/.env.example`).

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub token (`repo`, `workflow` permissions) |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for remote control |
| `TELEGRAM_CHAT_ID` | No | Authorized Telegram chat ID |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | No | Git identity |
| `CONTEXT7_API_KEY` | No | Context7 MCP server |
| `COOLIFY_BASE_URL` / `COOLIFY_ACCESS_TOKEN` | No | Coolify deployment management |
| `STITCH_API_KEY` | No | Google Stitch MCP server |
| `DEV_MODE` | No | Disable Telegram bot (`true`/`1`/`yes`) |
| `APP_NAME` | No | Volume prefix (default: `claude-code`) |

`LOOP_*` env vars (timeouts, queue limits) have sensible defaults — see `.env.example` for details.
