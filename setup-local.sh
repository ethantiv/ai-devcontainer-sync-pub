#!/bin/bash

# macOS local setup: Install Claude Code configuration for local development
# Installs CLI, Playwright, plugins, skills, scripts, and settings on macOS

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly CLAUDE_SCRIPTS_DIR="$CLAUDE_DIR/scripts"

readonly CLAUDE_PLUGINS_FILE="configuration/claude-plugins.txt"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"

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
DEVCONTAINER_DIR="$SCRIPT_DIR/.devcontainer"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

has_command() {
    command -v "$1" &>/dev/null
}

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

ok()   { echo -e "  \033[32m✔︎\033[0m $1"; }
warn() { echo -e "  \033[33m⚠️\033[0m  $1"; }
fail() { echo -e "  \033[31m❌\033[0m $1"; }

# =============================================================================
# REQUIREMENTS CHECK
# =============================================================================

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
                jq) echo "  brew install jq" ;;
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

# =============================================================================
# CLAUDE CLI INSTALLATION
# =============================================================================

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

# =============================================================================
# PLAYWRIGHT INSTALLATION
# =============================================================================

install_playwright() {
    print_header "Playwright + Chromium"

    if npm ls -g @playwright/cli &>/dev/null; then
        ok "@playwright/cli already installed"
    else
        echo "📥 Installing @playwright/cli..."
        npm install -g @playwright/cli
        ok "@playwright/cli installed"
    fi

    npx -y playwright install chromium 2>/dev/null
    ok "Chromium installed"
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
}

setup_playwright_env() {
    # Set Playwright environment variables
    local shell_rc="$HOME/.zshrc"
    [[ -f "$shell_rc" ]] || shell_rc="$HOME/.bashrc"

    local env_vars=(
        "PLAYWRIGHT_MCP_BROWSER=chromium"
        "PLAYWRIGHT_MCP_VIEWPORT_SIZE=1920x1080"
    )

    for var in "${env_vars[@]}"; do
        local key="${var%%=*}"
        if ! grep -q "export $key=" "$shell_rc" 2>/dev/null; then
            echo "export $var" >> "$shell_rc"
        fi
        export "$var"
    done
    ok "Playwright environment configured"
}

# =============================================================================
# CLAUDE CONFIGURATION
# =============================================================================

apply_claude_settings() {
    local default_settings='{
        "permissions": {
            "allow": [],
            "deny": [],
            "ask": [],
            "defaultMode": "bypassPermissions"
        },
        "language": "Polski",
        "statusLine": {
            "type": "command",
            "command": "~/.claude/scripts/context-bar.sh"
        }
    }'

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
        ok "Settings merged with existing"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
        ok "Settings created"
    fi
}

copy_claude_memory() {
    local source_file="$DEVCONTAINER_DIR/configuration/CLAUDE.md.memory"
    if [[ -f "$source_file" ]]; then
        cp "$source_file" "$CLAUDE_DIR/CLAUDE.md"
        ok "CLAUDE.md synced"
    else
        warn "CLAUDE.md.memory not found"
    fi
}

sync_claude_scripts() {
    local source_dir="$DEVCONTAINER_DIR/scripts"
    [[ -d "$source_dir" ]] || return 0

    ensure_directory "$CLAUDE_SCRIPTS_DIR"

    local count=0
    for script in "$source_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        cp "$script" "$CLAUDE_SCRIPTS_DIR/"
        chmod +x "$CLAUDE_SCRIPTS_DIR/$(basename "$script")"
        ((count++))
    done

    if [[ $count -gt 0 ]]; then
        ok "Synced $count scripts to ~/.claude/scripts/"
    fi
}

setup_claude_configuration() {
    print_header "Claude configuration"

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"
    ensure_directory "$CLAUDE_DIR/skills"

    apply_claude_settings
    copy_claude_memory
    sync_claude_scripts
}

# =============================================================================
# PLUGIN INSTALLATION HELPERS
# =============================================================================

# Install a Claude plugin. Returns: 0=installed, 1=already present, 2=failed
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user < /dev/null 2>/dev/null; then
        ok "Installed: $display_name"
        return 0
    fi
    warn "Failed: $display_name"
    return 2
}

ensure_marketplace() {
    local name="$1"
    local source="$2"

    if claude plugin marketplace list 2>/dev/null | grep -q "$name"; then
        return 0
    fi

    if claude plugin marketplace add "$source" 2>/dev/null; then
        ok "Added marketplace: $name"
        return 0
    fi
    warn "Failed to add marketplace: $name"
    return 1
}

# =============================================================================
# SKILL INSTALLATION HELPERS
# =============================================================================

# Install skill using skills CLI (npx skills add)
install_skill() {
    local name="$1"
    local repo="$2"

    has_command npx || return 1
    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y skills add "https://github.com/$repo" --skill "$name" < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

# Install skill from direct GitHub path
install_github_skill() {
    local name="$1"
    local path="$2"

    local skill_dir="$CLAUDE_DIR/skills/$name"
    ensure_directory "$skill_dir"

    # Reconstruct URL: owner/repo/path -> raw.githubusercontent.com/owner/repo/main/path
    local owner="${path%%/*}"
    local rest="${path#*/}"
    local repo="${rest%%/*}"
    local file_path="${rest#*/}"
    local url="https://raw.githubusercontent.com/${owner}/${repo}/main/${file_path}"

    if curl -fsSL -o "$skill_dir/SKILL.md" "$url" < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

# =============================================================================
# PLUGINS AND SKILLS INSTALLATION
# =============================================================================

install_all_plugins_and_skills() {
    print_header "Installing plugins and skills"

    local plugins_file="$DEVCONTAINER_DIR/$CLAUDE_PLUGINS_FILE"

    [[ -f "$plugins_file" ]] || { warn "$plugins_file not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        warn "Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0
    local _seen_marketplaces=""

    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        line=$(echo "$line" | xargs)
        [[ -z "$line" ]] && continue

        if [[ "$line" =~ @ ]]; then
            local name="${line%%@*}"
            local rest="${line#*@}"
            local type="${rest%%=*}"
            local source="${rest#*=}"

            case "$type" in
                *-marketplace)
                    if [[ "$_seen_marketplaces" != *"|$type|"* ]]; then
                        ensure_marketplace "$type" "$source" || continue
                        claude plugin marketplace update "$type" 2>/dev/null || true
                        _seen_marketplaces="${_seen_marketplaces}|$type|"
                    fi
                    local rc=0; install_plugin "${name}@${type}" "$name" || rc=$?
                    case $rc in
                        0) plugins_installed=$((plugins_installed + 1)) ;;
                        1) plugins_skipped=$((plugins_skipped + 1)) ;;
                        2) plugins_failed=$((plugins_failed + 1)) ;;
                    esac
                    ;;
                skills)
                    install_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                github)
                    install_github_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                *)
                    warn "Unknown source type: $type for $name"
                    ;;
            esac
        else
            local rc=0; install_plugin "${line}@${OFFICIAL_MARKETPLACE_NAME}" "$line" || rc=$?
            case $rc in
                0) plugins_installed=$((plugins_installed + 1)) ;;
                1) plugins_skipped=$((plugins_skipped + 1)) ;;
                2) plugins_failed=$((plugins_failed + 1)) ;;
            esac
        fi
    done < "$plugins_file"

    echo ""
    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo "🚀 Claude Code Local Setup for macOS"
    echo "   Source: $DEVCONTAINER_DIR"

    check_requirements
    install_claude_cli
    install_playwright
    install_agent_browser
    setup_playwright_env
    setup_claude_configuration
    install_all_plugins_and_skills
}

main "$@"
