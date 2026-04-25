#!/bin/bash

# DevContainer environment setup: authentication, Claude configuration, and plugins

set -e

# Ensure ~/.local/bin is in PATH (Claude CLI installed there by install.sh)
export PATH="$HOME/.local/bin:$PATH"

# Persist PATH for non-login shells (gh shim, credential helpers)
if ! grep -q '\.local/bin.*PATH' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly LOCK_FILE="/tmp/dev-env-setup.lock"
readonly LOCK_TIMEOUT=60

readonly SSH_DIR="$HOME/.ssh"
readonly SSH_KEY_FILE="$SSH_DIR/id_rsa"
readonly SSH_KNOWN_HOSTS_FILE="$SSH_DIR/known_hosts"

# Required by setup-common.sh (CONFIG_FILE and LOCAL_MARKETPLACE_DIR
# resolved inside detect_workspace_folder before sourcing the library).
CONFIG_FILE=""
ENVIRONMENT_TAG="devcontainer"
LOCAL_MARKETPLACE_DIR=""
ENV_EXPORT_FILE="$HOME/.bashrc"

# =============================================================================
# ENVIRONMENT-SPECIFIC FUNCTIONS
# =============================================================================

setup_file_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        warn "Another setup instance running, waiting..."
        if ! flock -w "$LOCK_TIMEOUT" 200; then
            fail "Timeout waiting for lock. Remove $LOCK_FILE to force continue."
            exit 1
        fi
    fi
    trap 'exec 200>&-; rm -f "$LOCK_FILE"' EXIT
}

detect_workspace_folder() {
    WORKSPACE_FOLDER="${CODESPACE_VSCODE_FOLDER:-$PWD}"
    CONFIG_FILE="$WORKSPACE_FOLDER/config/env-config.yaml"
    LOCAL_MARKETPLACE_DIR="$WORKSPACE_FOLDER/config/plugins/dev-marketplace"
    local env_type="local DevContainer"
    [[ -n "${CODESPACE_VSCODE_FOLDER}" ]] && env_type="Codespaces"
    echo "🌍 Detected $env_type environment: $WORKSPACE_FOLDER"

    source "$WORKSPACE_FOLDER/config/scripts/setup-common.sh"
}

load_env_file() {
    local env_file="$WORKSPACE_FOLDER/config/.env"
    if [[ -f "$env_file" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            # Export KEY=VALUE (split on first =)
            local key="${line%%=*}"
            local value="${line#*=}"
            export "$key=$value"
        done < "$env_file"
        ok "Loaded .env"
    fi
}

# =============================================================================
# AUTHENTICATION SETUP
# =============================================================================

setup_ssh_github_integration() {
    if [[ ! -f "$SSH_KNOWN_HOSTS_FILE" ]] || ! grep -q "github.com" "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null; then
        ssh-keyscan github.com >> "$SSH_KNOWN_HOSTS_FILE" 2>/dev/null
        chmod 644 "$SSH_KNOWN_HOSTS_FILE"
        ok "GitHub added to known_hosts"
    fi

    ssh -T git@github.com -o ConnectTimeout=10 -o StrictHostKeyChecking=yes 2>&1 | grep -q "successfully authenticated" \
        && { ok "SSH connection to GitHub successful"; return; }
    warn "SSH key configured but connection test failed (key may not be in GitHub account)"
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
            ok "SSH key configured from SSH_PRIVATE_KEY"
            setup_ssh_github_integration
        else
            fail "Failed to decode SSH_PRIVATE_KEY (invalid base64). Encode with: base64 -w 0 ~/.ssh/id_rsa"
        fi
        return
    fi

    warn "No SSH key found. Set SSH_PRIVATE_KEY secret (base64-encoded) to enable SSH auth."
}

setup_github_token() {
    if [[ -z "${GH_TOKEN}" && -n "${GITHUB_TOKEN}" ]]; then
        export GH_TOKEN="${GITHUB_TOKEN}"
    fi

    if [[ -z "${GH_TOKEN}" ]]; then
        fail "No GitHub token found (GH_TOKEN or GITHUB_TOKEN)"
        exit 1
    fi

    ok "GitHub token configured"
    gh auth setup-git 2>/dev/null || warn "Failed to configure gh as git credential helper"

    _write_env_export GH_TOKEN "$GH_TOKEN"
    if ! grep -q "^alias cc=" "$HOME/.bashrc" 2>/dev/null; then
        cat >> "$HOME/.bashrc" << 'ALIASEOF'

alias cc='clear && claude'
alias ccc='clear && claude -c'
alias ccr='clear && claude -r'
ALIASEOF
    fi
}

setup_git_identity() {
    local user_name="${GIT_USER_NAME:-}"
    local user_email="${GIT_USER_EMAIL:-}"

    if [[ -n "$user_name" ]]; then
        git config --global user.name "$user_name"
    fi
    if [[ -n "$user_email" ]]; then
        git config --global user.email "$user_email"
    fi
}

setup_multi_github() {
    # Skip if no work token configured
    [[ -n "${GH_TOKEN_WORK:-}" ]] || return 0

    echo "🔐 Setting up multi-GitHub account routing..."

    local work_email="${GIT_USER_EMAIL_WORK:-${GIT_USER_EMAIL:-}}"

    # Add includeIf for work repos (idempotent — unset first, then set)
    local work_dirs="${GH_WORK_DIRS:-}"
    if [[ -n "$work_dirs" ]]; then
        # Remove all existing includeIf entries for .gitconfig-work
        while read -r key value; do
            [[ "$value" == "~/.gitconfig-work" ]] && git config --global --unset-all "$key" 2>/dev/null || true
        done < <(git config --global --get-regexp 'includeIf\..*\.path' 2>/dev/null)
        # Add includeIf for each configured directory
        IFS='|' read -ra dirs <<< "$work_dirs"
        for dir in "${dirs[@]}"; do
            [[ -z "$dir" ]] && continue
            # Ensure trailing slash for gitdir matching
            dir="${dir%/}/"
            git config --global "includeIf.gitdir:${dir}.path" '~/.gitconfig-work'
        done
    else
        # Fallback: no dirs configured, skip includeIf
        warn "GH_WORK_DIRS not set — skipping git includeIf config (set git.work.dirs in env-config.yaml)"
    fi

    # Write ~/.gitconfig-work
    cat > "$HOME/.gitconfig-work" << EOF
[user]
    email = ${work_email}

[credential "https://github.com"]
    helper =
    helper = !~/.local/bin/git-credential-github-multi
EOF
    ok "Git identity routing configured"

    # Write credential helper script
    ensure_directory "$HOME/.local/bin"
    cat > "$HOME/.local/bin/git-credential-github-multi" << 'CREDEOF'
#!/bin/bash
# Credential helper for work GitHub account
[ "$1" != "get" ] && exit 0
if [[ -z "$GH_TOKEN_WORK" ]]; then
    echo "quit=true"
    exit 0
fi
while IFS= read -r line; do
    [[ -z "$line" ]] && break
done
echo "username=x-access-token"
echo "password=${GH_TOKEN_WORK}"
CREDEOF
    chmod +x "$HOME/.local/bin/git-credential-github-multi"
    ok "Credential helper installed"

    # Remove legacy gh() wrapper from bashrc (replaced by shim)
    if grep -q '^gh()' "$HOME/.bashrc" 2>/dev/null; then
        sed -i '/^gh()/,/^}/d' "$HOME/.bashrc"
        sed -i '/# Multi-GitHub: .* account routing/d' "$HOME/.bashrc"
    fi

    _write_env_export GH_TOKEN_WORK "$GH_TOKEN_WORK"

    # Write gh CLI shim (works in both interactive and non-interactive shells)
    cat > "$HOME/.local/bin/gh" << 'GHEOF'
#!/bin/bash
# Multi-GitHub account router — shadows /usr/bin/gh
# Routes GH_TOKEN based on URL arguments and PWD
token="${GH_TOKEN:-}"
work_orgs="${GH_WORK_ORGS:-RIS-Navify-Data-Platform}"

# URL-based detection: scan args for work org URLs
for arg in "$@"; do
    if [[ "$arg" =~ github\.com[:/](${work_orgs})(/|$) ]]; then
        token="${GH_TOKEN_WORK:-$token}"
        break
    fi
done

# PWD-based detection (fallback): check configured work directories
if [[ "$token" == "${GH_TOKEN:-}" && -n "${GH_WORK_DIRS:-}" ]]; then
    IFS='|' read -ra _dirs <<< "$GH_WORK_DIRS"
    for _d in "${_dirs[@]}"; do
        _d="${_d/#\~/$HOME}"
        case "$PWD" in
            "${_d}"/*|"${_d}")
                token="${GH_TOKEN_WORK:-$token}"
                break
                ;;
        esac
    done
fi

GH_TOKEN="$token" exec /usr/bin/gh "$@"
GHEOF
    chmod +x "$HOME/.local/bin/gh"
    ok "gh CLI shim installed"

    # Warn about missing token scopes (non-fatal)
    if command -v /usr/bin/gh &>/dev/null; then
        if GH_TOKEN="$GH_TOKEN_WORK" /usr/bin/gh auth status 2>&1 | grep -q "Missing required token scopes"; then
            warn "GH_TOKEN_WORK may be missing required scopes (e.g., read:org). Run: GH_TOKEN=\$GH_TOKEN_WORK gh auth status"
        fi
    fi

    ok "Multi-GitHub setup complete (personal + work account)"
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

setup_claude_configuration() {
    echo "📄 Setting up Claude configuration..."

    init_claude_dirs
    apply_claude_settings
    copy_claude_memory "$WORKSPACE_FOLDER"
    sync_claude_scripts "$WORKSPACE_FOLDER"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "🚀 Setting up development environment..."

    setup_file_lock
    detect_workspace_folder
    load_env_file

    propagate_env_from_config
    configure_agent_browser
    setup_git_identity
    setup_ssh_authentication
    setup_github_token
    setup_multi_github

    reset_config_if_requested "RESET_CLAUDE_CONFIG" "$CLAUDE_DIR"

    setup_claude_configuration
    run_plugin_sync_pipeline

    ok "Setup complete!"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
