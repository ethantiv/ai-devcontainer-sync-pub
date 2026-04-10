#!/bin/bash
# Tests for config/scripts/setup-common.sh
# Run: bash src/scripts/tests/test_setup_common.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMMON_SH="$REPO_ROOT/config/scripts/setup-common.sh"

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

fail_test() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "  ${RED}✗${RESET} $1: $2"
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$expected" == "$actual" ]]; then
        pass "$msg"
    else
        fail_test "$msg" "expected '$expected', got '$actual'"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$msg"
    else
        fail_test "$msg" "expected to contain '$needle' in '$haystack'"
    fi
}

assert_exit_code() {
    local expected="$1" actual="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$expected" -eq "$actual" ]]; then
        pass "$msg"
    else
        fail_test "$msg" "expected exit code $expected, got $actual"
    fi
}

# Create a shared temp dir and clean up on exit
TEST_TMP=$(mktemp -d)
trap 'rm -rf "$TEST_TMP"' EXIT

# Helper: set all required variables pointing to safe dummy paths
setup_required_vars() {
    export CLAUDE_DIR="$TEST_TMP/claude"
    export CLAUDE_SETTINGS_FILE="$TEST_TMP/claude/settings.json"
    export CONFIG_PARSER="$TEST_TMP/config-parser.js"
    export CONFIG_FILE="$TEST_TMP/env-config.yaml"
    export ENVIRONMENT_TAG="test"
    export OFFICIAL_MARKETPLACE_NAME="dev-marketplace"
    export OFFICIAL_MARKETPLACE_REPO="https://github.com/example/marketplace"
    export LOCAL_MARKETPLACE_NAME="local-marketplace"
    export LOCAL_MARKETPLACE_DIR="$TEST_TMP/local-plugins"
    export ENV_EXPORT_FILE="$TEST_TMP/env.sh"
}

unset_required_vars() {
    unset CLAUDE_DIR CLAUDE_SETTINGS_FILE CONFIG_PARSER CONFIG_FILE
    unset ENVIRONMENT_TAG OFFICIAL_MARKETPLACE_NAME OFFICIAL_MARKETPLACE_REPO
    unset LOCAL_MARKETPLACE_NAME LOCAL_MARKETPLACE_DIR ENV_EXPORT_FILE
}

# Source setup-common.sh with required vars set (once, for function tests)
setup_required_vars
# shellcheck source=/dev/null
source "$COMMON_SH"

# ============================================================
# Group 1: Sourcing validation
# ============================================================

echo "Group 1: Sourcing validation"

# Test: sourcing without required variables fails
# Explicitly unset all required vars so the subshell does not inherit them from setup_required_vars
exit_code=0
bash -c "
    unset CLAUDE_DIR CLAUDE_SETTINGS_FILE CONFIG_PARSER CONFIG_FILE
    unset ENVIRONMENT_TAG OFFICIAL_MARKETPLACE_NAME OFFICIAL_MARKETPLACE_REPO
    unset LOCAL_MARKETPLACE_NAME LOCAL_MARKETPLACE_DIR ENV_EXPORT_FILE
    source '$COMMON_SH'
" 2>/dev/null || exit_code=$?
assert_exit_code 1 "$exit_code" "sourcing without required variables exits with code 1"

# Test: sourcing with all required variables succeeds
exit_code=0
bash -c "
    export CLAUDE_DIR='$TEST_TMP/claude2'
    export CLAUDE_SETTINGS_FILE='$TEST_TMP/claude2/settings.json'
    export CONFIG_PARSER='$TEST_TMP/config-parser.js'
    export CONFIG_FILE='$TEST_TMP/env-config.yaml'
    export ENVIRONMENT_TAG='test'
    export OFFICIAL_MARKETPLACE_NAME='dev-marketplace'
    export OFFICIAL_MARKETPLACE_REPO='https://github.com/example/marketplace'
    export LOCAL_MARKETPLACE_NAME='local-marketplace'
    export LOCAL_MARKETPLACE_DIR='$TEST_TMP/local-plugins'
    export ENV_EXPORT_FILE='$TEST_TMP/env.sh'
    source '$COMMON_SH'
" 2>/dev/null || exit_code=$?
assert_exit_code 0 "$exit_code" "sourcing with all required variables succeeds"

# Test: double-sourcing is safe (no error) — _SETUP_COMMON_LOADED guard
exit_code=0
bash -c "
    export CLAUDE_DIR='$TEST_TMP/claude3'
    export CLAUDE_SETTINGS_FILE='$TEST_TMP/claude3/settings.json'
    export CONFIG_PARSER='$TEST_TMP/config-parser.js'
    export CONFIG_FILE='$TEST_TMP/env-config.yaml'
    export ENVIRONMENT_TAG='test'
    export OFFICIAL_MARKETPLACE_NAME='dev-marketplace'
    export OFFICIAL_MARKETPLACE_REPO='https://github.com/example/marketplace'
    export LOCAL_MARKETPLACE_NAME='local-marketplace'
    export LOCAL_MARKETPLACE_DIR='$TEST_TMP/local-plugins'
    export ENV_EXPORT_FILE='$TEST_TMP/env.sh'
    source '$COMMON_SH'
    source '$COMMON_SH'
" 2>/dev/null || exit_code=$?
assert_exit_code 0 "$exit_code" "double-sourcing is safe (no error)"

# ============================================================
# Group 2: Function availability
# ============================================================

echo ""
echo "Group 2: Function availability"

# Utility functions
for fn in ensure_directory has_command ok warn fail; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Claude settings / env / file functions
for fn in apply_claude_settings propagate_env_from_config copy_claude_memory sync_claude_scripts; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Plugin functions
for fn in install_plugin update_plugin_counters ensure_marketplace uninstall_plugin; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Skill functions
for fn in install_skill install_github_skill; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Bulk install functions
for fn in install_all_plugins_and_skills install_local_marketplace_plugins; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Plugin sync functions
for fn in build_expected_plugins_list get_installed_plugins sync_plugins; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# Skill sync
TESTS_RUN=$((TESTS_RUN + 1))
if declare -f sync_skills > /dev/null 2>&1; then
    pass "function 'sync_skills' is defined"
else
    fail_test "function 'sync_skills' is defined" "not found"
fi

# Marketplace sync
TESTS_RUN=$((TESTS_RUN + 1))
if declare -f sync_marketplaces > /dev/null 2>&1; then
    pass "function 'sync_marketplaces' is defined"
else
    fail_test "function 'sync_marketplaces' is defined" "not found"
fi

# MCP functions
for fn in add_mcp_server parse_mcp_servers sync_mcp_servers; do
    TESTS_RUN=$((TESTS_RUN + 1))
    if declare -f "$fn" > /dev/null 2>&1; then
        pass "function '$fn' is defined"
    else
        fail_test "function '$fn' is defined" "not found"
    fi
done

# ============================================================
# Group 3: Utility function tests
# ============================================================

echo ""
echo "Group 3: Utility function tests"

# ensure_directory: creates nested dirs
nested_dir="$TEST_TMP/a/b/c"
ensure_directory "$nested_dir"
TESTS_RUN=$((TESTS_RUN + 1))
if [[ -d "$nested_dir" ]]; then
    pass "ensure_directory creates nested directories"
else
    fail_test "ensure_directory creates nested directories" "directory not created"
fi

# ensure_directory: is idempotent (calling twice doesn't error)
exit_code=0
ensure_directory "$nested_dir" || exit_code=$?
assert_exit_code 0 "$exit_code" "ensure_directory is idempotent"

# has_command: finds bash
TESTS_RUN=$((TESTS_RUN + 1))
if has_command bash; then
    pass "has_command finds bash"
else
    fail_test "has_command finds bash" "bash not found"
fi

# has_command: fails on nonexistent command
TESTS_RUN=$((TESTS_RUN + 1))
if ! has_command __nonexistent_cmd_xyz__; then
    pass "has_command returns false for nonexistent command"
else
    fail_test "has_command returns false for nonexistent command" "unexpectedly found"
fi

# ok: output contains the message text
ok_output=$(ok "test ok message" 2>&1)
assert_contains "$ok_output" "test ok message" "ok() outputs the message text"

# warn: output contains the message text
warn_output=$(warn "test warn message" 2>&1)
assert_contains "$warn_output" "test warn message" "warn() outputs the message text"

# fail (setup-common's fail): output contains the message text
fail_output=$(fail "test fail message" 2>&1)
assert_contains "$fail_output" "test fail message" "fail() outputs the message text"

# update_plugin_counters: rc=0 increments installed
installed=0; skipped=0; failed_count=0
update_plugin_counters 0 installed skipped failed_count
assert_eq "1" "$installed" "update_plugin_counters rc=0 increments installed"
assert_eq "0" "$skipped"   "update_plugin_counters rc=0 does not increment skipped"
assert_eq "0" "$failed_count" "update_plugin_counters rc=0 does not increment failed"

# update_plugin_counters: rc=1 increments skipped
installed=0; skipped=0; failed_count=0
update_plugin_counters 1 installed skipped failed_count
assert_eq "0" "$installed" "update_plugin_counters rc=1 does not increment installed"
assert_eq "1" "$skipped"   "update_plugin_counters rc=1 increments skipped"
assert_eq "0" "$failed_count" "update_plugin_counters rc=1 does not increment failed"

# update_plugin_counters: rc=2 increments failed
installed=0; skipped=0; failed_count=0
update_plugin_counters 2 installed skipped failed_count
assert_eq "0" "$installed" "update_plugin_counters rc=2 does not increment installed"
assert_eq "0" "$skipped"   "update_plugin_counters rc=2 does not increment skipped"
assert_eq "1" "$failed_count" "update_plugin_counters rc=2 increments failed"

# ============================================================
# Group 4: File operation tests
# ============================================================

echo ""
echo "Group 4: File operation tests"

# copy_claude_memory: copies from correct path
mem_source_dir="$TEST_TMP/memsrc"
mkdir -p "$mem_source_dir/config"
echo "# Test memory content" > "$mem_source_dir/config/CLAUDE.md.memory"
dest_claude_dir="$TEST_TMP/claude_mem"
mkdir -p "$dest_claude_dir"
# Temporarily override CLAUDE_DIR for this test
orig_claude_dir="$CLAUDE_DIR"
CLAUDE_DIR="$dest_claude_dir"
copy_claude_memory "$mem_source_dir" 2>/dev/null
CLAUDE_DIR="$orig_claude_dir"
TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$dest_claude_dir/CLAUDE.md" ]]; then
    pass "copy_claude_memory copies CLAUDE.md.memory to CLAUDE_DIR/CLAUDE.md"
else
    fail_test "copy_claude_memory copies CLAUDE.md.memory to CLAUDE_DIR/CLAUDE.md" "file not found at $dest_claude_dir/CLAUDE.md"
fi

# copy_claude_memory: content is preserved
TESTS_RUN=$((TESTS_RUN + 1))
if grep -qF "# Test memory content" "$dest_claude_dir/CLAUDE.md" 2>/dev/null; then
    pass "copy_claude_memory preserves file content"
else
    fail_test "copy_claude_memory preserves file content" "content not found"
fi

# sync_claude_scripts: copies .sh scripts and sets +x
scripts_source_dir="$TEST_TMP/scripts_src"
mkdir -p "$scripts_source_dir/config/scripts"
echo "#!/bin/bash" > "$scripts_source_dir/config/scripts/context-bar.sh"
echo "#!/bin/bash" > "$scripts_source_dir/config/scripts/other-script.sh"
dest_claude_scripts="$TEST_TMP/claude_scripts"
mkdir -p "$dest_claude_scripts"
orig_claude_dir="$CLAUDE_DIR"
CLAUDE_DIR="$dest_claude_scripts"
sync_claude_scripts "$scripts_source_dir" 2>/dev/null
CLAUDE_DIR="$orig_claude_dir"

TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$dest_claude_scripts/scripts/context-bar.sh" ]]; then
    pass "sync_claude_scripts copies scripts to CLAUDE_DIR/scripts/"
else
    fail_test "sync_claude_scripts copies scripts to CLAUDE_DIR/scripts/" "context-bar.sh not found"
fi

TESTS_RUN=$((TESTS_RUN + 1))
if [[ -x "$dest_claude_scripts/scripts/context-bar.sh" ]]; then
    pass "sync_claude_scripts sets +x on copied scripts"
else
    fail_test "sync_claude_scripts sets +x on copied scripts" "context-bar.sh is not executable"
fi

TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$dest_claude_scripts/scripts/other-script.sh" && -x "$dest_claude_scripts/scripts/other-script.sh" ]]; then
    pass "sync_claude_scripts copies and makes executable all .sh files"
else
    fail_test "sync_claude_scripts copies and makes executable all .sh files" "other-script.sh missing or not executable"
fi

# ============================================================
# Summary
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: $TESTS_RUN | Passed: $TESTS_PASSED | Failed: $TESTS_FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $TESTS_FAILED -eq 0 ]] && exit 0 || exit 1
