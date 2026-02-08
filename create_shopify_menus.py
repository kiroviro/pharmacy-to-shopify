#!/usr/bin/env python3
"""
Shopify Menu Creator

Creates hierarchical navigation menus in Shopify based on product categories.
Uses the Shopify Admin API (GraphQL) to create menus with nested items.

Requirements:
    pip install requests

Usage:
    # Dry run (preview menu structure)
    python3 create_shopify_menus.py --shop STORE --token TOKEN --csv output/products_cleaned.csv --dry-run

    # Create menus
    python3 create_shopify_menus.py --shop STORE --token TOKEN --csv output/products_cleaned.csv

    # Create only brand menu
    python3 create_shopify_menus.py --shop STORE --token TOKEN --csv output/products_cleaned.csv --brands-only
"""

import argparse
import logging
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.common.log_config import setup_logging
from src.shopify import ShopifyMenuCreator

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create Shopify navigation menus from product data"
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
        "--csv", "-c",
        required=True,
        help="Input CSV file with products"
    )
    parser.add_argument(
        "--min-products", "-m",
        type=int,
        default=3,
        help="Minimum products for a category/brand to be included (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't create menus"
    )
    parser.add_argument(
        "--brands-only",
        action="store_true",
        help="Only create the brands menu"
    )
    parser.add_argument(
        "--main-only",
        action="store_true",
        help="Only create the main category menu"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Just preview the menu structure without API calls"
    )
    parser.add_argument(
        "--max-brands",
        type=int,
        default=50,
        help="Maximum brands to include in brands menu (default: 50)"
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
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    print("=" * 60)
    print("Shopify Menu Creator")
    print("=" * 60)
    print(f"  Shop: {args.shop}")
    print(f"  CSV: {args.csv}")
    print(f"  Min products: {args.min_products}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyMenuCreator(
        shop=args.shop,
        access_token=args.token,
        dry_run=args.dry_run
    )

    # Preview mode - no API calls
    if args.preview:
        creator.preview_menu_structure(args.csv, args.min_products)
        return

    # Create menus
    if args.brands_only:
        creator.create_brands_menu(
            csv_path=args.csv,
            min_products=args.min_products,
            max_brands=args.max_brands
        )
    elif args.main_only:
        creator.create_main_menu(
            csv_path=args.csv,
            min_products=args.min_products
        )
    else:
        # Create both
        creator.create_main_menu(
            csv_path=args.csv,
            min_products=args.min_products
        )
        creator.create_brands_menu(
            csv_path=args.csv,
            min_products=args.min_products,
            max_brands=args.max_brands
        )


if __name__ == "__main__":
    main()
