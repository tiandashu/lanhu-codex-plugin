---
name: lanhu-generate-baseline
description: "Generate an interactive HTML parity baseline from fetched Lanhu artifacts. Use after Lanhu schema/assets are downloaded and before translating a design into React, Next.js, Vue, Flutter, native code, or standalone HTML. Load lanhu-use first for script path and artifact safety rules."
---

# Generate Lanhu Baseline

Use this skill to create a schema-first interactive HTML checkpoint before framework translation. The baseline is not the final app implementation; it is a fidelity reference that reduces layout drift and exposes missing interaction semantics early.

## Prerequisites

Fetch artifacts with `lanhu-fetch-design` first. The input directory must contain a `.schema.json` file and, when images are present, localized assets under `assets/slices/`.

## Generate

Run:

```bash
python <plugin-root>/scripts/restore_lanhu.py \
  --input-dir "$OUTPUT_DIR" \
  --output-dir "$OUTPUT_DIR/restore"
```

Expected outputs:

- `restore/index.html`
- `restore/parity-report.json`

The baseline flattens visible layers with absolute row dimensions and local image references, then adds inferred native controls and a lightweight interaction script. Use it as the first visual and behavior checkpoint before building target-framework components.

## Preview

Serve from the fetch output root so relative asset paths resolve:

```bash
python -m http.server 8766 --bind 127.0.0.1 --directory "$OUTPUT_DIR"
```

Open:

```text
http://127.0.0.1:8766/restore/index.html
```

If another process uses the port, choose another port.

## How To Use The Baseline

- Compare `restore/index.html` against the preview PNG.
- Read `restore/parity-report.json` for missing images, unsupported layer types, interaction counts, or structural warnings.
- Use baseline layout values to cross-check framework implementation, but keep `.schema.json` authoritative when there is a conflict.
- Do not copy generated class names blindly into production code. Prefer semantic names in the final implementation.
- Treat inferred interactions as a starting point. Confirm against schema names, visible copy, and project behavior before finalizing production code.

## Stop Conditions

Do not proceed to framework implementation if:

- The baseline has broken or missing local images.
- Visible layers from the preview PNG are absent.
- The baseline report shows major unsupported or skipped layer groups that affect the requested screen.
- The baseline report has `interaction_nodes: 0` even though the design visibly contains buttons, inputs, tabs, or other controls.
- The schema file cannot be identified unambiguously.
