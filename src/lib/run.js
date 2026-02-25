const { spawn } = require('child_process');
const fs = require('fs');

function checkLoopScript() {
  const loopScript = './loop/loop.sh';
  if (!fs.existsSync(loopScript)) {
    console.error('Error: loop/loop.sh not found. Run "loop init" first.');
    process.exit(1);
  }

  // Check version mismatch (warning only)
  const versionPath = './loop/.version';
  if (fs.existsSync(versionPath)) {
    const fileVersion = fs.readFileSync(versionPath, 'utf-8').trim();
    const pkgVersion = require('../package.json').version;
    if (fileVersion !== pkgVersion) {
      console.warn(`Warning: loop version mismatch — project: ${fileVersion}, installed: ${pkgVersion}. Run "loop update" to refresh.`);
    }
  }

  return loopScript;
}

function spawnLoop(opts, mode) {
  const loopScript = checkLoopScript();
  const args = [];

  if (mode === 'plan') args.push('-p');
  if (mode === 'design') args.push('-d');
  if (!opts.interactive) args.push('-a');

  if (mode !== 'design') {
    const defaultIter = mode === 'build' ? '99' : '5';
    const iterations = opts.iterations || defaultIter;
    args.push('-i', iterations);
  }

  if (opts.idea) args.push('-I', opts.idea);
  if (opts.new) args.push('-n');
  if (opts.earlyExit === false) args.push('-e');

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

function runPlan(opts) {
  spawnLoop(opts, 'plan').then((code) => process.exit(code));
}

function runBuild(opts) {
  spawnLoop(opts, 'build').then((code) => process.exit(code));
}

function runDesign(opts) {
  spawnLoop({ ...opts, interactive: true }, 'design').then((code) => process.exit(code));
}

function runCombined(opts) {
  // Plan phase: default iterations, pass --idea, ignore -i override
  const planOpts = {
    interactive: opts.interactive,
    idea: opts.idea,
    new: opts.new,
  };

  // Build phase: uses -i if given, no --idea (plan already wrote it to ROADMAP)
  const buildOpts = {
    interactive: opts.interactive,
    earlyExit: opts.earlyExit,
    iterations: opts.iterations,
  };

  spawnLoop(planOpts, 'plan').then((planCode) => {
    if (planCode !== 0) {
      console.error(`Plan phase exited with code ${planCode}, skipping build.`);
      process.exit(planCode);
    }
    spawnLoop(buildOpts, 'build').then((buildCode) => process.exit(buildCode));
  });
}

module.exports = { runPlan, runBuild, runCombined, runDesign };
