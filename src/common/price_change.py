"""
Shared PriceChange dataclass used by price monitoring and sync scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PriceChange:
    """A detected price difference between benu.bg and viapharma.us."""

    handle: str
    title: str
    old_bgn: float
    new_bgn: float
    change_pct: float
    source: str = "benu"  # "benu" (benu raised) or "drift" (store drifted low)
    old_eur: float | None = None
    new_eur: float | None = None
    benu_url: str = ""
    shopify_url: str = ""
