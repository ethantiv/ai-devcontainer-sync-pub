# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/18 (0%)
**Last Verified:** 2026-02-09

## Goal

Implement current proposals from docs/ROADMAP.md: Feature 1 (High priority) consolidate duplicate .env files into single root .env, and Feature 2 (Medium priority) add Google Stitch MCP server and 6 skills. Feature 1 is a prerequisite for Feature 2's clean .env.example integration.

## Current Phase

Phase 1: Consolidate .env Files

## Phases

### Phase 1: Consolidate .env Files (Feature 1 - High Priority)
- [ ] Create `.env.example` at repo root merging all variables from `.devcontainer/.env.example` (5 vars: `GH_TOKEN`, `SSH_PRIVATE_KEY`, `CONTEXT7_API_KEY`, `RESET_CLAUDE_CONFIG`, `RESET_GEMINI_CONFIG`) and `docker/.env.example` (2 vars: `GH_TOKEN`, `APP_NAME`) plus undocumented vars from both `.env` files (`COOLIFY_BASE_URL`, `COOLIFY_ACCESS_TOKEN`, `GIT_USER_NAME`, `GIT_USER_EMAIL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `STITCH_API_KEY`, `DEV_MODE`)
- [ ] Update `.devcontainer/devcontainer.json`: change `runArgs` from `"--env-file", ".devcontainer/.env"` to `"--env-file", ".env"`
- [ ] Update `docker/docker-compose.yml`: change `env_file: - .env` to `env_file: - ../.env`
- [ ] Update `docker/docker-compose.dev.yml`: change `env_file: - .env` to `env_file: - ../.env`
- [ ] Update `.devcontainer/setup-env.sh`: change `load_env_file()` to source from `$WORKSPACE_FOLDER/.env` instead of `$WORKSPACE_FOLDER/.devcontainer/.env`
- [ ] Delete `.devcontainer/.env.example` and `docker/.env.example` (replaced by root `.env.example`)
- [ ] Update `README.md`: Docker quickstart from `cd docker && cp .env.example .env` to `cp .env.example .env && docker compose -f docker/docker-compose.yml up -d`; update env file references throughout (lines 168-189 mentioning `.devcontainer/.env` and `docker/.env`)
- [ ] Update `CLAUDE.md`: change `Local: create .devcontainer/.env` (line 51) to `Local: create .env`; update any other .env path references
- [ ] Run full test suite (438 Python + 20 JS) to verify no regressions
- **Status:** pending

### Phase 2: Google Stitch Integration (Feature 2 - Medium Priority)
- [ ] Add 6 Stitch skill lines to `.devcontainer/configuration/skills-plugins.txt` in a new "Google Stitch" section: `design-md`, `react:components`, `stitch-loop`, `enhance-prompt`, `remotion`, `shadcn-ui` (source: `google-labs-code/stitch-skills`)
- [ ] Add conditional Stitch MCP server block to `.devcontainer/setup-env.sh` in `setup_mcp_servers()` function (after existing servers, conditional on `STITCH_API_KEY`): type `url`, endpoint `https://stitch.googleapis.com/mcp`, auth via `X-Goog-Api-Key` header
- [ ] Add conditional Stitch MCP server block to `docker/setup-claude.sh` in `setup_mcp_servers()` function (same pattern as above)
- [ ] Add `STITCH_API_KEY` to root `.env.example` (created in Phase 1)
- [ ] Update `CLAUDE.md`: add `stitch` to MCP servers list (line 55); add `STITCH_API_KEY` row to env vars table (after `COOLIFY_ACCESS_TOKEN`)
- [ ] Update `README.md`: add `Stitch` to MCP servers mention (line 10); add `STITCH_API_KEY` row to env vars table (lines 170-188)
- [ ] Update `setup-local.sh` if Stitch skills need to be installable locally (check if skills format is compatible with existing `*-marketplace` glob pattern)
- [ ] Add `STITCH_API_KEY` env var to Coolify apps via MCP tool: prod (`mcggwo0co804sccscwkggswc`) and dev (`fg0ksg8wsgw0gs4wk0wkws08`)
- [ ] Run validation: `claude mcp list` to verify Stitch MCP server appears (requires `STITCH_API_KEY` set), verify skills install
- **Status:** pending

## Key Questions

| Question | Answer |
|----------|--------|
| Are the two .env files truly duplicated? | Yes — 5 shared vars (`GH_TOKEN`, `COOLIFY_BASE_URL`, `COOLIFY_ACCESS_TOKEN`, `CONTEXT7_API_KEY`, `STITCH_API_KEY`) duplicated across `.devcontainer/.env` and `docker/.env`. Docker-only: `APP_NAME`, `GIT_USER_NAME/EMAIL`, `TELEGRAM_BOT_TOKEN/CHAT_ID`. DevContainer-only: `SSH_PRIVATE_KEY`, `RESET_*` |
| Does `.gitignore` already cover root `.env`? | Yes — `.gitignore` has `.env` pattern which covers root `.env` |
| Can Feature 2 work without Feature 1? | Technically yes (add `STITCH_API_KEY` to both .env files), but Feature 1 is marked "prerequisite for clean Stitch integration" in ROADMAP. Implementing Feature 1 first avoids documentation debt and duplicate env var management |
| Does Stitch MCP use stdio or HTTP? | HTTP — `type: "url"` with remote endpoint `https://stitch.googleapis.com/mcp`. Different from existing servers (context7/coolify use stdio with npx/uvx). No local dependencies needed |
| Is `STITCH_API_KEY` already in .env files? | Yes — already present in both `.devcontainer/.env` and `docker/.env` with actual values. Missing only from `.env.example` templates and documentation |
| What's the Docker Compose variable substitution concern? | `docker-compose.yml` uses `${APP_NAME:-claude-code}` for volume names. Docker Compose reads `.env` from CWD for substitution. After consolidation, running from repo root with `-f docker/docker-compose.yml` will auto-read root `.env` |
| Does Coolify deployment need changes? | Coolify ignores `env_file` in compose (injects its own env vars). Only action: add `STITCH_API_KEY` env var to both Coolify apps if not already present |
| Are there any existing Stitch skills installed? | No — `skills-plugins.txt` has 10 skills, none from Stitch |
| Does `setup-local.sh` need Stitch MCP? | No — `setup-local.sh` handles only plugins and skills, no MCP servers. Skills from `skills-plugins.txt` will be installed automatically |
| How many total tests exist currently? | 438 Python + 20 JS = 458 total. All passing, no skips/xfails |

## Findings & Decisions

### Requirements

**Feature 1 — Consolidate .env Files (High Priority):**
- Merge `.devcontainer/.env` and `docker/.env` into single root `.env`
- Create root `.env.example` with all variables documented
- Update all references in `devcontainer.json`, `docker-compose.yml`, `docker-compose.dev.yml`, `setup-env.sh`
- Delete old `.env.example` files
- Update documentation (`README.md`, `CLAUDE.md`)
- No Coolify impact (env vars injected separately)

**Feature 2 — Google Stitch Integration (Medium Priority):**
- Add Stitch MCP server (HTTP type, conditional on `STITCH_API_KEY`)
- Add 6 skills from `google-labs-code/stitch-skills` to `skills-plugins.txt`
- Update documentation and `.env.example`
- Add `STITCH_API_KEY` to Coolify apps

### Research Findings

- **Dual .env files**: `.devcontainer/.env` (7 vars) and `docker/.env` (10 vars) with 5 overlapping variables. Total unique vars: 12
- **Docker Compose env_file resolution**: `env_file: - .env` resolves relative to compose file location (`docker/`). Changing to `../.env` points to repo root
- **DevContainer --env-file**: Path in `runArgs` is relative to workspace root. Currently `.devcontainer/.env`, needs to become `.env`
- **setup-env.sh load_env_file()**: Lines 63-69 hardcode path to `$WORKSPACE_FOLDER/.devcontainer/.env`. Needs path update only
- **Docker Compose variable substitution**: `${APP_NAME:-claude-code}` used in volume names (lines 31-37). Works from CWD `.env` — running from root with `-f` flag reads root `.env` automatically
- **Stitch MCP server type**: `url` type (not stdio) — first remote HTTP MCP server in the project. Uses `headers` field for API key auth, different from existing stdio servers using `env` field
- **Existing MCP server pattern**: DevContainer has 4 servers (aws-documentation, terraform, context7, coolify); Docker has 2 (context7, coolify). Context7 uses conditional `[[ -n "${CONTEXT7_API_KEY:-}" ]]` guard — same pattern for Stitch
- **Skills install format**: `skills-plugins.txt` uses `- https://github.com/owner/repo --skill name` format. Stitch skills from `google-labs-code/stitch-skills` repo
- **Codebase clean**: Zero TODO/FIXME/HACK comments, zero skipped tests, zero NotImplementedError. 458 tests all passing
- **No functional code changes needed**: Both features are configuration-only (setup scripts, env files, documentation). No Python/JS source code changes required
- **Coolify apps already have STITCH_API_KEY**: Present in both .env files but not confirmed in Coolify MCP env vars

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Feature 1 before Feature 2 | ROADMAP explicitly marks Feature 1 as "prerequisite for clean Stitch integration". Avoids having to update .env.example twice |
| `env_file: - ../.env` (relative path) | Docker Compose resolves relative to compose file. `../.env` correctly points to repo root from `docker/` subdirectory |
| `--env-file .env` (workspace-relative) | DevContainer `runArgs` paths are relative to workspace root. Simple `.env` is clearest |
| Keep `docker/.env` and `.devcontainer/.env` files until Phase 1 is validated | Don't delete actual .env files (gitignored, contain secrets) — only delete `.env.example` templates. Users migrate their own .env to root |
| Stitch MCP as `url` type (not stdio) | ROADMAP specifies remote HTTP endpoint at `https://stitch.googleapis.com/mcp`. No local binary/npx dependency needed |
| Conditional on `STITCH_API_KEY` | Matches existing pattern for optional MCP servers (context7 conditional on `CONTEXT7_API_KEY`). Stitch server only added when key is available |
| All 6 skills in one `skills-plugins.txt` section | ROADMAP lists all 6 from same repo. Group together with comment header for maintainability |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| Docker Compose reads .env from CWD, not compose file location | After consolidation, instruct users to run `docker compose -f docker/docker-compose.yml up -d` from repo root. CWD = repo root, so `.env` is found for variable substitution |
| `.env.example` at both locations must be merged | Root `.env.example` combines all 12 unique vars with comments explaining which are required and which are deployment-specific |
| Stitch MCP uses different type than existing servers | Existing servers use `stdio` with `command`/`args`. Stitch uses `url` with `headers`. Both are valid MCP types — `add_mcp_server` function handles any JSON config |
| `docker/.env` has unquoted values with spaces | `GIT_USER_NAME=Miroslaw Zaniewicz` — root `.env` should document quoting requirement. `setup-env.sh` uses `source` which handles this with `set -a` |

### Resources
- [Stitch MCP Setup](https://stitch.withgoogle.com/docs/mcp/setup)
- [Stitch Skills Repository](https://github.com/google-labs-code/stitch-skills)
- [Stitch API Keys Announcement](https://x.com/stitchbygoogle/status/2016567646180041166)
- Docker Compose env_file documentation — path resolution rules
- DevContainer runArgs documentation — env-file path behavior
