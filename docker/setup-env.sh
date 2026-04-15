#!/bin/bash
# Claude Code setup script for Docker container
# Thin adapter: sets environment variables and sources shared setup library

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

CLAUDE_DIR="$HOME/.claude"
CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CONFIG_PARSER="/opt/loop/lib/config-parser.js"
CONFIG_FILE="$CLAUDE_DIR/env-config.yaml"
ENVIRONMENT_TAG="docker"
OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
LOCAL_MARKETPLACE_NAME="dev-marketplace"
LOCAL_MARKETPLACE_DIR="$CLAUDE_DIR/plugins/$LOCAL_MARKETPLACE_NAME"
ENV_EXPORT_FILE="$CLAUDE_DIR/env.sh"

# =============================================================================
# SOURCE SHARED LIBRARY
# =============================================================================

source /opt/claude-config/scripts/setup-common.sh

# =============================================================================
# DOCKER-SPECIFIC FUNCTIONS
# =============================================================================

setup_github_token() {
    if [[ -n "${GH_TOKEN}" ]]; then
        if ! grep -q "^export GH_TOKEN=" "$ENV_EXPORT_FILE" 2>/dev/null; then
            echo "export GH_TOKEN='${GH_TOKEN}'" >> "$ENV_EXPORT_FILE" \
                && ok "GitHub token exported to env.sh" \
                || warn "Could not write to env.sh (GH_TOKEN available from env)"
        fi
    fi
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
    configure_agent_browser
    sync_plugins
    sync_skills
    install_all_plugins_and_skills
    install_external_marketplace_plugins
    install_local_marketplace_plugins
    sync_marketplaces
    sync_mcp_servers

    echo ""
    ok "Claude Code setup complete!"
    echo ""
    echo "Verify with:"
    echo "  claude mcp list"
    echo "  claude plugin marketplace list"
}

main "$@"
