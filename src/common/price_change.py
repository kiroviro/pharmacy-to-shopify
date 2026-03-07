"""
Shared PriceChange dataclass used by price monitoring and sync scripts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriceChange:
    """A detected price difference between source site and Shopify store."""

    handle: str
    title: str
    old_bgn: float
    new_bgn: float
    change_pct: float
    source: str = "source"  # "source" (source raised) or "drift" (store drifted low)
    old_eur: float | None = None
    new_eur: float | None = None
    source_url: str = ""
    shopify_url: str = ""
