# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 9/17 (53%)
**Last Verified:** 2026-02-09

## Goal

Implement current proposals from docs/ROADMAP.md: Feature 1 (High priority) consolidate duplicate .env files into single root .env, and Feature 2 (Medium priority) add Google Stitch MCP server and 6 skills. Feature 1 is a prerequisite for Feature 2's clean .env.example integration.

## Current Phase

Phase 2: Google Stitch Integration

## Phases

### Phase 1: Consolidate .env Files (Feature 1 - High Priority)
- [x] Create `.env.example` at repo root merging all variables
- [x] Update `.devcontainer/devcontainer.json`: `--env-file .env`
- [x] Update `docker/docker-compose.yml`: `env_file: - ../.env`
- [x] Update `docker/docker-compose.dev.yml`: `env_file: - ../.env`
- [x] Update `.devcontainer/setup-env.sh` `load_env_file()` path
- [x] Delete `.devcontainer/.env.example` and `docker/.env.example`
- [x] Update `README.md` .env references
- [x] Update `CLAUDE.md` .env reference
- [x] Run full test suite (458 tests) — all passing
- **Status:** complete

### Phase 2: Google Stitch Integration (Feature 2 - Medium Priority)
- [ ] Add 6 Stitch skill lines to `.devcontainer/configuration/skills-plugins.txt` in a new `# Google Stitch` section (after existing skills): `design-md`, `react:components`, `stitch-loop`, `enhance-prompt`, `remotion`, `shadcn-ui` — format: `- https://github.com/google-labs-code/stitch-skills --skill <name>`
- [ ] Add conditional Stitch MCP server block to `.devcontainer/setup-env.sh` after coolify block (after line 432): wrap in `if [[ -n "${STITCH_API_KEY:-}" ]]; then ... fi` guard, use `url` type with `headers` field (`X-Goog-Api-Key`), endpoint `https://stitch.googleapis.com/mcp`. Note: existing servers (context7 lines 415-422, coolify lines 424-432) use unconditional interpolation, but Stitch needs explicit guard because `url` type with empty header would fail
- [ ] Add same conditional Stitch MCP server block to `docker/setup-claude.sh` after coolify block (between lines 381-382, before closing `}` of `setup_mcp_servers()`). Docker script has only 2 MCP servers (context7 lines 364-371, coolify lines 373-381) vs DevContainer's 4
- [x] Add `STITCH_API_KEY` to root `.env.example` (done in Phase 1)
- [ ] Update `CLAUDE.md`: add `, stitch (needs STITCH_API_KEY, remote HTTP)` to MCP servers list (line 55); add `STITCH_API_KEY` row to env vars table (after `COOLIFY_ACCESS_TOKEN`)
- [ ] Update `README.md`: add `, Stitch` to MCP servers mention (line 10); add `STITCH_API_KEY` row to env vars table (lines 170-188)
- [ ] Add `STITCH_API_KEY` env var to Coolify apps via MCP tool: prod (`mcggwo0co804sccscwkggswc`) and dev (`fg0ksg8wsgw0gs4wk0wkws08`)
- [ ] Run validation: `claude mcp list` to verify Stitch MCP server appears (requires `STITCH_API_KEY` set), verify skills install via `skills-plugins.txt`
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
| Are there any existing Stitch skills installed? | No — `skills-plugins.txt` has 20 items (10 official plugins + 10 external skills), none from Stitch. Note: `remotion-best-practices` skill exists from `remotion-dev/skills` — different from Stitch's `remotion` skill (from `google-labs-code/stitch-skills`) |
| Does `setup-local.sh` need Stitch MCP? | No — `setup-local.sh` handles only plugins and skills, no MCP servers. The `- <url> --skill <name>` format in `skills-plugins.txt` is auto-parsed by `setup-local.sh` (line 361-366). No script changes needed — adding skills to `skills-plugins.txt` is sufficient |
| How many total tests exist currently? | 438 Python + 20 JS = 458 total. All passing, no skips/xfails |
| Do existing MCP servers use conditional guards? | No — context7 and coolify use unconditional `add_mcp_server` calls with `${VAR:-}` interpolation (empty string if unset). Stitch needs explicit `if [[ -n ... ]]` guard because `url` type with empty `X-Goog-Api-Key` header would create a non-functional server |
| Are there any TODOs/FIXMEs/placeholders in the codebase? | No — zero development markers found. Codebase is clean and production-ready |

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

- **Dual .env files**: `.devcontainer/.env` (6 vars) and `docker/.env` (10 vars) with 5 overlapping variables. Total unique vars: 13 (including `STITCH_API_KEY`)
- **Docker Compose env_file resolution**: `env_file: - .env` resolves relative to compose file location (`docker/`). Changing to `../.env` points to repo root
- **DevContainer --env-file**: Path in `runArgs` is relative to workspace root. Currently `.devcontainer/.env`, needs to become `.env`
- **setup-env.sh load_env_file()**: Lines 63-69 hardcode path to `$WORKSPACE_FOLDER/.devcontainer/.env`. Needs path update only
- **Docker Compose variable substitution**: `${APP_NAME:-claude-code}` used in volume names (lines 31-37). Works from CWD `.env` — running from root with `-f` flag reads root `.env` automatically
- **Stitch MCP server type**: `url` type (not stdio) — first remote HTTP MCP server in the project. Uses `headers` field for API key auth, different from existing stdio servers using `env` field
- **Existing MCP server pattern**: DevContainer has 4 servers (aws-documentation, terraform, context7, coolify); Docker has 2 (context7, coolify). None use explicit conditional guards — variables are interpolated via `'"${VAR:-}"'` in JSON (empty if unset). Stitch needs explicit `if [[ -n ... ]]` guard because `url` type with empty auth header is invalid
- **Skills install format**: `skills-plugins.txt` uses `- https://github.com/owner/repo --skill name` format. Stitch skills from `google-labs-code/stitch-skills` repo
- **Codebase clean**: Zero TODO/FIXME/HACK comments, zero skipped tests, zero NotImplementedError. 458 tests all passing
- **No functional code changes needed**: Both features are configuration-only (setup scripts, env files, documentation). No Python/JS source code changes required
- **Coolify apps already have STITCH_API_KEY**: Present in both .env files but not confirmed in Coolify MCP env vars
- **Verified line numbers (2026-02-09 scan)**: devcontainer.json:54, setup-env.sh load_env_file:63-69, setup-env.sh MCP servers:396-432, setup-claude.sh add_mcp_server:345-359 MCP servers:364-381, docker-compose.yml env_file:9-10, docker-compose.dev.yml env_file:9-10, CLAUDE.md .env ref:51 MCP list:55, README.md .env refs:20,24,34-35,168 MCP list:10
- **Test suite verified**: 458 tests (438 Python in 6 files + 20 JS in 1 file), zero skips, zero xfails, zero flaky markers. No test changes needed for config-only features
- **No TODO/FIXME/HACK/NotImplementedError/placeholder/stub** found anywhere in codebase. All STITCH references are in docs/plans only (not in config files yet)

### Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Feature 1 before Feature 2 | ROADMAP explicitly marks Feature 1 as "prerequisite for clean Stitch integration". Avoids having to update .env.example twice |
| `env_file: - ../.env` (relative path) | Docker Compose resolves relative to compose file. `../.env` correctly points to repo root from `docker/` subdirectory |
| `--env-file .env` (workspace-relative) | DevContainer `runArgs` paths are relative to workspace root. Simple `.env` is clearest |
| Keep `docker/.env` and `.devcontainer/.env` files until Phase 1 is validated | Don't delete actual .env files (gitignored, contain secrets) — only delete `.env.example` templates. Users migrate their own .env to root |
| Stitch MCP as `url` type (not stdio) | ROADMAP specifies remote HTTP endpoint at `https://stitch.googleapis.com/mcp`. No local binary/npx dependency needed |
| Conditional on `STITCH_API_KEY` | Matches existing pattern for optional MCP servers (context7 conditional on `CONTEXT7_API_KEY`). Stitch server only added when key is available |
| All 6 skills in one `skills-plugins.txt` section | ROADMAP lists all 6 from same repo. Group together with `# Google Stitch` comment header for maintainability |
| Explicit `if` guard for Stitch MCP (not unconditional interpolation) | Existing stdio servers tolerate empty env vars; `url` type with empty `X-Goog-Api-Key` header would add a non-functional server. Explicit guard prevents this |
| No `setup-local.sh` changes needed for Phase 2 | Verified: `setup-local.sh` auto-parses `- <url> --skill <name>` format from `skills-plugins.txt`. Adding skills to the file is sufficient |
| Keep `remotion-best-practices` alongside Stitch's `remotion` | Different skills from different repos — `remotion-best-practices` (from `remotion-dev/skills`) vs `remotion` (from `google-labs-code/stitch-skills`). Both provide value, no conflict |

### Issues Encountered
| Issue | Resolution |
|-------|------------|
| Docker Compose reads .env from CWD, not compose file location | After consolidation, instruct users to run `docker compose -f docker/docker-compose.yml up -d` from repo root. CWD = repo root, so `.env` is found for variable substitution |
| `.env.example` at both locations must be merged | Root `.env.example` combines all 13 unique vars with comments explaining which are required and which are deployment-specific |
| Stitch MCP uses different type than existing servers | Existing servers use `stdio` with `command`/`args`. Stitch uses `url` with `headers`. Both are valid MCP types — `add_mcp_server` function handles any JSON config |
| `docker/.env` has unquoted values with spaces | `GIT_USER_NAME=Miroslaw Zaniewicz` — root `.env` should document quoting requirement. `setup-env.sh` uses `source` which handles this with `set -a` |

### Resources
- [Stitch MCP Setup](https://stitch.withgoogle.com/docs/mcp/setup)
- [Stitch Skills Repository](https://github.com/google-labs-code/stitch-skills)
- [Stitch API Keys Announcement](https://x.com/stitchbygoogle/status/2016567646180041166)
- Docker Compose env_file documentation — path resolution rules
- DevContainer runArgs documentation — env-file path behavior
