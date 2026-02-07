# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **dev-loop** — autonomous plan/build cycles powered by Claude CLI (`loop` command)
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

### Option 4: macOS (Local Setup)

No Docker required. Installs plugins, skills, and the loop CLI directly on your Mac.

```bash
./setup-local.sh
```

MCP servers are not configured (requires `uvx` — install manually if needed).

## Using the Loop System

The `loop` command (package: `dev-loop`) runs Claude CLI in autonomous plan/build cycles against any project.

```bash
# Initialize loop in your project (creates symlinks + templates)
cd ~/projects/my-project
loop init

# Run planning (analyzes code, creates IMPLEMENTATION_PLAN.md)
loop run --plan

# Run build (implements tasks from the plan)
loop run

# Seed an idea before planning
loop run --plan -I "Add user authentication"

# Custom iteration count (default: 5 build, 3 plan)
loop run -i 10

# Interactive mode (manual Claude session instead of autonomous)
loop run --interactive

# Disable early exit (run all iterations even if plan is complete)
loop run --no-early-exit

# Re-create symlinks after updating the package
loop update

# Clean up dev server ports (3000, 5173, 8080, etc.)
loop cleanup
```

### What `loop init` Creates

```
your-project/
├── loop/
│   ├── loop.sh              (symlink → scripts)
│   ├── PROMPT_plan.md       (symlink → prompts)
│   ├── PROMPT_build.md      (symlink → prompts)
│   ├── PROMPT_skills.md     (symlink → prompts)
│   ├── cleanup.sh           (symlink → scripts)
│   ├── notify-telegram.sh   (symlink → scripts)
│   └── logs/                (gitignored)
├── docs/
│   ├── plans/
│   │   └── IMPLEMENTATION_PLAN_template.md
│   └── IDEA_template.md
├── .claude/
│   ├── settings.json        (cleanup hook on session end)
│   └── skills/auto-revise-claude-md/SKILL.md
└── CLAUDE_template.md
```

Core files are **symlinked** (stay up-to-date with the package). Templates are **copied** (customizable per project).

### Developer / Test Installation

To test changes to the loop system from this repository:

```bash
# Install globally from local source (recommended for development)
npm install -g ./src

# Or link for live development (changes take effect immediately)
cd src && npm link

# Verify
loop --version
```

In Docker, the loop system is pre-installed at `/opt/loop/` (copied during image build). In DevContainer, it's installed from the workspace `src/` directory during setup.

### Telegram Bot

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in your `.env` to enable remote control. The bot starts automatically in Docker and provides:

- Project list with status (standalone, worktree, running task)
- Plan/Build mode selection with iteration count
- Multi-turn brainstorming sessions with Claude
- Repository cloning with auto `loop init`
- Worktree creation
- Task queue management (up to 10 queued tasks)

Commands: `/projects`, `/status`, `/brainstorming <prompt>`, `/help`

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
