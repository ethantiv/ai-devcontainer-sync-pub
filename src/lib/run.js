const { spawn } = require('child_process');
const fs = require('fs');

function run(opts) {
  const loopScript = './loop/loop.sh';

  if (!fs.existsSync(loopScript)) {
    console.error('Error: loop/loop.sh not found. Run "npx loop init" first.');
    process.exit(1);
  }

  const args = [];

  // Mode
  if (opts.plan) args.push('-p');

  // Autonomous by default (unless --interactive)
  if (!opts.interactive) args.push('-a');

  // Iterations (default: 3 for plan, 5 for build)
  const iterations = opts.iterations || (opts.plan ? '3' : '5');
  args.push('-i', iterations);

  // Idea
  if (opts.idea) args.push('-I', opts.idea);

  // Early exit
  if (opts.earlyExit === false) args.push('-e');

  const child = spawn(loopScript, args, {
    stdio: 'inherit',
    cwd: process.cwd(),
  });

  child.on('close', (code) => {
    process.exit(code ?? 0);
  });
}

module.exports = { run };
