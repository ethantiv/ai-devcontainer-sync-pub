#!/usr/bin/env node

const { program } = require('commander');
const { init } = require('../lib/init');
const { PRESETS } = require('../lib/skill-presets');
const { runRun, runDesign } = require('../lib/run');
const { spawn } = require('child_process');
const path = require('path');

function parseTypes(opts) {
  return Object.keys(PRESETS).filter(t => opts[t]).join(',') || undefined;
}

program
  .name('loop')
  .description('Autonomous development loop powered by Claude CLI')
  .version(require('../package.json').version);

program
  .command('init')
  .description('Symlink scripts/prompts and copy templates into current project')
  .option('--web', 'Add web-specific skills')
  .option('--devops', 'Add DevOps-specific skills')
  .action((opts) => init({ types: parseTypes(opts) }));

program
  .command('design')
  .description('Run interactive design/brainstorming phase')
  .option('-i, --idea <text>', 'Seed idea written to docs/IDEA.md before start')
  .action((opts) => runDesign(opts));

program
  .command('run')
  .description('Autonomous plan + build (two phases)')
  .option('-i, --idea <text>', 'Seed idea written to docs/IDEA.md before start')
  .option('--plan', 'Run plan phase only')
  .option('--build', 'Run build phase only')
  .option('--interactive', 'Run interactively instead of autonomous')
  .option('--tmux', 'Run in a detached tmux session')
  .action((opts) => runRun(opts));

program
  .command('kill')
  .description('Kill all running loop processes and tmux sessions')
  .action(() => {
    const scriptDir = path.resolve(__dirname, '..', 'scripts');
    const child = spawn(path.join(scriptDir, 'kill-loop.sh'), [], {
      stdio: 'inherit',
      cwd: process.cwd(),
    });
    child.on('close', (code) => process.exit(code ?? 0));
  });

program
  .command('update')
  .description('Force-refresh all symlinks and templates from package')
  .option('--web', 'Add web-specific skills')
  .option('--devops', 'Add DevOps-specific skills')
  .action((opts) => init({ force: true, types: parseTypes(opts) }));

program.addHelpText('after', `
Examples:
  $ loop init               Set up loop in current project
  $ loop init --web         Init with web-specific skills
  $ loop design             Interactive design/brainstorming session
  $ loop run                Autonomous plan + build (two phases)
  $ loop run --plan         Plan phase only
  $ loop run --build        Build phase only (uses existing plan)
  $ loop run -i "Add auth"  Seed idea, then plan + build
  $ loop run --tmux         Run in a detached tmux session
  $ loop kill               Kill all loop processes
  $ loop update             Force-refresh symlinks and templates`);

program.parse();
