"""
Pharmacy Product Extractor

Thin wrapper combining PharmacyFetcher (HTTP/HTML) and PharmacyParser
(data extraction). All callers that use fetch(), load_html(), and extract()
continue to work unchanged.

For new code, prefer constructing PharmacyParser directly with pre-parsed
soup/json_ld — it avoids the HTTP dependency and is easier to test.
"""

from __future__ import annotations

import requests

from ..models import ExtractedProduct
from .fetcher import PharmacyFetcher
from .parser import PharmacyParser

BENU_DOMAIN = "benu.bg"


class PharmacyExtractor:
    """Fetches pharmacy product pages and extracts structured product data."""

    def __init__(
        self,
        url: str,
        site_domain: str = BENU_DOMAIN,
        validate_images: bool = False,
        session: requests.Session | None = None,
    ):
        self.url = url
        self.site_domain = site_domain
        self.validate_images = validate_images
        self._fetcher = PharmacyFetcher(url=url, session=session)
        self._parser: PharmacyParser | None = None

    # ── Public properties (backward-compatible with old monolith API) ─────────

    @property
    def html(self) -> str | None:
        return self._fetcher.html

    @property
    def soup(self):
        return self._fetcher.soup

    @property
    def json_ld(self) -> dict | None:
        return self._fetcher.json_ld

    @property
    def vue_data(self) -> dict | None:
        return self._parser.vue_data if self._parser else None

    @property
    def brand_matcher(self):
        return self._parser.brand_matcher if self._parser else None

    # ── Core operations ───────────────────────────────────────────────────────

    def fetch(self) -> None:
        """Fetch the product page HTML and initialise the parser."""
        self._fetcher.fetch()
        self._init_parser()

    def load_html(self, html: str) -> None:
        """Load pre-fetched HTML for extraction without a network request."""
        self._fetcher.load_html(html)
        self._init_parser()

    def extract(self) -> ExtractedProduct:
        """Extract all product data. Requires fetch() or load_html() first."""
        if self._parser is None:
            raise RuntimeError("Call fetch() or load_html() before extract()")
        return self._parser.extract()

    # ── Private method proxies (backward-compatible with existing tests) ───────
    # These delegate to PharmacyParser so tests that call extractor._extract_*()
    # continue to work without modification.

    def _extract_barcode(self, page_text: str = "") -> str:
        return self._parser._extract_barcode(page_text)

    def _extract_prices(self) -> tuple[str, str]:
        return self._parser._extract_prices()

    def _parse_vue_product_data(self) -> dict | None:
        return self._parser._parse_vue_product_data()

    def _extract_title(self) -> str:
        return self._parser._extract_title()

    def _extract_brand(self, title: str) -> str:
        return self._parser._extract_brand(title)

    def _extract_categories(self, product_title: str = "") -> list[str]:
        return self._parser._extract_categories(product_title)

    def _generate_handle(self, title: str) -> str:
        return self._parser._generate_handle(title)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _init_parser(self) -> None:
        self._parser = PharmacyParser(
            soup=self._fetcher.soup,
            json_ld=self._fetcher.json_ld,
            url=self.url,
            site_domain=self.site_domain,
            validate_images=self.validate_images,
        )
