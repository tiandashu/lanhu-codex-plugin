#!/usr/bin/env python3
"""Inspect local design-system assets for Lanhu implementation workflows."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".json",
    ".md",
    ".yaml",
    ".yml",
}

STYLE_EXTENSIONS = {".css", ".scss", ".sass", ".less"}
COMPONENT_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
TOKEN_EXTENSIONS = {".css", ".scss", ".sass", ".less", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml"}
TOKEN_NAME_RE = re.compile(
    r"(--[a-zA-Z0-9_-]+|[$@][a-zA-Z0-9_-]+|[\"']?[a-zA-Z0-9_.-]*(?:color|space|spacing|radius|shadow|font|typography|z-index|breakpoint)[a-zA-Z0-9_.-]*[\"']?)",
    re.IGNORECASE,
)
COMPONENT_NAME_RE = re.compile(
    r"(?:export\s+(?:default\s+)?(?:function|const|class)\s+|function\s+|class\s+)([A-Z][A-Za-z0-9_]*)|name\s*:\s*[\"']([A-Z][A-Za-z0-9_]*)[\"']"
)
CLASS_RE = re.compile(r"\.([a-zA-Z][a-zA-Z0-9_-]+)\s*[{,]")
TOKEN_PATH_RE = re.compile(r"(token|theme|variable|style|design-system|tailwind|config)", re.IGNORECASE)


@dataclass
class SearchResult:
    kind: str
    name: str
    path: str
    line: int
    excerpt: str


def should_skip(path: Path) -> bool:
    skip_parts = {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
        "lanhu_output",
        "lanhu_probe",
        "restore",
        "verify",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
    }
    return any(part in skip_parts for part in path.parts)


def iter_text_files(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for path in sorted(root.rglob("*")):
        if count >= max_files:
            break
        if path.is_file() and not should_skip(path) and path.suffix.lower() in TEXT_EXTENSIONS:
            count += 1
            yield path


def read_text(path: Path, max_bytes: int) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def add_result(results: list[SearchResult], kind: str, name: str, path: Path, root: Path, line: int, excerpt: str) -> None:
    cleaned = " ".join(excerpt.strip().split())
    if not cleaned:
        return
    results.append(
        SearchResult(
            kind=kind,
            name=name.strip("\"'"),
            path=relative(path, root),
            line=line,
            excerpt=cleaned[:220],
        )
    )


def should_scan_tokens(path: Path, rel: str) -> bool:
    if path.suffix.lower() not in TOKEN_EXTENSIONS:
        return False
    return bool(TOKEN_PATH_RE.search(rel))


def scan_project(root: Path, query: str, max_files: int, max_bytes: int) -> dict:
    query_terms = [term.lower() for term in re.split(r"[\s,;/]+", query or "") if term.strip()]
    design_docs: list[str] = []
    components: list[SearchResult] = []
    styles: list[SearchResult] = []
    tokens: list[SearchResult] = []
    matches: list[SearchResult] = []
    files_scanned = 0

    for path in iter_text_files(root, max_files):
        files_scanned += 1
        rel = relative(path, root)
        text = read_text(path, max_bytes)
        lower_rel = rel.lower()

        if path.name.lower() in {"design.md", "design-system.md", "tokens.md"} or "design-system" in lower_rel:
            design_docs.append(rel)

        if path.suffix.lower() in COMPONENT_EXTENSIONS:
            for match in COMPONENT_NAME_RE.finditer(text):
                name = match.group(1) or match.group(2)
                line = text.count("\n", 0, match.start()) + 1
                add_result(components, "component", name, path, root, line, line_excerpt(text, line))

        if path.suffix.lower() in STYLE_EXTENSIONS:
            for match in CLASS_RE.finditer(text):
                name = "." + match.group(1)
                line = text.count("\n", 0, match.start()) + 1
                add_result(styles, "style", name, path, root, line, line_excerpt(text, line))

        if should_scan_tokens(path, rel):
            for match in TOKEN_NAME_RE.finditer(text):
                name = match.group(1)
                if len(name.strip("\"'")) < 4:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                add_result(tokens, "token", name, path, root, line, line_excerpt(text, line))

        if query_terms:
            lines = text.splitlines()
            for index, line_text in enumerate(lines, start=1):
                haystack = f"{rel} {line_text}".lower()
                if all(term in haystack for term in query_terms):
                    add_result(matches, "match", query, path, root, index, line_text)

    return {
        "root": str(root),
        "files_scanned": files_scanned,
        "design_docs": sorted(set(design_docs)),
        "components": dedupe(components)[:200],
        "styles": dedupe(styles)[:200],
        "tokens": dedupe(tokens)[:300],
        "matches": dedupe(matches)[:100],
    }


def line_excerpt(text: str, line_number: int) -> str:
    lines = text.splitlines()
    if not lines or line_number < 1 or line_number > len(lines):
        return ""
    return lines[line_number - 1]


def dedupe(items: list[SearchResult]) -> list[dict]:
    seen: set[tuple[str, str, str, int]] = set()
    output: list[dict] = []
    for item in items:
        key = (item.kind, item.name, item.path, item.line)
        if key in seen:
            continue
        seen.add(key)
        output.append(asdict(item))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect local design-system assets.")
    parser.add_argument("--project-root", default=".", help="Target app repository root.")
    parser.add_argument("--query", default="", help="Optional component/token/style search query.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--max-bytes", type=int, default=250_000)
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    if not root.exists():
        raise SystemExit(f"Project root does not exist: {root}")

    report = scan_project(root, args.query, args.max_files, args.max_bytes)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
