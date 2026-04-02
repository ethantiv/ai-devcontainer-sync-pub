#!/usr/bin/env node

const { program } = require('commander');
const { init } = require('../lib/init');
const { listPresets } = require('../lib/skill-presets');
const { runPlan, runBuild, runCombined, runDesign } = require('../lib/run');
const { cleanup } = require('../lib/cleanup');
const { generateSummary } = require('../lib/summary');
const { doctor } = require('../lib/doctor');

function addLoopOptions(cmd) {
  return cmd
    .option('-i, --iterations <n>', 'Number of iterations')
    .option('-I, --idea <text>', 'Seed idea written to docs/IDEA.md before start')
    .option('-n, --new', 'Archive completed plan and start fresh')
    .option('--interactive', 'Run interactively instead of autonomous')
    .option('--tmux', 'Run in a detached tmux session');
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
  .option('-t, --type <types>', 'Project type(s) for domain-specific skills (comma-separated)')
  .option('--list-types', 'List available project types and exit')
  .action((opts) => {
    if (opts.listTypes) {
      console.log('Available project types:\n');
      for (const { name, description } of listPresets()) {
        console.log(`  ${name.padEnd(12)} ${description}`);
      }
      return;
    }
    init({ types: opts.type });
  });

program
  .command('design')
  .description('Run interactive design/brainstorming phase')
  .option('-I, --idea <text>', 'Seed idea written to docs/IDEA.md before start')
  .option('-n, --new', 'Archive completed plan and start fresh')
  .action((opts) => runDesign(opts));

addLoopOptions(
  program
    .command('plan')
    .description('Run planning phase (default: 3 iterations)')
).action((opts) => runPlan(opts));

addBuildOptions(
  program
    .command('build')
    .description('Run build phase (default: 99 iterations)')
).action((opts) => runBuild(opts));

addBuildOptions(
  program
    .command('run')
    .description('Plan then build sequentially (3 plan + 99 build iterations)')
    .addHelpText('after', `
In combined mode, -i applies only to the build phase.
Plan always uses default 3 iterations.

Examples:
  $ loop run                        Plan (3 iter) then build (99 iter)
  $ loop run -i 20                  Plan (3 iter) then build (20 iter)
  $ loop run -I "Add auth"          Seed idea for plan, then build`)
).action((opts) => runCombined(opts));

program
  .command('cleanup')
  .description('Kill processes on dev server ports (3000, 5173, 8080, etc.)')
  .action(() => cleanup());

program
  .command('summary')
  .description('Show summary of last loop run')
  .option('--log-dir <dir>', 'Log directory', './loop/logs')
  .action(async (opts) => {
    const report = await generateSummary(opts.logDir);
    console.log(report);
  });

program
  .command('doctor')
  .description('Check loop installation health')
  .action(() => doctor());

program
  .command('update')
  .description('Force-refresh all symlinks and templates from package')
  .option('-t, --type <types>', 'Project type(s) for domain-specific skills (comma-separated)')
  .action((opts) => init({ force: true, types: opts.type }));

program.addHelpText('after', `
Examples:
  $ loop init               Set up loop in current project
  $ loop init --type web    Init with web-specific skills
  $ loop init --list-types  Show available project types
  $ loop design             Interactive design/brainstorming session
  $ loop plan               Plan mode (3 autonomous iterations)
  $ loop build              Build mode (99 autonomous iterations)
  $ loop build -i 20        Build mode with 20 iterations
  $ loop run                Plan then build (3+99 iterations)
  $ loop run -I "Add auth"  Plan with seed idea, then build
  $ loop build --tmux       Build in a detached tmux session
  $ loop summary            Show summary of last loop run
  $ loop cleanup            Kill dev server processes
  $ loop doctor             Check loop installation health
  $ loop update             Force-refresh symlinks and templates`);

program.parse();
