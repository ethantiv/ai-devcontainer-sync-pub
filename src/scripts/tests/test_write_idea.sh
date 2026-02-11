#!/bin/bash
# Tests for resolve_idea() and write_idea() in loop.sh
# Run: bash src/scripts/tests/test_write_idea.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOOP_SH="$SCRIPT_DIR/../loop.sh"

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

assert_file_contains() {
    local file="$1" needle="$2" msg="$3"
    TESTS_RUN=$((TESTS_RUN + 1))
    if grep -qF "$needle" "$file" 2>/dev/null; then
        pass "$msg"
    else
        fail "$msg" "file '$file' does not contain '$needle'"
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

# Extract resolve_idea and write_idea functions from loop.sh
# We source only the function definitions, not the full script
extract_functions() {
    # Extract from "# Resolve idea" to end of write_idea function
    sed -n '/^# Resolve idea content/,/^}/p' "$LOOP_SH" | head -n -0
    # Also get write_idea
    sed -n '/^# Write idea to docs/,/^}/p' "$LOOP_SH"
}

# Create isolated test environment
setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    # Source the extracted functions
    eval "$(extract_functions)"
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

# ============================================================
# Tests for resolve_idea() — inline text
# ============================================================

echo "resolve_idea() — inline text"

setup
result=$(resolve_idea "Add authentication feature")
assert_eq "Add authentication feature" "$result" "returns inline text as-is"
teardown

setup
result=$(resolve_idea 'Text with $variables and `backticks`')
assert_eq 'Text with $variables and `backticks`' "$result" "preserves special characters in inline text"
teardown

# ============================================================
# Tests for resolve_idea() — @file
# ============================================================

echo ""
echo "resolve_idea() — @file source"

setup
echo "Feature idea from file" > "$TEST_DIR/idea.md"
result=$(resolve_idea "@$TEST_DIR/idea.md")
assert_eq "Feature idea from file" "$result" "reads content from @file path"
teardown

setup
cat > "$TEST_DIR/multi.md" << 'TESTEOF'
# Feature: User Auth

- Login with OAuth
- Support $HOME expansion in config
- Use `bcrypt` for hashing
TESTEOF
result=$(resolve_idea "@$TEST_DIR/multi.md")
assert_contains "$result" "Login with OAuth" "reads multi-line file content"
assert_contains "$result" '$HOME' "preserves dollar signs from file"
assert_contains "$result" '`bcrypt`' "preserves backticks from file"
teardown

setup
result=$(resolve_idea "@/nonexistent/file.md" 2>/dev/null) || exit_code=$?
assert_exit_code 1 "${exit_code:-0}" "returns error for missing @file"
teardown

# ============================================================
# Tests for resolve_idea() — GitHub issue URL (mocked)
# ============================================================

echo ""
echo "resolve_idea() — GitHub issue URL"

setup
# Mock gh command
mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/gh" << 'MOCKEOF'
#!/bin/bash
# Verify correct arguments
if [[ "$1" == "issue" && "$2" == "view" && "$4" == "--json" && "$5" == "body" ]]; then
    echo "Issue body content from GitHub"
    exit 0
fi
exit 1
MOCKEOF
chmod +x "$TEST_DIR/bin/gh"
export PATH="$TEST_DIR/bin:$PATH"

result=$(resolve_idea "https://github.com/owner/repo/issues/42")
assert_eq "Issue body content from GitHub" "$result" "fetches GitHub issue body via gh CLI"
teardown

setup
# Mock gh that fails
mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/gh" << 'MOCKEOF'
#!/bin/bash
exit 1
MOCKEOF
chmod +x "$TEST_DIR/bin/gh"
export PATH="$TEST_DIR/bin:$PATH"

result=$(resolve_idea "https://github.com/owner/repo/issues/99" 2>/dev/null) || exit_code=$?
assert_exit_code 1 "${exit_code:-0}" "returns error when gh issue view fails"
teardown

# ============================================================
# Tests for resolve_idea() — GitHub PR URL (mocked)
# ============================================================

echo ""
echo "resolve_idea() — GitHub PR URL"

setup
mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/gh" << 'MOCKEOF'
#!/bin/bash
if [[ "$1" == "pr" && "$2" == "view" && "$4" == "--json" && "$5" == "body" ]]; then
    echo "PR body content from GitHub"
    exit 0
fi
exit 1
MOCKEOF
chmod +x "$TEST_DIR/bin/gh"
export PATH="$TEST_DIR/bin:$PATH"

result=$(resolve_idea "https://github.com/owner/repo/pull/123")
assert_eq "PR body content from GitHub" "$result" "fetches GitHub PR body via gh CLI"
teardown

# ============================================================
# Tests for resolve_idea() — generic URL (mocked)
# ============================================================

echo ""
echo "resolve_idea() — generic URL"

setup
mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/curl" << 'MOCKEOF'
#!/bin/bash
echo "<html><body><p>Plain text content</p></body></html>"
MOCKEOF
chmod +x "$TEST_DIR/bin/curl"
export PATH="$TEST_DIR/bin:$PATH"

result=$(resolve_idea "https://example.com/idea.html")
assert_contains "$result" "Plain text content" "strips HTML tags from fetched URL"
teardown

setup
# Mock curl that fails
mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/curl" << 'MOCKEOF'
#!/bin/bash
exit 1
MOCKEOF
chmod +x "$TEST_DIR/bin/curl"
export PATH="$TEST_DIR/bin:$PATH"

result=$(resolve_idea "https://example.com/broken" 2>/dev/null) || exit_code=$?
assert_exit_code 1 "${exit_code:-0}" "returns error when curl fails"
teardown

# ============================================================
# Tests for write_idea() — integration
# ============================================================

echo ""
echo "write_idea() — integration"

setup
IDEA="Simple inline idea"
write_idea > /dev/null
assert_file_contains "docs/ROADMAP.md" "# Roadmap" "creates ROADMAP.md with header"
assert_file_contains "docs/ROADMAP.md" "Simple inline idea" "writes inline idea to ROADMAP.md"
teardown

setup
echo "Content from file source" > "$TEST_DIR/seed.txt"
IDEA="@$TEST_DIR/seed.txt"
write_idea > /dev/null
assert_file_contains "docs/ROADMAP.md" "Content from file source" "writes @file content to ROADMAP.md"
teardown

setup
cat > "$TEST_DIR/special.md" << 'TESTEOF'
Use $PATH and `command` in config
TESTEOF
IDEA="@$TEST_DIR/special.md"
write_idea > /dev/null
assert_file_contains 'docs/ROADMAP.md' '$PATH' "preserves dollar signs in ROADMAP.md (quoted heredoc)"
assert_file_contains 'docs/ROADMAP.md' '`command`' "preserves backticks in ROADMAP.md"
teardown

setup
IDEA=""
write_idea > /dev/null 2>&1
((TESTS_RUN++))
if [[ ! -f "docs/ROADMAP.md" ]]; then
    pass "does not create ROADMAP.md when IDEA is empty"
else
    fail "does not create ROADMAP.md when IDEA is empty" "file was created"
fi
teardown

# ============================================================
# Summary
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: $TESTS_RUN | Passed: $TESTS_PASSED | Failed: $TESTS_FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $TESTS_FAILED -eq 0 ]] && exit 0 || exit 1
