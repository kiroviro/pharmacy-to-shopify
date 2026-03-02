#!/usr/bin/env python3
"""
Create a "Намаления" smart collection in Shopify.

Auto-includes all products where compare_at_price > 0 (i.e., on sale).

Usage:
    python scripts/create_sale_collection.py              # Create collection
    python scripts/create_sale_collection.py --dry-run    # Preview only
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.common.log_config import setup_logging
from src.shopify import ShopifyCollectionCreator

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Create a sale smart collection in Shopify")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't create the collection",
    )
    parser.add_argument(
        "--title",
        default="Намаления",
        help="Collection title (default: Намаления)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop: {shop}")
    print(f"  Title: {args.title}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(
        shop=shop,
        access_token=token,
        dry_run=args.dry_run,
    )

    # Check if already exists
    if not args.dry_run:
        existing = creator.get_existing_collections()
        if args.title.lower() in existing:
            print(f"\n  Collection '{args.title}' already exists. Skipping.")
            return

    if creator.create_sale_collection(title=args.title):
        print(f"\n  Created collection: {args.title}")
    else:
        print(f"\n  Failed to create collection: {args.title}")
        sys.exit(1)


if __name__ == "__main__":
    main()
