#!/usr/bin/env python3
"""Verify Lanhu restored HTML against the preview PNG and interaction layer."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
from urllib.parse import urljoin

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError as e:
    raise SystemExit(
        "Error: Pillow is required for visual parity checks. "
        "Run `pip install -r plugins/lanhu/requirements.txt`."
    ) from e

try:
    from playwright.async_api import async_playwright
except ImportError as e:
    raise SystemExit(
        "Error: Playwright is required for rendered parity checks. "
        "Run `pip install -r plugins/lanhu/requirements.txt` and "
        "`python -m playwright install chromium`."
    ) from e


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_first(pattern_dir: Path, suffix: str) -> Path:
    matches = sorted(pattern_dir.glob(f"*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"No *{suffix} found in {pattern_dir}")
    return matches[0]


def infer_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    input_dir = Path(args.input_dir)
    restore_dir = Path(args.restore_dir) if args.restore_dir else input_dir / "restore"
    html_path = Path(args.html) if args.html else restore_dir / "index.html"
    preview_path = Path(args.preview) if args.preview else find_first(input_dir, ".png")
    report_path = Path(args.report) if args.report else restore_dir / "parity-report.json"
    return input_dir, html_path, preview_path, report_path


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def visual_metrics(preview_path: Path, screenshot_path: Path, width: int, height: int) -> dict:
    preview = Image.open(preview_path).convert("RGB")
    screenshot = Image.open(screenshot_path).convert("RGB")
    crop = screenshot.crop((0, 0, min(width, screenshot.width), min(height, screenshot.height)))
    if crop.size != (width, height):
        padded = Image.new("RGB", (width, height), "white")
        padded.paste(crop, (0, 0))
        crop = padded
    scaled_preview = preview.resize((width, height))
    diff = ImageChops.difference(scaled_preview, crop)
    stat = ImageStat.Stat(diff)
    mean_abs = sum(stat.mean) / len(stat.mean)
    rmse = math.sqrt(sum(channel * channel for channel in stat.rms) / len(stat.rms))
    visual_match = max(0.0, 100.0 * (1.0 - mean_abs / 255.0))
    exact_or_near = 0
    total = width * height
    tolerance = 3
    pixels = diff.get_flattened_data() if hasattr(diff, "get_flattened_data") else diff.getdata()
    for pixel in pixels:
        if max(pixel) <= tolerance:
            exact_or_near += 1
    return {
        "preview_size": list(preview.size),
        "screenshot_size": list(screenshot.size),
        "canvas_size": [width, height],
        "mean_abs_delta": round(mean_abs, 4),
        "rmse": round(rmse, 4),
        "visual_match_percent": round(visual_match, 4),
        "pixels_within_tolerance_percent": round(100.0 * exact_or_near / total, 4),
    }


async def render_and_probe(html_path: Path, screenshot_path: Path, width: int, height: int) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height + 100}, device_scale_factor=1)
        await page.goto(file_url(html_path), wait_until="networkidle")
        await page.screenshot(path=str(screenshot_path), full_page=True)
        metrics = await page.evaluate(
            """() => {
              const pageEl = document.querySelector('.lanhu-page');
              const controls = [...document.querySelectorAll('[data-lanhu-action]')];
              const byAction = controls.reduce((acc, el) => {
                acc[el.dataset.lanhuAction] = (acc[el.dataset.lanhuAction] || 0) + 1;
                return acc;
              }, {});
              return {
                title: document.title,
                visualSource: pageEl?.dataset.visualSource || '',
                controls: controls.length,
                byAction,
                textLength: document.body.innerText.length,
                remoteUrls: document.documentElement.outerHTML.match(/https?:\\/\\//g)?.length || 0,
              };
            }"""
        )
        input_value = ""
        first_input = page.locator('[data-lanhu-action="input"]').first
        if await first_input.count():
            await first_input.fill("Lanhu parity input")
            input_value = await first_input.input_value()
        await browser.close()
    metrics["inputProbeValue"] = input_value
    return metrics


async def main_async(args: argparse.Namespace) -> int:
    input_dir, html_path, preview_path, report_path = infer_paths(args)
    report = load_json(report_path) if report_path.exists() else {}
    width = int(args.width or report.get("width") or 0)
    height = int(args.height or report.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Design width/height could not be inferred; pass --width and --height.")

    output_dir = Path(args.output_dir) if args.output_dir else input_dir / "verify"
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / "parity-screenshot.png"

    render_metrics = await render_and_probe(html_path, screenshot_path, width, height)
    image_metrics = visual_metrics(preview_path, screenshot_path, width, height)
    result = {
        "passed": True,
        "threshold_percent": args.threshold,
        "html_path": str(html_path),
        "preview_path": str(preview_path),
        "screenshot_path": str(screenshot_path),
        "render": render_metrics,
        "visual": image_metrics,
    }

    failures = []
    if image_metrics["visual_match_percent"] < args.threshold:
        failures.append(
            f"visual_match_percent {image_metrics['visual_match_percent']} < {args.threshold}"
        )
    if args.require_interactions and render_metrics["controls"] <= 0:
        failures.append("no inferred interaction controls found")
    if render_metrics["remoteUrls"] != 0:
        failures.append(f"remote URLs remain in restored HTML: {render_metrics['remoteUrls']}")
    if failures:
        result["passed"] = False
        result["failures"] = failures

    result_path = output_dir / "verify-report.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Lanhu visual parity against preview PNG")
    parser.add_argument("--input-dir", default="./lanhu_output", help="Directory containing fetched Lanhu files")
    parser.add_argument("--restore-dir", help="Directory containing restore/index.html and parity-report.json")
    parser.add_argument("--html", help="Path to restored HTML")
    parser.add_argument("--preview", help="Path to Lanhu preview PNG")
    parser.add_argument("--report", help="Path to restore/parity-report.json")
    parser.add_argument("--output-dir", help="Directory for screenshot and verify-report.json")
    parser.add_argument("--threshold", type=float, default=99.0, help="Required visual match percent")
    parser.add_argument("--width", type=int, help="Design width override")
    parser.add_argument("--height", type=int, help="Design height override")
    parser.add_argument(
        "--require-interactions",
        action="store_true",
        help="Fail if no inferred interactive controls are found",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
