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
    parser = argparse.ArgumentParser(description="Create or update the Намаления smart collection")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify Shopify")
    parser.add_argument("--update", action="store_true", help="Update the rule on an existing collection in-place")
    parser.add_argument("--title", default="Намаления", help="Collection title (default: Намаления)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop:    {shop}")
    print(f"  Title:   {args.title}")
    print(f"  Mode:    {'update' if args.update else 'create'}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(shop=shop, access_token=token, dry_run=args.dry_run)

    if args.update:
        ok = creator.update_sale_collection(title=args.title)
        verb = "Updated" if ok else "Failed to update"
    else:
        if not args.dry_run and creator.collection_exists(args.title):
            print(f"\n  Collection '{args.title}' already exists. Use --update to change its rule.")
            return
        ok = creator.create_sale_collection(title=args.title)
        verb = "Created" if ok else "Failed to create"

    print(f"\n  {verb} collection: {args.title}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
