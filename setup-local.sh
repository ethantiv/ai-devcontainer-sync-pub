#!/bin/bash

# macOS local setup: Install Claude Code configuration identical to DevContainer
# This script installs plugins, skills, commands, and settings on local macOS machine

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

# =============================================================================
# REQUIREMENTS CHECK
# =============================================================================

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        echo "❌ This script is designed for macOS only"
        exit 1
    fi
    echo "✅ Running on macOS $(sw_vers -productVersion)"
}

check_requirements() {
    print_header "Checking requirements"

    local missing=()

    check_macos

    if ! has_command jq; then
        missing+=("jq")
        echo "❌ jq not found"
    else
        echo "✅ jq $(jq --version 2>/dev/null | head -1)"
    fi

    if ! has_command node; then
        missing+=("node")
        echo "❌ node not found"
    else
        echo "✅ node $(node --version)"
    fi

    if ! has_command npm; then
        missing+=("npm")
        echo "❌ npm not found"
    else
        echo "✅ npm $(npm --version 2>/dev/null)"
    fi

    if ! has_command npx; then
        missing+=("npx")
        echo "❌ npx not found"
    else
        echo "✅ npx available"
    fi

    if ! has_command uvx; then
        missing+=("uvx")
        echo "❌ uvx not found (required for MCP servers)"
    else
        echo "✅ uvx available"
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        echo "⚠️  Missing dependencies. Install them with:"
        echo ""
        for dep in "${missing[@]}"; do
            case "$dep" in
                jq) echo "  brew install jq" ;;
                node|npm|npx) echo "  brew install node" ;;
                uvx) echo "  brew install uv  # or: pipx install uv" ;;
            esac
        done
        echo ""
        echo "After installing, re-run this script."
        exit 1
    fi

    echo "✅ All requirements satisfied"
}

# =============================================================================
# CLAUDE CLI INSTALLATION
# =============================================================================

install_claude_cli() {
    print_header "Claude CLI"

    if has_command claude; then
        echo "✅ Claude CLI already installed: $(claude --version 2>/dev/null | head -1)"
        return 0
    fi

    echo "📥 Installing Claude CLI..."
    if curl -fsSL https://claude.ai/install.sh | bash; then
        # Source updated PATH
        export PATH="$HOME/.claude/bin:$PATH"
        if has_command claude; then
            echo "✅ Claude CLI installed successfully"
            return 0
        fi
    fi

    echo "❌ Failed to install Claude CLI"
    echo "   Try manual installation: https://claude.ai/install"
    exit 1
}

# =============================================================================
# PLAYWRIGHT INSTALLATION
# =============================================================================

install_playwright() {
    print_header "Playwright + Chromium"

    if npm ls -g @playwright/mcp &>/dev/null; then
        echo "✅ @playwright/mcp already installed"
    else
        echo "📥 Installing @playwright/mcp..."
        npm install -g @playwright/mcp
        echo "✅ @playwright/mcp installed"
    fi

    if npx playwright install chromium; then
        echo "✅ Chromium installed"
    else
        echo "⚠️  Failed to install Chromium"
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
        echo "  ✅ Settings merged with existing"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
        echo "  ✅ Settings created"
    fi
}

copy_claude_memory() {
    local source_file="$DEVCONTAINER_DIR/configuration/CLAUDE.md.memory"
    if [[ -f "$source_file" ]]; then
        cp "$source_file" "$CLAUDE_DIR/CLAUDE.md"
        echo "  ✅ CLAUDE.md synced"
    else
        echo "  ⚠️  CLAUDE.md.memory not found"
    fi
}

sync_claude_files() {
    local source_dir="$DEVCONTAINER_DIR/$1"
    local target_dir="$CLAUDE_DIR/$1"
    local extension="${2:-.md}"

    [[ -d "$source_dir" ]] || return 0

    # Remove files that no longer exist in source
    if [[ -d "$target_dir" ]]; then
        for file in "$target_dir"/*"$extension"; do
            [[ -f "$file" ]] || continue
            [[ -f "$source_dir/$(basename "$file")" ]] || rm -f "$file"
        done 2>/dev/null
    fi

    # Copy all source files
    local files=("$source_dir"/*"$extension")
    if [[ -e "${files[0]}" ]]; then
        cp "$source_dir"/*"$extension" "$target_dir/"
        echo "  ✅ Synced ${#files[@]} $1"
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
        echo "  ✅ Synced $count scripts to ~/.claude/scripts/"
    fi
}

setup_claude_configuration() {
    print_header "Claude configuration"

    ensure_directory "$CLAUDE_DIR"
    ensure_directory "$CLAUDE_DIR/tmp"
    ensure_directory "$CLAUDE_DIR/commands"
    ensure_directory "$CLAUDE_DIR/agents"
    ensure_directory "$CLAUDE_DIR/skills"

    apply_claude_settings
    copy_claude_memory
    sync_claude_files "commands" ".md"
    sync_claude_files "agents" ".md"
    sync_claude_scripts
}

# =============================================================================
# CLAUDE PLUGINS
# =============================================================================

# Install a Claude plugin. Returns: 0=installed, 1=already present, 2=failed
install_plugin() {
    local plugin="$1"
    local display_name="${2:-$plugin}"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]] && jq -e --arg p "$plugin" '.enabledPlugins[$p]' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
        return 1
    fi

    if claude plugin install "$plugin" --scope user < /dev/null 2>/dev/null; then
        echo "  ✅ Installed: $display_name"
        return 0
    fi
    echo "  ⚠️  Failed: $display_name"
    return 2
}

# Update counters based on install_plugin return code
update_plugin_counters() {
    local rc="$1"
    local -n _installed="$2"
    local -n _skipped="$3"
    local -n _failed="$4"

    case $rc in
        0) ((_installed++)) || true ;;
        1) ((_skipped++)) || true ;;
        2) ((_failed++)) || true ;;
    esac
}

ensure_marketplace() {
    local name="$1"
    local source="$2"

    if claude plugin marketplace list 2>/dev/null | grep -q "$name"; then
        return 0
    fi

    if claude plugin marketplace add "$source" 2>/dev/null; then
        echo "  ✅ Added marketplace: $name"
        return 0
    fi
    echo "  ⚠️  Failed to add marketplace: $name"
    return 1
}

# =============================================================================
# SKILL INSTALLATION HELPERS
# =============================================================================

# Install skill from Vercel skills repo using add-skill CLI
install_vercel_skill() {
    local name="$1"
    local repo="$2"

    has_command npx || return 1
    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y add-skill -g -y "$repo" -a claude-code -s "$name" < /dev/null 2>/dev/null; then
        echo "  ✅ Installed skill: $name"
        return 0
    fi
    echo "  ⚠️  Failed to install skill: $name"
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
        echo "  ✅ Installed skill: $name"
        return 0
    fi
    echo "  ⚠️  Failed to install skill: $name"
    return 1
}

# =============================================================================
# PLUGINS AND SKILLS INSTALLATION
# =============================================================================

install_all_plugins_and_skills() {
    print_header "Installing plugins and skills"

    local plugins_file="$DEVCONTAINER_DIR/$CLAUDE_PLUGINS_FILE"

    [[ -f "$plugins_file" ]] || { echo "  ⚠️  $plugins_file not found"; return 0; }

    if ! ensure_marketplace "$OFFICIAL_MARKETPLACE_NAME" "$OFFICIAL_MARKETPLACE_REPO"; then
        echo "  ⚠️  Skipping official marketplace plugins"
        return 0
    fi
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE_NAME" 2>/dev/null || true

    local plugins_installed=0 plugins_skipped=0 plugins_failed=0
    local skills_installed=0 skills_failed=0
    declare -A external_marketplaces

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
                    if [[ -z "${external_marketplaces[$type]}" ]]; then
                        ensure_marketplace "$type" "$source" || continue
                        claude plugin marketplace update "$type" 2>/dev/null || true
                        external_marketplaces[$type]=1
                    fi
                    local rc=0; install_plugin "${name}@${type}" "$name" || rc=$?
                    update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
                    ;;
                vercel-skills)
                    install_vercel_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                github)
                    install_github_skill "$name" "$source" && skills_installed=$((skills_installed + 1)) || skills_failed=$((skills_failed + 1))
                    ;;
                *)
                    echo "  ⚠️  Unknown source type: $type for $name"
                    ;;
            esac
        else
            local rc=0; install_plugin "${line}@${OFFICIAL_MARKETPLACE_NAME}" "$line" || rc=$?
            update_plugin_counters $rc plugins_installed plugins_skipped plugins_failed
        fi
    done < "$plugins_file"

    echo ""
    echo "  📊 Plugins: $plugins_installed installed, $plugins_skipped present, $plugins_failed failed"
    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
}

# =============================================================================
# FINAL REPORT
# =============================================================================

print_final_report() {
    print_header "Setup complete!"

    echo ""
    echo "Installed configuration:"
    echo ""

    echo "📁 Files:"
    echo "   ~/.claude/settings.json"
    echo "   ~/.claude/CLAUDE.md"

    if [[ -d "$CLAUDE_DIR/commands" ]]; then
        local cmd_count=$(find "$CLAUDE_DIR/commands" -name "*.md" 2>/dev/null | wc -l | xargs)
        echo "   ~/.claude/commands/ ($cmd_count commands)"
    fi

    if [[ -d "$CLAUDE_DIR/scripts" ]]; then
        local script_count=$(find "$CLAUDE_DIR/scripts" -name "*.sh" 2>/dev/null | wc -l | xargs)
        echo "   ~/.claude/scripts/ ($script_count scripts)"
    fi

    if [[ -d "$CLAUDE_DIR/skills" ]]; then
        local skill_count=$(find "$CLAUDE_DIR/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | xargs)
        echo "   ~/.claude/skills/ ($skill_count skills)"
    fi

    echo ""
    echo "🎭 Playwright:"
    echo "   @playwright/mcp (global npm package)"
    echo "   Chromium browser"

    echo ""
    echo "🔍 Verification commands:"
    echo "   claude mcp list                    # Check MCP servers"
    echo "   claude plugin marketplace list     # Check marketplaces"
    echo "   ls ~/.claude/commands/             # List custom commands"
    echo "   ls ~/.claude/skills/               # List installed skills"
    echo ""
    echo "💡 Note: MCP servers are NOT installed by this script."
    echo "   Configure them manually via: claude mcp add-json <name> '<config>'"
    echo ""
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
    setup_claude_configuration
    install_all_plugins_and_skills
    print_final_report
}

main "$@"
