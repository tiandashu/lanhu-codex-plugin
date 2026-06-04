# Lanhu Codex Plugin Marketplace

This repository is a Codex plugin marketplace for the Lanhu design-to-code plugin.

## Install In Codex

Add this marketplace:

```bash
codex plugin marketplace add tiandashu/lanhu-codex-plugin
```

Then restart Codex, open Plugins, choose the `Lanhu Codex Plugins` marketplace, and install `Lanhu`.

## Sparse Checkout Note

Do not use a leading slash in sparse checkout paths.

Incorrect:

```bash
codex plugin marketplace add tiandashu/lanhu-codex-plugin --sparse /
```

This can fail with:

```text
git sparse-checkout set / failed with status exit code: 128
fatal: specify directories rather than patterns (no leading slash)
```

Use the normal marketplace command above. If sparse checkout is required, pass directory paths without a leading slash and include both the marketplace metadata and plugin folder:

```bash
codex plugin marketplace add tiandashu/lanhu-codex-plugin --sparse .agents/plugins --sparse plugins/lanhu
```

## Repository Layout

- `.agents/plugins/marketplace.json`: marketplace catalog
- `plugins/lanhu/`: plugin package
- `plugins/lanhu/.codex-plugin/plugin.json`: plugin manifest
