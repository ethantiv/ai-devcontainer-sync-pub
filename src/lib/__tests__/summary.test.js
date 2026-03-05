/**
 * Tests for summary.js — log parsing, test result extraction, summary formatting.
 */

const fs = require('fs');
const path = require('path');
const { parseLog, findLatestLog, formatSummary } = require('../summary');

// Helper: write JSONL lines to a temp file
function writeJsonl(dir, filename, entries) {
  const filePath = path.join(dir, filename);
  const content = entries.map(e => JSON.stringify(e)).join('\n') + '\n';
  fs.writeFileSync(filePath, content);
  return filePath;
}

describe('findLatestLog', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'summary-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('returns null for nonexistent directory', () => {
    expect(findLatestLog('/nonexistent/dir/abc123')).toBeNull();
  });

  test('returns null for empty directory', () => {
    expect(findLatestLog(tmpDir)).toBeNull();
  });

  test('returns null when no .jsonl files exist', () => {
    fs.writeFileSync(path.join(tmpDir, 'notes.txt'), 'hello');
    expect(findLatestLog(tmpDir)).toBeNull();
  });

  test('returns the most recently modified .jsonl file', () => {
    // Create two files with different mtimes
    const older = path.join(tmpDir, 'older.jsonl');
    const newer = path.join(tmpDir, 'newer.jsonl');
    fs.writeFileSync(older, '{}');
    // Set older file to past mtime
    const past = new Date(Date.now() - 10000);
    fs.utimesSync(older, past, past);
    fs.writeFileSync(newer, '{}');

    const result = findLatestLog(tmpDir);
    expect(result).toBe(newer);
  });
});

describe('parseLog', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'summary-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('counts tool usage from assistant messages', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Read' },
            { type: 'tool_use', name: 'Edit' },
            { type: 'tool_use', name: 'Read' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.toolUsage).toEqual({ Read: 2, Edit: 1 });
  });

  test('tracks files modified by Edit and Write tools', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Edit', input: { file_path: '/src/foo.py' } },
            { type: 'tool_use', name: 'Write', input: { file_path: '/src/bar.py' } },
            { type: 'tool_use', name: 'Read', input: { file_path: '/src/baz.py' } },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.filesModified).toEqual(['/src/bar.py', '/src/foo.py']);
  });

  test('accumulates token usage from result entries', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 100, output_tokens: 50 } },
      { type: 'result', usage: { input_tokens: 200, output_tokens: 75 } },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.tokens).toEqual({ input: 300, output: 125, cacheRead: 0, cacheCreate: 0 });
  });

  test('skips malformed JSON lines', async () => {
    const filePath = path.join(tmpDir, 'bad.jsonl');
    fs.writeFileSync(filePath, 'not json\n{"type":"result","usage":{"input_tokens":10,"output_tokens":5}}\n');

    const metrics = await parseLog(filePath);
    expect(metrics.tokens).toEqual({ input: 10, output: 5, cacheRead: 0, cacheCreate: 0 });
  });

  test('skips empty lines', async () => {
    const filePath = path.join(tmpDir, 'empty.jsonl');
    fs.writeFileSync(filePath, '\n\n{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n\n');

    const metrics = await parseLog(filePath);
    expect(metrics.tokens).toEqual({ input: 1, output: 1, cacheRead: 0, cacheCreate: 0 });
  });

  test('extracts Jest test results from tool output', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: 'Tests: 10 passed, 2 failed, 12 total' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.testResults).toEqual([
      { passed: 10, failed: 2, total: 12 },
    ]);
  });

  test('extracts pytest results from tool output', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: '20 passed, 3 failed' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.testResults).toEqual([
      { passed: 20, failed: 3, total: 23 },
    ]);
  });

  test('extracts pytest passed-only results', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: '15 passed' },
          ],
        },
      },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.testResults).toEqual([
      { passed: 15, failed: 0, total: 15 },
    ]);
  });

  test('returns logFile path in metrics', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', []);
    const metrics = await parseLog(logPath);
    expect(metrics.logFile).toBe(logPath);
  });

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
    expect(metrics.tokens).toEqual({ input: 5, output: 3, cacheRead: 0, cacheCreate: 0 });
  });

  test('handles empty JSONL file', async () => {
    const filePath = path.join(tmpDir, 'empty.jsonl');
    fs.writeFileSync(filePath, '');

    const metrics = await parseLog(filePath);
    expect(metrics.toolUsage).toEqual({});
    expect(metrics.filesModified).toEqual([]);
    expect(metrics.tokens).toEqual({ input: 0, output: 0, cacheRead: 0, cacheCreate: 0 });
    expect(metrics.testResults).toEqual([]);
  });

  test('handles result entry with partial usage fields', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 100 } },
      { type: 'result', usage: { output_tokens: 50 } },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.tokens).toEqual({ input: 100, output: 50, cacheRead: 0, cacheCreate: 0 });
  });

  test('accumulates cache token usage from result entries', async () => {
    const logPath = writeJsonl(tmpDir, 'test.jsonl', [
      { type: 'result', usage: { input_tokens: 10, output_tokens: 50, cache_read_input_tokens: 5000, cache_creation_input_tokens: 200 } },
      { type: 'result', usage: { input_tokens: 20, output_tokens: 75, cache_read_input_tokens: 8000, cache_creation_input_tokens: 300 } },
    ]);

    const metrics = await parseLog(logPath);
    expect(metrics.tokens).toEqual({ input: 30, output: 125, cacheRead: 13000, cacheCreate: 500 });
  });

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
});

describe('formatSummary', () => {
  test('includes tool usage section', () => {
    const metrics = {
      toolUsage: { Read: 5, Edit: 3 },
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Tool Usage:');
    expect(output).toContain('Read: 5');
    expect(output).toContain('Edit: 3');
    expect(output).toContain('Total: 8 calls');
  });

  test('includes files modified section', () => {
    const metrics = {
      toolUsage: {},
      filesModified: ['/src/a.py', '/src/b.py'],
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Files Modified (2):');
    expect(output).toContain('/src/a.py');
  });

  test('includes test results section', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [{ passed: 10, failed: 0, total: 10 }],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Test Results:');
    expect(output).toContain('PASS');
  });

  test('shows FAIL for failed tests', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [{ passed: 8, failed: 2, total: 10 }],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('FAIL');
  });

  test('includes token usage section', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 1000, output: 500 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Token Usage:');
    expect(output).toContain('1,000');
  });

  test('includes log file reference', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/my-log.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Log: /tmp/my-log.jsonl');
  });

  test('omits empty sections', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 0, output: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).not.toContain('Tool Usage:');
    expect(output).not.toContain('Files Modified');
    expect(output).not.toContain('Token Usage:');
    expect(output).not.toContain('Test Results:');
  });

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

  test('shows cache token breakdown when cache tokens exist', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 100, output: 500, cacheRead: 9000, cacheCreate: 900 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Input:  10,000');
    expect(output).toContain('Cache read:    9,000 (90%)');
    expect(output).toContain('Cache create:  900');
    expect(output).toContain('Uncached:      100');
    expect(output).toContain('Output: 500');
    expect(output).toContain('Total:  10,500');
  });

  test('omits cache breakdown when no cache tokens', () => {
    const metrics = {
      toolUsage: {},
      filesModified: [],
      tokens: { input: 1000, output: 500, cacheRead: 0, cacheCreate: 0 },
      testResults: [],
      logFile: '/tmp/test.jsonl',
    };
    const output = formatSummary(metrics);
    expect(output).toContain('Input:  1,000');
    expect(output).not.toContain('Cache read');
    expect(output).not.toContain('Uncached');
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
    // Should be sorted by count descending — use "(N edits)" format to match
    // only in the Most Edited Files section (not in Files Modified)
    const aIdx = output.indexOf('/a.js (5 edits)');
    const cIdx = output.indexOf('/c.js (3 edits)');
    const bIdx = output.indexOf('/b.js (1 edit)');
    expect(aIdx).toBeGreaterThan(-1);
    expect(cIdx).toBeGreaterThan(-1);
    expect(bIdx).toBeGreaterThan(-1);
    expect(aIdx).toBeLessThan(cIdx);
    expect(cIdx).toBeLessThan(bIdx);
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
    expect(output).toContain('/src/file8.js (8 edits)');
    expect(output).toContain('/src/file4.js (4 edits)');
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
});
