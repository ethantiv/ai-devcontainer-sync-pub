#!/bin/bash

# =============================================================================
# setup-common.sh — Shared library for setup scripts
#
# Sourced by:
#   - .devcontainer/setup-env.sh
#   - docker/setup-env.sh
#   - setup-local.sh
#
# Each caller must set the required variables listed below before sourcing.
# =============================================================================

# Double-source guard
[[ -n "${_SETUP_COMMON_LOADED:-}" ]] && return 0
readonly _SETUP_COMMON_LOADED=1

# =============================================================================
# DEFAULTS AND REQUIRED VARIABLE VALIDATION
# =============================================================================

# Defaults — callers may override any of these before sourcing.
: "${CLAUDE_DIR:=$HOME/.claude}"
: "${CLAUDE_SETTINGS_FILE:=$CLAUDE_DIR/settings.json}"
: "${OFFICIAL_MARKETPLACE_NAME:=claude-plugins-official}"
: "${OFFICIAL_MARKETPLACE_REPO:=anthropics/claude-plugins-official}"
: "${LOCAL_MARKETPLACE_NAME:=dev-marketplace}"

# Required — callers must set before sourcing:
#   CONFIG_FILE             - Path to env-config.yaml
#   ENVIRONMENT_TAG         - Environment identifier (devcontainer|docker|local)
#   LOCAL_MARKETPLACE_DIR   - Directory of the local plugin marketplace
#   ENV_EXPORT_FILE         - File to write exported env vars into (e.g. ~/.bashrc or $CLAUDE_DIR/env.sh)

_validate_required_vars() {
    local missing=()
    local required_vars=(
        CONFIG_FILE
        ENVIRONMENT_TAG
        LOCAL_MARKETPLACE_DIR
        ENV_EXPORT_FILE
    )
    for var in "${required_vars[@]}"; do
        [[ -z "${!var:-}" ]] && missing+=("$var")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "setup-common.sh: missing required variables:" >&2
        for var in "${missing[@]}"; do
            echo "  - $var" >&2
        done
        return 1
    fi
}

_validate_required_vars || return 1

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

has_command() {
    command -v "$1" &>/dev/null
}

# Create ~/.claude and ~/.claude/tmp, then point TMPDIR at the latter so that
# rename(2) stays on the same filesystem as the Claude volume (avoids EXDEV).
init_claude_dirs() {
    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"
}

ok()   { echo -e "  \033[32m✔︎\033[0m $1"; }
warn() { echo -e "  \033[33m⚠️\033[0m  $1"; }
fail() { echo -e "  \033[31m❌\033[0m $1"; }

# Emit "📊 <label>: N removed, N failed" when there's activity, else "All <thing> in sync".
# Args: label, in_sync_msg, removed, failed
_print_sync_summary() {
    local label="$1" in_sync_msg="$2" removed="$3" failed="$4"
    if ((removed > 0 || failed > 0)); then
        echo "  📊 $label: $removed removed, $failed failed"
    else
        ok "$in_sync_msg"
    fi
}

# =============================================================================
# CONFIG LOADING (YAML → JSON via yq, merge/interp/dedup via jq)
# =============================================================================

# Emit merged config as JSON: defaults + environments[$ENVIRONMENT_TAG],
# with list deduplication (by .name or .url for objects, by value for strings)
# and ${VAR} interpolation from the process environment.
# Result is cached in _CONFIG_JSON_CACHE — ~10 callers per setup run.
_CONFIG_JSON_CACHE=""
_config_json() {
    [[ -n "$_CONFIG_JSON_CACHE" ]] && { printf '%s\n' "$_CONFIG_JSON_CACHE"; return 0; }
    has_command yq || { warn "yq not found — install mikefarah/yq"; return 1; }
    has_command jq || { warn "jq not found"; return 1; }

    local result
    result=$(yq eval -o=json "$CONFIG_FILE" | jq --arg env "$ENVIRONMENT_TAG" '
        def dedup_list(xs):
            if (xs | length) == 0 then xs
            elif (xs[0] | type) == "object" and ((xs[0].name // xs[0].url) // null) != null then
                reduce xs[] as $i ({}; .[($i.name // $i.url)] = $i) | [.[]]
            else (xs | unique) end;
        def merge($a; $b):
            if $b == null then $a
            elif $a == null then $b
            elif ($a | type) == "array" and ($b | type) == "array" then dedup_list($a + $b)
            elif ($a | type) == "object" and ($b | type) == "object" then
                reduce ([$a, $b] | add | keys_unsorted[]) as $k ({};
                    .[$k] = merge($a[$k]; $b[$k]))
            else $b end;
        def interp:
            walk(if type == "string" then
                gsub("\\$\\{(?<v>[^}]+)\\}";
                    (env[.v] // (. | "Warning: unresolved variable ${\(.v)}\n" | stderr | "")))
            else . end);
        def validate:
            . as $out |
            ["git.personal.name", "git.personal.email"] as $required |
            ($required | map(select(. as $p |
                ($out | getpath($p | split(".")) // "") | tostring | length == 0))) as $missing |
            if ($missing | length) > 0 then
                error("Missing required fields: \($missing | join(", "))")
            else $out end;
        (.defaults // {}) as $d |
        (.environments[$env] // {}) as $e |
        merge($d; $e) | interp | validate
    ') || return 1
    _CONFIG_JSON_CACHE="$result"
    printf '%s\n' "$_CONFIG_JSON_CACHE"
}

# Emit a computed section. Args: $1 = section name
#   __all__           — entire merged config
#   plugins_flat      — marketplace + lsp flattened to [{name, type:"marketplace"}]
#   plugins_external  — .plugins.external list
#   skills            — expanded to [{url, name}], with "*" wildcard for bundles without names
#   <top-level-key>   — raw value of .<key> (falls back to [] when missing)
_config_section() {
    local section="$1"
    local json
    json=$(_config_json) || return 1
    case "$section" in
        __all__)
            printf '%s\n' "$json" ;;
        plugins_flat)
            printf '%s\n' "$json" | jq '[(.plugins.marketplace // [])[], (.plugins.lsp // [])[]]
                | map({name: ., type: "marketplace"})' ;;
        plugins_external)
            printf '%s\n' "$json" | jq '.plugins.external // []' ;;
        skills)
            printf '%s\n' "$json" | jq '[.skills // [] | .[]
                | if (.names | type) == "array" and (.names | length) > 0
                    then .names[] as $n | {url, name: $n}
                  elif .name then {url, name}
                  else {url, name: "*"} end]' ;;
        *)
            printf '%s\n' "$json" | jq --arg s "$section" '.[$s] // []' ;;
    esac
}

# =============================================================================
# CLAUDE SETTINGS
# =============================================================================

apply_claude_settings() {
    has_command jq || { warn "jq not found - cannot manage settings"; return 0; }

    local claude_config
    claude_config=$(_config_section claude) || {
        warn "Failed to parse Claude settings"; return 0
    }

    # statusLine stays hardcoded — design doc marks it out of scope
    local default_settings
    default_settings=$(echo "$claude_config" | jq --argjson sl '{"type":"command","command":"~/.claude/scripts/context-bar.sh"}' '{
        permissions: .permissions,
        language: .language,
        statusLine: $sl
    }
    + if .sandbox then {sandbox: .sandbox} else {} end
    + if .effortLevel then {effortLevel: .effortLevel} else {} end')

    ensure_directory "$CLAUDE_DIR"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[1] * .[0]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    ok "Settings configured"

    # Apply remoteControlAtStartup to .claude.json (global config, not settings.json)
    local remote_control
    remote_control=$(echo "$claude_config" | jq -r '.remoteControl // empty')
    if [[ -n "$remote_control" ]]; then
        local claude_json="$CLAUDE_DIR/.claude.json"
        if [[ -f "$claude_json" ]]; then
            local updated
            updated=$(jq --argjson rc "$remote_control" '.remoteControlAtStartup = $rc' "$claude_json" 2>/dev/null)
            [[ -n "$updated" ]] && echo "$updated" > "$claude_json"
        else
            jq -n --argjson rc "$remote_control" '{remoteControlAtStartup: $rc}' > "$claude_json"
        fi
        ok "Remote Control: $remote_control"
    fi
}

# Append `export KEY=<shell-escaped value>` to $ENV_EXPORT_FILE, skipping empty
# values and entries already present. printf %q guards against injection via
# $()/backticks in config values.
_write_env_export() {
    local key="$1" value="$2"
    [[ -z "$value" ]] && return 0
    grep -q "^export $key=" "$ENV_EXPORT_FILE" 2>/dev/null && return 0
    printf 'export %s=%q\n' "$key" "$value" >> "$ENV_EXPORT_FILE"
}

# Propagate timezone, locale, and git identity from config to $ENV_EXPORT_FILE
# Includes all vars from the DevContainer version: tz, locale, git_name, git_email,
# work_email, work_orgs, work_dirs
propagate_env_from_config() {
    local config_json
    config_json=$(_config_section __all__ 2>/dev/null) || return 0

    local tz locale git_name git_email work_email work_orgs work_dirs
    IFS=$'\t' read -r tz locale git_name git_email work_email work_orgs work_dirs < <(
        echo "$config_json" | jq -r '[
            .timezone // "",
            .locale // "",
            .git.personal.name // "",
            .git.personal.email // "",
            .git.work.email // "",
            .git.work.orgs // "",
            ((.git.work.dirs // []) | join("|"))
        ] | @tsv'
    )

    _write_env_export TZ                 "$tz"
    _write_env_export LC_TIME            "$locale"
    _write_env_export GIT_USER_NAME      "$git_name"
    _write_env_export GIT_USER_EMAIL     "$git_email"
    _write_env_export GIT_USER_EMAIL_WORK "$work_email"
    _write_env_export GH_WORK_ORGS       "$work_orgs"
    if [[ -n "$work_dirs" ]]; then
        export GH_WORK_DIRS="$work_dirs"
        _write_env_export GH_WORK_DIRS   "$work_dirs"
    fi

    ok "Environment variables propagated to $ENV_EXPORT_FILE"
}

# Detect Playwright Chromium and set AGENT_BROWSER_EXECUTABLE_PATH
# Skips if already set (e.g. Docker sets it to /usr/bin/chromium in Dockerfile)
configure_agent_browser() {
    [[ -n "${AGENT_BROWSER_EXECUTABLE_PATH:-}" ]] && return 0

    local pw_path="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
    local chrome_bin
    chrome_bin=$(find "$pw_path" -path "*/chrome-linux/chrome" -type f 2>/dev/null | head -1)

    if [[ -n "$chrome_bin" ]]; then
        export AGENT_BROWSER_EXECUTABLE_PATH="$chrome_bin"
        if ! grep -q 'AGENT_BROWSER_EXECUTABLE_PATH' "$ENV_EXPORT_FILE" 2>/dev/null; then
            printf 'export AGENT_BROWSER_EXECUTABLE_PATH=%q\n' "$chrome_bin" >> "$ENV_EXPORT_FILE"
        fi
        ok "agent-browser → $chrome_bin"
    fi
}

# Copy CLAUDE.md.memory to ~/.claude/CLAUDE.md
# Args: source_dir — directory containing config/CLAUDE.md.memory
copy_claude_memory() {
    local source_dir="$1"
    local source_file="$source_dir/config/CLAUDE.md.memory"
    [[ -f "$source_file" ]] && cp "$source_file" "$CLAUDE_DIR/CLAUDE.md" && ok "CLAUDE.md synced"
}

# Copy all *.sh scripts from config/scripts/ to ~/.claude/scripts/
# Args: source_dir — directory containing config/scripts/
sync_claude_scripts() {
    local source_dir="$1/config/scripts"
    [[ -d "$source_dir" ]] || return 0

    local scripts_dir="$CLAUDE_DIR/scripts"
    ensure_directory "$scripts_dir"

    for script in "$source_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        # Skip setup-common.sh — it's a library, not a runtime script
        [[ "$(basename "$script")" == "setup-common.sh" ]] && continue
        cp "$script" "$scripts_dir/"
        chmod +x "$scripts_dir/${script##*/}"
    done
    ok "Synced scripts to ~/.claude/scripts/"
}

# =============================================================================
# PLUGIN INSTALLATION
# =============================================================================

# Install a Claude plugin. Returns: 0=installed, 1=already present, 2=failed
# Note: < /dev/null prevents claude CLI from consuming stdin (breaks while-read loops)
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user < /dev/null >/dev/null 2>&1; then
        ok "Installed: $display_name"
        return 0
    fi
    warn "Failed: $display_name"
    return 2
}

# Update install counters based on install_plugin return code
# Uses nameref (Bash 4.3+): pass variable names as strings
# Usage: update_plugin_counters $rc installed_var skipped_var failed_var
update_plugin_counters() {
    local rc="$1"
    local -n _installed="$2"
    local -n _skipped="$3"
    local -n _failed="$4"

    case $rc in
        0) _installed=$((_installed + 1)) ;;
        1) _skipped=$((_skipped + 1)) ;;
        *) _failed=$((_failed + 1)) ;;
    esac
}

# Ensure a plugin marketplace is registered
ensure_marketplace() {
    local name="$1"
    local source="$2"

    if claude plugin marketplace list 2>/dev/null | grep -q "$name"; then
        return 0
    fi

    if claude plugin marketplace add "$source" >/dev/null 2>&1; then
        ok "Added marketplace: $name"
        return 0
    fi
    warn "Failed to add marketplace: $name"
    return 1
}

# Uninstall a plugin by its full ID (name@marketplace)
uninstall_plugin() {
    local plugin="$1"
    local display_name="${plugin%%@*}"
    if claude plugin uninstall "$plugin" --scope user < /dev/null >/dev/null 2>&1; then
        echo "  🗑️  Uninstalled: $display_name"
        return 0
    fi
    warn "Failed to uninstall: $display_name"
    return 1
}

# =============================================================================
# SKILL INSTALLATION
# =============================================================================

# Install one or more skills from a single repo in a single `skills add` call.
# Args: url, name1 [name2 ...]  (use single "*" to install all skills from repo)
# For wildcard mode, records resolved skill names in $CLAUDE_DIR/skills/.sources.json
# so sync_skills can clean up when the URL is removed from YAML later.
# Note: < /dev/null prevents npx from consuming stdin (breaks while-read loops)
install_skill_bundle() {
    local url="$1"; shift
    local names=("$@")
    [[ ${#names[@]} -gt 0 ]] || return 1

    has_command npx || return 1
    local skills_dir="$CLAUDE_DIR/skills"
    ensure_directory "$skills_dir"

    local args=()
    local wildcard=0
    if [[ ${#names[@]} -eq 1 && "${names[0]}" == "*" ]]; then
        wildcard=1
        # Use --skill '*' instead of --all: --all forces --agent '*' which
        # installs into every supported agent (cursor, augment, bob, etc).
        args=(--skill '*' --agent claude-code -g -y)
    else
        args=(--skill "${names[@]}" --agent claude-code -g -y)
    fi

    local before=""
    (( wildcard )) && before=$(ls -1 "$skills_dir" 2>/dev/null | sort)

    if ! npx -y skills add "$url" "${args[@]}" < /dev/null >/dev/null 2>&1; then
        warn "Failed to install skills from $url: ${names[*]}"
        return 1
    fi

    if (( wildcard )); then
        local after resolved
        after=$(ls -1 "$skills_dir" 2>/dev/null | sort)
        # Resolved names = union of pre-existing and newly added from this repo.
        # Snapshot delta is approximate — on re-runs --all is idempotent and delta is empty.
        # Merge with any prior manifest entry so we don't lose previously tracked names.
        resolved=$(comm -13 <(echo "$before") <(echo "$after"))
        _update_skill_sources "$url" "$resolved"
        ok "Installed skills from $url (--all)"
    else
        ok "Installed skills from $url: ${names[*]}"
    fi
    return 0
}

# Update $CLAUDE_DIR/skills/.sources.json: merge resolved skill names under URL key.
# Args: url, newline-separated names (may be empty — still ensures key exists)
_update_skill_sources() {
    local url="$1"
    local new_names="$2"
    local manifest="$CLAUDE_DIR/skills/.sources.json"
    has_command jq || return 0
    [[ -f "$manifest" ]] || echo '{}' > "$manifest"

    local names_json
    names_json=$(echo "$new_names" | jq -R . | jq -s 'map(select(length > 0))')
    local tmp
    tmp=$(mktemp)
    jq --arg url "$url" --argjson new "$names_json" \
        '.[$url] = ((.[$url] // []) + $new | unique)' "$manifest" > "$tmp" \
        && mv "$tmp" "$manifest" || rm -f "$tmp"
}

# Install skill from direct GitHub path (no skills CLI required)
# Args: skill_name, path (e.g., owner/repo/path/to/SKILL.md)
install_github_skill() {
    local name="$1"
    local path="$2"

    local skill_dir="$CLAUDE_DIR/skills/$name"
    ensure_directory "$skill_dir"

    # Reconstruct URL: owner/repo/path -> raw.githubusercontent.com/owner/repo/main/path
    local owner="${path%%/*}"
    local rest="${path#*/}"
    local repo="${rest%%/*}"
    local file_path="${rest#*/}"
    local url="https://raw.githubusercontent.com/${owner}/${repo}/main/${file_path}"

    if curl -fsSL -o "$skill_dir/SKILL.md" "$url" < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

# =============================================================================
# BULK INSTALL
# =============================================================================

# Parse plugins and skills from YAML configuration and install all
# Handles: official marketplace plugins and skills
install_all_plugins_and_skills() {
    echo "📦 Installing plugins and skills..."

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        warn "Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" >/dev/null 2>&1 || true

    # Clean stale gemini skill symlinks (gemini-cli scans ~/.agents/skills/ directly)
    if [[ -d "$HOME/.gemini/skills" ]]; then
        find "$HOME/.gemini/skills" -maxdepth 1 -type l -delete 2>/dev/null || true
    fi

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0

    # Plugins (flat array from parser)
    local plugins_json
    plugins_json=$(_config_section plugins_flat) || {
        warn "Failed to parse plugin config"; return 0
    }

    # NOTE: Use process substitution (< <(...)) to avoid subshell variable scoping.
    # Piped while-loops run in subshells where counter/array mutations are lost.
    while IFS= read -r plugin; do
        local name
        name=$(echo "$plugin" | jq -r '.name')
        local rc=0; install_plugin "${name}@${OFFICIAL_MARKETPLACE_NAME}" "$name" || rc=$?
        update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Skills
    local skills_json
    skills_json=$(_config_section skills) || {
        warn "Failed to parse skills config"; return 0
    }

    # Group skills by URL so one repo -> one `skills add` call.
    while IFS= read -r group; do
        local url count names_json
        url=$(echo "$group" | jq -r '.url')
        names_json=$(echo "$group" | jq -r '.names[]')
        count=$(echo "$group" | jq -r '.names | length')
        local names=()
        while IFS= read -r n; do names+=("$n"); done <<< "$names_json"
        if install_skill_bundle "$url" "${names[@]}" < /dev/null; then
            skills_installed=$((skills_installed + count))
        else
            skills_failed=$((skills_failed + count))
        fi
    done < <(echo "$skills_json" | jq -c 'group_by(.url) | map({url: .[0].url, names: [.[].name]}) | .[]')

    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

# Install plugins from external marketplaces declared in plugins.external.
install_external_marketplace_plugins() {
    echo "📦 Installing external marketplace plugins..."

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    local external_json
    external_json=$(_config_section plugins_external 2>/dev/null) || {
        warn "Failed to parse external plugins"; return 0
    }
    [[ "$external_json" == "[]" ]] && { ok "No external plugins declared"; return 0; }

    local installed=0 skipped=0 failed=0

    while IFS= read -r entry; do
        [[ -z "$entry" ]] && continue
        local name marketplace source
        name=$(echo "$entry" | jq -r '.name // empty')
        marketplace=$(echo "$entry" | jq -r '.marketplace // empty')
        source=$(echo "$entry" | jq -r '.source // empty')
        if [[ -z "$name" || -z "$marketplace" || -z "$source" ]]; then
            warn "Skipping malformed external plugin entry: $entry"
            failed=$((failed + 1))
            continue
        fi

        ensure_marketplace "$marketplace" "$source" || { failed=$((failed + 1)); continue; }
        local rc=0; install_plugin "${name}@${marketplace}" "$name" || rc=$?
        update_plugin_counters $rc installed skipped failed
    done < <(echo "$external_json" | jq -c '.[]')

    echo "  📊 External: $installed installed, $skipped present, $failed failed"
}

# Install plugins from the local marketplace (uses $LOCAL_MARKETPLACE_DIR)
install_local_marketplace_plugins() {
    local manifest="$LOCAL_MARKETPLACE_DIR/.claude-plugin/marketplace.json"

    echo "📦 Installing local plugins..."

    has_command claude || return 0
    has_command jq || return 0
    [[ -f "$manifest" ]] || { warn "Local marketplace not found"; return 0; }
    if ! ensure_marketplace "$LOCAL_MARKETPLACE_NAME" "$LOCAL_MARKETPLACE_DIR"; then
        warn "Skipping local marketplace plugins"
        return 0
    fi

    local installed=0 skipped=0 failed=0

    while IFS= read -r plugin; do
        [[ -z "$plugin" ]] && continue
        local rc=0; install_plugin "${plugin}@${LOCAL_MARKETPLACE_NAME}" "$plugin" || rc=$?
        update_plugin_counters $rc installed skipped failed
    done < <(jq -r '.plugins[].name' "$manifest" 2>/dev/null)

    echo "  📊 Local: $installed installed, $skipped present, $failed failed"
}

# =============================================================================
# PLUGIN SYNC
# =============================================================================

# Build expected plugins associative array from YAML + local marketplace
# Sets global: expected_plugins[plugin_id]=1
# Requires Bash 4+ (declare -gA)
build_expected_plugins_list() {
    declare -gA expected_plugins
    expected_plugins=()

    local plugins_json
    plugins_json=$(_config_section plugins_flat) || return 0

    # Process substitution to preserve expected_plugins associative array
    while IFS= read -r plugin; do
        local name
        name=$(echo "$plugin" | jq -r '.name')
        expected_plugins["${name}@${OFFICIAL_MARKETPLACE_NAME}"]=1
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Local marketplace plugins (auto-discovered from manifest, not from YAML)
    local local_manifest="$LOCAL_MARKETPLACE_DIR/.claude-plugin/marketplace.json"
    if [[ -f "$local_manifest" ]]; then
        local plugin_names
        plugin_names=$(jq -r '.plugins[].name // empty' "$local_manifest" 2>/dev/null)
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            expected_plugins["${name}@${LOCAL_MARKETPLACE_NAME}"]=1
        done <<< "$plugin_names"
    fi

    # External marketplace plugins (keyed by their own marketplace name).
    # Fall back to [] on parser failure — returning early would empty the whole
    # expected list (built above) and cause sync_plugins to mass-uninstall.
    local external_json
    external_json=$(_config_section plugins_external 2>/dev/null) || external_json='[]'
    while IFS= read -r entry; do
        [[ -z "$entry" ]] && continue
        local name marketplace
        name=$(echo "$entry" | jq -r '.name // empty')
        marketplace=$(echo "$entry" | jq -r '.marketplace // empty')
        [[ -n "$name" && -n "$marketplace" ]] && expected_plugins["${name}@${marketplace}"]=1
    done < <(echo "$external_json" | jq -c '.[]?' 2>/dev/null)
}

# Get installed plugins from settings.json
# Sets global: installed_plugins[plugin_id]=1
# Requires Bash 4+ (declare -gA)
get_installed_plugins() {
    declare -gA installed_plugins
    installed_plugins=()
    [[ -f "$CLAUDE_SETTINGS_FILE" ]] || return 0
    while IFS= read -r plugin; do
        [[ -n "$plugin" ]] && installed_plugins["$plugin"]=1
    done < <(jq -r '.enabledPlugins | keys[]' "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
}

# Sync plugins: remove any installed plugins that are not in the expected list
sync_plugins() {
    echo "🔄 Synchronizing plugins..."
    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    build_expected_plugins_list
    get_installed_plugins

    local removed=0 failed=0
    for plugin in "${!installed_plugins[@]}"; do
        if [[ -z "${expected_plugins[$plugin]}" ]]; then
            uninstall_plugin "$plugin" && { ((removed++)) || true; } || { ((failed++)) || true; }
        fi
    done

    _print_sync_summary "Sync" "All plugins in sync" "$removed" "$failed"
}

# =============================================================================
# SKILL SYNC
# =============================================================================

# Sync skills: remove any installed skills not declared in YAML configuration
sync_skills() {
    echo "🔄 Synchronizing skills..."

    local skills_dir="$CLAUDE_DIR/skills"
    [[ -d "$skills_dir" ]] || return 0

    # Build expected skills list from YAML
    declare -A expected=()
    local skills_json
    skills_json=$(_config_section skills 2>/dev/null) || return 0

    local wildcard_urls=()
    while IFS= read -r skill; do
        local name url
        name=$(echo "$skill" | jq -r '.name')
        url=$(echo "$skill" | jq -r '.url')
        if [[ "$name" == "*" ]]; then
            wildcard_urls+=("$url")
        elif [[ -n "$name" ]]; then
            expected["$name"]=1
        fi
    done < <(echo "$skills_json" | jq -c '.[]')

    # Resolve wildcard URLs via manifest: all skill names previously installed from those repos
    local manifest="$skills_dir/.sources.json"
    if [[ ${#wildcard_urls[@]} -gt 0 && -f "$manifest" ]]; then
        local url
        for url in "${wildcard_urls[@]}"; do
            while IFS= read -r name; do
                [[ -n "$name" ]] && expected["$name"]=1
            done < <(jq -r --arg u "$url" '.[$u][]? // empty' "$manifest")
        done
    fi

    # Prune manifest entries whose URL is no longer declared in YAML
    if [[ -f "$manifest" ]] && has_command jq; then
        local declared_urls_json
        declared_urls_json=$(echo "$skills_json" | jq '[.[].url] | unique')
        local tmp
        tmp=$(mktemp)
        jq --argjson keep "$declared_urls_json" \
            'with_entries(select(.key as $k | $keep | index($k)))' "$manifest" > "$tmp" \
            && mv "$tmp" "$manifest" || rm -f "$tmp"
    fi

    # Compare installed vs expected, remove stale (directories and symlinks)
    local removed=0 failed=0
    for entry in "$skills_dir"/*; do
        [[ -d "$entry" || -L "$entry" ]] || continue
        local name
        name=$(basename "$entry")
        [[ "$name" == .* ]] && continue
        [[ -n "${expected[$name]:-}" ]] && continue
        if rm -rf "$entry"; then
            echo "  🗑️  Removed skill: $name"
            removed=$((removed + 1))
        else
            warn "Failed to remove skill: $name"
            failed=$((failed + 1))
        fi
    done

    _print_sync_summary "Skills sync" "All skills in sync" "$removed" "$failed"
}

# =============================================================================
# MCP SERVERS
# =============================================================================

# Add a single MCP server by name and JSON config (idempotent)
add_mcp_server() {
    local name="$1"
    local config="$2"

    local settings_file="$CLAUDE_DIR/.claude.json"
    if [[ -f "$settings_file" ]] && jq -e --arg n "$name" '.mcpServers[$n]' "$settings_file" &>/dev/null; then
        ok "$name already configured"
        return
    fi

    if claude mcp add-json "$name" "$config" --scope user >/dev/null 2>&1; then
        ok "Added: $name"
    else
        warn "Failed to add $name"
    fi
}

# Parse MCP server declarations from YAML and call add_mcp_server for each.
# Populates caller's mcp_expected associative array (must be declared as `declare -A`).
parse_mcp_servers() {
    local mcp_json
    mcp_json=$(_config_section mcp_servers) || {
        warn "Failed to parse MCP config"; return 0
    }

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

        mcp_expected["$name"]=1
        add_mcp_server "$name" "$config_json"
    done < <(echo "$mcp_json" | jq -c '.[]')
}

# Sync MCP servers: add from config, remove stale ones not in config
sync_mcp_servers() {
    echo "🔧 Setting up MCP servers..."
    has_command claude || return 0
    has_command jq || return 0

    declare -A mcp_expected=()
    parse_mcp_servers

    # Get installed MCP servers from .claude.json
    local settings_file="$CLAUDE_DIR/.claude.json"
    local installed=()
    if [[ -f "$settings_file" ]]; then
        while IFS= read -r name; do
            [[ -n "$name" ]] && installed+=("$name")
        done < <(jq -r '.mcpServers // {} | keys[]' "$settings_file" 2>/dev/null)
    fi

    # Remove servers not in expected list
    local removed=0
    for name in "${installed[@]}"; do
        if [[ -z "${mcp_expected[$name]:-}" ]]; then
            if claude mcp remove "$name" --scope user < /dev/null >/dev/null 2>&1; then
                echo "  🗑️  Removed MCP: $name"
                removed=$((removed + 1))
            fi
        fi
    done

    echo "  📊 MCP: ${#mcp_expected[@]} configured, $removed removed"
}

# =============================================================================
# MARKETPLACE SYNC
# =============================================================================

# Sync marketplaces: remove any installed marketplaces not in the expected set.
# Expected = OFFICIAL_MARKETPLACE_NAME + LOCAL_MARKETPLACE_NAME.
# Source of truth is ~/.claude/plugins/known_marketplaces.json (managed by
# claude plugin marketplace add/remove), which lists every registered
# marketplace including the official one.
sync_marketplaces() {
    echo "🔄 Synchronizing marketplaces..."
    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    local known_file="$CLAUDE_DIR/plugins/known_marketplaces.json"
    [[ -f "$known_file" ]] || { ok "No marketplaces registered — nothing to sync"; return 0; }

    declare -A expected_marketplaces=(
        ["$OFFICIAL_MARKETPLACE_NAME"]=1
        ["$LOCAL_MARKETPLACE_NAME"]=1
    )

    # Preserve marketplaces that host declared external plugins
    local external_json
    external_json=$(_config_section plugins_external 2>/dev/null) || external_json='[]'
    while IFS= read -r marketplace; do
        [[ -n "$marketplace" ]] && expected_marketplaces["$marketplace"]=1
    done < <(echo "$external_json" | jq -r '.[]?.marketplace // empty' 2>/dev/null)

    local removed=0 failed=0
    while IFS= read -r name; do
        [[ -z "$name" ]] && continue
        [[ -n "${expected_marketplaces[$name]:-}" ]] && continue
        if claude plugin marketplace remove "$name" < /dev/null >/dev/null 2>&1; then
            echo "  🗑️  Removed marketplace: $name"
            removed=$((removed + 1))
        else
            warn "Failed to remove marketplace: $name"
            failed=$((failed + 1))
        fi
    done < <(jq -r 'keys[]' "$known_file" 2>/dev/null)

    _print_sync_summary "Marketplaces sync" "All marketplaces in sync" "$removed" "$failed"
}

# =============================================================================
# PIPELINE
# =============================================================================

# Full install/sync pipeline. Order matters:
#   install_all_plugins_and_skills must run BEFORE sync_skills, because
#   sync_skills reads the wildcard manifest populated during install.
run_plugin_sync_pipeline() {
    sync_plugins
    install_all_plugins_and_skills
    sync_skills
    install_external_marketplace_plugins
    install_local_marketplace_plugins
    sync_marketplaces
    sync_mcp_servers
}
