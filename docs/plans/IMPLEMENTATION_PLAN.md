# Central Environment Configuration (env-config.yaml) Implementation Plan

**Status:** COMPLETE

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered DSL-based configuration (`skills-plugins.txt`) and hardcoded values across 3 setup scripts with a single YAML file (`env-config.yaml`) and a Node.js parser.

**Architecture:** A Node.js config-parser module (`src/lib/config-parser.js`) reads `env-config.yaml`, merges `defaults` with environment-specific overrides, and outputs structured JSON. Bash setup scripts call the parser via CLI and consume output with `jq`. The custom DSL in `skills-plugins.txt` is fully replaced.

**Tech Stack:** Node.js (js-yaml), Bash (jq for JSON consumption), Jest 30 (tests)

**Design doc:** `docs/plans/2026-03-20-central-config-design.md`

**Findings & Decisions:**
- All 3 setup scripts (`setup-env.sh`, `setup-claude.sh`, `setup-local.sh`) have nearly identical DSL parsing with subtle differences (associative arrays vs strings, `trim_whitespace()` vs `xargs`, different marketplace dedup strategies). The parser eliminates all of these.
- `apply_claude_settings()` is identical across all 3 scripts — hardcoded JSON with `jq -s '.[0] * .[1]'` merge. Moving `language` and `permissions` to YAML centralizes this. **`statusLine` stays hardcoded** in each script — the design doc explicitly marks it out of scope.
- `devcontainer.json` has hardcoded `GIT_USER_NAME`, `GIT_USER_EMAIL`, `GIT_USER_EMAIL_ROCHE`, `TZ`, `LC_TIME` in `containerEnv`. These move to YAML, with values propagated via `~/.bashrc` exports in setup scripts.
- Current `src/package.json` has only `commander` as production dep. `js-yaml` will be the second. Docker uses `npm install --omit=dev`, so `js-yaml` must be a production dependency.
- Tests use Jest 30 with real filesystem (tmpdir pattern), no fs mocks. Expect ~17 new tests.
- Docker: `skills-plugins.txt` is copied to `/opt/claude-config/` at build, then synced to `~/.claude/` at startup. Same flow applies to `env-config.yaml`.
- **`requires:VAR` behavior change:** The old DSL had `requires:VAR` tags that skipped MCP server registration entirely when the var was unset. The new YAML uses `${VAR}` interpolation which resolves to empty string + stderr warning. MCP servers will now be registered with empty env values instead of being skipped. This is acceptable — `claude mcp add-json` handles empty env values gracefully, and the server will simply fail to connect at runtime (same user-visible outcome).
- **Bash subshell gotcha:** All `while read` loops consuming piped `jq` output must use process substitution (`< <(...)`) instead of pipes to avoid subshell variable scoping issues.
- **Docker `build_expected_plugins_list` bug:** `docker/setup-claude.sh` is missing the `^-` skip guard (present in `setup-env.sh` line 784 and `setup-local.sh` line 484). This means new-format skill lines (`- https://...`) could leak into the expected plugins map. The migration to config-parser eliminates this bug entirely since plugin data comes from structured JSON, not DSL line parsing.
- **Mirror workflow outdated references:** The `.github/workflows/mirror-repository.yml` still references `loop/` directory (renamed to `src/`). This is out of scope but noted for awareness.
- **`setup-local.sh` macOS compatibility:** Uses string variable `_expected_plugins` (newline-separated) instead of `declare -gA` associative arrays. External marketplace type filter requires `*-marketplace` glob suffix. The config-parser migration normalizes all three scripts to the same `jq`-based iteration pattern.
- **Env propagation ordering:** `propagate_env_from_config()` writes env vars to `~/.bashrc` (takes effect in future sessions). `setup_multi_github()` reads `GIT_USER_NAME`/`GIT_USER_EMAIL` from current env. Currently safe because `devcontainer.json` `containerEnv` provides them. When Task 12 removes `containerEnv` values, `propagate_env_from_config()` must either export vars into current session or be called before `setup_multi_github()`.

---

*Phases 1–7 completed and trimmed. See git history for full task details.*

---

## Phase 8: Cleanup, Mirror, and Documentation

**Status:** complete

### Task 13: Delete skills-plugins.txt and update mirror workflow

- [x] Delete `.devcontainer/configuration/skills-plugins.txt`
- [x] Update `.github/workflows/mirror-repository.yml` to exclude `env-config.yaml`

### Task 14: Update CLAUDE.md and README.md

- [x] Update `CLAUDE.md` — replace all `skills-plugins.txt` references with `env-config.yaml`
- [x] Update `README.md` — reflect new configuration approach
