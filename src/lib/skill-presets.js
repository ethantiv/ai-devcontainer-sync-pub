const PRESETS = {
  web: {
    description: 'Web frontend (React, Next.js, UI design)',
    plan: ['web-design-guidelines'],
    build: ['frontend-design:frontend-design', 'web-design-guidelines',
            'vercel-composition-patterns', 'vercel-react-best-practices',
],
  },
  devops: {
    description: 'Infrastructure & DevOps (Terraform, cloud)',
    plan: [],
    build: ['terraform-style-guide', 'terraform-test', 'refactor-module'],
  },
  docs: {
    description: 'Documentation & technical writing',
    plan: ['beautiful-mermaid', 'mermaid-diagrams'],
    build: ['beautiful-mermaid', 'mermaid-diagrams', 'visual-explainer',
            'humanizer', 'docx', 'pdf'],
  },
  fullstack: {
    description: 'Full-stack web application',
    plan: ['web-design-guidelines'],
    build: ['frontend-design:frontend-design', 'web-design-guidelines',
            'vercel-composition-patterns', 'vercel-react-best-practices',
            'feature-dev:feature-dev'],
  },
};

function resolveTypes(commaString) {
  const types = commaString.split(',').map(t => t.trim()).filter(Boolean);
  const unknown = types.filter(t => !PRESETS[t]);
  if (unknown.length) {
    const valid = Object.keys(PRESETS).join(', ');
    throw new Error(`Unknown type(s): ${unknown.join(', ')}. Valid types: ${valid}`);
  }

  const plan = [];
  const build = [];
  for (const type of types) {
    for (const skill of PRESETS[type].plan) {
      if (!plan.includes(skill)) plan.push(skill);
    }
    for (const skill of PRESETS[type].build) {
      if (!build.includes(skill)) build.push(skill);
    }
  }
  return { plan, build };
}

function listPresets() {
  return Object.entries(PRESETS).map(([name, { description }]) => ({ name, description }));
}

module.exports = { PRESETS, resolveTypes, listPresets };
