# Central Environment Configuration — Design Document

> **Date:** 2026-03-20
> **Status:** Approved
> **Scope:** Introduce a single YAML configuration file that consolidates all environment parameters across 3 deployment targets (devcontainer, docker, local).

## Goal

Replace scattered, duplicated configuration (hardcoded values in `devcontainer.json`, custom DSL in `skills-plugins.txt`, repeated bash logic in 3 setup scripts) with a single YAML file that serves as the source of truth for all non-secret environment parameters.

## Current State — Problems

1. **Configuration scattered across files:**
   - Git identity hardcoded in `devcontainer.json` (`containerEnv`)
   - Timezone/locale hardcoded in `devcontainer.json`
   - Plugins, skills, MCP servers in `skills-plugins.txt` (custom DSL)
   - Claude settings (permissions, language) hardcoded identically in 3 setup scripts
   - Projects bind mount path hardcoded in `devcontainer.json`

2. **Custom DSL in `skills-plugins.txt`:**
   - Fragile parsing via `awk`/`sed` in bash
   - Subtle differences between parsers in `setup-env.sh`, `setup-local.sh`, `setup-claude.sh`
   - No schema, no validation, no structured comments

3. **Massive code duplication:**
   - `install_plugin()`, `sync_mcp_servers()`, `apply_claude_settings()` and ~10 other functions nearly identical across 3 scripts
   - Same Claude settings JSON block hardcoded in 3 places

## Design

### Configuration File

**Path:** `.devcontainer/configuration/env-config.yaml`
**Example:** `.devcontainer/configuration/env-config.example.yaml` (placeholder values for new developers)

**Git tracking:** `env-config.yaml` (with real user data) is committed to the private repository. The mirror workflow (`.github/workflows/mirror-repository.yml`) excludes it from the public repo via `git rm`. Only `env-config.example.yaml` is visible in the mirror.

### Structure

The full YAML below reflects the complete contents of the current `skills-plugins.txt` plus all hardcoded values being migrated.

```yaml
defaults:
  git:
    personal:
      name: "Miroslaw Zaniewicz"
      email: "mirek@example.com"
    work:
      email: "mirek.roche@example.com"
      orgs: "RIS-Navify-Data-Platform"

  timezone: "Europe/Warsaw"
  locale: "pl_PL.UTF-8"

  claude:
    language: "Polski"
    permissions:
      allow:
        - "Bash(npm*)"
        - "Bash(npx*)"
        # ... full current permissions list from setup scripts

  plugins:
    # Official marketplace (anthropics/claude-plugins-official)
    marketplace:
      - agent-sdk-dev
      - atlassian
      - claude-code-setup
      - claude-md-management
      - code-simplifier
      - commit-commands
      - explanatory-output-style
      - feature-dev
      - frontend-design
      - hookify
      - playground
      - plugin-dev
      - skill-creator
      - superpowers
    # LSP plugins (official marketplace)
    lsp:
      - jdtls-lsp
      - pyright-lsp
      - rust-analyzer-lsp
      - typescript-lsp
    # External marketplace sources
    external:
      - name: dev-marketplace
        type: dev-marketplace
        source: ethantiv/dev-marketplace

  skills:
    - url: "https://github.com/anthropics/skills"
      name: docx
    - url: "https://github.com/anthropics/skills"
      name: pdf
    - url: "https://github.com/anthropics/skills"
      name: xlsx
    - url: "https://github.com/hashicorp/agent-skills"
      name: refactor-module
    - url: "https://github.com/hashicorp/agent-skills"
      name: terraform-style-guide
    - url: "https://github.com/hashicorp/agent-skills"
      name: terraform-test
    - url: "https://github.com/intellectronica/agent-skills"
      name: beautiful-mermaid
    - url: "https://github.com/nicobailon/visual-explainer"
      name: visual-explainer
    - url: "https://github.com/softaworks/agent-toolkit"
      name: humanizer
    - url: "https://github.com/softaworks/agent-toolkit"
      name: mermaid-diagrams
    - url: "https://github.com/vercel-labs/agent-browser"
      name: agent-browser
    - url: "https://github.com/vercel-labs/agent-skills"
      name: vercel-composition-patterns
    - url: "https://github.com/vercel-labs/agent-skills"
      name: vercel-react-best-practices
    - url: "https://github.com/vercel-labs/agent-skills"
      name: web-design-guidelines
    - url: "https://github.com/vercel-labs/skills"
      name: find-skills

environments:
  devcontainer:
    projects_path: /home/vscode/projects
    projects_bind_mount: "/Users/mirek/Projekty"
    mcp_servers:
      - name: context7
        type: stdio
        command: npx
        args: ["-y", "@upstash/context7-mcp"]
        env:
          CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"
      - name: coolify
        type: stdio
        command: npx
        args: ["-y", "@masonator/coolify-mcp@latest"]
        env:
          COOLIFY_BASE_URL: "${COOLIFY_BASE_URL}"
          COOLIFY_ACCESS_TOKEN: "${COOLIFY_ACCESS_TOKEN}"
      - name: aws-documentation
        type: stdio
        command: uvx
        args: ["awslabs.aws-documentation-mcp-server@latest"]
        env:
          FASTMCP_LOG_LEVEL: "ERROR"
          AWS_DOCUMENTATION_PARTITION: "aws"
      - name: terraform
        type: stdio
        command: uvx
        args: ["awslabs.terraform-mcp-server@latest"]
        env:
          FASTMCP_LOG_LEVEL: "ERROR"

  docker:
    projects_path: /home/developer/projects
    mcp_servers:
      - name: context7
        type: stdio
        command: npx
        args: ["-y", "@upstash/context7-mcp"]
        env:
          CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"
      - name: coolify
        type: stdio
        command: npx
        args: ["-y", "@masonator/coolify-mcp@latest"]
        env:
          COOLIFY_BASE_URL: "${COOLIFY_BASE_URL}"
          COOLIFY_ACCESS_TOKEN: "${COOLIFY_ACCESS_TOKEN}"

  local:
    projects_path: "~/Projekty"
```

### `projects_bind_mount` — DevContainer Only

The `projects_bind_mount` field is a **documentation-only reference** for the host path used in the `devcontainer.json` `mounts` array. Since `devcontainer.json` does not support variable substitution from external files, the mount path must remain hardcoded in `devcontainer.json`. The parser does NOT consume this field — it exists so the value is centrally documented and visible in the YAML alongside other environment-specific paths. The `env-config.example.yaml` file will note that users must also update `devcontainer.json` if they change this value.

### Local Marketplace Plugins

Local marketplace plugins (in `.devcontainer/plugins/dev-marketplace/`) are NOT declared in `env-config.yaml`. They are auto-discovered from the filesystem via `marketplace.json`, as they are today. The YAML only declares their external source for initial installation (under `plugins.external`).

### Merge Rules

- **Scalars** (timezone, projects_path): environment value overrides default
- **Lists** (plugins, mcp_servers, skills): environment list is **appended** to defaults, deduplicated by `name` field for objects or by value for strings
- Environment-specific sections extend `defaults`, they don't replace it

### Parser — `src/lib/config-parser.js`

A Node.js module (part of the loop package) that reads `env-config.yaml` and outputs merged configuration.

**Dependency:** `js-yaml` added to `src/package.json` as a production dependency (not devDependency), ensuring it is available after `npm install --omit=dev` in Docker.

**Invocation paths per environment:**

| Environment | Parser path | Config path |
|-------------|-------------|-------------|
| DevContainer | `node /workspaces/*/src/lib/config-parser.js` (resolved via `$SCRIPT_DIR`) | `$SCRIPT_DIR/configuration/env-config.yaml` |
| Docker | `node /opt/loop/lib/config-parser.js` | `$CLAUDE_DIR/env-config.yaml` (synced by entrypoint) |
| Local | `node $SCRIPT_DIR/.devcontainer/src/lib/config-parser.js` (resolved from repo root) | `$SCRIPT_DIR/.devcontainer/configuration/env-config.yaml` |

Each setup script resolves the parser path relative to its own known location — no CWD dependency.

**CLI interface** (called from bash scripts):

```bash
# Flat key=value output for simple sections
node "$PARSER" --config "$CONFIG_FILE" --env devcontainer --section git
# GIT_PERSONAL_NAME=Miroslaw Zaniewicz
# GIT_PERSONAL_EMAIL=mirek@example.com
# GIT_WORK_EMAIL=mirek.roche@example.com
# GIT_WORK_ORGS=RIS-Navify-Data-Platform

# JSON output for structured sections
node "$PARSER" --config "$CONFIG_FILE" --env devcontainer --section claude
# { "language": "Polski", "permissions": { ... } }

# JSON array for list sections
node "$PARSER" --config "$CONFIG_FILE" --env docker --section mcp_servers
# [{ "name": "context7", ... }, { "name": "coolify", ... }]

# Full merged config as JSON
node "$PARSER" --config "$CONFIG_FILE" --env devcontainer --all
# { "git": { ... }, "timezone": "...", "claude": { ... }, ... }
```

**Key behaviors:**

- **Variable interpolation:** `${VAR_NAME}` in YAML values resolved from `process.env` at runtime. Unresolved variables become empty strings with a warning on stderr.
- **Validation:** Required fields: `defaults.git.personal.name`, `defaults.git.personal.email`. Clear error message listing missing fields.
- **Config path:** Accepts `--config <path>` flag (explicit path, no discovery needed). Each setup script passes the known absolute path.
- **Git worktrees:** Config discovery (fallback if `--config` not passed) handles both `.git` directories and `.git` files (worktree pointers).
- **Tests:** `src/lib/__tests__/config-parser.test.js`

### Plugin Sync Mapping

The parser outputs plugin data in a format that maps directly to the existing sync functions:

```bash
# Parser outputs JSON array:
# [{"name": "agent-sdk-dev", "type": "marketplace"},
#  {"name": "dev-marketplace", "type": "dev-marketplace", "source": "ethantiv/dev-marketplace"}]

# Bash script builds the expected set:
PLUGINS_JSON=$(node "$PARSER" --config "$CONFIG_FILE" --env "$ENV" --section plugins)
# Then iterates with jq:
echo "$PLUGINS_JSON" | jq -c '.[]' | while read -r plugin; do
  name=$(echo "$plugin" | jq -r '.name')
  type=$(echo "$plugin" | jq -r '.type')
  # ... call install_plugin / sync logic
done
```

The parser flattens `plugins.marketplace` (type: `"marketplace"`), `plugins.lsp` (type: `"marketplace"`), and `plugins.external` (preserves original type/source) into a single array. This replaces the `build_expected_plugins_list()` function.

### `jq` Availability

All three environments need `jq` for consuming parser JSON output:

| Environment | `jq` status |
|-------------|-------------|
| DevContainer | Already installed (base image `devcontainers/base:ubuntu`) |
| Docker | Already installed (`apt-get install jq` in Dockerfile) |
| Local (macOS) | `setup-local.sh` already has `has_command jq` check. Add `brew install jq` to prerequisites if missing, with a clear error message: "jq is required — install with: brew install jq" |

### Timezone and Locale Propagation

Currently `TZ` and `LC_TIME` are set via `containerEnv` in `devcontainer.json` (applied at container creation). After removing them from `containerEnv`:

- **DevContainer/Docker:** `setup-env.sh` / `entrypoint.sh` reads values from YAML via parser and exports them in `~/.bashrc`:
  ```bash
  TZ=$(node "$PARSER" --config "$CONFIG_FILE" --env "$ENV" --section timezone)
  echo "export TZ=\"$TZ\"" >> ~/.bashrc
  ```
  This is consistent with how `GH_TOKEN` and `PATH` are already propagated.

- **Local (macOS):** `setup-local.sh` writes to `~/.bashrc` or `~/.zshrc` similarly.

### Setup Script Migration

Each setup script replaces its DSL parsing with calls to the parser:

```bash
# Before (custom DSL parsing in bash):
parse_mcp_servers "$PLUGINS_FILE" "$ENVIRONMENT_TAG"

# After:
PARSER="/path/to/src/lib/config-parser.js"
CONFIG_FILE="/path/to/env-config.yaml"
CONFIG_JSON=$(node "$PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --all)
GIT_NAME=$(echo "$CONFIG_JSON" | jq -r '.git.personal.name')
```

**What changes in each script:**
- Remove all `skills-plugins.txt` parsing functions (DSL parser, tokenizer)
- Remove hardcoded Claude settings JSON blocks
- Replace with `node config-parser.js` calls + `jq` queries on JSON output
- Plugin install, MCP sync, and other action functions remain in bash — only their **data source** changes

**What does NOT change:**
- Script structure (3 separate files per environment)
- Script flow (SSH -> GH auth -> Claude config -> plugins -> MCP)
- `.env` with secrets
- `CLAUDE.md.memory`
- Tool installation (Dockerfile/brew — stays hardcoded)
- Local marketplace plugin discovery (from `marketplace.json` on filesystem)

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing `env-config.yaml` | Copy from `env-config.example.yaml`, warn user to customize, continue with placeholder values |
| Missing required fields | Parser throws error with list of missing fields |
| Unknown environment (`--env foo`) | Error with list of valid environments: `devcontainer`, `docker`, `local` |
| Unresolved `${VAR}` | Empty string + warning on stderr (non-blocking, consistent with current `requires:` tag behavior) |
| Missing `jq` (macOS) | `setup-local.sh` exits early with install instructions: `brew install jq` |

**Non-fatal philosophy:** Setup never blocks on non-critical errors. Uses `warn()` and continues.

### File Changes Summary

| Action | File | Description |
|--------|------|-------------|
| **Create** | `.devcontainer/configuration/env-config.yaml` | Central config with user data |
| **Create** | `.devcontainer/configuration/env-config.example.yaml` | Template for new developers |
| **Create** | `src/lib/config-parser.js` | YAML parser with merge logic |
| **Create** | `src/lib/__tests__/config-parser.test.js` | Parser tests |
| **Modify** | `src/package.json` | Add `js-yaml` to production dependencies, bump version |
| **Modify** | `.devcontainer/setup-env.sh` | Replace DSL parsing with config-parser calls |
| **Modify** | `setup-local.sh` | Same + add `jq` prerequisite check |
| **Modify** | `docker/setup-claude.sh` | Same |
| **Modify** | `.devcontainer/devcontainer.json` | Remove hardcoded `GIT_USER_NAME`, `GIT_USER_EMAIL`, `TZ`, `LC_TIME` from `containerEnv` |
| **Modify** | `docker/Dockerfile` | Copy `env-config.yaml` instead of `skills-plugins.txt` to `/opt/claude-config/` |
| **Modify** | `docker/entrypoint.sh` | Sync `env-config.yaml` instead of `skills-plugins.txt` to `$CLAUDE_DIR/` |
| **Modify** | `.github/workflows/mirror-repository.yml` | Add `git rm -f .devcontainer/configuration/env-config.yaml` |
| **Modify** | `CLAUDE.md` | Update documentation (skills-plugins.txt references -> env-config.yaml) |
| **Modify** | `README.md` | Update setup instructions |
| **Delete** | `.devcontainer/configuration/skills-plugins.txt` | Replaced by `env-config.yaml` |

### Out of Scope

- `.devcontainer/.env` / `.env.example` (secrets stay separate)
- `.devcontainer/configuration/CLAUDE.md.memory` (markdown, not config)
- VSCode extensions (stay in `devcontainer.json`)
- Claude `statusLine` setting
- Global tool installation (Dockerfile/brew)
- Shell tests for loop system (don't test `skills-plugins.txt` parsing)
- Loop prompts/templates
- Plugin directory structure (`dev-marketplace/`)
