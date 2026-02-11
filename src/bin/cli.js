#!/usr/bin/env node

const { program } = require('commander');
const { init } = require('../lib/init');
const { runPlan, runBuild, runCombined } = require('../lib/run');
const { cleanup } = require('../lib/cleanup');
const { generateSummary } = require('../lib/summary');

function addLoopOptions(cmd) {
  return cmd
    .option('-i, --iterations <n>', 'Number of iterations')
    .option('-I, --idea <text>', 'Seed idea written to docs/ROADMAP.md before start')
    .option('--interactive', 'Run interactively instead of autonomous');
}

function addBuildOptions(cmd) {
  return addLoopOptions(cmd)
    .option('-e, --no-early-exit', 'Disable early exit when plan is complete');
}

program
  .name('loop')
  .description('Autonomous development loop powered by Claude CLI')
  .version(require('../package.json').version);

program
  .command('init')
  .description('Symlink scripts/prompts and copy templates into current project')
  .action(() => init());

addLoopOptions(
  program
    .command('plan')
    .description('Run planning phase (default: 5 iterations)')
).action((opts) => runPlan(opts));

addBuildOptions(
  program
    .command('build')
    .description('Run build phase (default: 10 iterations)')
).action((opts) => runBuild(opts));

addBuildOptions(
  program
    .command('run')
    .description('Plan then build sequentially (5 plan + 10 build iterations)')
    .addHelpText('after', `
In combined mode, -i applies only to the build phase.
Plan always uses default 5 iterations.

Examples:
  $ loop run                        Plan (5 iter) then build (10 iter)
  $ loop run -i 20                  Plan (5 iter) then build (20 iter)
  $ loop run -I "Add auth"          Seed idea for plan, then build`)
).action((opts) => runCombined(opts));

program
  .command('cleanup')
  .description('Kill processes on dev server ports (3000, 5173, 8080, etc.)')
  .option('--logs', 'Rotate and prune log files instead of killing processes')
  .action((opts) => cleanup({ logs: opts.logs }));

program
  .command('summary')
  .description('Show summary of last loop run')
  .option('--log-dir <dir>', 'Log directory', './loop/logs')
  .action(async (opts) => {
    const report = await generateSummary(opts.logDir);
    console.log(report);
  });

program
  .command('update')
  .description('Force-refresh all symlinks and templates from package')
  .action(() => init({ force: true }));

program.addHelpText('after', `
Examples:
  $ loop init               Set up loop in current project
  $ loop plan               Plan mode (5 autonomous iterations)
  $ loop build              Build mode (10 autonomous iterations)
  $ loop build -i 20        Build mode with 20 iterations
  $ loop run                Plan then build (5+10 iterations)
  $ loop run -I "Add auth"  Plan with seed idea, then build
  $ loop summary            Show summary of last loop run
  $ loop cleanup            Kill dev server processes
  $ loop cleanup --logs     Rotate and prune log files
  $ loop update             Force-refresh symlinks and templates`);

program.parse();
