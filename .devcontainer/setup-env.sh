#!/bin/bash

# Script to setup complete development environment during DevContainer initialization
# This script:
# - Manages file-based locking to prevent concurrent initialization
# - Verifies and configures GitHub CLI authentication (GH_TOKEN)
# - Sets up SSH authentication from base64-encoded secrets
# - Copies Claude Code settings, commands, and agents to user directories

set -e

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

readonly LOCK_FILE="/tmp/dev-env-setup.lock"
readonly LOCK_TIMEOUT=60

readonly SSH_DIR="$HOME/.ssh"
readonly SSH_KEY_FILE="$SSH_DIR/id_rsa"
readonly SSH_KNOWN_HOSTS_FILE="$SSH_DIR/known_hosts"

# Environment variables for optional full reset (set to "true" to enable)
# RESET_CLAUDE_CONFIG=true  - Clears ~/.claude including plugins cache
# RESET_GEMINI_CONFIG=true  - Clears ~/.gemini
readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$HOME/.claude/settings.json"
readonly GEMINI_DIR="$HOME/.gemini"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    local dir="$1"
    local name="$2"
    if [[ ! -d "$dir" ]]; then
        echo "📁 Creating $name directory"
        mkdir -p "$dir"
    fi
}

setup_file_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "⚠️  Another instance of development environment setup is already running"
        echo "    Waiting for it to complete..."
        if ! flock -w "$LOCK_TIMEOUT" 200; then
            echo "❌ Timeout waiting for lock. Another setup may be stuck."
            echo "    To force continue, remove: $LOCK_FILE"
            exit 1
        fi
        echo "✅ Lock acquired, continuing setup"
    fi

    # Release file descriptor 200 (lock file handle) and remove lock file on exit
    trap 'exec 200>&-; rm -f "$LOCK_FILE"' EXIT
}

detect_workspace_folder() {
    if [[ -n "${CODESPACE_VSCODE_FOLDER}" ]]; then
        WORKSPACE_FOLDER="${CODESPACE_VSCODE_FOLDER}"
        echo "🌍 Detected Codespaces environment: $WORKSPACE_FOLDER"
    else
        WORKSPACE_FOLDER="${PWD}"
        echo "🖥️ Detected local DevContainer environment: $WORKSPACE_FOLDER"
    fi
}

# =============================================================================
# AUTHENTICATION SETUP
# =============================================================================

setup_ssh_github_integration() {
    if [[ ! -f "$SSH_KNOWN_HOSTS_FILE" ]] || ! grep -q "github.com" "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null; then
        echo "🌐 Adding GitHub to SSH known_hosts..."
        ssh-keyscan github.com >> "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null
        chmod 644 "$SSH_KNOWN_HOSTS_FILE"
        echo "✅ GitHub added to known_hosts"
    else
        echo "✅ GitHub already in known_hosts"
    fi

    echo "🔍 Testing SSH connection to GitHub..."
    if ssh -T git@github.com -o ConnectTimeout=10 -o StrictHostKeyChecking=yes 2>&1 | grep -q "successfully authenticated"; then
        echo "✅ SSH connection to GitHub successful"
    else
        echo "⚠️  SSH connection test failed, but key has been configured"
        echo "    This is normal if the key hasn't been added to your GitHub account yet"
    fi
}

setup_ssh_authentication() {
    echo "🔐 Setting up SSH key for GitHub..."

    ensure_directory "$SSH_DIR" ".ssh"

    if [[ -f "$SSH_KEY_FILE" ]]; then
        echo "📄 Using existing ~/.ssh/id_rsa file"
        local current_perms=$(stat -c "%a" "$SSH_KEY_FILE")
        if [[ "$current_perms" != "600" ]]; then
            chmod "600" "$SSH_KEY_FILE"
            echo "🔒 Updated file permissions to 600"
        fi

    elif [[ -n "${SSH_PRIVATE_KEY}" ]]; then
        echo "🔑 Found SSH_PRIVATE_KEY environment variable"

        if echo "${SSH_PRIVATE_KEY}" | base64 --decode > "$SSH_KEY_FILE" 2>/dev/null; then
            chmod "600" "$SSH_KEY_FILE"
            echo "✅ SSH private key authentication configured successfully"
            echo "🔒 Set SSH key permissions to 600 (owner read/write only)"

            setup_ssh_github_integration
        else
            echo "❌ Failed to decode SSH_PRIVATE_KEY - invalid base64 format"
            echo "    Please ensure SSH_PRIVATE_KEY is properly base64 encoded"
            echo "    To encode your key: base64 -w 0 ~/.ssh/id_rsa"
        fi

    else
        echo "⚠️  No SSH_PRIVATE_KEY environment variable found and no existing ~/.ssh/id_rsa"
        echo "    To set up SSH authentication in Codespaces:"
        echo "    1. Get your local ~/.ssh/id_rsa content"
        echo "    2. Encode it with: base64 -w 0 ~/.ssh/id_rsa"
        echo "    3. Add the result as SSH_PRIVATE_KEY secret in GitHub Codespaces"
        echo "    4. Restart the DevContainer"
        echo ""
        echo "    SSH will not be authenticated but the environment is ready."
    fi

    echo "🎉 SSH setup completed!"
}

setup_github_token() {
    echo "🔐 Checking GitHub token availability..."

    if [[ -n "${CODESPACES}" && -n "${GH_TOKEN}" ]]; then
        echo "✅ Codespaces environment with GH_TOKEN found"
    elif [[ -n "${GH_TOKEN}" ]]; then
        echo "✅ GitHub token found (GH_TOKEN)"
    elif [[ -n "${GITHUB_TOKEN}" ]]; then
        echo "✅ GitHub token found (GITHUB_TOKEN)"
        export GH_TOKEN="${GITHUB_TOKEN}"
    else
        echo "❌ No GitHub token found (GH_TOKEN or GITHUB_TOKEN)"
        exit 1
    fi

    echo "export GH_TOKEN='${GH_TOKEN}'" >> ~/.bashrc
    echo "🔧 Added GH_TOKEN to ~/.bashrc for session persistence"
}

# =============================================================================
# CONFIG RESET FUNCTIONS
# =============================================================================

reset_config_if_requested() {
    local reset_var="$1"
    local config_dir="$2"
    local config_name="$3"

    if [[ "${!reset_var}" == "true" ]]; then
        echo "  $reset_var=true detected - performing full reset..."
        if [[ -d "$config_dir" ]]; then
            rm -rf "${config_dir:?}"/* "${config_dir:?}"/.* 2>/dev/null || true
            echo "  Cleared $config_dir directory"
        fi
    else
        echo "  Preserving existing $config_name configuration"
    fi
}

# =============================================================================
# CLAUDE CONFIGURATION
# =============================================================================

apply_claude_settings() {
    local target_file="$HOME/.claude/settings.json"

    # Default settings to apply (merged with existing settings)
    # These won't overwrite user-added settings like enabledPlugins
    local default_settings='{
        "permissions": {
            "allow": [],
            "deny": [],
            "ask": [],
            "defaultMode": "bypassPermissions"
        },
        "language": "Polski"
    }'

    if [[ -f "$target_file" ]]; then
        # Merge: existing settings take precedence, but add missing keys from defaults
        # Using jq to deep merge (defaults * existing = existing wins on conflicts)
        if command -v jq &> /dev/null; then
            local merged
            merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$target_file" 2>/dev/null)
            if [[ -n "$merged" ]]; then
                echo "$merged" > "$target_file"
                echo "  ✅ Merged default settings into ~/.claude/settings.json"
            else
                echo "  ⚠️  Failed to merge settings - keeping existing file"
            fi
        else
            echo "  ⚠️  jq not found - cannot merge settings"
        fi
    else
        # No existing file - create with defaults
        echo "$default_settings" | jq '.' > "$target_file"
        echo "  ✅ Created ~/.claude/settings.json with default settings"
    fi
}

copy_claude_memory() {
    local workspace_folder="$1"
    local source_file="$workspace_folder/.devcontainer/configuration/CLAUDE.md.memory"
    local target_file="$HOME/.claude/CLAUDE.md"

    if [[ -f "$source_file" ]]; then
        cp "$source_file" "$target_file"
        echo "  ✅ Copied CLAUDE.md.memory → ~/.claude/CLAUDE.md"
    else
        echo "  ⚠️  CLAUDE.md.memory not found at: $source_file"
    fi
}

copy_claude_files() {
    local workspace_folder="$1"
    local file_type="$2"
    local source_dir="$workspace_folder/.devcontainer/$file_type"
    local target_dir="$HOME/.claude/$file_type"

    if [[ ! -d "$source_dir" ]]; then
        echo "  ⚠️  ${file_type^} directory not found: $source_dir"
        return
    fi

    local removed_count=0
    if [[ -d "$target_dir" ]]; then
        for existing_file in "$target_dir"/*.md; do
            [[ -f "$existing_file" ]] || continue
            local filename
            filename=$(basename "$existing_file")
            if [[ ! -f "$source_dir/$filename" ]]; then
                rm -f "$existing_file"
                removed_count=$((removed_count + 1))
                echo "  🗑️  Removed deleted ${file_type%s}: $filename"
            fi
        done 2>/dev/null
    fi

    local source_files
    source_files=("$source_dir"/*.md)
    if [[ -e "${source_files[0]}" ]]; then
        cp "$source_dir"/*.md "$target_dir/"
        echo "  ✅ Copied ${#source_files[@]} $file_type files to ~/.claude/$file_type/"
    else
        echo "  ⚠️  No .md $file_type files found in: $source_dir"
    fi

    if [[ $removed_count -gt 0 ]]; then
        echo "  🧹 Removed $removed_count obsolete $file_type files"
    fi
}

setup_claude_configuration() {
    local workspace_folder="$1"
    echo "📄 Copying Claude configuration files..."

    ensure_directory "$CLAUDE_DIR" ".claude"
    ensure_directory "$CLAUDE_DIR/commands" ".claude/commands"
    ensure_directory "$CLAUDE_DIR/agents" ".claude/agents"

    apply_claude_settings
    copy_claude_memory "$workspace_folder"
    copy_claude_files "$workspace_folder" "commands"
    copy_claude_files "$workspace_folder" "agents"

    echo "📄 Claude configuration files setup completed!"
}

# =============================================================================
# CLAUDE PLUGINS (from official marketplace)
# =============================================================================

# Plugins list is loaded from external file for easier management
# See: .devcontainer/configuration/claude-plugins.txt
# Official marketplace: https://github.com/anthropics/claude-plugins-official
readonly CLAUDE_PLUGINS_FILE="configuration/claude-plugins.txt"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"

# Helper function to install a single plugin
# Returns: 0=installed, 1=already present, 2=failed
install_single_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    # Check if plugin is already in enabledPlugins (using --arg to prevent injection)
    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        echo "  ✅ Plugin '$display_name' already installed"
        return 1
    elif claude plugin install "$plugin" --scope user 2>/dev/null; then
        echo "  ✅ Installed plugin: $display_name"
        return 0
    else
        echo "  ⚠️  Failed to install plugin: $display_name"
        return 2
    fi
}

ensure_marketplace_available() {
    echo "  🏪 Ensuring official marketplace is available..."

    if claude plugin marketplace list 2>/dev/null | grep -q "$OFFICIAL_MARKETPLACE_NAME"; then
        echo "  ✅ Marketplace '$OFFICIAL_MARKETPLACE_NAME' already configured"
    else
        echo "  📦 Adding official marketplace from GitHub..."
        if claude plugin marketplace add "$OFFICIAL_MARKETPLACE_REPO" 2>/dev/null; then
            echo "  ✅ Marketplace added successfully"
        else
            echo "  ⚠️  Failed to add marketplace - plugins may not install"
            return 1
        fi
    fi

    echo "  🔄 Updating marketplace..."
    if claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null; then
        echo "  ✅ Marketplace updated"
    else
        echo "  ⚠️  Failed to update marketplace - continuing with cached version"
    fi
}

install_claude_plugins() {
    local workspace_folder="$1"
    local plugins_file="$workspace_folder/.devcontainer/$CLAUDE_PLUGINS_FILE"

    echo "📦 Installing Claude Code plugins..."

    if ! command -v claude &> /dev/null; then
        echo "  ⚠️  Claude CLI not found - skipping plugin installation"
        return 0
    fi

    if [[ ! -f "$plugins_file" ]]; then
        echo "  ⚠️  Plugins file not found: $plugins_file"
        return 0
    fi

    if ! command -v jq &> /dev/null; then
        echo "  ⚠️  jq not found - cannot check installed plugins"
        return 0
    fi

    if ! ensure_marketplace_available; then
        echo "  ⚠️  Marketplace not available - skipping plugin installation"
        return 0
    fi

    local installed_count=0
    local skipped_count=0
    local failed_count=0

    while IFS= read -r plugin || [[ -n "$plugin" ]]; do
        [[ -z "$plugin" || "$plugin" =~ ^[[:space:]]*# ]] && continue
        plugin=$(echo "$plugin" | xargs)
        [[ -z "$plugin" ]] && continue

        local plugin_name="${plugin%@*}"

        install_single_plugin "$plugin" "$plugin_name"
        case $? in
            0) installed_count=$((installed_count + 1)) ;;
            1) skipped_count=$((skipped_count + 1)) ;;
            2) failed_count=$((failed_count + 1)) ;;
        esac
    done < "$plugins_file"

    echo "  📊 Plugins: $installed_count installed, $skipped_count already present, $failed_count failed"
}

# =============================================================================
# LOCAL DEV-MARKETPLACE PLUGINS
# =============================================================================

install_local_marketplace_plugins() {
    local workspace_folder="$1"
    local marketplace_dir="$workspace_folder/.devcontainer/plugins/dev-marketplace"
    local marketplace_name="dev-marketplace"

    echo "📦 Installing local dev-marketplace plugins..."

    if ! command -v claude &> /dev/null; then
        echo "  ⚠️  Claude CLI not found - skipping local marketplace setup"
        return 0
    fi

    if [[ ! -f "$marketplace_dir/.claude-plugin/marketplace.json" ]]; then
        echo "  ⚠️  Local marketplace not found: $marketplace_dir"
        return 0
    fi

    # Add local marketplace if not already added
    if claude plugin marketplace list 2>/dev/null | grep -q "$marketplace_name"; then
        echo "  ✅ Marketplace '$marketplace_name' already configured"
    else
        echo "  📦 Adding local marketplace..."
        if claude plugin marketplace add "$marketplace_dir" 2>/dev/null; then
            echo "  ✅ Added local marketplace: $marketplace_name"
        else
            echo "  ⚠️  Failed to add local marketplace"
            return 1
        fi
    fi

    # Install plugins from local marketplace
    if ! command -v jq &> /dev/null; then
        echo "  ⚠️  jq not found - cannot parse marketplace.json"
        return 0
    fi

    local plugins_file="$marketplace_dir/.claude-plugin/marketplace.json"
    local installed_count=0
    local skipped_count=0
    local failed_count=0

    # Use while read to handle plugin names with spaces correctly
    while IFS= read -r plugin; do
        [[ -z "$plugin" ]] && continue
        local full_plugin_name="${plugin}@${marketplace_name}"

        install_single_plugin "$full_plugin_name" "$plugin"
        case $? in
            0) installed_count=$((installed_count + 1)) ;;
            1) skipped_count=$((skipped_count + 1)) ;;
            2) failed_count=$((failed_count + 1)) ;;
        esac
    done < <(jq -r '.plugins[].name' "$plugins_file" 2>/dev/null)

    echo "  📊 Local plugins: $installed_count installed, $skipped_count already present, $failed_count failed"
}

# =============================================================================
# CLAUDE MCP SERVERS
# =============================================================================

setup_claude_mcp_servers() {
    echo "🔧 Setting up Claude Code MCP servers..."

    if ! command -v claude &> /dev/null; then
        echo "  ⚠️  Claude CLI not found - skipping MCP server setup"
        return 0
    fi

    local added_count=0
    local skipped_count=0

    if claude mcp list 2>/dev/null | grep -q "playwright"; then
        echo "  ✅ MCP server 'playwright' already configured"
        skipped_count=$((skipped_count + 1))
    else
        local playwright_config='{
            "type": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@playwright/mcp@latest",
                "--headless",
                "--browser",
                "chromium",
                "--executable-path",
                "/home/vscode/.cache/ms-playwright/chromium-1200/chrome-linux/chrome"
            ]
        }'
        if claude mcp add-json playwright "$playwright_config" --scope user 2>/dev/null; then
            echo "  ✅ Added MCP server: playwright"
            added_count=$((added_count + 1))
        else
            echo "  ⚠️  Failed to add MCP server: playwright"
        fi
    fi

    echo "  📊 MCP servers: $added_count added, $skipped_count already present"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    echo "🚀 Setting up development environment..."

    setup_file_lock

    detect_workspace_folder

    setup_ssh_authentication
    setup_github_token

    # Handle optional full reset before syncing configuration
    reset_config_if_requested "RESET_CLAUDE_CONFIG" "$CLAUDE_DIR" "Claude Code"
    reset_config_if_requested "RESET_GEMINI_CONFIG" "$GEMINI_DIR" "Gemini CLI"

    setup_claude_configuration "$WORKSPACE_FOLDER"
    install_claude_plugins "$WORKSPACE_FOLDER"
    install_local_marketplace_plugins "$WORKSPACE_FOLDER"
    setup_claude_mcp_servers

    echo "✅ Development environment setup completed successfully!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
