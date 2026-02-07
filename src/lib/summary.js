const fs = require('fs');
const path = require('path');
const readline = require('readline');

/**
 * Find the most recent .jsonl log file in logDir.
 * Returns absolute path or null if none found.
 */
function findLatestLog(logDir) {
  const absDir = path.resolve(logDir);
  if (!fs.existsSync(absDir)) return null;

  const files = fs.readdirSync(absDir)
    .filter(f => f.endsWith('.jsonl'))
    .map(f => ({ name: f, mtime: fs.statSync(path.join(absDir, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);

  return files.length > 0 ? path.join(absDir, files[0].name) : null;
}

/**
 * Parse a JSONL log file and extract summary metrics.
 *
 * Extracts:
 * - toolUsage: map of tool name → call count
 * - filesModified: set of file paths from Edit/Write tool inputs
 * - tokens: { input, output } totals from "result" entries with usage
 * - testResults: array of { passed, failed, total } from Bash tool output
 */
async function parseLog(logPath) {
  const toolUsage = {};
  const filesModified = new Set();
  let inputTokens = 0;
  let outputTokens = 0;
  const testResults = [];

  const rl = readline.createInterface({
    input: fs.createReadStream(logPath),
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (!line.trim()) continue;

    let entry;
    try {
      entry = JSON.parse(line);
    } catch {
      continue;
    }

    // Count tool uses from assistant messages
    if (entry.type === 'assistant' && Array.isArray(entry.message?.content)) {
      for (const block of entry.message.content) {
        if (block.type === 'tool_use') {
          const name = block.name || 'unknown';
          toolUsage[name] = (toolUsage[name] || 0) + 1;

          // Track files modified by Edit/Write tools
          if ((name === 'Edit' || name === 'Write') && block.input?.file_path) {
            filesModified.add(block.input.file_path);
          }
        }
      }
    }

    // Extract token usage from result entries
    if (entry.type === 'result' && entry.usage) {
      inputTokens += entry.usage.input_tokens || 0;
      outputTokens += entry.usage.output_tokens || 0;
    }

    // Extract test results from tool_result content (Bash output)
    if (entry.type === 'assistant' && Array.isArray(entry.message?.content)) {
      for (const block of entry.message.content) {
        if (block.type === 'tool_result' || block.type === 'text') {
          const text = typeof block.text === 'string' ? block.text :
                       typeof block.content === 'string' ? block.content : '';
          extractTestResults(text, testResults);
        }
      }
    }
  }

  return {
    toolUsage,
    filesModified: [...filesModified].sort(),
    tokens: { input: inputTokens, output: outputTokens },
    testResults,
    logFile: logPath,
  };
}

/**
 * Look for common test framework output patterns in text.
 */
function extractTestResults(text, results) {
  if (!text) return;

  // Jest/Vitest pattern: "Tests: X passed, Y failed, Z total"
  const jestMatch = text.match(/Tests:\s+(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+total)?/i);
  if (jestMatch) {
    results.push({
      passed: parseInt(jestMatch[1], 10),
      failed: parseInt(jestMatch[2] || '0', 10),
      total: parseInt(jestMatch[3] || jestMatch[1], 10),
    });
    return;
  }

  // pytest pattern: "X passed, Y failed" or "X passed"
  const pytestMatch = text.match(/(\d+)\s+passed(?:,\s+(\d+)\s+failed)?/i);
  if (pytestMatch) {
    const passed = parseInt(pytestMatch[1], 10);
    const failed = parseInt(pytestMatch[2] || '0', 10);
    results.push({ passed, failed, total: passed + failed });
  }
}

/**
 * Format summary metrics into a human-readable report string.
 */
function formatSummary(metrics) {
  const lines = [];
  lines.push('=== Loop Run Summary ===');
  lines.push('');

  // Tool Usage
  const sortedTools = Object.entries(metrics.toolUsage)
    .sort(([, a], [, b]) => b - a);

  if (sortedTools.length > 0) {
    lines.push('Tool Usage:');
    const totalCalls = sortedTools.reduce((sum, [, count]) => sum + count, 0);
    for (const [name, count] of sortedTools) {
      const pct = Math.round((count / totalCalls) * 100);
      lines.push(`  ${name}: ${count} (${pct}%)`);
    }
    lines.push(`  Total: ${totalCalls} calls`);
    lines.push('');
  }

  // Files Modified
  if (metrics.filesModified.length > 0) {
    lines.push(`Files Modified (${metrics.filesModified.length}):`);
    for (const f of metrics.filesModified) {
      lines.push(`  ${f}`);
    }
    lines.push('');
  }

  // Test Results
  if (metrics.testResults.length > 0) {
    lines.push('Test Results:');
    for (const r of metrics.testResults) {
      const status = r.failed > 0 ? 'FAIL' : 'PASS';
      lines.push(`  ${status}: ${r.passed} passed, ${r.failed} failed (${r.total} total)`);
    }
    lines.push('');
  }

  // Token Usage
  if (metrics.tokens.input > 0 || metrics.tokens.output > 0) {
    const total = metrics.tokens.input + metrics.tokens.output;
    lines.push('Token Usage:');
    lines.push(`  Input:  ${metrics.tokens.input.toLocaleString()}`);
    lines.push(`  Output: ${metrics.tokens.output.toLocaleString()}`);
    lines.push(`  Total:  ${total.toLocaleString()}`);
    lines.push('');
  }

  // Log file reference
  lines.push(`Log: ${metrics.logFile}`);

  return lines.join('\n');
}

/**
 * Generate a summary report from the latest JSONL log in logDir.
 * Returns the formatted report string, or a message if no logs found.
 */
async function generateSummary(logDir) {
  const logPath = findLatestLog(logDir);
  if (!logPath) {
    return 'No log files found in ' + path.resolve(logDir);
  }

  const metrics = await parseLog(logPath);
  return formatSummary(metrics);
}

module.exports = { generateSummary, parseLog, findLatestLog, formatSummary };
