---
name: lanhu-restore-design
description: "Restore Lanhu designs into target project code with high visual fidelity. Use when the user provides a Lanhu URL and wants a screen/page/component implemented in React, Next.js, Vue, Nuxt, Flutter, Android, iOS, or standalone HTML. This is the high-level orchestration skill; load lanhu-use, lanhu-fetch-design, lanhu-generate-baseline, and lanhu-verify-parity as needed."
---

# Lanhu Design Restoration

This skill orchestrates end-to-end Lanhu design restoration. It turns a Lanhu design into maintainable project code by fetching structured design data, localizing assets, generating an interactive parity baseline, implementing from schema values, and verifying visual plus behavioral parity.

Use the smaller Lanhu skills for focused phases:

- `lanhu-use`: authentication, script safety, URL parsing, and error recovery.
- `lanhu-fetch-design`: list/fetch designs and produce local schema, tokens, preview, and assets.
- `lanhu-design-system`: inspect local design docs, components, styles, variables, and tokens before implementation.
- `lanhu-generate-baseline`: create the interactive HTML parity checkpoint.
- `lanhu-verify-parity`: validate baseline and final implementation.

## Core Rule

Restore from real artifacts, not from memory. Use `.schema.json` as the source of truth, preview PNG for visible-frame confirmation, and project conventions for production code structure.

## Prerequisites

- Python 3.10+
- `httpx`, Playwright, and Pillow installed from the plugin `requirements.txt`
- Playwright Chromium installed with `python -m playwright install chromium`
- Lanhu authentication saved locally by `scripts/lanhu_auth.py login`

For authentication and endpoint rules, load `lanhu-use`. For code restoration precision rules, read `references/codegen-precision.md` when implementing.

## Locate The Plugin Root

When invoked from this plugin, the fetch script is:

```bash
python <plugin-root>/scripts/fetch_lanhu.py
```

If unsure where the plugin root is, use the directory that contains this skill's parent `skills/` folder.

## Required Workflow

Follow these steps in order. Do not write production UI code before local design artifacts and the baseline exist.

### Step 1: Fetch Design Artifacts

Use `lanhu-fetch-design`.

Expected artifacts:

- `<name>.schema.json`: authoritative layer tree and styles
- `<name>.tokens.txt`: supplemental high-risk visual attributes
- `<name>.png`: full design preview for visible-frame checking
- `assets/slices/img_N.*`: localized image assets
- `<name>.image_mapping.json`: local path to remote URL mapping
- optional `<name>.official.html` and `<name>.official.css`: reference-only official generated code

### Step 2: Inspect The Target Project And Design System

Before writing code, inspect the user's repository:

- `package.json` with React or Next.js dependencies: implement React/Next.js conventions
- `package.json` with Vue or Nuxt dependencies: implement Vue/Nuxt conventions
- `pubspec.yaml`: implement Flutter conventions
- `build.gradle` or `AndroidManifest.xml`: implement Android conventions
- `Podfile` or `Package.swift`: implement iOS/SwiftUI conventions
- otherwise, create a standalone HTML implementation

Also detect the style system: CSS Modules, scoped Vue styles, SCSS, Tailwind, Styled Components, global CSS, or the existing local pattern.

If a root `DESIGN.md` or equivalent design-system document exists, read it before generating code. Use it for tokens, themes, reusable components, naming, accessibility, directory layout, and style conventions. Concrete layer values still come from `.schema.json`; if there is an unavoidable conflict, preserve visual parity and report the tradeoff.

Use `lanhu-design-system` to generate a local report before planning implementation:

```bash
python <plugin-root>/scripts/inspect_design_system.py \
  --project-root <target-project-root> \
  --output <artifact-dir>/design-system-report.json
```

Run focused searches when the Lanhu design contains clear reusable controls:

```bash
python <plugin-root>/scripts/inspect_design_system.py \
  --project-root <target-project-root> \
  --query "button primary"
```

Treat the report as the local equivalent of component and variable search. Reuse discovered components, CSS selectors, and tokens only when they preserve schema dimensions, visual fidelity, and required interaction states.

### Step 3: Generate Interactive Baseline

Use `lanhu-generate-baseline`.

Create `restore/index.html` and `restore/parity-report.json` before framework translation. Use the generated baseline as the first fidelity checkpoint for static visuals, inferred interactions, and component extraction planning.

Read these report fields before coding:

- `interaction_contracts`: the behavior contract for each inferred control, including role, action, label, group, bounds, expected behavior, and required state attributes.
- `component_candidates`: suggested extraction boundaries based on semantics, repeated structures, visible descendants, and interaction density.
- `interaction_roles`: quick coverage summary for controls found in the design.

### Step 4: Plan The Implementation

Before editing app code, identify:

- target route/component/file
- framework and styling convention
- required local assets
- visible sections in the preview PNG
- repeated or semantic components worth extracting from `component_candidates`
- controls and flows from `interaction_contracts` that must be real in code, not static shapes
- project design-system rules, components, tokens, and variables that must be respected or intentionally bypassed

Prefer a page-level component first. Extract child components only when they are repeated, have a clear business boundary, or map to obvious reusable UI modules such as cards, list items, navigation, forms, dialogs, and tabs.

Use component extraction levels deliberately:

- Page/screen wrapper: always useful for route-level layout and asset wiring.
- Section components: use for large semantic regions such as headers, navigation, forms, list sections, dialogs, or dashboards.
- Item components: use for repeated cards, rows, list items, tabs, menu items, or option controls.
- Primitive wrappers: only use existing project/design-system primitives; do not create new one-off primitives for decorative shapes.

### Step 5: Implement From Schema

Authority order:

```text
schema.json > optional official HTML/CSS > tokens.txt > preview PNG
```

Use `.schema.json` as the source of truth for all dimensions, coordinates, colors, typography, spacing, border radius, shadows, gradients, opacity, and layout values.

Use the preview `.png` to determine what is visible in the current frame. Skip hidden layers, alternate interaction states, covered screens, and invisible overlays unless the user explicitly asks for those states.

Suggested HTML mapping:

- `lanhutext`: `span` or semantic text element
- `lanhuimage`: `img`
- `lanhubutton`: `button`
- input-like layers: `input`, `textarea`, or the target platform equivalent
- tab/switch/select-like layers: real native or project design-system controls with visible state changes
- other/container layers: `div` or the target platform equivalent

Keep class names semantic. For CSS and SCSS, prefer BEM-style kebab-case names such as `study-card__title` instead of generated names such as `group_4`.

Do not use Lanhu CDN URLs in generated app code. Reference local assets from `assets/slices` and adapt imports to the project framework.

## Style Rules

- Preserve CSS values exactly; do not round, simplify, or convert `rgba()` to hex.
- Preserve multi-stop gradients. Do not collapse gradients into flat colors.
- Preserve non-uniform radius as four values in top-left, top-right, bottom-right, bottom-left order.
- Preserve all shadows, including multiple and inset shadows.
- If `opacity` applies to a node with gradient or image fill, apply opacity to the wrapper rather than mixing alpha into child colors.
- Preserve `flexGap` as `gap` or the target platform equivalent.
- For fixed-size flex-centered containers, ignore schema padding when that padding would shrink centered content under `box-sizing: border-box`; use flex centering as the alignment source.

## Implementation Strategy

- Match the repository's existing component and style patterns before introducing new ones.
- Keep generated code maintainable: semantic class names, readable component boundaries, no raw Lanhu layer names such as `group_4` unless no better semantic name exists.
- Use local helper components and design tokens when they preserve parity.
- Avoid adding abstractions for one-off decorative shapes, separators, simple icon wrappers, or tiny structures with fewer than three meaningful elements.
- Keep assets close to the target app's existing asset convention.

## Incremental Workflow

Borrow Figma's incremental pattern: inspect, create a stable wrapper/page, implement one section at a time, validate, then continue. For larger screens:

1. Implement the page shell and asset wiring.
2. Implement one visible section.
3. Render or run a targeted check.
4. Fix issues before moving to the next section.
5. Run final parity checks after all sections are complete.

Do not build on a broken baseline or a section with known visual drift.

## Interaction Parity

Do not leave visually interactive elements inert. Restore behavior for:

- primary and secondary actions
- links and navigation affordances
- text inputs, search fields, password fields, and verification-code fields
- tabs, segmented controls, radios, checkboxes, switches, and selects
- dialogs, drawers, popovers, dropdown menus, and close/back affordances
- disabled, selected, focused, loading, and active states when they are visible or implied by layer names

The generated baseline uses heuristics from layer type, layer name, text, and children to expose likely controls. In production code, confirm the correct behavior from the product context and existing app conventions.

For each `interaction_contracts` entry:

- Implement the expected behavior or map it to an existing product flow.
- Preserve keyboard access and visible focus for buttons, links, inputs, tabs, toggles, selects, dialogs, and dismiss actions.
- Maintain grouped state for tabs, radios, segmented controls, and select-like controls.
- Report any contract that cannot be implemented because the product route, data source, or destination is unknown.

## Use Tokens As A Gap Check

Read `<name>.tokens.txt` after implementation. Only use it when the schema-derived implementation appears to be missing a complex visual property. Never overwrite a schema value with a token summary.

## Verify Parity

Use `lanhu-verify-parity` before finishing. At minimum, compare generated code against the schema and preview image:

- fixed dimensions remain fixed where required
- clipping and overflow match
- colors and gradients match
- absolute positions and flex layout values match
- font family, size, weight, and line-height are restored
- margins, padding, and gaps are preserved
- local images are used and visible
- visible elements from the PNG are present
- visible controls are keyboard-accessible and trigger observable state changes
- every relevant `interaction_contracts` item is implemented, tested, or explicitly deferred
- extracted components match `component_candidates` or have a clearer project-specific boundary
- no Lanhu CDN URL remains in app code
- complex radius, shadow, opacity, and gradient values are complete
- components are not over-split and names are semantic
- `DESIGN.md` conventions were followed when present

Fix implementation errors immediately. In the final response, summarize what was implemented, what verification ran, and any intentional platform adaptations.

## Error Recovery

On any failed fetch, baseline generation, app build, or parity check:

1. Stop and read the actual error.
2. Determine whether the failing phase is auth, fetch, baseline, implementation, or verification.
3. Use the relevant smaller Lanhu skill rather than retrying the entire workflow.
4. Preserve user code changes and make the smallest targeted fix.
5. Re-run the failed check before reporting completion.
