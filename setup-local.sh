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

CONFIG_FILE="$CONFIG_DIR/env-config.yaml"
ENVIRONMENT_TAG="local"
LOCAL_MARKETPLACE_DIR="$CONFIG_DIR/plugins/dev-marketplace"
ENV_EXPORT_FILE="$HOME/.bashrc"

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

    check_macos

    local missing=()
    local dep
    for dep in jq yq node npm npx brew; do
        if has_command "$dep"; then
            ok "$dep present"
        else
            missing+=("$dep")
            fail "$dep not found"
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        warn "Missing dependencies. Install them with:"
        echo ""
        for dep in "${missing[@]}"; do
            case "$dep" in
                jq|yq) echo "  brew install $dep" ;;
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

    local pw_cache="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"
    if find "$pw_cache" -path '*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium' -print -quit 2>/dev/null | grep -q .; then
        ok "Chromium already installed"
    else
        npx -y playwright install chromium 2>/dev/null
        ok "Chromium installed"
    fi
}

setup_claude_configuration() {
    print_header "Claude configuration"

    init_claude_dirs
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
    run_plugin_sync_pipeline
}

main "$@"
