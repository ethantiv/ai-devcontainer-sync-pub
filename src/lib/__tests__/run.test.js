const fs = require('fs');
const path = require('path');
const os = require('os');
const { runDesign, buildArgs, buildShellCommand, checkLoopScript } = require('../run');

describe('runDesign', () => {
  test('is exported as a function', () => {
    expect(typeof runDesign).toBe('function');
  });
});

describe('buildArgs', () => {
  test('plan mode adds -p and -a with default 3 iterations', () => {
    const args = buildArgs({}, 'plan');
    expect(args).toEqual(['-p', '-a', '-i', '3']);
  });

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

  test('tmux flag is not included in shell args', () => {
    const args = buildArgs({ tmux: true }, 'build');
    expect(args).not.toContain('--tmux');
    expect(args).toEqual(['-a', '-i', '99']);
  });
});

describe('buildShellCommand', () => {
  test('builds escaped shell command from script and args', () => {
    const cmd = buildShellCommand('./loop/loop.sh', ['-a', '-i', '99']);
    expect(cmd).toBe("'./loop/loop.sh' '-a' '-i' '99'");
  });

  test('escapes single quotes in arguments', () => {
    const cmd = buildShellCommand('./loop/loop.sh', ['-I', "it's a test"]);
    expect(cmd).toBe("'./loop/loop.sh' '-I' 'it'\\''s a test'");
  });

  test('handles arguments with spaces', () => {
    const cmd = buildShellCommand('./loop/loop.sh', ['-I', 'Add auth module']);
    expect(cmd).toBe("'./loop/loop.sh' '-I' 'Add auth module'");
  });
});

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
