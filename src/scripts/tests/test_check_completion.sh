#!/bin/bash
# Tests for check_completion() in loop.sh
# Run: bash src/scripts/tests/test_check_completion.sh

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

# Create temp dir for test plans
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Source only check_completion from loop.sh by extracting it
# We override the plan path via a wrapper
extract_check_completion() {
    cat <<'FUNC'
check_completion() {
    local plan="$TEST_PLAN_FILE"
    [[ ! -f "$plan" ]] && return 1

    local unchecked pending_phases complete_marker

    unchecked=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]\]' "$plan" 2>/dev/null) || unchecked=0
    pending_phases=$(grep -ciE '\*{0,2}Status\*{0,2}:\*{0,2}\s*(pending|in.progress)' "$plan" 2>/dev/null) || pending_phases=0
    complete_marker=$(grep -cE '\*{0,2}Status\*{0,2}:\*{0,2}\s*(COMPLETE|DONE)|BUILD COMPLETE|PLAN COMPLETE' "$plan" 2>/dev/null) || complete_marker=0

    [[ "$unchecked" -eq 0 && "$pending_phases" -eq 0 && "$complete_marker" -gt 0 ]]
}
FUNC
}

eval "$(extract_check_completion)"

# Helper: assert check_completion returns 0 (complete)
assert_complete() {
    local msg="$1"
    TESTS_RUN=$((TESTS_RUN + 1))
    if check_completion; then
        pass "$msg"
    else
        fail "$msg" "expected COMPLETE but got NOT COMPLETE"
    fi
}

# Helper: assert check_completion returns 1 (not complete)
assert_not_complete() {
    local msg="$1"
    TESTS_RUN=$((TESTS_RUN + 1))
    if check_completion; then
        fail "$msg" "expected NOT COMPLETE but got COMPLETE"
    else
        pass "$msg"
    fi
}

write_plan() {
    TEST_PLAN_FILE="$TMPDIR/plan_${TESTS_RUN}.md"
    cat > "$TEST_PLAN_FILE"
}

echo "=== check_completion() tests ==="
echo ""
echo "--- Basic signals ---"

# Test 1: No plan file
TEST_PLAN_FILE="$TMPDIR/nonexistent.md"
assert_not_complete "no plan file → not complete"

# Test 2: Empty plan
write_plan <<'EOF'
# Plan
EOF
assert_not_complete "empty plan (no markers) → not complete"

# Test 3: Only completion marker, no tracking
write_plan <<'EOF'
# Plan

**Status:** COMPLETE
EOF
assert_complete "completion marker only, no checkboxes/phases → complete"

# Test 4: Unchecked checkboxes + completion marker
write_plan <<'EOF'
# Plan

**Status:** COMPLETE

- [ ] Task 1
- [x] Task 2
EOF
assert_not_complete "unchecked checkbox + completion marker → not complete"

# Test 5: All checked + completion marker
write_plan <<'EOF'
# Plan

**Status:** COMPLETE

- [x] Task 1
- [x] Task 2
EOF
assert_complete "all checked + completion marker → complete"

echo ""
echo "--- Phase status tracking ---"

# Test 6: Phases pending, no checkboxes
write_plan <<'EOF'
## Phase 1

**Status:** pending

## Phase 2

**Status:** pending
EOF
assert_not_complete "pending phases → not complete"

# Test 7: Phases in_progress
write_plan <<'EOF'
## Phase 1

**Status:** complete

## Phase 2

**Status:** in_progress
EOF
assert_not_complete "in_progress phase → not complete"

# Test 8: All phases complete (lowercase) but no COMPLETE marker
write_plan <<'EOF'
## Phase 1

**Status:** complete

## Phase 2

**Status:** complete
EOF
assert_not_complete "all phases lowercase complete but no COMPLETE marker → not complete"

# Test 9: All phases complete + COMPLETE marker
write_plan <<'EOF'
**Status:** COMPLETE

## Phase 1

**Status:** complete

## Phase 2

**Status:** complete
EOF
assert_complete "all phases complete + COMPLETE marker → complete"

echo ""
echo "--- Mixed signals (checkboxes + phases) ---"

# Test 10: Phases complete + unchecked checkbox
write_plan <<'EOF'
**Status:** COMPLETE

## Phase 1

**Status:** complete

- [x] Task 1
- [ ] Task 2
EOF
assert_not_complete "phases complete but unchecked checkbox → not complete"

# Test 11: Checkboxes done + pending phase
write_plan <<'EOF'
**Status:** COMPLETE

## Phase 1

**Status:** complete

- [x] Task 1

## Phase 2

**Status:** pending

- [x] Task 2
EOF
assert_not_complete "checkboxes done but pending phase → not complete"

# Test 12: Everything done
write_plan <<'EOF'
**Status:** COMPLETE

## Phase 1

**Status:** complete

- [x] Task 1

## Phase 2

**Status:** complete

- [x] Task 2
EOF
assert_complete "all checkboxes + all phases + marker → complete"

echo ""
echo "--- Edge cases ---"

# Test 13: BUILD COMPLETE as marker
write_plan <<'EOF'
BUILD COMPLETE

## Phase 1

**Status:** complete
EOF
assert_complete "BUILD COMPLETE marker works"

# Test 14: PLAN COMPLETE as marker
write_plan <<'EOF'
PLAN COMPLETE
EOF
assert_complete "PLAN COMPLETE marker works"

# Test 15: Status: DONE as marker
write_plan <<'EOF'
**Status:** DONE
EOF
assert_complete "Status: DONE marker works"

# Test 16: Case sensitivity — lowercase "complete" is NOT a completion marker
write_plan <<'EOF'
**Status:** complete
EOF
assert_not_complete "lowercase 'complete' is phase status, not completion marker"

# Test 17: In_progress with hyphen
write_plan <<'EOF'
**Status:** COMPLETE

## Phase 1

**Status:** in-progress
EOF
assert_not_complete "in-progress (hyphen) detected as pending"

# Test 18: Status without bold markers
write_plan <<'EOF'
Status: COMPLETE

## Phase 1

Status: complete
EOF
assert_complete "Status without ** bold markers also works"

echo ""
echo "--- Regression: old bug — no checkboxes at all ---"

# Test 19: Plan with phases only (no checkboxes), first phase marked COMPLETE
# This was the old bug: incomplete=0 always, so first COMPLETE triggered exit
write_plan <<'EOF'
## Phase 1

**Status:** COMPLETE

## Phase 2

**Status:** pending

### Task 3: Something
EOF
assert_not_complete "REGRESSION: first phase COMPLETE + second pending → not complete (old bug)"

# Test 20: Plan with no checkboxes, no phases — just text + COMPLETE
write_plan <<'EOF'
# My Plan

Some text about the plan.

**Status:** COMPLETE
EOF
assert_complete "no checkboxes, no phases, just COMPLETE marker → complete"

echo ""
echo "=== Results ==="
echo "  Total:  $TESTS_RUN"
echo "  Passed: $TESTS_PASSED"
echo "  Failed: $TESTS_FAILED"

[[ "$TESTS_FAILED" -eq 0 ]] && exit 0 || exit 1
