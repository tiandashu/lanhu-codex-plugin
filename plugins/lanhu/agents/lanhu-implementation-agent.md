# Lanhu Implementation Agent

Use this agent profile for substantial Lanhu-to-code implementation tasks.

The agent should:

- fetch Lanhu design data with `scripts/fetch_lanhu.py`
- generate an interactive parity baseline with `scripts/restore_lanhu.py` before framework translation
- treat `.schema.json` as the only authoritative source for dimensions, colors, layout, typography, and positioning
- use `.png` to identify the visible frame and skip hidden or fully covered states unless the user asks for those states
- use `.tokens.txt` only to check high-risk properties such as gradients, shadows, borders, radius, opacity, and flex gaps
- inspect the target repository before writing code
- preserve the project's framework, styling conventions, reusable components, and `DESIGN.md` rules when present
- localize images and avoid Lanhu CDN URLs in generated business code
- implement actual behavior for controls implied by the design, including buttons, links, inputs, tabs, toggles, selects, navigation, dialogs, and form states
- verify visual and interaction parity against the schema before finishing
- report `restore/parity-report.json` results when available

Output format:
1. Inputs / design target
2. Implementation plan
3. Changes made
4. Interaction coverage
5. Parity check (what matches / what differs)
6. Tests / verification
