#!/bin/bash

# macOS local setup: Install Claude Code configuration for local development
# Installs CLI, agent-browser, plugins, skills, scripts, and settings on macOS

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly CLAUDE_SCRIPTS_DIR="$CLAUDE_DIR/scripts"

readonly CLAUDE_PLUGINS_FILE="configuration/skills-plugins.txt"
readonly OFFICIAL_MARKETPLACE_NAME="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"
readonly LOCAL_MARKETPLACE_NAME="dev-marketplace"

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
# AGENT BROWSER INSTALLATION
# =============================================================================

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

# =============================================================================
# LOOP CLI INSTALLATION
# =============================================================================

install_loop() {
    print_header "Loop CLI"

    local loop_dir="$SCRIPT_DIR/src"

    if [[ ! -d "$loop_dir" ]]; then
        warn "src/ directory not found"
        return 0
    fi

    (cd "$loop_dir" && npm install --omit=dev 2>/dev/null)
    chmod +x "$loop_dir/bin/cli.js" "$loop_dir/scripts/"*.sh
    sudo ln -sf "$loop_dir/bin/cli.js" /usr/local/bin/loop

    if command -v loop &>/dev/null; then
        ok "loop CLI installed"
    else
        warn "Failed to install loop CLI"
    fi
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

copy_claude_memory() {
    local source_file="$DEVCONTAINER_DIR/configuration/CLAUDE.md.memory"
    [[ -f "$source_file" ]] && cp "$source_file" "$CLAUDE_DIR/CLAUDE.md" && ok "CLAUDE.md synced"
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
# Args: skill_name, url (e.g., https://github.com/vercel-labs/agent-skills)
install_skill() {
    local name="$1"
    local url="$2"

    has_command npx || return 1
    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y skills add "$url" --skill "$name" --agent claude-code gemini-cli -g -y < /dev/null 2>/dev/null; then
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

        # New format: - <url> --skill <name>
        if [[ "$line" =~ ^-[[:space:]]+(https://[^[:space:]]+)[[:space:]]+--skill[[:space:]]+([^[:space:]]+) ]]; then
            local url="${BASH_REMATCH[1]}"
            local name="${BASH_REMATCH[2]}"
            install_skill "$name" "$url" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
            continue
        fi

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
# LOCAL MARKETPLACE PLUGINS
# =============================================================================

install_local_marketplace_plugins() {
    print_header "Installing local plugins"

    local marketplace_dir="$DEVCONTAINER_DIR/plugins/$LOCAL_MARKETPLACE_NAME"
    local manifest="$marketplace_dir/.claude-plugin/marketplace.json"

    has_command claude || return 0
    has_command jq || return 0
    [[ -f "$manifest" ]] || { warn "Local marketplace not found"; return 0; }

    if ! ensure_marketplace "$LOCAL_MARKETPLACE_NAME" "$marketplace_dir"; then
        warn "Skipping local marketplace plugins"
        return 0
    fi

    local installed=0 skipped=0 failed=0

    while IFS= read -r plugin; do
        [[ -z "$plugin" ]] && continue
        local rc=0; install_plugin "${plugin}@${LOCAL_MARKETPLACE_NAME}" "$plugin" || rc=$?
        case $rc in
            0) installed=$((installed + 1)) ;;
            1) skipped=$((skipped + 1)) ;;
            2) failed=$((failed + 1)) ;;
        esac
    done < <(jq -r '.plugins[].name' "$manifest" 2>/dev/null)

    echo ""
    echo "  📊 Local: $installed installed, $skipped present, $failed failed"
}

# =============================================================================
# PLUGIN SYNCHRONIZATION
# =============================================================================

# Build newline-separated list of expected plugin IDs from configuration
# Sets global: _expected_plugins
build_expected_plugins_list() {
    local plugins_file="$DEVCONTAINER_DIR/$CLAUDE_PLUGINS_FILE"
    local local_manifest="$DEVCONTAINER_DIR/plugins/$LOCAL_MARKETPLACE_NAME/.claude-plugin/marketplace.json"

    _expected_plugins=""

    # Parse skills-plugins.txt (only plugins, skip skills/github)
    if [[ -f "$plugins_file" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            line=$(echo "$line" | xargs)
            [[ -z "$line" ]] && continue

            # Skip new-format skill entries (- https://... --skill ...)
            [[ "$line" =~ ^-[[:space:]] ]] && continue

            if [[ "$line" =~ @ ]]; then
                local name="${line%%@*}"
                local rest="${line#*@}"
                local type="${rest%%=*}"
                case "$type" in
                    skills|github) ;; # not in settings.json
                    *) _expected_plugins="${_expected_plugins}${name}@${type}"$'\n' ;;
                esac
            else
                _expected_plugins="${_expected_plugins}${line}@${OFFICIAL_MARKETPLACE_NAME}"$'\n'
            fi
        done < "$plugins_file"
    fi

    # Parse local marketplace
    if [[ -f "$local_manifest" ]]; then
        while IFS= read -r plugin; do
            [[ -n "$plugin" ]] && _expected_plugins="${_expected_plugins}${plugin}@${LOCAL_MARKETPLACE_NAME}"$'\n'
        done < <(jq -r '.plugins[].name // empty' "$local_manifest" 2>/dev/null)
    fi
}

# Get installed plugins from settings.json
# Sets global: _installed_plugins
get_installed_plugins() {
    _installed_plugins=""
    [[ -f "$CLAUDE_SETTINGS_FILE" ]] || return 0
    while IFS= read -r plugin; do
        [[ -n "$plugin" ]] && _installed_plugins="${_installed_plugins}${plugin}"$'\n'
    done < <(jq -r '.enabledPlugins | keys[]' "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
}

# Uninstall a plugin by its full ID
uninstall_plugin() {
    local plugin="$1"
    local display_name="${plugin%%@*}"
    if claude plugin uninstall "$plugin" --scope user < /dev/null 2>/dev/null; then
        echo "  🗑️  Uninstalled: $display_name"
        return 0
    fi
    warn "Failed to uninstall: $display_name"
    return 1
}

# Sync: remove plugins not in expected list
sync_plugins() {
    print_header "Synchronizing plugins"

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    build_expected_plugins_list
    get_installed_plugins

    local removed=0 failed=0
    while IFS= read -r plugin; do
        [[ -z "$plugin" ]] && continue
        if [[ $'\n'"$_expected_plugins" != *$'\n'"$plugin"$'\n'* ]]; then
            uninstall_plugin "$plugin" && removed=$((removed + 1)) || failed=$((failed + 1))
        fi
    done <<< "$_installed_plugins"

    if ((removed > 0 || failed > 0)); then
        echo ""
        echo "  📊 Sync: $removed removed, $failed failed"
    else
        ok "All plugins in sync"
    fi
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
    install_agent_browser
    install_loop
    setup_claude_configuration
    sync_plugins
    install_all_plugins_and_skills
    install_local_marketplace_plugins
}

main "$@"
