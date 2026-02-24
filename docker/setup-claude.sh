#!/bin/bash
# Claude Code setup script for Docker container
# Installs plugins, skills, and MCP servers

set -e

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly CLAUDE_PLUGINS_FILE="$CLAUDE_DIR/skills-plugins.txt"
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
        {
            echo "export GH_TOKEN='${GH_TOKEN}'"
            echo "alias cc='clear && claude'"
            echo "alias ccc='clear && claude -c'"
            echo "alias ccr='clear && claude -r'"
        } >> ~/.bashrc 2>/dev/null && ok "GitHub token exported to ~/.bashrc" \
            || warn "Could not write to ~/.bashrc (GH_TOKEN available from env)"
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

    if claude plugin marketplace list < /dev/null 2>/dev/null | grep -q "$name"; then
        return 0
    fi

    if claude plugin marketplace add "$source" < /dev/null 2>/dev/null; then
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

    local default_settings='{
        "permissions": {
            "allow": [],
            "deny": [],
            "ask": [],
            "defaultMode": "bypassPermissions"
        },
        "language": "Polski",
        "statusLine": {
            "type": "command",
            "command": "~/.claude/scripts/context-bar.sh"
        }
    }'

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

# Parse plugins and skills from configuration file
install_all_plugins_and_skills() {
    echo "📦 Installing plugins and skills..."

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }
    [[ -f "$CLAUDE_PLUGINS_FILE" ]] || { warn "$CLAUDE_PLUGINS_FILE not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        warn "Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" < /dev/null 2>/dev/null || true

    # Clean stale gemini skill symlinks (gemini-cli scans ~/.agents/skills/ directly)
    if [ -d "$HOME/.gemini/skills" ]; then
        find "$HOME/.gemini/skills" -maxdepth 1 -type l -delete 2>/dev/null || true
    fi

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0
    declare -A external_marketplaces

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Stop at MCP SERVERS section (handled by sync_mcp_servers)
        [[ "$line" =~ "MCP SERVERS" ]] && break
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        line=$(echo "$line" | xargs)
        [[ -z "$line" ]] && continue

        # New format: - <url> --skill <name>
        if [[ "$line" =~ ^-[[:space:]]+(https://[^[:space:]]+)[[:space:]]+--skill[[:space:]]+([^[:space:]]+) ]]; then
            local url="${BASH_REMATCH[1]}"
            local name="${BASH_REMATCH[2]}"
            install_skill "$name" "$url" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
            continue
        fi

        if [[ "$line" =~ @ ]]; then
            local name="${line%%@*}"
            local rest="${line#*@}"
            local type="${rest%%=*}"
            local source="${rest#*=}"

            case "$type" in
                skills)
                    install_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                github)
                    install_github_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                *)
                    if [[ -z "${external_marketplaces[$type]}" ]]; then
                        ensure_marketplace "$type" "$source" || continue
                        claude plugin marketplace update "$type" < /dev/null 2>/dev/null || true
                        external_marketplaces[$type]=1
                    fi
                    local rc=0; install_plugin "${name}@${type}" "$name" || rc=$?
                    update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
                    ;;
            esac
        else
            local rc=0; install_plugin "${line}@${OFFICIAL_MARKETPLACE_NAME}" "$line" || rc=$?
            update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
        fi
    done < "$CLAUDE_PLUGINS_FILE"

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

# Build list of expected plugins from configuration
build_expected_plugins_list() {
    local local_manifest="$LOCAL_MARKETPLACE_DIR/.claude-plugin/marketplace.json"

    declare -gA expected_plugins
    expected_plugins=()

    # Parse skills-plugins.txt (only plugins, skip skills and MCP)
    if [[ -f "$CLAUDE_PLUGINS_FILE" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ "$line" =~ "MCP SERVERS" ]] && break
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            line=$(echo "$line" | xargs)
            [[ -z "$line" ]] && continue

            if [[ "$line" =~ @ ]]; then
                local name="${line%%@*}"
                local rest="${line#*@}"
                local type="${rest%%=*}"
                case "$type" in
                    skills|github) ;; # skills - not in settings.json
                    *) expected_plugins["${name}@${type}"]=1 ;;
                esac
            else
                expected_plugins["${line}@${OFFICIAL_MARKETPLACE_NAME}"]=1
            fi
        done < "$CLAUDE_PLUGINS_FILE"
    fi

    # Parse local marketplace
    if [[ -f "$local_manifest" ]]; then
        while IFS= read -r plugin; do
            [[ -n "$plugin" ]] && expected_plugins["${plugin}@${LOCAL_MARKETPLACE_NAME}"]=1
        done < <(jq -r '.plugins[].name // empty' "$local_manifest" 2>/dev/null)
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

# =============================================================================
# MCP SERVERS
# =============================================================================

add_mcp_server() {
    local name="$1"
    local config="$2"

    if claude mcp list < /dev/null 2>/dev/null | grep -q "$name"; then
        ok "$name already configured"
        return
    fi

    if claude mcp add-json "$name" "$config" --scope user < /dev/null 2>/dev/null; then
        ok "Added: $name"
    else
        warn "Failed to add $name"
    fi
}

# Build JSON config for a stdio MCP server from parsed tokens
build_stdio_json() {
    local tokens=("$@")
    local command="${tokens[0]}"
    local args=()
    local env_pairs=()

    for token in "${tokens[@]:1}"; do
        if [[ "$token" =~ ^env:(.+)=(.+)$ ]]; then
            env_pairs+=("${BASH_REMATCH[1]}|${BASH_REMATCH[2]}")
        elif [[ "$token" =~ ^env:(.+)$ ]]; then
            local var="${BASH_REMATCH[1]}"
            env_pairs+=("${var}|${!var:-}")
        elif [[ "$token" =~ ^(requires:|header:) ]]; then
            continue
        else
            args+=("$token")
        fi
    done

    local json
    json=$(jq -n --arg cmd "$command" \
        --argjson args "$(printf '%s\n' "${args[@]}" | jq -R . | jq -s .)" \
        '{type: "stdio", command: $cmd, args: $args}')

    if [[ ${#env_pairs[@]} -gt 0 ]]; then
        local env_obj="{}"
        for pair in "${env_pairs[@]}"; do
            local key="${pair%%|*}"
            local val="${pair#*|}"
            env_obj=$(echo "$env_obj" | jq --arg k "$key" --arg v "$val" '. + {($k): $v}')
        done
        json=$(echo "$json" | jq --argjson env "$env_obj" '. + {env: $env}')
    fi

    echo "$json"
}

# Build JSON config for an HTTP MCP server from parsed tokens
build_http_json() {
    local tokens=("$@")
    local url="${tokens[0]}"
    local header_pairs=()

    for token in "${tokens[@]:1}"; do
        if [[ "$token" =~ ^header:(.+)=(.+)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local var="${BASH_REMATCH[2]}"
            header_pairs+=("${key}|${!var:-}")
        fi
    done

    local json
    json=$(jq -n --arg url "$url" '{type: "http", url: $url}')

    if [[ ${#header_pairs[@]} -gt 0 ]]; then
        local headers="{}"
        for pair in "${header_pairs[@]}"; do
            local key="${pair%%|*}"
            local val="${pair#*|}"
            headers=$(echo "$headers" | jq --arg k "$key" --arg v "$val" '. + {($k): $v}')
        done
        json=$(echo "$json" | jq --argjson h "$headers" '. + {headers: $h}')
    fi

    echo "$json"
}

# Parse MCP server declarations from skills-plugins.txt
parse_mcp_servers() {
    local file="$1"
    local in_mcp_section=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ "MCP SERVERS" ]]; then
            in_mcp_section=1
            continue
        fi
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        [[ $in_mcp_section -eq 0 ]] && continue

        line=$(echo "$line" | xargs)
        [[ -z "$line" ]] && continue

        [[ "$line" =~ ^- ]] && continue
        [[ ! "$line" =~ (stdio|http) ]] && continue

        local tags_str="all"
        if [[ "$line" =~ \[([a-z,]+)\]$ ]]; then
            tags_str="${BASH_REMATCH[1]}"
            line="${line% \[*}"
        fi

        if [[ "$tags_str" != "all" ]] && [[ ! ",$tags_str," =~ ,"$ENVIRONMENT_TAG", ]]; then
            continue
        fi

        local name type
        name="${line%% *}"; line="${line#* }"
        type="${line%% *}"; line="${line#* }"

        local tokens=()
        read -ra tokens <<< "$line"

        local skip=0
        for token in "${tokens[@]}"; do
            if [[ "$token" =~ ^requires:(.+)$ ]]; then
                local var="${BASH_REMATCH[1]}"
                if [[ -z "${!var:-}" ]]; then
                    warn "Skipping $name: $var not set"
                    skip=1
                    break
                fi
            fi
        done
        [[ $skip -eq 1 ]] && continue

        local json
        if [[ "$type" == "stdio" ]]; then
            json=$(build_stdio_json "${tokens[@]}")
        elif [[ "$type" == "http" ]]; then
            json=$(build_http_json "${tokens[@]}")
        else
            warn "Unknown MCP type: $type for $name"
            continue
        fi

        mcp_expected+=("$name")
        add_mcp_server "$name" "$json"
    done < "$file"
}

# Sync MCP servers: add from config, remove stale ones
sync_mcp_servers() {
    echo "🔧 Setting up MCP servers..."
    has_command jq || return 0

    [[ -f "$CLAUDE_PLUGINS_FILE" ]] || { warn "$CLAUDE_PLUGINS_FILE not found"; return 0; }

    local mcp_expected=()
    parse_mcp_servers "$CLAUDE_PLUGINS_FILE"

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
            if claude mcp remove "$name" --scope user < /dev/null 2>/dev/null; then
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
    sync_plugins
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
