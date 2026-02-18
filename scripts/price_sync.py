#!/usr/bin/env python3
"""
Price Sync: Detect price changes and generate Shopify import CSV.

Compares benu.bg prices with viapharma.us and outputs a minimal CSV
containing only products with price changes, ready for Shopify import.

Usage:
    # Check sample and generate report
    python3 scripts/price_sync.py --sample 100

    # Full catalog check
    python3 scripts/price_sync.py

    # Output CSV for Shopify import
    python3 scripts/price_sync.py --output output/price_updates.csv

    # Check specific products
    python3 scripts/price_sync.py --handles "handle1,handle2,handle3"
"""

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Add project root to path for proper package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.constants import EUR_TO_BGN

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class PriceChange:
    """Detected price change for a product."""
    handle: str
    title: str
    old_bgn: float
    new_bgn: float
    old_eur: float
    new_eur: float
    change_pct: float
    benu_url: str
    shopify_url: str


def fetch_benu_price(session: requests.Session, handle: str) -> tuple[float | None, float | None, str | None]:
    """Fetch live price from benu.bg using JSON-LD."""
    url = f"https://benu.bg/{handle}"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") == "Product":
                    offers = data.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = offers.get("price")
                    if price:
                        price_eur = float(str(price).replace(",", "."))
                        price_bgn = round(price_eur * EUR_TO_BGN, 2)
                        return price_bgn, round(price_eur, 2), None
            except (json.JSONDecodeError, ValueError):
                continue

        return None, None, "No price in JSON-LD"

    except requests.exceptions.HTTPError as e:
        return None, None, f"HTTP {e.response.status_code}"
    except Exception as e:
        return None, None, str(e)[:40]


def fetch_shopify_price(session: requests.Session, handle: str) -> tuple[float | None, float | None, str | None]:
    """Fetch current price from viapharma.us product JSON."""
    url = f"https://viapharma.us/products/{handle}.json"
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 404:
            return None, None, "Not found on Shopify"
        resp.raise_for_status()

        data = resp.json()
        product = data.get("product", {})
        variants = product.get("variants", [])

        if variants:
            price_str = variants[0].get("price", "0")
            price_bgn = float(price_str)
            price_eur = round(price_bgn / EUR_TO_BGN, 2)
            return price_bgn, price_eur, None

        return None, None, "No variants"

    except Exception as e:
        return None, None, str(e)[:40]


def load_handles_from_csv(csv_path: str) -> list[tuple[str, str]]:
    """Load (handle, title) pairs from products CSV."""
    products = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Title", "").strip():
                handle = row.get("URL handle", "").strip()
                title = row.get("Title", "").strip()
                if handle:
                    products.append((handle, title))
    return products


def compare_prices(
    products: list[tuple[str, str]],
    delay: float = 0.3,
) -> list[PriceChange]:
    """
    Compare prices between benu.bg and viapharma.us.

    Returns list of products with price differences.
    """
    changes = []
    total = len(products)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
    })

    print(f"\nComparing {total} products...\n")
    print(f"{'#':>4} | {'Status':<10} | {'Handle':<50} | {'Shopify':>10} | {'Benu.bg':>10} | {'Diff':>8}")
    print("-" * 100)

    for i, (handle, title) in enumerate(products, 1):
        # Fetch both prices
        shopify_bgn, shopify_eur, shopify_err = fetch_shopify_price(session, handle)

        if shopify_err:
            print(f"{i:4} | {'SKIP':<10} | {handle[:50]:<50} | {'N/A':>10} | {'N/A':>10} | {shopify_err}")
            time.sleep(delay)
            continue

        benu_bgn, benu_eur, benu_err = fetch_benu_price(session, handle)

        if benu_err:
            print(f"{i:4} | {'SKIP':<10} | {handle[:50]:<50} | {shopify_bgn:>10.2f} | {'N/A':>10} | {benu_err}")
            time.sleep(delay)
            continue

        # Compare
        diff = benu_bgn - shopify_bgn
        diff_pct = (diff / shopify_bgn) * 100 if shopify_bgn else 0
        tolerance = max(0.50, shopify_bgn * 0.02)  # 2% or 0.50 BGN

        if abs(diff) <= tolerance:
            status = "MATCH"
        elif diff > 0:
            status = "INCREASE"
        else:
            status = "DECREASE"

        # Format diff string
        if diff > 0:
            diff_str = f"+{diff:.2f}"
        else:
            diff_str = f"{diff:.2f}"

        print(f"{i:4} | {status:<10} | {handle[:50]:<50} | {shopify_bgn:>10.2f} | {benu_bgn:>10.2f} | {diff_str:>8}")

        # Record change if significant
        if abs(diff) > tolerance:
            changes.append(PriceChange(
                handle=handle,
                title=title,
                old_bgn=shopify_bgn,
                new_bgn=benu_bgn,
                old_eur=shopify_eur,
                new_eur=benu_eur,
                change_pct=diff_pct,
                benu_url=f"https://benu.bg/{handle}",
                shopify_url=f"https://viapharma.us/products/{handle}",
            ))

        time.sleep(delay)

    return changes


def generate_shopify_csv(changes: list[PriceChange], output_path: str) -> None:
    """
    Generate Shopify-compatible CSV with price updates.

    Uses minimal fields required for price update import:
    - Handle (to match existing products)
    - Variant Price (new price)
    """
    fieldnames = [
        "Handle",
        "Title",
        "Variant Price",
        "Variant Compare At Price",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for change in changes:
            writer.writerow({
                "Handle": change.handle,
                "Title": change.title,
                "Variant Price": f"{change.new_bgn:.2f}",
                "Variant Compare At Price": "",  # Clear compare-at price
            })

    print(f"\nCSV saved to: {output_path}")
    print(f"Products to update: {len(changes)}")


def print_summary(changes: list[PriceChange]) -> None:
    """Print summary of price changes."""
    if not changes:
        print("\n" + "=" * 80)
        print("✓ ALL PRICES IN SYNC - No updates needed")
        print("=" * 80)
        return

    increases = [c for c in changes if c.change_pct > 0]
    decreases = [c for c in changes if c.change_pct < 0]

    print("\n" + "=" * 80)
    print("PRICE CHANGES DETECTED")
    print("=" * 80)
    print(f"\nTotal changes: {len(changes)}")
    print(f"  Price increases: {len(increases)}")
    print(f"  Price decreases: {len(decreases)}")

    if increases:
        print(f"\n--- TOP INCREASES ---")
        for c in sorted(increases, key=lambda x: -x.change_pct)[:5]:
            print(f"  {c.handle[:40]}...")
            print(f"    {c.old_bgn:.2f} → {c.new_bgn:.2f} BGN (+{c.change_pct:.1f}%)")
            print(f"    {c.benu_url}")

    if decreases:
        print(f"\n--- TOP DECREASES ---")
        for c in sorted(decreases, key=lambda x: x.change_pct)[:5]:
            print(f"  {c.handle[:40]}...")
            print(f"    {c.old_bgn:.2f} → {c.new_bgn:.2f} BGN ({c.change_pct:.1f}%)")
            print(f"    {c.benu_url}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Detect price changes and generate Shopify import CSV"
    )
    parser.add_argument(
        "--csv",
        default="/Users/kiril/IdeaProjects/pharmacy-to-shopify/data/benu.bg/raw/products.csv",
        help="Source products CSV",
    )
    parser.add_argument(
        "--handles",
        help="Comma-separated handles to check (instead of CSV)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Check random sample of N products",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output CSV path for Shopify import",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between requests (seconds)",
    )

    args = parser.parse_args()

    # Get products to check
    if args.handles:
        handles = args.handles.split(",")
        products = [(h.strip(), h.strip()) for h in handles]
    elif os.path.exists(args.csv):
        products = load_handles_from_csv(args.csv)
        print(f"Loaded {len(products)} products from {args.csv}")
    else:
        print(f"Error: CSV not found: {args.csv}")
        sys.exit(1)

    # Sample if requested
    if args.sample and len(products) > args.sample:
        products = random.sample(products, args.sample)
        print(f"Sampling {args.sample} random products")

    # Compare prices
    changes = compare_prices(products, delay=args.delay)

    # Print summary
    print_summary(changes)

    # Generate CSV if output specified and changes found
    if args.output and changes:
        generate_shopify_csv(changes, args.output)
        print("\nTo import into Shopify:")
        print("  1. Go to Shopify Admin > Products > Import")
        print("  2. Upload the CSV file")
        print("  3. Select 'Overwrite existing products with matching handles'")
        print("  4. Review and confirm")
    elif changes and not args.output:
        print("\nTo generate Shopify import CSV, run with --output:")
        print(f"  python3 scripts/price_sync.py --output output/price_updates.csv")


if __name__ == "__main__":
    main()
