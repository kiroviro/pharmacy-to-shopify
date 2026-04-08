#!/usr/bin/env python3
"""
Daily DSA campaign report with Gmail email delivery.

Queries Shopify orders, classifies DSA vs organic, computes ROAS,
generates alerts with proposed actions, and emails the report.

Campaign: ViaPharma DSA (ID: 23713866882)
Account: 825-619-0101 (ViaPharma US)
Daily budget: €10, Max CPC: €0.50

Usage:
    python scripts/dsa_daily_report.py                # Email report for last 24h
    python scripts/dsa_daily_report.py --days 7       # Last 7 days
    python scripts/dsa_daily_report.py --no-email     # Print only, skip email
    python scripts/dsa_daily_report.py --force        # Send even if already sent today
    python scripts/dsa_daily_report.py --verbose       # Debug logging

Scheduled via launchd (08:00 local = UTC+3):
    ~/Library/LaunchAgents/com.viapharma.dsa-daily-report.plist
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _lock_path() -> Path:
    return Path(__file__).resolve().parent.parent / "output" / "dsa_report_sent.date"


def _already_sent_today(local_now: datetime) -> bool:
    """Return True if an email was already sent today (local date)."""
    lock = _lock_path()
    if not lock.exists():
        return False
    return lock.read_text().strip() == local_now.strftime("%Y-%m-%d")


def _mark_sent_today(local_now: datetime) -> None:
    lock = _lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(local_now.strftime("%Y-%m-%d"))

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
from src.common.mailer import send_alert
from src.shopify.api_client import ShopifyAPIClient

# UTC+3 (Bulgaria/EEST)
TZ_LOCAL = timezone(timedelta(hours=3))


def build_report(
    days: int,
    orders: list[dict],
    dsa_orders: list[dict],
    other_gads_orders: list[dict],
    organic_orders: list[dict],
    now: datetime,
) -> tuple[str, str, list[str]]:
    """Build the report body, subject line, and alerts.

    Returns:
        (subject, body, alerts)
    """
    campaign_days = (now - CAMPAIGN_START).days
    local_now = now.astimezone(TZ_LOCAL)
    date_str = local_now.strftime("%d %b %Y")

    all_gads = dsa_orders + other_gads_orders
    dsa_revenue = compute_revenue(dsa_orders)
    other_gads_revenue = compute_revenue(other_gads_orders)
    organic_revenue = compute_revenue(organic_orders)
    total_revenue = dsa_revenue + other_gads_revenue + organic_revenue

    estimated_spend = min(days, max(campaign_days, 0)) * DAILY_BUDGET_EUR

    # ROAS
    roas_str = "N/A"
    roas_value = 0.0
    if estimated_spend > 0 and dsa_revenue > 0:
        roas_value = dsa_revenue / estimated_spend
        roas_str = f"{roas_value:.1f}x"
    elif estimated_spend > 0:
        roas_str = "0.0x"

    # Alerts
    alerts = []

    if campaign_days >= 3 and days >= 3 and len(orders) == 0:
        alerts.append(
            "ZERO orders across all channels after 3+ days — check Shopify API "
            "connectivity and store status"
        )
    elif campaign_days >= 3 and len(dsa_orders) == 0 and days >= 3:
        alerts.append(
            "ZERO DSA orders after 3+ days — check campaign status, "
            "ad approval, and conversion tracking in Google Ads UI"
        )

    gclid_alert = check_gclid_health(orders)
    if gclid_alert:
        alerts.append(gclid_alert)

    if len(all_gads) > 0 and estimated_spend > 0:
        gads_revenue = dsa_revenue + other_gads_revenue
        if gads_revenue > estimated_spend * 50:
            alerts.append(
                "Revenue/spend ratio > 50x — verify conversion tracking "
                "is not double-counting (Goals > Conversions)"
            )

    if estimated_spend > 0 and dsa_revenue > 0:
        if roas_value < BREAK_EVEN_ROAS:
            alerts.append(
                f"DSA ROAS {roas_value:.2f}x is below break-even ({BREAK_EVEN_ROAS}x) — "
                f"campaign is currently loss-making at {GROSS_MARGIN*100:.1f}% gross margin"
            )

    if days == 1 and len(orders) == 0:
        alerts.append("ZERO orders in the last 24 hours — site issue?")

    # Alert emoji for subject
    alert_emoji = ""
    if alerts:
        alert_emoji = " !!!"
    elif roas_value >= BREAK_EVEN_ROAS:
        alert_emoji = ""
    elif roas_value > 0:
        alert_emoji = " !"

    # Subject
    subject = (
        f"DSA Report {date_str} — ROAS {roas_str}{alert_emoji} | "
        f"{len(dsa_orders)} DSA orders | EUR {total_revenue:.2f} total"
    )

    # Body
    period = f"last {days} day(s)" if days > 1 else "last 24 hours"
    since = now - timedelta(days=days)

    lines = []
    lines.append(f"ViaPharma DSA Campaign Report — {local_now.strftime('%Y-%m-%d %H:%M')} (UTC+3)")
    lines.append("=" * 65)
    lines.append(f"Period: {period} (since {since.astimezone(TZ_LOCAL).strftime('%Y-%m-%d %H:%M')})")
    lines.append(f"Campaign running: {campaign_days} day(s)")
    lines.append("")
    lines.append(f"Orders (total):       {len(orders)}")
    lines.append(f"  DSA campaign:       {len(dsa_orders)}  (EUR {dsa_revenue:.2f})")
    if other_gads_orders:
        lines.append(f"  Other Google Ads:   {len(other_gads_orders)}  (EUR {other_gads_revenue:.2f})")
    lines.append(f"  Organic/direct:     {len(organic_orders)}  (EUR {organic_revenue:.2f})")
    lines.append("")
    lines.append(f"Revenue (total):      EUR {total_revenue:.2f}")
    lines.append(
        f"DSA ad spend (est):   EUR {estimated_spend:.2f} "
        f"(EUR {DAILY_BUDGET_EUR}/day x {min(days, max(campaign_days, 0))}d)"
    )
    lines.append(
        f"DSA ROAS (est):       {roas_str}  "
        f"(break-even: {BREAK_EVEN_ROAS}x at {GROSS_MARGIN*100:.1f}% margin)"
    )
    lines.append("")

    if len(orders) > 0:
        gads_pct = len(all_gads) / len(orders) * 100
        lines.append(f"Google Ads share:     {gads_pct:.1f}% of orders ({len(all_gads)}/{len(orders)})")
        lines.append("")

    # Alerts section
    if alerts:
        lines.append("-" * 50)
        lines.append("ALERTS:")
        for a in alerts:
            lines.append(f"  ! {a}")
        lines.append("")

    # Order details
    if all_gads:
        lines.append("Google Ads orders detail:")
        for o in all_gads:
            cls = classify_order(o)
            landing = o.get("landing_site") or ""
            lines.append(
                f"  #{o['order_number']} — EUR {o['total_price']} ({cls}) "
                f"landing={landing[:80]}"
            )
        lines.append("")

    # Proposed actions
    lines.append("-" * 50)
    lines.append("PROPOSED ACTIONS:")
    if len(dsa_orders) == 0 and days <= 1:
        lines.append("  - Check DSA campaign status in Google Ads UI")
        lines.append("  - Verify auto-tagging is ON")
        lines.append("  - Review search terms for wasted spend on competitor brands")
    elif roas_value >= BREAK_EVEN_ROAS:
        lines.append("  - ROAS is above break-even. Consider increasing daily budget.")
        lines.append("  - Review search terms weekly for new negative keyword opportunities.")
    elif 0 < roas_value < 1:
        lines.append("  - ROAS below 1x — campaign is losing money.")
        lines.append("  - Review search terms report and add negative keywords urgently.")
        lines.append("  - Consider pausing campaign if ROAS doesn't improve in 2 days.")
    elif 0 < roas_value < BREAK_EVEN_ROAS:
        lines.append(f"  - ROAS {roas_value:.1f}x is below break-even ({BREAK_EVEN_ROAS}x).")
        lines.append("  - Review search terms and add negative keywords.")
        lines.append("  - Consider reducing budget or pausing if trend continues.")
    else:
        lines.append("  - Monitor for another day before taking action.")
        lines.append("  - Review search terms in Google Ads UI.")
    lines.append("")

    lines.append("-" * 50)
    lines.append("Manual checks (Google Ads UI):")
    lines.append("  - Campaign status: ads.google.com > Campaigns > ViaPharma DSA")
    lines.append("  - Auto-tagging: Settings > Auto-tagging (must be ON)")
    lines.append("  - Conversion tracking: Goals > Conversions (only Purchase = Primary)")
    lines.append("=" * 65)

    body = "\n".join(lines)
    return subject, body, alerts


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DSA daily report with email")
    parser.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    parser.add_argument("--no-email", action="store_true", help="Print report only, skip email")
    parser.add_argument("--force", action="store_true", help="Send email even if already sent today")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    local_now = now.astimezone(TZ_LOCAL)
    since = now - timedelta(days=args.days)

    # Fetch orders
    shop, token = load_shopify_credentials()
    client = ShopifyAPIClient(shop=shop, access_token=token)
    orders = fetch_orders(client, since)

    # Classify
    dsa_orders, other_gads_orders, organic_orders = split_orders(orders)

    # Build report
    subject, body, alerts = build_report(
        args.days, orders, dsa_orders, other_gads_orders, organic_orders, now
    )

    # Always print
    print(body)

    # Email — guard against duplicate sends on the same local date
    if not args.no_email:
        if not args.force and _already_sent_today(local_now):
            print(
                f"\nSkipping email — already sent today ({local_now.strftime('%Y-%m-%d')}). "
                "Use --force to override."
            )
            return
        try:
            send_alert(subject=subject, body=body)
            _mark_sent_today(local_now)
            print(f"\nEmail sent at {local_now.strftime('%H:%M')} UTC+3")
        except Exception as e:
            print(f"\nFailed to send email: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
