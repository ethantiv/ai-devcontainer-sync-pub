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

readonly ENVIRONMENT_TAG="local"
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
CONFIG_DIR="$SCRIPT_DIR/config"

# Config parser (replaces skills-plugins.txt DSL)
CONFIG_PARSER="$SCRIPT_DIR/src/lib/config-parser.js"
CONFIG_FILE="$CONFIG_DIR/env-config.yaml"

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
                jq) echo "  jq is required — install with: brew install jq" ;;
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
    has_command jq || { warn "jq not found - cannot manage settings"; return 0; }

    local claude_config
    claude_config=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section claude) || {
        warn "Failed to parse Claude settings"; return 0
    }

    # statusLine stays hardcoded — design doc marks it out of scope
    local default_settings
    default_settings=$(echo "$claude_config" | jq --argjson sl '{"type":"command","command":"~/.claude/scripts/context-bar.sh"}' '{
        permissions: .permissions,
        language: .language,
        statusLine: $sl
    }')

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    ok "Settings configured"
}

sync_claude_scripts() {
    local source_dir="$CONFIG_DIR/scripts"
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
    local source_file="$CONFIG_DIR/CLAUDE.md.memory"
    [[ -f "$source_file" ]] && cp "$source_file" "$CLAUDE_DIR/CLAUDE.md" && ok "CLAUDE.md synced"
}

propagate_env_from_config() {
    local config_json
    config_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --all 2>/dev/null) || return 0

    local tz locale git_name git_email work_email work_orgs
    tz=$(echo "$config_json" | jq -r '.timezone // empty')
    locale=$(echo "$config_json" | jq -r '.locale // empty')
    git_name=$(echo "$config_json" | jq -r '.git.personal.name // empty')
    git_email=$(echo "$config_json" | jq -r '.git.personal.email // empty')
    work_email=$(echo "$config_json" | jq -r '.git.work.email // empty')
    work_orgs=$(echo "$config_json" | jq -r '.git.work.orgs // empty')

    local bashrc="$HOME/.bashrc"
    [[ -n "$tz" ]] && ! grep -q "^export TZ=" "$bashrc" 2>/dev/null && echo "export TZ=\"$tz\"" >> "$bashrc"
    [[ -n "$locale" ]] && ! grep -q "^export LC_TIME=" "$bashrc" 2>/dev/null && echo "export LC_TIME=\"$locale\"" >> "$bashrc"
    [[ -n "$git_name" ]] && ! grep -q "^export GIT_USER_NAME=" "$bashrc" 2>/dev/null && echo "export GIT_USER_NAME=\"$git_name\"" >> "$bashrc"
    [[ -n "$git_email" ]] && ! grep -q "^export GIT_USER_EMAIL=" "$bashrc" 2>/dev/null && echo "export GIT_USER_EMAIL=\"$git_email\"" >> "$bashrc"
    [[ -n "$work_email" ]] && ! grep -q "^export GIT_USER_EMAIL_WORK=" "$bashrc" 2>/dev/null && echo "export GIT_USER_EMAIL_WORK=\"$work_email\"" >> "$bashrc"
    [[ -n "$work_orgs" ]] && ! grep -q "^export GH_WORK_ORGS=" "$bashrc" 2>/dev/null && echo "export GH_WORK_ORGS=\"$work_orgs\"" >> "$bashrc"

    ok "Environment variables propagated to ~/.bashrc"
}

setup_claude_configuration() {
    print_header "Claude configuration"

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"
    ensure_directory "$CLAUDE_DIR/skills"

    apply_claude_settings
    propagate_env_from_config
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

    if npx -y skills add "$url" --skill "$name" --agent claude-code -g -y < /dev/null 2>/dev/null; then
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

    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        warn "Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    # Clean stale gemini skill symlinks (gemini-cli scans ~/.agents/skills/ directly)
    if [ -d "$HOME/.gemini/skills" ]; then
        find "$HOME/.gemini/skills" -maxdepth 1 -type l -delete 2>/dev/null || true
    fi

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0

    # Plugins (flat array from parser)
    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || {
        warn "Failed to parse plugin config"; return 0
    }

    while IFS= read -r plugin; do
        local name
        name=$(echo "$plugin" | jq -r '.name')
        local rc=0; install_plugin "${name}@${OFFICIAL_MARKETPLACE_NAME}" "$name" || rc=$?
        case $rc in
            0) plugins_installed=$((plugins_installed + 1)) ;;
            1) plugins_skipped=$((plugins_skipped + 1)) ;;
            2) plugins_failed=$((plugins_failed + 1)) ;;
        esac
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Skills
    local skills_json
    skills_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section skills) || {
        warn "Failed to parse skills config"; return 0
    }

    while IFS= read -r skill; do
        local name url
        name=$(echo "$skill" | jq -r '.name')
        url=$(echo "$skill" | jq -r '.url')
        install_skill "$name" "$url" < /dev/null && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
    done < <(echo "$skills_json" | jq -c '.[]')

    echo ""
    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

# =============================================================================
# LOCAL MARKETPLACE PLUGINS
# =============================================================================

install_local_marketplace_plugins() {
    print_header "Installing local plugins"

    local marketplace_dir="$CONFIG_DIR/plugins/$LOCAL_MARKETPLACE_NAME"
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
    _expected_plugins=""

    local plugins_json
    plugins_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section plugins_flat) || return 0

    while IFS= read -r plugin; do
        local name
        name=$(echo "$plugin" | jq -r '.name')
        _expected_plugins="${_expected_plugins}${name}@${OFFICIAL_MARKETPLACE_NAME}"$'\n'
    done < <(echo "$plugins_json" | jq -c '.[]')

    # Local marketplace plugins (auto-discovered, not from YAML)
    local local_manifest="$CONFIG_DIR/plugins/$LOCAL_MARKETPLACE_NAME/.claude-plugin/marketplace.json"
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

# Sync: remove skills not in expected list
sync_skills() {
    print_header "Synchronizing skills"

    local skills_dir="$CLAUDE_DIR/skills"
    [[ -d "$skills_dir" ]] || return 0

    # Build expected skills list from YAML
    local expected=()
    local skills_json
    skills_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section skills 2>/dev/null) || return 0

    while IFS= read -r skill; do
        local name
        name=$(echo "$skill" | jq -r '.name')
        [[ -n "$name" ]] && expected+=("$name")
    done < <(echo "$skills_json" | jq -c '.[]')

    # Compare installed vs expected, remove stale (directories and symlinks)
    local removed=0 failed=0
    for entry in "$skills_dir"/*; do
        [[ -d "$entry" || -L "$entry" ]] || continue
        local name
        name=$(basename "$entry")
        local found=0
        for exp in "${expected[@]}"; do
            [[ "$name" == "$exp" ]] && { found=1; break; }
        done
        if [[ $found -eq 0 ]]; then
            if rm -rf "$entry"; then
                echo "  🗑️  Removed skill: $name"
                removed=$((removed + 1))
            else
                warn "Failed to remove skill: $name"
                failed=$((failed + 1))
            fi
        fi
    done

    if ((removed > 0 || failed > 0)); then
        echo ""
        echo "  📊 Skills sync: $removed removed, $failed failed"
    else
        ok "All skills in sync"
    fi
}

# =============================================================================
# MCP SERVERS
# =============================================================================

add_mcp_server() {
    local name="$1"
    local config="$2"

    if claude mcp list 2>/dev/null | grep -q "$name"; then
        ok "$name already configured"
        return
    fi

    if claude mcp add-json "$name" "$config" --scope user 2>/dev/null; then
        ok "Added: $name"
    else
        warn "Failed to add $name"
    fi
}

parse_mcp_servers() {
    local mcp_json
    mcp_json=$(node "$CONFIG_PARSER" --config "$CONFIG_FILE" --env "$ENVIRONMENT_TAG" --section mcp_servers) || {
        warn "Failed to parse MCP config"; return 0
    }

    while IFS= read -r server; do
        local name type
        name=$(echo "$server" | jq -r '.name')
        type=$(echo "$server" | jq -r '.type')

        local config_json
        if [[ "$type" == "stdio" ]]; then
            config_json=$(echo "$server" | jq '{type, command, args, env}')
        else
            config_json=$(echo "$server" | jq '{type, url, headers}')
        fi

        mcp_expected+=("$name")
        add_mcp_server "$name" "$config_json"
    done < <(echo "$mcp_json" | jq -c '.[]')
}

# Sync MCP servers: add from config, remove stale ones
sync_mcp_servers() {
    print_header "Setting up MCP servers"
    has_command claude || { warn "Claude CLI not found"; return 0; }
    has_command jq || { warn "jq not found"; return 0; }

    local mcp_expected=()
    parse_mcp_servers

    # Get installed MCP servers from .claude.json
    local settings_file="$CLAUDE_DIR/.claude.json"
    local installed=()
    if [[ -f "$settings_file" ]]; then
        while IFS= read -r name; do
            [[ -n "$name" ]] && installed+=("$name")
        done < <(jq -r '.mcpServers // {} | keys[]' "$settings_file" 2>/dev/null)
    fi

    # Remove servers not in expected list
    local removed=0
    for name in "${installed[@]}"; do
        local found=0
        for expected in "${mcp_expected[@]}"; do
            [[ "$name" == "$expected" ]] && { found=1; break; }
        done
        if [[ $found -eq 0 ]]; then
            if claude mcp remove "$name" --scope user < /dev/null 2>/dev/null; then
                echo "  🗑️  Removed MCP: $name"
                removed=$((removed + 1))
            fi
        fi
    done

    echo ""
    echo "  📊 MCP: ${#mcp_expected[@]} configured, $removed removed"
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
    install_loop
    setup_claude_configuration
    sync_plugins
    sync_skills
    install_all_plugins_and_skills
    install_local_marketplace_plugins
    sync_mcp_servers
}

main "$@"
