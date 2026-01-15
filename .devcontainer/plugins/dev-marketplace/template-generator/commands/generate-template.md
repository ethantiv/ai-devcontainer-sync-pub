---
description: Generate design system HTML templates with guided questionnaire or auto-detection
argument-hint: [--count N] [--output DIR] [--random]
allowed-tools: Read, Write, Glob, AskUserQuestion
---

Generate design system HTML template(s) using the template-generator agent.

Parse arguments from: $ARGUMENTS
- `--count N` or `-c N`: Number of template proposals to generate (default: 3)
- `--output DIR` or `-o DIR`: Output directory for templates (default: templates)
- `--random` or `-r`: Skip questionnaire, auto-detect project context

**Mode Selection:**
- **Interactive mode (default):** Ask one question about project mood, then delegate to `frontend-design` skill
- **Random mode (`--random`):** Analyze project context (package.json, structure), then delegate to `frontend-design` skill

Launch the template-generator agent to:
1. Parse command arguments
2. If `--random`: Detect project type from package.json and directory structure
3. Otherwise: Ask one question about desired mood (minimalist/bold/elegant/playful)
4. Delegate all aesthetic decisions to the `frontend-design` skill
5. Generate templates with required HTML structure (colors, typography, buttons, forms, cards)
6. Save to output directory
