#!/usr/bin/env python3
"""
Shopify Collection Creator

Creates smart collections in Shopify based on tags from a product CSV.
Each unique tag becomes a smart collection with rule: "tag equals [tag_name]"

Requirements:
    pip install requests

Usage:
    # Dry run (preview only)
    python3 create_shopify_collections.py --csv products.csv --shop STORE --token TOKEN --dry-run

    # Create collections (min 3 products by default)
    python3 create_shopify_collections.py --csv products.csv --shop STORE --token TOKEN

    # Create collections excluding brand tags (use with --vendors-only separately)
    python3 create_shopify_collections.py --csv products.csv --shop STORE --token TOKEN --skip-brands

    # Create only brand collections from Vendor field
    python3 create_shopify_collections.py --csv products.csv --shop STORE --token TOKEN --vendors-only

    # Create only collections with 5+ products
    python3 create_shopify_collections.py --csv products.csv --shop STORE --token TOKEN --min-products 5
"""

import argparse
import logging
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging
from src.shopify import ShopifyCollectionCreator

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create Shopify smart collections from CSV tags"
    )
    parser.add_argument(
        "--csv", "-c",
        required=True,
        help="Input Shopify CSV file with products"
    )
    parser.add_argument(
        "--shop", "-s",
        required=True,
        help="Shopify shop name (e.g., 'my-store' or 'my-store.myshopify.com')"
    )
    parser.add_argument(
        "--token", "-t",
        required=True,
        help="Shopify Admin API access token"
    )
    parser.add_argument(
        "--min-products", "-m",
        type=int,
        default=3,
        help="Minimum products for a tag to become a collection (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't create collections"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Don't skip existing collections (may cause errors)"
    )
    parser.add_argument(
        "--skip-brands",
        action="store_true",
        help="Skip tags that match vendor names (avoid brand duplicates)"
    )
    parser.add_argument(
        "--vendors-only",
        action="store_true",
        help="Only create collections from Vendor field (brand collections)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages, show only warnings and errors"
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Validate CSV exists
    if not os.path.exists(args.csv):
        print(f"CSV file not found: {args.csv}")
        sys.exit(1)

    print("=" * 60)
    print("Shopify Collection Creator")
    print("=" * 60)
    print(f"  Shop: {args.shop}")
    print(f"  CSV: {args.csv}")
    print(f"  Min products: {args.min_products}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Skip brands: {args.skip_brands}")
    print(f"  Vendors only: {args.vendors_only}")

    # Create collections
    creator = ShopifyCollectionCreator(
        shop=args.shop,
        access_token=args.token,
        dry_run=args.dry_run,
    )

    creator.create_collections_from_csv(
        csv_path=args.csv,
        min_products=args.min_products,
        skip_existing=not args.no_skip_existing,
        skip_brands=args.skip_brands,
        vendors_only=args.vendors_only,
    )


if __name__ == "__main__":
    main()
