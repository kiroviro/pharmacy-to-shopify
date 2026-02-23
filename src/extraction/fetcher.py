"""
PharmacyFetcher — HTTP fetch and HTML loading for pharmacy product pages.

Responsible for:
- Making HTTP GET requests and storing the response HTML
- Parsing HTML into a BeautifulSoup tree
- Extracting the JSON-LD Product structured data block

No product data extraction logic lives here; see parser.py.
"""

from __future__ import annotations

import json
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PharmacyFetcher:
    """Fetches and parses pharmacy product page HTML."""

    def __init__(
        self,
        url: str,
        session: requests.Session | None = None,
    ) -> None:
        self.url = url
        self._session = session
        self.html: str | None = None
        self.soup: BeautifulSoup | None = None
        self.json_ld: dict | None = None

    def fetch(self) -> None:
        """Fetch the product page via HTTP GET."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
        }
        requester = self._session or requests
        response = requester.get(self.url, headers=headers, timeout=30)
        response.raise_for_status()
        self._load(response.text)

    def load_html(self, html: str) -> None:
        """Load pre-fetched HTML without a network request (used in tests)."""
        self._load(html)

    def _load(self, html: str) -> None:
        self.html = html
        self.soup = BeautifulSoup(self.html, "lxml")
        self.json_ld = None
        self._parse_json_ld()

    def _parse_json_ld(self) -> None:
        """Extract the first JSON-LD Product structured data block."""
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    self.json_ld = data
                    return
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            self.json_ld = item
                            return
            except (json.JSONDecodeError, TypeError):
                continue
