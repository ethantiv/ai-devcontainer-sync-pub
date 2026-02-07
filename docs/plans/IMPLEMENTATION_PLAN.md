# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 2/14 (14%)

## Goal

Enhance DEV_MODE to support dual deployment (dev/prod) of claude-code on the same Raspberry Pi via Coolify. Beyond disabling the Telegram bot, DEV_MODE must:
1. Differentiate container/service names: `claude-code` (prod) vs `dev-claude-code` (dev)
2. Enable SSH aliases `cc` and `dev-cc` on `mirek@raspberrypi.local` to exec into the correct container
3. All within a single Coolify environment (no separate environments)

## Current Phase

Phase 1: Docker & Compose Configuration

## Phases

### Phase 1: Docker & Compose Configuration
- [x] Add `APP_NAME` to `container_name` and `hostname` in `docker-compose.yml` (lines 7-8) — done in commit `e35738e`
- [x] Add `DEV_MODE` implementation: entrypoint.sh (line 130-135), config.py (line 53), run.py (lines 23-25), 6 tests — done in commit `4f3d756`
- [ ] Parameterize image name in `docker-compose.yml` using `APP_NAME`: change `image: claude-code:latest` → `image: ${APP_NAME:-claude-code}:latest` (line 6)
- [ ] Parameterize volume names in `docker-compose.yml` — both service-level mounts (lines 13-17) and top-level `name:` fields (lines 30-37) — to use `${APP_NAME:-claude-code}` prefix (e.g. `${APP_NAME:-claude-code}-claude-config`)
- [ ] Add `APP_NAME=claude-code` to `docker/.env` (currently absent; needed for local `docker compose` usage)
- [ ] Add `APP_NAME` to `docker/.env.example` with comment explaining dev vs prod values
- [ ] Update README.md Docker Volumes table to reflect parameterized volume names
- **Status:** in_progress
- **Note:** Do NOT add `DEV_MODE` to `docker/.env` — it must only be set as a Coolify per-app env var to avoid branch conflicts

### Phase 2: Coolify Dev Application Deployment
- [ ] Create new Coolify application `dev-claude-code` via MCP `application` tool with `create_github` action in project `mirek-rpi` (`qgso0gw8ow8kk04o80kscwg8`) / `production` environment, tracking `develop` branch, using GitHub App UUID `x8k4ssgkcgkk0cks0scw0ssg` and server `w8gg4k4wgkw484sg8g84sgco`
- [ ] Provide `docker_compose_raw` at creation time with service name `dev-claude-code` (cannot be PATCHed later) — copy current compose content but change the `services:` key from `claude-code` to `dev-claude-code`
- [ ] Set `base_directory: /docker` and `docker_compose_location: /docker-compose.yml` via PATCH API (not available in MCP tool — use `curl -X PATCH`)
- [ ] Configure Coolify env vars for dev app: `DEV_MODE=true`, `APP_NAME=dev-claude-code`, plus all other env vars from production app (GH_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc.)
- [ ] Deploy and verify dev app starts correctly with isolated volumes (Coolify auto-prefixes with UUID), DEV_MODE skips Telegram bot, container name prefix is `dev-claude-code-`
- **Status:** pending

### Phase 3: SSH Aliases on Raspberry Pi
- [ ] Create shell functions `cc` and `dev-cc` in `mirek@raspberrypi.local:~/.bash_aliases` (or `~/.bashrc`) that resolve the full container name via `docker ps --format '{{.Names}}' | grep "^claude-code-"` (for `cc`) and `grep "^dev-claude-code-"` (for `dev-cc`), then exec into it with `docker exec -it <name> bash`. Note: `docker ps --filter "name=^..."` has a known bug with `^` anchor — use grep instead
- **Status:** pending

### Phase 4: Documentation & Verification
- [ ] Update CLAUDE.md: add dual deployment pattern, APP_NAME volume parameterization, dev app UUID, SSH aliases documentation
- [ ] Update README.md: add dual deployment instructions in Coolify section, document `cc`/`dev-cc` SSH aliases
- [ ] Run all tests (151 Python + 20 JS) to verify no regressions from compose changes
- **Status:** pending

## Key Questions

### Q1: How does Coolify name containers?
**Answer:** Coolify uses pattern `{service_name}-{resource_uuid}-{timestamp}`. The service name comes from the `services:` key in docker-compose.yml. Coolify **overrides** the `container_name` directive with its own naming. Verified from production app: `claude-code-mcggwo0co804sccscwkggswc-181751248290`.

### Q2: Can the docker-compose service name be parameterized?
**Answer:** No. Docker Compose does not support environment variables in service name keys (`services:` section). The service name is a YAML key, not a value.

### Q3: How to get different service names for dev and prod?
**Answer:** Use Coolify's `docker_compose_raw` field when creating the dev application. This field stores the compose content that Coolify uses (separate from the git repo file). Set the service name to `dev-claude-code` in the raw compose for the dev app. Note: `docker_compose_raw` cannot be PATCHed after creation — must be set correctly at app creation time.

### Q4: Are volumes isolated between Coolify apps?
**Answer:** Yes. Coolify prefixes all volume names with the application UUID: `{uuid}_volume-name`. Each app gets its own isolated volumes. Verified from production: `mcggwo0co804sccscwkggswc_claude-config`.

### Q5: Can both apps use the same `docker/.env` file?
**Answer:** Yes, the `.env` file in git is the same for both. But each Coolify app has its own environment variables set via the Coolify API/UI. The dev app will have `DEV_MODE=true` set as a Coolify env var, overriding anything in the git `.env` file.

### Q6: Do we need separate Coolify environments?
**Answer:** No. ROADMAP.md explicitly states this must work within a single Coolify environment. Both apps will be in `mirek-rpi` project / `production` environment, just tracking different branches (main vs develop).

### Q7: Will `cc` alias on RPi host conflict with `cc` alias inside the container?
**Answer:** No. The RPi host alias (`cc` → `docker exec`) and the in-container alias (`cc` → `clear && claude`) live in different scopes. The host alias runs `docker exec` which opens a shell inside the container, where the in-container alias is then available. No renaming needed.

### Q8: How to reliably match container names by prefix?
**Answer:** `docker ps --filter "name=^..."` has a known bug where the `^` anchor doesn't work as expected ([docker/cli#1201](https://github.com/docker/cli/issues/1201)). Use `docker ps --format '{{.Names}}' | grep "^claude-code-"` instead. For `cc`: pipe through `grep "^claude-code-"` (excludes `dev-claude-code-` because of `^` anchor in grep). For `dev-cc`: `grep "^dev-claude-code-"`.

## Findings & Decisions

### Requirements

From ROADMAP.md:
1. **Container naming**: Image, container, and service names must differ between prod (`claude-code`) and dev (`dev-claude-code`)
2. **SSH aliases**: `cc` and `dev-cc` must work on `mirek@raspberrypi.local` for both containers, resolving by container name prefix (since Coolify adds random suffixes)
3. **Coolify deployment**: Research and implement correct dual deployment within a single environment
4. **Single environment constraint**: No separate Coolify environments — both apps in one environment on the same Raspberry Pi

### Research Findings

**Coolify Container Naming** (verified from production app API response):
- Container name: `claude-code-mcggwo0co804sccscwkggswc-181751248290`
- Pattern: `{service_name}-{uuid}-{timestamp}`
- Coolify sets env vars: `COOLIFY_BRANCH`, `COOLIFY_RESOURCE_UUID`, `COOLIFY_CONTAINER_NAME`, `SERVICE_NAME_CLAUDE_CODE`

**Coolify Volume Isolation** (verified):
- All volumes prefixed with app UUID: `mcggwo0co804sccscwkggswc_claude-config`
- Complete isolation between apps — no shared state

**Coolify docker_compose_raw** (from memory + API):
- `docker_compose_raw` field stores the compose YAML that Coolify parsed from git
- Coolify resolves `${APP_NAME:-claude-code}` → `claude-code` at parse time
- Cannot be PATCHed after creation (API limitation)
- For dev app: must set correct compose with `dev-claude-code` service name at creation time

**Coolify Network Isolation**:
- Each app gets its own Docker network named after the UUID
- No network conflicts between dev and prod

**Existing DEV_MODE Implementation** (already working, 6 tests in test_config.py):
- `docker/entrypoint.sh:130-135` — bash-level check via `${DEV_MODE,,}` lowercase + regex, skips Telegram bot
- `src/telegram_bot/config.py:53` — Python-level `DEV_MODE` boolean via `_is_truthy()`
- `src/telegram_bot/run.py:23-25` — graceful exit with code 0, prints `MSG_DEV_MODE_SKIP`
- Accepts `true`, `1`, `yes` (case-insensitive)
- Tests: `TestDevMode` class (test_config.py) — 6 tests covering all truthy/falsy values and validation warnings

**Existing APP_NAME Implementation** (partially working):
- `docker-compose.yml:7-8` — `${APP_NAME:-claude-code}` for `container_name` and `hostname`
- But Coolify **overrides** `container_name` — APP_NAME only affects hostname
- APP_NAME not currently in `docker/.env` or `docker/.env.example`

**Current docker-compose.yml Gaps** (verified via code review):
- `image: claude-code:latest` (line 6) — hardcoded, NOT parameterized with APP_NAME
- Volume names hardcoded: `claude-config`, `agents-skills`, `gemini-config`, `projects` (lines 13-17, 30-37) — no APP_NAME prefix
- Volume `name:` fields also hardcoded (lines 31, 33, 35, 37)
- These must be parameterized for local `docker compose` dual usage (Coolify adds its own UUID prefix regardless)

**Current Aliases** (only `cc` inside container):
- `docker/Dockerfile:94` — `alias cc='clear && claude'` (inside container)
- `docker/setup-claude.sh:36` — `alias cc='clear && claude'` + `ccc` and `ccr` variants
- `.devcontainer/setup-env.sh:124-127` — same aliases for DevContainer
- These are aliases **inside** the container (for running claude), NOT SSH aliases on RPi host
- No `dev-cc` alias exists anywhere
- ROADMAP requires **host-level aliases** on RPi for `docker exec` into containers

**Codebase Quality** (verified via code review, 2026-02-07):
- No TODOs, FIXMEs, or placeholder implementations found in `src/` or `docker/`
- No skipped or expected-failure tests
- Test count: 151 Python tests (52 config + 20 git_utils + 33 projects + 46 tasks) + 20 JS tests = 171 total
- No existing tests for Coolify deployment configuration or APP_NAME parameterization

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use `docker_compose_raw` with different service name for dev app | Docker Compose doesn't support variable interpolation in service name keys; Coolify names containers from service name |
| Parameterize image name with `APP_NAME` in compose | Allows dev and prod to have distinct image names (`claude-code:latest` vs `dev-claude-code:latest`), avoids image confusion on the same Docker host |
| Parameterize volume names with `APP_NAME` prefix in compose | Even though Coolify adds UUID prefix, explicit naming helps with local `docker compose` usage and clarity |
| SSH aliases use `docker ps --format` piped to `grep` | `docker ps --filter "name=^..."` has known `^` anchor bug; `grep "^claude-code-"` is reliable for prefix matching and avoids matching `dev-claude-code-` |
| DEV_MODE set as Coolify env var (not in git `.env`) | The `.env` in git is shared between branches; Coolify per-app env vars provide clean separation |
| Keep both apps in same Coolify project/environment | Explicit requirement from ROADMAP.md; Coolify UUID-based isolation makes this safe |
| No new tests needed for compose parameterization | Volume/image name changes are Docker Compose interpolation — tested by `docker compose config` during deployment, not unit-testable |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| `docker_compose_raw` not PATCHable via API | Must set correct compose at app creation time via Coolify MCP `application` tool with `create_github` action |
| Coolify overrides `container_name` from compose | Container name prefix comes from service name in compose, not from `container_name` field |
| `APP_NAME` resolved at Coolify parse time | Coolify resolves env vars in compose YAML during parsing; `${APP_NAME:-claude-code}` becomes `claude-code` in `docker_compose_raw` — so dev compose must have `dev-claude-code` hardcoded as service name in `docker_compose_raw` |
| `base_directory`/`docker_compose_location` not in MCP tool | Must use `curl -X PATCH` against Coolify API directly to set these fields |
| `cc` alias collision | Inside-container alias `cc='clear && claude'` and RPi host alias `cc` for `docker exec` are in different scopes — no conflict |

### Resources

- Coolify docs: Docker Compose Build Packs — https://coolify.io/docs/applications/build-packs/docker-compose
- Coolify docs: Docker Compose Knowledge Base — https://coolify.io/docs/knowledge-base/docker/compose
- Coolify docs: Environment Variables — https://coolify.io/docs/knowledge-base/environment-variables
- Coolify API: Create Application — https://coolify.io/docs/api-reference/api/operations/create-private-github-app-application
- GitHub Discussion: Container naming — https://github.com/coollabsio/coolify/discussions/3231
- GitHub Issue: Container name env var — https://github.com/coollabsio/coolify/issues/2545
