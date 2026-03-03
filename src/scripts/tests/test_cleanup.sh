#!/bin/bash
# Tests for cleanup.sh port cleanup
# Run: bash src/scripts/tests/test_cleanup.sh

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

fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "  ${RED}✗${RESET} $1: $2"
}

assert_eq() {
  local expected="$1" actual="$2" msg="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  if [[ "$expected" == "$actual" ]]; then pass "$msg"
  else fail "$msg" "expected '$expected', got '$actual'"; fi
}

assert_contains() {
  local haystack="$1" needle="$2" msg="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  if [[ "$haystack" == *"$needle"* ]]; then pass "$msg"
  else fail "$msg" "expected to contain '$needle'"; fi
}

assert_not_contains() {
  local haystack="$1" needle="$2" msg="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  if [[ "$haystack" != *"$needle"* ]]; then pass "$msg"
  else fail "$msg" "expected NOT to contain '$needle'"; fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/../cleanup.sh"

TEST_DIR=""
ORIG_PATH=""

setup() {
  TEST_DIR=$(mktemp -d)
  ORIG_PATH="$PATH"
  mkdir -p "$TEST_DIR/bin"
}

teardown() {
  export PATH="$ORIG_PATH"
  [[ -n "$TEST_DIR" ]] && rm -rf "$TEST_DIR"
  TEST_DIR=""
}

# ============================================================
# Test 1: Default ports — no ports released when lsof reports nothing
# ============================================================

echo "cleanup.sh — default ports, nothing occupied"

setup

# Mock lsof: always reports no port occupied (exit 1)
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$TEST_DIR/bin/lsof"

# Mock fuser: record calls (should not be called)
cat > "$TEST_DIR/bin/fuser" << MOCK
#!/bin/bash
echo "fuser \$*" >> "$TEST_DIR/fuser_calls.log"
exit 0
MOCK
chmod +x "$TEST_DIR/bin/fuser"

export PATH="$TEST_DIR/bin:$PATH"

output=$(bash "$CLEANUP_SCRIPT" 2>&1)
assert_eq "" "$output" "no output when no ports occupied"

TESTS_RUN=$((TESTS_RUN + 1))
if [[ ! -f "$TEST_DIR/fuser_calls.log" ]]; then
  pass "fuser not called when no ports occupied"
else
  fail "fuser not called when no ports occupied" "fuser was called: $(cat "$TEST_DIR/fuser_calls.log")"
fi

teardown

# ============================================================
# Test 2: Releases port when lsof reports port 3000 occupied
# ============================================================

echo ""
echo "cleanup.sh — port 3000 occupied"

setup

# Mock lsof: only port 3000 is occupied (unquoted MOCK for variable expansion)
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
# Parse the port from -i :PORT argument
for arg in "$@"; do
  if [[ "$arg" == ":3000" ]]; then
    exit 0  # port 3000 is occupied
  fi
done
exit 1  # all other ports free
MOCK
chmod +x "$TEST_DIR/bin/lsof"

# Mock fuser: record calls (unquoted MOCK for $TEST_DIR expansion)
cat > "$TEST_DIR/bin/fuser" << MOCK
#!/bin/bash
echo "\$*" >> "$TEST_DIR/fuser_calls.log"
exit 0
MOCK
chmod +x "$TEST_DIR/bin/fuser"

export PATH="$TEST_DIR/bin:$PATH"

output=$(bash "$CLEANUP_SCRIPT" 2>&1)
assert_contains "$output" "Released port 3000" "reports released port 3000"

TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$TEST_DIR/fuser_calls.log" ]]; then
  fuser_cmd=$(cat "$TEST_DIR/fuser_calls.log")
  if [[ "$fuser_cmd" == *"3000/tcp"* ]]; then
    pass "fuser called with 3000/tcp"
  else
    fail "fuser called with 3000/tcp" "got: $fuser_cmd"
  fi
else
  fail "fuser called with 3000/tcp" "fuser was never called"
fi

# Verify fuser was called only once (only for port 3000)
TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$TEST_DIR/fuser_calls.log" ]]; then
  call_count=$(wc -l < "$TEST_DIR/fuser_calls.log")
  if [[ "$call_count" -eq 1 ]]; then
    pass "fuser called exactly once (only for occupied port)"
  else
    fail "fuser called exactly once (only for occupied port)" "called $call_count times"
  fi
else
  fail "fuser called exactly once (only for occupied port)" "fuser was never called"
fi

teardown

# ============================================================
# Test 3: Respects LOOP_PORTS override
# ============================================================

echo ""
echo "cleanup.sh — LOOP_PORTS override"

setup

# Mock lsof: all ports occupied
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$TEST_DIR/bin/lsof"

# Mock fuser: record calls (unquoted MOCK for $TEST_DIR expansion)
cat > "$TEST_DIR/bin/fuser" << MOCK
#!/bin/bash
echo "\$*" >> "$TEST_DIR/fuser_calls.log"
exit 0
MOCK
chmod +x "$TEST_DIR/bin/fuser"

export PATH="$TEST_DIR/bin:$PATH"

output=$(LOOP_PORTS="9090 9091" bash "$CLEANUP_SCRIPT" 2>&1)

assert_contains "$output" "Released port 9090" "releases custom port 9090"
assert_contains "$output" "Released port 9091" "releases custom port 9091"
assert_not_contains "$output" "Released port 3000" "does not touch default port 3000"

# Verify fuser was called exactly twice (for 9090 and 9091)
TESTS_RUN=$((TESTS_RUN + 1))
if [[ -f "$TEST_DIR/fuser_calls.log" ]]; then
  call_count=$(wc -l < "$TEST_DIR/fuser_calls.log")
  if [[ "$call_count" -eq 2 ]]; then
    pass "fuser called exactly twice for custom ports"
  else
    fail "fuser called exactly twice for custom ports" "called $call_count times"
  fi
else
  fail "fuser called exactly twice for custom ports" "fuser was never called"
fi

teardown

# ============================================================
# Test 4: Handles fuser failure gracefully
# ============================================================

echo ""
echo "cleanup.sh — fuser failure handled gracefully"

setup

# Mock lsof: port occupied
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$TEST_DIR/bin/lsof"

# Mock fuser: always fails
cat > "$TEST_DIR/bin/fuser" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$TEST_DIR/bin/fuser"

export PATH="$TEST_DIR/bin:$PATH"

exit_code=0
output=$(LOOP_PORTS="4444" bash "$CLEANUP_SCRIPT" 2>&1) || exit_code=$?

TESTS_RUN=$((TESTS_RUN + 1))
if [[ "$exit_code" -eq 0 ]]; then
  pass "script exits 0 even when fuser fails (|| true)"
else
  fail "script exits 0 even when fuser fails (|| true)" "exit code was $exit_code"
fi

assert_contains "$output" "Released port 4444" "still reports released port despite fuser failure"

teardown

# ============================================================
# Summary
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "cleanup.sh tests: $TESTS_RUN total, $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $TESTS_FAILED -eq 0 ]] && exit 0 || exit 1
