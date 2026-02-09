# Implementation Plan

**Status:** COMPLETE
**Progress:** 17/17 (100%)
**Last Verified:** 2026-02-09

## Goal

Implement current proposals from docs/ROADMAP.md: Feature 1 (High priority) consolidate duplicate .env files into single root .env, and Feature 2 (Medium priority) add Google Stitch MCP server and 6 skills. Feature 1 is a prerequisite for Feature 2's clean .env.example integration.

## Current Phase

All phases complete.

## Phases

### Phase 1: Consolidate .env Files (Feature 1 - High Priority)
- **Status:** complete

### Phase 2: Google Stitch Integration (Feature 2 - Medium Priority)
- [x] Add 6 Stitch skill lines to `.devcontainer/configuration/skills-plugins.txt` in a new `# Google Stitch` section
- [x] Add conditional Stitch MCP server block to `.devcontainer/setup-env.sh` after coolify block
- [x] Add same conditional Stitch MCP server block to `docker/setup-claude.sh` after coolify block
- [x] Add `STITCH_API_KEY` to root `.env.example` (done in Phase 1)
- [x] Update `CLAUDE.md`: add Stitch to MCP servers list and `STITCH_API_KEY` to env vars table
- [x] Update `README.md`: add Stitch to MCP servers mention and `STITCH_API_KEY` to env vars table
- [x] Add `STITCH_API_KEY` env var to Coolify apps — already present in both prod and dev
- [x] Run validation: tests passing, config files verified
- **Status:** complete

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Feature 1 before Feature 2 | ROADMAP explicitly marks Feature 1 as "prerequisite for clean Stitch integration" |
| Stitch MCP as `url` type (not stdio) | Remote HTTP endpoint at `https://stitch.googleapis.com/mcp`. No local binary needed |
| Explicit `if` guard for Stitch MCP | `url` type with empty `X-Goog-Api-Key` header would add a non-functional server |
| All 6 skills in one `skills-plugins.txt` section | Same repo, grouped with `# Google Stitch` comment header |
| Keep `remotion-best-practices` alongside Stitch's `remotion` | Different skills from different repos, no conflict |

## Resources
- [Stitch MCP Setup](https://stitch.withgoogle.com/docs/mcp/setup)
- [Stitch Skills Repository](https://github.com/google-labs-code/stitch-skills)
