#!/usr/bin/env python3
"""
Daily monitor for ViaPharma DSA Google Ads campaign.

Queries Shopify orders from the last 24 hours, separates Google Ads traffic
from organic, calculates revenue, and flags anomalies.

Campaign: ViaPharma DSA (ID: 23713866882)
Account: 825-619-0101 (ViaPharma US)
Started: 2026-04-03
Daily budget: €10, Max CPC: €0.50

Usage:
    python scripts/monitor_dsa_campaign.py
    python scripts/monitor_dsa_campaign.py --days 7   # Look back 7 days
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.credentials import load_shopify_credentials
from src.shopify.api_client import ShopifyAPIClient

CAMPAIGN_START = datetime(2026, 4, 3, tzinfo=timezone.utc)
DAILY_BUDGET_EUR = 20.0


def load_client() -> ShopifyAPIClient:
    shop, token = load_shopify_credentials()
    return ShopifyAPIClient(shop=shop, access_token=token)


def is_google_ads_order(order: dict) -> bool:
    """Check if order came from Google Ads (paid search)."""
    # Check landing_site for gclid parameter
    landing = order.get("landing_site") or ""
    if "gclid" in landing:
        return True

    # Check referring_site
    referrer = order.get("referring_site") or ""
    if "google" in referrer.lower() and ("gclid" in referrer or "ads" in referrer.lower()):
        return True

    # Check UTM tags in landing_site_ref or note attributes
    if "utm_source=google" in landing and "utm_medium=cpc" in landing:
        return True

    # Check source_name
    source = order.get("source_name") or ""
    if source == "google":
        return True

    # Check customer visit tracking via note attributes or tags
    tags = order.get("tags") or ""
    if "google_ads" in tags.lower() or "gclid" in tags.lower():
        return True

    return False


def fetch_orders(client: ShopifyAPIClient, since: datetime) -> list[dict]:
    """Fetch all orders since the given datetime."""
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%S%z")
    return client.paginate_rest(
        f"orders.json?status=any&created_at_min={since_iso}", "orders"
    )


def compute_revenue(orders: list[dict]) -> float:
    """Sum total_price across orders (EUR)."""
    return sum(float(o.get("total_price", 0)) for o in orders)


def main():
    parser = argparse.ArgumentParser(description="Monitor ViaPharma DSA campaign")
    parser.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)
    campaign_days = (now - CAMPAIGN_START).days

    client = load_client()
    orders = fetch_orders(client, since)

    google_orders = [o for o in orders if is_google_ads_order(o)]
    organic_orders = [o for o in orders if not is_google_ads_order(o)]

    google_revenue = compute_revenue(google_orders)
    organic_revenue = compute_revenue(organic_orders)
    total_revenue = google_revenue + organic_revenue

    estimated_spend = min(args.days, campaign_days) * DAILY_BUDGET_EUR

    # Print report
    period = f"last {args.days} day(s)" if args.days > 1 else "last 24 hours"
    print(f"\n{'='*60}")
    print(f"  ViaPharma DSA Campaign Monitor — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"  Period: {period} (since {since.strftime('%Y-%m-%d %H:%M')})")
    print(f"  Campaign running: {campaign_days} day(s)")
    print()
    print(f"  Orders (total):       {len(orders)}")
    print(f"  ├─ Google Ads:        {len(google_orders)}  (€{google_revenue:.2f})")
    print(f"  └─ Organic/other:     {len(organic_orders)}  (€{organic_revenue:.2f})")
    print()
    print(f"  Revenue:              €{total_revenue:.2f}")
    budget_days = min(args.days, campaign_days)
    print(f"  Est. ad spend:        €{estimated_spend:.2f} (€{DAILY_BUDGET_EUR}/day × {budget_days}d)")

    if estimated_spend > 0:
        roas = google_revenue / estimated_spend
        print(f"  Est. ROAS:            {roas:.2f}x")
    print()

    # Alerts
    alerts = []

    if campaign_days >= 3 and len(google_orders) == 0 and args.days >= 3:
        alerts.append(
            "⚠ ZERO Google Ads orders after 3+ days — check campaign status, "
            "ad approval, and conversion tracking in Google Ads UI"
        )

    if len(google_orders) > 0 and estimated_spend > 0:
        # Rough conversion rate: need click data (not available without API)
        # But we can flag if revenue seems impossibly high relative to spend
        if google_revenue > estimated_spend * 50:
            alerts.append(
                "⚠ Revenue/spend ratio > 50x — verify conversion tracking "
                "is not double-counting (check Goals → Conversions)"
            )

    if len(orders) > 0:
        google_pct = len(google_orders) / len(orders) * 100
        print(f"  Google Ads share:     {google_pct:.1f}% of orders")

    if alerts:
        print(f"  {'─'*50}")
        for alert in alerts:
            print(f"  {alert}")

    print(f"\n{'='*60}")
    print("  Manual checks (Google Ads UI):")
    print("  • Campaign status: ads.google.com → Campaigns → ViaPharma DSA")
    print("  • Actual clicks & CPC: Campaign → Ad group → Keywords")
    print("  • Conversion tracking: Goals → Conversions (only Purchase = Primary)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
