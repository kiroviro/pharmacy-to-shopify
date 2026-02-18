#!/usr/bin/env python3
"""
Price Monitoring System: benu.bg vs viapharma.us

Monitors price changes and syncs Shopify store without full re-crawl.

WORKFLOW:
1. Fetch current prices from benu.bg (source of truth)
2. Fetch current prices from viapharma.us (Shopify store)
3. Generate change report with three categories:
   - Price increases (benu.bg raised prices)
   - Price decreases (benu.bg lowered prices)
   - Drift detected (viapharma.us doesn't match benu.bg)

4. Options for syncing:
   --report-only     Just generate report, no changes
   --auto-sync       Automatically update Shopify prices
   --review          Generate report and ask for confirmation

Usage:
    # Daily monitoring (report only)
    python3 scripts/price_monitor.py --report-only

    # Sync prices to Shopify (requires API credentials)
    python3 scripts/price_monitor.py --auto-sync

    # Interactive review mode
    python3 scripts/price_monitor.py --review

    # Check specific products
    python3 scripts/price_monitor.py --handles "product-handle-1,product-handle-2"

    # Sample check (100 random products)
    python3 scripts/price_monitor.py --sample 100 --report-only

SETUP:
    Set environment variables:
    - SHOPIFY_SHOP: Your shop name (e.g., "viapharma-us")
    - SHOPIFY_ACCESS_TOKEN: Admin API access token
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

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.constants import EUR_TO_BGN
from src.shopify.api_client import ShopifyAPIClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class PriceInfo:
    """Price information for a product."""

    handle: str
    title: str
    benu_bgn: float | None = None
    benu_eur: float | None = None
    shopify_bgn: float | None = None
    shopify_eur: float | None = None
    error: str | None = None


@dataclass
class PriceChange:
    """Detected price change."""

    handle: str
    title: str
    old_price: float
    new_price: float
    change_pct: float
    source: str  # "benu" or "drift"


class PriceMonitor:
    """
    Monitor and sync prices between benu.bg and viapharma.us.

    Attributes:
        shopify_client: Shopify API client (optional, for sync)
        products: Dict mapping handle -> product info
    """

    def __init__(self, shopify_shop: str | None = None, shopify_token: str | None = None):
        self.shopify_client = None
        if shopify_shop and shopify_token:
            self.shopify_client = ShopifyAPIClient(shopify_shop, shopify_token)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
        })

        # Product cache
        self.products: dict[str, PriceInfo] = {}
        self.changes: list[PriceChange] = []

    def fetch_benu_price(self, handle: str) -> tuple[float | None, float | None, str | None]:
        """
        Fetch live price from benu.bg.

        Args:
            handle: Product URL handle

        Returns:
            Tuple of (price_bgn, price_eur, error)
        """
        url = f"https://benu.bg/{handle}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Extract from JSON-LD (most reliable)
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
                            return price_bgn, price_eur, None
                except (json.JSONDecodeError, ValueError):
                    continue

            return None, None, "No JSON-LD price found"

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None, None, "Product not found (404)"
            return None, None, f"HTTP {e.response.status_code}"
        except Exception as e:
            return None, None, str(e)[:50]

    def fetch_shopify_prices(self, handles: list[str]) -> dict[str, tuple[float | None, str | None]]:
        """
        Fetch prices from Shopify using GraphQL.

        Args:
            handles: List of product handles

        Returns:
            Dict mapping handle -> (price, error)
        """
        if not self.shopify_client:
            return {h: (None, "No Shopify client") for h in handles}

        results = {}

        # GraphQL query to fetch products by handle
        query = """
        query getProductByHandle($handle: String!) {
            productByHandle(handle: $handle) {
                handle
                title
                variants(first: 1) {
                    edges {
                        node {
                            price
                        }
                    }
                }
            }
        }
        """

        for handle in handles:
            try:
                data = self.shopify_client.graphql_request(query, {"handle": handle})
                if data and data.get("productByHandle"):
                    product = data["productByHandle"]
                    variants = product.get("variants", {}).get("edges", [])
                    if variants:
                        price = float(variants[0]["node"]["price"])
                        results[handle] = (price, None)
                    else:
                        results[handle] = (None, "No variants")
                else:
                    results[handle] = (None, "Not found")
            except Exception as e:
                results[handle] = (None, str(e)[:50])

            time.sleep(0.3)  # Rate limit

        return results

    def load_products_from_csv(self, csv_path: str) -> list[str]:
        """
        Load product handles from existing Shopify CSV.

        Args:
            csv_path: Path to products.csv

        Returns:
            List of product handles
        """
        handles = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only main product rows (with Title)
                if row.get("Title", "").strip():
                    handle = row.get("URL handle", "").strip()
                    if handle:
                        handles.append(handle)
        return handles

    def compare_prices(
        self,
        handles: list[str],
        delay: float = 0.5,
        progress_callback=None,
    ) -> list[PriceChange]:
        """
        Compare prices between benu.bg and Shopify.

        Args:
            handles: Product handles to check
            delay: Delay between requests
            progress_callback: Optional callback(current, total)

        Returns:
            List of detected price changes
        """
        changes = []
        total = len(handles)

        # Batch fetch Shopify prices if client available
        shopify_prices = {}
        if self.shopify_client:
            logger.info("Fetching prices from Shopify...")
            shopify_prices = self.fetch_shopify_prices(handles)

        logger.info("Comparing %d products with benu.bg...", total)

        for i, handle in enumerate(handles, 1):
            if progress_callback:
                progress_callback(i, total)

            # Fetch benu.bg price
            benu_bgn, benu_eur, benu_error = self.fetch_benu_price(handle)

            if benu_error:
                logger.debug("Skipping %s: %s", handle, benu_error)
                continue

            # Compare with Shopify
            if handle in shopify_prices:
                shopify_price, shopify_error = shopify_prices[handle]
                if shopify_price and benu_bgn:
                    diff = abs(shopify_price - benu_bgn)
                    tolerance = max(0.50, benu_bgn * 0.02)  # 2% or 0.50 BGN

                    if diff > tolerance:
                        change_pct = ((benu_bgn - shopify_price) / shopify_price) * 100
                        changes.append(PriceChange(
                            handle=handle,
                            title=handle[:40],  # Will be enriched later
                            old_price=shopify_price,
                            new_price=benu_bgn,
                            change_pct=change_pct,
                            source="benu" if benu_bgn > shopify_price else "drift",
                        ))

            time.sleep(delay)

        self.changes = changes
        return changes

    def generate_report(self, changes: list[PriceChange]) -> str:
        """Generate human-readable price change report."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "=" * 80,
            f"PRICE MONITORING REPORT - {now}",
            "=" * 80,
            "",
            f"Products checked: {len(self.products) or 'N/A'}",
            f"Price changes detected: {len(changes)}",
            "",
        ]

        if not changes:
            lines.append("✓ All prices are in sync!")
            lines.append("")
            return "\n".join(lines)

        # Group by change type
        increases = [c for c in changes if c.change_pct > 0]
        decreases = [c for c in changes if c.change_pct < 0]

        if increases:
            lines.append("-" * 80)
            lines.append(f"PRICE INCREASES ({len(increases)} products)")
            lines.append("-" * 80)
            for c in sorted(increases, key=lambda x: -x.change_pct):
                lines.append(
                    f"  {c.handle[:50]}..."
                    f"\n    {c.old_price:.2f} → {c.new_price:.2f} BGN (+{c.change_pct:.1f}%)"
                )
            lines.append("")

        if decreases:
            lines.append("-" * 80)
            lines.append(f"PRICE DECREASES ({len(decreases)} products)")
            lines.append("-" * 80)
            for c in sorted(decreases, key=lambda x: x.change_pct):
                lines.append(
                    f"  {c.handle[:50]}..."
                    f"\n    {c.old_price:.2f} → {c.new_price:.2f} BGN ({c.change_pct:.1f}%)"
                )
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def sync_to_shopify(self, changes: list[PriceChange], dry_run: bool = True) -> int:
        """
        Update Shopify prices using Admin API.

        Args:
            changes: List of price changes to apply
            dry_run: If True, don't actually update

        Returns:
            Number of products updated
        """
        if not self.shopify_client:
            logger.error("No Shopify client configured")
            return 0

        if dry_run:
            logger.info("[DRY RUN] Would update %d products", len(changes))
            return 0

        # GraphQL mutation to update variant price
        mutation = """
        mutation productVariantUpdate($input: ProductVariantInput!) {
            productVariantUpdate(input: $input) {
                productVariant {
                    id
                    price
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        updated = 0
        for change in changes:
            # First, get the variant ID
            query = """
            query getProductVariant($handle: String!) {
                productByHandle(handle: $handle) {
                    variants(first: 1) {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
            }
            """

            data = self.shopify_client.graphql_request(query, {"handle": change.handle})
            if not data or not data.get("productByHandle"):
                logger.warning("Product not found: %s", change.handle)
                continue

            variants = data["productByHandle"].get("variants", {}).get("edges", [])
            if not variants:
                logger.warning("No variants for: %s", change.handle)
                continue

            variant_id = variants[0]["node"]["id"]

            # Update the price
            result = self.shopify_client.graphql_request(
                mutation,
                {"input": {"id": variant_id, "price": str(change.new_price)}},
            )

            if result:
                user_errors = result.get("productVariantUpdate", {}).get("userErrors", [])
                if user_errors:
                    logger.error("Error updating %s: %s", change.handle, user_errors)
                else:
                    updated += 1
                    logger.info("Updated %s: %.2f BGN", change.handle, change.new_price)

            time.sleep(0.5)  # Rate limit

        return updated


def main():
    parser = argparse.ArgumentParser(
        description="Monitor and sync prices between benu.bg and viapharma.us"
    )
    parser.add_argument(
        "--csv",
        default="data/benu.bg/raw/products.csv",
        help="Path to products CSV (for handle list)",
    )
    parser.add_argument(
        "--handles",
        help="Comma-separated list of specific handles to check",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Check random sample of N products",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report without syncing",
    )
    parser.add_argument(
        "--auto-sync",
        action="store_true",
        help="Automatically sync prices to Shopify",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Don't actually update Shopify (default)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests (seconds)",
    )
    parser.add_argument(
        "--output",
        help="Save report to file",
    )

    args = parser.parse_args()

    # Get Shopify credentials
    shop = os.environ.get("SHOPIFY_SHOP")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")

    if args.auto_sync and not (shop and token):
        logger.error("SHOPIFY_SHOP and SHOPIFY_ACCESS_TOKEN required for --auto-sync")
        sys.exit(1)

    # Initialize monitor
    monitor = PriceMonitor(shop, token)

    # Get handles to check
    if args.handles:
        handles = [h.strip() for h in args.handles.split(",")]
    elif os.path.exists(args.csv):
        handles = monitor.load_products_from_csv(args.csv)
        logger.info("Loaded %d products from %s", len(handles), args.csv)
    else:
        logger.error("No products to check. Provide --csv or --handles")
        sys.exit(1)

    # Sample if requested
    if args.sample and len(handles) > args.sample:
        handles = random.sample(handles, args.sample)
        logger.info("Sampling %d random products", args.sample)

    # Compare prices
    def progress(current, total):
        if current % 10 == 0:
            print(f"  Progress: {current}/{total} ({current * 100 // total}%)", end="\r")

    changes = monitor.compare_prices(handles, delay=args.delay, progress_callback=progress)
    print()  # Clear progress line

    # Generate report
    report = monitor.generate_report(changes)
    print(report)

    # Save report if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Report saved to %s", args.output)

    # Sync to Shopify if requested
    if args.auto_sync and changes:
        if args.dry_run:
            logger.info("[DRY RUN] Would update %d products", len(changes))
        else:
            updated = monitor.sync_to_shopify(changes, dry_run=False)
            logger.info("Updated %d products in Shopify", updated)

    # Exit with code based on changes
    sys.exit(0 if not changes else 1)


if __name__ == "__main__":
    main()
