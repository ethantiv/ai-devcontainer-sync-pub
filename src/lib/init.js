const fs = require('fs');
const path = require('path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');

// Core files: symlinked from package to project's ./loop/
const CORE_FILES = [
  { src: 'scripts/loop.sh', dest: 'loop/loop.sh' },
  { src: 'prompts/PROMPT_plan.md', dest: 'loop/PROMPT_plan.md' },
  { src: 'prompts/PROMPT_build.md', dest: 'loop/PROMPT_build.md' },
  { src: 'prompts/PROMPT_skills.md', dest: 'loop/PROMPT_skills.md' },
  { src: 'scripts/cleanup.sh', dest: 'loop/cleanup.sh' },
  { src: 'scripts/notify-telegram.sh', dest: 'loop/notify-telegram.sh' },
];

// Templates: copied (not symlinked) so they can be customized per project
const TEMPLATES = [
  { src: 'templates/CLAUDE_template.md', dest: 'CLAUDE_template.md' },
  { src: 'templates/IMPLEMENTATION_PLAN_template.md', dest: 'docs/plans/IMPLEMENTATION_PLAN_template.md' },
  { src: 'templates/IDEA_template.md', dest: 'docs/IDEA_template.md' },
  { src: '.claude/settings.json', dest: '.claude/settings.json' },
  { src: '.claude/skills/auto-revise-claude-md/SKILL.md', dest: '.claude/skills/auto-revise-claude-md/SKILL.md' },
];

const DIRS = ['docs/plans', 'loop/logs', '.claude/skills/auto-revise-claude-md'];

function init({ force = false, symlinkOnly = false } = {}) {
  const projectRoot = process.cwd();

  // Don't create symlinks if running from the source repo itself
  if (path.resolve(projectRoot) === path.resolve(PACKAGE_ROOT)) {
    console.log('Running from source repo - nothing to do.');
    return;
  }

  // Create directories
  for (const dir of DIRS) {
    const dirPath = path.join(projectRoot, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      console.log(`  created ${dir}/`);
    }
  }

  // Copy templates (skip existing)
  if (!symlinkOnly) {
    for (const { src, dest } of TEMPLATES) {
      const srcPath = path.join(PACKAGE_ROOT, src);
      const destPath = path.join(projectRoot, dest);

      if (!fs.existsSync(srcPath)) continue;

      if (fs.existsSync(destPath)) {
        console.log(`  skip ${dest} (exists)`);
      } else {
        fs.copyFileSync(srcPath, destPath);
        console.log(`  copied ${dest}`);
      }
    }
  }

  // Create symlinks for core files
  for (const { src, dest } of CORE_FILES) {
    const srcPath = path.join(PACKAGE_ROOT, src);
    const destPath = path.join(projectRoot, dest);

    if (!fs.existsSync(srcPath)) {
      console.log(`  warn: ${src} not found in package`);
      continue;
    }

    const destDir = path.dirname(destPath);
    fs.mkdirSync(destDir, { recursive: true });

    // lstat doesn't follow symlinks — catches broken symlinks that existsSync misses
    let destStat;
    try { destStat = fs.lstatSync(destPath); } catch { destStat = null; }

    if (destStat) {
      if (!destStat.isSymbolicLink()) {
        console.log(`  skip ${dest} (real file exists)`);
        continue;
      }
      if (!force) {
        console.log(`  skip ${dest} (symlink exists)`);
        continue;
      }
      fs.unlinkSync(destPath);
    }

    const relTarget = path.relative(destDir, srcPath);
    fs.symlinkSync(relTarget, destPath);

    if (src.endsWith('.sh')) {
      try { fs.chmodSync(srcPath, 0o755); } catch { /* read-only source */ }
    }

    console.log(`  linked ${dest}`);
  }

  // Add loop/logs/ to .gitignore
  const gitignorePath = path.join(projectRoot, '.gitignore');
  const entry = 'loop/logs/';

  if (fs.existsSync(gitignorePath)) {
    const content = fs.readFileSync(gitignorePath, 'utf-8');
    if (!content.includes(entry)) {
      fs.appendFileSync(gitignorePath, `\n${entry}\n`);
      console.log('  added loop/logs/ to .gitignore');
    }
  } else {
    fs.writeFileSync(gitignorePath, `${entry}\n`);
    console.log('  created .gitignore with loop/logs/');
  }

  console.log('\nDone! Run: npx loop run --plan');
}

module.exports = { init };
