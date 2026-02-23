"""
Shared Shopify credential loading.

Resolves credentials from environment variables first, then falls back
to .shopify_token.json (written by shopify_oauth.py).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_shopify_credentials() -> tuple[str, str]:
    """
    Load Shopify shop name and access token.

    Resolution order:
        1. SHOPIFY_SHOP_URL / SHOPIFY_ACCESS_TOKEN env vars
        2. .shopify_token.json in project root

    Returns:
        Tuple of (shop, access_token). Shop is the bare name
        (e.g. "61a7bb-4d") without .myshopify.com suffix.

    Raises:
        SystemExit: If no credentials found.
    """
    # Try dotenv if available
    try:
        from dotenv import load_dotenv
        load_dotenv(_PROJECT_ROOT / ".env")
    except ImportError:
        pass

    shop = os.getenv("SHOPIFY_SHOP_URL", "")
    token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

    # Fallback to token file
    if not shop or not token:
        token_file = _PROJECT_ROOT / ".shopify_token.json"
        if token_file.exists():
            data = json.loads(token_file.read_text())
            shop = shop or data.get("shop", "")
            token = token or data.get("access_token", "")

    # Normalize shop name — strip protocol, .myshopify.com suffix
    shop = shop.replace("https://", "").replace("http://", "").rstrip("/")
    if ".myshopify.com" in shop:
        shop = shop.split(".myshopify.com")[0]

    if not shop or not token:
        logger.error("No Shopify credentials found. Set SHOPIFY_SHOP_URL and "
                      "SHOPIFY_ACCESS_TOKEN env vars, or run shopify_oauth.py")
        raise SystemExit(1)

    return shop, token
