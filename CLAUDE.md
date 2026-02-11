# CLAUDE.md

DevContainer for multi-AI agent development with Claude Code and Gemini CLI. Configuration-only repository.

## Build & Run

Re-sync configuration after changes:
```bash
./.devcontainer/setup-env.sh
```

## Validation

```bash
claude mcp list                    # Verify MCP servers
claude plugin marketplace list     # List installed plugins
python3 -m pytest src/telegram_bot/tests/ -v  # Run Telegram bot tests (456 tests)
npm install --prefix src && npm test --prefix src  # Run JS tests (20 tests, requires install)
```

Single test: `python3 -m pytest src/telegram_bot/tests/test_tasks.py::TestTaskManager::test_start_task -v`

## Custom Slash Commands

Available as local marketplace plugins (`dev-marketplace`):
- `/code-review` - parallel code review with multiple agents
- `/roadmap` - manage ROADMAP.md with features and proposals
- `/git-worktree:create <name>` / `/git-worktree:delete <name>` - manage worktrees
- `/loop-analyzer` - analyze autonomous loop logs with 5 parallel subagents

## Operational Notes

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub PAT with `repo`, `workflow` permissions |
| `SSH_PRIVATE_KEY` | No | Base64-encoded SSH key for Git auth |
| `RESET_CLAUDE_CONFIG` | No | Clear `~/.claude/` on startup |
| `RESET_GEMINI_CONFIG` | No | Clear `~/.gemini/` on startup |
| `CONTEXT7_API_KEY` | No | API key for Context7 MCP server |
| `COOLIFY_BASE_URL` | No | URL of Coolify instance |
| `COOLIFY_ACCESS_TOKEN` | No | Coolify API access token |
| `STITCH_API_KEY` | No | Google Stitch API key for Stitch MCP server |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | No | Git global identity |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | No | Telegram bot auth |
| `APP_NAME` | No | Volume name prefix (default: `claude-code`, `dev-claude-code` for dev) |
| `DEV_MODE` | No | Disable Telegram bot in dev containers (true/1/yes) |

`LOOP_*` env vars (thresholds, timeouts, queue limits) are defined with defaults in `src/telegram_bot/config.py`.

Codespaces: add as repository secrets. Local: create `.devcontainer/.env` (copy from `.devcontainer/.env.example`).

### MCP Servers

`aws-documentation`, `terraform`, `context7` (needs `CONTEXT7_API_KEY`), `coolify` (needs `COOLIFY_BASE_URL` + `COOLIFY_ACCESS_TOKEN`), `stitch` (needs `STITCH_API_KEY`, remote HTTP). First four require `uvx` (from `uv`).

### Loop System

Source at `src/`. Docker: `COPY src /opt/loop` + `npm install`, symlinked as `/usr/bin/loop`. Telegram bot: `/opt/loop/telegram_bot/` with `PYTHONPATH="/opt"`.

```bash
loop init / update      # Initialize/refresh symlinks in project
loop plan / build / run # Run planning (3 iter), build (5 iter), or both
loop summary / cleanup  # Show run stats / clean artifacts
```

**Structure**: `src/scripts/` (shell), `src/prompts/`, `src/templates/`, `src/telegram_bot/` (Python bot + `handlers/`), `src/bin/` + `src/lib/` (Node.js CLI).

**Telegram bot**: Starts in Docker if `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` set. Commands: `src/telegram_bot/COMMANDS.md`.

**Auto-commit**: `ensure_committed()` in `loop.sh` auto-commits after each iteration (prefix `chore(loop):`).

### Adding New Components

**Global npm tools** — 4 files: `.devcontainer/Dockerfile`, `docker/Dockerfile`, `setup-local.sh`, `skills-plugins.txt` (if plugin).

**Plugins/Skills** — Edit `.devcontainer/configuration/skills-plugins.txt`, then `setup-env.sh`. Local plugins: add to `.devcontainer/plugins/dev-marketplace/` + register in `marketplace.json`.

**Local plugin layout**: `plugins/dev-marketplace/<name>/.claude-plugin/plugin.json` + `commands/<cmd>.md` (YAML frontmatter: `allowed-tools`, `description`, `argument-hint`).

### Key Files for Parallel Changes

Setup/sync — apply across all:
- `.devcontainer/setup-env.sh` — DevContainer/Codespaces
- `setup-local.sh` — macOS local (plugins and skills only, no MCP)
- `docker/Dockerfile` + `docker/entrypoint.sh` + `docker/setup-claude.sh` — Docker
- `README.md` — docs for all deployment options

Loop system: `src/` + `docker/Dockerfile` + `docker/entrypoint.sh`.

Loop CLI flags/defaults: `src/bin/cli.js`, `src/lib/run.js`, `src/scripts/loop.sh`, optionally `src/lib/init.js`. `loop init` skips existing; `loop update` calls `init({ force: true })`.

### Setup Flow

**DevContainer**: start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins → MCP servers.

**Docker**: start → `entrypoint.sh` → sync `/opt/claude-config` → first-run (`.configured` marker) → `setup-claude.sh`. Claude binary installed to `~/.claude/bin/` (volume) at first start, not during build. GH auth via `gh auth login --with-token`.

**Docker volumes** (4, prefixed with `APP_NAME`): `claude-config` (~/.claude), `agents-skills` (~/.agents), `gemini-config` (~/.gemini), `projects` (~/projects).

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |

### Codebase Patterns

- **EXDEV gotcha**: `~/.claude` is ext4 volume, `/tmp` is tmpfs — `rename()` fails cross-device. Scripts export `TMPDIR="$CLAUDE_DIR/tmp"`.
- **Claude binary in Docker**: Scripts use `CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"; claude() { "$CLAUDE_CMD" "$@"; }` to ensure correct binary.
- **Claude config persistence**: `CLAUDE_CONFIG_DIR=~/.claude` keeps `.claude.json` inside the volume. Set in `devcontainer.json` and `Dockerfile`.
- **Setup scripts must be non-fatal**: Writes to dotfiles use `|| warn` / `|| true`. Don't block plugin/MCP setup on non-essential ops.
- **UTF-8 locale**: Dockerfile must generate `en_US.UTF-8` locale. Without it, Polish chars in tmux show as `_`.
- **Shell helpers**: `ok()`, `warn()`, `fail()` for colored status output in setup scripts.
- **skills-plugins.txt formats**: `- https://github.com/owner/repo --skill name` (new), `name@skills=owner/repo` (legacy), `name@github=owner/repo/path`, `name@type=owner/repo` (external). Gotcha: `setup-local.sh` requires type to match `*-marketplace` glob.
- **Skills install**: `npx -y skills add "$url" --skill "$name" --agent claude-code gemini-cli -g -y`
- **Python deps**: Add to `src/telegram_bot/requirements.txt` — Dockerfile auto-installs.
- **Test patterns**: pytest + pytest-asyncio. Patch `PROJECTS_ROOT` in module namespace, not via env vars. Fixtures with `with patch(...)` must `yield` not `return`. Bot tests patch `TELEGRAM_CHAT_ID` in the module where the decorated function is defined.
- **Deadlock prevention**: `_save_tasks()` acquires `_queue_lock` internally — never call while holding the lock.
- **State persistence**: `TaskManager` and `BrainstormManager` use atomic `os.replace()` to JSON files in `PROJECTS_ROOT`. Validate tmux sessions on load, remove stale entries.
- **Coolify MCP limitations**: `base_directory` and `docker_compose_location` not in MCP tool — use `curl -X PATCH` directly.
- **MCP server JSON type**: Remote HTTP MCP servers require `"type": "http"` in `add-json` config, not `"type": "url"` (which silently fails).
- **Docker Compose volumes**: Env var interpolation works only in YAML values (not keys). Volume `name:` uses `${APP_NAME:-claude-code}-<vol>` for dev/prod isolation.
- **Dual deployment**: Prod uses `docker-compose.yml` (main branch), dev uses `docker-compose.dev.yml` (develop branch). Separate compose files = separate Coolify container names.
