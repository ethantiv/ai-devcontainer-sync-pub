#!/bin/bash
# Entrypoint script for Claude Code container
# Syncs configuration files and runs setup on first start

set -e

readonly CLAUDE_DIR="$HOME/.claude"
readonly CONFIGURED_MARKER="$CLAUDE_DIR/.configured"
readonly CONFIG_SOURCE="/opt/claude-config"
readonly CLAUDE_BIN="$CLAUDE_DIR/bin/claude"

# =============================================================================
# CLAUDE INSTALLATION (installs to volume on first run)
# =============================================================================

install_claude() {
    if [[ -x "$CLAUDE_BIN" ]]; then
        echo "  ✔︎ Claude Code already installed in volume"
        return 0
    fi

    echo "🔧 Installing Claude Code to volume..."

    # Create bin directory in volume
    mkdir -p "$CLAUDE_DIR/bin"

    # Set TMPDIR to avoid cross-device rename errors (volume is ext4, /tmp is tmpfs)
    export TMPDIR="$CLAUDE_DIR/tmp"
    mkdir -p "$TMPDIR"

    # Download and install Claude with custom install directory
    if CLAUDE_INSTALL_DIR="$CLAUDE_DIR" curl -fsSL https://claude.ai/install.sh | bash; then
        # The installer puts claude in $CLAUDE_INSTALL_DIR/bin/claude
        if [[ -x "$CLAUDE_BIN" ]]; then
            echo "  ✔︎ Claude Code installed to $CLAUDE_DIR/bin/"
        elif [[ -x "$HOME/.local/bin/claude" ]]; then
            # Fallback: move from default location if installer ignored CLAUDE_INSTALL_DIR
            mv "$HOME/.local/bin/claude" "$CLAUDE_BIN"
            echo "  ✔︎ Claude Code installed to $CLAUDE_DIR/bin/"
        else
            echo "  ❌ Claude installation succeeded but binary not found"
            return 1
        fi
    else
        echo "  ❌ Failed to install Claude Code"
        return 1
    fi
}

# Install Claude to volume (persists across container recreates)
install_claude

# =============================================================================
# CONFIGURATION SYNC (runs every startup)
# =============================================================================

sync_config_files() {
    # Ensure directories exist
    mkdir -p "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/skills" "$CLAUDE_DIR/plugins"

    # Sync CLAUDE.md (global user instructions)
    if [[ -f "$CONFIG_SOURCE/CLAUDE.md" ]]; then
        cp "$CONFIG_SOURCE/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
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

    # Sync local marketplace plugins
    if [[ -d "$CONFIG_SOURCE/plugins/dev-marketplace" ]]; then
        cp -r "$CONFIG_SOURCE/plugins/dev-marketplace" "$CLAUDE_DIR/plugins/"
    fi

    # Sync plugin configuration file
    if [[ -f "$CONFIG_SOURCE/skills-plugins.txt" ]]; then
        cp "$CONFIG_SOURCE/skills-plugins.txt" "$CLAUDE_DIR/skills-plugins.txt"
    fi
}

# Always sync config files (from image to volume)
sync_config_files

# =============================================================================
# FIRST-RUN SETUP (MCP servers, settings, plugins)
# =============================================================================

# Run full setup on first start (no token required)
if [[ ! -f "$CONFIGURED_MARKER" ]]; then
    echo "🚀 First run detected - configuring Claude Code..."
    if /usr/local/bin/setup-claude.sh; then
        touch "$CONFIGURED_MARKER"
        echo "✅ Configuration complete!"
    else
        echo "⚠️  Setup encountered errors (will retry on next start)"
    fi
fi

# =============================================================================
# GITHUB CLI AUTHENTICATION
# =============================================================================

setup_gh_auth() {
    if [[ -n "${GH_TOKEN}" ]] && command -v gh &>/dev/null; then
        if ! gh auth status &>/dev/null; then
            echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null && \
                echo "  ✔︎ GitHub CLI authenticated" || \
                echo "  ⚠️  GitHub CLI auth failed"
        fi
        gh auth setup-git 2>/dev/null
    fi
}

# Authenticate GitHub CLI if token is available
setup_gh_auth

# =============================================================================
# STARTUP INFO
# =============================================================================

# Use claude from volume
claude_version() {
    if [[ -x "$CLAUDE_BIN" ]]; then
        "$CLAUDE_BIN" --version 2>/dev/null || echo 'not available'
    else
        echo 'not installed'
    fi
}

echo ""
echo "AI Code DevContainer"
echo ""
echo "  claude --version    : $(claude_version)"
echo "  gemini --version    : $(gemini --version 2>/dev/null || echo 'not available')"
echo "  playwright-cli      : $(playwright-cli --version 2>/dev/null || echo 'not available')"
echo ""
echo "  Working directory   : $(pwd)"
echo "  Config initialized  : $([ -f "$CONFIGURED_MARKER" ] && echo 'Yes' || echo 'No')"
echo ""

# Execute command (default: bash)
exec "$@"
