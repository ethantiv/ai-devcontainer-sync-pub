#!/bin/bash
# Claude Code setup script for RPi5 container
# Installs plugins, skills, and MCP servers

set -e

readonly CLAUDE_DIR="$HOME/.claude"
readonly CLAUDE_SETTINGS_FILE="$CLAUDE_DIR/settings.json"
readonly OFFICIAL_MARKETPLACE="claude-plugins-official"
readonly OFFICIAL_MARKETPLACE_REPO="anthropics/claude-plugins-official"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

ensure_directory() {
    [[ -d "$1" ]] || mkdir -p "$1"
}

has_command() {
    command -v "$1" &>/dev/null
}

ok()   { echo -e "  \033[32m✔︎\033[0m $1"; }
warn() { echo -e "  \033[33m⚠️\033[0m  $1"; }
fail() { echo -e "  \033[31m❌\033[0m $1"; }

setup_github_token() {
    if [[ -n "${GH_TOKEN}" ]]; then
        echo "export GH_TOKEN='${GH_TOKEN}'" >> ~/.bashrc
        ok "GitHub token exported to ~/.bashrc"
    fi
}

# Install a Claude plugin (returns: 0=installed, 1=already present, 2=failed)
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
# CLAUDE SETTINGS
# =============================================================================

apply_claude_settings() {
    echo "📄 Applying Claude settings..."

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

    ensure_directory "$CLAUDE_DIR"

    if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
        local merged
        merged=$(jq -s '.[0] * .[1]' <(echo "$default_settings") "$CLAUDE_SETTINGS_FILE" 2>/dev/null)
        [[ -n "$merged" ]] && echo "$merged" > "$CLAUDE_SETTINGS_FILE"
    else
        echo "$default_settings" | jq '.' > "$CLAUDE_SETTINGS_FILE"
    fi
    ok "Settings configured"
}

# =============================================================================
# PLUGINS INSTALLATION
# =============================================================================

install_official_plugins() {
    echo "📦 Installing official plugins..."

    ensure_marketplace "$OFFICIAL_MARKETPLACE" "$OFFICIAL_MARKETPLACE_REPO" || return
    claude plugin marketplace update "$OFFICIAL_MARKETPLACE" 2>/dev/null || true

    local plugins=(
        "agent-sdk-dev"
        "claude-code-setup"
        "code-simplifier"
        "commit-commands"
        "feature-dev"
        "frontend-design"
        "pyright-lsp"
        "typescript-lsp"
    )

    local installed=0 skipped=0 failed=0

    for plugin in "${plugins[@]}"; do
        local rc=0
        install_plugin "${plugin}@${OFFICIAL_MARKETPLACE}" "$plugin" || rc=$?
        case $rc in
            0) ((installed++)) || true ;;
            1) ((skipped++)) || true ;;
            2) ((failed++)) || true ;;
        esac
    done

    echo "  📊 Official: $installed installed, $skipped present, $failed failed"
}

# =============================================================================
# SKILLS INSTALLATION
# =============================================================================

install_skill() {
    local name="$1"
    local repo="$2"

    ensure_directory "$CLAUDE_DIR/skills"

    if npx -y skills add "https://github.com/$repo" --skill "$name" -g -y < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

install_github_skill() {
    local name="$1"
    local url="$2"

    local skill_dir="$CLAUDE_DIR/skills/$name"
    ensure_directory "$skill_dir"

    if curl -fsSL -o "$skill_dir/SKILL.md" "$url" < /dev/null 2>/dev/null; then
        ok "Installed skill: $name"
        return 0
    fi
    warn "Failed to install skill: $name"
    return 1
}

install_skills() {
    echo "📦 Installing skills..."

    local skills_installed=0 skills_failed=0

    local vercel_repo="vercel-labs/agent-skills"
    for skill in "vercel-react-best-practices" "web-design-guidelines"; do
        install_skill "$skill" "$vercel_repo" && ((skills_installed++)) || ((skills_failed++))
    done

    install_skill "agent-browser" "vercel-labs/agent-browser" && ((skills_installed++)) || ((skills_failed++))

    # Playwright CLI
    install_skill "playwright-cli" "microsoft/playwright" && ((skills_installed++)) || ((skills_failed++))

    echo "  📊 Skills: $skills_installed installed, $skills_failed failed"
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

setup_mcp_servers() {
    echo "🔧 Setting up MCP servers..."

    add_mcp_server "aws-documentation" '{
        "type": "stdio",
        "command": "uvx",
        "args": ["awslabs.aws-documentation-mcp-server@latest"],
        "env": {
            "FASTMCP_LOG_LEVEL": "ERROR",
            "AWS_DOCUMENTATION_PARTITION": "aws"
        }
    }'

    add_mcp_server "terraform" '{
        "type": "stdio",
        "command": "uvx",
        "args": ["awslabs.terraform-mcp-server@latest"],
        "env": {
            "FASTMCP_LOG_LEVEL": "ERROR"
        }
    }'

    add_mcp_server "context7" '{
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "env": {
            "CONTEXT7_API_KEY": "'"${CONTEXT7_API_KEY:-}"'"
        }
    }'
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "🚀 Setting up Claude Code..."

    has_command claude || { fail "Claude CLI not found"; exit 1; }
    has_command jq || { fail "jq not found"; exit 1; }

    ensure_directory "$CLAUDE_DIR/tmp"
    export TMPDIR="$CLAUDE_DIR/tmp"

    setup_github_token
    apply_claude_settings
    install_official_plugins
    install_skills
    setup_mcp_servers

    echo ""
    ok "Claude Code setup complete!"
    echo ""
    echo "Verify with:"
    echo "  claude mcp list"
    echo "  claude plugin marketplace list"
}

main "$@"
