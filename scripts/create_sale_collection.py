#!/usr/bin/env python3
"""
Create or update the "Намаления" smart collection in Shopify.

Auto-includes all products where compare_at_price > 0 (i.e., on sale).
Shopify evaluates the rule live after every price write — no tagging needed.

Usage:
    python scripts/create_sale_collection.py              # Create collection (first time)
    python scripts/create_sale_collection.py --update     # Update rule on existing collection
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
    parser = argparse.ArgumentParser(description="Create or update sale/liquidation smart collections")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify Shopify")
    parser.add_argument("--update", action="store_true", help="Update the rule on an existing collection in-place")
    parser.add_argument("--title", default="Намаления", help="Collection title (default: Намаления)")
    parser.add_argument("--likvidatsii", action="store_true", help="Create the Ликвидации collection (handle: likvidatsii)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop:    {shop}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(shop=shop, access_token=token, dry_run=args.dry_run)

    if args.likvidatsii:
        print("  Mode:    create Ликвидации collection")
        ok = creator.create_liquidation_collection()
        verb = "Created" if ok else "Failed to create"
        print(f"\n  {verb} collection: Ликвидации (handle: likvidatsii)")
    elif args.update:
        print(f"  Title:   {args.title}")
        print("  Mode:    update")
        ok = creator.update_sale_collection(title=args.title)
        verb = "Updated" if ok else "Failed to update"
        print(f"\n  {verb} collection: {args.title}")
    else:
        print(f"  Title:   {args.title}")
        print("  Mode:    create")
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
