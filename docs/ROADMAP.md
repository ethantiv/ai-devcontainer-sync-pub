# Roadmap

## Feature 1: Consolidate .env files

**Status**: Proposed
**Priority**: High (prerequisite for clean Stitch integration)

### Problem

Two duplicate `.env` files with overlapping variables:
- `.devcontainer/.env` — used by `devcontainer.json` via `runArgs: ["--env-file", ".devcontainer/.env"]`
- `docker/.env` — used by `docker-compose.yml` via `env_file: - .env` + variable substitution (`${APP_NAME}`)

6 shared variables (`GH_TOKEN`, `CONTEXT7_API_KEY`, `COOLIFY_BASE_URL`, `COOLIFY_ACCESS_TOKEN`, `STITCH_API_KEY`, `RESET_*`) are duplicated. Docker-only vars (`APP_NAME`, `GIT_USER_*`, `TELEGRAM_*`) and DevContainer-only vars (`SSH_PRIVATE_KEY`) differ.

### Solution

Single `.env` at repo root. Merge all variables into one file.

### Changes

| File | Change |
|------|--------|
| `.env.example` (new) | Combined template with all env vars (replaces both `.devcontainer/.env.example` and `docker/.env.example`) |
| `.devcontainer/.env` | Delete (replaced by root `.env`) |
| `.devcontainer/.env.example` | Delete (replaced by root `.env.example`) |
| `docker/.env` | Delete (replaced by root `.env`) |
| `docker/.env.example` | Delete (replaced by root `.env.example`) |
| `.devcontainer/devcontainer.json` | `runArgs`: `"--env-file", ".env"` (was `.devcontainer/.env`) |
| `docker/docker-compose.yml` | `env_file: - ../.env` (was `.env`) |
| `docker/docker-compose.dev.yml` | `env_file: - ../.env` (was `.env`) |
| `README.md` | Update Docker quickstart: `cp .env.example .env` at root, `docker compose -f docker/docker-compose.yml up -d` |
| `CLAUDE.md` | Update env file references |

### Docker workflow change

Before: `cd docker && cp .env.example .env && docker compose up -d`
After: `cp .env.example .env && docker compose -f docker/docker-compose.yml up -d`

Docker Compose reads `.env` from CWD for variable substitution (`${APP_NAME}`), so running from root ensures it picks up the root `.env` automatically.

### Coolify impact

None. Coolify injects env vars from its own settings — `env_file` in compose is irrelevant for Coolify deployments (`.env` is gitignored, doesn't exist in build context).

---

## Feature 2: Google Stitch integration

**Status**: Proposed
**Priority**: Medium

### Overview

Full integration of [Google Stitch](https://stitch.withgoogle.com/) (AI UI design tool). Two components: MCP server for direct API access and 6 agent skills for specialized workflows.

### MCP Server

**Type**: Remote HTTP (no npx/gcloud dependency)
**Auth**: API key via `STITCH_API_KEY` env var

```json
{
  "type": "url",
  "url": "https://stitch.googleapis.com/mcp",
  "headers": {
    "X-Goog-Api-Key": "<STITCH_API_KEY>"
  }
}
```

Conditional — only added when `STITCH_API_KEY` is set (same pattern as other optional MCP servers).

### Skills (6)

All from [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills), installed via `skills-plugins.txt`:

| Skill | Purpose |
|-------|---------|
| `design-md` | Generate DESIGN.md from Stitch projects |
| `react:components` | Convert Stitch screens to React components |
| `stitch-loop` | Multi-page website from single prompt |
| `enhance-prompt` | Refine vague UI ideas into Stitch-optimized prompts |
| `remotion` | Walkthrough videos from Stitch projects |
| `shadcn-ui` | shadcn/ui component integration guidance |

### Changes

| File | Change |
|------|--------|
| `.devcontainer/configuration/skills-plugins.txt` | +6 skill lines (Google Stitch section) |
| `.devcontainer/setup-env.sh` | +`add_mcp_server "stitch"` block (conditional on `STITCH_API_KEY`) |
| `docker/setup-claude.sh` | +`add_mcp_server "stitch"` block (conditional on `STITCH_API_KEY`) |
| `.env.example` | +`STITCH_API_KEY` (part of consolidated .env) |
| `CLAUDE.md` | +`STITCH_API_KEY` env var, `stitch` in MCP servers list |
| `README.md` | +`STITCH_API_KEY` in env vars table, `stitch` in MCP list |

### Coolify env vars

Add `STITCH_API_KEY` to both apps:
- Prod: `mcggwo0co804sccscwkggswc`
- Dev: `fg0ksg8wsgw0gs4wk0wkws08`

### Sources

- [Stitch MCP Setup](https://stitch.withgoogle.com/docs/mcp/setup)
- [Stitch Skills Repository](https://github.com/google-labs-code/stitch-skills)
- [davideast/stitch-mcp](https://github.com/davideast/stitch-mcp) — CLI helper
- [Stitch API Keys Announcement](https://x.com/stitchbygoogle/status/2016567646180041166)
