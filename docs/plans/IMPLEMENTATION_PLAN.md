# Central Environment Configuration (env-config.yaml) Implementation Plan

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

---

## Phase 1: Config Parser Module

**Status:** complete

### Task 1: Add js-yaml dependency and scaffold config-parser.js

- [x] Add `js-yaml` to `src/package.json` dependencies and bump version

Run: `cd /workspaces/ai-devcontainer-sync/src && npm install js-yaml --save`

Verify: `node -e "require('js-yaml')"` in `src/` — should exit 0.

- [x] Create `src/lib/config-parser.js` with YAML loading, merge logic, and variable interpolation

The module exports: `loadConfig(configPath, env)`, `mergeConfig(defaults, envOverrides)`, `interpolateVars(obj)`.

**`loadConfig(configPath, env)`** — reads YAML, validates required fields, merges defaults with environment section, interpolates `${VAR}` from `process.env`.

**`mergeConfig(defaults, envOverrides)`** — scalars: env overrides default. Lists of objects (deduplicated by `name`): env appended to defaults. Lists of strings: env appended, deduplicated by value.

**`interpolateVars(obj)`** — recursively walks the config object, replaces `${VAR_NAME}` patterns in string values with `process.env[VAR_NAME]`. Unresolved vars become empty string + stderr warning.

**Validation:** Required fields: `defaults.git.personal.name`, `defaults.git.personal.email`. Throws with list of missing fields.

```javascript
// src/lib/config-parser.js
const fs = require('fs');
const yaml = require('js-yaml');

function interpolateVars(obj) {
  if (typeof obj === 'string') {
    return obj.replace(/\$\{([^}]+)\}/g, (_, varName) => {
      const val = process.env[varName];
      if (val === undefined) {
        process.stderr.write(`Warning: unresolved variable \${${varName}}\n`);
        return '';
      }
      return val;
    });
  }
  if (Array.isArray(obj)) return obj.map(interpolateVars);
  if (obj && typeof obj === 'object') {
    const result = {};
    for (const [k, v] of Object.entries(obj)) result[k] = interpolateVars(v);
    return result;
  }
  return obj;
}

function mergeConfig(defaults, envOverrides) {
  if (!envOverrides) return { ...defaults };
  const merged = {};
  const allKeys = new Set([...Object.keys(defaults), ...Object.keys(envOverrides)]);
  for (const key of allKeys) {
    const def = defaults[key];
    const env = envOverrides[key];
    if (env === undefined) { merged[key] = def; continue; }
    if (def === undefined) { merged[key] = env; continue; }
    if (Array.isArray(def) && Array.isArray(env)) {
      // Deduplicate by 'name' for objects, by value for strings
      const combined = [...def, ...env];
      if (combined.length > 0 && typeof combined[0] === 'object' && combined[0].name) {
        const seen = new Map();
        for (const item of combined) seen.set(item.name, item);
        merged[key] = [...seen.values()];
      } else {
        merged[key] = [...new Set(combined)];
      }
    } else if (def && typeof def === 'object' && !Array.isArray(def) && env && typeof env === 'object' && !Array.isArray(env)) {
      merged[key] = mergeConfig(def, env);
    } else {
      merged[key] = env; // scalar override
    }
  }
  return merged;
}

const REQUIRED_FIELDS = [
  'git.personal.name',
  'git.personal.email',
];

function getNestedValue(obj, path) {
  return path.split('.').reduce((o, k) => o && o[k], obj);
}

function validateConfig(config) {
  const missing = REQUIRED_FIELDS.filter(f => !getNestedValue(config, f));
  if (missing.length > 0) {
    throw new Error(`Missing required fields: ${missing.join(', ')}`);
  }
}

function loadConfig(configPath, env) {
  const raw = fs.readFileSync(configPath, 'utf8');
  const doc = yaml.load(raw);
  const defaults = doc.defaults || {};
  const environments = doc.environments || {};

  if (env && !environments[env]) {
    const valid = Object.keys(environments).join(', ');
    throw new Error(`Unknown environment "${env}". Valid: ${valid}`);
  }

  const envOverrides = env ? environments[env] : {};
  const merged = mergeConfig(defaults, envOverrides);
  validateConfig(merged);
  return interpolateVars(merged);
}

function flattenSection(obj, prefix = '') {
  const lines = [];
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}_${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      lines.push(...flattenSection(v, key));
    } else {
      lines.push(`${key.toUpperCase()}=${v}`);
    }
  }
  return lines;
}

module.exports = { loadConfig, mergeConfig, interpolateVars, validateConfig, flattenSection };
```

- [x] Bump version in `src/package.json` from `0.9.0` to `0.10.0`

**Files:**
- Modify: `src/package.json` (add js-yaml dep, bump version)
- Create: `src/lib/config-parser.js`

---

### Task 2: Write config-parser tests

- [x] Create `src/lib/__tests__/config-parser.test.js` with tests for all core functions

Test categories:
1. **`interpolateVars`** — resolves `${VAR}`, leaves non-vars alone, warns on unresolved
2. **`mergeConfig`** — scalar override, list append+dedup (strings), list append+dedup (objects by name), recursive object merge, missing sections
3. **`validateConfig`** — passes with required fields, throws listing missing fields
4. **`loadConfig`** — full integration: reads YAML file, merges with environment, interpolates vars, validates
5. **Error cases** — unknown environment, missing file, missing required fields

```javascript
// src/lib/__tests__/config-parser.test.js
const fs = require('fs');
const path = require('path');
const os = require('os');
const { loadConfig, mergeConfig, interpolateVars, validateConfig, flattenSection } = require('../config-parser');

let tmpDir;
beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'config-parser-'));
});
afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

function writeYaml(name, content) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, content);
  return p;
}

describe('interpolateVars', () => {
  test('resolves env vars in strings', () => {
    process.env.TEST_VAR = 'hello';
    expect(interpolateVars('${TEST_VAR}')).toBe('hello');
    delete process.env.TEST_VAR;
  });

  test('warns and returns empty for unresolved vars', () => {
    const stderr = jest.spyOn(process.stderr, 'write').mockImplementation();
    expect(interpolateVars('${NONEXISTENT_VAR_XYZ}')).toBe('');
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining('NONEXISTENT_VAR_XYZ'));
    stderr.mockRestore();
  });

  test('recurses into objects and arrays', () => {
    process.env.TV1 = 'a';
    process.env.TV2 = 'b';
    const result = interpolateVars({ x: '${TV1}', y: ['${TV2}'] });
    expect(result).toEqual({ x: 'a', y: ['b'] });
    delete process.env.TV1;
    delete process.env.TV2;
  });

  test('passes through non-string primitives', () => {
    expect(interpolateVars(42)).toBe(42);
    expect(interpolateVars(true)).toBe(true);
    expect(interpolateVars(null)).toBe(null);
  });
});

describe('mergeConfig', () => {
  test('scalar override', () => {
    expect(mergeConfig({ a: 1 }, { a: 2 })).toEqual({ a: 2 });
  });

  test('appends and deduplicates string arrays', () => {
    expect(mergeConfig({ a: ['x', 'y'] }, { a: ['y', 'z'] }))
      .toEqual({ a: ['x', 'y', 'z'] });
  });

  test('appends and deduplicates object arrays by name', () => {
    const def = [{ name: 'a', v: 1 }, { name: 'b', v: 2 }];
    const env = [{ name: 'b', v: 3 }, { name: 'c', v: 4 }];
    const result = mergeConfig({ items: def }, { items: env });
    expect(result.items).toEqual([
      { name: 'a', v: 1 },
      { name: 'b', v: 3 },  // env overrides
      { name: 'c', v: 4 },
    ]);
  });

  test('deep merges nested objects', () => {
    expect(mergeConfig(
      { git: { personal: { name: 'A' }, work: { email: 'B' } } },
      { git: { personal: { name: 'C' } } }
    )).toEqual({ git: { personal: { name: 'C' }, work: { email: 'B' } } });
  });

  test('handles missing env overrides', () => {
    expect(mergeConfig({ a: 1 }, undefined)).toEqual({ a: 1 });
  });
});

describe('validateConfig', () => {
  test('passes with required fields', () => {
    expect(() => validateConfig({
      git: { personal: { name: 'Test', email: 'test@test.com' } }
    })).not.toThrow();
  });

  test('throws listing missing fields', () => {
    expect(() => validateConfig({ git: {} }))
      .toThrow('git.personal.name');
  });
});

describe('loadConfig', () => {
  test('loads and merges YAML with environment', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  git:
    personal:
      name: Test User
      email: test@example.com
  timezone: UTC
  plugins:
    marketplace:
      - plugin-a

environments:
  devcontainer:
    timezone: Europe/Warsaw
    plugins:
      marketplace:
        - plugin-b
`);
    const result = loadConfig(configPath, 'devcontainer');
    expect(result.timezone).toBe('Europe/Warsaw');
    expect(result.git.personal.name).toBe('Test User');
    expect(result.plugins.marketplace).toEqual(['plugin-a', 'plugin-b']);
  });

  test('throws on unknown environment', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  git:
    personal:
      name: Test
      email: test@test.com
environments:
  devcontainer: {}
`);
    expect(() => loadConfig(configPath, 'unknown'))
      .toThrow('Unknown environment');
  });

  test('throws on missing required fields', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  timezone: UTC
environments: {}
`);
    expect(() => loadConfig(configPath, null))
      .toThrow('git.personal.name');
  });
});

describe('flattenSection', () => {
  test('flattens nested object to KEY=value lines', () => {
    const result = flattenSection({ personal: { name: 'Test', email: 'e@e.com' } });
    expect(result).toContain('PERSONAL_NAME=Test');
    expect(result).toContain('PERSONAL_EMAIL=e@e.com');
  });
});
```

Run: `cd /workspaces/ai-devcontainer-sync/src && npx jest lib/__tests__/config-parser.test.js --verbose`
Expected: All tests pass.

**Files:**
- Create: `src/lib/__tests__/config-parser.test.js`

---

## Phase 2: Config Parser CLI

**Status:** complete

### Task 3: Add CLI interface to config-parser.js

- [x] Add CLI entry point at the bottom of `config-parser.js` for bash script consumption

The CLI is invoked by bash scripts as:
```bash
node config-parser.js --config <path> --env <environment> --section <section>
node config-parser.js --config <path> --env <environment> --all
```

`--section` returns: flat `KEY=value` for simple sections (`git`, `timezone`, `locale`), JSON for structured sections (`claude`, `mcp_servers`, `plugins`, `skills`).

`--all` returns the full merged config as JSON.

```javascript
// Append to src/lib/config-parser.js — CLI block
if (require.main === module) {
  const args = process.argv.slice(2);
  const getArg = (name) => {
    const idx = args.indexOf(`--${name}`);
    return idx >= 0 && idx + 1 < args.length ? args[idx + 1] : null;
  };

  const configPath = getArg('config');
  const env = getArg('env');
  const section = getArg('section');
  const showAll = args.includes('--all');

  if (!configPath) {
    process.stderr.write('Error: --config <path> is required\n');
    process.exit(1);
  }

  try {
    const config = loadConfig(configPath, env);

    if (showAll) {
      process.stdout.write(JSON.stringify(config, null, 2) + '\n');
    } else if (section) {
      const value = config[section];
      if (value === undefined) {
        process.stderr.write(`Error: section "${section}" not found\n`);
        process.exit(1);
      }
      if (typeof value === 'object') {
        process.stdout.write(JSON.stringify(value, null, 2) + '\n');
      } else {
        // Scalar value — flat KEY=value output
        process.stdout.write(`${section.toUpperCase()}=${value}\n`);
      }
    } else {
      process.stderr.write('Error: --section <name> or --all is required\n');
      process.exit(1);
    }
  } catch (err) {
    process.stderr.write(`Error: ${err.message}\n`);
    process.exit(1);
  }
}
```

- [x] Write CLI integration tests

Test the CLI by spawning `node config-parser.js` as a child process with a temp YAML file.

```javascript
// Add to config-parser.test.js
const { execFileSync } = require('child_process');
const parserPath = path.resolve(__dirname, '../config-parser.js');

describe('CLI', () => {
  test('--all returns full merged JSON', () => {
    const configPath = writeYaml('cli.yaml', `
defaults:
  git:
    personal:
      name: CLI Test
      email: cli@test.com
  timezone: UTC
environments:
  devcontainer:
    timezone: Europe/Warsaw
`);
    const output = execFileSync('node', [parserPath, '--config', configPath, '--env', 'devcontainer', '--all'], { encoding: 'utf8' });
    const parsed = JSON.parse(output);
    expect(parsed.timezone).toBe('Europe/Warsaw');
    expect(parsed.git.personal.name).toBe('CLI Test');
  });

  test('--section returns specific section', () => {
    const configPath = writeYaml('cli2.yaml', `
defaults:
  git:
    personal:
      name: Test
      email: t@t.com
  timezone: UTC
environments: {}
`);
    const output = execFileSync('node', [parserPath, '--config', configPath, '--section', 'timezone'], { encoding: 'utf8' });
    expect(output.trim()).toBe('TIMEZONE=UTC');
  });

  test('exits with error on unknown env', () => {
    const configPath = writeYaml('cli3.yaml', `
defaults:
  git:
    personal:
      name: T
      email: t@t.com
environments:
  devcontainer: {}
`);
    expect(() => execFileSync('node', [parserPath, '--config', configPath, '--env', 'bad'], { encoding: 'utf8' }))
      .toThrow();
  });
});
```

Run: `cd /workspaces/ai-devcontainer-sync/src && npx jest lib/__tests__/config-parser.test.js --verbose`
Expected: All tests pass (unit + CLI tests).

**Files:**
- Modify: `src/lib/config-parser.js` (add CLI block)
- Modify: `src/lib/__tests__/config-parser.test.js` (add CLI tests)

---

## Phase 3: YAML Config Files

**Status:** complete

### Task 4: Create env-config.example.yaml

- [x] Create `.devcontainer/configuration/env-config.example.yaml` with placeholder values

Use the structure from the design doc. Replace personal data with placeholders like `Your Name`, `your@email.com`. Add inline comments explaining each section and the merge rules.

**Files:**
- Create: `.devcontainer/configuration/env-config.example.yaml`

Verify: `cd /workspaces/ai-devcontainer-sync/src && node lib/config-parser.js --config ../.devcontainer/configuration/env-config.example.yaml --env devcontainer --all | jq .`
Expected: Valid JSON output with placeholder values.

---

### Task 5: Create env-config.yaml with real data

- [x] Create `.devcontainer/configuration/env-config.yaml` by migrating all current values

Sources to migrate from:
1. **Git identity** — from `devcontainer.json` `containerEnv`: `GIT_USER_NAME`, `GIT_USER_EMAIL`
2. **Timezone/locale** — from `devcontainer.json` `containerEnv`: `TZ`, `LC_TIME`
3. **Claude settings** — from `setup-env.sh:303-316` (`apply_claude_settings`): language, permissions, statusLine
4. **Plugins** — from `skills-plugins.txt` lines 16-35 (official + LSP)
5. **Skills** — from `skills-plugins.txt` lines 42-56
6. **External plugins** — from `skills-plugins.txt` line (external marketplace section — currently none declared in file, but `dev-marketplace` is auto-discovered)
7. **MCP servers** — from `skills-plugins.txt` lines 78-82 (with tags mapping to environments)

Use the exact YAML structure from design doc (section "Structure").

**Files:**
- Create: `.devcontainer/configuration/env-config.yaml`

Verify: `cd /workspaces/ai-devcontainer-sync/src && node lib/config-parser.js --config ../.devcontainer/configuration/env-config.yaml --env devcontainer --all | jq .`
Expected: Full merged config JSON with resolved env vars. Warnings on stderr for unset env vars like `CONTEXT7_API_KEY` are OK.

---

## Phase 4: Plugin Flattening in Parser

**Status:** complete

### Task 6: Add plugin flattening logic to config-parser

- [x] Add `flattenPlugins(config)` function to `config-parser.js`

The YAML has plugins in structured form (`marketplace`, `lsp`, `external`). Setup scripts need a flat array for iteration:
```json
[
  {"name": "agent-sdk-dev", "type": "marketplace"},
  {"name": "jdtls-lsp", "type": "marketplace"},
  {"name": "dev-marketplace", "type": "dev-marketplace", "source": "ethantiv/dev-marketplace"}
]
```

```javascript
function flattenPlugins(config) {
  const plugins = config.plugins || {};
  const result = [];
  for (const name of (plugins.marketplace || [])) {
    result.push({ name, type: 'marketplace' });
  }
  for (const name of (plugins.lsp || [])) {
    result.push({ name, type: 'marketplace' });
  }
  for (const ext of (plugins.external || [])) {
    result.push({ name: ext.name, type: ext.type, source: ext.source });
  }
  return result;
}
```

Export `flattenPlugins` and add `--section plugins_flat` CLI support that returns the flattened array. In the CLI `if (require.main === module)` block, add a special case BEFORE the generic section lookup:

```javascript
      // Special computed section (added by Task 6)
      if (section === 'plugins_flat') {
        process.stdout.write(JSON.stringify(flattenPlugins(config), null, 2) + '\n');
      } else {
        const value = config[section];
        // ... existing generic section handling
      }
```

- [x] Write tests for `flattenPlugins`

```javascript
describe('flattenPlugins', () => {
  test('flattens marketplace, lsp, and external into flat array', () => {
    const config = {
      plugins: {
        marketplace: ['plugin-a', 'plugin-b'],
        lsp: ['ts-lsp'],
        external: [{ name: 'ext1', type: 'dev-marketplace', source: 'owner/repo' }]
      }
    };
    const result = flattenPlugins(config);
    expect(result).toEqual([
      { name: 'plugin-a', type: 'marketplace' },
      { name: 'plugin-b', type: 'marketplace' },
      { name: 'ts-lsp', type: 'marketplace' },
      { name: 'ext1', type: 'dev-marketplace', source: 'owner/repo' },
    ]);
  });

  test('handles missing sections gracefully', () => {
    expect(flattenPlugins({})).toEqual([]);
  });
});
```

Run: `cd /workspaces/ai-devcontainer-sync/src && npx jest lib/__tests__/config-parser.test.js --verbose`
Expected: All tests pass.

**Files:**
- Modify: `src/lib/config-parser.js` (add `flattenPlugins`, update CLI)
- Modify: `src/lib/__tests__/config-parser.test.js` (add flattenPlugins tests)

---

## Phase 5: setup-env.sh Migration

**Status:** pending

### Task 7: Replace DSL-based plugin/skill/MCP parsing in setup-env.sh

- [ ] Add config-parser invocation variables near top of `setup-env.sh`

After the existing constants block (around line 35), add:

```bash
# Config parser (replaces skills-plugins.txt DSL)
CONFIG_PARSER="$WORKSPACE_FOLDER/src/lib/config-parser.js"
CONFIG_FILE="$WORKSPACE_FOLDER/.devcontainer/configuration/env-config.yaml"
```

- [ ] Replace `install_all_plugins_and_skills()` body with config-parser calls

Replace the DSL while-loop (lines ~420-480) with:

```bash
install_all_plugins_and_skills() {
    echo "📦 Installing plugins and skills..."
    local installed=0 skipped=0 failed=0

    # Plugins (flat array from parser)
    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || {
        warn "Failed to parse plugin config"; return 0
    }

    # NOTE: Use process substitution (< <(...)) to avoid subshell variable scoping.
    # Piped while-loops run in subshells where counter/array mutations are lost.
    while IFS= read -r plugin; do
        local name type source
        name=$(echo "$plugin" | jq -r '.name')
        type=$(echo "$plugin" | jq -r '.type')
        source=$(echo "$plugin" | jq -r '.source // empty')

        if [[ "$type" == "marketplace" ]]; then
            install_plugin "${name}@${OFFICIAL_MARKETPLACE_NAME}" < /dev/null
        else
            [[ -n "$source" ]] && ensure_marketplace "$name" "$type" "$source"
            install_plugin "${name}@${type}" < /dev/null
        fi
        update_plugin_counters $? installed skipped failed
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Skills
    local skills_json
    skills_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section skills) || {
        warn "Failed to parse skills config"; return 0
    }

    while IFS= read -r skill; do
        local name url
        name=$(echo "$skill" | jq -r '.name')
        url=$(echo "$skill" | jq -r '.url')
        install_skill "$name" "$url" < /dev/null
    done < <(echo "$skills_json" | jq -c '.[]')

    echo "  Plugins: $installed installed, $skipped skipped, $failed failed"
}
```

- [ ] Replace `parse_mcp_servers()` body with config-parser calls

Replace the DSL while-loop with:

```bash
parse_mcp_servers() {
    local mcp_json
    mcp_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section mcp_servers) || {
        warn "Failed to parse MCP config"; return 0
    }

    # Process substitution to preserve mcp_expected array modifications
    while IFS= read -r server; do
        local name type
        name=$(echo "$server" | jq -r '.name')
        type=$(echo "$server" | jq -r '.type')

        local config_json
        if [[ "$type" == "stdio" ]]; then
            config_json=$(echo "$server" | jq '{type, command, args, env}')
        else
            config_json=$(echo "$server" | jq '{type, url, headers}')
        fi

        mcp_expected+=("$name")
        add_mcp_server "$name" "$config_json"
    done < <(echo "$mcp_json" | jq -c '.[]')
}
```

- [ ] Replace `build_expected_plugins_list()` body with config-parser calls

```bash
build_expected_plugins_list() {
    declare -gA expected_plugins

    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || return 0

    # Process substitution to preserve expected_plugins associative array
    while IFS= read -r plugin; do
        local name type
        name=$(echo "$plugin" | jq -r '.name')
        type=$(echo "$plugin" | jq -r '.type')
        if [[ "$type" == "marketplace" ]]; then
            expected_plugins["${name}@${OFFICIAL_MARKETPLACE_NAME}"]=1
        else
            expected_plugins["${name}@${type}"]=1
        fi
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Local marketplace plugins (auto-discovered, not from YAML)
    local marketplace_json="$WORKSPACE_FOLDER/.devcontainer/plugins/${LOCAL_MARKETPLACE_NAME}/.claude-plugin/marketplace.json"
    if [[ -f "$marketplace_json" ]]; then
        local plugin_names
        plugin_names=$(jq -r '.plugins[].name // empty' "$marketplace_json" 2>/dev/null)
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            expected_plugins["${name}@${LOCAL_MARKETPLACE_NAME}"]=1
        done <<< "$plugin_names"
    fi
}
```

**Files:**
- Modify: `.devcontainer/setup-env.sh`

Verify: `.devcontainer/setup-env.sh` (dry run — the script is non-fatal, check for syntax errors):
```bash
bash -n .devcontainer/setup-env.sh
```
Expected: No syntax errors.

---

### Task 8: Replace hardcoded Claude settings and remove DSL functions from setup-env.sh

- [ ] Replace `apply_claude_settings()` to read from config-parser

```bash
apply_claude_settings() {
    has_command jq || { warn "jq not found - cannot manage settings"; return 0; }

    local claude_config
    claude_config=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section claude) || {
        warn "Failed to parse Claude settings"; return 0
    }

    # statusLine stays hardcoded — design doc marks it out of scope
    local default_settings
    default_settings=$(echo "$claude_config" | jq --argjson sl '{"type":"command","command":"~/.claude/scripts/context-bar.sh"}' '{
        permissions: .permissions,
        language: .language,
        statusLine: $sl
    }')

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    ok "Settings configured"
}
```

- [ ] Add timezone, locale, and git work identity propagation to `setup_claude_configuration()` or `main()`

After `apply_claude_settings`, add environment propagation block. This replaces the hardcoded values previously in `devcontainer.json` `containerEnv`:

```bash
# Propagate timezone, locale, and git work identity from config
propagate_env_from_config() {
    local config_json
    config_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --all 2>/dev/null) || return 0

    local tz locale work_email work_orgs git_name git_email
    tz=$(echo "$config_json" | jq -r '.timezone // empty')
    locale=$(echo "$config_json" | jq -r '.locale // empty')
    git_name=$(echo "$config_json" | jq -r '.git.personal.name // empty')
    git_email=$(echo "$config_json" | jq -r '.git.personal.email // empty')
    work_email=$(echo "$config_json" | jq -r '.git.work.email // empty')
    work_orgs=$(echo "$config_json" | jq -r '.git.work.orgs // empty')

    # Append to ~/.bashrc if not already present (idempotent)
    local bashrc="$HOME/.bashrc"
    [[ -n "$tz" ]] && grep -q "^export TZ=" "$bashrc" 2>/dev/null || echo "export TZ=\"$tz\"" >> "$bashrc"
    [[ -n "$locale" ]] && grep -q "^export LC_TIME=" "$bashrc" 2>/dev/null || echo "export LC_TIME=\"$locale\"" >> "$bashrc"
    [[ -n "$git_name" ]] && grep -q "^export GIT_USER_NAME=" "$bashrc" 2>/dev/null || echo "export GIT_USER_NAME=\"$git_name\"" >> "$bashrc"
    [[ -n "$git_email" ]] && grep -q "^export GIT_USER_EMAIL=" "$bashrc" 2>/dev/null || echo "export GIT_USER_EMAIL=\"$git_email\"" >> "$bashrc"
    [[ -n "$work_email" ]] && grep -q "^export GIT_USER_EMAIL_ROCHE=" "$bashrc" 2>/dev/null || echo "export GIT_USER_EMAIL_ROCHE=\"$work_email\"" >> "$bashrc"
    [[ -n "$work_orgs" ]] && grep -q "^export GH_ROCHE_ORGS=" "$bashrc" 2>/dev/null || echo "export GH_ROCHE_ORGS=\"$work_orgs\"" >> "$bashrc"

    ok "Environment variables propagated to ~/.bashrc"
}
```

This function replaces the hardcoded `containerEnv` values that were previously in `devcontainer.json`. The `setup_multi_github()` function in `setup-env.sh` already reads `GIT_USER_EMAIL_ROCHE` and `GH_ROCHE_ORGS` from environment — now those vars come from `~/.bashrc` instead of `containerEnv`.

- [ ] Remove dead DSL parsing code from `setup-env.sh`

Remove these functions that are no longer called:
- `trim_whitespace()` (~line 53)
- The old `install_all_plugins_and_skills()` body (replaced above)
- The old `parse_mcp_servers()` body (replaced above)
- The old `build_expected_plugins_list()` body (replaced above)
- Any references to `$CLAUDE_PLUGINS_FILE` constant

Keep: `install_plugin()`, `install_skill()`, `install_github_skill()`, `ensure_marketplace()`, `add_mcp_server()`, `build_stdio_json()`, `build_http_json()`, `sync_mcp_servers()`, `sync_plugins()`, `get_installed_plugins()`, `uninstall_plugin()`, `update_plugin_counters()` — these are action functions, not parsers.

Wait — with the new `parse_mcp_servers`, MCP config JSON comes directly from the parser, so `build_stdio_json()` and `build_http_json()` are also no longer needed. Remove them too.

**Files:**
- Modify: `.devcontainer/setup-env.sh`

Verify:
```bash
bash -n .devcontainer/setup-env.sh
```
Expected: No syntax errors.

---

## Phase 6: Docker Migration

**Status:** pending

### Task 9: Update Dockerfile and entrypoint.sh for env-config.yaml

- [ ] Modify `docker/Dockerfile` to copy `env-config.yaml` instead of `skills-plugins.txt`

In Dockerfile, find the line that copies `skills-plugins.txt` to `/opt/claude-config/` and change to:

```dockerfile
COPY .devcontainer/configuration/env-config.yaml /opt/claude-config/env-config.yaml
```

Keep other COPY lines (`CLAUDE.md.memory`, `scripts/`, `plugins/`) unchanged.

- [ ] Modify `docker/entrypoint.sh` to sync `env-config.yaml` instead of `skills-plugins.txt`

In `sync_config_files()`, change the `skills-plugins.txt` sync line to:

```bash
cp "$SOURCE_DIR/env-config.yaml" "$DEST_DIR/env-config.yaml" 2>/dev/null && ok "env-config.yaml synced" || true
```

Remove the old `skills-plugins.txt` copy line.

**Files:**
- Modify: `docker/Dockerfile`
- Modify: `docker/entrypoint.sh`

Verify: `bash -n docker/entrypoint.sh` — no syntax errors.

---

### Task 10: Migrate setup-claude.sh to config-parser

- [ ] Add config-parser variables and replace DSL parsing in `docker/setup-claude.sh`

Same pattern as `setup-env.sh` migration (Task 7-8). Key differences:
- Parser path: `CONFIG_PARSER="/opt/loop/lib/config-parser.js"` (Docker bakes loop to `/opt/loop`)
- Config path: `CONFIG_FILE="$CLAUDE_DIR/env-config.yaml"` (synced by entrypoint)
- Environment tag: `ENVIRONMENT_TAG="docker"`

Replace: `install_all_plugins_and_skills()`, `parse_mcp_servers()`, `build_expected_plugins_list()`, `apply_claude_settings()`.

Remove: `build_stdio_json()`, `build_http_json()`, `trim_whitespace()` (if present), old DSL loop code, `$CLAUDE_PLUGINS_FILE` constant.

- [ ] Add timezone/locale propagation (same pattern as Task 8)

**Files:**
- Modify: `docker/setup-claude.sh`

Verify: `bash -n docker/setup-claude.sh` — no syntax errors.

---

## Phase 7: Local Setup and DevContainer JSON Migration

**Status:** pending

### Task 11: Migrate setup-local.sh to config-parser

- [ ] Add config-parser variables and replace DSL parsing in `setup-local.sh`

Key differences:
- Parser path: `CONFIG_PARSER="$DEVCONTAINER_DIR/src/lib/config-parser.js"` (resolved from repo root)
- Config path: `CONFIG_FILE="$DEVCONTAINER_DIR/.devcontainer/configuration/env-config.yaml"`
- Environment tag: `ENVIRONMENT_TAG="local"`

Replace same functions as other scripts. Additionally:
- `check_requirements()` already checks for `jq` — ensure the error message says: `"jq is required — install with: brew install jq"`
- The string-based `_expected_plugins` can be replaced with the same `jq` iteration pattern used in the other scripts

Remove: dead DSL parsing code, `_seen_marketplaces` tracking, old `build_expected_plugins_list()` with string membership.

**Files:**
- Modify: `setup-local.sh`

Verify: `bash -n setup-local.sh` — no syntax errors.

---

### Task 12: Remove hardcoded values from devcontainer.json

- [ ] Remove personal env vars from `containerEnv` in `devcontainer.json`

Remove these keys from `containerEnv` (they're now in `env-config.yaml` and propagated by setup-env.sh):
- `GIT_USER_NAME`
- `GIT_USER_EMAIL`
- `GIT_USER_EMAIL_ROCHE`
- `TZ`
- `LC_TIME`

Keep `CLAUDE_CONFIG_DIR` (infrastructure, not personal).

**Files:**
- Modify: `.devcontainer/devcontainer.json`

Verify: `cat .devcontainer/devcontainer.json | python3 -m json.tool > /dev/null` — valid JSON.

---

## Phase 8: Cleanup, Mirror, and Documentation

**Status:** pending

### Task 13: Delete skills-plugins.txt and update mirror workflow

- [ ] Delete `.devcontainer/configuration/skills-plugins.txt`

```bash
git rm .devcontainer/configuration/skills-plugins.txt
```

- [ ] Update `.github/workflows/mirror-repository.yml` to exclude `env-config.yaml`

Add a new `git rm` line:
```bash
git rm -f --ignore-unmatch .devcontainer/configuration/env-config.yaml
```

Note: `skills-plugins.txt` was never in the mirror exclusion list (it was public), so no removal needed there.

**Files:**
- Delete: `.devcontainer/configuration/skills-plugins.txt`
- Modify: `.github/workflows/mirror-repository.yml`

---

### Task 14: Update CLAUDE.md and README.md

- [ ] Update `CLAUDE.md` — replace all `skills-plugins.txt` references with `env-config.yaml`

Key sections to update:
- "MCP Servers" — change reference from `skills-plugins.txt` to `env-config.yaml`
- "Adding New Components" — update plugin/MCP instructions
- "Codebase Patterns" — update `skills-plugins.txt formats` entry to document YAML structure
- "Key Files for Parallel Changes" — remove `skills-plugins.txt` references, add `env-config.yaml`
- "Setup Flow" — mention config-parser
- "File Sync Mapping" — add `env-config.yaml` row

- [ ] Update `README.md` — reflect new configuration approach

Update setup instructions to mention `env-config.yaml` instead of `skills-plugins.txt`. Note that users should copy `env-config.example.yaml` to `env-config.yaml` and customize.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

Verify: Both files are valid markdown, no broken references to `skills-plugins.txt`.
