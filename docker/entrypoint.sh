#!/bin/bash
# Entrypoint script for Claude Code container
# Syncs configuration files and runs setup on first start

set -e

readonly CLAUDE_DIR="$HOME/.claude"
readonly CONFIGURED_MARKER="$CLAUDE_DIR/.configured"
readonly CONFIG_SOURCE="/opt/claude-config"

# =============================================================================
# CONFIGURATION SYNC (runs every startup)
# =============================================================================

sync_config_files() {
    # Ensure directories exist
    mkdir -p "$CLAUDE_DIR/commands" "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/skills"

    # Sync CLAUDE.md (global user instructions)
    if [[ -f "$CONFIG_SOURCE/CLAUDE.md" ]]; then
        cp "$CONFIG_SOURCE/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
    fi

    # Sync commands
    if [[ -d "$CONFIG_SOURCE/commands" ]]; then
        # Remove commands that no longer exist in source
        for file in "$CLAUDE_DIR/commands"/*.md; do
            [[ -f "$file" ]] || continue
            [[ -f "$CONFIG_SOURCE/commands/$(basename "$file")" ]] || rm -f "$file"
        done
        # Copy all source commands
        cp "$CONFIG_SOURCE/commands"/*.md "$CLAUDE_DIR/commands/" 2>/dev/null || true
    fi

    # Sync scripts
    if [[ -d "$CONFIG_SOURCE/scripts" ]]; then
        # Remove scripts that no longer exist in source
        for file in "$CLAUDE_DIR/scripts"/*.sh; do
            [[ -f "$file" ]] || continue
            [[ -f "$CONFIG_SOURCE/scripts/$(basename "$file")" ]] || rm -f "$file"
        done
        # Copy all source scripts and make executable
        cp "$CONFIG_SOURCE/scripts"/*.sh "$CLAUDE_DIR/scripts/" 2>/dev/null || true
        chmod +x "$CLAUDE_DIR/scripts"/*.sh 2>/dev/null || true
    fi
}

# Always sync config files (from image to volume)
sync_config_files

# =============================================================================
# FIRST-RUN SETUP (plugins and MCP servers)
# =============================================================================

if [[ ! -f "$CONFIGURED_MARKER" ]]; then
    if [[ -n "${CLAUDE_CODE_OAUTH_TOKEN}" ]]; then
        echo "🚀 First run detected - configuring Claude Code..."

        if /usr/local/bin/setup-claude.sh; then
            touch "$CONFIGURED_MARKER"
            echo "✅ Configuration complete!"
        else
            echo "⚠️  Setup encountered errors (will retry on next start)"
        fi
    else
        echo "⚠️  CLAUDE_CODE_OAUTH_TOKEN not set - skipping plugin setup"
        echo "   Set the key and restart container to configure plugins"
    fi
fi

# =============================================================================
# STARTUP INFO
# =============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   AI Code DevContainer                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  claude --version    : $(claude --version 2>/dev/null || echo 'not available')                         ║"
echo "║  gemini --version    : $(gemini --version 2>/dev/null || echo 'not available')                         ║"
echo "║  terraform version   : $(terraform version -json 2>/dev/null | jq -r '.terraform_version' || echo 'n/a')                              ║"
echo "║  aws --version       : $(aws --version 2>/dev/null | cut -d' ' -f1 | cut -d'/' -f2 || echo 'n/a')                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Working directory   : $(pwd)                    ║"
echo "║  API Key configured  : $([ -n "${CLAUDE_CODE_OAUTH_TOKEN}" ] && echo 'Yes' || echo 'No')                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Execute command (default: bash)
exec "$@"
