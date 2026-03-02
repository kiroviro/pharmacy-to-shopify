"""
Shared price fetching via Vue.js component data with JSON-LD fallback.

Used by both price_sync.py and price_monitor.py to avoid duplicating
the HTML fetch + price parsing logic.
"""

from __future__ import annotations

import html as html_module
import json
import logging

import requests
from bs4 import BeautifulSoup

from .constants import EUR_TO_BGN

logger = logging.getLogger(__name__)


def fetch_source_price(
    session: requests.Session,
    handle: str,
    timeout: int = 15,
) -> tuple[float | None, float | None, str | None]:
    """
    Fetch live price from source site.

    Extraction strategy (matches PharmacyParser):
    1. Vue.js ``<add-to-cart :product="...">`` component (most reliable)
    2. JSON-LD ``offers.price`` fallback

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

        # Strategy 1: Vue.js component data (same as PharmacyParser)
        add_to_cart = soup.select_one("add-to-cart")
        if add_to_cart and add_to_cart.get(":product"):
            try:
                product_json = html_module.unescape(add_to_cart.get(":product", "{}"))
                vue_data = json.loads(product_json)
                variants = vue_data.get("variants", [])
                if variants:
                    variant = variants[0]
                    price_eur = float(variant.get("price", 0))
                    if price_eur > 0:
                        price_bgn = round(price_eur * EUR_TO_BGN, 2)
                        return price_bgn, round(price_eur, 2), None
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Strategy 2: JSON-LD fallback
        for script in soup.find_all("script", type="application/ld+json"):
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

        return None, None, "No price found"

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None, None, "Product not found (404)"
        status = e.response.status_code if e.response is not None else "unknown"
        return None, None, f"HTTP {status}"
    except Exception as e:
        return None, None, str(e)[:50]
