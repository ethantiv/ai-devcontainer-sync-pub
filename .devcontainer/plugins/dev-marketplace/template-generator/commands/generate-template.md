---
description: Generate design system HTML templates with guided questionnaire or auto-detection
argument-hint: [--count N] [--output DIR] [--random]
allowed-tools: Read, Write, Glob, AskUserQuestion
---

Generate design system HTML template(s) using the template-generator agent.

Parse arguments from: $ARGUMENTS
- `--count N` or `-c N`: Number of template proposals to generate (default: 3)
- `--output DIR` or `-o DIR`: Output directory for templates (default: templates)
- `--random` or `-r`: Skip questionnaire, auto-detect project context and generate templates with intelligent variation

**Mode Selection:**
- **Interactive mode (default):** The agent asks design preference questions
- **Random mode (`--random`):** The agent analyzes the current project (package.json, file structure, existing styles) to auto-detect context and generates N unique templates without asking questions

Launch the template-generator agent to:
1. If `--random`: Auto-detect project context using Glob/Read and generate templates
2. Otherwise: Ask the user a series of closed-ended questions about design preferences
3. Use the frontend-design skill to generate requested number of template proposals
4. Save templates to the specified output directory
