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

    # Push to a specific (non-live) staging theme instead of the default live theme
    python scripts/push_theme.py --theme 200012345678 sections/featured-collection.liquid
    python scripts/push_theme.py --theme 200012345678 --all
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient
from src.shopify.theme_pusher import ThemePusher

LIVE_THEME_ID = os.getenv("SHOPIFY_THEME_ID", "195131081041")
THEME_DIR = Path(__file__).parent.parent.parent / "viapharma.us-theme"


def list_themes(client: ShopifyAPIClient, theme_id: str) -> None:
    """Print all themes on the store."""
    result = client.rest_request("GET", "themes.json")
    if result is None:
        print("[error] Failed to fetch themes (see log for details)")
        sys.exit(1)
    themes = result.get("themes", [])
    print(f"{'ID':<20} {'ROLE':<12} NAME")
    print("-" * 60)
    for t in themes:
        role = t.get("role", "")
        marker = " ← current" if str(t["id"]) == str(theme_id) else ""
        print(f"{t['id']:<20} {role:<12} {t['name']}{marker}")


def resolve_theme_id(client: ShopifyAPIClient, theme_arg: str) -> str:
    """Validate a theme ID exists on the store and return it as a string."""
    result = client.rest_request("GET", "themes.json")
    if result is None:
        print("[error] Failed to fetch themes while validating --theme")
        sys.exit(1)
    themes = {str(t["id"]): t for t in result.get("themes", [])}
    if theme_arg not in themes:
        print(f"[error] Theme ID {theme_arg} not found on this store. Run --list-themes to see available themes.")
        sys.exit(1)
    return theme_arg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push Shopify theme files via Admin API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("files", nargs="*", help="File paths relative to theme root")
    parser.add_argument("--all", action="store_true", help="Push all files in the theme repo")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed without sending")
    parser.add_argument("--list-themes", action="store_true", help="List all themes on the store and exit")
    parser.add_argument(
        "--theme",
        metavar="THEME_ID",
        help=f"Target theme ID (default: live theme {LIVE_THEME_ID}). Use for staging themes during upgrades.",
    )
    args = parser.parse_args()

    client = None
    if not args.dry_run or args.list_themes:
        shop, token = load_shopify_credentials()
        client = ShopifyAPIClient(shop, token)

    if args.list_themes:
        list_themes(client, LIVE_THEME_ID)
        return

    if not args.files and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.theme:
        theme_id = resolve_theme_id(client, args.theme) if client else args.theme
        target_label = f"theme {theme_id} (custom)"
    else:
        theme_id = LIVE_THEME_ID
        target_label = f"theme {theme_id} (live)"

    pusher = ThemePusher(client=client, theme_id=theme_id, theme_dir=THEME_DIR)

    files = pusher.collect_theme_files() if args.all else [THEME_DIR / f for f in args.files]

    shop_display = f"{client.shop}.myshopify.com" if client else "(dry-run)"
    mode = "DRY RUN — " if args.dry_run else ""
    print(f"\n{mode}Pushing to {target_label} on {shop_display}")
    print(f"Theme dir: {THEME_DIR}")
    print(f"Files: {len(files)}\n")

    ok = failed = skipped = 0
    for f in files:
        result = pusher.push_file(f, dry_run=args.dry_run)
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
