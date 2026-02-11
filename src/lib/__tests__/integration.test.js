/**
 * Integration tests for the loop workflow: init, update, and summary.
 *
 * These tests exercise the full module behavior (not mocked internals)
 * by running init() in real temp directories and generateSummary() on
 * real JSONL files. Timeouts are extended because fs operations on
 * overlayfs (Docker) can be slow.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { init } = require('../init');
const { generateSummary } = require('../summary');

const PACKAGE_ROOT = path.resolve(__dirname, '..', '..');

/** Create an isolated temp directory and chdir into it, returning a restore fn. */
function useTempProject() {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'loop-integration-'));
  const origCwd = process.cwd();
  process.chdir(tmpDir);
  return {
    dir: tmpDir,
    restore() {
      process.chdir(origCwd);
      fs.rmSync(tmpDir, { recursive: true, force: true });
    },
  };
}

// Expected symlinks created by init() (src → dest relative to project root)
const EXPECTED_SYMLINKS = [
  'loop/loop.sh',
  'loop/PROMPT_plan.md',
  'loop/PROMPT_build.md',
  'loop/cleanup.sh',
  'loop/notify-telegram.sh',
  'loop/kill-loop.sh',
];

// Expected directories
const EXPECTED_DIRS = [
  'docs/plans',
  'loop/logs',
  '.claude/skills/auto-revise-claude-md',
];

// Expected copied templates
const EXPECTED_TEMPLATES = [
  'CLAUDE_template.md',
  'docs/plans/IMPLEMENTATION_PLAN_template.md',
  '.claude/settings.json',
  '.claude/skills/auto-revise-claude-md/SKILL.md',
  'loop/PROMPT_skills.md',
];

describe('loop init', () => {
  let project;

  beforeEach(() => {
    project = useTempProject();
  });

  afterEach(() => {
    project.restore();
  });

  test('creates expected symlinks pointing back to package source', () => {
    init();

    for (const rel of EXPECTED_SYMLINKS) {
      const full = path.join(project.dir, rel);
      expect(fs.existsSync(full)).toBe(true);

      const stat = fs.lstatSync(full);
      expect(stat.isSymbolicLink()).toBe(true);

      // Symlink target should resolve to the package source file
      const resolved = fs.realpathSync(full);
      expect(resolved.startsWith(PACKAGE_ROOT)).toBe(true);
    }
  });

  test('creates expected directories', () => {
    init();

    for (const dir of EXPECTED_DIRS) {
      const full = path.join(project.dir, dir);
      expect(fs.existsSync(full)).toBe(true);
      expect(fs.statSync(full).isDirectory()).toBe(true);
    }
  });

  test('copies template files (not symlinks)', () => {
    init();

    for (const rel of EXPECTED_TEMPLATES) {
      const srcPath = path.join(PACKAGE_ROOT, templateSrcPath(rel));
      // Template source may not exist (e.g. optional skill files)
      if (!fs.existsSync(srcPath)) continue;

      const full = path.join(project.dir, rel);
      expect(fs.existsSync(full)).toBe(true);

      const stat = fs.lstatSync(full);
      // Templates are copied, not symlinked
      expect(stat.isSymbolicLink()).toBe(false);
      expect(stat.isFile()).toBe(true);
    }
  });

  test('writes loop/.version matching package.json version', () => {
    init();

    const versionPath = path.join(project.dir, 'loop/.version');
    expect(fs.existsSync(versionPath)).toBe(true);

    const version = fs.readFileSync(versionPath, 'utf-8').trim();
    const pkgVersion = require('../../package.json').version;
    expect(version).toBe(pkgVersion);
  });

  test('creates .gitignore with loop/logs/ entry', () => {
    init();

    const gitignore = path.join(project.dir, '.gitignore');
    expect(fs.existsSync(gitignore)).toBe(true);

    const content = fs.readFileSync(gitignore, 'utf-8');
    expect(content).toContain('loop/logs/');
  });

  test('appends to existing .gitignore without duplicating', () => {
    // Pre-create a .gitignore with unrelated content
    fs.writeFileSync(path.join(project.dir, '.gitignore'), '*.log\nnode_modules/\n');

    init();

    const content = fs.readFileSync(path.join(project.dir, '.gitignore'), 'utf-8');
    expect(content).toContain('*.log');
    expect(content).toContain('node_modules/');
    expect(content).toContain('loop/logs/');
  });

  test('skips existing symlinks without force', () => {
    // First init
    init();

    // Capture symlink target
    const linkPath = path.join(project.dir, 'loop/loop.sh');
    const target1 = fs.readlinkSync(linkPath);

    // Second init (no force) — symlink should remain unchanged
    init();
    const target2 = fs.readlinkSync(linkPath);
    expect(target2).toBe(target1);
  });
}, 30000);

describe('loop update (force init)', () => {
  let project;

  beforeEach(() => {
    project = useTempProject();
  });

  afterEach(() => {
    project.restore();
  });

  test('refreshes symlinks when force=true', () => {
    init();

    // Verify initial symlink exists
    const linkPath = path.join(project.dir, 'loop/loop.sh');
    expect(fs.lstatSync(linkPath).isSymbolicLink()).toBe(true);

    // Force update — should recreate without errors
    init({ force: true });

    expect(fs.lstatSync(linkPath).isSymbolicLink()).toBe(true);
    // Resolved path still points to package source
    const resolved = fs.realpathSync(linkPath);
    expect(resolved).toBe(path.join(PACKAGE_ROOT, 'scripts/loop.sh'));
  });

  test('overwrites template files when force=true', () => {
    init();

    // Modify a template file
    const templatePath = path.join(project.dir, 'loop/PROMPT_skills.md');
    if (fs.existsSync(templatePath)) {
      fs.writeFileSync(templatePath, 'modified content');

      // Force update — should overwrite
      init({ force: true });

      const content = fs.readFileSync(templatePath, 'utf-8');
      expect(content).not.toBe('modified content');
    }
  });

  test('updates .version file to current package version', () => {
    init();

    // Tamper with version file
    const versionPath = path.join(project.dir, 'loop/.version');
    fs.writeFileSync(versionPath, '0.0.0\n');

    init({ force: true });

    const version = fs.readFileSync(versionPath, 'utf-8').trim();
    const pkgVersion = require('../../package.json').version;
    expect(version).toBe(pkgVersion);
  });
}, 30000);

describe('loop summary (generateSummary end-to-end)', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'loop-summary-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('returns "no log files" message for empty directory', async () => {
    const report = await generateSummary(tmpDir);
    expect(report).toContain('No log files found');
  });

  test('produces formatted report from a realistic JSONL log', async () => {
    // Build a realistic log file with tool usage, tokens, and test results
    const logEntries = [
      // Assistant uses tools
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Read', input: { file_path: '/src/app.js' } },
            { type: 'tool_use', name: 'Edit', input: { file_path: '/src/app.js' } },
          ],
        },
      },
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Bash' },
            { type: 'tool_use', name: 'Read', input: { file_path: '/src/utils.js' } },
            { type: 'tool_use', name: 'Write', input: { file_path: '/src/new.js' } },
          ],
        },
      },
      // Token usage
      { type: 'result', usage: { input_tokens: 5000, output_tokens: 2000 } },
      { type: 'result', usage: { input_tokens: 3000, output_tokens: 1500 } },
      // Test results in output
      {
        type: 'assistant',
        message: {
          content: [
            { type: 'text', text: 'Running tests...\nTests: 42 passed, 1 failed, 43 total\n' },
          ],
        },
      },
    ];

    const logPath = path.join(tmpDir, 'run-2026-02-11.jsonl');
    const content = logEntries.map(e => JSON.stringify(e)).join('\n') + '\n';
    fs.writeFileSync(logPath, content);

    const report = await generateSummary(tmpDir);

    // Verify all sections appear in the report
    expect(report).toContain('=== Loop Run Summary ===');

    // Tool usage
    expect(report).toContain('Tool Usage:');
    expect(report).toContain('Read: 2');
    expect(report).toContain('Edit: 1');
    expect(report).toContain('Bash: 1');
    expect(report).toContain('Write: 1');
    expect(report).toContain('Total: 5 calls');

    // Files modified (Edit and Write targets only)
    expect(report).toContain('Files Modified (2):');
    expect(report).toContain('/src/app.js');
    expect(report).toContain('/src/new.js');

    // Token usage
    expect(report).toContain('Token Usage:');
    expect(report).toContain('8,000');  // input: 5000 + 3000
    expect(report).toContain('3,500');  // output: 2000 + 1500

    // Test results
    expect(report).toContain('Test Results:');
    expect(report).toContain('FAIL');
    expect(report).toContain('42 passed');
    expect(report).toContain('1 failed');

    // Log file reference
    expect(report).toContain(logPath);
  });

  test('picks the most recent log when multiple exist', async () => {
    // Create two log files with different timestamps
    const oldLog = path.join(tmpDir, 'old.jsonl');
    const newLog = path.join(tmpDir, 'new.jsonl');

    fs.writeFileSync(oldLog, JSON.stringify({
      type: 'result', usage: { input_tokens: 100, output_tokens: 50 },
    }) + '\n');
    // Set old mtime
    const past = new Date(Date.now() - 60000);
    fs.utimesSync(oldLog, past, past);

    fs.writeFileSync(newLog, JSON.stringify({
      type: 'result', usage: { input_tokens: 9999, output_tokens: 1 },
    }) + '\n');

    const report = await generateSummary(tmpDir);

    // Should use the newer log (9999 input tokens)
    expect(report).toContain('9,999');
    expect(report).not.toContain('100');
  });

  test('handles log with only token data (no tools, no tests)', async () => {
    const logPath = path.join(tmpDir, 'minimal.jsonl');
    fs.writeFileSync(logPath, JSON.stringify({
      type: 'result', usage: { input_tokens: 500, output_tokens: 200 },
    }) + '\n');

    const report = await generateSummary(tmpDir);

    expect(report).toContain('Token Usage:');
    expect(report).toContain('500');
    expect(report).toContain('200');
    // Should NOT contain sections with no data
    expect(report).not.toContain('Tool Usage:');
    expect(report).not.toContain('Files Modified');
    expect(report).not.toContain('Test Results:');
  });
}, 30000);

/**
 * Map a template destination path back to its source path in the package.
 * Matches the TEMPLATES array in init.js.
 */
function templateSrcPath(destRel) {
  const mapping = {
    'CLAUDE_template.md': 'templates/CLAUDE_template.md',
    'docs/plans/IMPLEMENTATION_PLAN_template.md': 'templates/IMPLEMENTATION_PLAN_template.md',
    '.claude/settings.json': '.claude/settings.json',
    '.claude/skills/auto-revise-claude-md/SKILL.md': '.claude/skills/auto-revise-claude-md/SKILL.md',
    'loop/PROMPT_skills.md': 'prompts/PROMPT_skills.md',
  };
  return mapping[destRel] || destRel;
}
