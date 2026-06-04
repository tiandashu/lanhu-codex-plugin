# Code Restoration Precision Rules

Use `scripts/restore_lanhu.py` as the first implementation baseline after Lanhu data has been fetched.

## Baseline Strategy

The generator creates a static HTML parity baseline by:

- reading `<name>.schema.json`
- replacing Lanhu remote image URLs with paths from `<name>.image_mapping.json`
- flattening visible layers onto the page using absolute `rowDims`
- preserving width, height, left, top, z-index, colors, typography, overflow, background, radius, shadow, opacity, and flex metadata where available
- emitting `parity-report.json`

This baseline is deliberately literal. Use it to reduce drift before translating into a project framework.

## Framework Translation

When moving from generated HTML to React, Vue, Flutter, or other project code:

- keep the generated CSS values as the numeric source of truth
- preserve local asset paths and imports
- translate direct absolute layout only when the target project clearly needs a responsive abstraction
- if replacing generated blocks with existing components, compare every affected size, color, font, radius, and asset afterward
- keep generated `parity-report.json` as evidence for node counts and remote URL checks

## Visual Checks

After generation:

```bash
python scripts/restore_lanhu.py --input-dir ./lanhu_output --output-dir ./lanhu_output/restore
```

Serve from the fetch output directory, not from the `restore` subdirectory, so `../assets/...` paths resolve:

```bash
python -m http.server 8766 --bind 127.0.0.1 --directory ./lanhu_output
```

Then open:

```text
http://127.0.0.1:8766/restore/index.html
```

Required checks:

- page size matches schema root width and height
- all generated `<img>` elements have non-zero natural dimensions
- generated HTML contains no `http://` or `https://` Lanhu asset URLs
- text nodes match schema content, including non-breaking spaces
- local backgrounds and image slices render
- `parity-report.json` has `remote_url_count: 0`
