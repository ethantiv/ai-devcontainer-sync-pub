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
