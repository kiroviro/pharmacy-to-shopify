#!/usr/bin/env python3
"""
Push theme files to Shopify via the Admin API.

Usage:
    # Push one or more specific files
    python scripts/push_theme.py assets/component-card.css
    python scripts/push_theme.py sections/multicolumn.liquid templates/index.json

    # Push all files in the theme repo
    python scripts/push_theme.py --all

    # Preview what would be pushed without sending
    python scripts/push_theme.py --dry-run assets/component-card.css
    python scripts/push_theme.py --dry-run --all

    # List available themes on the store
    python scripts/push_theme.py --list-themes
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────

def _load_token_file() -> tuple[str, str]:
    """Fallback: read shop + token from .shopify_token.json written by shopify_oauth.py."""
    token_file = Path(__file__).parent.parent / ".shopify_token.json"
    if token_file.exists():
        data = json.loads(token_file.read_text())
        shop = data.get("shop", "")
        if shop and "." not in shop:
            shop = f"{shop}.myshopify.com"
        return shop, data.get("access_token", "")
    return "", ""

_token_shop, _token_access = _load_token_file()

SHOP_URL = (os.getenv("SHOPIFY_SHOP_URL") or _token_shop).rstrip("/")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN") or _token_access
THEME_ID = os.getenv("SHOPIFY_THEME_ID", "195131081041")
API_VERSION = "2024-01"

# Theme repo lives next to this project
THEME_DIR = Path(__file__).parent.parent.parent / "viapharma.us-theme"

# Shopify rate limit: 2 req/s for REST API (leaky bucket 40 calls, fills at 2/s)
REQUEST_DELAY = 0.6  # seconds between requests

# ── Helpers ───────────────────────────────────────────────────────────────────

BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"}


def api_url() -> str:
    return f"https://{SHOP_URL}/admin/api/{API_VERSION}/themes/{THEME_ID}/assets.json"


def headers() -> dict:
    return {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def validate_config() -> None:
    missing = []
    if not SHOP_URL:
        missing.append("SHOPIFY_SHOP_URL")
    if not ACCESS_TOKEN:
        missing.append("SHOPIFY_ACCESS_TOKEN")
    if missing:
        print(f"[error] Missing env vars: {', '.join(missing)}")
        print("        Set them in .env or export them before running.")
        sys.exit(1)


def theme_key(file_path: Path) -> str:
    """Convert absolute path to Shopify asset key, e.g. 'assets/component-card.css'."""
    return str(file_path.relative_to(THEME_DIR))


def build_asset_payload(file_path: Path) -> dict:
    """Build the asset dict for the API request."""
    key = theme_key(file_path)
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        return {"key": key, "attachment": encoded}
    else:
        return {"key": key, "value": file_path.read_text(encoding="utf-8")}


def push_file(file_path: Path, dry_run: bool = False) -> bool:
    """Push a single file. Returns True on success."""
    key = theme_key(file_path)

    if not file_path.exists():
        print(f"  [skip]  {key}  (file not found)")
        return False

    if dry_run:
        size = file_path.stat().st_size
        print(f"  [dry]   {key}  ({size:,} bytes)")
        return True

    asset = build_asset_payload(file_path)
    response = requests.put(api_url(), headers=headers(), json={"asset": asset}, timeout=30)

    if response.status_code == 200:
        updated_at = response.json().get("asset", {}).get("updated_at", "")
        print(f"  [ok]    {key}  ({updated_at})")
        return True
    else:
        print(f"  [error] {key}  HTTP {response.status_code}: {response.text[:200]}")
        return False


def collect_theme_files() -> list[Path]:
    """Return all text/binary theme files, excluding non-theme artifacts."""
    exclude = {".git", "node_modules", ".DS_Store", "THEME_INFO.json", "README.md"}
    files = []
    for f in sorted(THEME_DIR.rglob("*")):
        if f.is_file() and not any(part in exclude for part in f.parts):
            files.append(f)
    return files


def list_themes() -> None:
    """Print all themes on the store."""
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/themes.json"
    response = requests.get(url, headers=headers(), timeout=15)
    if response.status_code != 200:
        print(f"[error] HTTP {response.status_code}: {response.text[:200]}")
        sys.exit(1)
    themes = response.json().get("themes", [])
    print(f"{'ID':<20} {'ROLE':<12} NAME")
    print("-" * 60)
    for t in themes:
        role = t.get("role", "")
        marker = " ← current" if str(t["id"]) == str(THEME_ID) else ""
        print(f"{t['id']:<20} {role:<12} {t['name']}{marker}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push Shopify theme files via Admin API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("files", nargs="*", help="File paths relative to theme root (e.g. assets/component-card.css)")
    parser.add_argument("--all", action="store_true", help="Push all files in the theme repo")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed without sending")
    parser.add_argument("--list-themes", action="store_true", help="List all themes on the store and exit")
    args = parser.parse_args()

    if not args.dry_run:
        validate_config()

    if args.list_themes:
        list_themes()
        return

    if not args.files and not args.all:
        parser.print_help()
        sys.exit(1)

    # Resolve file list
    if args.all:
        files = collect_theme_files()
    else:
        files = [THEME_DIR / f for f in args.files]

    mode = "DRY RUN — " if args.dry_run else ""
    print(f"\n{mode}Pushing to theme {THEME_ID} on {SHOP_URL}")
    print(f"Theme dir: {THEME_DIR}")
    print(f"Files: {len(files)}\n")

    ok = failed = skipped = 0

    for i, f in enumerate(files):
        result = push_file(f, dry_run=args.dry_run)
        if result:
            ok += 1
        elif f.exists():
            failed += 1
        else:
            skipped += 1

        # Rate limiting — pause between requests (skip on dry run)
        if not args.dry_run and i < len(files) - 1:
            time.sleep(REQUEST_DELAY)

    print(f"\nDone. {ok} pushed, {failed} failed, {skipped} skipped.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
