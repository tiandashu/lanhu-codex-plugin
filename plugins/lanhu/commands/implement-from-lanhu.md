# /implement-from-lanhu

Implement a Lanhu design into project code with visual and interaction parity.

## Arguments

- `lanhu_url`: Lanhu project or single-design URL containing `tid` and `pid`
- `design`: optional design index or exact design name
- `target`: optional file/component/route/framework hint
- `mode`: `component` or `screen` (optional; infer if omitted)
- `download_code`: optional; only fetch Lanhu official HTML/CSS when explicitly useful as reference

## Workflow

1. Use `lanhu-restore-design` as the high-level workflow.
2. Fetch schema, tokens, preview PNG, image mapping, and local assets with `lanhu-fetch-design`.
3. Generate the interactive baseline with `lanhu-generate-baseline`; keep `.schema.json` authoritative.
4. Run `lanhu-design-system` / `scripts/inspect_design_system.py` against the target project to discover `DESIGN.md`, local components, styles, and token candidates.
5. Reuse existing components, variables, routing, and styling conventions when they preserve schema and interaction parity.
6. Implement visible layout first, then wire real interactions: buttons, inputs, tabs, toggles, selects, navigation, dialogs, and form states when present in the design.
7. Run local build/preview checks and `lanhu-verify-parity`.
8. Summarize visual parity, interaction coverage, design-system reuse decisions, known deltas, and verification evidence.

## Escalation

Delegate substantial UI work or multi-file changes to `lanhu-implementation-agent`.
