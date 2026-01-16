---
description: Generate self-contained HTML design system templates with embedded CSS and theming
argument-hint: <project-name> [count]
---

# Design System Template Generator

<context>
You are generating comprehensive design system documentation pages. The output is a single, self-contained HTML file that showcases all design tokens and components. This serves as both documentation and a living style guide.

Use the `frontend-design` skill to make bold, distinctive aesthetic choices. Do not create generic, cookie-cutter design systems.
</context>

<arguments>
- `$1` (project-name): Name for the design system (default: "design-system")
- `$2` (count): Number of distinct template variants to generate in parallel (default: 1, max: 5)

**Argument parsing logic:**
1. If `$1` is a number 1-5 and `$2` is empty → treat `$1` as count, use default project name
   - `/design-system 3` → project="design-system", count=3
2. If `$1` is text and `$2` is a number → standard parsing
   - `/design-system my-app 3` → project="my-app", count=3
3. If only `$1` is provided and it's text → single template
   - `/design-system my-app` → project="my-app", count=1
4. If no arguments → defaults
   - `/design-system` → project="design-system", count=1

When count > 1, launch parallel agents to generate different aesthetic directions simultaneously.
</arguments>

<requirements>
Each generated HTML file must include:

1. **Embedded CSS** - No external stylesheets, all styles in `<style>` block
2. **Google Fonts** - Import 2-3 distinctive font families (display + body + optional mono)
3. **CSS Custom Properties** - Full theming system with:
   - Color palette (primary, secondary, accent, neutral scales)
   - Typography scale (font sizes, line heights, font weights)
   - Spacing scale (4px base or similar)
   - Border radii, shadows, transitions
4. **Responsive Design** - Mobile breakpoint at 768px minimum
</requirements>

<template_sections>
The HTML must include all these documented sections:

## 1. Color Palette
- Primary colors (5 shades: 100-900)
- Secondary colors (5 shades)
- Accent colors (5 shades)
- Neutral/gray scale (full range)
- Semantic colors (success, warning, error, info)
- Visual swatches showing each color with hex values

## 2. Typography Specimens
- Display/Hero text examples
- H1-H6 headings with actual rendered examples
- Body text (regular, bold, italic)
- Small/caption text
- Code/monospace text
- Show font family, size, weight, line-height for each

## 3. Spacing & Grid System
- Visual representation of spacing scale (4, 8, 12, 16, 24, 32, 48, 64px)
- Container max-widths
- Grid column examples (12-column or similar)

## 4. Buttons
All variants in multiple sizes (sm, md, lg):
- Primary button
- Secondary button
- Accent button
- Ghost/outline button
- Disabled states for each
- With icons (left/right)

## 5. Form Elements
- Text inputs (default, focus, error, disabled)
- Labels with required indicator
- Helper text and error messages
- Textareas
- Select dropdowns
- Checkboxes and radio buttons
- Toggle switches

## 6. Cards
- Standard card
- Accent/highlighted card
- Interactive/hoverable card
- Card with image
- Card with footer actions

## 7. Badges & Labels
- Status badges (success, warning, error, info, neutral)
- Size variants
- With/without icons
- Pill vs rounded rectangle

## 8. Example Layout Composition
A real-world example showing components in context:
- Header with navigation
- Hero section
- Content section with cards grid
- Footer
</template_sections>

<parallel_execution>
When count argument is provided (e.g., `/design-system my-app 3`):

1. Parse the count value from `$2` (default: 1, max: 5)
2. Launch N parallel agents using Task tool, each generating a distinct aesthetic direction:
   - Variant 1: Modern minimalist (clean lines, subtle shadows, neutral palette)
   - Variant 2: Bold vibrant (saturated colors, strong typography, playful elements)
   - Variant 3: Elegant sophisticated (serif accents, refined spacing, muted tones)
   - Variant 4: Tech/futuristic (gradients, glassmorphism, neon accents)
   - Variant 5: Warm organic (earth tones, rounded shapes, natural feel)

Each agent receives:
- Unique aesthetic direction
- Same technical requirements
- Different output filename: `templates/<project-name>-variant-N.html`

If you intend to call multiple agents and there are no dependencies between the calls, make all calls in parallel to maximize efficiency.
</parallel_execution>

<output_specification>
1. **Location**: Save to `templates/` directory
   - Single template: `templates/<project-name>-design-system.html`
   - Multiple variants: `templates/<project-name>-variant-1.html`, `-variant-2.html`, etc.
   - Create `templates/` directory if it doesn't exist

2. **File Structure**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Project Name] Design System</title>
    <!-- Google Fonts imports -->
    <style>
        /* CSS Custom Properties */
        :root { ... }
        /* Dark theme variant */
        [data-theme="dark"] { ... }
        /* All component styles */
    </style>
</head>
<body>
    <!-- Theme toggle -->
    <!-- Navigation/TOC -->
    <!-- All sections -->
    <script>
        /* Theme toggle functionality */
        /* Any interactive demos */
    </script>
</body>
</html>
```

3. **Quality Requirements**:
   - Valid HTML5
   - Accessible (proper ARIA labels, color contrast)
   - Working theme toggle (light/dark)
   - Smooth transitions on interactive elements
</output_specification>

<execution>
1. Parse arguments using the logic above:
   - Check if `$1` is a number 1-5 with no `$2` → count=`$1`, project="design-system"
   - Otherwise → project=`$1` or default, count=`$2` or 1
2. Create `templates/` directory if needed
3. If count == 1: Generate single template directly
4. If count > 1: Launch parallel Task agents with distinct aesthetic directions
5. Apply `frontend-design` skill principles for each variant
6. Report completion with all generated file paths
</execution>
