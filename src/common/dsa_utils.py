"""
Shared utilities for DSA campaign monitoring and reporting.

Provides order classification (DSA vs other Google Ads vs organic),
order fetching, and revenue computation used by both the interactive
monitor and the daily email report.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.shopify.api_client import ShopifyAPIClient

CAMPAIGN_START = datetime(2026, 4, 3, tzinfo=timezone.utc)
DSA_CAMPAIGN_ID = "23713866882"
DAILY_BUDGET_EUR = 10.0  # reduced from €20 to €10 on 2026-04-04

# ViaPharma blended gross margin: ~5.3% (confirmed 2026-04-05)
GROSS_MARGIN = 0.053
BREAK_EVEN_ROAS = round(1 / GROSS_MARGIN, 2)  # ≈18.87x


def classify_order(order: dict) -> str | None:
    """Classify order as DSA, other Google Ads, or organic.

    Returns:
        "dsa" — from DSA campaign (23713866882)
        "google_ads" — from another Google Ads campaign
        None — organic / not from Google Ads
    """
    landing = order.get("landing_site") or ""
    referrer = order.get("referring_site") or ""
    tags = order.get("tags") or ""
    source = order.get("source_name") or ""
    source_identifier = order.get("source_identifier") or ""

    is_gads = False

    if "gclid" in landing:
        is_gads = True
    if "gad_source" in landing:
        is_gads = True
    if "google" in referrer.lower() and ("gclid" in referrer or "ads" in referrer.lower()):
        is_gads = True
    if "utm_source=google" in landing and "utm_medium=cpc" in landing:
        is_gads = True
    if source == "google":
        is_gads = True
    if source_identifier == "google":
        is_gads = True
    if "google_ads" in tags.lower() or "gclid" in tags.lower():
        is_gads = True

    if not is_gads:
        return None

    if f"gad_campaignid={DSA_CAMPAIGN_ID}" in landing:
        return "dsa"

    return "google_ads"


def check_gclid_health(orders: list[dict]) -> str | None:
    """Return an alert string if Google-referred orders lack gclid auto-tagging.

    Only fires when there are actual Google-referred orders (by referrer) that
    do NOT have gclid/gad_source in their landing URL — indicating auto-tagging
    is off. Returns None when there are no Google-referred orders at all.
    """
    google_referred = [
        o for o in orders
        if "google" in (o.get("referring_site") or "").lower()
    ]
    if not google_referred:
        return None

    missing_gclid = [
        o for o in google_referred
        if "gclid" not in (o.get("landing_site") or "")
        and "gad_source" not in (o.get("landing_site") or "")
    ]
    if not missing_gclid:
        return None

    return (
        f"ℹ {len(missing_gclid)}/{len(google_referred)} Google-referred orders lack gclid "
        "in landing URL — auto-tagging may be disabled. "
        "Check: Google Ads → Settings → Auto-tagging."
    )


def fetch_orders(client: ShopifyAPIClient, since: datetime) -> list[dict]:
    """Fetch all orders since the given datetime."""
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%S%z")
    return client.paginate_rest(
        f"orders.json?status=any&created_at_min={since_iso}", "orders"
    )


def compute_revenue(orders: list[dict]) -> float:
    """Sum total_price across orders (EUR)."""
    return sum(float(o.get("total_price", 0)) for o in orders)


def split_orders(orders: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Split orders into (dsa, other_gads, organic) lists."""
    dsa, other_gads, organic = [], [], []
    for o in orders:
        cls = classify_order(o)
        if cls == "dsa":
            dsa.append(o)
        elif cls == "google_ads":
            other_gads.append(o)
        else:
            organic.append(o)
    return dsa, other_gads, organic
