# /restore-from-lanhu

Restore a Lanhu design into project code.

## Arguments

- `lanhu_url`: Lanhu project or design URL containing `tid` and `pid`
- `design`: optional design index or exact design name
- `target`: optional target file, component, route, or framework hint
- `download_code`: optional; only use when the user explicitly wants Lanhu official generated HTML/CSS for reference

## Workflow

1. Use the `lanhu-restore-design` skill.
2. Ensure local Lanhu cookies exist and are not expired with `scripts/lanhu_auth.py status`; if missing or expired, run `scripts/lanhu_auth.py login --url <lanhu_url>`.
3. If `design` is omitted and the URL does not include a design id, list project designs with `scripts/fetch_lanhu.py`.
4. If the URL includes `image_id`, fetch that single design directly.
5. Fetch schema, tokens, preview PNG, and image assets for the selected design.
6. Generate a static parity baseline with `scripts/restore_lanhu.py`.
7. Inspect the target project conventions and any `DESIGN.md`.
8. Implement using schema values and the generated baseline as the source of truth.
9. Run local verification and summarize parity plus known deltas.

If Lanhu returns SSO or permission errors, rerun `scripts/lanhu_auth.py login --url <lanhu_url>` instead of asking the user for `LANHU_COOKIE`.

## Escalation

Delegate substantial multi-file UI work to `lanhu-implementation-agent`.
