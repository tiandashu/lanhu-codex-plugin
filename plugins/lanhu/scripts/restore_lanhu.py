#!/usr/bin/env python3
"""
Generate high-fidelity static HTML/CSS from a fetched Lanhu schema.

The generator is intentionally conservative: it treats schema row dimensions as
the source of truth, flattens visible layers onto one absolute-positioned page,
and replaces Lanhu remote image URLs with downloaded local slice paths.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CSS_KEY_MAP = {
    "backgroundColor": "background-color",
    "backgroundImage": "background-image",
    "backgroundSize": "background-size",
    "backgroundPosition": "background-position",
    "backgroundRepeat": "background-repeat",
    "borderRadius": "border-radius",
    "boxShadow": "box-shadow",
    "color": "color",
    "display": "display",
    "flexDirection": "flex-direction",
    "flexWrap": "flex-wrap",
    "fontFamily": "font-family",
    "fontSize": "font-size",
    "fontWeight": "font-weight",
    "height": "height",
    "justifyContent": "justify-content",
    "alignItems": "align-items",
    "lineHeight": "line-height",
    "opacity": "opacity",
    "overflow": "overflow",
    "overflowWrap": "overflow-wrap",
    "textAlign": "text-align",
    "whiteSpace": "white-space",
    "width": "width",
    "zIndex": "z-index",
}

UNITLESS_CSS = {"font-weight", "opacity", "z-index"}
VISIBLE_STYLE_KEYS = {
    "background",
    "backgroundColor",
    "backgroundImage",
    "border",
    "borderColor",
    "borderRadius",
    "borderStyle",
    "borderWidth",
    "boxShadow",
    "opacity",
}


@dataclass
class RenderNode:
    node: dict[str, Any]
    class_name: str
    tag: str
    text: str = ""
    src: str = ""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str, fallback: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return value or fallback


def px(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{value}px"
    return str(value)


def css_value(key: str, value: Any) -> str:
    css_key = CSS_KEY_MAP.get(key, key)
    if value is None:
        return ""
    if css_key == "opacity" and isinstance(value, (int, float)) and value > 1:
        return str(value / 100)
    if css_key in UNITLESS_CSS:
        return str(value)
    if css_key in {"width", "height", "left", "top", "font-size", "line-height"}:
        return px(value)
    return str(value)


def invert_mapping(mapping: dict[str, str]) -> dict[str, str]:
    return {remote: local for local, remote in mapping.items()}


def replace_remote_urls(value: str, remote_to_local: dict[str, str]) -> str:
    result = value
    for remote, local in remote_to_local.items():
        result = result.replace(remote, local)
    return result


def style_to_css(
    node: dict[str, Any],
    remote_to_local: dict[str, str],
    root: bool = False,
) -> list[tuple[str, str]]:
    style = node.get("style") or {}
    dims = node.get("rowDims") or {}
    rules: list[tuple[str, str]] = [("box-sizing", "border-box")]

    if root:
        rules.extend(
            [
                ("position", "relative"),
                ("overflow", str(style.get("overflow", "hidden"))),
                ("width", px(dims.get("width", style.get("width", 0)))),
                ("height", px(dims.get("height", style.get("height", 0)))),
            ]
        )
    else:
        rules.extend(
            [
                ("position", "absolute"),
                ("left", px(dims.get("left", style.get("left", 0)))),
                ("top", px(dims.get("top", style.get("top", 0)))),
                ("width", px(dims.get("width", style.get("width", 0)))),
                ("height", px(dims.get("height", style.get("height", 0)))),
            ]
        )

    if "background" in style:
        rules.append(("background", replace_remote_urls(str(style["background"]), remote_to_local)))

    for key, value in style.items():
        css_key = CSS_KEY_MAP.get(key)
        if not css_key:
            continue
        if css_key in {"width", "height"}:
            continue
        if root and css_key in {"position"}:
            continue
        rendered = css_value(key, value)
        if rendered:
            rules.append((css_key, replace_remote_urls(rendered, remote_to_local)))

    border = border_css(style)
    if border:
        rules.append(("border", border))

    if "background" not in style and style.get("backgroundImage"):
        rules.append(
            (
                "background-image",
                replace_remote_urls(str(style["backgroundImage"]), remote_to_local),
            )
        )

    deduped: dict[str, str] = {}
    for key, value in rules:
        deduped[key] = value
    return list(deduped.items())


def border_css(style: dict[str, Any]) -> str:
    if style.get("border"):
        return str(style["border"])
    width = style.get("borderWidth")
    color = style.get("borderColor")
    border_style = style.get("borderStyle", "solid")
    if width is not None and color:
        return f"{px(width)} {border_style} {color}"
    return ""


def is_visible(node: dict[str, Any]) -> bool:
    if node.get("isVisible") is False:
        return False
    style = node.get("style") or {}
    if style.get("display") == "none" or style.get("visibility") == "hidden":
        return False
    dims = node.get("rowDims") or style
    width = dims.get("width", 0) or 0
    height = dims.get("height", 0) or 0
    return width != 0 and height != 0


def has_visible_paint(node: dict[str, Any]) -> bool:
    node_type = node.get("type")
    if node_type in {"lanhutext", "lanhuimage"}:
        return True
    style = node.get("style") or {}
    return any(key in style for key in VISIBLE_STYLE_KEYS)


def text_value(node: dict[str, Any]) -> str:
    raw = (node.get("data") or {}).get("value")
    if raw is None:
        raw = (node.get("props") or {}).get("text", "")
    value = html.unescape(str(raw))
    return html.escape(value).replace("\xa0", "&nbsp;")


def image_src(node: dict[str, Any], remote_to_local: dict[str, str]) -> str:
    src = (node.get("data") or {}).get("value") or (node.get("props") or {}).get("src", "")
    return replace_remote_urls(str(src), remote_to_local)


def collect_render_nodes(schema: dict[str, Any]) -> list[RenderNode]:
    nodes: list[RenderNode] = []
    counts: dict[str, int] = {}

    def walk(node: dict[str, Any]) -> None:
        if not is_visible(node):
            return
        node_type = node.get("type", "node")
        if has_visible_paint(node):
            base = slugify(node.get("eleName") or node.get("id") or node_type, node_type)
            counts[base] = counts.get(base, 0) + 1
            suffix = f"-{counts[base]}" if counts[base] > 1 else ""
            class_name = f"lanhu__{base}{suffix}"
            tag = "div"
            text = ""
            src = ""
            if node_type == "lanhutext":
                tag = "span"
                text = text_value(node)
            elif node_type == "lanhuimage":
                tag = "img"
            nodes.append(RenderNode(node=node, class_name=class_name, tag=tag, text=text, src=src))
        for child in node.get("children") or []:
            walk(child)

    for child in schema.get("children") or []:
        walk(child)
    return nodes


def css_block(selector: str, rules: list[tuple[str, str]]) -> str:
    body = "\n".join(f"  {key}: {value};" for key, value in rules if value != "")
    return f"{selector} {{\n{body}\n}}"


def generate_html(
    schema: dict[str, Any],
    mapping: dict[str, str],
    title: str,
) -> tuple[str, dict[str, Any]]:
    remote_to_local = invert_mapping(mapping)
    root_rules = style_to_css(schema, remote_to_local, root=True)
    render_nodes = collect_render_nodes(schema)

    css_blocks = [
        "html, body {\n  margin: 0;\n  min-height: 100%;\n  background: #f3f4f7;\n}",
        "body {\n  display: grid;\n  place-items: start center;\n}",
        ".lanhu-page {\n  " + "\n  ".join(f"{k}: {v};" for k, v in root_rules) + "\n}",
        ".lanhu-page img {\n  display: block;\n  object-fit: fill;\n}",
    ]

    elements: list[str] = []
    for item in render_nodes:
        rules = style_to_css(item.node, remote_to_local)
        css_blocks.append(css_block(f".{item.class_name}", rules))
        if item.tag == "span":
            elements.append(f'    <span class="{item.class_name}">{item.text}</span>')
        elif item.tag == "img":
            src = image_src(item.node, remote_to_local)
            alt = html.escape(item.node.get("eleName") or "Lanhu image")
            elements.append(f'    <img class="{item.class_name}" src="{html.escape(src)}" alt="{alt}">')
        else:
            elements.append(f'    <div class="{item.class_name}"></div>')

    design_type = schema.get("designType", "")
    width = (schema.get("rowDims") or schema.get("style") or {}).get("width")
    height = (schema.get("rowDims") or schema.get("style") or {}).get("height")

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
{chr(10).join(css_blocks)}
  </style>
</head>
<body>
  <main class="lanhu-page" data-design-type="{html.escape(str(design_type))}" data-design-width="{width}" data-design-height="{height}">
{chr(10).join(elements)}
  </main>
</body>
</html>
"""
    report = {
        "title": title,
        "design_type": design_type,
        "width": width,
        "height": height,
        "rendered_nodes": len(render_nodes),
        "remote_url_count": document.count("http://") + document.count("https://"),
        "text_nodes": sum(1 for n in render_nodes if n.node.get("type") == "lanhutext"),
        "image_nodes": sum(1 for n in render_nodes if n.node.get("type") == "lanhuimage"),
        "strategy": "absolute-rowDims-flattened",
    }
    return document, report


def adjust_mapping_paths(
    mapping: dict[str, str],
    schema_dir: Path,
    output_dir: Path,
) -> dict[str, str]:
    adjusted: dict[str, str] = {}
    for local, remote in mapping.items():
        local_path = Path(local)
        if str(local).startswith("./"):
            local_path = schema_dir / str(local)[2:]
        elif not local_path.is_absolute():
            local_path = schema_dir / local_path
        adjusted_local = Path(os.path.relpath(local_path, output_dir)).as_posix()
        if not adjusted_local.startswith("."):
            adjusted_local = f"./{adjusted_local}"
        adjusted[adjusted_local] = remote
    return adjusted


def infer_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.schema:
        schema_path = Path(args.schema)
    else:
        input_dir = Path(args.input_dir)
        matches = sorted(input_dir.glob("*.schema.json"))
        if not matches:
            raise FileNotFoundError(f"No *.schema.json found in {input_dir}")
        schema_path = matches[0]

    if args.mapping:
        mapping_path = Path(args.mapping)
    else:
        mapping_path = schema_path.with_name(schema_path.name.replace(".schema.json", ".image_mapping.json"))

    output_dir = Path(args.output_dir) if args.output_dir else schema_path.parent / "restore"
    return schema_path, mapping_path, output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate high-fidelity static HTML from Lanhu schema")
    parser.add_argument("--input-dir", default="./lanhu_output", help="Directory containing fetched Lanhu files")
    parser.add_argument("--schema", help="Path to a specific *.schema.json")
    parser.add_argument("--mapping", help="Path to *.image_mapping.json")
    parser.add_argument("--output-dir", help="Output directory for restored files")
    parser.add_argument("--title", help="HTML title")
    args = parser.parse_args()

    schema_path, mapping_path, output_dir = infer_paths(args)
    schema = load_json(schema_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_mapping = load_json(mapping_path) if mapping_path.exists() else {}
    mapping = adjust_mapping_paths(raw_mapping, schema_path.parent, output_dir)

    title = args.title or schema_path.name.replace(".schema.json", "")
    document, report = generate_html(schema, mapping, title)

    html_path = output_dir / "index.html"
    report_path = output_dir / "parity-report.json"
    html_path.write_text(document, encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"html_path": str(html_path), "report_path": str(report_path), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
