#!/usr/bin/env bash
# ensure-playwright.sh — Idempotent Playwright Chromium installer for lazy first-use.
# Checks if Chromium is already present at $PLAYWRIGHT_BROWSERS_PATH;
# if not, installs system deps and Chromium via npx playwright.
# Designed to run as a PreToolUse hook before agent-browser invocations.
set -euo pipefail

BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

# Check if Chromium is already installed by looking for any chromium-* directory
# with the actual browser binary inside.
chromium_ready() {
    local chrome_bin
    for dir in "$BROWSERS_PATH"/chromium-*/; do
        chrome_bin="$dir/chrome-linux/chrome"
        [ -x "$chrome_bin" ] && return 0
        # ARM64 uses a different path
        chrome_bin="$dir/chrome-linux/headless_shell"
        [ -x "$chrome_bin" ] && return 0
    done
    return 1
}

if chromium_ready; then
    exit 0
fi

echo "[ensure-playwright] Chromium not found at $BROWSERS_PATH — installing..."

# System dependencies required by Chromium (same list previously in Dockerfile).
# Only install if apt-get is available (Docker/Linux environment).
PLAYWRIGHT_DEPS=(
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1
    libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0
)

if command -v apt-get &>/dev/null; then
    # Check if deps are already present (avoid sudo if unnecessary)
    missing=()
    for pkg in "${PLAYWRIGHT_DEPS[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "[ensure-playwright] Installing ${#missing[@]} system dependencies..."
        sudo apt-get update -qq
        sudo apt-get install -y --no-install-recommends "${missing[@]}"
        sudo rm -rf /var/lib/apt/lists/* 2>/dev/null || true
    fi
fi

# Install Chromium browser via Playwright
echo "[ensure-playwright] Installing Chromium via Playwright..."
mkdir -p "$BROWSERS_PATH"
npx -y playwright install chromium

echo "[ensure-playwright] Chromium installed successfully."
