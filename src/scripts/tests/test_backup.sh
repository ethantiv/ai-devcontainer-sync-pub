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

# ── Create tests ─────────────────────────────────────────

echo ""
echo "=== Create tests ==="

# create fails without BACKUP_PIN (unset)
setup
unset BACKUP_PIN 2>/dev/null || true
output=$(bash "$BACKUP_SCRIPT" create 2>&1 || true)
assert_contains "$output" "BACKUP_PIN" "create fails without BACKUP_PIN"
teardown

# create fails with empty BACKUP_PIN
setup
export BACKUP_PIN=""
output=$(bash "$BACKUP_SCRIPT" create 2>&1 || true)
assert_contains "$output" "BACKUP_PIN" "create fails with empty BACKUP_PIN"
teardown

# create succeeds with valid PIN
setup
export BACKUP_PIN="testpin123"
exit_code=0
output=$(bash "$BACKUP_SCRIPT" create 2>&1) || exit_code=$?
TESTS_RUN=$((TESTS_RUN + 1))
if [[ $exit_code -eq 0 ]]; then pass "create succeeds with valid PIN"
else fail_test "create succeeds with valid PIN" "exit code: $exit_code, output: $output"; fi
teardown

# create produces .tar.gz.gpg file
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
gpg_files=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" 2>/dev/null | wc -l)
assert_eq "1" "$(echo "$gpg_files" | tr -d ' ')" "create produces exactly one .tar.gz.gpg file"
teardown

# create does not leave unencrypted .tar.gz
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
tar_files=$(find "$BACKUP_DIR" -name "*.tar.gz" ! -name "*.gpg" 2>/dev/null | wc -l)
assert_eq "0" "$(echo "$tar_files" | tr -d ' ')" "create does not leave unencrypted .tar.gz"
teardown

# create skips missing source folder with warning
setup
export BACKUP_PIN="testpin123"
rm -rf "$TEST_DIR/home/vscode/.gemini"
TESTS_RUN=$((TESTS_RUN + 1))
exit_code=0
output=$(bash "$BACKUP_SCRIPT" create 2>&1) || exit_code=$?
if [[ "$output" == *"⚠"* && $exit_code -eq 0 ]]; then pass "create warns on missing folder but succeeds"
else fail_test "create warns on missing folder but succeeds" "exit=$exit_code, output: $output"; fi
teardown

# create fails when ALL source folders are missing
setup
export BACKUP_PIN="testpin123"
rm -rf "$TEST_DIR/home"
output=$(bash "$BACKUP_SCRIPT" create 2>&1 || true)
assert_contains "$output" "No source folders" "create fails when all source folders missing"
teardown

# backup content is valid (decrypt + extract with full paths)
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
gpg_file=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" | head -1)
extract_dir="$TEST_DIR/extracted"
mkdir -p "$extract_dir"
gpg --batch --yes --passphrase "$BACKUP_PIN" --decrypt "$gpg_file" 2>/dev/null | tar xzf - -C "$extract_dir"
TESTS_RUN=$((TESTS_RUN + 1))
# Archive stores full paths (tar strips leading /), so extracted structure mirrors the original
if [[ -f "$extract_dir/$TEST_DIR/home/vscode/.claude/token.json" ]]; then pass "backup contains correct file content"
else fail_test "backup contains correct file content" "file not found in extracted archive"; fi
teardown

# create prunes old backups keeping max BACKUP_MAX_KEEP
setup
export BACKUP_PIN="testpin123"
export BACKUP_MAX_KEEP=2
for i in 1 2 3; do
    bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
    sleep 1
done
gpg_count=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" | wc -l)
assert_eq "2" "$(echo "$gpg_count" | tr -d ' ')" "create prunes old backups keeping max BACKUP_MAX_KEEP"
teardown

# ── Restore tests ────────────────────────────────────────

echo ""
echo "=== Restore tests ==="

# restore without file fails when no backups exist
setup
export BACKUP_PIN="testpin123"
output=$(bash "$BACKUP_SCRIPT" restore --force 2>&1 || true)
assert_contains "$output" "No backup files" "restore without file fails when no backups exist"
teardown

# restore without file uses latest backup
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
rm -rf "$TEST_DIR/home/vscode/.claude" "$TEST_DIR/home/vscode/.gemini"
export BACKUP_RESTORE_ROOT="$TEST_DIR"
exit_code=0
output=$(bash "$BACKUP_SCRIPT" restore --force 2>&1) || exit_code=$?
TESTS_RUN=$((TESTS_RUN + 1))
if [[ $exit_code -eq 0 && "$output" == *"Using latest"* ]]; then pass "restore without file uses latest backup"
else fail_test "restore without file uses latest backup" "exit=$exit_code, output: $output"; fi
teardown

# restore fails with nonexistent file
setup
export BACKUP_PIN="testpin123"
output=$(bash "$BACKUP_SCRIPT" restore /tmp/nonexistent.gpg 2>&1 || true)
assert_contains "$output" "not found" "restore fails with nonexistent file"
teardown

# restore fails without --force in non-interactive mode
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
gpg_file=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" | head -1)
output=$(bash "$BACKUP_SCRIPT" restore "$gpg_file" 2>&1 || true)
assert_contains "$output" "--force" "restore fails without --force in non-interactive mode"
teardown

# restore roundtrip: create -> delete originals -> restore -> verify
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
gpg_file=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" | head -1)
# Delete original data
rm -rf "$TEST_DIR/home/vscode/.claude" "$TEST_DIR/home/vscode/.gemini"
# Restore with --force, extract to TEST_DIR as root
export BACKUP_RESTORE_ROOT="$TEST_DIR"
bash "$BACKUP_SCRIPT" restore "$gpg_file" --force >/dev/null 2>&1
TESTS_RUN=$((TESTS_RUN + 1))
# tar strips leading / from absolute paths, so archive contains e.g. "tmp/tmp.XXX/home/vscode/.claude/..."
# With -C $TEST_DIR, files land at $TEST_DIR/tmp/tmp.XXX/home/vscode/.claude/...
restored_file=$(find "$TEST_DIR" -name "token.json" -path "*/.claude/*" 2>/dev/null | head -1)
if [[ -n "$restored_file" ]]; then
    content=$(cat "$restored_file")
    if [[ "$content" == "secret-token-1" ]]; then pass "restore roundtrip preserves file content"
    else fail_test "restore roundtrip preserves file content" "wrong content: $content"; fi
else
    fail_test "restore roundtrip preserves file content" "token.json not found after restore"
fi
teardown

# restore fails with wrong PIN
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
gpg_file=$(find "$BACKUP_DIR" -name "*.tar.gz.gpg" | head -1)
export BACKUP_PIN="wrongpin"
output=$(bash "$BACKUP_SCRIPT" restore "$gpg_file" --force 2>&1 || true)
assert_contains "$output" "❌" "restore fails with wrong PIN"
teardown

# ── List tests ───────────────────────────────────────────

echo ""
echo "=== List tests ==="

# list with no backups
setup
output=$(bash "$BACKUP_SCRIPT" list 2>&1)
assert_contains "$output" "No backups" "list shows message when no backups exist"
teardown

# list after creating backup
setup
export BACKUP_PIN="testpin123"
bash "$BACKUP_SCRIPT" create >/dev/null 2>&1
output=$(bash "$BACKUP_SCRIPT" list 2>&1)
assert_contains "$output" ".tar.gz.gpg" "list shows backup file after create"
teardown

# ── Summary ──────────────────────────────────────────────

echo ""
echo "Results: $TESTS_PASSED/$TESTS_RUN passed, $TESTS_FAILED failed"
if [[ "$TESTS_FAILED" -gt 0 ]]; then exit 1; fi
