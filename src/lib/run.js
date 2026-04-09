const { spawn } = require('child_process');
const fs = require('fs');

const PKG_VERSION = require('../package.json').version;

function checkVersionMismatch() {
  const versionPath = './loop/.version';
  try {
    const fileVersion = fs.readFileSync(versionPath, 'utf-8').trim();
    if (fileVersion !== PKG_VERSION) {
      return { fileVersion, pkgVersion: PKG_VERSION };
    }
  } catch { /* missing file — skip */ }
  return null;
}

function checkLoopScript() {
  const loopScript = './loop/loop.sh';
  if (!fs.existsSync(loopScript)) {
    console.error('Error: loop/loop.sh not found. Run "loop init" first.');
    process.exit(1);
  }

  const mismatch = checkVersionMismatch();
  if (mismatch) {
    console.warn(`Warning: loop version mismatch — project: ${mismatch.fileVersion}, installed: ${mismatch.pkgVersion}. Run "loop update" to refresh.`);
  }

  return loopScript;
}

function buildArgs(opts, mode) {
  const args = [];

  if (mode === 'design') args.push('-d');
  if (!opts.interactive) args.push('-a');

  if (opts.plan) args.push('-P');
  if (opts.build) args.push('-B');
  if (opts.idea) args.push('-i', opts.idea);

  return args;
}

function shellEscape(arg) {
  return `'${arg.replace(/'/g, "'\\''")}'`;
}

function buildShellCommand(loopScript, args) {
  return [loopScript, ...args].map(shellEscape).join(' ');
}

function spawnTmux(sessionName, shellCommand) {
  return new Promise((resolve) => {
    const child = spawn('tmux', ['new-session', '-d', '-s', sessionName, 'bash', '-c', shellCommand], {
      stdio: 'inherit',
      cwd: process.cwd(),
    });
    child.on('close', (code, signal) => {
      const exitCode = signal ? 1 : (code ?? 0);
      if (exitCode === 0) {
        console.log(`tmux session '${sessionName}' started. Attach: tmux attach -t ${sessionName}`);
      } else {
        console.error(`Error: failed to start tmux session '${sessionName}' (exit code ${exitCode}). Session may already exist.`);
      }
      resolve(exitCode);
    });
  });
}

function spawnLoop(opts, mode) {
  const loopScript = checkLoopScript();
  const args = buildArgs(opts, mode);

  if (opts.tmux) {
    const sessionName = `loop-${mode}`;
    const cmd = `cd ${shellEscape(process.cwd())} && ${buildShellCommand(loopScript, args)}`;
    return spawnTmux(sessionName, cmd);
  }

  return new Promise((resolve) => {
    const child = spawn(loopScript, args, {
      stdio: 'inherit',
      cwd: process.cwd(),
    });
    child.on('close', (code, signal) => {
      resolve(signal ? 1 : (code ?? 0));
    });
  });
}

async function runDesign(opts) {
  const code = await spawnLoop({ ...opts, interactive: true }, 'design');
  process.exit(code);
}

async function runRun(opts) {
  const code = await spawnLoop(opts, 'run');
  process.exit(code);
}

module.exports = { runRun, runDesign, buildArgs, buildShellCommand, checkLoopScript, checkVersionMismatch, PKG_VERSION };
