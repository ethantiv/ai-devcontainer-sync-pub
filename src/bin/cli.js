#!/usr/bin/env node

const { program } = require('commander');
const { init } = require('../lib/init');
const { listPresets } = require('../lib/skill-presets');
const { runRun, runDesign } = require('../lib/run');
const { spawn } = require('child_process');
const path = require('path');

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

program
  .command('run')
  .description('Autonomous plan + build in a single session')
  .option('-I, --idea <text>', 'Seed idea written to docs/IDEA.md before start')
  .option('-n, --new', 'Archive completed plan and start fresh')
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
  .option('-t, --type <types>', 'Project type(s) for domain-specific skills (comma-separated)')
  .action((opts) => init({ force: true, types: opts.type }));

program.addHelpText('after', `
Examples:
  $ loop init               Set up loop in current project
  $ loop init --type web    Init with web-specific skills
  $ loop design             Interactive design/brainstorming session
  $ loop run                Autonomous plan + build
  $ loop run -I "Add auth"  Seed idea, then plan + build
  $ loop run --tmux         Run in a detached tmux session
  $ loop run --new          Archive completed plan, start fresh
  $ loop kill               Kill all loop processes
  $ loop update             Force-refresh symlinks and templates`);

program.parse();
