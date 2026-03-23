#!/bin/bash
# Tests for .devcontainer/backup.sh
# Run: bash src/scripts/tests/test_backup.sh

set -euo pipefail

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

RED='\033[31m'
GREEN='\033[32m'
RESET='\033[0m'

pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "  ${GREEN}✓${RESET} $1"
}

fail_test() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "  ${RED}✗${RESET} $1: $2"
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$expected" == "$actual" ]]; then pass "$msg"
    else fail_test "$msg" "expected '$expected', got '$actual'"; fi
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$haystack" == *"$needle"* ]]; then pass "$msg"
    else fail_test "$msg" "expected to contain '$needle'"; fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BACKUP_SCRIPT="$REPO_ROOT/.devcontainer/backup.sh"

# Temp dir for all tests
TEST_DIR=""
setup() {
    TEST_DIR="$(mktemp -d)"
    export BACKUP_DIR="$TEST_DIR/backups"
    # Use full paths inside TEST_DIR to simulate real volume paths
    mkdir -p "$TEST_DIR/home/vscode/.claude" "$TEST_DIR/home/vscode/.gemini"
    echo "secret-token-1" > "$TEST_DIR/home/vscode/.claude/token.json"
    echo "secret-token-2" > "$TEST_DIR/home/vscode/.gemini/config.yaml"
    export BACKUP_SOURCE_PATHS="$TEST_DIR/home/vscode/.claude $TEST_DIR/home/vscode/.gemini"
}

teardown() {
    [[ -n "$TEST_DIR" ]] && rm -rf "$TEST_DIR"
    unset BACKUP_DIR BACKUP_SOURCE_PATHS BACKUP_PIN BACKUP_RESTORE_ROOT 2>/dev/null || true
}

# ── Usage tests ──────────────────────────────────────────

echo "=== Usage tests ==="

TESTS_RUN=$((TESTS_RUN + 1))
output=$(bash "$BACKUP_SCRIPT" unknown 2>&1 || true)
if [[ "$output" == *"Usage:"* ]]; then pass "unknown subcommand shows usage"
else fail_test "unknown subcommand shows usage" "got: $output"; fi

TESTS_RUN=$((TESTS_RUN + 1))
bash "$BACKUP_SCRIPT" unknown >/dev/null 2>&1 && {
    fail_test "unknown subcommand exits with code 1" "got exit 0"
} || {
    pass "unknown subcommand exits with code 1"
}

TESTS_RUN=$((TESTS_RUN + 1))
output=$(bash "$BACKUP_SCRIPT" 2>&1 || true)
if [[ "$output" == *"Usage:"* ]]; then pass "no arguments shows usage"
else fail_test "no arguments shows usage" "got: $output"; fi

# ── Summary ──────────────────────────────────────────────

echo ""
echo "Results: $TESTS_PASSED/$TESTS_RUN passed, $TESTS_FAILED failed"
if [[ "$TESTS_FAILED" -gt 0 ]]; then exit 1; fi
