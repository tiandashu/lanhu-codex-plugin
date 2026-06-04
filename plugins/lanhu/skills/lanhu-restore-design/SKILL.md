---
name: lanhu-restore-design
description: Restore Lanhu designs into target project code. Use when the user provides a Lanhu URL, asks to fetch Lanhu schema/assets, or wants a Lanhu design implemented with high visual fidelity.
---

# Lanhu Design Restoration

This skill turns a Lanhu design into maintainable project code by fetching structured design data, localizing assets, implementing from schema values, and checking parity.

## Prerequisites

- Python 3.10+
- `httpx` and `python-dotenv` installed from the plugin `requirements.txt`
- Playwright Chromium installed with `python -m playwright install chromium`
- Lanhu authentication saved locally by `scripts/lanhu_auth.py login`

Treat the Lanhu cookie as a secret. Do not print it, commit it, or copy it into generated source code.

Do not ask the user to configure `LANHU_COOKIE`. Use the local login helper:

```bash
python <plugin-root>/scripts/lanhu_auth.py login --url "$LANHU_URL"
```

The helper opens an interactive browser window, lets the user complete Lanhu or team SSO login, captures Lanhu cookies, and encrypts them locally with Windows DPAPI. `fetch_lanhu.py` decrypts that cookie store automatically on later runs.

Reuse the saved encrypted cookie store by default. Do not rerun login unless the cookie store is missing, expired, cleared, or Lanhu returns an auth/permission error for the requested team/project.

If login status is unclear:

```bash
python <plugin-root>/scripts/lanhu_auth.py status
```

If the saved cookies are expired or belong to the wrong team:

```bash
python <plugin-root>/scripts/lanhu_auth.py clear
python <plugin-root>/scripts/lanhu_auth.py login --url "$LANHU_URL"
```

For endpoint details, see `references/lanhu-api.md`.
For code restoration precision rules, see `references/codegen-precision.md`.

## Locate The Plugin Root

When invoked from this plugin, the fetch script is:

```bash
python <plugin-root>/scripts/fetch_lanhu.py
```

If unsure where the plugin root is, use the directory that contains this skill's parent `skills/` folder.

## Step 1: List Designs

If the user did not provide a design index/name and the URL does not include a design id, list available designs:

```bash
python <plugin-root>/scripts/fetch_lanhu.py --url "$LANHU_URL"
```

Show the compact JSON list to the user and ask which `index` or exact `name` to restore.

If the URL contains `image_id`, skip user selection and fetch that design directly.

## Step 2: Fetch Design Data

Fetch the selected design:

```bash
python <plugin-root>/scripts/fetch_lanhu.py \
  --url "$LANHU_URL" \
  --design "$DESIGN_TARGET" \
  --download-images \
  --output-dir "$OUTPUT_DIR"
```

Only add `--download-code` when the user explicitly requests official Lanhu generated HTML/CSS. Official code is slow to generate and is reference-only.

Expected outputs:

- `<name>.schema.json`: authoritative layer tree and styles
- `<name>.tokens.txt`: supplemental high-risk visual attributes
- `<name>.png`: full design preview for visible-frame checking
- `assets/slices/img_N.*`: localized image assets
- `<name>.image_mapping.json`: local path to remote URL mapping
- `<name>.official.html` and `<name>.official.css`: optional reference-only files when `--download-code` is used

## Step 3: Inspect The Target Project

Before writing code, inspect the user's repository:

- `package.json` with React or Next.js dependencies: implement React/Next.js conventions
- `package.json` with Vue or Nuxt dependencies: implement Vue/Nuxt conventions
- `pubspec.yaml`: implement Flutter conventions
- `build.gradle` or `AndroidManifest.xml`: implement Android conventions
- `Podfile` or `Package.swift`: implement iOS/SwiftUI conventions
- otherwise, create a standalone HTML implementation

Also detect the style system: CSS Modules, scoped Vue styles, SCSS, Tailwind, Styled Components, global CSS, or the existing local pattern.

If a root `DESIGN.md` or equivalent design-system document exists, read it before generating code. Use it for tokens, themes, reusable components, naming, accessibility, directory layout, and style conventions. Concrete layer values still come from `.schema.json`; if there is an unavoidable conflict, preserve visual parity and report the tradeoff.

## Step 4: Implement From Schema

Authority order:

```text
schema.json > optional official HTML/CSS > tokens.txt > preview PNG
```

Use `.schema.json` as the source of truth for all dimensions, coordinates, colors, typography, spacing, border radius, shadows, gradients, opacity, and layout values.

Use the preview `.png` to determine what is visible in the current frame. Skip hidden layers, alternate interaction states, covered screens, and invisible overlays unless the user explicitly asks for those states.

Before translating into a framework, generate a static parity baseline:

```bash
python <plugin-root>/scripts/restore_lanhu.py \
  --input-dir "$OUTPUT_DIR" \
  --output-dir "$OUTPUT_DIR/restore"
```

Use the generated `restore/index.html` and `restore/parity-report.json` as the first fidelity checkpoint. The baseline flattens visible layers with absolute `rowDims` and localizes image references, which reduces layout drift before React/Vue/Flutter translation.

Suggested HTML mapping:

- `lanhutext`: `span` or semantic text element
- `lanhuimage`: `img`
- `lanhubutton`: `button`
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

## Component Strategy

Start with a page-level component. Extract child components only when they are repeated, have a clear business boundary, or map to obvious reusable UI modules such as cards, list items, navigation, forms, dialogs, and tabs.

Avoid extracting one-off decorative shapes, separators, simple icon wrappers, or tiny structures with fewer than three meaningful elements.

## Step 5: Use Tokens As A Gap Check

Read `<name>.tokens.txt` after implementation. Only use it when the schema-derived implementation appears to be missing a complex visual property. Never overwrite a schema value with a token summary.

## Step 6: Verify Parity

Before finishing, compare generated code against the schema and preview image:

- fixed dimensions remain fixed where required
- clipping and overflow match
- colors and gradients match
- absolute positions and flex layout values match
- font family, size, weight, and line-height are restored
- margins, padding, and gaps are preserved
- local images are used and visible
- visible elements from the PNG are present
- no Lanhu CDN URL remains in app code
- complex radius, shadow, opacity, and gradient values are complete
- components are not over-split and names are semantic
- `DESIGN.md` conventions were followed when present

Fix implementation errors immediately. In the final response, summarize what was implemented, what verification ran, and any intentional platform adaptations.
