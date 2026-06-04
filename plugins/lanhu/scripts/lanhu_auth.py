#!/usr/bin/env python3
"""
Lanhu local authentication helper.

Commands:
    python scripts/lanhu_auth.py login --url "<LANHU_URL>"
    python scripts/lanhu_auth.py status
    python scripts/lanhu_auth.py clear

The login command opens an interactive browser window, lets the user complete
Lanhu/SSO login, then encrypts Lanhu cookies with Windows DPAPI and stores them
locally for fetch_lanhu.py.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from ctypes import wintypes
from datetime import datetime, timezone
from time import time
from pathlib import Path

DEFAULT_LOGIN_URL = "https://lanhuapp.com/web/"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _default_auth_file() -> Path:
    base = os.getenv("APPDATA")
    if base:
        root = Path(base) / "Codex" / "lanhu"
    else:
        root = Path.home() / ".codex" / "lanhu"
    return root / "cookies.dpapi"


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob._buffer = buffer  # keep buffer alive while the Win32 call runs
    return blob


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def _dpapi_encrypt(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI cookie storage is only available on Windows.")
    crypt32 = ctypes.windll.crypt32
    in_blob = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "Lanhu Codex Plugin Cookies",
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    return _bytes_from_blob(out_blob)


def _dpapi_decrypt(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI cookie storage is only available on Windows.")
    crypt32 = ctypes.windll.crypt32
    in_blob = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    return _bytes_from_blob(out_blob)


def save_cookie_store(payload: dict, auth_file: Path | None = None) -> Path:
    auth_file = auth_file or _default_auth_file()
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    auth_file.write_bytes(_dpapi_encrypt(plaintext))
    return auth_file


def load_cookie_store(auth_file: Path | None = None) -> dict:
    auth_file = auth_file or _default_auth_file()
    if not auth_file.exists():
        raise FileNotFoundError(f"Lanhu cookie store not found: {auth_file}")
    plaintext = _dpapi_decrypt(auth_file.read_bytes())
    return json.loads(plaintext.decode("utf-8"))


def _is_cookie_expired(cookie: dict, now: float | None = None) -> bool:
    expires = cookie.get("expires")
    if expires in (None, -1, 0):
        return False
    try:
        expires_at = float(expires)
    except (TypeError, ValueError):
        return False
    return expires_at <= (now or time())


def is_cookie_store_expired(payload: dict) -> bool:
    cookies = [
        cookie
        for cookie in payload.get("cookies", [])
        if "lanhuapp.com" in cookie.get("domain", "") and cookie.get("name")
    ]
    if not cookies:
        return True
    now = time()
    return all(_is_cookie_expired(cookie, now) for cookie in cookies)


def cookie_store_summary(payload: dict) -> dict:
    cookies = [
        cookie
        for cookie in payload.get("cookies", [])
        if "lanhuapp.com" in cookie.get("domain", "") and cookie.get("name")
    ]
    expiring = []
    session_count = 0
    for cookie in cookies:
        expires = cookie.get("expires")
        if expires in (None, -1, 0):
            session_count += 1
            continue
        try:
            expiring.append(float(expires))
        except (TypeError, ValueError):
            session_count += 1
    next_expiry = min(expiring) if expiring else None
    return {
        "cookie_count": len(cookies),
        "session_cookie_count": session_count,
        "expired": is_cookie_store_expired(payload),
        "next_expiry": (
            datetime.fromtimestamp(next_expiry, timezone.utc).isoformat()
            if next_expiry
            else None
        ),
    }


def load_cookie_header(auth_file: Path | None = None, silent: bool = False) -> str:
    try:
        payload = load_cookie_store(auth_file)
    except FileNotFoundError:
        if silent:
            return ""
        raise
    if is_cookie_store_expired(payload):
        if silent:
            return ""
        raise RuntimeError("Saved Lanhu cookies are expired. Run `lanhu_auth.py login` again.")
    return payload.get("cookie_header", "")


def _cookie_header_from_playwright(cookies: list[dict]) -> str:
    filtered = []
    seen = set()
    now = time()
    for cookie in cookies:
        domain = cookie.get("domain", "")
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if "lanhuapp.com" not in domain or not name:
            continue
        if _is_cookie_expired(cookie, now):
            continue
        if name in seen:
            continue
        seen.add(name)
        filtered.append(f"{name}={value}")
    return "; ".join(filtered)


def login(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        print(
            "Error: playwright is not installed. Run `pip install -r requirements.txt` "
            "and then `python -m playwright install chromium`.",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    url = args.url or DEFAULT_LOGIN_URL
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        print("Lanhu login browser opened.")
        print("Complete Lanhu/SSO login in the browser window.")
        input("After the Lanhu project/design page is accessible, press Enter here...")

        cookies = context.cookies(["https://lanhuapp.com", "https://dds.lanhuapp.com"])
        cookie_header = _cookie_header_from_playwright(cookies)
        browser.close()

    if not cookie_header:
        print("Error: no Lanhu cookies were captured. Please log in and try again.", file=sys.stderr)
        return 1

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "login_url": url,
        "cookie_header": cookie_header,
        "cookies": cookies,
    }
    auth_file = save_cookie_store(payload, Path(args.auth_file) if args.auth_file else None)
    print(f"Saved encrypted Lanhu cookies to: {auth_file}")
    print(f"Captured {len(cookies)} cookies; cookie names: {', '.join(c.get('name', '') for c in cookies)}")
    return 0


def status(args: argparse.Namespace) -> int:
    auth_file = Path(args.auth_file) if args.auth_file else _default_auth_file()
    try:
        payload = load_cookie_store(auth_file)
    except FileNotFoundError:
        print(f"No encrypted Lanhu cookie store found at: {auth_file}")
        return 1
    cookies = payload.get("cookies", [])
    summary = cookie_store_summary(payload)
    print(f"Encrypted Lanhu cookie store: {auth_file}")
    print(f"Created at: {payload.get('created_at', 'unknown')}")
    print(f"Cookie count: {summary['cookie_count']}")
    print(f"Session cookies: {summary['session_cookie_count']}")
    print(f"Expired: {summary['expired']}")
    if summary["next_expiry"]:
        print(f"Next expiry: {summary['next_expiry']}")
    print("Cookie names: " + ", ".join(c.get("name", "") for c in cookies))
    return 0


def clear(args: argparse.Namespace) -> int:
    auth_file = Path(args.auth_file) if args.auth_file else _default_auth_file()
    if auth_file.exists():
        auth_file.unlink()
        print(f"Removed encrypted Lanhu cookie store: {auth_file}")
    else:
        print(f"No encrypted Lanhu cookie store found at: {auth_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lanhu local login and encrypted cookie storage")
    parser.add_argument("--auth-file", help="Custom encrypted cookie store path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Open browser login and save encrypted cookies")
    login_parser.add_argument("--url", default=DEFAULT_LOGIN_URL, help="Lanhu URL to open for login")
    login_parser.set_defaults(func=login)

    status_parser = subparsers.add_parser("status", help="Show encrypted cookie store metadata")
    status_parser.set_defaults(func=status)

    clear_parser = subparsers.add_parser("clear", help="Remove encrypted Lanhu cookies")
    clear_parser.set_defaults(func=clear)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
