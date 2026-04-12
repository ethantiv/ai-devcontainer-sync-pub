# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## Table of Contents

- [What's Inside](#whats-inside)
- [Interactive Guide](#interactive-guide)
- [Getting Started](#getting-started)
- [Using the Loop System](#using-the-loop-system)
- [Environment Variables](#environment-variables)
- [Multi-GitHub Accounts](#multi-github-accounts)
- [Volume Backups](#volume-backups)

## Interactive Guide

Open [`ai-devcontainer-course.html`](ai-devcontainer-course.html) in your browser for a step-by-step walkthrough covering setup, the loop system, plugins, skills, and configuration. It's a single self-contained HTML file — no server needed.

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **dev-loop** — autonomous plan + build powered by Claude CLI (`loop` command)
- **MCP Servers** — Context7, Coolify
- **Local Plugins** — `roadmap`, `git-worktree`, `dependency-update`, `read-arxiv-paper`, `spec-compliance-review`
- **Skills & Plugins** — official marketplace plugins + external skills, auto-installed from `config/env-config.yaml`. Skills entries support single (`name: x`), bundle (`names: [a, b]`), or wildcard (url only → install all skills from repo)
- **LSP Support** — TypeScript, Python (Pyright), Java (jdtls)

## Getting Started

### Option 1: Local DevContainer

1. Install [Docker](https://www.docker.com/) and [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone this repository
3. Create `config/.env`:

   ```bash
   cp config/.env.example config/.env
   # Edit config/.env — at minimum set GH_TOKEN
   ```

4. Open in VS Code and click **Reopen in Container**

### Option 2: Docker (Raspberry Pi / Standalone)

Works on ARM64 (Raspberry Pi 5, Apple Silicon) and x86_64.

```bash
cp config/.env.example config/.env
# Edit config/.env — at minimum set GH_TOKEN

docker compose -f docker/docker-compose.yml up -d
docker exec -it claude-code bash
```

### Option 3: Coolify

Deploy as a Docker Compose app on a [Coolify](https://coolify.io/)-managed server.

1. Create a new **Docker Compose** resource pointing to this repository
2. Set **Base Directory** to `/docker` and **Docker Compose Location** to `/docker-compose.yml`
3. Add environment variables (same as `config/.env`) in app settings
4. Deploy


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
loop init --web                    # Init with web-specific skills

loop design                        # Interactive brainstorming / design session
loop run                           # Autonomous plan + build (two phases)
loop run --plan                    # Plan phase only
loop run --build                   # Build phase only

loop run -i "Add authentication"   # Seed an idea before running
loop run --interactive             # Manual Claude session
loop run --tmux                    # Run in a detached tmux session

loop kill                          # Kill all loop processes
loop update                        # Refresh symlinks after package update
loop update --web --devops         # Update with merged skill presets
```

### Idea Seeding

The `-i` flag accepts multiple source formats — not just inline text:

```bash
loop run -i "Add user authentication"                        # Inline text
loop run -i @docs/feature-spec.md                            # Read from file
loop run -i https://github.com/org/repo/issues/42            # GitHub issue body (via gh CLI)
loop run -i https://github.com/org/repo/pull/15              # GitHub PR body (via gh CLI)
loop run -i https://example.com/spec.html                    # Any URL (via curl, HTML stripped)
```

The resolved content is written to `docs/IDEA.md`, which Claude reads as context during planning.

Completed plans are archived automatically to `docs/superpowers/archive/` at the start of each new `loop run`, so you can just re-run the command to start a new cycle.

## Environment Variables

Set in `config/.env` (copy from `config/.env.example`).

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub token (`repo`, `workflow` permissions) |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | No | Git identity |
| `CONTEXT7_API_KEY` | No | Context7 MCP server |
| `COOLIFY_BASE_URL` / `COOLIFY_ACCESS_TOKEN` | No | Coolify deployment management |
| `STITCH_API_KEY` | No | Google Stitch MCP server |
| `RESET_CLAUDE_CONFIG` / `RESET_GEMINI_CONFIG` | No | Set `true` to clear config on startup |
| `BACKUP_PIN` | No | PIN for encrypting/decrypting volume backups |

## Multi-GitHub Accounts

If you use a separate GitHub account for work (e.g., corporate SSO), the environment auto-routes `gh` CLI and git credentials based on org URLs and working directories.

1. Set `GH_TOKEN_WORK` in `config/.env` (PAT classic with `repo`, `read:user`, `read:org`, `workflow`)
2. Configure the `git.work` section in `config/env-config.yaml`:

   ```yaml
   git:
     work:
       email: "your.work@company.com"
       orgs: "YourOrg|AnotherOrg"    # GitHub orgs routed to work token
       dirs:                          # Directories routed to work account
         - "~/projects/Work"
   ```

3. Rebuild the container (or re-run `setup-env.sh`)

The `gh` CLI shim at `~/.local/bin/gh` detects org URLs in arguments first, then falls back to checking if your `PWD` is inside a configured work directory.

## Volume Backups

Create encrypted backups of DevContainer Docker volumes (`~/.claude`, `~/.gemini`, `~/.cache/google-vscode-extension/auth`).

```bash
.devcontainer/backup.sh create              # Create encrypted backup
.devcontainer/backup.sh restore <file>      # Restore from backup (use --force to skip confirmation)
.devcontainer/backup.sh list                # List existing backups
```

Set `BACKUP_PIN` in `config/.env` before use. Backups are saved to `.devcontainer/backups/` (gitignored) as AES-256 encrypted `.tar.gz.gpg` files.
