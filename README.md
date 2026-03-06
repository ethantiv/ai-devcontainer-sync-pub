# AI DevContainer Environment

Ready-to-use development environment with Claude Code, Gemini CLI, autonomous development loops, and pre-configured AI tools.

## What's Inside

- **Claude Code** and **Gemini CLI** — pre-installed and configured
- **dev-loop** — autonomous plan/build cycles powered by Claude CLI (`loop` command)
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

Set in `.devcontainer/.env` (copy from `.devcontainer/.env.example`).

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub token (`repo`, `workflow` permissions) |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | No | Git identity |
| `CONTEXT7_API_KEY` | No | Context7 MCP server |
| `COOLIFY_BASE_URL` / `COOLIFY_ACCESS_TOKEN` | No | Coolify deployment management |
| `STITCH_API_KEY` | No | Google Stitch MCP server |
