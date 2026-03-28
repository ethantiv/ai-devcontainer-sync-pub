#!/usr/bin/env bash
# ensure-playwright.sh — Idempotent Playwright Chromium installer for lazy first-use.
# Checks if Chromium is already present at $PLAYWRIGHT_BROWSERS_PATH;
# if not, installs system deps and Chromium via npx playwright.
# Designed to run as a PreToolUse hook before agent-browser invocations.
set -euo pipefail

# Fast exit: if AGENT_BROWSER_EXECUTABLE_PATH already points to a valid binary, nothing to do.
if [ -n "${AGENT_BROWSER_EXECUTABLE_PATH:-}" ] && [ -x "$AGENT_BROWSER_EXECUTABLE_PATH" ]; then
    exit 0
fi

BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

# Check if Chromium is already installed by looking for any chromium-* directory
# with the actual browser binary inside (chrome on x86_64, headless_shell on ARM64).
chromium_ready() {
    for dir in "$BROWSERS_PATH"/chromium-*/; do
        for bin in chrome headless_shell; do
            [ -x "$dir/chrome-linux/$bin" ] && return 0
        done
    done
    return 1
}

if chromium_ready; then
    exit 0
fi

# On ARM64 Linux, Playwright and Chrome for Testing lack prebuilt binaries.
# Fall back to system chromium package and point agent-browser at it.
ARCH="$(uname -m)"

# Find system chromium binary from known paths.
find_system_chromium() {
    for candidate in /usr/bin/chromium /usr/bin/chromium-browser; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    echo "[ensure-playwright] ARM64 detected — using system chromium package..."

    CHROMIUM_BIN="$(find_system_chromium || true)"

    # Install if not present
    if [ -z "$CHROMIUM_BIN" ] && command -v apt-get &>/dev/null; then
        echo "[ensure-playwright] Installing chromium via apt..."
        sudo apt-get update -qq
        sudo apt-get install -y --no-install-recommends chromium
        sudo rm -rf /var/lib/apt/lists/* 2>/dev/null || true
        CHROMIUM_BIN="$(find_system_chromium || true)"
    fi

    if [ -z "$CHROMIUM_BIN" ]; then
        echo "[ensure-playwright] ERROR: Could not find or install chromium on ARM64."
        exit 1
    fi

    # Persist for agent-browser (current session + future shells)
    export AGENT_BROWSER_EXECUTABLE_PATH="$CHROMIUM_BIN"
    BASHRC="$HOME/.bashrc"
    if ! grep -q 'AGENT_BROWSER_EXECUTABLE_PATH' "$BASHRC" 2>/dev/null; then
        echo "export AGENT_BROWSER_EXECUTABLE_PATH=\"$CHROMIUM_BIN\"" >> "$BASHRC"
    fi

    echo "[ensure-playwright] Using system chromium: $CHROMIUM_BIN"
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
