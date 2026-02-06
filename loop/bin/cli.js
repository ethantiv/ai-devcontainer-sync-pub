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
  .description('Symlink scripts/prompts and copy templates into current project')
  .option('--force', 'Overwrite existing symlinks')
  .action((opts) => init({ force: opts.force }));

program
  .command('run')
  .description('Run Claude in autonomous loop (default: build mode, 5 iterations)')
  .option('-p, --plan', 'plan mode instead of build (default: 3 iterations)')
  .option('-i, --iterations <n>', 'Number of iterations (default: 5 build, 3 plan)')
  .option('-I, --idea <text>', 'seed idea written to docs/IDEA.md before start')
  .option('--interactive', 'run interactively instead of autonomous')
  .option('-e, --no-early-exit', 'disable early exit when plan is complete')
  .addHelpText('after', `
Defaults:
  Mode:        build (use -p for plan)
  Execution:   autonomous (use --interactive for manual)
  Iterations:  5 in build, 3 in plan
  Early exit:  enabled in build (stops when plan marked complete)

Examples:
  $ loop run                        Build, 5 autonomous iterations
  $ loop run --plan                 Plan, 3 autonomous iterations
  $ loop run -p -i 1               Single planning iteration
  $ loop run -p -I "Add auth"      Plan with seed idea
  $ loop run -e                    Build, all iterations (no early exit)
  $ loop run --interactive          Build with interactive Claude session`)
  .action((opts) => run(opts));

program
  .command('cleanup')
  .description('Kill processes on dev server ports (3000, 5173, 8080, etc.)')
  .action(() => cleanup());

program
  .command('update')
  .description('Re-create symlinks from package to project (after npm update)')
  .action(() => init({ force: true, symlinkOnly: true }));

program.addHelpText('after', `
Examples:
  $ loop init               Set up loop in current project
  $ loop run --plan         Plan mode (3 autonomous iterations)
  $ loop run                Build mode (5 autonomous iterations)
  $ loop run -i 10          Build mode with 10 iterations
  $ loop run --interactive  Build mode with interactive Claude session
  $ loop cleanup            Kill dev server processes
  $ loop update             Refresh symlinks after package update`);

program.parse();
