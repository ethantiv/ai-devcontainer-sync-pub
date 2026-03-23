#!/bin/bash
# Claude Code setup script for Docker container
# Installs plugins, skills, and MCP servers

set -e

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly CONFIG_PARSER="/opt/loop/lib/config-parser.js"
readonly CONFIG_FILE="$CLAUDE_DIR/env-config.yaml"
readonly ENVIRONMENT_TAG="docker"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
readonly LOCAL_MARKETPLACE_NAME="dev-marketplace"
readonly LOCAL_MARKETPLACE_DIR="$CLAUDE_DIR/plugins/$LOCAL_MARKETPLACE_NAME"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

has_command() {
    command -v "$1" &>/dev/null
}

ok()   { echo -e "  \033[32m✔︎\033[0m $1"; }
warn() { echo -e "  \033[33m⚠️\033[0m  $1"; }
fail() { echo -e "  \033[31m❌\033[0m $1"; }

setup_github_token() {
    if [[ -n "${GH_TOKEN}" ]]; then
        local env_file="$CLAUDE_DIR/env.sh"
        if ! grep -q "^export GH_TOKEN=" "$env_file" 2>/dev/null; then
            echo "export GH_TOKEN='${GH_TOKEN}'" >> "$env_file" \
                && ok "GitHub token exported to env.sh" \
                || warn "Could not write to env.sh (GH_TOKEN available from env)"
        fi
    fi
}

# Install a Claude plugin (returns: 0=installed, 1=already present, 2=failed)
# Note: < /dev/null prevents claude CLI from consuming stdin (breaks while-read loops)
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user < /dev/null 2>/dev/null; then
        ok "Installed: $display_name"
        return 0
    fi
    warn "Failed: $display_name"
    return 2
}

# Update counters based on install_plugin return code
update_plugin_counters() {
    local rc="$1"
    local -n _installed="$2"
    local -n _skipped="$3"
    local -n _failed="$4"

    case $rc in
        0) ((_installed++)) || true ;;
        1) ((_skipped++)) || true ;;
        2) ((_failed++)) || true ;;
    esac
}

ensure_marketplace() {
    local name="$1"
    local source="$2"

    if claude plugin marketplace list 2>/dev/null | grep -q "$name"; then
        return 0
    fi

    if claude plugin marketplace add "$source" 2>/dev/null; then
        ok "Added marketplace: $name"
        return 0
    fi
    warn "Failed to add marketplace: $name"
    return 1
}

# =============================================================================
# CLAUDE SETTINGS
# =============================================================================

apply_claude_settings() {
    echo "📄 Applying Claude settings..."

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

    ensure_directory "$CLAUDE_DIR"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    ok "Settings configured"
}

# Propagate timezone, locale, and git work identity from config
propagate_env_from_config() {
    local config_json
    config_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --all 2>/dev/null) || return 0

    local tz locale git_name git_email work_email work_orgs
    tz=$(echo "$config_json" | jq -r '.timezone // empty')
    locale=$(echo "$config_json" | jq -r '.locale // empty')
    git_name=$(echo "$config_json" | jq -r '.git.personal.name // empty')
    git_email=$(echo "$config_json" | jq -r '.git.personal.email // empty')
    work_email=$(echo "$config_json" | jq -r '.git.work.email // empty')
    work_orgs=$(echo "$config_json" | jq -r '.git.work.orgs // empty')

    # Append to env.sh in volume (not ~/.bashrc which may be read-only)
    local env_file="$CLAUDE_DIR/env.sh"
    [[ -n "$tz" ]] && ! grep -q "^export TZ=" "$env_file" 2>/dev/null && echo "export TZ=\"$tz\"" >> "$env_file"
    [[ -n "$locale" ]] && ! grep -q "^export LC_TIME=" "$env_file" 2>/dev/null && echo "export LC_TIME=\"$locale\"" >> "$env_file"
    [[ -n "$git_name" ]] && ! grep -q "^export GIT_USER_NAME=" "$env_file" 2>/dev/null && echo "export GIT_USER_NAME=\"$git_name\"" >> "$env_file"
    [[ -n "$git_email" ]] && ! grep -q "^export GIT_USER_EMAIL=" "$env_file" 2>/dev/null && echo "export GIT_USER_EMAIL=\"$git_email\"" >> "$env_file"
    [[ -n "$work_email" ]] && ! grep -q "^export GIT_USER_EMAIL_ROCHE=" "$env_file" 2>/dev/null && echo "export GIT_USER_EMAIL_ROCHE=\"$work_email\"" >> "$env_file"
    [[ -n "$work_orgs" ]] && ! grep -q "^export GH_ROCHE_ORGS=" "$env_file" 2>/dev/null && echo "export GH_ROCHE_ORGS=\"$work_orgs\"" >> "$env_file"

    ok "Environment variables propagated to env.sh"
}

# =============================================================================
# SKILL INSTALLATION HELPERS
# =============================================================================

# Install skill using skills CLI (npx skills add)
# Args: skill_name, url (e.g., https://github.com/vercel-labs/agent-skills)
install_skill() {
    local name="$1"
    local url="$2"

    has_command npx || return 1
    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y skills add "$url" --skill "$name" --agent claude-code -g -y < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

# Install skill from direct GitHub path
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
# PLUGINS AND SKILLS INSTALLATION
# =============================================================================

# Parse plugins and skills from YAML configuration via config-parser
# Handles: official marketplace, external marketplaces, skills
install_all_plugins_and_skills() {
    echo "📦 Installing plugins and skills..."

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        warn "Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    # Clean stale gemini skill symlinks (gemini-cli scans ~/.agents/skills/ directly)
    if [ -d "$HOME/.gemini/skills" ]; then
        find "$HOME/.gemini/skills" -maxdepth 1 -type l -delete 2>/dev/null || true
    fi

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0

    # Plugins (flat array from parser)
    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || {
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
    skills_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section skills) || {
        warn "Failed to parse skills config"; return 0
    }

    while IFS= read -r skill; do
        local name url
        name=$(echo "$skill" | jq -r '.name')
        url=$(echo "$skill" | jq -r '.url')
        install_skill "$name" "$url" < /dev/null && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
    done < <(echo "$skills_json" | jq -c '.[]')

    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

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
# PLUGIN SYNCHRONIZATION
# =============================================================================

# Build list of expected plugins from YAML configuration via config-parser
# Sets global: expected_plugins[plugin_id]=1
build_expected_plugins_list() {
    declare -gA expected_plugins
    expected_plugins=()

    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || return 0

    # Process substitution to preserve expected_plugins associative array
    while IFS= read -r plugin; do
        local name
        name=$(echo "$plugin" | jq -r '.name')
        expected_plugins["${name}@${OFFICIAL_MARKETPLACE_NAME}"]=1
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Local marketplace plugins (auto-discovered, not from YAML)
    local local_manifest="$LOCAL_MARKETPLACE_DIR/.claude-plugin/marketplace.json"
    if [[ -f "$local_manifest" ]]; then
        local plugin_names
        plugin_names=$(jq -r '.plugins[].name // empty' "$local_manifest" 2>/dev/null)
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            expected_plugins["${name}@${LOCAL_MARKETPLACE_NAME}"]=1
        done <<< "$plugin_names"
    fi
}

# Get installed plugins from settings.json
get_installed_plugins() {
    declare -gA installed_plugins
    installed_plugins=()
    [[ -f "$CLAUDE_SETTINGS_FILE" ]] || return 0
    while IFS= read -r plugin; do
        [[ -n "$plugin" ]] && installed_plugins["$plugin"]=1
    done < <(jq -r '.enabledPlugins | keys[]' "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
}

# Uninstall plugin
uninstall_plugin() {
    local plugin="$1"
    local display_name="${plugin%%@*}"
    if claude plugin uninstall "$plugin" --scope user < /dev/null 2>/dev/null; then
        echo "  🗑️  Uninstalled: $display_name"
        return 0
    fi
    warn "Failed to uninstall: $display_name"
    return 1
}

# Sync: remove plugins not in expected list
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

    ((removed > 0 || failed > 0)) && echo "  📊 Sync: $removed removed, $failed failed" || ok "All plugins in sync"
}

# Sync: remove skills not in expected list
sync_skills() {
    echo "🔄 Synchronizing skills..."

    local skills_dir="$CLAUDE_DIR/skills"
    [[ -d "$skills_dir" ]] || return 0

    # Build expected skills list from YAML
    local expected=()
    local skills_json
    skills_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section skills 2>/dev/null) || return 0

    while IFS= read -r skill; do
        local name
        name=$(echo "$skill" | jq -r '.name')
        [[ -n "$name" ]] && expected+=("$name")
    done < <(echo "$skills_json" | jq -c '.[]')

    # Compare installed vs expected, remove stale (directories and symlinks)
    local removed=0 failed=0
    for entry in "$skills_dir"/*; do
        [[ -d "$entry" || -L "$entry" ]] || continue
        local name
        name=$(basename "$entry")
        local found=0
        for exp in "${expected[@]}"; do
            [[ "$name" == "$exp" ]] && { found=1; break; }
        done
        if [[ $found -eq 0 ]]; then
            if rm -rf "$entry"; then
                echo "  🗑️  Removed skill: $name"
                removed=$((removed + 1))
            else
                warn "Failed to remove skill: $name"
                failed=$((failed + 1))
            fi
        fi
    done

    ((removed > 0 || failed > 0)) && echo "  📊 Skills sync: $removed removed, $failed failed" || ok "All skills in sync"
}

# =============================================================================
# MCP SERVERS
# =============================================================================

add_mcp_server() {
    local name="$1"
    local config="$2"

    if claude mcp list 2>/dev/null | grep -q "$name"; then
        ok "$name already configured"
        return
    fi

    if claude mcp add-json "$name" "$config" --scope user 2>/dev/null; then
        ok "Added: $name"
    else
        warn "Failed to add $name"
    fi
}

# Parse MCP server declarations from YAML configuration via config-parser
# Populates mcp_expected array and calls add_mcp_server for each
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

# Sync MCP servers: add from config, remove stale ones
sync_mcp_servers() {
    echo "🔧 Setting up MCP servers..."
    has_command jq || return 0

    local mcp_expected=()
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
        local found=0
        for expected in "${mcp_expected[@]}"; do
            [[ "$name" == "$expected" ]] && { found=1; break; }
        done
        if [[ $found -eq 0 ]]; then
            if claude mcp remove "$name" --scope user 2>/dev/null; then
                echo "  🗑️  Removed MCP: $name"
                removed=$((removed + 1))
            fi
        fi
    done

    echo "  📊 MCP: ${#mcp_expected[@]} configured, $removed removed"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "🚀 Setting up Claude Code..."

    # Find claude binary (prefer volume location)
    CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"
    [[ -x "$CLAUDE_CMD" ]] || CLAUDE_CMD="$(command -v claude 2>/dev/null || true)"
    [[ -x "$CLAUDE_CMD" ]] || { fail "Claude CLI not found"; exit 1; }
    has_command jq || { fail "jq not found"; exit 1; }

    # Define claude function to use correct binary
    claude() { "$CLAUDE_CMD" "$@"; }
    export -f claude

    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"

    setup_github_token
    apply_claude_settings
    propagate_env_from_config
    sync_plugins
    sync_skills
    install_all_plugins_and_skills
    install_local_marketplace_plugins
    sync_mcp_servers

    echo ""
    ok "Claude Code setup complete!"
    echo ""
    echo "Verify with:"
    echo "  claude mcp list"
    echo "  claude plugin marketplace list"
}

main "$@"
