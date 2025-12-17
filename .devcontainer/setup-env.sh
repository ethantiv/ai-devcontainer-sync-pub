#!/bin/bash

# Script to setup complete development environment during DevContainer initialization
# This script:
# - Manages file-based locking to prevent concurrent initialization
# - Verifies and configures GitHub CLI authentication (GH_TOKEN)
# - Sets up SSH authentication from base64-encoded secrets
# - Installs and enables Claude Code plugins from local marketplace
# - Copies Claude Code settings, commands, and agents to user directories

set -e

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

readonly LOCK_FILE="/tmp/dev-env-setup.lock"
readonly LOCK_TIMEOUT=60

readonly HOME_DIR="$HOME"
readonly SSH_DIR="$HOME_DIR/.ssh"
readonly SSH_KEY_FILE="$SSH_DIR/id_rsa"
readonly SSH_KNOWN_HOSTS_FILE="$SSH_DIR/known_hosts"

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
    local key_file="$1"

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

            setup_ssh_github_integration "$SSH_KEY_FILE"
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
        echo "🔧 Using your personal GH_TOKEN from Codespaces secrets"
    elif [[ -n "${GH_TOKEN}" ]]; then
        echo "✅ GitHub token found (GH_TOKEN)"
    elif [[ -n "${GITHUB_TOKEN}" ]]; then
        echo "✅ GitHub token found (GITHUB_TOKEN)"
        export GH_TOKEN="${GITHUB_TOKEN}"
        echo "🔧 Set GH_TOKEN=${GITHUB_TOKEN:0:20}... for GitHub CLI"
    else
        echo "❌ No GitHub token found (GH_TOKEN or GITHUB_TOKEN)"
        exit 1
    fi

    if [[ -n "${GH_TOKEN}" ]]; then
        echo "export GH_TOKEN='${GH_TOKEN}'" >> ~/.bashrc
        echo "🔧 Added GH_TOKEN to ~/.bashrc for session persistence"
    fi
}

# =============================================================================
# CLAUDE CONFIGURATION
# =============================================================================

copy_claude_settings() {
    local workspace_folder="$1"
    local source_file="$workspace_folder/.devcontainer/configuration/settings.devcontainer.json"
    local target_file="$HOME/.claude/settings.json"

    if [[ -f "$source_file" ]]; then
        cp "$source_file" "$target_file"
        echo "  ✅ Copied settings.devcontainer.json → ~/.claude/settings.json"
    else
        echo "  ⚠️  settings.devcontainer.json not found at: $source_file"
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

    if [[ -d "$source_dir" ]]; then
        local removed_count=0
        if [[ -d "$target_dir" ]]; then
            for existing_file in "$target_dir"/*.md; do
                if [[ -f "$existing_file" ]]; then
                    local filename=$(basename "$existing_file")
                    if [[ ! -f "$source_dir/$filename" ]]; then
                        rm -f "$existing_file"
                        removed_count=$((removed_count + 1))
                        echo "  🗑️  Removed deleted ${file_type%s}: $filename"
                    fi
                fi
            done 2>/dev/null
        fi

        if [[ -n "$(ls -A "$source_dir"/*.md 2>/dev/null)" ]]; then
            cp "$source_dir"/*.md "$target_dir/" 2>/dev/null
            local copied_count=$(ls -1 "$source_dir"/*.md 2>/dev/null | wc -l)
            echo "  ✅ Copied $copied_count $file_type files to ~/.claude/$file_type/"
        else
            echo "  ⚠️  No .md $file_type files found in: $source_dir"
        fi

        if [[ $removed_count -gt 0 ]]; then
            echo "  🧹 Removed $removed_count obsolete $file_type files"
        fi
    else
        echo "  ⚠️  ${file_type^} directory not found: $source_dir"
    fi
}

setup_claude_configuration() {
    local workspace_folder="$1"
    echo "📄 Copying Claude configuration files..."

    local claude_dir="$HOME/.claude"

    ensure_directory "$claude_dir" ".claude"
    ensure_directory "$claude_dir/commands" ".claude/commands"
    ensure_directory "$claude_dir/agents" ".claude/agents"

    copy_claude_settings "$workspace_folder"
    copy_claude_memory "$workspace_folder"
    copy_claude_files "$workspace_folder" "commands"
    copy_claude_files "$workspace_folder" "agents"

    echo "📄 Claude configuration files setup completed!"
}

setup_local_marketplace() {
    local workspace_folder="$1"
    local marketplace_path="$workspace_folder/.devcontainer/plugins/dev-marketplace"
    local marketplace_json="$marketplace_path/.claude-plugin/marketplace.json"

    echo "🏠 Setting up local Claude Code marketplace..."

    if ! command -v jq &> /dev/null; then
        echo "  ❌ jq is required but not installed"
        return 1
    fi

    if [[ ! -d "$marketplace_path" ]]; then
        echo "  ⚠️  Local marketplace directory not found: $marketplace_path"
        echo "      Skipping local marketplace setup"
        return 0
    fi

    if [[ ! -f "$marketplace_json" ]]; then
        echo "  ⚠️  marketplace.json not found: $marketplace_json"
        echo "      Skipping local marketplace setup"
        return 0
    fi

    local marketplace_name=$(jq -r '.name // "dev-marketplace"' "$marketplace_json")

    # Remove existing marketplace with same name to ensure fresh configuration
    echo "🔄 Removing existing $marketplace_name marketplace (if any)..."
    if claude plugin marketplace remove "$marketplace_name" >/dev/null 2>&1; then
        echo "  ✅ Removed existing $marketplace_name"
    else
        echo "  ℹ️  No existing $marketplace_name to remove"
    fi

    # Add local marketplace from path
    echo "➕ Adding local marketplace: $marketplace_name"
    if output=$(claude plugin marketplace add "$marketplace_path" 2>&1); then
        echo "  ✅ Successfully added local marketplace: $marketplace_name"
    elif [[ "$output" == *"already"* ]]; then
        echo "  ℹ️  Local marketplace already configured"
    else
        echo "  ❌ Failed to add local marketplace: $output"
        return 1
    fi

    # Parse and install all plugins from marketplace.json
    echo "📦 Installing plugins from local marketplace..."
    local plugins=$(jq -r '.plugins[].name' "$marketplace_json" 2>/dev/null)

    if [[ -z "$plugins" ]]; then
        echo "  ⚠️  No plugins found in marketplace.json"
        return 0
    fi

    while IFS= read -r plugin_name; do
        [[ -z "$plugin_name" ]] && continue
        local plugin_id="${plugin_name}@${marketplace_name}"
        echo "➕ Installing local plugin: $plugin_id"

        if output=$(claude plugin install "$plugin_id" 2>&1); then
            echo "  ✅ Successfully installed and enabled: $plugin_name"
        elif [[ "$output" == *"already"* ]]; then
            echo "  ℹ️  Plugin already installed: $plugin_name"
        else
            echo "  ❌ Failed to install $plugin_name: $output"
            continue
        fi
    done <<< "$plugins"

    echo "🎉 Local marketplace setup completed!"
}

setup_claude_plugins() {
    local workspace_folder="$1"

    echo "🔌 Setting up Claude Code plugins..."

    # Setup local marketplace only
    setup_local_marketplace "$workspace_folder"

    echo "🎉 Claude plugins setup completed!"
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

    setup_claude_configuration "$WORKSPACE_FOLDER"

    setup_claude_plugins "$WORKSPACE_FOLDER"

    echo "✅ Development environment setup completed successfully!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
