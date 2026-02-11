#!/usr/bin/env bash
# pre-tool-check-playwright.sh — PreToolUse hook for Bash tool.
# Reads tool input from stdin, checks if the command involves agent-browser,
# and runs ensure-playwright.sh if Chromium is not yet installed.
# Exits 0 quickly for non-browser commands (no overhead).
set -euo pipefail

# Read hook input from stdin
input=$(cat)

# Extract the command being run
command=$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

# Only act on agent-browser commands
case "$command" in
    *agent-browser*) ;;
    *) exit 0 ;;
esac

# Locate ensure-playwright.sh: Docker path first, then project-local
SCRIPT="/opt/loop/scripts/ensure-playwright.sh"
if [ ! -f "$SCRIPT" ]; then
    SCRIPT="${CLAUDE_PROJECT_DIR:-}/src/scripts/ensure-playwright.sh"
fi
if [ ! -f "$SCRIPT" ]; then
    # Script not found — don't block the command
    exit 0
fi

exec bash "$SCRIPT"
