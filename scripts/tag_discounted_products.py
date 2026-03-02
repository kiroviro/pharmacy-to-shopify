#!/usr/bin/env python3
"""
Tag discounted products in Shopify.

Scans all products and adds/removes a "Намаление" tag based on whether
any variant has compare_at_price > price.

Usage:
    python scripts/tag_discounted_products.py              # Tag products
    python scripts/tag_discounted_products.py --dry-run    # Preview only
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.common.log_config import setup_logging
from src.shopify.tagger import DiscountTagger

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Tag discounted products in Shopify")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't modify products",
    )
    parser.add_argument(
        "--tag",
        default="Намаление",
        help="Tag name to apply (default: Намаление)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Discount Product Tagger")
    print("=" * 60)
    print(f"  Shop: {shop}")
    print(f"  Tag: {args.tag}")
    print(f"  Dry run: {args.dry_run}")

    tagger = DiscountTagger(
        shop=shop,
        access_token=token,
        dry_run=args.dry_run,
        tag=args.tag,
    )
    tagger.run()


if __name__ == "__main__":
    main()
