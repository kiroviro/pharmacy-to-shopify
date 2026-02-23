"""
Shared price fetching from benu.bg via JSON-LD.

Used by both price_sync.py and price_monitor.py to avoid duplicating
the HTML fetch + JSON-LD parsing logic.
"""

from __future__ import annotations

import json
import logging

import requests
from bs4 import BeautifulSoup

from .constants import EUR_TO_BGN

logger = logging.getLogger(__name__)


def fetch_benu_price(
    session: requests.Session,
    handle: str,
    timeout: int = 15,
) -> tuple[float | None, float | None, str | None]:
    """
    Fetch live price from benu.bg using JSON-LD structured data.

    Args:
        session: requests.Session to use (for connection reuse)
        handle: Product URL handle (appended to https://benu.bg/)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (price_bgn, price_eur, error).
        On success: (float, float, None).
        On failure: (None, None, error_string).
    """
    url = f"https://benu.bg/{handle}"
    try:
        resp = session.get(url, timeout=timeout)
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
        if e.response is not None and e.response.status_code == 404:
            return None, None, "Product not found (404)"
        status = e.response.status_code if e.response is not None else "unknown"
        return None, None, f"HTTP {status}"
    except Exception as e:
        return None, None, str(e)[:50]
