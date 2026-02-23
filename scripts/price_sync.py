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
import logging
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Add project root to path for proper package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.constants import BENU_USER_AGENT, EUR_TO_BGN
from src.common.price_change import PriceChange
from src.common.price_fetcher import fetch_benu_price

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Thread-local storage: one session per worker thread (avoids shared-state race conditions)
_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Return this thread's session, creating it on first use."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
        _thread_local.session.headers.update({"User-Agent": BENU_USER_AGENT})
    return _thread_local.session


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


def _fetch_shopify_with_delay(
    handle: str, delay: float
) -> tuple[str, float | None, float | None, str | None]:
    """Fetch a single Shopify price, with rate-limit delay. Returns (handle, bgn, eur, error)."""
    result = fetch_shopify_price(_get_session(), handle)
    time.sleep(delay)
    return (handle, *result)


def _fetch_benu_with_delay(
    handle: str, delay: float
) -> tuple[str, float | None, float | None, str | None]:
    """Fetch a single benu.bg price, with rate-limit delay. Returns (handle, bgn, eur, error)."""
    result = fetch_benu_price(_get_session(), handle)
    time.sleep(delay)
    return (handle, *result)


def compare_prices(
    products: list[tuple[str, str]],
    delay: float = 0.3,
    max_workers: int = 5,
) -> list[PriceChange]:
    """
    Compare prices between benu.bg and viapharma.us.

    Fetches Shopify and benu.bg prices concurrently using ThreadPoolExecutor,
    then compares the pre-fetched data without further HTTP calls.

    Returns list of products with price differences.
    """
    total = len(products)
    handles = [h for h, _ in products]

    # Phase 1: Fetch all Shopify prices concurrently (each thread uses its own session)
    print(f"\nFetching {total} Shopify prices (max_workers={max_workers})...")
    shopify_data: dict[str, tuple[float | None, float | None, str | None]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_shopify_with_delay, h, delay): h
            for h in handles
        }
        for future in as_completed(futures):
            h, bgn, eur, err = future.result()
            shopify_data[h] = (bgn, eur, err)

    # Phase 2: Fetch all benu.bg prices concurrently (each thread uses its own session)
    print(f"Fetching {total} benu.bg prices (max_workers={max_workers})...")
    benu_data: dict[str, tuple[float | None, float | None, str | None]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_benu_with_delay, h, delay): h
            for h in handles
        }
        for future in as_completed(futures):
            h, bgn, eur, err = future.result()
            benu_data[h] = (bgn, eur, err)

    # Phase 3: Compare pre-fetched data (no HTTP)
    changes = []
    print(f"\nComparing {total} products...\n")
    print(f"{'#':>4} | {'Status':<10} | {'Handle':<50} | {'Shopify':>10} | {'Benu.bg':>10} | {'Diff':>8}")
    print("-" * 100)

    for i, (handle, title) in enumerate(products, 1):
        shopify_bgn, shopify_eur, shopify_err = shopify_data.get(handle, (None, None, "Missing"))
        benu_bgn, benu_eur, benu_err = benu_data.get(handle, (None, None, "Missing"))

        if shopify_err:
            print(f"{i:4} | {'SKIP':<10} | {handle[:50]:<50} | {'N/A':>10} | {'N/A':>10} | {shopify_err}")
            continue

        if benu_err:
            print(f"{i:4} | {'SKIP':<10} | {handle[:50]:<50} | {shopify_bgn:>10.2f} | {'N/A':>10} | {benu_err}")
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

        diff_str = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
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
        print("\n--- TOP INCREASES ---")
        for c in sorted(increases, key=lambda x: -x.change_pct)[:5]:
            print(f"  {c.handle[:40]}...")
            print(f"    {c.old_bgn:.2f} → {c.new_bgn:.2f} BGN (+{c.change_pct:.1f}%)")
            print(f"    {c.benu_url}")

    if decreases:
        print("\n--- TOP DECREASES ---")
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
        default="data/benu.bg/raw/products.csv",
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
        print("  python3 scripts/price_sync.py --output output/price_updates.csv")


if __name__ == "__main__":
    main()
