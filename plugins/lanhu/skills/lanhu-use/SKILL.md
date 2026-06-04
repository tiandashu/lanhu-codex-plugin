---
name: lanhu-use
description: "Core Lanhu tool-use rules for Codex. Use before running Lanhu plugin scripts, authenticating with Lanhu, parsing Lanhu URLs, fetching schema/assets, or handling Lanhu API errors. This is the foundational skill for all Lanhu design-to-code workflows and should be loaded alongside higher-level Lanhu skills such as lanhu-fetch-design, lanhu-generate-baseline, lanhu-verify-parity, and lanhu-restore-design."
---

# Lanhu Tool Use

Use this skill as the shared operating manual for Lanhu plugin scripts. Higher-level Lanhu skills describe what to accomplish; this skill describes the safe, repeatable way to call the local tools.

## Plugin Root

Resolve the plugin root as the directory that contains this skill's parent `skills/` folder. From this repository, that is:

```bash
plugins/lanhu
```

The main scripts are:

- `scripts/lanhu_auth.py`
- `scripts/fetch_lanhu.py`
- `scripts/restore_lanhu.py`

## Authentication Rules

Treat Lanhu cookies as secrets. Do not print cookies, commit cookies, paste cookies into generated source, or ask the user to provide `LANHU_COOKIE`.

Use the encrypted local cookie store by default:

```bash
python <plugin-root>/scripts/lanhu_auth.py status
```

If the cookie store is missing, expired, cleared, or Lanhu returns an auth, SSO, team, or permission error, run:

```bash
python <plugin-root>/scripts/lanhu_auth.py login --url "$LANHU_URL"
```

The helper opens an interactive browser, lets the user complete Lanhu or team SSO login, and encrypts cookies locally with Windows DPAPI. Reuse saved cookies unless access fails.

To reset a wrong or expired team session:

```bash
python <plugin-root>/scripts/lanhu_auth.py clear
python <plugin-root>/scripts/lanhu_auth.py login --url "$LANHU_URL"
```

## URL And Design Selection

Lanhu project URLs normally include `tid` and `pid`. Single-design URLs may include `image_id`.

- If the URL includes `image_id`, fetch that design directly.
- If no design id/index/name is provided, list designs first and ask the user for an `index` or exact `name`.
- Do not guess the intended design when a project contains multiple designs.

For API endpoint details, read `../lanhu-restore-design/references/lanhu-api.md` only when implementing or debugging fetch behavior.

## Command Discipline

Prefer the bundled scripts over hand-written HTTP calls. They encode Lanhu endpoint quirks, latest-version lookup, asset localization, and cookie handling.

Use structured output directories. A typical fetch output should contain:

- `<name>.schema.json`
- `<name>.tokens.txt`
- `<name>.png`
- `assets/slices/img_N.*`
- `<name>.image_mapping.json`
- optional `<name>.official.html` and `<name>.official.css`

Never use Lanhu CDN URLs in generated app code. Always localize images and adapt local paths/imports to the target framework.

## Error Recovery

On script or API failure:

1. Stop and read the error message before retrying.
2. Check auth state if the failure mentions login, SSO, permission, team, project, cookie, or forbidden access.
3. Re-run login only when the stored cookie is missing, expired, or mismatched.
4. If schema or asset output is partial, re-fetch into a fresh output directory or clearly verify which files are complete before continuing.
5. If a script behavior appears wrong, inspect the script and the relevant reference instead of inventing endpoint behavior from memory.

## Pre-Flight Checklist

- Lanhu URL is captured exactly.
- Plugin root is resolved.
- Cookie status is known or login has completed.
- Design target is explicit unless the URL contains `image_id`.
- Output directory is chosen and separate from app source unless the user requested otherwise.
- `--download-code` is omitted unless the user explicitly wants official Lanhu generated HTML/CSS.
