# Template Generator Plugin

Generate design system HTML templates by delegating aesthetic decisions to the `frontend-design` skill.

## Features

- **Interactive mode**: One question about project mood, then full delegation to `frontend-design`
- **Random mode**: Auto-detect project context and delegate to `frontend-design`
- Generates multiple template proposals in one go
- Creates standalone HTML files with embedded CSS
- Customizable output directory and proposal count

## Usage

### Basic Usage

```
/generate-template
```

This asks one question about project mood:
- **Minimalist** - clean, calm, lots of whitespace
- **Bold** - strong colors, expressive elements
- **Elegant** - refined, premium, subtle
- **Playful** - colorful, friendly, rounded
- **Corporate** - professional, trustworthy, structured
- **Futuristic** - tech-forward, modern, innovative
- **Organic** - natural, earthy, soft shapes
- **Dark & Dramatic** - moody, high contrast, cinematic
- **Retro** - nostalgic, vintage vibes, warm tones

The `frontend-design` skill then determines all aesthetic details (colors, typography, animations).

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

The agent analyzes your project to provide context to `frontend-design`:

| Detection Method | Project Type |
|------------------|--------------|
| `react`, `vue`, `angular` in package.json | Web Application |
| `next`, `nuxt`, `gatsby` in package.json | JAMstack |
| `dashboard/`, `admin/`, `analytics/` dirs | SaaS Dashboard |
| `products/`, `cart/`, `checkout/` dirs | E-commerce |
| `posts/`, `blog/`, `content/` dirs | Blog/Content |

The `frontend-design` skill uses this context to select appropriate aesthetics.

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

## How It Works

This plugin does NOT define aesthetics itself. Instead:

1. **Collects minimal input** (mood or project context)
2. **Delegates to `frontend-design` skill** for all design decisions
3. **Generates HTML** following the required structure
4. **Saves templates** with descriptive filenames

The `frontend-design` skill (from `frontend-design@claude-plugins-official`) handles:
- Aesthetic direction selection
- Color palette and theme choices
- Typography selection
- Animation and interaction style

## Installation

### In DevContainer (automatic)

The plugin is automatically installed after DevContainer rebuild via `setup-env.sh`.

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

# Check plugin is enabled
cat ~/.claude/settings.json | jq '.enabledPlugins'
```

## Requirements

- `frontend-design` plugin must be installed (from Claude plugins marketplace)

## Author

Mirek Zaniewicz
