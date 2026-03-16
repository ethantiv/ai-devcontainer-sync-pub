#!/bin/bash
# Tests for setup_multi_github() function
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Test counters
passed=0
failed=0
total=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    total=$((total + 1))
    if [[ "$expected" == "$actual" ]]; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        failed=$((failed + 1))
    fi
}

assert_file_exists() {
    local desc="$1" file="$2"
    total=$((total + 1))
    if [[ -f "$file" ]]; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc (file not found: $file)"
        failed=$((failed + 1))
    fi
}

assert_file_contains() {
    local desc="$1" file="$2" pattern="$3"
    total=$((total + 1))
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc (pattern not found: $pattern)"
        failed=$((failed + 1))
    fi
}

assert_file_not_contains() {
    local desc="$1" file="$2" pattern="$3"
    total=$((total + 1))
    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc (pattern found but should not be: $pattern)"
        failed=$((failed + 1))
    fi
}

assert_file_executable() {
    local desc="$1" file="$2"
    total=$((total + 1))
    if [[ -x "$file" ]]; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc (not executable: $file)"
        failed=$((failed + 1))
    fi
}

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    total=$((total + 1))
    if [[ "$haystack" == *"$needle"* ]]; then
        echo "  ✔ $desc"
        passed=$((passed + 1))
    else
        echo "  ✘ $desc (not found: $needle)"
        failed=$((failed + 1))
    fi
}

# Setup: create temp HOME to avoid touching real config
TEST_HOME=$(mktemp -d)
ORIG_HOME="$HOME"
trap 'HOME="$ORIG_HOME"; rm -rf "$TEST_HOME"' EXIT

setup_test_env() {
    rm -rf "$TEST_HOME"
    TEST_HOME=$(mktemp -d)
    HOME="$TEST_HOME"
    mkdir -p "$HOME/.local/bin"
    touch "$HOME/.bashrc"
}

# Source the functions from setup-env.sh (without running main)
source "$REPO_ROOT/.devcontainer/setup-env.sh" 2>/dev/null || true

echo "=== test_multi_github.sh ==="

# --- Test: skips when GH_TOKEN_ROCHE is not set ---
echo ""
echo "Test group: GH_TOKEN_ROCHE not set"
setup_test_env
unset GH_TOKEN_ROCHE 2>/dev/null || true
export GIT_USER_NAME="Test User"
export GIT_USER_EMAIL="test@personal.com"
export GIT_USER_EMAIL_ROCHE=""
setup_multi_github 2>/dev/null || true
assert_file_not_contains "no includeIf in gitconfig" "$HOME/.gitconfig" "includeIf"
assert_file_not_contains "no GH_TOKEN_ROCHE in bashrc" "$HOME/.bashrc" "GH_TOKEN_ROCHE"

# --- Test: creates all files when GH_TOKEN_ROCHE is set ---
echo ""
echo "Test group: GH_TOKEN_ROCHE set"
setup_test_env
export GH_TOKEN_ROCHE="ghp_test_roche_token"
export GH_TOKEN="ghp_test_personal_token"
export GIT_USER_NAME="Test User"
export GIT_USER_EMAIL="test@personal.com"
export GIT_USER_EMAIL_ROCHE="test@roche.com"
setup_multi_github 2>/dev/null || true

assert_file_exists "~/.gitconfig created" "$HOME/.gitconfig"
assert_file_exists "~/.gitconfig-roche created" "$HOME/.gitconfig-roche"
assert_file_exists "credential helper created" "$HOME/.local/bin/git-credential-github-multi"
assert_file_executable "credential helper is executable" "$HOME/.local/bin/git-credential-github-multi"

# Check gitconfig content
assert_file_contains "gitconfig has user.name" "$HOME/.gitconfig" "name = Test User"
assert_file_contains "gitconfig has user.email" "$HOME/.gitconfig" "email = test@personal.com"
assert_file_contains "gitconfig has includeIf for Roche" "$HOME/.gitconfig" 'includeIf "gitdir:~/projects/Roche/"'
assert_file_contains "gitconfig points to gitconfig-roche" "$HOME/.gitconfig" "path = ~/.gitconfig-roche"

# Check gitconfig-roche content
assert_file_contains "roche config has email" "$HOME/.gitconfig-roche" "email = test@roche.com"
assert_file_contains "roche config clears helper list" "$HOME/.gitconfig-roche" "helper =$"
assert_file_contains "roche config has custom helper" "$HOME/.gitconfig-roche" "git-credential-github-multi"

# Check bashrc
assert_file_contains "bashrc exports GH_TOKEN_ROCHE" "$HOME/.bashrc" "GH_TOKEN_ROCHE"
assert_file_contains "bashrc has gh wrapper" "$HOME/.bashrc" "gh()"
assert_file_contains "bashrc has Roche path check" "$HOME/.bashrc" "projects/Roche"

# Check credential helper script
assert_file_contains "credential helper checks get" "$HOME/.local/bin/git-credential-github-multi" 'get'
assert_file_contains "credential helper uses GH_TOKEN_ROCHE" "$HOME/.local/bin/git-credential-github-multi" 'GH_TOKEN_ROCHE'
assert_file_contains "credential helper has quit guard" "$HOME/.local/bin/git-credential-github-multi" 'quit=true'

# --- Test: idempotency - second run doesn't duplicate ---
echo ""
echo "Test group: Idempotency"
bashrc_lines_before=$(wc -l < "$HOME/.bashrc")
setup_multi_github 2>/dev/null || true
bashrc_lines_after=$(wc -l < "$HOME/.bashrc")
assert_eq "bashrc not duplicated on re-run" "$bashrc_lines_before" "$bashrc_lines_after"

# --- Test: credential helper returns correct token ---
echo ""
echo "Test group: Credential helper output"
export GH_TOKEN_ROCHE="ghp_test_roche_token"
cred_output=$(echo -e "protocol=https\nhost=github.com\n" | "$HOME/.local/bin/git-credential-github-multi" get)
assert_contains "cred helper outputs username" "$cred_output" "username=x-access-token"
assert_contains "cred helper outputs password" "$cred_output" "password=ghp_test_roche_token"

# --- Test: credential helper quits when token empty ---
echo ""
echo "Test group: Credential helper without token"
unset GH_TOKEN_ROCHE
quit_output=$(echo -e "protocol=https\nhost=github.com\n" | "$HOME/.local/bin/git-credential-github-multi" get)
assert_contains "cred helper outputs quit" "$quit_output" "quit=true"

# --- Summary ---
echo ""
echo "=== Results: $passed/$total passed, $failed failed ==="
[[ $failed -eq 0 ]] && exit 0 || exit 1
