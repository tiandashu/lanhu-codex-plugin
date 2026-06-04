# Lanhu Codex Plugin Marketplace

This repository is a Codex plugin marketplace for the Lanhu design-to-code plugin.

## Install In Codex

Add this marketplace:

```bash
codex plugin marketplace add tiandashu/lanhu-codex-plugin
codex plugin add lanhu@vtian
```

Then restart Codex, or open a new Codex thread, so the new plugin skills are loaded.

If you prefer the Codex UI, restart Codex, open Plugins, choose the `vtian` marketplace, and install `Lanhu`.

## Update In Codex

Refresh the marketplace snapshot and reinstall the plugin:

```bash
codex plugin marketplace upgrade vtian
codex plugin remove lanhu@vtian
codex plugin add lanhu@vtian
```

Restart Codex, or open a new Codex thread, after updating.

If you installed an older version whose marketplace was named `lanhu-codex-plugin`, migrate it to the new `vtian` marketplace name:

```bash
codex plugin remove lanhu@lanhu-codex-plugin
codex plugin marketplace remove lanhu-codex-plugin
codex plugin marketplace add tiandashu/lanhu-codex-plugin
codex plugin add lanhu@vtian
```

## Uninstall From Codex

Remove the plugin only:

```bash
codex plugin remove lanhu@vtian
```

Remove both the plugin and the marketplace:

```bash
codex plugin remove lanhu@vtian
codex plugin marketplace remove vtian
```

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
codex plugin add lanhu@vtian
```

## Repository Layout

- `.agents/plugins/marketplace.json`: marketplace catalog
- `plugins/lanhu/`: plugin package
- `plugins/lanhu/.codex-plugin/plugin.json`: plugin manifest
