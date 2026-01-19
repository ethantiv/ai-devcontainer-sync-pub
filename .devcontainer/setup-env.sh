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
readonly GEMINI_DIR="$HOME/.gemini"

readonly CLAUDE_PLUGINS_FILE="configuration/claude-plugins.txt"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
readonly LOCAL_MARKETPLACE_NAME="dev-marketplace"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    local dir="$1"
    [[ -d "$dir" ]] || mkdir -p "$dir"
}

require_command() {
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
        [[ "$(stat -c '%a' "$SSH_KEY_FILE")" == "600" ]] || chmod 600 "$SSH_KEY_FILE"
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
        "language": "Polski"
    }'

    require_command jq || { echo "  ⚠️  jq not found - cannot manage settings"; return; }

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

    [[ -d "$source_dir" ]] || return

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

setup_claude_configuration() {
    echo "📄 Setting up Claude configuration..."

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/commands"
    ensure_directory "$CLAUDE_DIR/agents"

    apply_claude_settings
    copy_claude_memory "$WORKSPACE_FOLDER"
    sync_claude_files "$WORKSPACE_FOLDER" "commands"
    sync_claude_files "$WORKSPACE_FOLDER" "agents"
}

# =============================================================================
# CLAUDE PLUGINS
# =============================================================================

# Returns: 0=installed, 1=already present, 2=failed
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user 2>/dev/null; then
        echo "  ✅ Installed: $display_name"
        return 0
    fi
    echo "  ⚠️  Failed: $display_name"
    return 2
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

install_claude_plugins() {
    local plugins_file="$WORKSPACE_FOLDER/.devcontainer/$CLAUDE_PLUGINS_FILE"

    echo "📦 Installing plugins..."

    require_command claude || { echo "  ⚠️  Claude CLI not found"; return; }
    require_command jq || { echo "  ⚠️  jq not found"; return; }
    [[ -f "$plugins_file" ]] || { echo "  ⚠️  $plugins_file not found"; return; }
    ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO" || return
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    local installed=0 skipped=0 failed=0

    while IFS= read -r plugin || [[ -n "$plugin" ]]; do
        [[ -z "$plugin" || "$plugin" =~ ^[[:space:]]*# ]] && continue
        plugin=$(echo "$plugin" | xargs)
        [[ -z "$plugin" ]] && continue

        local rc=0
        install_plugin "$plugin" "${plugin%@*}" || rc=$?
        case $rc in
            0) installed=$((installed + 1)) ;;
            1) skipped=$((skipped + 1)) ;;
            2) failed=$((failed + 1)) ;;
        esac
    done < "$plugins_file"

    echo "  📊 Official: $installed installed, $skipped present, $failed failed"
}

install_local_marketplace_plugins() {
    local marketplace_dir="$WORKSPACE_FOLDER/.devcontainer/plugins/$LOCAL_MARKETPLACE_NAME"
    local manifest="$marketplace_dir/.claude-plugin/marketplace.json"

    echo "📦 Installing local plugins..."

    require_command claude || return
    require_command jq || return
    [[ -f "$manifest" ]] || { echo "  ⚠️  Local marketplace not found"; return; }
    ensure_marketplace "$LOCAL_MARKETPLACE_NAME" "$marketplace_dir" || return

    local installed=0 skipped=0 failed=0

    while IFS= read -r plugin; do
        [[ -z "$plugin" ]] && continue

        local rc=0
        install_plugin "${plugin}@${LOCAL_MARKETPLACE_NAME}" "$plugin" || rc=$?
        case $rc in
            0) installed=$((installed + 1)) ;;
            1) skipped=$((skipped + 1)) ;;
            2) failed=$((failed + 1)) ;;
        esac
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
    require_command claude || return

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

    add_mcp_server "aws-api" '{
        "type": "stdio",
        "command": "uvx",
        "args": ["awslabs.aws-api-mcp-server@latest"]
    }'
}

# =============================================================================
# VERCEL SKILLS
# =============================================================================

install_vercel_skills() {
    local skills=(vercel-react-best-practices web-design-guidelines)

    echo "📚 Installing Vercel skills..."

    require_command npx || { echo "  ⚠️  npx not found"; return; }
    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y add-skill -g -y vercel-labs/agent-skills -a claude-code -s "${skills[@]}" 2>/dev/null; then
        echo "  ✅ Installed ${#skills[@]} skills: ${skills[*]}"
    else
        echo "  ⚠️  Failed to install Vercel skills"
    fi
}

install_agent_browser_skill() {
    echo "📚 Installing agent-browser skill..."

    local skill_dir="$CLAUDE_DIR/skills/agent-browser"
    ensure_directory "$skill_dir"

    if curl -fsSL -o "$skill_dir/SKILL.md" \
        "https://raw.githubusercontent.com/vercel-labs/agent-browser/main/skills/agent-browser/SKILL.md" 2>/dev/null; then
        echo "  ✅ Installed agent-browser skill"
    else
        echo "  ⚠️  Failed to install agent-browser skill"
    fi
}

install_ast_grep_skill() {
    echo "📚 Installing ast-grep skill..."

    require_command claude || return

    ensure_marketplace "ast-grep-marketplace" "ast-grep/claude-skill" || return

    local rc=0
    install_plugin "ast-grep@ast-grep-marketplace" "ast-grep" || rc=$?
    case $rc in
        0) echo "  ✅ ast-grep skill installed" ;;
        1) echo "  ✅ ast-grep skill already present" ;;
        2) echo "  ⚠️  Failed to install ast-grep skill" ;;
    esac
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
    install_vercel_skills
    install_agent_browser_skill
    install_ast_grep_skill
    install_claude_plugins
    install_local_marketplace_plugins
    setup_mcp_servers

    echo "✅ Setup complete!"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
