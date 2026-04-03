const fs = require('fs');
const path = require('path');
const os = require('os');
const { resolveTypes, PRESETS } = require('../skill-presets');

describe('resolveTypes', () => {
  test('returns same skills for design and run', () => {
    const result = resolveTypes('web');
    expect(result.design).toEqual(PRESETS.web.skills);
    expect(result.run).toEqual(PRESETS.web.skills);
    expect(result.design).toBe(result.run);
  });

  test('merges web,devops without overlap', () => {
    const result = resolveTypes('web,devops');
    expect(result.run).toEqual([
      ...PRESETS.web.skills,
      ...PRESETS.devops.skills,
    ]);
    expect(result.design).toBe(result.run);
  });

  test('throws on unknown type with valid types listed', () => {
    expect(() => resolveTypes('unknown')).toThrow(/Unknown type\(s\): unknown/);
    expect(() => resolveTypes('unknown')).toThrow(/Valid types:/);
    expect(() => resolveTypes('unknown')).toThrow(/web/);
  });

  test('throws on mixed valid and unknown types', () => {
    expect(() => resolveTypes('web,bogus')).toThrow(/bogus/);
  });

  test('handles whitespace in comma-separated list', () => {
    const result = resolveTypes(' web , devops ');
    expect(result.run).toEqual([...PRESETS.web.skills, ...PRESETS.devops.skills]);
  });

  test('devops returns same skills for design and run', () => {
    const result = resolveTypes('devops');
    expect(result.design).toEqual(PRESETS.devops.skills);
    expect(result.design).toBe(result.run);
  });
});

describe('init integration with types', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'loop-preset-'));
    fs.mkdirSync(path.join(tmpDir, 'loop'), { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('appendSkills adds skills to file', () => {
    const runPath = path.join(tmpDir, 'loop/PROMPT_skills_run.md');
    fs.writeFileSync(runPath, '- `superpowers:subagent-driven-development`\n- `agent-browser`\n');

    const content = fs.readFileSync(runPath, 'utf-8');
    const skills = ['frontend-design:frontend-design', 'web-design-guidelines'];
    const existing = skills.filter(s => !content.includes(s));
    const section = '\n# Project-specific skills (--type)\n'
      + existing.map(s => `- \`${s}\``).join('\n') + '\n';
    fs.writeFileSync(runPath, content.trimEnd() + '\n' + section);

    const updated = fs.readFileSync(runPath, 'utf-8');
    expect(updated).toContain('# Project-specific skills (--type)');
    expect(updated).toContain('frontend-design:frontend-design');
    expect(updated).toContain('web-design-guidelines');
    expect(updated).toContain('superpowers:subagent-driven-development');
    expect(updated).toContain('agent-browser');
  });

  test('does not duplicate skills already present', () => {
    const runPath = path.join(tmpDir, 'loop/PROMPT_skills_run.md');
    fs.writeFileSync(runPath, '- `agent-browser`\n- `web-design-guidelines`\n');

    const content = fs.readFileSync(runPath, 'utf-8');
    const skills = ['web-design-guidelines', 'frontend-design:frontend-design'];
    const newSkills = skills.filter(s => !content.includes(s));
    expect(newSkills).toEqual(['frontend-design:frontend-design']);
  });
});
