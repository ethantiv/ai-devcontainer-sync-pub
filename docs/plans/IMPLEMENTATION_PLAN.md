# Implementation Plan

**Status:** IN_PROGRESS
**Progress:** 0/10 (0%)

## Goal

Enhance DEV_MODE to support dual deployment (dev/prod) of claude-code on the same Raspberry Pi via Coolify. Beyond disabling the Telegram bot, DEV_MODE must:
1. Differentiate container/service names: `claude-code` (prod) vs `dev-claude-code` (dev)
2. Enable SSH aliases `cc` and `dev-cc` on `mirek@raspberrypi.local` to exec into the correct container
3. All within a single Coolify environment (no separate environments)

## Current Phase

Phase 1: Docker & Compose Configuration

## Phases

### Phase 1: Docker & Compose Configuration
- [ ] Add `APP_NAME` env var to `docker/.env` with default value `claude-code`
- [ ] Parameterize image name in `docker-compose.yml` using `APP_NAME` (e.g. `${APP_NAME:-claude-code}:latest`)
- [ ] Update volume names in `docker-compose.yml` to use `APP_NAME` prefix (e.g. `${APP_NAME:-claude-code}-claude-config`)
- [ ] Add `DEV_MODE` to `docker/.env` (default empty/unset for production)
- **Status:** pending

### Phase 2: Coolify Dev Application Deployment
- [ ] Create new Coolify application `dev-claude-code` in project `mirek-rpi` / `production` environment, tracking `develop` branch
- [ ] Set `docker_compose_raw` with service name `dev-claude-code` (instead of `claude-code`) — Coolify uses service name as container name prefix (`{service_name}-{uuid}-{timestamp}`)
- [ ] Configure Coolify env vars for dev app: `DEV_MODE=true`, `APP_NAME=dev-claude-code`
- [ ] Set `base_directory: /docker` and `docker_compose_location: /docker-compose.yml` on dev app
- [ ] Verify dev app deploys correctly with isolated volumes (Coolify auto-prefixes with UUID)
- **Status:** pending

### Phase 3: SSH Aliases on Raspberry Pi
- [ ] Create shell aliases `cc` and `dev-cc` on `mirek@raspberrypi.local` that use `docker exec` with container name prefix matching (`docker ps --filter name=claude-code- | grep -v dev-` for `cc`, `docker ps --filter name=dev-claude-code-` for `dev-cc`)
- **Status:** pending

### Phase 4: Documentation & Verification
- [ ] Update CLAUDE.md with new DEV_MODE capabilities and dual deployment pattern
- [ ] Update README.md Docker section with dev/prod deployment instructions
- [ ] Run all tests (151 Python + 20 JS) to verify no regressions
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

**Existing DEV_MODE Implementation** (already working):
- `docker/entrypoint.sh:132` — bash-level check, skips Telegram bot
- `src/telegram_bot/config.py:53` — Python-level `DEV_MODE` boolean
- `src/telegram_bot/run.py:23-25` — graceful exit with code 0
- Accepts `true`, `1`, `yes` (case-insensitive)

**Existing APP_NAME Implementation** (partially working):
- `docker-compose.yml:7-8` — `${APP_NAME:-claude-code}` for `container_name` and `hostname`
- But Coolify **overrides** `container_name` — APP_NAME only affects hostname
- APP_NAME not currently in `docker/.env`

**Current Aliases** (only `cc` exists):
- `docker/Dockerfile:94` — `alias cc='clear && claude'` (inside container)
- `docker/setup-claude.sh:36` — same alias in bashrc
- These are aliases **inside** the container (for running claude), NOT SSH aliases on RPi host
- No `dev-cc` alias exists anywhere
- ROADMAP requires host-level aliases on RPi for `docker exec` into containers

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use `docker_compose_raw` with different service name for dev app | Docker Compose doesn't support variable interpolation in service name keys; Coolify names containers from service name |
| Parameterize image name with `APP_NAME` in compose | Allows dev and prod to have distinct image names (`claude-code:latest` vs `dev-claude-code:latest`), avoids image confusion on the same Docker host |
| Parameterize volume names with `APP_NAME` prefix in compose | Even though Coolify adds UUID prefix, explicit naming helps with local `docker compose` usage and clarity |
| SSH aliases use `docker ps --filter` with `--format` | Container names have random suffixes from Coolify; need pattern matching on the stable prefix (`claude-code-` vs `dev-claude-code-`) |
| DEV_MODE set as Coolify env var (not in git `.env`) | The `.env` in git is shared between branches; Coolify per-app env vars provide clean separation |
| Keep both apps in same Coolify project/environment | Explicit requirement from ROADMAP.md; Coolify UUID-based isolation makes this safe |

### Issues Encountered

| Issue | Resolution |
|-------|------------|
| `docker_compose_raw` not PATCHable via API | Must set correct compose at app creation time via Coolify MCP `application` tool with `create_github` action |
| Coolify overrides `container_name` from compose | Container name prefix comes from service name in compose, not from `container_name` field |
| `APP_NAME` resolved at Coolify parse time | Coolify resolves env vars in compose YAML during parsing; `${APP_NAME:-claude-code}` becomes `claude-code` in `docker_compose_raw` |

### Resources

- Coolify docs: Docker Compose Build Packs — https://coolify.io/docs/applications/build-packs/docker-compose
- Coolify docs: Docker Compose Knowledge Base — https://coolify.io/docs/knowledge-base/docker/compose
- Coolify docs: Environment Variables — https://coolify.io/docs/knowledge-base/environment-variables
- Coolify API: Create Application — https://coolify.io/docs/api-reference/api/operations/create-private-github-app-application
- GitHub Discussion: Container naming — https://github.com/coollabsio/coolify/discussions/3231
- GitHub Issue: Container name env var — https://github.com/coollabsio/coolify/issues/2545
