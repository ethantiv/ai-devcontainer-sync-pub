# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## Table of Contents

- [What's Inside](#whats-inside)
- [Getting Started](#getting-started)
- [Using the Loop System](#using-the-loop-system)
- [Environment Variables](#environment-variables)
- [Multi-GitHub Accounts](#multi-github-accounts)
- [Volume Backups](#volume-backups)

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **dev-loop** — autonomous plan/build cycles powered by Claude CLI (`loop` command)
- **MCP Servers** — Context7, Coolify, AWS docs, Terraform
- **Slash Commands** — `/roadmap`, `/git-worktree:create`, `/git-worktree:delete`, `/dependency-update`, `/read-arxiv-paper`
- **Skills & Plugins** — 18 official + 4 local + 13 external skills, auto-installed from `config/env-config.yaml`
- **LSP Support** — TypeScript, Python (Pyright), Rust (rust-analyzer), Java (jdtls)

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
loop init --type web               # Init with web-specific skills
loop init --list-types             # Show available project types (web/devops)

loop design                        # Interactive brainstorming / design session
loop plan                          # Planning phase (3 iterations)
loop build                         # Build phase (99 iterations)
loop run                           # Plan + build combined

loop plan -I "Add authentication"  # Seed an idea before planning
loop build -i 20                   # Custom iteration count
loop run -i 20                     # -i applies to build phase only
loop build --interactive           # Manual Claude session
loop build --no-early-exit         # Run all iterations
loop plan --new                    # Archive completed plan, start fresh

loop doctor                        # Check loop installation health
loop update                        # Refresh symlinks after package update
loop update --type web,devops      # Update with merged skill presets
loop summary                       # Show stats from last run
loop cleanup                       # Kill dev server ports
```

### Idea Seeding

The `-I` flag accepts multiple source formats — not just inline text:

```bash
loop plan -I "Add user authentication"                        # Inline text
loop plan -I @docs/feature-spec.md                            # Read from file
loop plan -I https://github.com/org/repo/issues/42            # GitHub issue body (via gh CLI)
loop plan -I https://github.com/org/repo/pull/15              # GitHub PR body (via gh CLI)
loop plan -I https://example.com/spec.html                    # Any URL (via curl, HTML stripped)
```

The resolved content is written to `docs/ROADMAP.md`, which Claude reads as context during planning.

### Early Exit and New Cycles

In build mode, loop automatically stops when `docs/plans/IMPLEMENTATION_PLAN.md` is 100% complete (all checkboxes checked, no pending phases, completion marker present). Use `--no-early-exit` to override this.

When a plan is complete and you want to start a new one, use `--new` to archive the finished plan to `docs/plans/archive/` before planning begins.

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
