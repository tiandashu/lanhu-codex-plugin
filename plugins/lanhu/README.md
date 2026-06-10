# Lanhu Codex Plugin

This plugin packages a Lanhu design-to-code workflow for Codex.

It provides:

- `lanhu-use` for authentication, script safety, URL parsing, and error recovery
- `lanhu-fetch-design` for listing designs and fetching schema, preview, tokens, and assets
- `lanhu-generate-baseline` for creating a schema-first interactive HTML parity baseline
- `lanhu-verify-parity` for final visual, interaction, and implementation checks
- `lanhu-restore-design` for end-to-end schema-first Lanhu implementation
- `/restore-from-lanhu`, `/implement-from-lanhu`, and `/review-lanhu-parity` command prompts
- `scripts/fetch_lanhu.py` for listing designs, fetching schema JSON, extracting design tokens, downloading preview images, and localizing image assets
- `scripts/restore_lanhu.py` for generating a schema-first interactive HTML parity baseline with inferred buttons, inputs, tabs, toggles, selects, links, and keyboard/focus behavior
- `scripts/verify_lanhu.py` for screenshot-based visual parity verification with a default 99% pass threshold
- `ui/lanhu-workbench.html` for the plugin workflow dashboard
- API notes in `skills/lanhu-restore-design/references/lanhu-api.md`

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Login

Authenticate through an interactive browser. The helper opens Lanhu, lets you complete Lanhu or team SSO login, then encrypts cookies locally with Windows DPAPI:

```bash
python scripts/lanhu_auth.py login --url "https://lanhuapp.com/web/#/item/project/stage?tid=...&pid=..."
```

Check or clear the saved login:

```bash
python scripts/lanhu_auth.py status
python scripts/lanhu_auth.py clear
```

If you need to paste a browser `Cookie:` request header manually, use the hidden local prompt so the value is encrypted with Windows DPAPI and not stored in shell history:

```bash
python scripts/lanhu_auth.py import-cookie --url "<LANHU_URL>"
```

`fetch_lanhu.py` reads the encrypted cookie store by default. `--cookie` is still available for debugging, but environment-variable authentication is no longer the recommended flow.

The encrypted cookie store is reused across runs. Log in again only when the saved cookies expire, are cleared, or no longer have access to the target Lanhu team/project.

## Quick Commands

List designs in a Lanhu project:

```bash
python scripts/fetch_lanhu.py --url "https://lanhuapp.com/web/#/item/project/stage?tid=...&pid=..."
```

Fetch one design and its local assets:

```bash
python scripts/fetch_lanhu.py \
  --url "https://lanhuapp.com/web/#/item/project/stage?tid=...&pid=..." \
  --design 1 \
  --download-images \
  --output-dir ./lanhu_output
```

Single design URLs containing `image_id` are supported directly, including `detailDetach` links that omit `tid`. The script uses `project/multi_info` to find the latest design version before fetching DDS schema data. If DDS schema data is unavailable for an older or raster-backed design version, the script falls back to raw Sketch JSON and the generated baseline uses the preview PNG as a visual backing image with transparent interactive hit areas.

Generate a high-fidelity interactive HTML baseline:

```bash
python scripts/restore_lanhu.py --input-dir ./lanhu_output --output-dir ./lanhu_output/restore
```

Preview it from the fetch output root so local assets resolve:

```bash
python -m http.server 8766 --bind 127.0.0.1 --directory ./lanhu_output
```

Then open `http://127.0.0.1:8766/restore/index.html`.

The generated `.schema.json` is the source of truth for implementation. The preview `.png` is used to confirm visible layers, and `.tokens.txt` is only a supplemental check for complex visual attributes.

Run the 99% visual parity gate:

```bash
python scripts/verify_lanhu.py --input-dir ./lanhu_output --threshold 99 --require-interactions
```

The verifier renders `restore/index.html`, captures a screenshot, compares it against the Lanhu preview PNG, writes `verify/verify-report.json`, and exits non-zero if visual parity is below the threshold.

To reproduce the old static-only baseline for debugging:

```bash
python scripts/restore_lanhu.py --input-dir ./lanhu_output --output-dir ./lanhu_output/restore --no-interactions
```
