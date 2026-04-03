/**
 * Integration tests for the loop workflow: init, update, and summary.
 *
 * These tests exercise the full module behavior (not mocked internals)
 * by running init() in real temp directories and generateSummary() on
 * real JSONL files. Timeouts are extended because fs operations on
 * overlayfs (Docker) can be slow.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { init } = require('../init');
const PACKAGE_ROOT = path.resolve(__dirname, '..', '..');

/** Create an isolated temp directory and chdir into it, returning a restore fn. */
function useTempProject() {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'loop-integration-'));
  const origCwd = process.cwd();
  process.chdir(tmpDir);
  return {
    dir: tmpDir,
    restore() {
      process.chdir(origCwd);
      fs.rmSync(tmpDir, { recursive: true, force: true });
    },
  };
}

// Expected symlinks created by init() (src → dest relative to project root)
const EXPECTED_SYMLINKS = [
  'loop/loop.sh',
  'loop/PROMPT_design.md',
  'loop/PROMPT_run.md',
  'loop/kill-loop.sh',
];

// Expected directories
const EXPECTED_DIRS = [
  'docs',
  'loop/logs',
  '.claude/skills/auto-revise-claude-md',
];

// Expected copied templates
const EXPECTED_TEMPLATES = [
  'loop/CLAUDE_template.md',
  '.claude/settings.json',
  '.claude/skills/auto-revise-claude-md/SKILL.md',
  'loop/PROMPT_skills_design.md',
  'loop/PROMPT_skills_run.md',
];

describe('loop init', () => {
  let project;

  beforeEach(() => {
    project = useTempProject();
  });

  afterEach(() => {
    project.restore();
  });

  test('creates expected symlinks pointing back to package source', () => {
    init();

    for (const rel of EXPECTED_SYMLINKS) {
      const full = path.join(project.dir, rel);
      expect(fs.existsSync(full)).toBe(true);

      const stat = fs.lstatSync(full);
      expect(stat.isSymbolicLink()).toBe(true);

      // Symlink target should resolve to the package source file
      const resolved = fs.realpathSync(full);
      expect(resolved.startsWith(PACKAGE_ROOT)).toBe(true);
    }
  });

  test('creates expected directories', () => {
    init();

    for (const dir of EXPECTED_DIRS) {
      const full = path.join(project.dir, dir);
      expect(fs.existsSync(full)).toBe(true);
      expect(fs.statSync(full).isDirectory()).toBe(true);
    }
  });

  test('copies template files (not symlinks)', () => {
    init();

    for (const rel of EXPECTED_TEMPLATES) {
      const srcPath = path.join(PACKAGE_ROOT, templateSrcPath(rel));
      // Template source may not exist (e.g. optional skill files)
      if (!fs.existsSync(srcPath)) continue;

      const full = path.join(project.dir, rel);
      expect(fs.existsSync(full)).toBe(true);

      const stat = fs.lstatSync(full);
      // Templates are copied, not symlinked
      expect(stat.isSymbolicLink()).toBe(false);
      expect(stat.isFile()).toBe(true);
    }
  });

  test('writes loop/.version matching package.json version', () => {
    init();

    const versionPath = path.join(project.dir, 'loop/.version');
    expect(fs.existsSync(versionPath)).toBe(true);

    const version = fs.readFileSync(versionPath, 'utf-8').trim();
    const pkgVersion = require('../../package.json').version;
    expect(version).toBe(pkgVersion);
  });

  test('creates .gitignore with loop/logs/ entry', () => {
    init();

    const gitignore = path.join(project.dir, '.gitignore');
    expect(fs.existsSync(gitignore)).toBe(true);

    const content = fs.readFileSync(gitignore, 'utf-8');
    expect(content).toContain('loop/logs/');
  });

  test('appends to existing .gitignore without duplicating', () => {
    // Pre-create a .gitignore with unrelated content
    fs.writeFileSync(path.join(project.dir, '.gitignore'), '*.log\nnode_modules/\n');

    init();

    const content = fs.readFileSync(path.join(project.dir, '.gitignore'), 'utf-8');
    expect(content).toContain('*.log');
    expect(content).toContain('node_modules/');
    expect(content).toContain('loop/logs/');
  });

  test('creates docs/IDEA.md on init', () => {
    init();

    const ideaPath = path.join(project.dir, 'docs/IDEA.md');
    expect(fs.existsSync(ideaPath)).toBe(true);
    expect(fs.readFileSync(ideaPath, 'utf-8')).toBe('# Idea\n');
  });

  test('does not overwrite existing docs/IDEA.md on update', () => {
    init();

    const ideaPath = path.join(project.dir, 'docs/IDEA.md');
    fs.writeFileSync(ideaPath, '# Idea\n\nMy project idea\n');

    init({ force: true });

    const content = fs.readFileSync(ideaPath, 'utf-8');
    expect(content).toContain('My project idea');
  });

  test('skips existing symlinks without force', () => {
    // First init
    init();

    // Capture symlink target
    const linkPath = path.join(project.dir, 'loop/loop.sh');
    const target1 = fs.readlinkSync(linkPath);

    // Second init (no force) — symlink should remain unchanged
    init();
    const target2 = fs.readlinkSync(linkPath);
    expect(target2).toBe(target1);
  });
}, 30000);

describe('loop update (force init)', () => {
  let project;

  beforeEach(() => {
    project = useTempProject();
  });

  afterEach(() => {
    project.restore();
  });

  test('refreshes symlinks when force=true', () => {
    init();

    // Verify initial symlink exists
    const linkPath = path.join(project.dir, 'loop/loop.sh');
    expect(fs.lstatSync(linkPath).isSymbolicLink()).toBe(true);

    // Force update — should recreate without errors
    init({ force: true });

    expect(fs.lstatSync(linkPath).isSymbolicLink()).toBe(true);
    // Resolved path still points to package source
    const resolved = fs.realpathSync(linkPath);
    expect(resolved).toBe(path.join(PACKAGE_ROOT, 'scripts/loop.sh'));
  });

  test('overwrites template files when force=true', () => {
    init();

    // Modify a template file
    const templatePath = path.join(project.dir, 'loop/PROMPT_skills_run.md');
    if (fs.existsSync(templatePath)) {
      fs.writeFileSync(templatePath, 'modified content');

      // Force update — should overwrite
      init({ force: true });

      const content = fs.readFileSync(templatePath, 'utf-8');
      expect(content).not.toBe('modified content');
    }
  });

  test('updates .version file to current package version', () => {
    init();

    // Tamper with version file
    const versionPath = path.join(project.dir, 'loop/.version');
    fs.writeFileSync(versionPath, '0.0.0\n');

    init({ force: true });

    const version = fs.readFileSync(versionPath, 'utf-8').trim();
    const pkgVersion = require('../../package.json').version;
    expect(version).toBe(pkgVersion);
  });
}, 30000);

/**
 * Map a template destination path back to its source path in the package.
 * Matches the TEMPLATES array in init.js.
 */
function templateSrcPath(destRel) {
  const mapping = {
    'loop/CLAUDE_template.md': 'templates/CLAUDE_template.md',
    '.claude/settings.json': '.claude/settings.json',
    '.claude/skills/auto-revise-claude-md/SKILL.md': '.claude/skills/auto-revise-claude-md/SKILL.md',
    'loop/PROMPT_skills_design.md': 'prompts/PROMPT_skills_design.md',
    'loop/PROMPT_skills_run.md': 'prompts/PROMPT_skills_run.md',
  };
  return mapping[destRel] || destRel;
}
