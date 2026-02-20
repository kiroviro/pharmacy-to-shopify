#!/usr/bin/env python3
"""
Shopify Post-Import Verification Script

Verifies that products in the raw CSV were successfully imported
into Shopify by fetching each product handle via the Admin API.

Usage:
    python3 scripts/verify_shopify.py \\
        --csv data/benu.bg/raw/products.csv \\
        --shop viapharma \\
        [--sample 100] \\
        [--token shpat_xxx]   # or set SHOPIFY_ACCESS_TOKEN env var

Exit codes:
    0 = all sampled products found and verified
    1 = missing products or field mismatches detected
"""

import argparse
import csv
import logging
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging
from src.shopify.api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)

# Price tolerance: 5%
_PRICE_TOLERANCE = 0.05


def read_handles_from_csv(csv_path: str) -> list[dict]:
    """Read product rows (with non-empty Title) from raw CSV."""
    products = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Title", "").strip() and row.get("URL handle", "").strip():
                products.append({
                    "handle": row["URL handle"].strip(),
                    "title": row.get("Title", "").strip(),
                    "vendor": row.get("Vendor", "").strip(),
                    "price": row.get("Price", "").strip(),
                    "sku": row.get("SKU", "").strip(),
                })
    return products


def verify_product(
    client: ShopifyAPIClient, source: dict
) -> dict:
    """
    Fetch a single product from Shopify by handle and compare fields.

    Returns a result dict with keys: handle, found, issues.
    """
    handle = source["handle"]
    result = {"handle": handle, "found": False, "issues": []}

    data = client.rest_request("GET", f"products.json?handle={handle}&fields=title,vendor,variants")
    if not data:
        result["issues"].append("API request failed")
        return result

    shopify_products = data.get("products", [])
    if not shopify_products:
        result["issues"].append("product not found in Shopify")
        return result

    result["found"] = True
    sp = shopify_products[0]

    # Title comparison (case-insensitive)
    shopify_title = sp.get("title", "")
    if source["title"].lower() != shopify_title.lower():
        result["issues"].append(
            f"title mismatch: CSV={source['title']!r}, Shopify={shopify_title!r}"
        )

    # Vendor comparison
    shopify_vendor = sp.get("vendor", "")
    if source["vendor"] and source["vendor"].lower() != shopify_vendor.lower():
        result["issues"].append(
            f"vendor mismatch: CSV={source['vendor']!r}, Shopify={shopify_vendor!r}"
        )

    # Price comparison (check first variant)
    variants = sp.get("variants", [])
    if source["price"] and variants:
        try:
            csv_price = float(source["price"])
            shopify_price = float(variants[0].get("price", 0))
            if csv_price > 0:
                deviation = abs(csv_price - shopify_price) / csv_price
                if deviation > _PRICE_TOLERANCE:
                    result["issues"].append(
                        f"price mismatch: CSV={csv_price:.2f}, "
                        f"Shopify={shopify_price:.2f} "
                        f"({deviation:.1%} deviation)"
                    )
        except (ValueError, TypeError):
            pass

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Shopify products against raw products CSV"
    )
    parser.add_argument("--csv", required=True, help="Path to raw products CSV")
    parser.add_argument("--shop", required=True, help="Shopify shop name (without .myshopify.com)")
    parser.add_argument(
        "--sample",
        type=int,
        default=100,
        metavar="N",
        help="Number of products to sample for verification (default: 100)",
    )
    parser.add_argument(
        "--token",
        help="Shopify Admin API access token (default: reads SHOPIFY_ACCESS_TOKEN env var)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Resolve token
    token = args.token or os.environ.get("SHOPIFY_ACCESS_TOKEN")
    if not token:
        print("ERROR: No Shopify access token. Use --token or set SHOPIFY_ACCESS_TOKEN.")
        sys.exit(1)

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV file not found: {args.csv}")
        sys.exit(1)

    products = read_handles_from_csv(args.csv)
    if not products:
        print("No products with handles found in CSV.")
        sys.exit(1)

    sample_size = min(args.sample, len(products))
    sample = random.sample(products, sample_size)

    print("\nShopify Post-Import Verification")
    print(f"  Shop:    {args.shop}.myshopify.com")
    print(f"  CSV:     {args.csv}")
    print(f"  Total:   {len(products)} products in CSV")
    print(f"  Sample:  {sample_size}")
    print()

    client = ShopifyAPIClient(shop=args.shop, access_token=token)
    if not client.test_connection():
        print("ERROR: Could not connect to Shopify API. Check shop name and token.")
        client.close()
        sys.exit(1)

    results = []
    missing = 0
    mismatched = 0

    for i, source in enumerate(sample, 1):
        res = verify_product(client, source)
        results.append(res)

        if not res["found"]:
            missing += 1
            status = "❌ MISSING"
        elif res["issues"]:
            mismatched += 1
            status = "⚠️  MISMATCH"
        else:
            status = "✅ OK"

        print(f"  [{i:>4}/{sample_size}] {status}  {res['handle'][:60]}")
        for issue in res["issues"]:
            print(f"           {issue}")

    client.close()

    # Summary
    verified = sample_size - missing - mismatched
    verified_pct = verified / sample_size * 100
    missing_pct = missing / sample_size * 100
    mismatch_pct = mismatched / sample_size * 100

    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print(f"  ✅ Verified (no issues):  {verified:>4}  ({verified_pct:.1f}%)")
    print(f"  ⚠️  Field mismatches:      {mismatched:>4}  ({mismatch_pct:.1f}%)")
    print(f"  ❌ Missing from Shopify:  {missing:>4}  ({missing_pct:.1f}%)")
    print("=" * 60)

    has_failures = missing > 0 or mismatched > 0
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
