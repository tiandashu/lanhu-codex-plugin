# /review-lanhu-parity

Review implemented UI against a Lanhu design and call out visual or behavioral mismatches.

## Arguments

- `lanhu_url`: Lanhu project or single-design URL (required unless local artifacts are provided)
- `target`: local page/component/route to review (required)
- `artifacts`: optional local directory containing `.schema.json`, preview PNG, tokens, and `restore/parity-report.json`

## Workflow

1. Ensure Lanhu artifacts exist; fetch them when needed.
2. Generate or refresh the interactive baseline with `scripts/restore_lanhu.py`.
3. Inspect the target implementation and run the relevant local preview or test path.
4. Compare layout, typography, colors, assets, clipping, interactions, and component boundaries.
5. Check every relevant `interaction_contracts` item and major `component_candidates` entry from `restore/parity-report.json`.
6. Report findings first, ordered by severity, then list checked evidence and suggested fixes.

## Output Requirements

- Findings ordered by severity
- Interaction mismatches called out separately from static visual drift
- Component boundary problems called out separately from visual drift
- Evidence checked: schema, preview PNG, baseline report, rendered app, tests
- Missing evidence that blocks a full parity judgment
