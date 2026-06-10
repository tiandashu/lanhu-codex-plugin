# /restore-from-lanhu

Restore a Lanhu design into project code.

## Arguments

- `lanhu_url`: Lanhu project or design URL containing `tid` and `pid`
- `design`: optional design index or exact design name
- `target`: optional target file, component, route, or framework hint
- `download_code`: optional; only use when the user explicitly wants Lanhu official generated HTML/CSS for reference

## Workflow

1. Use `lanhu-restore-design` as the high-level workflow.
2. Use `lanhu-use` for authentication, URL handling, and script safety.
3. Use `lanhu-fetch-design` to list/select designs when needed and fetch schema, tokens, preview PNG, and image assets.
4. Use `lanhu-generate-baseline` to create the interactive parity baseline with `scripts/restore_lanhu.py`.
5. Inspect the target project conventions and any `DESIGN.md`.
6. Implement using schema values and the generated baseline as fidelity checkpoints.
7. Wire actual interactions implied by the design instead of leaving controls inert.
8. Use `lanhu-verify-parity` for local verification and summarize visual parity, interaction coverage, and known deltas.

If Lanhu returns SSO or permission errors, rerun `scripts/lanhu_auth.py login --url <lanhu_url>` instead of asking the user for `LANHU_COOKIE`.

## Escalation

Delegate substantial multi-file UI work to `lanhu-implementation-agent`.
