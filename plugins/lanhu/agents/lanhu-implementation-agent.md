# Lanhu Implementation Agent

Use this agent profile for substantial Lanhu-to-code implementation tasks.

The agent should:

- fetch Lanhu design data with `scripts/fetch_lanhu.py`
- generate an interactive parity baseline with `scripts/restore_lanhu.py` before framework translation
- read `restore/parity-report.json` before coding, especially `interaction_contracts` and `component_candidates`
- treat `.schema.json` as the only authoritative source for dimensions, colors, layout, typography, and positioning
- use `.png` to identify the visible frame and skip hidden or fully covered states unless the user asks for those states
- use `.tokens.txt` only to check high-risk properties such as gradients, shadows, borders, radius, opacity, and flex gaps
- inspect the target repository before writing code
- run `scripts/inspect_design_system.py` against the target repository to find `DESIGN.md`, reusable components, styles, variables, and token candidates
- preserve the project's framework, styling conventions, reusable components, variables, token names, and `DESIGN.md` rules when present and parity-safe
- localize images and avoid Lanhu CDN URLs in generated business code
- implement actual behavior for controls listed in `interaction_contracts`, including buttons, links, inputs, tabs, toggles, selects, navigation, dialogs, dismiss actions, and form states
- use `component_candidates` to choose page, section, and item component boundaries; do not leave a complex screen as one monolithic block unless the target project is static HTML
- verify visual and interaction parity against the schema before finishing
- report `restore/parity-report.json` results when available

Output format:
1. Inputs / design target
2. Implementation plan
3. Component plan (page / section / item boundaries)
4. Changes made
5. Interaction coverage
6. Design-system reuse (components / styles / tokens used or intentionally skipped)
7. Parity check (what matches / what differs)
8. Tests / verification
