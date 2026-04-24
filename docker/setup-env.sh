#!/bin/bash
# Claude Code setup script for Docker container
# Thin adapter: sets environment variables and sources shared setup library

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_FILE="$HOME/.claude/env-config.yaml"
ENVIRONMENT_TAG="docker"
LOCAL_MARKETPLACE_DIR="$HOME/.claude/plugins/dev-marketplace"
ENV_EXPORT_FILE="$HOME/.claude/env.sh"

source /opt/claude-config/scripts/setup-common.sh

# =============================================================================
# DOCKER-SPECIFIC FUNCTIONS
# =============================================================================

resolve_claude_binary() {
    CLAUDE_CMD="${CLAUDE_DIR}/bin/claude"
    [[ -x "$CLAUDE_CMD" ]] || CLAUDE_CMD="$(command -v claude 2>/dev/null || true)"
    [[ -x "$CLAUDE_CMD" ]] || { fail "Claude CLI not found"; exit 1; }
    claude() { "$CLAUDE_CMD" "$@"; }
    export -f claude
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "🚀 Setting up Claude Code..."

    resolve_claude_binary
    has_command jq || { fail "jq not found"; exit 1; }
    has_command yq || { fail "yq not found"; exit 1; }

    init_claude_dirs
    _write_env_export GH_TOKEN "${GH_TOKEN:-}"

    apply_claude_settings
    propagate_env_from_config
    configure_agent_browser
    run_plugin_sync_pipeline

    echo ""
    ok "Claude Code setup complete!"
    echo ""
    echo "Verify with:"
    echo "  claude mcp list"
    echo "  claude plugin marketplace list"
}

main "$@"
