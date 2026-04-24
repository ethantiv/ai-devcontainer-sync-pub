#!/bin/bash

# macOS local setup: Install Claude Code configuration for local development

set -e

# Require Bash 4+ for associative arrays (macOS default is 3.2)
# Auto-re-exec with Homebrew bash if available
if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    for brew_bash in /opt/homebrew/bin/bash /usr/local/bin/bash; do
        if [[ -x "$brew_bash" ]] && "$brew_bash" -c '[[ ${BASH_VERSINFO[0]} -ge 4 ]]' 2>/dev/null; then
            exec "$brew_bash" "$0" "$@"
        fi
    done
    echo "❌ Bash 4+ required (found ${BASH_VERSION}). Install with: brew install bash"
    exit 1
fi

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get script directory (supports symlinks)
get_script_dir() {
    local source="${BASH_SOURCE[0]}"
    while [[ -L "$source" ]]; do
        local dir="$(cd -P "$(dirname "$source")" && pwd)"
        source="$(readlink "$source")"
        [[ "$source" != /* ]] && source="$dir/$source"
    done
    cd -P "$(dirname "$source")" && pwd
}

SCRIPT_DIR="$(get_script_dir)"
CONFIG_DIR="$SCRIPT_DIR/config"

CLAUDE_DIR="$HOME/.claude"
CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CONFIG_FILE="$CONFIG_DIR/env-config.yaml"
ENVIRONMENT_TAG="local"
OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
LOCAL_MARKETPLACE_NAME="dev-marketplace"
LOCAL_MARKETPLACE_DIR="$CONFIG_DIR/plugins/$LOCAL_MARKETPLACE_NAME"
ENV_EXPORT_FILE="$HOME/.bashrc"

# Source shared library
source "$CONFIG_DIR/scripts/setup-common.sh"

# =============================================================================
# LOCAL-SPECIFIC FUNCTIONS
# =============================================================================

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        fail "This script is designed for macOS only"
        exit 1
    fi
    ok "Running on macOS $(sw_vers -productVersion)"
}

check_requirements() {
    print_header "Checking requirements"

    local missing=()

    check_macos

    if ! has_command jq; then
        missing+=("jq")
        fail "jq not found"
    else
        ok "jq $(jq --version 2>/dev/null | head -1)"
    fi

    if ! has_command yq; then
        missing+=("yq")
        fail "yq not found"
    else
        ok "yq $(yq --version 2>/dev/null | head -1)"
    fi

    if ! has_command node; then
        missing+=("node")
        fail "node not found"
    else
        ok "node $(node --version)"
    fi

    if ! has_command npm; then
        missing+=("npm")
        fail "npm not found"
    else
        ok "npm $(npm --version 2>/dev/null)"
    fi

    if ! has_command npx; then
        missing+=("npx")
        fail "npx not found"
    else
        ok "npx available"
    fi

    if ! has_command brew; then
        missing+=("brew")
        fail "brew not found"
    else
        ok "brew $(brew --version 2>/dev/null | head -1)"
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        warn "Missing dependencies. Install them with:"
        echo ""
        for dep in "${missing[@]}"; do
            case "$dep" in
                jq) echo "  jq is required — install with: brew install jq" ;;
                yq) echo "  yq is required — install with: brew install yq" ;;
                node|npm|npx) echo "  brew install node" ;;
                brew) echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"" ;;
            esac
        done
        echo ""
        echo "After installing, re-run this script."
        exit 1
    fi

    ok "All requirements satisfied"
}

install_claude_cli() {
    print_header "Claude CLI"

    if has_command claude; then
        ok "Claude CLI already installed"
        return
    fi

    echo "📥 Installing Claude CLI..."
    brew install --cask claude-code
    ok "Claude CLI installed"
}

install_agent_browser() {
    print_header "Agent Browser"

    if npm ls -g agent-browser &>/dev/null; then
        ok "agent-browser already installed"
    else
        echo "📥 Installing agent-browser..."
        npm install -g agent-browser
        ok "agent-browser installed"
    fi

    # Install Chromium browser (required by agent-browser)
    npx -y playwright install chromium 2>/dev/null
    ok "Chromium installed"
}

setup_claude_configuration() {
    print_header "Claude configuration"

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"
    ensure_directory "$CLAUDE_DIR/skills"

    apply_claude_settings
    propagate_env_from_config
    configure_agent_browser
    copy_claude_memory "$SCRIPT_DIR"
    sync_claude_scripts "$SCRIPT_DIR"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo "🚀 Claude Code Local Setup for macOS"
    echo "   Source: $CONFIG_DIR"

    check_requirements
    install_claude_cli
    install_agent_browser
    setup_claude_configuration
    sync_plugins
    sync_skills
    install_all_plugins_and_skills
    install_external_marketplace_plugins
    install_local_marketplace_plugins
    sync_marketplaces
    sync_mcp_servers
}

main "$@"
