#!/usr/bin/env python3
"""
Shopify Theme Backup

Downloads the active Shopify theme to a local directory for version control.
Only text assets (Liquid, CSS, JS, JSON, locale files) are saved — binary
assets (images, fonts) are skipped since they don't benefit from diffing.

Usage:
    python3 scripts/backup_theme.py
    python3 scripts/backup_theme.py --output theme/
    python3 scripts/backup_theme.py --shop STORE --token TOKEN
    python3 scripts/backup_theme.py --theme-id 193881276753  # specific theme ID

Credentials (in order of precedence):
    1. --shop / --token flags
    2. SHOPIFY_SHOP / SHOPIFY_ACCESS_TOKEN environment variables
    3. .shopify_token.json (written by shopify_oauth.py)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.common.log_config import setup_logging
from src.shopify import ShopifyAPIClient

load_dotenv()

logger = logging.getLogger(__name__)

# Binary content types — skip these, they don't benefit from git diffing
BINARY_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp",
    "image/svg+xml", "image/x-icon", "image/vnd.microsoft.icon",
    "font/woff", "font/woff2", "font/ttf", "font/otf", "font/eot",
    "application/font-woff", "application/font-woff2",
    "application/vnd.ms-fontobject", "application/octet-stream",
}

# Binary file extensions — fallback check when content_type is missing
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def _load_token_file() -> tuple[str, str] | tuple[None, None]:
    """Try to read shop + token from .shopify_token.json."""
    token_file = Path(__file__).parent.parent / ".shopify_token.json"
    if token_file.exists():
        try:
            data = json.loads(token_file.read_text())
            return data.get("shop"), data.get("access_token")
        except (json.JSONDecodeError, OSError):
            pass
    return None, None


def _is_binary(asset: dict) -> bool:
    """Return True if this asset is binary (image, font, etc.)."""
    content_type = asset.get("content_type", "")
    if content_type in BINARY_CONTENT_TYPES:
        return True
    ext = Path(asset["key"]).suffix.lower()
    return ext in BINARY_EXTENSIONS


def _find_active_theme(client: ShopifyAPIClient) -> dict | None:
    """Return the active (role=main) theme dict, or None on failure."""
    result = client.rest_request("GET", "themes.json")
    if not result:
        return None
    themes = result.get("themes", [])
    return next((t for t in themes if t.get("role") == "main"), None)


def backup_theme(
    client: ShopifyAPIClient,
    output_dir: Path,
    theme_id: int | None = None,
) -> dict:
    """
    Download all text assets of a theme to output_dir.

    Returns a summary dict with keys: theme_name, theme_id, written, skipped, failed.
    """
    # Resolve theme
    if theme_id is None:
        theme = _find_active_theme(client)
        if not theme:
            logger.error("No active theme found")
            sys.exit(1)
        theme_id = theme["id"]
        theme_name = theme.get("name", "Unknown")
    else:
        theme_name = f"theme-{theme_id}"

    logger.info("Theme: %s (ID: %d)", theme_name, theme_id)

    # List all assets
    result = client.rest_request("GET", f"themes/{theme_id}/assets.json")
    if not result:
        logger.error("Failed to list theme assets")
        sys.exit(1)

    assets = result.get("assets", [])
    logger.info("Found %d total assets", len(assets))

    text_assets = [a for a in assets if not _is_binary(a)]
    binary_count = len(assets) - len(text_assets)
    logger.info(
        "Downloading %d text assets (skipping %d binary)",
        len(text_assets), binary_count,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    failed = 0

    for i, asset in enumerate(text_assets, 1):
        key = asset["key"]

        # Fetch full asset content
        result = client.rest_request(
            "GET", f"themes/{theme_id}/assets.json?asset[key]={key}"
        )
        if not result or "asset" not in result:
            logger.warning("Failed to fetch: %s", key)
            failed += 1
            continue

        content = result["asset"].get("value")
        if content is None:
            # Shopify returned attachment (base64 binary) — skip
            logger.debug("Skipping binary attachment: %s", key)
            skipped += 1
            continue

        out_path = output_dir / key
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        written += 1

        if i % 25 == 0 or i == len(text_assets):
            logger.info("  %d/%d assets downloaded", i, len(text_assets))

    # Write metadata file so we know when this backup was taken
    metadata = {
        "theme_name": theme_name,
        "theme_id": theme_id,
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "assets_total": len(assets),
        "assets_text": len(text_assets),
        "assets_binary_skipped": binary_count,
        "assets_written": written,
        "assets_failed": failed,
    }
    (output_dir / "THEME_INFO.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {**metadata, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Back up the active Shopify theme to a local directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        default="theme",
        metavar="DIR",
        help="Directory to write theme files (default: theme/)",
    )
    parser.add_argument(
        "--shop",
        help="Shopify store name (default: SHOPIFY_SHOP env var or .shopify_token.json)",
    )
    parser.add_argument(
        "--token",
        help="Shopify Admin API access token (default: SHOPIFY_ACCESS_TOKEN env var)",
    )
    parser.add_argument(
        "--theme-id",
        type=int,
        metavar="ID",
        help="Theme ID to back up (default: active/main theme)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Resolve credentials
    shop = args.shop or os.environ.get("SHOPIFY_SHOP")
    token = args.token or os.environ.get("SHOPIFY_ACCESS_TOKEN")

    if not shop or not token:
        file_shop, file_token = _load_token_file()
        shop = shop or file_shop
        token = token or file_token

    if not shop or not token:
        print(
            "ERROR: Shopify credentials not found.\n"
            "Use --shop / --token, set SHOPIFY_SHOP / SHOPIFY_ACCESS_TOKEN,\n"
            "or run shopify_oauth.py first to create .shopify_token.json."
        )
        sys.exit(1)

    output_dir = Path(args.output)

    with ShopifyAPIClient(shop=shop, access_token=token) as client:
        if not client.test_connection():
            print("ERROR: Could not connect to Shopify. Check your credentials.")
            sys.exit(1)

        summary = backup_theme(client, output_dir, theme_id=args.theme_id)

    print()
    print("Theme backup complete")
    print(f"  Theme:    {summary['theme_name']} (ID: {summary['theme_id']})")
    print(f"  Output:   {output_dir}/")
    print(f"  Written:  {summary['assets_written']} files")
    print(f"  Skipped:  {summary['assets_binary_skipped']} binary assets")
    if summary["assets_failed"]:
        print(f"  Failed:   {summary['assets_failed']} assets (check logs)")
    print()
    print(f"  git add {output_dir}/ && git commit -m 'chore: backup Shopify theme'")


if __name__ == "__main__":
    main()
