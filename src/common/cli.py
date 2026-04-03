"""
Common CLI script utilities.

Eliminates boilerplate across 20+ scripts: sys.path setup,
argument parsing, logging configuration, credential loading.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path so `from src...` imports work
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.common.credentials import load_shopify_credentials  # noqa: E402
from src.common.log_config import setup_logging  # noqa: E402
from src.shopify.api_client import ShopifyAPIClient  # noqa: E402


def base_parser(
    description: str,
    *,
    shopify: bool = True,
) -> argparse.ArgumentParser:
    """Create an ArgumentParser with common flags.

    Args:
        description: Script description for --help.
        shopify: If True, add --dry-run flag (most Shopify scripts need it).

    Returns:
        ArgumentParser with --verbose and optionally --dry-run flags.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    if shopify:
        parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify Shopify")
    return parser


def init_logging(args: argparse.Namespace) -> None:
    """Configure logging from parsed args (expects --verbose flag)."""
    setup_logging(verbose=getattr(args, "verbose", False))


def shopify_client_from_env() -> tuple[ShopifyAPIClient, str, str]:
    """Load credentials and return (client, shop, token).

    Returns:
        Tuple of (ShopifyAPIClient, shop_name, access_token).
    """
    shop, token = load_shopify_credentials()
    return ShopifyAPIClient(shop, token), shop, token
