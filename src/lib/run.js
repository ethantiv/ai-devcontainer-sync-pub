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

function spawnLoop(opts, mode) {
  const loopScript = checkLoopScript();
  const args = buildArgs(opts, mode);

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

async function runPlan(opts) {
  const code = await spawnLoop(opts, 'plan');
  process.exit(code);
}

async function runBuild(opts) {
  const code = await spawnLoop(opts, 'build');
  process.exit(code);
}

async function runDesign(opts) {
  const code = await spawnLoop({ ...opts, interactive: true }, 'design');
  process.exit(code);
}

async function runCombined(opts) {
  // Plan phase: default iterations, pass --idea, ignore -i override
  const planOpts = {
    interactive: opts.interactive,
    idea: opts.idea,
    new: opts.new,
  };

  const planCode = await spawnLoop(planOpts, 'plan');
  if (planCode !== 0) {
    console.error(`Plan phase exited with code ${planCode}, skipping build.`);
    process.exit(planCode);
  }

  // Build phase: uses -i if given, no --idea (plan already wrote it to ROADMAP)
  const buildOpts = {
    interactive: opts.interactive,
    earlyExit: opts.earlyExit,
    iterations: opts.iterations,
  };

  const buildCode = await spawnLoop(buildOpts, 'build');
  process.exit(buildCode);
}

module.exports = { runPlan, runBuild, runCombined, runDesign, buildArgs, checkLoopScript, checkVersionMismatch, PKG_VERSION };
