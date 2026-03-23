// src/lib/config-parser.js
const fs = require('fs');
const yaml = require('js-yaml');

function interpolateVars(obj) {
  if (typeof obj === 'string') {
    return obj.replace(/\$\{([^}]+)\}/g, (_, varName) => {
      const val = process.env[varName];
      if (val === undefined) {
        process.stderr.write(`Warning: unresolved variable \${${varName}}\n`);
        return '';
      }
      return val;
    });
  }
  if (Array.isArray(obj)) return obj.map(interpolateVars);
  if (obj && typeof obj === 'object') {
    const result = {};
    for (const [k, v] of Object.entries(obj)) result[k] = interpolateVars(v);
    return result;
  }
  return obj;
}

function mergeConfig(defaults, envOverrides) {
  if (!envOverrides) return { ...defaults };
  const merged = {};
  const allKeys = new Set([...Object.keys(defaults), ...Object.keys(envOverrides)]);
  for (const key of allKeys) {
    const def = defaults[key];
    const env = envOverrides[key];
    if (env === undefined) { merged[key] = def; continue; }
    if (def === undefined) { merged[key] = env; continue; }
    if (Array.isArray(def) && Array.isArray(env)) {
      // Deduplicate by 'name' for objects, by value for strings
      const combined = [...def, ...env];
      if (combined.length > 0 && typeof combined[0] === 'object' && combined[0].name) {
        const seen = new Map();
        for (const item of combined) seen.set(item.name, item);
        merged[key] = [...seen.values()];
      } else {
        merged[key] = [...new Set(combined)];
      }
    } else if (def && typeof def === 'object' && !Array.isArray(def) && env && typeof env === 'object' && !Array.isArray(env)) {
      merged[key] = mergeConfig(def, env);
    } else {
      merged[key] = env; // scalar override
    }
  }
  return merged;
}

const REQUIRED_FIELDS = [
  'git.personal.name',
  'git.personal.email',
];

function getNestedValue(obj, path) {
  return path.split('.').reduce((o, k) => o && o[k], obj);
}

function validateConfig(config) {
  const missing = REQUIRED_FIELDS.filter(f => !getNestedValue(config, f));
  if (missing.length > 0) {
    throw new Error(`Missing required fields: ${missing.join(', ')}`);
  }
}

function loadConfig(configPath, env) {
  const raw = fs.readFileSync(configPath, 'utf8');
  const doc = yaml.load(raw);
  const defaults = doc.defaults || {};
  const environments = doc.environments || {};

  const envOverrides = env ? (environments[env] || {}) : {};
  const merged = mergeConfig(defaults, envOverrides);
  validateConfig(merged);
  return interpolateVars(merged);
}

function flattenSection(obj, prefix = '') {
  const lines = [];
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}_${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      lines.push(...flattenSection(v, key));
    } else {
      lines.push(`${key.toUpperCase()}=${v}`);
    }
  }
  return lines;
}

function flattenPlugins(config) {
  const plugins = config.plugins || {};
  const result = [];
  for (const name of (plugins.marketplace || [])) {
    result.push({ name, type: 'marketplace' });
  }
  for (const name of (plugins.lsp || [])) {
    result.push({ name, type: 'marketplace' });
  }
  return result;
}

module.exports = { loadConfig, mergeConfig, interpolateVars, validateConfig, flattenSection, flattenPlugins };

if (require.main === module) {
  const args = process.argv.slice(2);
  const getArg = (name) => {
    const idx = args.indexOf(`--${name}`);
    return idx >= 0 && idx + 1 < args.length ? args[idx + 1] : null;
  };

  const configPath = getArg('config');
  const env = getArg('env');
  const section = getArg('section');
  const showAll = args.includes('--all');

  if (!configPath) {
    process.stderr.write('Error: --config <path> is required\n');
    process.exit(1);
  }

  try {
    const config = loadConfig(configPath, env);

    if (showAll) {
      process.stdout.write(JSON.stringify(config, null, 2) + '\n');
    } else if (section) {
      // Special computed section
      if (section === 'plugins_flat') {
        process.stdout.write(JSON.stringify(flattenPlugins(config), null, 2) + '\n');
      } else {
        const value = config[section];
        if (value === undefined) {
          process.stdout.write('[]\n');
        } else if (typeof value === 'object') {
          process.stdout.write(JSON.stringify(value, null, 2) + '\n');
        } else {
          // Scalar value — flat KEY=value output
          process.stdout.write(`${section.toUpperCase()}=${value}\n`);
        }
      }
    } else {
      process.stderr.write('Error: --section <name> or --all is required\n');
      process.exit(1);
    }
  } catch (err) {
    process.stderr.write(`Error: ${err.message}\n`);
    process.exit(1);
  }
}
