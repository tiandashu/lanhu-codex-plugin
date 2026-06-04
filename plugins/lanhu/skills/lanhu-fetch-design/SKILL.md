---
name: lanhu-fetch-design
description: "Fetch Lanhu design data into local artifacts. Use when the user asks to list Lanhu designs, fetch Lanhu schema, download preview PNGs, localize image assets, inspect Lanhu tokens, or prepare design artifacts before implementation. Load lanhu-use first for authentication, URL parsing, and script safety rules."
---

# Fetch Lanhu Design

Use this skill to produce the local design artifacts that downstream restoration work consumes. Always also load `lanhu-use` before running scripts.

## Workflow

### Step 1: Confirm Auth

Check cookie status:

```bash
python <plugin-root>/scripts/lanhu_auth.py status
```

If auth is missing or fails for the target project, run:

```bash
python <plugin-root>/scripts/lanhu_auth.py login --url "$LANHU_URL"
```

### Step 2: Resolve The Design Target

If the user did not provide a design index/name and the URL does not include `image_id`, list available designs:

```bash
python <plugin-root>/scripts/fetch_lanhu.py --url "$LANHU_URL"
```

Show the compact JSON list and ask the user which `index` or exact `name` to fetch.

If the URL includes `image_id`, skip selection and fetch directly.

### Step 3: Fetch Schema, Preview, Tokens, And Images

Fetch the selected design:

```bash
python <plugin-root>/scripts/fetch_lanhu.py \
  --url "$LANHU_URL" \
  --design "$DESIGN_TARGET" \
  --download-images \
  --output-dir "$OUTPUT_DIR"
```

Only add `--download-code` when the user explicitly requests official Lanhu generated HTML/CSS. Treat official code as reference-only; schema remains authoritative.

### Step 4: Verify The Artifact Set

Confirm these outputs exist:

- `.schema.json`
- `.tokens.txt`
- `.png`
- `.image_mapping.json`
- `assets/slices/`

If any asset is missing, do not continue to implementation until the cause is understood.

## Output Authority

Use artifacts in this order:

```text
schema.json > optional official HTML/CSS > tokens.txt > preview PNG
```

The schema is the source of truth for geometry, layout, typography, fills, strokes, radius, shadows, opacity, gradients, clipping, and asset references.

Use the preview PNG to understand visible-frame composition: what is actually visible, covered, hidden, or outside the selected screen.

Use `tokens.txt` only as a gap check for complex properties that may be easy to miss.

## Common Failure Handling

- Auth or permission failure: use `lanhu-use` auth recovery.
- Empty design list: verify `tid` and `pid`, then check team access.
- Missing assets: re-fetch with `--download-images`.
- Slow official code generation: omit `--download-code` unless explicitly needed.
- Mismatched design version: rely on `fetch_lanhu.py`; it looks up the latest design version before fetching DDS schema data.
