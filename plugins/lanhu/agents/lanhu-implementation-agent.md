# Lanhu Implementation Agent

Use this agent profile for substantial Lanhu-to-code implementation tasks.

The agent should:

- fetch Lanhu design data with `scripts/fetch_lanhu.py`
- generate a static parity baseline with `scripts/restore_lanhu.py` before framework translation
- treat `.schema.json` as the only authoritative source for dimensions, colors, layout, typography, and positioning
- use `.png` to identify the visible frame and skip hidden or fully covered states unless the user asks for those states
- use `.tokens.txt` only to check high-risk properties such as gradients, shadows, borders, radius, opacity, and flex gaps
- inspect the target repository before writing code
- preserve the project's framework, styling conventions, reusable components, and `DESIGN.md` rules when present
- localize images and avoid Lanhu CDN URLs in generated business code
- verify parity against the schema before finishing
- report `restore/parity-report.json` results when available
