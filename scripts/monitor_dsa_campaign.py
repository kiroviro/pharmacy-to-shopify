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
    python scripts/monitor_dsa_campaign.py --email     # Send alert email
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.common.credentials import load_shopify_credentials
from src.common.dsa_utils import (
    BREAK_EVEN_ROAS,
    CAMPAIGN_START,
    DAILY_BUDGET_EUR,
    GROSS_MARGIN,
    check_gclid_health,
    classify_order,
    compute_revenue,
    fetch_orders,
    split_orders,
)
from src.shopify.api_client import ShopifyAPIClient

# Backward-compat alias
classify_google_ads_order = classify_order


def load_client() -> ShopifyAPIClient:
    shop, token = load_shopify_credentials()
    return ShopifyAPIClient(shop=shop, access_token=token)


def build_report(args_days: int) -> tuple[str, list[str]]:
    """Build the monitor report. Returns (report_text, alerts)."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args_days)
    campaign_days = (now - CAMPAIGN_START).days

    client = load_client()
    orders = fetch_orders(client, since)

    dsa_orders, other_gads_orders, organic_orders = split_orders(orders)

    all_gads = dsa_orders + other_gads_orders
    dsa_revenue = compute_revenue(dsa_orders)
    other_gads_revenue = compute_revenue(other_gads_orders)
    organic_revenue = compute_revenue(organic_orders)
    total_revenue = dsa_revenue + other_gads_revenue + organic_revenue

    estimated_spend = min(args_days, campaign_days) * DAILY_BUDGET_EUR

    lines = []

    period = f"last {args_days} day(s)" if args_days > 1 else "last 24 hours"
    lines.append(f"\n{'='*60}")
    lines.append(f"  ViaPharma DSA Campaign Monitor — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"{'='*60}")
    lines.append(f"  Period: {period} (since {since.strftime('%Y-%m-%d %H:%M')})")
    lines.append(f"  Campaign running: {campaign_days} day(s)")
    lines.append("")
    lines.append(f"  Orders (total):       {len(orders)}")
    lines.append(f"  ├─ DSA campaign:      {len(dsa_orders)}  (€{dsa_revenue:.2f})")
    if other_gads_orders:
        lines.append(f"  ├─ Other Google Ads:  {len(other_gads_orders)}  (€{other_gads_revenue:.2f})")
    lines.append(f"  └─ Organic/direct:    {len(organic_orders)}  (€{organic_revenue:.2f})")
    lines.append("")
    lines.append(f"  Revenue (total):      €{total_revenue:.2f}")
    lines.append(
        f"  DSA ad spend (est):   €{estimated_spend:.2f} "
        f"(€{DAILY_BUDGET_EUR}/day × {min(args_days, campaign_days)}d)"
    )

    if estimated_spend > 0 and dsa_revenue > 0:
        roas = dsa_revenue / estimated_spend
        lines.append(f"  DSA ROAS (est):       {roas:.2f}x  (break-even: {BREAK_EVEN_ROAS}x at {GROSS_MARGIN*100:.1f}% margin)")
    elif estimated_spend > 0:
        lines.append(
            f"  DSA ROAS (est):       0.00x  (break-even: {BREAK_EVEN_ROAS}x at {GROSS_MARGIN*100:.1f}% margin)"
        )
    lines.append("")

    if len(orders) > 0:
        gads_pct = len(all_gads) / len(orders) * 100
        lines.append(f"  Google Ads share:     {gads_pct:.1f}% of orders ({len(all_gads)}/{len(orders)})")

    # --- Alerts ---
    alerts = []

    if campaign_days >= 3 and args_days >= 3 and len(orders) == 0:
        alerts.append(
            "⚠ ZERO orders across all channels after 3+ days — check Shopify API "
            "connectivity and store status"
        )
    elif campaign_days >= 3 and args_days >= 3 and len(dsa_orders) == 0:
        alerts.append(
            "⚠ ZERO DSA orders after 3+ days — check campaign status, "
            "ad approval, and conversion tracking in Google Ads UI"
        )

    gclid_alert = check_gclid_health(orders)
    if gclid_alert:
        alerts.append(gclid_alert)

    if len(all_gads) > 0 and estimated_spend > 0:
        gads_revenue = dsa_revenue + other_gads_revenue
        if gads_revenue > estimated_spend * 50:
            alerts.append(
                "⚠ Revenue/spend ratio > 50x — verify conversion tracking "
                "is not double-counting (Goals → Conversions)"
            )

    if estimated_spend > 0 and dsa_revenue > 0:
        roas = dsa_revenue / estimated_spend
        if roas < BREAK_EVEN_ROAS:
            alerts.append(
                f"⚠ DSA ROAS {roas:.2f}x is below break-even ({BREAK_EVEN_ROAS}x) — "
                f"campaign is currently loss-making at {GROSS_MARGIN*100:.1f}% gross margin"
            )

    if alerts:
        lines.append(f"  {'─'*50}")
        for alert in alerts:
            lines.append(f"  {alert}")

    # Order details for debugging
    if all_gads:
        lines.append("\n  Google Ads orders detail:")
        for o in all_gads:
            cls = classify_order(o)
            landing = o.get("landing_site") or ""
            lines.append(
                f"    #{o['order_number']} — €{o['total_price']} ({cls}) landing={landing[:80]}"
            )

    lines.append(f"\n{'='*60}")
    lines.append("  Manual checks (Google Ads UI):")
    lines.append("  • Campaign status: ads.google.com → Campaigns → ViaPharma DSA")
    lines.append("  • Settings → Auto-tagging: must be ON for gclid tracking")
    lines.append("  • Conversion tracking: Goals → Conversions (only Purchase = Primary)")
    lines.append(f"{'='*60}\n")

    return "\n".join(lines), alerts


def main():
    parser = argparse.ArgumentParser(description="Monitor ViaPharma DSA campaign")
    parser.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    parser.add_argument("--email", action="store_true", help="Send alert email via Gmail")
    args = parser.parse_args()

    report, alerts = build_report(args.days)
    print(report)

    if args.email:
        from src.common.mailer import send_alert

        subject = "ViaPharma DSA Monitor"
        if alerts:
            subject += f" — {len(alerts)} alert(s)"
        send_alert(subject=subject, body=report)
        print("  ✓ Alert email sent.")


if __name__ == "__main__":
    main()
