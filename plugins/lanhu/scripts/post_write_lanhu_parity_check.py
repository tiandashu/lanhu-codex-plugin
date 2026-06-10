#!/usr/bin/env python3
"""Post-write parity reminder for Lanhu UI restoration work."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    candidates = sorted(Path.cwd().glob("**/restore/parity-report.json"))
    if not candidates:
        print(
            "[lanhu-hook] UI files changed. If this was Lanhu restoration work, "
            "fetch artifacts, regenerate the interactive baseline, and run parity checks before finalizing."
        )
        return

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    try:
        report = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        print(f"[lanhu-hook] Found {latest}; re-run Lanhu parity checks if UI code changed.")
        return

    interactions = report.get("interaction_nodes", 0)
    remote_urls = report.get("remote_url_count", 0)
    print(
        "[lanhu-hook] Latest Lanhu parity report: "
        f"{latest} | rendered_nodes={report.get('rendered_nodes', 'n/a')} "
        f"interaction_nodes={interactions} remote_urls={remote_urls}. "
        "Re-check visual parity and interactions for UI-affecting writes."
    )


if __name__ == "__main__":
    main()
