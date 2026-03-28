# CLAUDE.md

DevContainer for multi-AI agent development with Claude Code and Gemini CLI. Includes configuration, loop system (Node.js CLI + shell scripts), prompts, and templates.

## Build & Run

Re-sync configuration after changes:
```bash
./.devcontainer/setup-env.sh
```

## Validation

```bash
claude mcp list                    # Verify MCP servers
claude plugin marketplace list     # List installed plugins
npm install --prefix src && npm test --prefix src  # Run JS tests (120 tests, requires install)
npm run test:integration --prefix src              # Run only integration tests (17 tests)
bash src/scripts/tests/test_write_idea.sh          # Run shell tests (18 tests)
bash src/scripts/tests/test_check_completion.sh    # Run completion detection tests (20 tests)
bash src/scripts/tests/test_ensure_playwright.sh   # Run Playwright lazy-install tests (14 tests)
bash src/scripts/tests/test_cleanup.sh             # Run cleanup.sh port tests (11 tests)
bash src/scripts/tests/test_backup.sh              # Run backup.sh tests (20 tests)
bash src/scripts/tests/test_setup_common.sh        # Run setup-common.sh tests (48 tests)
```

No typecheck (pure JS/Bash project). No linter configured.

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
| `GH_TOKEN_WORK` | No | GitHub PAT (classic) with SSO for corporate/work account |
| `GH_WORK_ORGS` | No | Pipe-separated GitHub orgs routed to work token (default: `RIS-Navify-Data-Platform`) |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | No | Git global identity |
| `GIT_USER_EMAIL_WORK` | No | Git email for corporate/work account |
| `BACKUP_PIN` | No | PIN for encrypting/decrypting volume backups |

Codespaces: add as repository secrets. Local: create `config/.env` (copy from `config/.env.example`).

### MCP Servers

Declared in `config/env-config.yaml` (per-environment `mcp_servers` section) — single source of truth. All three setup scripts (`setup-env.sh`, `docker/setup-env.sh`, `setup-local.sh`) use `config-parser.js` to read YAML and sync (add/remove) servers automatically.

### Loop System

Source at `src/`. Docker: `COPY src /opt/loop` + `npm install`, symlinked as `/usr/bin/loop`.

```bash
loop init / update      # Initialize/refresh symlinks in project
loop init --type web    # Init with domain-specific skills (web/devops/docs/fullstack)
loop init --list-types  # Show available project types
loop design             # Interactive brainstorming / design session
loop plan / build / run # Run planning (3 iter), build (99 iter), or both
loop doctor             # Check loop installation health
loop summary / cleanup  # Show run stats / kill dev server processes
```

**Structure**: `src/scripts/` (shell), `src/prompts/`, `src/templates/`, `src/bin/` + `src/lib/` (Node.js CLI).

**Idea seeding**: `loop plan -I` accepts inline text, `@file.md` (read from file), or `https://...` URLs (GitHub issues/PRs via `gh`, generic via `curl`). Resolved by `resolve_idea()` in `loop.sh`.

**Auto-commit**: `ensure_committed()` in `loop.sh` auto-commits after each iteration (prefix `chore(loop):`).

### Adding New Components

**Global npm tools** — 3 files: `.devcontainer/Dockerfile`, `docker/Dockerfile`, `setup-local.sh`.

**Plugins/Skills** — Edit `config/env-config.yaml` (plugins/skills sections). All three setup scripts read via config-parser. Local plugins: add to `config/plugins/dev-marketplace/` + register in `marketplace.json`.

**Local plugin layout**: `plugins/dev-marketplace/<name>/.claude-plugin/plugin.json` + `commands/<cmd>.md` (YAML frontmatter: `allowed-tools`, `description`, `argument-hint`).

### Key Files for Parallel Changes

Setup/sync — apply across all:
- `.devcontainer/setup-env.sh` — DevContainer/Codespaces
- `setup-local.sh` — macOS local (plugins, skills, and MCP)
- `docker/Dockerfile` + `docker/entrypoint.sh` + `docker/setup-env.sh` — Docker
- `README.md` — docs for all deployment options

Loop system: `src/` + `docker/Dockerfile` + `docker/entrypoint.sh`.

Loop CLI flags/defaults: `src/bin/cli.js`, `src/lib/run.js`, `src/scripts/loop.sh`, optionally `src/lib/init.js`. `loop init` skips existing; `loop update` calls `init({ force: true })`.

### Setup Flow

**DevContainer**: start → `setup-env.sh` → SSH/GH auth → Claude config → sync plugins → MCP servers.

**Docker**: start → `entrypoint.sh` → sync `/opt/claude-config` → first-run (`.configured` marker) → `setup-env.sh`. Claude binary installed to `~/.claude/bin/` (volume) at first start, not during build. GH auth via `gh auth login --with-token`.

**Docker volumes** (4): `claude-code-claude-config` (~/.claude), `claude-code-agents-skills` (~/.agents), `claude-code-gemini-config` (~/.gemini), `claude-code-projects` (~/projects).

### File Sync Mapping

| Source | Destination |
|--------|-------------|
| `config/CLAUDE.md.memory` | `~/.claude/CLAUDE.md` |
| `config/plugins/dev-marketplace/` | local plugin marketplace |

### Codebase Patterns

**Setup scripts & config:**
- **Setup scripts architecture**: Shared functions in `config/scripts/setup-common.sh`, sourced by three adapters (`.devcontainer/setup-env.sh`, `docker/setup-env.sh`, `setup-local.sh`). Each adapter sets required variables (see contract at top of `setup-common.sh`), sources the library, defines env-specific functions, and runs `main()`. Edit only `setup-common.sh` for plugin/skill/MCP changes. Requires Bash 4+.
- **Setup scripts must be non-fatal**: Writes to dotfiles use `|| warn` / `|| true`. Don't block plugin/MCP setup on non-essential ops.
- **Shell helpers**: `ok()`, `warn()`, `fail()` for colored status output in setup scripts.
- **Config parser**: `src/lib/config-parser.js` reads `config/env-config.yaml`, merges defaults with environment overrides, interpolates `${VAR}`. CLI: `node config-parser.js --config <path> --env <env> --section <name>` or `--all`. YAML configs: `env-config.yaml` (real, private), `env-config.example.yaml` (template, public).
- **Config parser path timing**: In `setup-env.sh`, `CONFIG_PARSER`/`CONFIG_FILE` must be set inside `detect_workspace_folder()`, not at script top-level — `WORKSPACE_FOLDER` is unset until that function runs. In `setup-local.sh`, they're set at top-level using `$CONFIG_DIR` (`$SCRIPT_DIR/config`) which is available immediately.
- **Skills install**: `npx -y skills add "$url" --skill "$name" --agent claude-code -g -y`

**Docker & containers:**
- **EXDEV gotcha**: `~/.claude` is ext4 volume, `/tmp` is tmpfs — `rename()` fails cross-device. Scripts export `TMPDIR="$CLAUDE_DIR/tmp"`.
- **Claude binary in Docker**: Scripts use `CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"; claude() { "$CLAUDE_CMD" "$@"; }` to ensure correct binary.
- **Claude config persistence**: `CLAUDE_CONFIG_DIR=~/.claude` keeps `.claude.json` inside the volume. Set in `devcontainer.json` and `Dockerfile`.
- **UTF-8 locale**: Dockerfile must generate `en_US.UTF-8` locale. Without it, Polish chars in tmux show as `_`.
- **Lazy Playwright**: Docker image ships with system `chromium` package (ARM64 compatible) and sets `AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium`. On x86_64, `ensure-playwright.sh` installs Chromium via Playwright on first `agent-browser` use (PreToolUse hook). On ARM64, the script falls back to system chromium since Chrome for Testing and Playwright lack ARM64 builds. DevContainer retains build-time Playwright install.
- **GPG in container**: Use `--pinentry-mode loopback` with `--passphrase` — without it, gpg tries to launch pinentry dialog which doesn't exist.

**Testing & dev tools:**
- **NODE_ENV gotcha**: DevContainer sets `NODE_ENV=production` which skips `devDependencies` on `npm install`. Use `NODE_ENV=development npm install --prefix src` to install jest and other dev tools.
- **Jest 30 CLI**: Use `--testPathPatterns` (with trailing `s`), not `--testPathPattern`. The old flag is removed in Jest 30.
- **Shell test assert helpers**: `assert_eq`/`assert_contains` in `src/scripts/tests/` increment `TESTS_RUN` internally — don't also increment manually before calling them.

**MCP & integrations:**
- **Coolify MCP limitations**: `base_directory` and `docker_compose_location` not in MCP tool — use `curl -X PATCH` directly.
- **MCP server JSON type**: Remote HTTP MCP servers require `"type": "http"` in `add-json` config, not `"type": "url"` (which silently fails).

**Loop system:**
- **Skill presets**: `src/lib/skill-presets.js` defines project type → skills mapping. `loop init --type` appends to PROMPT_skills_{plan,build}.md. Type persisted in `loop/.type` for `loop update`.
