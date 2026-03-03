# Loop System Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement three ROADMAP proposals: `loop doctor` health-check command, enhanced `loop summary` metrics (file edit frequency, iteration timing, error rates), and expanded test coverage for `run.js`, `cleanup.js/sh`, and `summary.js` edge cases.

**Architecture:** Test coverage tasks come first (Phases 1-4) so new code is validated by tests from the start. The `doctor` command (Phases 5-6) follows the existing pattern: `lib/doctor.js` module + `cli.js` registration. Summary enhancements (Phases 7-8) extend existing `parseLog()` and `formatSummary()` functions in `summary.js` with backward-compatible new fields.

**Tech Stack:** Node.js (>=18), Jest 30, Commander 14, Bash (shell tests)

---

## Findings & Decisions

1. **run.js testability**: `spawnLoop()` mixes argument-building with process spawning, making it untestable without mocking `child_process`. Solution: extract a pure `buildArgs(opts, mode)` function and export it alongside the existing public API. This is the minimal change needed — no refactor of `spawnLoop` itself.

2. **cleanup.js/sh**: Both are thin wrappers. JS module tests mock `child_process.spawn` and `fs.existsSync`. Shell tests mock `lsof`/`fuser` via `$PATH` prepend (same pattern as existing shell tests).

3. **summary.js edge cases**: Current test coverage is solid for happy paths but misses: `unknown` tool name fallback, missing `file_path` in Edit/Write, non-array `content`, empty JSONL file, multiple `testResults` entries, and the `tool_result` block type in test extraction.

4. **loop doctor checks**: Claude CLI binary, loop symlinks (6 files), `.version` match, `jq` binary, git repo status, required env vars (`GH_TOKEN`). MCP connectivity via `claude mcp list` (subprocess, non-fatal). Output: pass/fail checklist with fix suggestions.

5. **Summary enhancements**: `parseLog` already tracks `filesModified` as a Set (unique paths). Extend to `fileEditCounts` Map (path → count). Add timestamp parsing for iteration boundaries (using `result` entries with `usage`). Error rate = count of `result` entries with `is_error: true`.

6. **Version bump**: Final task bumps `src/package.json` from `0.7.3` to `0.8.0` (new `doctor` command = minor bump).

---

## Phase 1: run.js Testability Refactor

**Status:** complete

### Task 1: Extract buildArgs function

- [x] Extract `buildArgs(opts, mode)` from `spawnLoop()` and export it

**Files:**
- Modify: `src/lib/run.js:24-51`
- Modify: `src/lib/run.js:89` (module.exports)

**Step 1: Write the failing test**

Add to `src/lib/__tests__/run.test.js`:

```js
const { runDesign, buildArgs } = require('../run');

describe('buildArgs', () => {
  test('plan mode adds -p and -a with default 3 iterations', () => {
    const args = buildArgs({}, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3']);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: FAIL — `buildArgs is not a function` (not exported yet)

**Step 3: Write minimal implementation**

In `src/lib/run.js`, extract arg-building logic from `spawnLoop()`:

```js
function buildArgs(opts, mode) {
  const args = [];
  if (mode === 'plan') args.push('-p');
  if (mode === 'design') args.push('-d');
  if (!opts.interactive) args.push('-a');

  if (mode !== 'design') {
    const defaultIter = mode === 'build' ? '99' : '3';
    const iterations = opts.iterations || defaultIter;
    args.push('-i', iterations);
  }

  if (opts.idea) args.push('-I', opts.idea);
  if (opts.new) args.push('-n');
  if (opts.earlyExit === false) args.push('-e');

  return args;
}
```

Update `spawnLoop()` to call `buildArgs`:

```js
function spawnLoop(opts, mode) {
  const loopScript = checkLoopScript();
  const args = buildArgs(opts, mode);
  // ... spawn logic unchanged
}
```

Update exports: `module.exports = { runPlan, runBuild, runCombined, runDesign, buildArgs };`

**Step 4: Run test to verify it passes**

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/run.js src/lib/__tests__/run.test.js
git commit -m "refactor: extract buildArgs from spawnLoop for testability"
```

---

### Task 2: Full buildArgs test coverage

- [x] Test all modes and optional flags in buildArgs

**Files:**
- Modify: `src/lib/__tests__/run.test.js`

**Step 1: Write the failing tests**

Add to the `buildArgs` describe block in `src/lib/__tests__/run.test.js`:

```js
  test('build mode adds -a with default 99 iterations', () => {
    const args = buildArgs({}, 'build');
    expect(args).toEqual(['-a', '-i', '99']);
  });

  test('design mode adds -d, no -a, no -i', () => {
    const args = buildArgs({ interactive: true }, 'design');
    expect(args).toEqual(['-d']);
  });

  test('interactive mode omits -a flag', () => {
    const args = buildArgs({ interactive: true }, 'plan');
    expect(args).toEqual(['-p', '-i', '3']);
  });

  test('custom iterations overrides default', () => {
    const args = buildArgs({ iterations: '10' }, 'build');
    expect(args).toEqual(['-a', '-i', '10']);
  });

  test('idea flag adds -I with text', () => {
    const args = buildArgs({ idea: 'Add auth' }, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3', '-I', 'Add auth']);
  });

  test('new flag adds -n', () => {
    const args = buildArgs({ new: true }, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3', '-n']);
  });

  test('earlyExit false adds -e flag', () => {
    const args = buildArgs({ earlyExit: false }, 'build');
    expect(args).toEqual(['-a', '-i', '99', '-e']);
  });

  test('earlyExit undefined does not add -e', () => {
    const args = buildArgs({}, 'build');
    expect(args).not.toContain('-e');
  });

  test('all flags combined', () => {
    const args = buildArgs({
      interactive: true,
      iterations: '5',
      idea: 'Fix bug',
      new: true,
      earlyExit: false,
    }, 'build');
    expect(args).toEqual(['-i', '5', '-I', 'Fix bug', '-n', '-e']);
  });
```

**Step 2: Run tests to verify they pass** (buildArgs was already extracted in Task 1)

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: PASS (all 10 tests in buildArgs describe block)

**Step 3: Commit**

```bash
git add src/lib/__tests__/run.test.js
git commit -m "test: add full buildArgs coverage for all modes and flags"
```

---

## Phase 2: run.js checkLoopScript & cleanup.js Tests

**Status:** complete

### Task 3: Test checkLoopScript error paths

- [x] Test checkLoopScript for missing script, version mismatch, and happy path

**Files:**
- Modify: `src/lib/run.js:89` (export checkLoopScript)
- Modify: `src/lib/__tests__/run.test.js`

**Step 1: Write the failing tests**

First, export `checkLoopScript` from `run.js`:
```js
module.exports = { runPlan, runBuild, runCombined, runDesign, buildArgs, checkLoopScript };
```

Add to `src/lib/__tests__/run.test.js`:

```js
const fs = require('fs');
const path = require('path');
const os = require('os');
const { checkLoopScript, buildArgs } = require('../run');

describe('checkLoopScript', () => {
  let tmpDir, origCwd;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'run-test-'));
    origCwd = process.cwd();
    process.chdir(tmpDir);
  });

  afterEach(() => {
    process.chdir(origCwd);
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('exits with code 1 when loop/loop.sh is missing', () => {
    const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {
      throw new Error('process.exit');
    });
    const mockError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => checkLoopScript()).toThrow('process.exit');
    expect(mockExit).toHaveBeenCalledWith(1);
    expect(mockError).toHaveBeenCalledWith(expect.stringContaining('loop/loop.sh not found'));

    mockExit.mockRestore();
    mockError.mockRestore();
  });

  test('returns script path when loop/loop.sh exists', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/loop.sh'), '#!/bin/bash\n');

    const result = checkLoopScript();
    expect(result).toBe('./loop/loop.sh');
  });

  test('warns on version mismatch', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/loop.sh'), '#!/bin/bash\n');
    fs.writeFileSync(path.join(tmpDir, 'loop/.version'), '0.0.0\n');

    const mockWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});

    checkLoopScript();
    expect(mockWarn).toHaveBeenCalledWith(expect.stringContaining('version mismatch'));

    mockWarn.mockRestore();
  });
});
```

**Step 2: Run tests to verify they pass**

Run: `npm test --prefix src -- --testPathPattern=run.test`
Expected: PASS

**Step 3: Commit**

```bash
git add src/lib/run.js src/lib/__tests__/run.test.js
git commit -m "test: add checkLoopScript tests for missing script and version mismatch"
```

---

### Task 4: Create cleanup.test.js

- [x] Create unit tests for cleanup.js with spawn mocks

**Files:**
- Create: `src/lib/__tests__/cleanup.test.js`

**Step 1: Write the tests**

```js
const fs = require('fs');
const path = require('path');
const os = require('os');

jest.mock('child_process', () => ({
  spawn: jest.fn(),
}));

const { spawn } = require('child_process');
const { cleanup } = require('../cleanup');

describe('cleanup', () => {
  let tmpDir, origCwd;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cleanup-test-'));
    origCwd = process.cwd();
    process.chdir(tmpDir);
    jest.clearAllMocks();
  });

  afterEach(() => {
    process.chdir(origCwd);
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('exits with code 1 when cleanup.sh is missing', () => {
    const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {
      throw new Error('process.exit');
    });
    const mockError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => cleanup()).toThrow('process.exit');
    expect(mockExit).toHaveBeenCalledWith(1);
    expect(mockError).toHaveBeenCalledWith(expect.stringContaining('cleanup.sh not found'));

    mockExit.mockRestore();
    mockError.mockRestore();
  });

  test('spawns cleanup.sh when it exists', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/cleanup.sh'), '#!/bin/bash\n');

    const mockChild = { on: jest.fn() };
    spawn.mockReturnValue(mockChild);

    const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {});

    cleanup();

    expect(spawn).toHaveBeenCalledWith('./loop/cleanup.sh', [], {
      stdio: 'inherit',
      cwd: process.cwd(),
    });

    // Simulate child close with exit code 0
    const closeHandler = mockChild.on.mock.calls.find(c => c[0] === 'close')[1];
    closeHandler(0);
    expect(mockExit).toHaveBeenCalledWith(0);

    mockExit.mockRestore();
  });

  test('forwards non-zero exit code from child', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/cleanup.sh'), '#!/bin/bash\n');

    const mockChild = { on: jest.fn() };
    spawn.mockReturnValue(mockChild);

    const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {});

    cleanup();

    const closeHandler = mockChild.on.mock.calls.find(c => c[0] === 'close')[1];
    closeHandler(2);
    expect(mockExit).toHaveBeenCalledWith(2);

    mockExit.mockRestore();
  });

  test('uses exit code 0 when child code is null', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/cleanup.sh'), '#!/bin/bash\n');

    const mockChild = { on: jest.fn() };
    spawn.mockReturnValue(mockChild);

    const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {});

    cleanup();

    const closeHandler = mockChild.on.mock.calls.find(c => c[0] === 'close')[1];
    closeHandler(null);
    expect(mockExit).toHaveBeenCalledWith(0);

    mockExit.mockRestore();
  });
});
```

**Step 2: Run tests**

Run: `npm test --prefix src -- --testPathPattern=cleanup.test`
Expected: PASS (4 tests)

**Step 3: Commit**

```bash
git add src/lib/__tests__/cleanup.test.js
git commit -m "test: add cleanup.js unit tests with spawn mocks"
```

---

## Phase 3: Shell Script Tests for cleanup.sh

**Status:** pending

### Task 5: Create test_cleanup.sh

- [ ] Write shell tests for cleanup.sh covering port cleanup and LOOP_PORTS override

**Files:**
- Create: `src/scripts/tests/test_cleanup.sh`

**Step 1: Write the test file**

```bash
#!/bin/bash
set -euo pipefail

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { TESTS_PASSED=$((TESTS_PASSED + 1)); echo -e "${GREEN}PASS${NC}: $1"; }
fail() { TESTS_FAILED=$((TESTS_FAILED + 1)); echo -e "${RED}FAIL${NC}: $1 — $2"; }

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
setup() {
  TEST_DIR=$(mktemp -d)
  mkdir -p "$TEST_DIR/bin"
}

teardown() {
  [[ -n "$TEST_DIR" ]] && rm -rf "$TEST_DIR"
  TEST_DIR=""
}

# ─── Test 1: Uses default ports when LOOP_PORTS is unset ───
setup
# Create mock lsof that reports nothing occupied
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$TEST_DIR/bin/lsof"

cat > "$TEST_DIR/bin/fuser" << 'MOCK'
#!/bin/bash
echo "fuser called with $*" >> "$TEST_DIR/fuser_calls.txt"
MOCK
chmod +x "$TEST_DIR/bin/fuser"
export TEST_DIR

output=$(unset LOOP_PORTS; PATH="$TEST_DIR/bin:$PATH" bash "$CLEANUP_SCRIPT" 2>&1) || true
assert_not_contains "$output" "Released port" "No ports released when lsof reports nothing"
teardown

# ─── Test 2: Releases port when lsof reports occupied ───
setup
# Mock lsof to report port 3000 as occupied
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
[[ "$*" == *":3000" ]] && exit 0
exit 1
MOCK
chmod +x "$TEST_DIR/bin/lsof"

FUSER_LOG="$TEST_DIR/fuser_calls.txt"
cat > "$TEST_DIR/bin/fuser" << MOCK
#!/bin/bash
echo "\$*" >> "$FUSER_LOG"
MOCK
chmod +x "$TEST_DIR/bin/fuser"

output=$(PATH="$TEST_DIR/bin:$PATH" bash "$CLEANUP_SCRIPT" 2>&1) || true
assert_contains "$output" "Released port 3000" "Reports released port 3000"
# fuser should have been called
if [[ -f "$FUSER_LOG" ]]; then
  fuser_args=$(cat "$FUSER_LOG")
  assert_contains "$fuser_args" "3000/tcp" "Calls fuser with 3000/tcp"
else
  TESTS_RUN=$((TESTS_RUN + 1))
  fail "fuser call check" "fuser was not called"
fi
teardown

# ─── Test 3: Respects LOOP_PORTS override ───
setup
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$TEST_DIR/bin/lsof"

FUSER_LOG="$TEST_DIR/fuser_calls.txt"
cat > "$TEST_DIR/bin/fuser" << MOCK
#!/bin/bash
echo "\$*" >> "$FUSER_LOG"
MOCK
chmod +x "$TEST_DIR/bin/fuser"

output=$(LOOP_PORTS="9090 9091" PATH="$TEST_DIR/bin:$PATH" bash "$CLEANUP_SCRIPT" 2>&1) || true
assert_contains "$output" "Released port 9090" "Releases custom port 9090"
assert_contains "$output" "Released port 9091" "Releases custom port 9091"
assert_not_contains "$output" "Released port 3000" "Does not touch default port 3000"
teardown

# ─── Test 4: Handles fuser failure gracefully ───
setup
cat > "$TEST_DIR/bin/lsof" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$TEST_DIR/bin/lsof"

cat > "$TEST_DIR/bin/fuser" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$TEST_DIR/bin/fuser"

# Should not crash (|| true in cleanup.sh)
exit_code=0
output=$(LOOP_PORTS="3000" PATH="$TEST_DIR/bin:$PATH" bash "$CLEANUP_SCRIPT" 2>&1) || exit_code=$?
assert_eq "0" "$exit_code" "Does not crash when fuser fails"
teardown

# ─── Summary ───
echo ""
echo "cleanup.sh tests: $TESTS_RUN total, $TESTS_PASSED passed, $TESTS_FAILED failed"
[[ "$TESTS_FAILED" -eq 0 ]] || exit 1
```

**Step 2: Run tests**

Run: `bash src/scripts/tests/test_cleanup.sh`
Expected: PASS (7 tests, 0 failed)

**Step 3: Commit**

```bash
git add src/scripts/tests/test_cleanup.sh
git commit -m "test: add shell tests for cleanup.sh port cleanup"
```

---

### Task 6: Verify all existing tests still pass

- [ ] Run full test suite to confirm no regressions

**Step 1: Run all JS tests**

Run: `npm test --prefix src`
Expected: PASS (all tests including new ones from Phases 1-3)

**Step 2: Run all shell tests**

Run: `bash src/scripts/tests/test_write_idea.sh && bash src/scripts/tests/test_check_completion.sh && bash src/scripts/tests/test_ensure_playwright.sh && bash src/scripts/tests/test_cleanup.sh`
Expected: All pass

**Step 3: Commit** (only if any fixups needed)

---

## Phase 4: summary.js Edge Case Tests

**Status:** pending

### Task 7: Test parseLog fallback paths

- [ ] Test unknown tool name, missing file_path, non-array content, and empty file

**Files:**
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the tests**

Add to the `parseLog` describe block in `src/lib/__tests__/summary.test.js`:

```js
  test('uses "unknown" for tool_use blocks with no name', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.toolUsage).toEqual({ unknown: 1 });
  });

  test('ignores Edit/Write without file_path in input', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Edit', input: {} },
            { type: 'tool_use', name: 'Write' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.toolUsage).toEqual({ Edit: 1, Write: 1 });
    expect(metrics.filesModified).toEqual([]);
  });

  test('skips assistant entries where content is not an array', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: { content: 'just a string' },
      },
      {
        type: 'result',
        usage: { input_tokens: 5, output_tokens: 3 },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.toolUsage).toEqual({});
    expect(metrics.tokens).toEqual({ input: 5, output: 3 });
  });

  test('handles empty JSONL file', async () => {
    const filePath = path.join(tmpDir, 'empty.jsonl');
    fs.writeFileSync(filePath, '');

    const metrics = await parseLog(filePath);
    expect(metrics.toolUsage).toEqual({});
    expect(metrics.filesModified).toEqual([]);
    expect(metrics.tokens).toEqual({ input: 0, output: 0 });
    expect(metrics.testResults).toEqual([]);
  });

  test('handles result entry with partial usage fields', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 100 } },
      { type: 'result', usage: { output_tokens: 50 } },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.tokens).toEqual({ input: 100, output: 50 });
  });

  test('extracts test results from multiple assistant messages', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: 'Tests: 10 passed, 0 failed, 10 total' },
          ],
        },
      },
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: 'Tests: 5 passed, 1 failed, 6 total' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.testResults).toHaveLength(2);
    expect(metrics.testResults[0]).toEqual({ passed: 10, failed: 0, total: 10 });
    expect(metrics.testResults[1]).toEqual({ passed: 5, failed: 1, total: 6 });
  });
```

**Step 2: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 3: Commit**

```bash
git add src/lib/__tests__/summary.test.js
git commit -m "test: add parseLog edge case tests for fallback paths"
```

---

### Task 8: Test formatSummary percentage and Total line

- [ ] Test tool usage percentage calculation and token Total line

**Files:**
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the tests**

Add to the `formatSummary` describe block:

```js
  test('shows correct percentage for tool usage', () => {
    const metrics = {
      toolUsage: { Read: 3, Edit: 1 },
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Read: 3 (75%)');
    expect(output).toContain('Edit: 1 (25%)');
  });

  test('shows token Total line', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 1000, output: 500 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Total:  1,500');
  });

  test('shows multiple test result entries', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [
        { passed: 10, failed: 0, total: 10 },
        { passed: 5, failed: 2, total: 7 },
      ],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('PASS: 10 passed, 0 failed (10 total)');
    expect(output).toContain('FAIL: 5 passed, 2 failed (7 total)');
  });
```

**Step 2: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 3: Commit**

```bash
git add src/lib/__tests__/summary.test.js
git commit -m "test: add formatSummary percentage and Total line assertions"
```

---

## Phase 5: loop doctor - Core Module

**Status:** pending

### Task 9: Create doctor.js with check runner framework

- [ ] Create doctor module with health check functions and CLI registration

**Files:**
- Create: `src/lib/doctor.js`
- Modify: `src/bin/cli.js`

**Step 1: Write the failing test first**

Create `src/lib/__tests__/doctor.test.js`:

```js
const fs = require('fs');
const path = require('path');
const os = require('os');
const { runChecks, checks } = require('../doctor');

describe('doctor checks', () => {
  let tmpDir, origCwd;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'doctor-test-'));
    origCwd = process.cwd();
    process.chdir(tmpDir);
  });

  afterEach(() => {
    process.chdir(origCwd);
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('exports runChecks as a function', () => {
    expect(typeof runChecks).toBe('function');
  });

  test('exports checks as an array', () => {
    expect(Array.isArray(checks)).toBe(true);
    expect(checks.length).toBeGreaterThan(0);
  });

  test('loop symlink check fails when loop/loop.sh is missing', () => {
    const check = checks.find(c => c.name === 'Loop symlinks');
    const result = check.fn();
    expect(result.ok).toBe(false);
    expect(result.message).toContain('missing');
  });

  test('loop symlink check passes when all symlinks exist', () => {
    // Create all expected symlinks as regular files (sufficient for existence check)
    const symlinks = ['loop.sh', 'PROMPT_design.md', 'PROMPT_plan.md', 'PROMPT_build.md', 'cleanup.sh', 'kill-loop.sh'];
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    for (const f of symlinks) {
      fs.writeFileSync(path.join(tmpDir, 'loop', f), '');
    }
    const check = checks.find(c => c.name === 'Loop symlinks');
    const result = check.fn();
    expect(result.ok).toBe(true);
  });

  test('version check fails on mismatch', () => {
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/.version'), '0.0.0\n');

    const check = checks.find(c => c.name === 'Loop version');
    const result = check.fn();
    expect(result.ok).toBe(false);
    expect(result.fix).toContain('loop update');
  });

  test('version check passes on match', () => {
    const pkgVersion = require('../../package.json').version;
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'loop/.version'), pkgVersion + '\n');

    const check = checks.find(c => c.name === 'Loop version');
    const result = check.fn();
    expect(result.ok).toBe(true);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=doctor.test`
Expected: FAIL — `Cannot find module '../doctor'`

**Step 3: Write the implementation**

Create `src/lib/doctor.js`:

```js
const fs = require('fs');
const { execSync } = require('child_process');

const SYMLINK_FILES = ['loop.sh', 'PROMPT_design.md', 'PROMPT_plan.md', 'PROMPT_build.md', 'cleanup.sh', 'kill-loop.sh'];

const checks = [
  {
    name: 'Loop symlinks',
    fn() {
      const missing = SYMLINK_FILES.filter(f => !fs.existsSync(`./loop/${f}`));
      if (missing.length > 0) {
        return { ok: false, message: `${missing.length} missing: ${missing.join(', ')}`, fix: 'Run "loop init" to create symlinks' };
      }
      return { ok: true, message: `${SYMLINK_FILES.length} files present` };
    },
  },
  {
    name: 'Loop version',
    fn() {
      const versionPath = './loop/.version';
      if (!fs.existsSync(versionPath)) {
        return { ok: false, message: '.version file missing', fix: 'Run "loop init"' };
      }
      const fileVersion = fs.readFileSync(versionPath, 'utf-8').trim();
      const pkgVersion = require('../package.json').version;
      if (fileVersion !== pkgVersion) {
        return { ok: false, message: `project: ${fileVersion}, installed: ${pkgVersion}`, fix: 'Run "loop update" to refresh' };
      }
      return { ok: true, message: `v${pkgVersion}` };
    },
  },
  {
    name: 'Claude CLI',
    fn() {
      try {
        const version = execSync('claude --version 2>/dev/null', { encoding: 'utf-8', timeout: 5000 }).trim();
        return { ok: true, message: version };
      } catch {
        // Also check ~/.claude/bin/claude
        const homeClaude = `${process.env.HOME}/.claude/bin/claude`;
        if (fs.existsSync(homeClaude)) {
          return { ok: true, message: `found at ${homeClaude}` };
        }
        return { ok: false, message: 'not found in PATH or ~/.claude/bin/', fix: 'Install Claude CLI: https://docs.anthropic.com/en/docs/claude-code' };
      }
    },
  },
  {
    name: 'Git repository',
    fn() {
      try {
        execSync('git rev-parse --is-inside-work-tree 2>/dev/null', { encoding: 'utf-8', timeout: 5000 });
        return { ok: true, message: 'inside git repo' };
      } catch {
        return { ok: false, message: 'not a git repository', fix: 'Run "git init"' };
      }
    },
  },
  {
    name: 'jq binary',
    fn() {
      try {
        execSync('jq --version 2>/dev/null', { encoding: 'utf-8', timeout: 5000 });
        return { ok: true, message: 'available' };
      } catch {
        return { ok: false, message: 'not found', fix: 'Install jq: apt-get install jq / brew install jq' };
      }
    },
  },
  {
    name: 'GH_TOKEN',
    fn() {
      if (process.env.GH_TOKEN) {
        return { ok: true, message: 'set' };
      }
      return { ok: false, message: 'not set', fix: 'Set GH_TOKEN env var with a GitHub PAT (repo, workflow scopes)' };
    },
  },
];

function runChecks() {
  const results = [];

  for (const check of checks) {
    try {
      const result = check.fn();
      results.push({ name: check.name, ...result });
    } catch (err) {
      results.push({ name: check.name, ok: false, message: err.message });
    }
  }

  return results;
}

function formatResults(results) {
  const lines = [];
  lines.push('=== Loop Doctor ===');
  lines.push('');

  let passed = 0;
  let failed = 0;

  for (const r of results) {
    const icon = r.ok ? '[OK]' : '[FAIL]';
    lines.push(`${icon}  ${r.name}: ${r.message}`);
    if (!r.ok && r.fix) {
      lines.push(`      Fix: ${r.fix}`);
    }
    if (r.ok) passed++;
    else failed++;
  }

  lines.push('');
  lines.push(`${passed} passed, ${failed} failed`);

  return lines.join('\n');
}

function doctor() {
  const results = runChecks();
  console.log(formatResults(results));
  process.exit(results.every(r => r.ok) ? 0 : 1);
}

module.exports = { doctor, runChecks, checks, formatResults };
```

**Step 4: Register in cli.js**

Add to `src/bin/cli.js` after the `update` command registration:

```js
const { doctor } = require('../lib/doctor');
```

```js
program
  .command('doctor')
  .description('Check loop installation health')
  .action(() => doctor());
```

Add to the help text examples: `  $ loop doctor            Check loop installation health`

**Step 5: Run tests**

Run: `npm test --prefix src -- --testPathPattern=doctor.test`
Expected: PASS (6 tests)

**Step 6: Commit**

```bash
git add src/lib/doctor.js src/lib/__tests__/doctor.test.js src/bin/cli.js
git commit -m "feat: add loop doctor command with core health checks"
```

---

### Task 10: Doctor integration test

- [ ] Add integration test that runs doctor in a real temp project

**Files:**
- Modify: `src/lib/__tests__/integration.test.js`

**Step 1: Write the integration test**

Add a new describe block at the end of `src/lib/__tests__/integration.test.js`:

```js
const { runChecks } = require('../doctor');

describe('loop doctor (integration)', () => {
  let project;

  beforeEach(() => {
    project = useTempProject();
  });

  afterEach(() => {
    project.restore();
  });

  test('symlink check fails before init', () => {
    const results = runChecks();
    const symCheck = results.find(r => r.name === 'Loop symlinks');
    expect(symCheck.ok).toBe(false);
  });

  test('symlink and version checks pass after init', () => {
    init();
    const results = runChecks();
    const symCheck = results.find(r => r.name === 'Loop symlinks');
    const verCheck = results.find(r => r.name === 'Loop version');
    expect(symCheck.ok).toBe(true);
    expect(verCheck.ok).toBe(true);
  });
}, 30000);
```

**Step 2: Run tests**

Run: `npm test --prefix src -- --testPathPattern=integration.test`
Expected: PASS

**Step 3: Commit**

```bash
git add src/lib/__tests__/integration.test.js
git commit -m "test: add doctor integration tests with init"
```

---

## Phase 6: Enhanced Summary - File Edit Frequency

**Status:** pending

### Task 11: Track per-file edit counts in parseLog

- [ ] Add fileEditCounts tracking to parseLog and test it

**Files:**
- Modify: `src/lib/summary.js:30-92`
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the failing test**

Add to the `parseLog` describe block in `summary.test.js`:

```js
  test('tracks per-file edit counts', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Edit', input: { file_path: '/src/app.js' } },
            { type: 'tool_use', name: 'Write', input: { file_path: '/src/app.js' } },
            { type: 'tool_use', name: 'Edit', input: { file_path: '/src/utils.js' } },
          ],
        },
      },
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Edit', input: { file_path: '/src/app.js' } },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.fileEditCounts).toEqual({
      '/src/app.js': 3,
      '/src/utils.js': 1,
    });
  });

  test('fileEditCounts is empty when no Edit/Write tools used', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: { content: [{ type: 'tool_use', name: 'Read' }] },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.fileEditCounts).toEqual({});
  });
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: FAIL — `metrics.fileEditCounts` is `undefined`

**Step 3: Implement**

In `src/lib/summary.js` `parseLog()`, add `fileEditCounts` map:

After line 32 (`const filesModified = new Set();`), add:
```js
  const fileEditCounts = {};
```

Inside the `Edit`/`Write` file_path block (after line 61), add:
```js
            fileEditCounts[block.input.file_path] = (fileEditCounts[block.input.file_path] || 0) + 1;
```

In the return object (line 85-91), add `fileEditCounts`:
```js
  return {
    toolUsage,
    filesModified: [...filesModified].sort(),
    fileEditCounts,
    tokens: { input: inputTokens, output: outputTokens },
    testResults,
    logFile: logPath,
  };
```

**Step 4: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/summary.js src/lib/__tests__/summary.test.js
git commit -m "feat: track per-file edit counts in parseLog"
```

---

### Task 12: Display most-edited files in formatSummary

- [ ] Add "Most Edited Files" section to formatSummary showing top 5 files

**Files:**
- Modify: `src/lib/summary.js:123-176`
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the failing test**

Add to the `formatSummary` describe block:

```js
  test('shows Most Edited Files section sorted by count', () => {
    const metrics = {
      toolUsage: {},
      filesModified: ['/a.js', '/b.js', '/c.js'],
      fileEditCounts: { '/a.js': 5, '/b.js': 1, '/c.js': 3 },
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Most Edited Files:');
    // Should be sorted by count descending
    const aIdx = output.indexOf('/a.js');
    const cIdx = output.indexOf('/c.js');
    const bIdx = output.indexOf('/b.js');
    expect(aIdx).toBeLessThan(cIdx);
    expect(cIdx).toBeLessThan(bIdx);
    expect(output).toContain('/a.js (5 edits)');
  });

  test('limits Most Edited Files to top 5', () => {
    const fileEditCounts = {};
    const filesModified = [];
    for (let i = 1; i <= 8; i++) {
      const f = `/src/file${i}.js`;
      fileEditCounts[f] = i;
      filesModified.push(f);
    }
    const metrics = {
      toolUsage: {},
      filesModified,
      fileEditCounts,
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('/src/file8.js');
    expect(output).toContain('/src/file4.js');
    expect(output).not.toContain('/src/file3.js (3 edits)');
  });

  test('omits Most Edited Files when fileEditCounts is empty', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      fileEditCounts: {},
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).not.toContain('Most Edited');
  });
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: FAIL — no "Most Edited Files" section in output

**Step 3: Implement**

In `src/lib/summary.js` `formatSummary()`, add after the "Files Modified" section (after line 150):

```js
  // Most Edited Files (top 5 by edit count)
  if (metrics.fileEditCounts && Object.keys(metrics.fileEditCounts).length > 0) {
    const sorted = Object.entries(metrics.fileEditCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);
    lines.push('Most Edited Files:');
    for (const [file, count] of sorted) {
      lines.push(`  ${file} (${count} edits)`);
    }
    lines.push('');
  }
```

**Step 4: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/summary.js src/lib/__tests__/summary.test.js
git commit -m "feat: add Most Edited Files section to loop summary"
```

---

## Phase 7: Enhanced Summary - Iteration Timing & Error Rates

**Status:** pending

### Task 13: Track iteration timing from JSONL timestamps

- [ ] Parse result entry timestamps to calculate iteration duration and total time

**Files:**
- Modify: `src/lib/summary.js:30-92`
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the failing test**

Add to the `parseLog` describe block:

```js
  test('tracks iteration count from result entries', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 100, output_tokens: 50 }, timestamp: '2026-03-03T10:00:00Z' },
      { type: 'result', usage: { input_tokens: 200, output_tokens: 75 }, timestamp: '2026-03-03T10:05:00Z' },
      { type: 'result', usage: { input_tokens: 150, output_tokens: 60 }, timestamp: '2026-03-03T10:12:00Z' },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.iterationCount).toBe(3);
    expect(metrics.totalTimeMs).toBeGreaterThan(0);
  });

  test('tracks error count from result entries with is_error', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 100, output_tokens: 50 } },
      { type: 'result', usage: { input_tokens: 100, output_tokens: 50 }, is_error: true },
      { type: 'result', usage: { input_tokens: 100, output_tokens: 50 }, is_error: true },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.errorCount).toBe(2);
    expect(metrics.iterationCount).toBe(3);
  });

  test('handles log with no result entries for timing', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'assistant', message: { content: [{ type: 'tool_use', name: 'Read' }] } },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.iterationCount).toBe(0);
    expect(metrics.totalTimeMs).toBe(0);
    expect(metrics.errorCount).toBe(0);
  });
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: FAIL — `metrics.iterationCount` is `undefined`

**Step 3: Implement**

In `src/lib/summary.js` `parseLog()`, add tracking variables after `const testResults = [];` (line 35):

```js
  let iterationCount = 0;
  let errorCount = 0;
  let firstTimestamp = null;
  let lastTimestamp = null;
```

Inside the `result` entry block (after line 70), add:

```js
      iterationCount++;
      if (entry.is_error) errorCount++;
      if (entry.timestamp) {
        const ts = new Date(entry.timestamp).getTime();
        if (!isNaN(ts)) {
          if (firstTimestamp === null) firstTimestamp = ts;
          lastTimestamp = ts;
        }
      }
```

In the return object, add:

```js
    iterationCount,
    errorCount,
    totalTimeMs: (firstTimestamp && lastTimestamp) ? lastTimestamp - firstTimestamp : 0,
```

**Step 4: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/summary.js src/lib/__tests__/summary.test.js
git commit -m "feat: track iteration count, timing, and errors in parseLog"
```

---

### Task 14: Display timing and error rate in formatSummary

- [ ] Add Iteration Stats section showing count, duration, and error rate

**Files:**
- Modify: `src/lib/summary.js:123-176`
- Modify: `src/lib/__tests__/summary.test.js`

**Step 1: Write the failing test**

Add to the `formatSummary` describe block:

```js
  test('shows Iterations section with count and duration', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      fileEditCounts: {},
      tokens: { input: 0, output: 0 },
      testResults: [],
      iterationCount: 5,
      totalTimeMs: 720000,  // 12 minutes
      errorCount: 0,
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Iterations: 5');
    expect(output).toContain('Duration: 12m');
  });

  test('shows error rate when errors exist', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      fileEditCounts: {},
      tokens: { input: 0, output: 0 },
      testResults: [],
      iterationCount: 10,
      totalTimeMs: 600000,
      errorCount: 3,
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Errors: 3/10 (30%)');
  });

  test('omits Iterations section when count is 0', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      fileEditCounts: {},
      tokens: { input: 0, output: 0 },
      testResults: [],
      iterationCount: 0,
      totalTimeMs: 0,
      errorCount: 0,
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).not.toContain('Iterations:');
  });
```

**Step 2: Run test to verify it fails**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: FAIL — no "Iterations" section in output

**Step 3: Implement**

In `src/lib/summary.js` `formatSummary()`, add after the header (after line 126 `lines.push('');`):

```js
  // Iteration Stats
  if (metrics.iterationCount > 0) {
    lines.push(`Iterations: ${metrics.iterationCount}`);
    if (metrics.totalTimeMs > 0) {
      const mins = Math.round(metrics.totalTimeMs / 60000);
      lines.push(`Duration: ${mins}m`);
    }
    if (metrics.errorCount > 0) {
      const pct = Math.round((metrics.errorCount / metrics.iterationCount) * 100);
      lines.push(`Errors: ${metrics.errorCount}/${metrics.iterationCount} (${pct}%)`);
    }
    lines.push('');
  }
```

**Step 4: Run tests**

Run: `npm test --prefix src -- --testPathPattern=summary.test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/summary.js src/lib/__tests__/summary.test.js
git commit -m "feat: add iteration stats and error rate to loop summary"
```

---

## Phase 8: Version Bump & Integration Verification

**Status:** pending

### Task 15: Update integration tests for new summary fields

- [ ] Update integration test realistic JSONL to verify new metrics fields

**Files:**
- Modify: `src/lib/__tests__/integration.test.js`

**Step 1: Update the integration test**

In the `produces formatted report from a realistic JSONL log` test, add assertions for new fields:

```js
    // Iteration stats (2 result entries)
    expect(report).toContain('Iterations: 2');
```

Also add a new test for the doctor command help text:

```js
  test('doctor command is registered in CLI', () => {
    const { execSync } = require('child_process');
    const help = execSync('node ' + path.join(PACKAGE_ROOT, 'bin/cli.js') + ' --help', { encoding: 'utf-8' });
    expect(help).toContain('doctor');
  });
```

**Step 2: Run tests**

Run: `npm test --prefix src`
Expected: PASS (all tests)

**Step 3: Commit**

```bash
git add src/lib/__tests__/integration.test.js
git commit -m "test: update integration tests for new summary fields and doctor command"
```

---

### Task 16: Bump version and run full validation

- [ ] Bump package version to 0.8.0 and run all tests

**Files:**
- Modify: `src/package.json:3` (version)

**Step 1: Bump version**

Change `"version": "0.7.3"` to `"version": "0.8.0"` in `src/package.json`.

**Step 2: Run all JS tests**

Run: `npm test --prefix src`
Expected: PASS (all ~45+ tests)

**Step 3: Run all shell tests**

Run: `bash src/scripts/tests/test_write_idea.sh && bash src/scripts/tests/test_check_completion.sh && bash src/scripts/tests/test_ensure_playwright.sh && bash src/scripts/tests/test_cleanup.sh`
Expected: All pass

**Step 4: Run integration tests separately**

Run: `npm run test:integration --prefix src`
Expected: PASS

**Step 5: Commit**

```bash
git add src/package.json
git commit -m "chore: bump dev-loop version to 0.8.0"
```
