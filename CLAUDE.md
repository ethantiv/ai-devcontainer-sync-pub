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

### Test Output Guidelines

- Keep test stdout minimal: summary line with pass/fail counts
- Pipe full output to `loop/logs/test-output.log` (e.g., `npm test 2>&1 | tee loop/logs/test-output.log`)
- Use ERROR prefix on failure summary lines for grep: `ERROR: 3 tests failed out of 47`
- On failure, log 3-line diagnostic: which test, error message, root cause hypothesis

## Custom Slash Commands

Available as local marketplace plugins (`dev-marketplace`):
- `/code-review` - parallel code review with multiple agents
- `/design-system` - generate HTML design system templates
- `/roadmap` - manage ROADMAP.md with features and proposals
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
| `COOLIFY_BASE_URL` | No | URL of Coolify instance |
| `COOLIFY_ACCESS_TOKEN` | No | Coolify API access token |
| `GIT_USER_NAME` | No | Git global user.name |
| `GIT_USER_EMAIL` | No | Git global user.email |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for remote loop control |
| `TELEGRAM_CHAT_ID` | No | Authorized Telegram chat ID |

Codespaces: add as repository secrets. Local: create `.devcontainer/.env`.

### MCP Servers (pre-configured)

- `aws-documentation` - AWS docs search and reading
- `terraform` - Terraform/Terragrunt execution, AWS provider docs
- `context7` - Context7 documentation search (requires `CONTEXT7_API_KEY`)
- `coolify` - Coolify deployment platform management (requires `COOLIFY_BASE_URL`, `COOLIFY_ACCESS_TOKEN`)

MCP servers require `uvx` (from `uv`). Installed via Dockerfile in DevContainer/Docker paths. Not available in `setup-local.sh` (macOS manual install).

### Gemini CLI

Pre-installed alongside Claude Code. Reset config with `RESET_GEMINI_CONFIG=true`.

### Loop System (dev-loop)

Built-in autonomous development loop at `src/` in this repository. Includes CLI (`loop` command), shell scripts, prompts, Telegram bot, and templates. Installed to Docker image at `/opt/loop/` via `COPY src /opt/loop` in Dockerfile.

```bash
loop --help             # Show available subcommands
loop init               # Initialize loop config in current project (symlinks scripts/prompts)
loop plan               # Run planning phase (default: 3 iterations)
loop build              # Run build phase (default: 5 iterations)
loop run                # Plan then build (3+5 iterations)
loop summary            # Show summary of last loop run (tool usage, files, tokens)
loop cleanup            # Clean up loop artifacts
loop update             # Refresh symlinks after update
```

**Structure**: `src/scripts/` (shell), `src/prompts/` (Claude prompts), `src/templates/` (project templates), `src/telegram_bot/` (Python bot), `src/bin/` + `src/lib/` (Node.js CLI).

**Telegram bot**: Starts automatically in Docker if `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars are set. Runs from `/opt/loop/telegram_bot/` via entrypoint.sh.

**Post-iteration auto-commit**: `ensure_committed()` in `loop.sh` auto-commits and pushes after each iteration if the agent skipped git. Auto-commits use the `chore(loop):` prefix — absence of these in `git log` means the prompt fix is working.

### Adding New Global npm Tools

Requires changes in 4 files:
1. `.devcontainer/Dockerfile` — `npm install -g` + symlink in runtime stage
2. `docker/Dockerfile` — `npm install -g` + symlink after COPY
3. `setup-local.sh` — dedicated `install_<tool>()` function + call in `main()`
4. `.devcontainer/configuration/skills-plugins.txt` — if it has a skill/plugin

### Adding New Plugins/Skills/Commands

1. **Plugins**: Edit `.devcontainer/configuration/skills-plugins.txt` (see file for format examples)
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

Loop system changes require parallel updates across:
- `src/` — source code (scripts, prompts, templates, telegram bot, npm CLI)
- `docker/Dockerfile` — `COPY src /opt/loop` and `npm install`
- `docker/entrypoint.sh` — Telegram bot startup path

Loop CLI changes (flags, defaults) require edits across 4 files: `src/bin/cli.js` (Commander option), `src/lib/run.js` (JS→shell bridge), `src/scripts/loop.sh` (bash implementation), and optionally `src/lib/init.js` (suggested commands).

### Setup Flow

**DevContainer/Codespaces**: Container start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins → add MCP servers

**Docker image**: Container start → `entrypoint.sh` → sync config from `/opt/claude-config` to `~/.claude` → first-run setup (`.configured` marker) → `setup-claude.sh` for plugins/MCP

**Docker GitHub auth**: `entrypoint.sh` automatically runs `gh auth login --with-token` using `GH_TOKEN` env var at every container start. No manual login required.

**Docker Claude persistence**: Claude installed to `~/.claude/bin/` (volume) at first container start, not during image build. This preserves updates across `docker compose down && up`. The `CLAUDE_INSTALL_DIR` env var controls install location; fallback moves binary from `~/.local/bin/` if installer ignores it.

**Docker volumes**: Four named volumes persist data across container rebuilds:
- `claude-config` → `~/.claude` — Claude binary, settings, credentials, skills symlinks
- `agents-skills` → `~/.agents` — Global skills installed via `npx skills add -g` (symlinked from `~/.claude/skills/`)
- `gemini-config` → `~/.gemini` — Gemini CLI configuration
- `projects` → `~/projects` — Working directory for projects

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `configuration/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `scripts/*.sh` | `~/.claude/scripts/` |
| `plugins/dev-marketplace/` | local plugin marketplace |

### Claude Config Persistence

- `CLAUDE_CONFIG_DIR` env var controls where Claude stores `.claude.json` (main config with `installMethod`, `userID`, `oauthAccount`)
- Without it: `~/.claude.json` (home dir, outside volume = lost on rebuild)
- With `CLAUDE_CONFIG_DIR=~/.claude`: `~/.claude/.claude.json` (inside volume = persisted)
- DevContainer sets this in `devcontainer.json`, Docker sets it in `Dockerfile`

### Codebase Patterns

- `~/.claude` is a named Docker volume (ext4), `/tmp` is tmpfs — `rename()` fails cross-device (EXDEV). Setup scripts export `TMPDIR="$CLAUDE_DIR/tmp"` to keep all temp ops on the same filesystem.
- `skills-plugins.txt` formats:
  - Skills (new): `- https://github.com/owner/repo --skill skill-name` — installed with `--agent claude-code gemini-cli`
  - Skills (legacy): `name@skills=owner/repo` — still supported for backward compatibility
  - GitHub skills: `name@github=owner/repo/path-to-SKILL.md`
  - External plugins: `name@type=owner/repo` — `type` is treated as marketplace name
- **Gotcha**: `setup-env.sh` accepts any `type` as marketplace (fallthrough `*)`), but `setup-local.sh` requires `type` to match `*-marketplace` glob. Always name external marketplace types with `-marketplace` suffix to work in both scripts.
- Shell scripts use `ok()`, `warn()`, `fail()` helpers for status output (colored ANSI with ✔︎/⚠️/❌). Use these instead of raw emoji in `setup-local.sh`, `setup-env.sh`, and `docker/setup-claude.sh`. Section headers with informational emoji (📄, 📦, 🔧, 🔄, 🔐, 🚀, 🌍) remain as plain `echo`.
- `uv`/`uvx`: installed via `pip3 install --break-system-packages uv` in Dockerfiles (builder stage → COPY to runtime). MCP servers `aws-documentation` and `terraform` depend on `uvx`. Ad-hoc install without rebuild: `pip3 install --break-system-packages uv`.
- Skills install syntax: `npx -y skills add "$url" --skill "$name" --agent claude-code gemini-cli -g -y`. The `-g` flag installs globally to `~/.agents/skills/` with symlinks to `~/.claude/skills/`. The `-y` flag skips interactive confirmation prompts. The `--agent claude-code gemini-cli` flag limits installation to Claude Code and Gemini CLI agents only.
- **Claude binary in Docker**: Lives at `~/.claude/bin/claude` (volume). Scripts should define wrapper: `CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"; claude() { "$CLAUDE_CMD" "$@"; }` to ensure correct binary is used regardless of PATH.
- **Testing Docker on Raspberry Pi**: `ssh mirek@raspberrypi.local`, then `cd ~/Downloads/ai-devcontainer-sync/docker && git pull && sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d`. Verify with `sudo docker exec claude-code bash -c 'echo $VAR_NAME'`.
- **Loop system in Docker**: Installed at `/opt/loop/` via `COPY src /opt/loop` + `npm install`. Symlinked as `/usr/bin/loop`. Telegram bot runs from `/opt/loop/telegram_bot/` with `PYTHONPATH="/opt"`. Shell scripts at `/opt/loop/scripts/loop.sh`.
- **Loop script path resolution**: `loop.sh` resolves `LOOP_SCRIPTS_DIR` via `readlink -f "$0"` to find sibling scripts (notify-telegram.sh, cleanup.sh). Prompt files: uses project-local `loop/PROMPT_*.md` if present (symlinked by `loop init`), falls back to `$LOOP_ROOT/prompts/`. `tasks.py` resolves loop.sh: `/opt/loop/scripts/loop.sh` first, then project-local `./loop/loop.sh`.
- **UTF-8 locale in Docker**: debian:bookworm-slim has no locales generated by default. Required: `apt install locales`, `sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen`, and `ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8`. Without this, Polish characters in tmux display as `_`.
- **Coolify MCP limitations**: `base_directory` and `docker_compose_location` are not available in the Coolify MCP tool. Use `curl -X PATCH` against the Coolify API directly to set these fields.
- **Setup scripts must be non-fatal**: In Docker/Coolify containers, `~/.bashrc` may not be writable. All writes to user dotfiles in setup scripts should use `|| warn` / `|| true` instead of relying on `set -e`. Critical setup (plugins, MCP servers) must not be blocked by non-essential operations.
- **Loop `init` for external projects**: `loop init` creates symlinks from `/opt/loop/scripts/` and `/opt/loop/prompts/` into project's `loop/` directory. Templates are copied (not symlinked) so they can be customized per project.
- **Brainstorm session persistence**: `BrainstormManager` persists sessions to `PROJECTS_ROOT/.brainstorm_sessions.json` via atomic writes (`os.replace`). `_save_sessions()` is called via `_cleanup_session()` (covers `finish()`/`cancel()`) and after `start()`/`respond()`. Sessions are restored in `__init__()` via `_load_sessions()`, which validates tmux sessions exist and removes stale entries.
- **Loop run summary**: `src/lib/summary.js` parses JSONL log files for tool usage counts, files modified (Edit/Write), token usage, and test results. `loop summary` CLI command reads from `./loop/logs/` by default. `loop.sh` cleanup trap auto-generates `summary-latest.txt` in log dir on each run completion. Uses `$LOOP_ROOT/lib/summary` path (resolved via `readlink -f`) so it works in both Docker (`/opt/loop`) and local dev.
- **Telegram bot string localization**: All user-facing strings live in `src/telegram_bot/messages.py` as named constants (e.g. `MSG_NO_PROJECT_SELECTED`). `bot.py`, `tasks.py`, `projects.py` import from `messages.py` — no inline strings. Error codes (`ERR_SESSION_ACTIVE`, `ERR_START_FAILED`, etc.) decouple error detection from display language. `BrainstormManager.start()`/`respond()` yield `(error_code, status, is_final)` tuples; `_is_brainstorm_error()` checks `error_code in BRAINSTORM_ERROR_CODES`.
