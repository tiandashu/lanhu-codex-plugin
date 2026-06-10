---
name: lanhu-design-system
description: "Inspect and search the target project's local design system before implementing a Lanhu design. Use when a Lanhu-to-code workflow needs existing components, variables, tokens, CSS classes, DESIGN.md rules, or reusable style conventions. This fills the local equivalent of Figma design-system library search for Lanhu workflows."
---

# Lanhu Design System

Use this skill before translating Lanhu schema into production code. It discovers local design-system evidence so the implementation can reuse project components, variables, tokens, styles, and documented rules instead of creating one-off UI.

## What It Provides

- Reads `DESIGN.md`, `design-system.md`, `tokens.md`, and similar project rule documents.
- Indexes component declarations in React, Vue, Svelte, and TypeScript/JavaScript files.
- Indexes CSS, SCSS, Sass, and Less class selectors.
- Indexes likely design tokens and variables such as colors, spacing, radius, typography, shadows, breakpoints, and z-index values.
- Supports keyword search for component, token, and style candidates.
- Emits a JSON report that can be saved as implementation evidence.

## Inspect The Project

Run from the user's target project root, or pass the target app path explicitly:

```bash
python <plugin-root>/scripts/inspect_design_system.py \
  --project-root <target-project-root> \
  --output <artifact-dir>/design-system-report.json
```

For a focused search:

```bash
python <plugin-root>/scripts/inspect_design_system.py \
  --project-root <target-project-root> \
  --query "button primary" \
  --output <artifact-dir>/design-system-button.json
```

## How To Use The Report

Read these fields first:

- `design_docs`: project design-system documents to read before implementation.
- `components`: local component declarations that may map to Lanhu layers.
- `styles`: reusable CSS class selectors.
- `tokens`: likely variables and design tokens.
- `matches`: keyword hits for a focused search.

Use discovered assets when they preserve visual parity. Do not replace exact Lanhu schema values with a local token if doing so creates visible drift. If a design-system rule conflicts with schema values, preserve the requested screen's visual parity and report the tradeoff.

## Search Patterns

Search by visible role and product language:

- `button primary`
- `input search`
- `tab segmented`
- `modal dialog`
- `card list item`
- `color brand`
- `spacing gap`
- `radius shadow`

Prefer exact local components for interactive controls such as buttons, links, inputs, tabs, toggles, selects, dialogs, and navigation. Use local tokens for colors, spacing, typography, and radii when their values match or intentionally govern the project.

## Stop Conditions

Do not rely on the design-system report alone when:

- The report finds no relevant component or token candidates.
- A local component cannot match Lanhu size, state, or styling without heavy overrides.
- The project has no clear design-system documents or component library.
- The implementation target is standalone HTML and the user wants schema-first parity over project integration.

In those cases, implement directly from `.schema.json`, keep class names semantic, and mention that no local design-system match was available.
