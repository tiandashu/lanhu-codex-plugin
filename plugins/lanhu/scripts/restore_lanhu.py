#!/usr/bin/env python3
"""
Generate high-fidelity interactive HTML/CSS from a fetched Lanhu schema.

The generator is intentionally conservative: it treats schema row dimensions as
the source of truth, flattens visible layers onto one absolute-positioned page,
replaces Lanhu remote image URLs with downloaded local slice paths, and adds an
inferred interaction layer for common controls.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from dataclasses import asdict, dataclass
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
    role: str = ""
    action: str = ""
    label: str = ""
    group: str = ""
    placeholder: str = ""
    reason: str = ""
    passive_child: bool = False


@dataclass
class InteractionHint:
    role: str
    action: str
    label: str
    group: str = ""
    placeholder: str = ""
    reason: str = ""


@dataclass
class ComponentCandidate:
    name: str
    suggested_component: str
    reason: str
    node_type: str
    bounds: dict[str, Any]
    child_count: int
    visible_descendants: int
    interaction_count: int
    repeated_count: int
    text_sample: str


BUTTON_KEYWORDS = (
    "button",
    "btn",
    "cta",
    "action",
    "submit",
    "confirm",
    "cancel",
    "save",
    "login",
    "register",
    "按钮",
    "提交",
    "确定",
    "确认",
    "取消",
    "保存",
    "登录",
    "登陆",
    "注册",
    "立即",
    "开始",
    "完成",
    "下一步",
    "返回",
    "支付",
    "购买",
)

INPUT_KEYWORDS = (
    "input",
    "textfield",
    "text-field",
    "textarea",
    "searchfield",
    "search-field",
    "输入框",
    "文本框",
    "搜索框",
    "输入",
    "请输入",
    "搜索输入",
    "手机号",
    "手机号码",
    "密码",
    "验证码",
    "邮箱",
    "地址",
    "备注",
)

SELECT_KEYWORDS = (
    "select",
    "dropdown",
    "picker",
    "combobox",
    "下拉",
    "选择",
    "筛选",
    "排序",
)

TAB_KEYWORDS = ("tab", "tabs", "segmented", "segment", "选项卡", "标签页", "分段")
TOGGLE_KEYWORDS = ("switch", "toggle", "checkbox", "radio", "开关", "切换", "复选", "单选")
LINK_KEYWORDS = ("link", "href", "nav", "menu", "导航", "链接", "查看", "详情", "更多")
NAV_KEYWORDS = (
    "nav",
    "navbar",
    "navigation",
    "menu",
    "sidebar",
    "breadcrumb",
    "tabbar",
    "首页",
    "导航",
    "菜单",
    "侧边栏",
    "面包屑",
)
CARD_KEYWORDS = ("card", "item", "cell", "tile", "panel", "list-item", "卡片", "列表项", "条目", "面板")
FORM_KEYWORDS = ("form", "field", "input", "search", "filter", "表单", "字段", "搜索", "筛选")
DIALOG_KEYWORDS = ("modal", "dialog", "drawer", "popover", "popup", "overlay", "弹窗", "对话框", "抽屉", "浮层", "弹出")
CLOSE_KEYWORDS = ("close", "dismiss", "back", "cancel", "关闭", "取消", "返回")
LIST_KEYWORDS = ("list", "table", "grid", "collection", "列表", "表格", "宫格")
ACTION_BUTTON_TEXTS = (
    "预览",
    "复制",
    "搜索",
    "重置",
    "新增",
    "新建",
    "创建",
    "导出",
    "导入",
    "编辑",
    "删除",
    "发布",
    "下架",
)
SEGMENTED_OPTION_TEXTS = ("集团", "本校", "全国", "全部")


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
    raw = raw_text_value(node)
    value = html.unescape(str(raw))
    return html.escape(value).replace("\xa0", "&nbsp;")


def raw_text_value(node: dict[str, Any]) -> str:
    raw = (node.get("data") or {}).get("value")
    if raw is None:
        raw = (node.get("props") or {}).get("text", "")
    return str(raw or "")


def image_src(node: dict[str, Any], remote_to_local: dict[str, str]) -> str:
    src = (node.get("data") or {}).get("value") or (node.get("props") or {}).get("src", "")
    return replace_remote_urls(str(src), remote_to_local)


def collect_text(node: dict[str, Any], limit: int = 120) -> str:
    parts: list[str] = []

    def walk(current: dict[str, Any]) -> None:
        if len(" ".join(parts)) >= limit:
            return
        if current.get("type") == "lanhutext":
            text = html.unescape(raw_text_value(current)).strip()
            if text:
                parts.append(text)
        for child in current.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(node)
    joined = " ".join(parts).strip()
    return joined[:limit]


def node_blob(node: dict[str, Any]) -> str:
    parts = [
        str(node.get("type") or ""),
        str(node.get("eleName") or ""),
        str(node.get("id") or ""),
        raw_text_value(node),
        collect_text(node),
    ]
    props = node.get("props") or {}
    for key in ("name", "title", "placeholder", "ariaLabel", "href"):
        if props.get(key):
            parts.append(str(props[key]))
    return " ".join(parts)


def has_any_keyword(blob: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword_in_blob(blob, keyword) for keyword in keywords)


def keyword_in_blob(blob: str, keyword: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", keyword):
        return keyword in blob
    if not re.search(r"[A-Za-z0-9]", keyword):
        return keyword.lower() in blob.lower()
    pattern = rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])"
    return re.search(pattern, blob.lower()) is not None


def label_matches(label: str, values: tuple[str, ...]) -> bool:
    return html.unescape(label or "").strip() in values


def row_dims(node: dict[str, Any]) -> dict[str, Any]:
    style = node.get("style") or {}
    dims = node.get("rowDims") or style
    return {
        "left": dims.get("left", style.get("left", 0)),
        "top": dims.get("top", style.get("top", 0)),
        "width": dims.get("width", style.get("width", 0)),
        "height": dims.get("height", style.get("height", 0)),
    }


def bounds_area(node: dict[str, Any]) -> float:
    dims = row_dims(node)
    return float(dims.get("width") or 0) * float(dims.get("height") or 0)


def is_control_sized(node: dict[str, Any]) -> bool:
    dims = row_dims(node)
    width = float(dims.get("width") or 0)
    height = float(dims.get("height") or 0)
    return 12 <= height <= 72 and 16 <= width <= 520


def visible_descendant_count(node: dict[str, Any]) -> int:
    count = 0
    for child in node.get("children") or []:
        if isinstance(child, dict) and is_visible(child):
            count += 1 + visible_descendant_count(child)
    return count


def interaction_count(node: dict[str, Any], inherited_hint: InteractionHint | None = None) -> int:
    own_hint = infer_interaction(node)
    if inherited_hint and node.get("type") in {"lanhutext", "lanhuimage"}:
        own_hint = None
    inherited_click = inherit_click_hint(inherited_hint)
    passive_child = bool(inherited_click and not own_hint)
    count = 1 if own_hint and not passive_child else 0
    for child in node.get("children") or []:
        if isinstance(child, dict) and is_visible(child):
            count += interaction_count(child, own_hint or inherited_hint)
    return count


def structural_signature(node: dict[str, Any]) -> str:
    children = [child for child in node.get("children") or [] if isinstance(child, dict) and is_visible(child)]
    child_types = [str(child.get("type") or "node") for child in children[:8]]
    text_count = sum(1 for child in children if child.get("type") == "lanhutext")
    image_count = sum(1 for child in children if child.get("type") == "lanhuimage")
    control_count = sum(1 for child in children if infer_interaction(child))
    return "|".join(
        [
            str(node.get("type") or "node"),
            ",".join(child_types),
            f"t{text_count}",
            f"i{image_count}",
            f"c{control_count}",
        ]
    )


def control_label(node: dict[str, Any], fallback: str) -> str:
    text = collect_text(node) or raw_text_value(node)
    name = node.get("eleName") or (node.get("props") or {}).get("name")
    label = html.unescape(str(text or name or fallback)).strip()
    return label[:80] or fallback


def interaction_group(node: dict[str, Any], role: str) -> str:
    raw = str(node.get("eleName") or node.get("id") or role)
    raw = re.sub(r"[\d_\-]+$", "", raw).strip() or role
    return slugify(raw, role)


def infer_interaction(node: dict[str, Any]) -> InteractionHint | None:
    node_type = str(node.get("type") or "").lower()
    blob = node_blob(node)
    label = control_label(node, node_type or "Lanhu control")
    control_sized = is_control_sized(node)

    if has_any_keyword(blob, DIALOG_KEYWORDS) and bounds_area(node) >= 1200:
        return InteractionHint(
            role="dialog",
            action="dialog",
            label=label,
            group=interaction_group(node, "dialog"),
            reason="dialog/drawer/popover-like layer name or text",
        )

    if label_matches(label, ACTION_BUTTON_TEXTS) and control_sized:
        return InteractionHint(
            role="button",
            action="button",
            label=label,
            reason="explicit action text",
        )

    dims = row_dims(node)
    if (
        label_matches(label, SEGMENTED_OPTION_TEXTS)
        and control_sized
        and float(dims.get("width") or 0) >= 48
        and float(dims.get("height") or 0) >= 28
    ):
        return InteractionHint(
            role="radio",
            action="radio",
            label=label,
            group=interaction_group(node, "segmented"),
            reason="segmented option text",
        )

    if (node_type in {"lanhuinput", "input", "textarea"} or has_any_keyword(blob, INPUT_KEYWORDS)) and control_sized:
        return InteractionHint(
            role="textbox",
            action="input",
            label=label,
            placeholder=label if len(label) <= 40 else "",
            reason="input-like layer name, type, or placeholder text",
        )

    if (node_type in {"lanhuselect", "select"} or has_any_keyword(blob, SELECT_KEYWORDS)) and control_sized:
        return InteractionHint(
            role="combobox",
            action="select",
            label=label,
            group=interaction_group(node, "select"),
            reason="select/dropdown-like layer name or text",
        )

    if (node_type in {"lanhutab", "tab"} or has_any_keyword(blob, TAB_KEYWORDS)) and control_sized:
        return InteractionHint(
            role="tab",
            action="tab",
            label=label,
            group="tabs",
            reason="tab-like layer name or text",
        )

    if (node_type in {"lanhuswitch", "switch", "checkbox", "radio"} or has_any_keyword(blob, TOGGLE_KEYWORDS)) and control_sized:
        action = "radio" if "radio" in blob.lower() or "单选" in blob else "toggle"
        return InteractionHint(
            role="radio" if action == "radio" else "switch",
            action=action,
            label=label,
            group="radio" if action == "radio" else interaction_group(node, action),
            reason="toggle/checkbox/radio-like layer name or text",
        )

    if control_sized and (node_type in {"lanhulink", "link"} or (
        has_any_keyword(blob, LINK_KEYWORDS) and not has_any_keyword(blob, NAV_KEYWORDS)
    )):
        return InteractionHint(
            role="link",
            action="link",
            label=label,
            reason="link/navigation-like layer name or text",
        )

    if has_any_keyword(blob, CLOSE_KEYWORDS) and control_sized:
        return InteractionHint(
            role="button",
            action="dismiss",
            label=label,
            reason="close/back/cancel affordance",
        )

    if (node_type in {"lanhubutton", "button"} or has_any_keyword(blob, BUTTON_KEYWORDS)) and control_sized:
        return InteractionHint(
            role="button",
            action="button",
            label=label,
            reason="button-like layer name, type, or action text",
        )

    return None


def inherit_click_hint(parent: InteractionHint | None) -> InteractionHint | None:
    if not parent or parent.action not in {"button", "link", "tab", "toggle", "radio", "select", "dismiss"}:
        return None
    return InteractionHint(
        role=parent.role,
        action=parent.action,
        label=parent.label,
        group=parent.group,
        placeholder=parent.placeholder,
        reason=f"inside inferred {parent.role}",
    )


def collect_render_nodes(schema: dict[str, Any]) -> list[RenderNode]:
    nodes: list[RenderNode] = []
    counts: dict[str, int] = {}

    def walk(node: dict[str, Any], inherited_hint: InteractionHint | None = None) -> None:
        if not is_visible(node):
            return
        node_type = node.get("type", "node")
        own_hint = infer_interaction(node)
        if inherited_hint and node_type in {"lanhutext", "lanhuimage"}:
            own_hint = None
        inherited_click = inherit_click_hint(inherited_hint)
        hint = own_hint or inherited_click
        passive_child = bool(inherited_click and not own_hint)
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
            if own_hint:
                if own_hint.action == "input":
                    tag = "input"
                elif own_hint.role == "link":
                    tag = "a"
                elif own_hint.action in {"button", "tab", "toggle", "radio", "select", "dialog", "dismiss"}:
                    tag = "button"
            nodes.append(
                RenderNode(
                    node=node,
                    class_name=class_name,
                    tag=tag,
                    text=text,
                    src=src,
                    role=hint.role if hint else "",
                    action=hint.action if hint else "",
                    label=hint.label if hint else "",
                    group=hint.group if hint else "",
                    placeholder=hint.placeholder if hint else "",
                    reason=hint.reason if hint else "",
                    passive_child=passive_child,
                )
            )
        for child in node.get("children") or []:
            walk(child, own_hint or inherited_hint)

    for child in schema.get("children") or []:
        walk(child)
    return nodes


def interaction_expected_behavior(action: str, role: str) -> str:
    expectations = {
        "button": "Trigger a visible command, navigation, submit, or local state change.",
        "link": "Navigate to the intended route or open the referenced detail surface.",
        "input": "Accept keyboard input, expose value changes, and preserve focus feedback.",
        "tab": "Switch selected state within its group and reveal the matching content panel.",
        "toggle": "Toggle checked/on state with visible selected feedback.",
        "radio": "Select one option within its group and clear sibling options.",
        "select": "Open and close an option list or picker, then commit a selected value.",
        "dialog": "Open or focus the related dialog, drawer, popover, or overlay.",
        "dismiss": "Close the nearest dialog, drawer, popover, or navigate back when appropriate.",
    }
    return expectations.get(action) or f"Implement visible behavior for the inferred {role or action} control."


def interaction_state_attrs(action: str) -> list[str]:
    if action in {"toggle", "radio"}:
        return ["aria-checked", "aria-pressed", "data-lanhu-checked", "data-lanhu-active"]
    if action == "tab":
        return ["aria-selected", "data-lanhu-active"]
    if action in {"select", "dialog"}:
        return ["aria-expanded", "data-lanhu-open"]
    if action == "input":
        return ["value", "focus-visible"]
    return ["data-lanhu-active"]


def interaction_contracts(render_nodes: list[RenderNode]) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for item in render_nodes:
        if not item.action or item.passive_child:
            continue
        node = item.node
        contracts.append(
            {
                "node_id": node.get("id", ""),
                "layer_name": node.get("eleName", ""),
                "class_name": item.class_name,
                "role": item.role,
                "action": item.action,
                "label": item.label,
                "group": item.group,
                "bounds": row_dims(node),
                "reason": item.reason,
                "expected_behavior": interaction_expected_behavior(item.action, item.role),
                "required_state_attrs": interaction_state_attrs(item.action),
                "implementation_note": (
                    "Use an existing project/design-system control when it can preserve Lanhu size, "
                    "style, keyboard access, and visible state feedback."
                ),
            }
        )
    return contracts


def pascal_name(value: str, fallback: str) -> str:
    value = html.unescape(value or "")
    words = re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", value)
    ascii_words = [word for word in words if re.search(r"[A-Za-z0-9]", word)]
    if ascii_words:
        name = "".join(word[:1].upper() + word[1:] for word in ascii_words)
    else:
        name = fallback
    if not re.match(r"[A-Z]", name):
        name = fallback + name[:1].upper() + name[1:]
    return name[:48] or fallback


def component_kind(node: dict[str, Any], interactions: int, visible_children: int, repeated: int) -> tuple[str, str]:
    blob = node_blob(node)
    dims = row_dims(node)
    height = float(dims.get("height") or 0)
    if has_any_keyword(blob, NAV_KEYWORDS):
        return "Navigation", "navigation/menu naming"
    if has_any_keyword(blob, DIALOG_KEYWORDS):
        return "Dialog", "dialog/drawer/popover naming"
    if has_any_keyword(blob, CARD_KEYWORDS) and visible_children >= 3:
        return "CardGrid" if visible_children >= 4 and interactions >= 4 else "CardItem", "card naming"
    if has_any_keyword(blob, FORM_KEYWORDS):
        return "FormRow" if height <= 72 and visible_children >= 3 else "FormSection", "multiple controls or form/search naming"
    if has_any_keyword(blob, TAB_KEYWORDS):
        return "Tabs", "tab/segmented naming"
    if has_any_keyword(blob, LIST_KEYWORDS) and visible_children >= 4:
        return "ListSection", "list/table/grid naming"
    if interactions >= 2 and height <= 72 and visible_children >= 3:
        return "FormRow", "compact interactive control row"
    if interactions >= 2 and visible_children >= 3:
        return "CardGrid" if visible_children >= 4 or visible_descendant_count(node) >= 30 else "CardItem", "interactive repeated content group"
    if repeated >= 2 and visible_children >= 3:
        return "CardGrid", "repeated interactive card structure"
    if repeated >= 2:
        return "CardItem", "card/list-item naming or repeated structure"
    if visible_children >= 8:
        return "Section", "large visible child group"
    return "Component", "semantic group"


def component_candidates(schema: dict[str, Any]) -> list[dict[str, Any]]:
    signatures: dict[str, int] = {}

    def count_signatures(node: dict[str, Any]) -> None:
        if not is_visible(node):
            return
        signatures[structural_signature(node)] = signatures.get(structural_signature(node), 0) + 1
        for child in node.get("children") or []:
            if isinstance(child, dict):
                count_signatures(child)

    count_signatures(schema)

    candidates: dict[tuple[str, str], tuple[int, ComponentCandidate]] = {}

    def walk(node: dict[str, Any]) -> None:
        if not is_visible(node):
            return
        children = [child for child in node.get("children") or [] if isinstance(child, dict) and is_visible(child)]
        child_count = len(children)
        descendants = visible_descendant_count(node)
        interactions = interaction_count(node)
        repeated = signatures.get(structural_signature(node), 0)
        area = bounds_area(node)
        blob = node_blob(node)
        semantic = any(
            has_any_keyword(blob, keywords)
            for keywords in (NAV_KEYWORDS, CARD_KEYWORDS, FORM_KEYWORDS, DIALOG_KEYWORDS, LIST_KEYWORDS, TAB_KEYWORDS)
        )
        meaningful_boundary = area >= 2400 and descendants >= 5
        repeated_boundary = repeated >= 2 and area >= 3200 and descendants >= 8
        should_extract = (
            child_count >= 3
            and meaningful_boundary
            and (
                interactions >= 1
                or repeated_boundary
                or semantic
            )
        )
        if should_extract:
            kind, reason = component_kind(node, interactions, descendants, repeated)
            raw_name = str(node.get("eleName") or collect_text(node, 40) or kind)
            candidate = ComponentCandidate(
                name=raw_name[:80],
                suggested_component=pascal_name(raw_name, kind),
                reason=reason,
                node_type=str(node.get("type") or ""),
                bounds=row_dims(node),
                child_count=child_count,
                visible_descendants=descendants,
                interaction_count=interactions,
                repeated_count=repeated,
                text_sample=collect_text(node, 120),
            )
            score = descendants + interactions * 5 + repeated * 3 + (4 if semantic else 0)
            key = (kind, structural_signature(node))
            existing = candidates.get(key)
            if existing is None or score > existing[0]:
                candidates[key] = (score, candidate)
        for child in children:
            walk(child)

    for child in schema.get("children") or []:
        if isinstance(child, dict):
            walk(child)

    ranked = sorted(candidates.values(), key=lambda item: item[0], reverse=True)
    return [asdict(candidate) for _, candidate in ranked[:40]]


def css_block(selector: str, rules: list[tuple[str, str]]) -> str:
    body = "\n".join(f"  {key}: {value};" for key, value in rules if value != "")
    return f"{selector} {{\n{body}\n}}"


def html_attrs(item: RenderNode) -> str:
    attrs: list[tuple[str, str | None]] = []
    if item.action and not item.passive_child:
        attrs.extend(
            [
                ("data-lanhu-action", item.action),
                ("data-lanhu-label", item.label),
                ("data-lanhu-role", item.role),
                ("data-lanhu-reason", item.reason),
            ]
        )
        if item.group:
            attrs.append(("data-lanhu-group", item.group))
        if item.role and item.tag not in {"button", "input", "a"}:
            attrs.append(("role", item.role))
        if item.tag not in {"button", "input", "a"}:
            attrs.append(("tabindex", "0"))
        if item.action in {"toggle", "radio"}:
            attrs.append(("aria-checked", "false"))
            attrs.append(("aria-pressed", "false"))
        elif item.action == "tab":
            attrs.append(("aria-selected", "false"))
        elif item.action == "select":
            attrs.append(("aria-expanded", "false"))
        elif item.action == "dialog":
            attrs.append(("aria-expanded", "false"))
            attrs.append(("aria-haspopup", "dialog"))
        if item.label and item.tag != "input":
            attrs.append(("aria-label", item.label))
    if item.tag == "a":
        attrs.append(("href", "#"))
    if item.tag == "button":
        attrs.append(("type", "button"))
    if item.tag == "input":
        attrs.append(("type", "text"))
        attrs.append(("aria-label", item.label or item.placeholder or "Lanhu input"))
        if item.placeholder:
            attrs.append(("placeholder", item.placeholder))
        attrs.append(("value", ""))
    rendered = []
    for key, value in attrs:
        if value is None:
            continue
        rendered.append(f'{key}="{html.escape(str(value), quote=True)}"')
    return (" " + " ".join(rendered)) if rendered else ""


def interaction_css() -> str:
    return """.lanhu-interactive {
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
button.lanhu-interactive,
input.lanhu-interactive {
  appearance: none;
  margin: 0;
  padding: 0;
  border: 0;
  font: inherit;
  color: inherit;
}
a.lanhu-interactive {
  color: inherit;
  text-decoration: none;
}
.lanhu-interactive:focus-visible {
  outline: 2px solid rgba(22, 119, 255, 0.72);
  outline-offset: 2px;
}
.lanhu-interactive[data-lanhu-active="true"] {
  filter: brightness(0.96);
}
.lanhu-interactive[data-lanhu-open="true"] {
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.24);
}
.lanhu-toast {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%) translateY(12px);
  z-index: 2147483647;
  max-width: min(360px, calc(100vw - 32px));
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(17, 24, 39, 0.92);
  color: #fff;
  font: 13px/1.4 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}
.lanhu-toast[data-visible="true"] {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}"""


def interaction_script() -> str:
    return """<script>
(() => {
  const page = document.querySelector(".lanhu-page");
  if (!page) return;

  const toast = document.createElement("div");
  toast.className = "lanhu-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  document.body.appendChild(toast);
  let toastTimer = 0;

  const show = (message) => {
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.dataset.visible = "true";
    toastTimer = window.setTimeout(() => {
      toast.dataset.visible = "false";
    }, 1200);
  };

  const setChecked = (target, checked) => {
    target.dataset.lanhuChecked = String(checked);
    target.dataset.lanhuActive = String(checked);
    target.setAttribute("aria-checked", String(checked));
    target.setAttribute("aria-pressed", String(checked));
  };

  const setOpen = (target, open) => {
    target.dataset.lanhuOpen = String(open);
    target.setAttribute("aria-expanded", String(open));
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-lanhu-action]");
    if (!target) return;
    const action = target.dataset.lanhuAction;
    const label = target.dataset.lanhuLabel || "control";
    if (target.tagName === "A" || action !== "input") {
      event.preventDefault();
    }

    if (action === "tab") {
      const group = target.dataset.lanhuGroup || "";
      document.querySelectorAll(`[data-lanhu-action="tab"][data-lanhu-group="${CSS.escape(group)}"]`).forEach((item) => {
        item.dataset.lanhuActive = "false";
        item.setAttribute("aria-selected", "false");
      });
      target.dataset.lanhuActive = "true";
      target.setAttribute("aria-selected", "true");
      show(`已切换到：${label}`);
      page.dataset.lastInteraction = `tab:${label}`;
      return;
    }

    if (action === "toggle") {
      const checked = target.dataset.lanhuChecked !== "true";
      setChecked(target, checked);
      show(`${label}${checked ? "已开启" : "已关闭"}`);
      page.dataset.lastInteraction = `toggle:${label}:${checked}`;
      return;
    }

    if (action === "radio") {
      const group = target.dataset.lanhuGroup || "";
      document.querySelectorAll(`[data-lanhu-action="radio"][data-lanhu-group="${CSS.escape(group)}"]`).forEach((item) => {
        setChecked(item, false);
      });
      setChecked(target, true);
      show(`已选择：${label}`);
      page.dataset.lastInteraction = `radio:${label}`;
      return;
    }

    if (action === "select") {
      const open = target.dataset.lanhuOpen !== "true";
      setOpen(target, open);
      show(`${label}${open ? "已展开" : "已收起"}`);
      page.dataset.lastInteraction = `select:${label}:${open}`;
      return;
    }

    if (action === "dialog") {
      const open = target.dataset.lanhuOpen !== "true";
      setOpen(target, open);
      show(`${label}${open ? "已打开" : "已收起"}`);
      page.dataset.lastInteraction = `dialog:${label}:${open}`;
      return;
    }

    if (action === "dismiss") {
      target.dataset.lanhuActive = "true";
      document.querySelectorAll('[data-lanhu-action="dialog"][data-lanhu-open="true"]').forEach((item) => {
        setOpen(item, false);
      });
      window.setTimeout(() => {
        target.dataset.lanhuActive = "false";
      }, 180);
      show(`已关闭：${label}`);
      page.dataset.lastInteraction = `dismiss:${label}`;
      return;
    }

    target.dataset.lanhuActive = "true";
    window.setTimeout(() => {
      target.dataset.lanhuActive = "false";
    }, 180);
    show(`已触发：${label}`);
    page.dataset.lastInteraction = `${action}:${label}`;
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target.closest("[data-lanhu-action]");
    if (!target || event.defaultPrevented) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      target.click();
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target.closest('input[data-lanhu-action="input"]');
    if (!target) return;
    page.dataset.lastInteraction = `input:${target.dataset.lanhuLabel || target.placeholder || "field"}`;
  });
})();
</script>"""


def generate_html(
    schema: dict[str, Any],
    mapping: dict[str, str],
    title: str,
    include_interactions: bool = True,
    preview_image: str = "",
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
    use_preview_visual = bool(preview_image) and schema.get("designType") == "sketch-fallback"
    if use_preview_visual:
        css_blocks.append(
            ".lanhu-page[data-visual-source=\"preview-image\"] {\n"
            f"  background-image: url(\"{preview_image}\");\n"
            "  background-size: 100% 100%;\n"
            "  background-position: center;\n"
            "  background-repeat: no-repeat;\n"
            "}"
        )
        css_blocks.append(
            ".lanhu-page[data-visual-source=\"preview-image\"] > .lanhu-hit-area {\n"
            "  opacity: 0;\n"
            "  background: transparent !important;\n"
            "  border-color: transparent !important;\n"
            "  box-shadow: none !important;\n"
            "  color: transparent !important;\n"
            "}\n"
            ".lanhu-page[data-visual-source=\"preview-image\"] > .lanhu-hit-area:focus-visible {\n"
            "  opacity: 1;\n"
            "  outline: 2px solid rgba(22, 119, 255, 0.72);\n"
            "}"
        )
    if include_interactions:
        css_blocks.append(interaction_css())

    elements: list[str] = []
    for item in render_nodes:
        rules = style_to_css(item.node, remote_to_local)
        css_blocks.append(css_block(f".{item.class_name}", rules))
        interactive_class = " lanhu-interactive" if include_interactions and item.action and not item.passive_child else ""
        hit_class = " lanhu-hit-area" if use_preview_visual else ""
        attrs = html_attrs(item) if include_interactions else ""
        if item.tag == "span":
            elements.append(f'    <span class="{item.class_name}{interactive_class}{hit_class}"{attrs}>{item.text}</span>')
        elif item.tag == "img":
            src = image_src(item.node, remote_to_local)
            alt = html.escape(item.node.get("eleName") or "Lanhu image")
            elements.append(
                f'    <img class="{item.class_name}{interactive_class}{hit_class}" src="{html.escape(src)}" alt="{alt}"{attrs}>'
            )
        elif item.tag == "input":
            elements.append(f'    <input class="{item.class_name}{interactive_class}{hit_class}"{attrs}>')
        elif item.tag == "a":
            elements.append(f'    <a class="{item.class_name}{interactive_class}{hit_class}"{attrs}></a>')
        elif item.tag == "button":
            elements.append(f'    <button class="{item.class_name}{interactive_class}{hit_class}"{attrs}></button>')
        else:
            elements.append(f'    <div class="{item.class_name}{interactive_class}{hit_class}"{attrs}></div>')

    design_type = schema.get("designType", "")
    width = (schema.get("rowDims") or schema.get("style") or {}).get("width")
    height = (schema.get("rowDims") or schema.get("style") or {}).get("height")
    interactive_nodes = [node for node in render_nodes if node.action and not node.passive_child]
    role_counts: dict[str, int] = {}
    for node in interactive_nodes:
        role_counts[node.role or node.action] = role_counts.get(node.role or node.action, 0) + 1
    contracts = interaction_contracts(render_nodes)
    candidates = component_candidates(schema)

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
  <main class="lanhu-page" data-design-type="{html.escape(str(design_type))}" data-design-width="{width}" data-design-height="{height}"{(' data-visual-source="preview-image"') if use_preview_visual else ''}>
{chr(10).join(elements)}
  </main>
  {interaction_script() if include_interactions else ""}
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
        "interaction_nodes": len(interactive_nodes),
        "interaction_roles": role_counts,
        "interaction_contracts": contracts,
        "component_candidates": candidates,
        "component_strategy": "semantic-boundaries-repeated-structures-interactive-groups",
        "interaction_strategy": "semantic-heuristics-native-controls-event-delegation"
        if include_interactions
        else "disabled",
        "visual_source": "preview-image-overlay" if use_preview_visual else "schema-vector",
        "preview_image": preview_image if use_preview_visual else "",
        "strategy": "absolute-rowDims-flattened-with-interaction-layer"
        if include_interactions
        else "absolute-rowDims-flattened",
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


def infer_preview_path(schema_path: Path, output_dir: Path, explicit: str | None) -> str:
    if explicit:
        preview_path = Path(explicit)
    else:
        preview_path = schema_path.with_name(schema_path.name.replace(".schema.json", ".png"))
    if not preview_path.exists():
        return ""
    adjusted = Path(os.path.relpath(preview_path, output_dir)).as_posix()
    if not adjusted.startswith("."):
        adjusted = f"./{adjusted}"
    return adjusted


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate high-fidelity interactive HTML from Lanhu schema")
    parser.add_argument("--input-dir", default="./lanhu_output", help="Directory containing fetched Lanhu files")
    parser.add_argument("--schema", help="Path to a specific *.schema.json")
    parser.add_argument("--mapping", help="Path to *.image_mapping.json")
    parser.add_argument("--output-dir", help="Output directory for restored files")
    parser.add_argument("--title", help="HTML title")
    parser.add_argument("--preview-image", help="Optional preview PNG to use as visual background for sketch fallback schemas")
    parser.add_argument(
        "--no-interactions",
        action="store_true",
        help="Generate a static baseline without inferred controls or interaction script",
    )
    args = parser.parse_args()

    schema_path, mapping_path, output_dir = infer_paths(args)
    schema = load_json(schema_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_mapping = load_json(mapping_path) if mapping_path.exists() else {}
    mapping = adjust_mapping_paths(raw_mapping, schema_path.parent, output_dir)

    title = args.title or schema_path.name.replace(".schema.json", "")
    preview_image = infer_preview_path(schema_path, output_dir, args.preview_image)
    document, report = generate_html(
        schema,
        mapping,
        title,
        include_interactions=not args.no_interactions,
        preview_image=preview_image,
    )

    html_path = output_dir / "index.html"
    report_path = output_dir / "parity-report.json"
    html_path.write_text(document, encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"html_path": str(html_path), "report_path": str(report_path), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
