#!/bin/bash
# Tests for ensure-playwright.sh and pre-tool-check-playwright.sh
# Run: bash src/scripts/tests/test_ensure_playwright.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENSURE_SH="$SCRIPT_DIR/../ensure-playwright.sh"
PRE_TOOL_SH="$SCRIPT_DIR/../pre-tool-check-playwright.sh"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Colors
RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "  ${GREEN}✓${RESET} $1"
}

fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "  ${RED}✗${RESET} $1: $2"
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$expected" == "$actual" ]]; then
        pass "$msg"
    else
        fail "$msg" "expected '$expected', got '$actual'"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$msg"
    else
        fail "$msg" "expected to contain '$needle' in '$haystack'"
    fi
}

assert_exit_code() {
    local expected="$1" actual="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$expected" -eq "$actual" ]]; then
        pass "$msg"
    else
        fail "$msg" "expected exit code $expected, got $actual"
    fi
}

# Create isolated test environment
setup() {
    TEST_DIR=$(mktemp -d)
    ORIG_PATH="$PATH"
    # Create a fake PLAYWRIGHT_BROWSERS_PATH
    export PLAYWRIGHT_BROWSERS_PATH="$TEST_DIR/browsers"
    mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
}

teardown() {
    export PATH="$ORIG_PATH"
    unset PLAYWRIGHT_BROWSERS_PATH
    cd /
    rm -rf "$TEST_DIR"
}

# ============================================================
# Tests for ensure-playwright.sh — chromium_ready detection
# ============================================================

echo "ensure-playwright.sh — exits 0 when Chromium is already present"

setup
# Simulate installed Chromium: create browser binary
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"

exit_code=0
bash "$ENSURE_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 when chrome binary exists"
teardown

setup
# Simulate ARM64 headless_shell path
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-5678/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-5678/chrome-linux/headless_shell"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-5678/chrome-linux/headless_shell"

exit_code=0
bash "$ENSURE_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 when headless_shell binary exists"
teardown

# ============================================================
# Tests for ensure-playwright.sh — triggers install when absent
# ============================================================

echo ""
echo "ensure-playwright.sh — attempts install when Chromium absent"

setup
# Mock npx to verify it gets called, and apt-get/dpkg to avoid system changes
mkdir -p "$TEST_DIR/bin"

# Use unquoted heredoc so $TEST_DIR and $PLAYWRIGHT_BROWSERS_PATH are expanded at creation time
cat > "$TEST_DIR/bin/npx" << MOCKEOF
#!/bin/bash
# Record that npx was called
echo "npx called: \$*" >> "$TEST_DIR/npx_calls.log"
# Simulate successful Chromium install by creating the binary
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/npx"

cat > "$TEST_DIR/bin/dpkg" << MOCKEOF
#!/bin/bash
# Simulate all packages as already installed
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/dpkg"

export PATH="$TEST_DIR/bin:$PATH"

exit_code=0
output=$(bash "$ENSURE_SH" 2>&1) || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 after successful install"
assert_contains "$output" "installing" "outputs install message (case-insensitive)"

TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$TEST_DIR/npx_calls.log" ]]; then
    npx_cmd=$(cat "$TEST_DIR/npx_calls.log")
    if [[ "$npx_cmd" == *"playwright install chromium"* ]]; then
        pass "calls npx playwright install chromium"
    else
        fail "calls npx playwright install chromium" "got: $npx_cmd"
    fi
else
    fail "calls npx playwright install chromium" "npx was never called"
fi
teardown

# ============================================================
# Tests for ensure-playwright.sh — system deps check
# ============================================================

echo ""
echo "ensure-playwright.sh — system dependency checking"

setup
mkdir -p "$TEST_DIR/bin"

# Mock dpkg to report a package as missing (unquoted heredoc for variable expansion)
cat > "$TEST_DIR/bin/dpkg" << MOCKEOF
#!/bin/bash
if [[ "\$2" == "libnss3" ]]; then
    exit 1  # missing
fi
exit 0  # others installed
MOCKEOF
chmod +x "$TEST_DIR/bin/dpkg"

# Mock apt-get to record calls
cat > "$TEST_DIR/bin/apt-get" << MOCKEOF
#!/bin/bash
echo "apt-get \$*" >> "$TEST_DIR/apt_calls.log"
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/apt-get"

# Mock sudo to pass through
cat > "$TEST_DIR/bin/sudo" << MOCKEOF
#!/bin/bash
"\$@"
MOCKEOF
chmod +x "$TEST_DIR/bin/sudo"

# Mock npx to simulate install
cat > "$TEST_DIR/bin/npx" << MOCKEOF
#!/bin/bash
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/npx"

export PATH="$TEST_DIR/bin:$PATH"

bash "$ENSURE_SH" >/dev/null 2>&1
TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$TEST_DIR/apt_calls.log" ]] && grep -q "install" "$TEST_DIR/apt_calls.log"; then
    pass "runs apt-get install when dependencies are missing"
else
    fail "runs apt-get install when dependencies are missing" "apt-get install was not called"
fi
teardown

setup
mkdir -p "$TEST_DIR/bin"

# Mock dpkg to report all packages as installed
cat > "$TEST_DIR/bin/dpkg" << MOCKEOF
#!/bin/bash
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/dpkg"

# Mock apt-get to record calls
cat > "$TEST_DIR/bin/apt-get" << MOCKEOF
#!/bin/bash
echo "apt-get \$*" >> "$TEST_DIR/apt_calls.log"
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/apt-get"

# Mock sudo
cat > "$TEST_DIR/bin/sudo" << MOCKEOF
#!/bin/bash
"\$@"
MOCKEOF
chmod +x "$TEST_DIR/bin/sudo"

# Mock npx
cat > "$TEST_DIR/bin/npx" << MOCKEOF
#!/bin/bash
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-9999/chrome-linux/chrome"
exit 0
MOCKEOF
chmod +x "$TEST_DIR/bin/npx"

export PATH="$TEST_DIR/bin:$PATH"

bash "$ENSURE_SH" >/dev/null 2>&1
TESTS_RUN=$((TESTS_RUN + 1))
if [[ ! -f "$TEST_DIR/apt_calls.log" ]] || ! grep -q "install" "$TEST_DIR/apt_calls.log"; then
    pass "skips apt-get install when all dependencies are present"
else
    fail "skips apt-get install when all dependencies are present" "apt-get install was called"
fi
teardown

# ============================================================
# Tests for pre-tool-check-playwright.sh — routing logic
# ============================================================

echo ""
echo "pre-tool-check-playwright.sh — command routing"

setup
# Non-browser command should exit 0 immediately without calling ensure
exit_code=0
echo '{"tool_input":{"command":"ls -la"}}' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 for non-browser commands"
teardown

setup
exit_code=0
echo '{"tool_input":{"command":"npm test"}}' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 for npm test command"
teardown

setup
# Simulate already-installed chromium so ensure-playwright.sh exits 0
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"

# Set CLAUDE_PROJECT_DIR so pre-tool can find the script
export CLAUDE_PROJECT_DIR="$SCRIPT_DIR/../../.."

exit_code=0
echo '{"tool_input":{"command":"agent-browser open https://example.com"}}' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "exits 0 for agent-browser command when chromium present"
teardown

setup
# Pre-tool script needs to find ensure-playwright.sh via CLAUDE_PROJECT_DIR
export CLAUDE_PROJECT_DIR="$SCRIPT_DIR/../../.."
# Simulate chromium already present so ensure-playwright.sh exits 0
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux"
touch "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"
chmod +x "$PLAYWRIGHT_BROWSERS_PATH/chromium-1234/chrome-linux/chrome"

exit_code=0
echo '{"tool_input":{"command":"agent-browser snapshot -i"}}' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "handles agent-browser snapshot command"
teardown

# ============================================================
# Tests for pre-tool-check-playwright.sh — malformed input
# ============================================================

echo ""
echo "pre-tool-check-playwright.sh — malformed input handling"

setup
exit_code=0
echo '' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "handles empty stdin gracefully"
teardown

setup
exit_code=0
echo 'not valid json' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "handles invalid JSON gracefully"
teardown

setup
exit_code=0
echo '{}' | bash "$PRE_TOOL_SH" >/dev/null 2>&1 || exit_code=$?
assert_exit_code 0 "$exit_code" "handles missing tool_input gracefully"
teardown

# ============================================================
# Summary
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: $TESTS_RUN | Passed: $TESTS_PASSED | Failed: $TESTS_FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $TESTS_FAILED -eq 0 ]] && exit 0 || exit 1
