const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { CORE_FILES } = require('./init');
const { checkVersionMismatch, PKG_VERSION } = require('./run');

const SYMLINK_FILES = CORE_FILES.map(f => path.basename(f.dest));

const checks = [
  {
    name: 'Loop symlinks',
    fn() {
      const missing = SYMLINK_FILES.filter(f => !fs.existsSync(`./loop/${f}`));
      if (missing.length > 0) {
        return { ok: false, message: `${missing.length} missing: ${missing.join(', ')}`, fix: 'Run "loop init" to create symlinks' };
      }
      return { ok: true, message: `${SYMLINK_FILES.length} files present` };
    },
  },
  {
    name: 'Loop version',
    fn() {
      const mismatch = checkVersionMismatch();
      if (mismatch) {
        return { ok: false, message: `project: ${mismatch.fileVersion}, installed: ${mismatch.pkgVersion}`, fix: 'Run "loop update" to refresh' };
      }
      if (!fs.existsSync('./loop/.version')) {
        return { ok: false, message: '.version file missing', fix: 'Run "loop init"' };
      }
      return { ok: true, message: `v${PKG_VERSION}` };
    },
  },
  {
    name: 'Claude CLI',
    fn() {
      try {
        const version = execSync('claude --version 2>/dev/null', { encoding: 'utf-8', timeout: 5000 }).trim();
        return { ok: true, message: version };
      } catch {
        const homeClaude = `${process.env.HOME}/.claude/bin/claude`;
        if (fs.existsSync(homeClaude)) {
          return { ok: true, message: `found at ${homeClaude}` };
        }
        return { ok: false, message: 'not found in PATH or ~/.claude/bin/', fix: 'Install Claude CLI: https://docs.anthropic.com/en/docs/claude-code' };
      }
    },
  },
  {
    name: 'Git repository',
    fn() {
      try {
        execSync('git rev-parse --is-inside-work-tree 2>/dev/null', { encoding: 'utf-8', timeout: 5000 });
        return { ok: true, message: 'inside git repo' };
      } catch {
        return { ok: false, message: 'not a git repository', fix: 'Run "git init"' };
      }
    },
  },
  {
    name: 'jq binary',
    fn() {
      try {
        execSync('jq --version 2>/dev/null', { encoding: 'utf-8', timeout: 5000 });
        return { ok: true, message: 'available' };
      } catch {
        return { ok: false, message: 'not found', fix: 'Install jq: apt-get install jq / brew install jq' };
      }
    },
  },
  {
    name: 'GH_TOKEN',
    fn() {
      if (process.env.GH_TOKEN) {
        return { ok: true, message: 'set' };
      }
      return { ok: false, message: 'not set', fix: 'Set GH_TOKEN env var with a GitHub PAT (repo, workflow scopes)' };
    },
  },
];

function runChecks() {
  const results = [];
  for (const check of checks) {
    try {
      const result = check.fn();
      results.push({ name: check.name, ...result });
    } catch (err) {
      results.push({ name: check.name, ok: false, message: err.message });
    }
  }
  return results;
}

function formatResults(results) {
  const lines = ['=== Loop Doctor ===', ''];

  for (const r of results) {
    const icon = r.ok ? '[OK]' : '[FAIL]';
    lines.push(`${icon}  ${r.name}: ${r.message}`);
    if (!r.ok && r.fix) {
      lines.push(`      Fix: ${r.fix}`);
    }
  }

  const passed = results.filter(r => r.ok).length;
  const failed = results.length - passed;
  lines.push('', `${passed} passed, ${failed} failed`);

  return lines.join('\n');
}

function doctor() {
  const results = runChecks();
  console.log(formatResults(results));
  process.exit(results.every(r => r.ok) ? 0 : 1);
}

module.exports = { doctor, runChecks, checks, formatResults };
