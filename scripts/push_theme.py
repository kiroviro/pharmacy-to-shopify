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
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

# ── Config ────────────────────────────────────────────────────────────────────

THEME_ID = os.getenv("SHOPIFY_THEME_ID", "195131081041")

# Theme repo lives next to this project
THEME_DIR = Path(__file__).parent.parent.parent / "viapharma.us-theme"

# ── Helpers ───────────────────────────────────────────────────────────────────

BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"}

# Module-level client — initialized in main()
_client: ShopifyAPIClient | None = None


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
    result = _client.rest_request("PUT", f"themes/{THEME_ID}/assets.json", data={"asset": asset})
    if result is not None:
        updated_at = result.get("asset", {}).get("updated_at", "")
        print(f"  [ok]    {key}  ({updated_at})")
        return True
    else:
        print(f"  [error] {key}  (see log for details)")
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
    result = _client.rest_request("GET", "themes.json")
    if result is None:
        print("[error] Failed to fetch themes (see log for details)")
        sys.exit(1)
    themes = result.get("themes", [])
    print(f"{'ID':<20} {'ROLE':<12} NAME")
    print("-" * 60)
    for t in themes:
        role = t.get("role", "")
        marker = " ← current" if str(t["id"]) == str(THEME_ID) else ""
        print(f"{t['id']:<20} {role:<12} {t['name']}{marker}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    global _client

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

    if not args.dry_run or args.list_themes:
        shop, token = load_shopify_credentials()
        _client = ShopifyAPIClient(shop, token)

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

    shop_display = f"{_client.shop}.myshopify.com" if _client else "(dry-run)"
    mode = "DRY RUN — " if args.dry_run else ""
    print(f"\n{mode}Pushing to theme {THEME_ID} on {shop_display}")
    print(f"Theme dir: {THEME_DIR}")
    print(f"Files: {len(files)}\n")

    ok = failed = skipped = 0

    for f in files:
        result = push_file(f, dry_run=args.dry_run)
        if result:
            ok += 1
        elif f.exists():
            failed += 1
        else:
            skipped += 1

    print(f"\nDone. {ok} pushed, {failed} failed, {skipped} skipped.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
