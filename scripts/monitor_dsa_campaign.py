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
DSA_CAMPAIGN_ID = "23713866882"
DAILY_BUDGET_EUR = 10.0  # reduced from €20 to €10 on 2026-04-04


def load_client() -> ShopifyAPIClient:
    shop, token = load_shopify_credentials()
    return ShopifyAPIClient(shop=shop, access_token=token)


def classify_google_ads_order(order: dict) -> str | None:
    """Classify order as DSA, other Google Ads, or None (organic).

    Returns:
        "dsa" — from DSA campaign (23713866882)
        "google_ads" — from another Google Ads campaign (e.g. old PMax)
        None — organic / not from Google Ads
    """
    landing = order.get("landing_site") or ""
    referrer = order.get("referring_site") or ""
    tags = order.get("tags") or ""
    source = order.get("source_name") or ""

    is_gads = False

    # gclid in landing URL is the strongest signal
    if "gclid" in landing:
        is_gads = True

    # gad_source parameter (Google Ads auto-tagging)
    if "gad_source" in landing:
        is_gads = True

    # Referring site from Google with ads signals
    if "google" in referrer.lower() and ("gclid" in referrer or "ads" in referrer.lower()):
        is_gads = True

    # UTM tags for paid search
    if "utm_source=google" in landing and "utm_medium=cpc" in landing:
        is_gads = True

    # source_name "google" (rare but possible)
    if source == "google":
        is_gads = True

    # Tags-based detection
    if "google_ads" in tags.lower() or "gclid" in tags.lower():
        is_gads = True

    if not is_gads:
        return None

    # Distinguish DSA from other campaigns via gad_campaignid
    if f"gad_campaignid={DSA_CAMPAIGN_ID}" in landing:
        return "dsa"

    return "google_ads"


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

    dsa_orders = []
    other_gads_orders = []
    organic_orders = []

    for o in orders:
        cls = classify_google_ads_order(o)
        if cls == "dsa":
            dsa_orders.append(o)
        elif cls == "google_ads":
            other_gads_orders.append(o)
        else:
            organic_orders.append(o)

    all_gads = dsa_orders + other_gads_orders
    dsa_revenue = compute_revenue(dsa_orders)
    other_gads_revenue = compute_revenue(other_gads_orders)
    organic_revenue = compute_revenue(organic_orders)
    total_revenue = dsa_revenue + other_gads_revenue + organic_revenue

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
    print(f"  ├─ DSA campaign:      {len(dsa_orders)}  (€{dsa_revenue:.2f})")
    if other_gads_orders:
        print(f"  ├─ Other Google Ads:  {len(other_gads_orders)}  (€{other_gads_revenue:.2f})")
    print(f"  └─ Organic/direct:    {len(organic_orders)}  (€{organic_revenue:.2f})")
    print()
    print(f"  Revenue (total):      €{total_revenue:.2f}")
    print(f"  DSA ad spend (est):   €{estimated_spend:.2f} (€{DAILY_BUDGET_EUR}/day × {min(args.days, campaign_days)}d)")

    if estimated_spend > 0 and dsa_revenue > 0:
        roas = dsa_revenue / estimated_spend
        print(f"  DSA ROAS (est):       {roas:.2f}x")
    elif estimated_spend > 0:
        print("  DSA ROAS (est):       0.00x (no DSA orders yet)")
    print()

    if len(orders) > 0:
        gads_pct = len(all_gads) / len(orders) * 100
        print(f"  Google Ads share:     {gads_pct:.1f}% of orders ({len(all_gads)}/{len(orders)})")

    # Alerts
    alerts = []

    if campaign_days >= 3 and len(dsa_orders) == 0 and args.days >= 3:
        alerts.append(
            "⚠ ZERO DSA orders after 3+ days — check campaign status, "
            "ad approval, and conversion tracking in Google Ads UI"
        )

    if campaign_days >= 1 and len(dsa_orders) == 0 and len(all_gads) == 0:
        alerts.append(
            "ℹ No gclid/gad_source in any order landing URLs — "
            "Google Ads auto-tagging may not be enabled, or no ad-driven "
            "purchases yet. Check: Settings → Auto-tagging in Google Ads."
        )

    if len(all_gads) > 0 and estimated_spend > 0:
        gads_revenue = dsa_revenue + other_gads_revenue
        if gads_revenue > estimated_spend * 50:
            alerts.append(
                "⚠ Revenue/spend ratio > 50x — verify conversion tracking "
                "is not double-counting (Goals → Conversions)"
            )

    if alerts:
        print(f"  {'─'*50}")
        for alert in alerts:
            print(f"  {alert}")

    # Order details for debugging
    if all_gads:
        print("\n  Google Ads orders detail:")
        for o in all_gads:
            cls = classify_google_ads_order(o)
            landing = o.get("landing_site") or ""
            print(f"    #{o['order_number']} — €{o['total_price']} ({cls}) landing={landing[:80]}")

    print(f"\n{'='*60}")
    print("  Manual checks (Google Ads UI):")
    print("  • Campaign status: ads.google.com → Campaigns → ViaPharma DSA")
    print("  • Settings → Auto-tagging: must be ON for gclid tracking")
    print("  • Conversion tracking: Goals → Conversions (only Purchase = Primary)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
