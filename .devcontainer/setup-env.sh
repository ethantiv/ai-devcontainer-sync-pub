#!/bin/bash

# DevContainer environment setup: authentication, Claude configuration, and plugins

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly LOCK_FILE="/tmp/dev-env-setup.lock"
readonly LOCK_TIMEOUT=60

readonly SSH_DIR="$HOME/.ssh"
readonly SSH_KEY_FILE="$SSH_DIR/id_rsa"
readonly SSH_KNOWN_HOSTS_FILE="$SSH_DIR/known_hosts"

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly CLAUDE_SCRIPTS_DIR="$CLAUDE_DIR/scripts"
readonly GEMINI_DIR="$HOME/.gemini"

readonly CLAUDE_PLUGINS_FILE="configuration/claude-plugins.txt"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
readonly LOCAL_MARKETPLACE_NAME="dev-marketplace"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

has_command() {
    command -v "$1" &>/dev/null
}

setup_file_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "⚠️  Another setup instance running, waiting..."
        if ! flock -w "$LOCK_TIMEOUT" 200; then
            echo "❌ Timeout waiting for lock. Remove $LOCK_FILE to force continue."
            exit 1
        fi
    fi
    trap 'exec 200>&-; rm -f "$LOCK_FILE"' EXIT
}

detect_workspace_folder() {
    WORKSPACE_FOLDER="${CODESPACE_VSCODE_FOLDER:-$PWD}"
    local env_type="local DevContainer"
    [[ -n "${CODESPACE_VSCODE_FOLDER}" ]] && env_type="Codespaces"
    echo "🌍 Detected $env_type environment: $WORKSPACE_FOLDER"
}

load_env_file() {
    local env_file="$WORKSPACE_FOLDER/.devcontainer/.env"
    if [[ -f "$env_file" ]]; then
        set -a && source "$env_file" && set +a
        echo "✅ Loaded .devcontainer/.env"
    fi
}

# =============================================================================
# AUTHENTICATION SETUP
# =============================================================================

setup_ssh_github_integration() {
    if [[ ! -f "$SSH_KNOWN_HOSTS_FILE" ]] || ! grep -q "github.com" "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null; then
        ssh-keyscan github.com >> "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null
        chmod 644 "$SSH_KNOWN_HOSTS_FILE"
        echo "✅ GitHub added to known_hosts"
    fi

    if ssh -T git@github.com -o ConnectTimeout=10 -o StrictHostKeyChecking=yes 2>&1 | grep -q "successfully authenticated"; then
        echo "✅ SSH connection to GitHub successful"
    else
        echo "⚠️  SSH key configured but connection test failed (key may not be in GitHub account)"
    fi
}

setup_ssh_authentication() {
    echo "🔐 Setting up SSH..."
    ensure_directory "$SSH_DIR"

    if [[ -f "$SSH_KEY_FILE" ]]; then
        echo "📄 Using existing ~/.ssh/id_rsa"
        chmod 600 "$SSH_KEY_FILE" 2>/dev/null || true
        return
    fi

    if [[ -n "${SSH_PRIVATE_KEY}" ]]; then
        if echo "${SSH_PRIVATE_KEY}" | base64 --decode > "$SSH_KEY_FILE" 2>/dev/null; then
            chmod 600 "$SSH_KEY_FILE"
            echo "✅ SSH key configured from SSH_PRIVATE_KEY"
            setup_ssh_github_integration
        else
            echo "❌ Failed to decode SSH_PRIVATE_KEY (invalid base64). Encode with: base64 -w 0 ~/.ssh/id_rsa"
        fi
        return
    fi

    echo "⚠️  No SSH key found. Set SSH_PRIVATE_KEY secret (base64-encoded) to enable SSH auth."
}

setup_github_token() {
    if [[ -z "${GH_TOKEN}" && -n "${GITHUB_TOKEN}" ]]; then
        export GH_TOKEN="${GITHUB_TOKEN}"
    fi

    if [[ -z "${GH_TOKEN}" ]]; then
        echo "❌ No GitHub token found (GH_TOKEN or GITHUB_TOKEN)"
        exit 1
    fi

    echo "✅ GitHub token configured"
    echo "export GH_TOKEN='${GH_TOKEN}'" >> ~/.bashrc
    echo "alias cc='clear && claude'" >> ~/.bashrc
}

# =============================================================================
# CLAUDE CONFIGURATION
# =============================================================================

reset_config_if_requested() {
    local reset_var="$1"
    local config_dir="$2"

    if [[ "${!reset_var}" == "true" && -d "$config_dir" ]]; then
        echo "  🔄 $reset_var=true - clearing $config_dir"
        rm -rf "${config_dir:?}"/* "${config_dir:?}"/.* 2>/dev/null || true
    fi
}

apply_claude_settings() {
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

    has_command jq || { echo "  ⚠️  jq not found - cannot manage settings"; return 0; }

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    echo "  ✅ Settings configured"
}

copy_claude_memory() {
    local source_file="$1/.devcontainer/configuration/CLAUDE.md.memory"
    [[ -f "$source_file" ]] && cp "$source_file" "$CLAUDE_DIR/CLAUDE.md" && echo "  ✅ CLAUDE.md synced"
}

sync_claude_files() {
    local source_dir="$1/.devcontainer/$2"
    local target_dir="$CLAUDE_DIR/$2"

    [[ -d "$source_dir" ]] || return 0

    # Remove files that no longer exist in source
    if [[ -d "$target_dir" ]]; then
        for file in "$target_dir"/*.md; do
            [[ -f "$file" ]] || continue
            [[ -f "$source_dir/$(basename "$file")" ]] || rm -f "$file"
        done 2>/dev/null
    fi

    # Copy all source files
    local files=("$source_dir"/*.md)
    if [[ -e "${files[0]}" ]]; then
        cp "$source_dir"/*.md "$target_dir/"
        echo "  ✅ Synced ${#files[@]} $2"
    fi
}

sync_claude_scripts() {
    local source_dir="$1/.devcontainer/scripts"
    [[ -d "$source_dir" ]] || return 0

    ensure_directory "$CLAUDE_SCRIPTS_DIR"

    for script in "$source_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        cp "$script" "$CLAUDE_SCRIPTS_DIR/"
        chmod +x "$CLAUDE_SCRIPTS_DIR/$(basename "$script")"
    done
    echo "  ✅ Synced scripts to ~/.claude/scripts/"
}

setup_claude_configuration() {
    echo "📄 Setting up Claude configuration..."

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    ensure_directory "$CLAUDE_DIR/commands"
    ensure_directory "$CLAUDE_DIR/agents"

    apply_claude_settings
    copy_claude_memory "$WORKSPACE_FOLDER"
    sync_claude_files "$WORKSPACE_FOLDER" "commands"
    sync_claude_files "$WORKSPACE_FOLDER" "agents"
    sync_claude_scripts "$WORKSPACE_FOLDER"
}

# =============================================================================
# CLAUDE PLUGINS
# =============================================================================

# Install a Claude plugin. Returns: 0=installed, 1=already present, 2=failed
# Note: < /dev/null prevents claude CLI from consuming stdin (breaks while-read loops)
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user < /dev/null 2>/dev/null; then
        echo "  ✅ Installed: $display_name"
        return 0
    fi
    echo "  ⚠️  Failed: $display_name"
    return 2
}

# Update counters based on install_plugin return code
# Usage: update_counters $? installed skipped failed
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
        echo "  ✅ Added marketplace: $name"
        return 0
    fi
    echo "  ⚠️  Failed to add marketplace: $name"
    return 1
}

# Parse plugins and skills from configuration file
# Handles: official marketplace, external marketplaces, vercel skills, github skills
install_all_plugins_and_skills() {
    local plugins_file="$WORKSPACE_FOLDER/.devcontainer/$CLAUDE_PLUGINS_FILE"

    echo "📦 Installing plugins and skills..."

    has_command claude || { echo "  ⚠️  Claude CLI not found"; return 0; }
    has_command jq || { echo "  ⚠️  jq not found"; return 0; }
    [[ -f "$plugins_file" ]] || { echo "  ⚠️  $plugins_file not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        echo "  ⚠️  Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0
    declare -A external_marketplaces

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        line=$(echo "$line" | xargs)
        [[ -z "$line" ]] && continue

        if [[ "$line" =~ @ ]]; then
            local name="${line%%@*}"
            local rest="${line#*@}"
            local type="${rest%%=*}"
            local source="${rest#*=}"

            case "$type" in
                *-marketplace)
                    if [[ -z "${external_marketplaces[$type]}" ]]; then
                        ensure_marketplace "$type" "$source" || continue
                        claude plugin marketplace update "$type" 2>/dev/null || true
                        external_marketplaces[$type]=1
                    fi
                    local rc=0; install_plugin "${name}@${type}" "$name" || rc=$?
                    update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
                    ;;
                vercel-skills)
                    install_vercel_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                github)
                    install_github_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                *)
                    echo "  ⚠️  Unknown source type: $type for $name"
                    ;;
            esac
        else
            local rc=0; install_plugin "${line}@${OFFICIAL_MARKETPLACE_NAME}" "$line" || rc=$?
            update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
        fi
    done < "$plugins_file"

    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

install_local_marketplace_plugins() {
    local marketplace_dir="$WORKSPACE_FOLDER/.devcontainer/plugins/$LOCAL_MARKETPLACE_NAME"
    local manifest="$marketplace_dir/.claude-plugin/marketplace.json"

    echo "📦 Installing local plugins..."

    has_command claude || return 0
    has_command jq || return 0
    [[ -f "$manifest" ]] || { echo "  ⚠️  Local marketplace not found"; return 0; }
    if ! ensure_marketplace "$LOCAL_MARKETPLACE_NAME" "$marketplace_dir"; then
        echo "  ⚠️  Skipping local marketplace plugins"
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
# MCP SERVERS
# =============================================================================

add_mcp_server() {
    local name="$1"
    local config="$2"

    if claude mcp list 2>/dev/null | grep -q "$name"; then
        echo "  ✅ $name already configured"
        return
    fi

    if claude mcp add-json "$name" "$config" --scope user 2>/dev/null; then
        echo "  ✅ Added: $name"
    else
        echo "  ⚠️  Failed to add $name"
    fi
}

setup_mcp_servers() {
    echo "🔧 Setting up MCP servers..."
    has_command claude || return 0

    add_mcp_server "aws-documentation" '{
        "type": "stdio",
        "command": "uvx",
        "args": ["awslabs.aws-documentation-mcp-server@latest"],
        "env": {
            "FASTMCP_LOG_LEVEL": "ERROR",
            "AWS_DOCUMENTATION_PARTITION": "aws"
        }
    }'

    add_mcp_server "terraform" '{
        "type": "stdio",
        "command": "uvx",
        "args": ["awslabs.terraform-mcp-server@latest"],
        "env": {
            "FASTMCP_LOG_LEVEL": "ERROR"
        }
    }'
}

# =============================================================================
# SKILL INSTALLATION HELPERS
# =============================================================================

# Install skill from Vercel skills repo using add-skill CLI
# Args: skill_name, repo (e.g., vercel-labs/agent-skills)
install_vercel_skill() {
    local name="$1"
    local repo="$2"

    has_command npx || return 1
    ensure_directory "$CLAUDE_DIR/skills"

    # Note: < /dev/null prevents npx from consuming stdin (which would break the while-read loop)
    if npx -y add-skill -g -y "$repo" -a claude-code -s "$name" < /dev/null 2>/dev/null; then
        echo "  ✅ Installed skill: $name"
        return 0
    fi
    echo "  ⚠️  Failed to install skill: $name"
    return 1
}

# Install skill from direct GitHub path
# Args: skill_name, path (e.g., owner/repo/path-to-SKILL.md)
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
        echo "  ✅ Installed skill: $name"
        return 0
    fi
    echo "  ⚠️  Failed to install skill: $name"
    return 1
}

# =============================================================================
# PLUGIN SYNCHRONIZATION
# =============================================================================

# Build list of expected plugins from configuration
# Sets global: expected_plugins[plugin_id]=1
build_expected_plugins_list() {
    local plugins_file="$WORKSPACE_FOLDER/.devcontainer/$CLAUDE_PLUGINS_FILE"
    local local_manifest="$WORKSPACE_FOLDER/.devcontainer/plugins/$LOCAL_MARKETPLACE_NAME/.claude-plugin/marketplace.json"

    declare -gA expected_plugins
    expected_plugins=()

    # Parse claude-plugins.txt (only plugins, skip skills)
    if [[ -f "$plugins_file" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            line=$(echo "$line" | xargs)
            [[ -z "$line" ]] && continue

            if [[ "$line" =~ @ ]]; then
                local name="${line%%@*}"
                local rest="${line#*@}"
                local type="${rest%%=*}"
                case "$type" in
                    *-marketplace) expected_plugins["${name}@${type}"]=1 ;;
                    # vercel-skills, github - skip (not in settings.json)
                esac
            else
                expected_plugins["${line}@${OFFICIAL_MARKETPLACE_NAME}"]=1
            fi
        done < "$plugins_file"
    fi

    # Parse local marketplace
    if [[ -f "$local_manifest" ]]; then
        while IFS= read -r plugin; do
            [[ -n "$plugin" ]] && expected_plugins["${plugin}@${LOCAL_MARKETPLACE_NAME}"]=1
        done < <(jq -r '.plugins[].name // empty' "$local_manifest" 2>/dev/null)
    fi
}

# Get installed plugins from settings.json
# Sets global: installed_plugins[plugin_id]=1
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
    echo "  ⚠️  Failed to uninstall: $display_name"
    return 1
}

# Sync: remove plugins not in expected list
sync_plugins() {
    echo "🔄 Synchronizing plugins..."
    has_command claude || { echo "  ⚠️  Claude CLI not found"; return 0; }
    has_command jq || { echo "  ⚠️  jq not found"; return 0; }

    build_expected_plugins_list
    get_installed_plugins

    local removed=0 failed=0
    for plugin in "${!installed_plugins[@]}"; do
        if [[ -z "${expected_plugins[$plugin]}" ]]; then
            uninstall_plugin "$plugin" && { ((removed++)) || true; } || { ((failed++)) || true; }
        fi
    done

    ((removed > 0 || failed > 0)) && echo "  📊 Sync: $removed removed, $failed failed" || echo "  ✅ All plugins in sync"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "🚀 Setting up development environment..."

    setup_file_lock
    detect_workspace_folder
    load_env_file

    setup_ssh_authentication
    setup_github_token

    # Optional config reset (set RESET_CLAUDE_CONFIG=true or RESET_GEMINI_CONFIG=true)
    reset_config_if_requested "RESET_CLAUDE_CONFIG" "$CLAUDE_DIR"
    reset_config_if_requested "RESET_GEMINI_CONFIG" "$GEMINI_DIR"

    setup_claude_configuration
    sync_plugins
    install_all_plugins_and_skills
    install_local_marketplace_plugins
    setup_mcp_servers

    echo "✅ Setup complete!"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
