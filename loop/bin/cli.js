#!/usr/bin/env node

const { program } = require('commander');
const { init } = require('../lib/init');
const { run } = require('../lib/run');
const { cleanup } = require('../lib/cleanup');

program
  .name('loop')
  .description('Autonomous development loop powered by Claude CLI')
  .version(require('../package.json').version);

program
  .command('init')
  .description('Initialize loop system in current project')
  .option('--force', 'Overwrite existing symlinks')
  .action((opts) => init({ force: opts.force }));

program
  .command('run')
  .description('Run the development loop')
  .option('-p, --plan', 'Run in plan mode')
  .option('-i, --iterations <n>', 'Number of iterations (default: 5 build, 3 plan)')
  .option('-I, --idea <text>', 'Initial idea for planning')
  .option('--interactive', 'Interactive mode (default: autonomous)')
  .option('-e, --no-early-exit', 'Disable early exit')
  .action((opts) => run(opts));

program
  .command('cleanup')
  .description('Kill processes on dev server ports')
  .action(() => cleanup());

program
  .command('update')
  .description('Refresh symlinks after npm update')
  .action(() => init({ force: true, symlinkOnly: true }));

program.parse();
