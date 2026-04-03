const PRESETS = {
  web: {
    description: 'Web frontend (React, Next.js, UI design)',
    skills: ['frontend-design:frontend-design', 'web-design-guidelines',
             'vercel-composition-patterns', 'vercel-react-best-practices'],
  },
  devops: {
    description: 'Infrastructure & DevOps (Terraform, cloud)',
    skills: ['terraform-style-guide', 'terraform-test', 'refactor-module'],
  },
};

function resolveTypes(commaString) {
  const types = commaString.split(',').map(t => t.trim()).filter(Boolean);
  const unknown = types.filter(t => !PRESETS[t]);
  if (unknown.length) {
    const valid = Object.keys(PRESETS).join(', ');
    throw new Error(`Unknown type(s): ${unknown.join(', ')}. Valid types: ${valid}`);
  }

  const skills = [...new Set(types.flatMap(t => PRESETS[t].skills))];
  return { design: skills, run: skills };
}

module.exports = { PRESETS, resolveTypes };
