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
    expect(metrics.tokens).toEqual({ input: 300, output: 125 });
  });

  test('skips malformed JSON lines', async () => {
    const filePath = path.join(tmpDir, 'bad.jsonl');
    fs.writeFileSync(filePath, 'not json\n{"type":"result","usage":{"input_tokens":10,"output_tokens":5}}\n');

    const metrics = await parseLog(filePath);
    expect(metrics.tokens).toEqual({ input: 10, output: 5 });
  });

  test('skips empty lines', async () => {
    const filePath = path.join(tmpDir, 'empty.jsonl');
    fs.writeFileSync(filePath, '\n\n{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n\n');

    const metrics = await parseLog(filePath);
    expect(metrics.tokens).toEqual({ input: 1, output: 1 });
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
});
