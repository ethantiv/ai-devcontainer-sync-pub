const fs = require('fs');
const path = require('path');
const { resolveTypes } = require('./skill-presets');
const { PKG_VERSION } = require('./run');

const PACKAGE_ROOT = path.resolve(__dirname, '..');

// Core files: symlinked from package to project's ./loop/
const CORE_FILES = [
  { src: 'scripts/loop.sh', dest: 'loop/loop.sh' },
  { src: 'prompts/PROMPT_design.md', dest: 'loop/PROMPT_design.md' },
  { src: 'prompts/PROMPT_run.md', dest: 'loop/PROMPT_run.md' },
  { src: 'scripts/kill-loop.sh', dest: 'loop/kill-loop.sh' },
];

// Templates: copied (not symlinked) so they can be customized per project
const TEMPLATES = [
  { src: '.claude/skills/auto-revise-claude-md/SKILL.md', dest: '.claude/skills/auto-revise-claude-md/SKILL.md' },
  { src: 'prompts/PROMPT_skills_design.md', dest: 'loop/PROMPT_skills_design.md' },
  { src: 'prompts/PROMPT_skills_run.md', dest: 'loop/PROMPT_skills_run.md' },
];

const DIRS = ['docs', 'loop/logs', '.claude/skills/auto-revise-claude-md'];

// overlayfs (Docker) can leave ghost entries where existsSync returns true
// but the file has nlink=0 and readFileSync throws ENOENT
function fileExists(p) {
  try { return fs.statSync(p).nlink > 0; } catch { return false; }
}

function appendSkills(filePath, skills) {
  if (!skills.length) return;
  const content = fs.readFileSync(filePath, 'utf-8');
  const newSkills = skills.filter(s => !content.includes(s));
  if (!newSkills.length) return;
  const section = '\n# Project-specific skills (--type)\n'
    + newSkills.map(s => `- \`${s}\``).join('\n') + '\n';
  fs.writeFileSync(filePath, content.trimEnd() + '\n' + section);
}

function init({ force = false, types } = {}) {
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

  // Create docs/IDEA.md if missing (never overwrite)
  const ideaPath = path.join(projectRoot, 'docs/IDEA.md');
  if (!fileExists(ideaPath)) {
    fs.writeFileSync(ideaPath, '# Idea\n');
    console.log('  created docs/IDEA.md');
  }

  // Copy templates (skip existing unless force)
  for (const { src, dest } of TEMPLATES) {
    const srcPath = path.join(PACKAGE_ROOT, src);
    const destPath = path.join(projectRoot, dest);

    if (!fs.existsSync(srcPath)) continue;

    if (!force && fileExists(destPath)) {
      console.log(`  skip ${dest} (exists)`);
    } else {
      fs.copyFileSync(srcPath, destPath);
      console.log(`  copied ${dest}`);
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

  // Write version file for run-time checks
  const versionPath = path.join(projectRoot, 'loop/.version');
  fs.writeFileSync(versionPath, PKG_VERSION + '\n');
  console.log(`  wrote loop/.version (${PKG_VERSION})`);

  // Add loop artifacts to .gitignore
  const gitignorePath = path.join(projectRoot, '.gitignore');
  const entries = ['loop/logs/'];

  if (fs.existsSync(gitignorePath)) {
    const content = fs.readFileSync(gitignorePath, 'utf-8');
    const missing = entries.filter(e => !content.includes(e));
    if (missing.length) {
      fs.appendFileSync(gitignorePath, `\n${missing.join('\n')}\n`);
      console.log(`  added ${missing.join(', ')} to .gitignore`);
    }
  } else {
    fs.writeFileSync(gitignorePath, `${entries.join('\n')}\n`);
    console.log('  created .gitignore with loop entries');
  }

  // Resolve types: use explicit flag, fall back to persisted .type
  const typeFile = path.join(projectRoot, 'loop/.type');
  const effectiveTypes = types
    || (fs.existsSync(typeFile) ? fs.readFileSync(typeFile, 'utf-8').trim() : null);

  if (types) {
    fs.writeFileSync(typeFile, types + '\n');
  }

  if (effectiveTypes) {
    const resolved = resolveTypes(effectiveTypes);
    const designPath = path.join(projectRoot, 'loop/PROMPT_skills_design.md');
    const runPath = path.join(projectRoot, 'loop/PROMPT_skills_run.md');
    if (fs.existsSync(designPath)) appendSkills(designPath, resolved.design);
    if (fs.existsSync(runPath)) appendSkills(runPath, resolved.run);
    console.log(`  applied skills for type: ${effectiveTypes}`);
  }

  console.log('\nDone! Run: loop run');
}

module.exports = { init, CORE_FILES };
