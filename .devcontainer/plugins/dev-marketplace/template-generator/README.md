# Template Generator Plugin

Generate design system HTML templates with a guided style questionnaire or automatic context detection using the `frontend-design` skill.

## Features

- **Interactive mode**: Guided questionnaire to define design preferences
- **Random mode**: Auto-detect project context and generate templates without questions
- Generates multiple template proposals in one go
- Creates standalone HTML files with embedded CSS
- Supports various aesthetic directions (brutalist, swiss, neon-cyber, etc.)
- Customizable output directory and proposal count

## Usage

### Basic Usage

```
/generate-template
```

This launches an interactive questionnaire asking about:
1. **Project Purpose** - Dashboard, landing page, e-commerce, etc.
2. **Aesthetic Direction** - Brutalist, swiss, editorial, neon-cyber, etc.
3. **Color Theme** - Light, dark, high contrast, warm/cool palettes
4. **Typography Style** - Monospace, serif, sans-serif, display

### With Options

```
/generate-template --count 5
```
Generate 5 template proposals instead of the default 3.

```
/generate-template --output my-templates
```
Save templates to `my-templates/` directory instead of `templates/`.

```
/generate-template -c 4 -o designs
```
Short form: generate 4 templates in `designs/` folder.

### Random Mode (Auto-Detection)

```
/generate-template --random
```
Skip the questionnaire and auto-generate templates based on detected project context.

```
/generate-template --random --count 5
```
Generate 5 auto-detected templates.

**How context detection works:**

The agent analyzes your project to determine appropriate aesthetics:

| Detection Method | Project Type | Aesthetic Pool |
|------------------|--------------|----------------|
| `react`, `vue`, `angular` in package.json | Web Application | Glassmorphism, Swiss, Brutalist, Neon |
| `next`, `nuxt`, `gatsby` in package.json | JAMstack | Swiss, Japanese Minimalism, Editorial |
| `dashboard/`, `admin/`, `analytics/` dirs | SaaS Dashboard | Swiss, Scandinavian, Glassmorphism |
| `products/`, `cart/`, `checkout/` dirs | E-commerce | Scandinavian, Luxury, Organic |
| `posts/`, `blog/`, `content/` dirs | Blog/Content | Editorial, Swiss, Japanese Minimalism |
| `tailwind.config.*` detected | Modern utility-first | Swiss, Scandinavian |
| No specific patterns | Fallback | Random from full pool |

Each generated template has a unique combination of:
- Aesthetic direction (from detected pool)
- Color theme (dark/light/contrast - no duplicates)
- Typography style (matching the aesthetic)

## Generated Template Structure

Each template is a self-contained HTML file containing:

- Color palette swatches
- Typography specimens (H1-H6, body, small text)
- Spacing/grid system visualization
- Button variants (primary, secondary, accent, ghost) and sizes
- Form elements (inputs, labels, error/disabled states)
- Card components (standard, accent, interactive)
- Badges/labels
- Example layout (header, hero section, footer)

## Template Styles

Available aesthetic directions:

| Style | Description |
|-------|-------------|
| Brutalist | Raw, exposed structure, monospace fonts, hard edges |
| Swiss/Minimal | Clean grids, typography-focused, systematic |
| Editorial/Geometric | Magazine-like, asymmetric, bold typography |
| Neon/Cyber | Dark themes, glowing accents, futuristic |
| Retro/Vintage | Nostalgic, textured, warm colors |
| Organic/Nature | Soft shapes, earthy tones, flowing layouts |
| Luxury/Refined | Elegant, premium feel, subtle animations |
| Playful/Toy-like | Bright colors, rounded shapes, fun interactions |

## Installation

### In DevContainer (automatic)

The plugin is automatically installed after DevContainer rebuild via `setup-env.sh`. It registers `dev-marketplace` as a local marketplace and installs plugins globally.

### Manual installation

```bash
# Add local marketplace
claude plugin marketplace add /path/to/dev-marketplace

# Install plugin globally
claude plugin install template-generator@dev-marketplace --scope user
```

### Verify installation

```bash
# Check marketplace is registered
claude plugin marketplace list

# Check plugin is enabled in settings
cat ~/.claude/settings.json | jq '.enabledPlugins'
```

## Requirements

- `frontend-design` plugin must be installed (from Claude plugins marketplace)

## Author

Mirek Zaniewicz
