# Lanhu Web API Notes

These notes document the Lanhu web endpoints used by this plugin. They are based on the bundled `scripts/fetch_lanhu.py` implementation and local probing against Lanhu web URLs.

## URL Shapes

Project stage URL:

```text
https://lanhuapp.com/web/#/item/project/stage?tid=<team_id>&pid=<project_id>
```

Single detached design URL:

```text
https://lanhuapp.com/web/#/item/project/detailDetach?pid=<project_id>&project_id=<project_id>&image_id=<image_id>&fromEditor=true
```

Important parameters:

- `tid`: Lanhu team id, optional on some `detailDetach` links
- `pid` or `project_id`: project id
- `image_id`: design image id for a single design URL
- `docId`: alternate design image id used by some Lanhu routes

Some `detailDetach` URLs omit `tid`, for example:

```text
https://lanhuapp.com/web/#/item/project/detailDetach?pid=04d3f972-20e3-4172-aef4-a32ff96b33bf&project_id=04d3f972-20e3-4172-aef4-a32ff96b33bf&image_id=5c6ce78a-a5d5-4317-8bb2-ba7161954816&fromEditor=true
```

In that case, fetch the target by `project_id` and `image_id`; do not reject the URL before trying `project/multi_info`.

## Authentication

Lanhu web APIs require the full browser Cookie state. A standalone JWT/token string is not enough for SSO-protected teams.

The plugin should not ask users to paste or configure cookies in chat. Use the local login helper instead:

```bash
python scripts/lanhu_auth.py login --url "<LANHU_URL>"
```

The helper:

1. Opens an interactive browser window.
2. Lets the user complete Lanhu or team SSO login.
3. Captures cookies for `lanhuapp.com` and `dds.lanhuapp.com`.
4. Encrypts them locally with Windows DPAPI.
5. Lets `fetch_lanhu.py` decrypt and use them on later runs.

Saved cookies are reused until they expire. Session cookies are treated as usable, and the API response decides whether they are still valid.

If authentication is incomplete, Lanhu may return:

- redirect to `/sso/#/main/sso?tid=<team_id>` in the browser
- `HTTP 418` from project APIs
- response text similar to `You don't have the permission to access this project!`

## Endpoint Chain

### List project designs

```http
GET https://lanhuapp.com/api/project/images
```

Query:

- `project_id=<project_id>`
- `team_id=<team_id>`
- `dds_status=1`
- `position=1`
- `show_cb_src=1`

Purpose:

- Returns project metadata and an `images` array.
- Used when the user provides a project URL and still needs to choose a design.

Normalized fields used by the plugin:

- `id`
- `name`
- `width`
- `height`
- `url`
- `update_time`

### Find latest version

```http
GET https://lanhuapp.com/api/project/multi_info
```

Query:

- `project_id=<project_id>`
- `team_id=<team_id>`
- `img_limit=500`
- `detach=1`

Purpose:

- Returns images and version metadata.
- Used to find `latest_version` for a selected `image_id`.
- Single design URLs use this endpoint before falling back to `project/images`, because `image_id` is already known.

### Fetch DDS schema pointer

```http
GET https://dds.lanhuapp.com/api/dds/image/store_schema_revise
```

Query:

- `version_id=<latest_version>`

Headers:

- Full Lanhu `Cookie`
- `Authorization: Basic dW5kZWZpbmVkOg==`
- `Referer: https://dds.lanhuapp.com/`

Purpose:

- Returns `data.data_resource_url`.
- The script downloads that URL to produce `<name>.schema.json`.
- Some image versions return `版本数据不存在` here. When that happens, fetch raw Sketch JSON and generate a fallback schema.

### Fetch raw Sketch JSON

```http
GET https://lanhuapp.com/api/project/image
```

Query:

- `dds_status=1`
- `image_id=<image_id>`
- `team_id=<team_id>`
- `project_id=<project_id>`

Purpose:

- Returns versions with `json_url`.
- The script downloads the selected `json_url` and extracts high-risk visual tokens into `<name>.tokens.txt`.
- Also acts as a fallback source for schema generation when DDS schema data is unavailable.

### Optional official code package

```http
POST https://dds.lanhuapp.com/api/dds/code_package/task
```

Purpose:

- Creates a Lanhu official code package task.
- Used only when the user explicitly requests `--download-code`.
- Generated HTML/CSS is reference-only; schema remains authoritative.

## Local Outputs

- `<name>.schema.json`: authoritative UI data
- `<name>.sketch.json`: raw Sketch fallback source when available
- `<name>.tokens.txt`: supplemental high-risk style summary
- `<name>.png`: preview image
- `assets/slices/img_N.*`: localized image assets
- `<name>.image_mapping.json`: local asset path to remote URL mapping
