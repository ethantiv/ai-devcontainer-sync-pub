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
