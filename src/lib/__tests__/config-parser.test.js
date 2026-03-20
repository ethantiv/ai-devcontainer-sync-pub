const fs = require('fs');
const path = require('path');
const os = require('os');
const { loadConfig, mergeConfig, interpolateVars, validateConfig, flattenSection } = require('../config-parser');

let tmpDir;
beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'config-parser-'));
});
afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

function writeYaml(name, content) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, content);
  return p;
}

describe('interpolateVars', () => {
  test('resolves env vars in strings', () => {
    process.env.TEST_VAR = 'hello';
    expect(interpolateVars('${TEST_VAR}')).toBe('hello');
    delete process.env.TEST_VAR;
  });

  test('warns and returns empty for unresolved vars', () => {
    const stderr = jest.spyOn(process.stderr, 'write').mockImplementation();
    expect(interpolateVars('${NONEXISTENT_VAR_XYZ}')).toBe('');
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining('NONEXISTENT_VAR_XYZ'));
    stderr.mockRestore();
  });

  test('recurses into objects and arrays', () => {
    process.env.TV1 = 'a';
    process.env.TV2 = 'b';
    const result = interpolateVars({ x: '${TV1}', y: ['${TV2}'] });
    expect(result).toEqual({ x: 'a', y: ['b'] });
    delete process.env.TV1;
    delete process.env.TV2;
  });

  test('passes through non-string primitives', () => {
    expect(interpolateVars(42)).toBe(42);
    expect(interpolateVars(true)).toBe(true);
    expect(interpolateVars(null)).toBe(null);
  });
});

describe('mergeConfig', () => {
  test('scalar override', () => {
    expect(mergeConfig({ a: 1 }, { a: 2 })).toEqual({ a: 2 });
  });

  test('appends and deduplicates string arrays', () => {
    expect(mergeConfig({ a: ['x', 'y'] }, { a: ['y', 'z'] }))
      .toEqual({ a: ['x', 'y', 'z'] });
  });

  test('appends and deduplicates object arrays by name', () => {
    const def = [{ name: 'a', v: 1 }, { name: 'b', v: 2 }];
    const env = [{ name: 'b', v: 3 }, { name: 'c', v: 4 }];
    const result = mergeConfig({ items: def }, { items: env });
    expect(result.items).toEqual([
      { name: 'a', v: 1 },
      { name: 'b', v: 3 },  // env overrides
      { name: 'c', v: 4 },
    ]);
  });

  test('deep merges nested objects', () => {
    expect(mergeConfig(
      { git: { personal: { name: 'A' }, work: { email: 'B' } } },
      { git: { personal: { name: 'C' } } }
    )).toEqual({ git: { personal: { name: 'C' }, work: { email: 'B' } } });
  });

  test('handles missing env overrides', () => {
    expect(mergeConfig({ a: 1 }, undefined)).toEqual({ a: 1 });
  });
});

describe('validateConfig', () => {
  test('passes with required fields', () => {
    expect(() => validateConfig({
      git: { personal: { name: 'Test', email: 'test@test.com' } }
    })).not.toThrow();
  });

  test('throws listing missing fields', () => {
    expect(() => validateConfig({ git: {} }))
      .toThrow('git.personal.name');
  });
});

describe('loadConfig', () => {
  test('loads and merges YAML with environment', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  git:
    personal:
      name: Test User
      email: test@example.com
  timezone: UTC
  plugins:
    marketplace:
      - plugin-a

environments:
  devcontainer:
    timezone: Europe/Warsaw
    plugins:
      marketplace:
        - plugin-b
`);
    const result = loadConfig(configPath, 'devcontainer');
    expect(result.timezone).toBe('Europe/Warsaw');
    expect(result.git.personal.name).toBe('Test User');
    expect(result.plugins.marketplace).toEqual(['plugin-a', 'plugin-b']);
  });

  test('throws on unknown environment', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  git:
    personal:
      name: Test
      email: test@test.com
environments:
  devcontainer: {}
`);
    expect(() => loadConfig(configPath, 'unknown'))
      .toThrow('Unknown environment');
  });

  test('throws on missing required fields', () => {
    const configPath = writeYaml('config.yaml', `
defaults:
  timezone: UTC
environments: {}
`);
    expect(() => loadConfig(configPath, null))
      .toThrow('git.personal.name');
  });
});

describe('flattenSection', () => {
  test('flattens nested object to KEY=value lines', () => {
    const result = flattenSection({ personal: { name: 'Test', email: 'e@e.com' } });
    expect(result).toContain('PERSONAL_NAME=Test');
    expect(result).toContain('PERSONAL_EMAIL=e@e.com');
  });
});
