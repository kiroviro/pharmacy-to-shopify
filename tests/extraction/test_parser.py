"""
Direct tests for PharmacyParser.

PharmacyParser accepts pre-parsed soup and json_ld — no HTTP required.
These tests construct a parser with known HTML and assert on extracted fields,
validating the extraction logic in isolation from network concerns.
"""

from __future__ import annotations

import json as _json

from bs4 import BeautifulSoup

from src.extraction.brand_matcher import BrandMatcher
from src.extraction.parser import PharmacyParser

URL = "https://benu.bg/testbrand-vitamin-c-500mg-tabletki"

# Sentinel to distinguish "caller passed None explicitly" from "not provided"
_UNSET = object()

# Minimal realistic benu.bg HTML used across most tests
_BASE_HTML = """
<html><body>
<script type="application/ld+json">
{{
  "@type": "Product",
  "name": "{title}",
  "sku": "{sku}",
  "brand": {{"@type": "Brand", "name": "{brand}"}},
  "offers": {{"price": "6.39", "priceCurrency": "EUR"}}
}}
</script>
<add-to-cart :product="{{
    &quot;variants&quot;: [{{
        &quot;price&quot;: 6.39,
        &quot;discountedPrice&quot;: 6.39
    }}]
}}"></add-to-cart>
<div class="tab-group">
<div id="description">Какво представлява
{details}
Активни съставки
Витамин C 500mg
</div>
</div>
<div class="additional-info"><p>Допълнителна информация
Баркод : {barcode}
</p></div>
</body></html>
"""


def _parse_json_ld_from_soup(soup: BeautifulSoup) -> dict | None:
    """Mirror of PharmacyFetcher._parse_json_ld — extracts JSON-LD Product block."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = _json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "Product":
                return data
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        except (ValueError, TypeError):
            continue
    return None


def _make_parser(
    html: str | None = None,
    json_ld: object = _UNSET,
    url: str = URL,
    brand_matcher: BrandMatcher | None = None,
) -> PharmacyParser:
    """
    Build a PharmacyParser from raw HTML.

    When json_ld is not provided, auto-parses it from the soup (mirroring
    PharmacyFetcher behaviour). Pass json_ld=None explicitly to test
    parser behaviour when no JSON-LD is present.
    """
    if html is None:
        html = _BASE_HTML.format(
            title="TestBrand Витамин C таблетки",
            sku="TST-001",
            brand="TestBrand",
            details="Есенциален витамин.",
            barcode="3352710009079",
        )
    soup = BeautifulSoup(html, "lxml")

    resolved_json_ld = _parse_json_ld_from_soup(soup) if json_ld is _UNSET else json_ld

    return PharmacyParser(
        soup=soup,
        json_ld=resolved_json_ld,
        url=url,
        site_domain="benu.bg",
        brand_matcher=brand_matcher or BrandMatcher(brands={"TestBrand"}),
    )


# ── title ────────────────────────────────────────────────────────────────────


class TestExtractTitle:
    def test_extracts_from_json_ld(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(soup=soup, json_ld={"@type": "Product", "name": "JSON-LD Title"}, url=URL)
        assert parser._extract_title() == "JSON-LD Title"

    def test_falls_back_to_h1(self):
        html = "<html><body><h1>H1 Title</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")
        parser = PharmacyParser(soup=soup, json_ld=None, url=URL)
        assert parser._extract_title() == "H1 Title"

    def test_title_is_cached(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(soup=soup, json_ld={"@type": "Product", "name": "Cached Title"}, url=URL)
        first = parser._extract_title()
        second = parser._extract_title()
        assert first is second  # same object (cache hit)


# ── brand ─────────────────────────────────────────────────────────────────────


class TestExtractBrand:
    def test_extracts_brand_from_json_ld_dict(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(
            soup=soup,
            json_ld={"@type": "Product", "name": "X", "brand": {"@type": "Brand", "name": "Solgar"}},
            url=URL,
        )
        assert parser._extract_brand("X") == "Solgar"

    def test_extracts_brand_from_json_ld_string(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(
            soup=soup,
            json_ld={"@type": "Product", "name": "X", "brand": "Vichy"},
            url=URL,
        )
        assert parser._extract_brand("X") == "Vichy"

    def test_falls_back_to_brand_matcher(self):
        bm = BrandMatcher(brands={"TestBrand"})
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(soup=soup, json_ld=None, url=URL, brand_matcher=bm)
        result = parser._extract_brand("TestBrand Продукт")
        assert result == "TestBrand"


# ── price ─────────────────────────────────────────────────────────────────────


class TestExtractPrices:
    def test_vue_price_takes_precedence(self):
        html = """<html><body>
        <add-to-cart :product="{&quot;variants&quot;: [{&quot;price&quot;: 9.99, &quot;discountedPrice&quot;: 9.99}]}">
        </add-to-cart></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        # JSON-LD has 5.00 but Vue has 9.99 — Vue must win
        parser = PharmacyParser(soup=soup, json_ld={"offers": {"price": "5.00"}}, url=URL)
        bgn, eur = parser._extract_prices()
        assert eur == "9.99"

    def test_falls_back_to_json_ld_price(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(soup=soup, json_ld={"offers": {"price": "12.50"}}, url=URL)
        bgn, eur = parser._extract_prices()
        assert eur == "12.50"

    def test_returns_empty_strings_when_no_price(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        parser = PharmacyParser(soup=soup, json_ld=None, url=URL)
        bgn, eur = parser._extract_prices()
        assert bgn == ""
        assert eur == ""


# ── barcode ──────────────────────────────────────────────────────────────────


class TestExtractBarcode:
    def test_extracts_barcode_from_more_info(self):
        parser = _make_parser()
        page_text = parser.soup.get_text(separator="\n")
        barcode = parser._extract_barcode(page_text)
        assert barcode == "3352710009079"

    def test_rejects_invalid_length(self):
        html = _BASE_HTML.format(
            title="X", sku="1", brand="B", details="D", barcode="12345"
        )
        parser = _make_parser(html=html)
        page_text = parser.soup.get_text(separator="\n")
        assert parser._extract_barcode(page_text) == ""


# ── extract() (full pipeline) ─────────────────────────────────────────────────


class TestExtractFull:
    def test_extract_returns_extracted_product(self):
        from src.models.product import ExtractedProduct
        parser = _make_parser()
        product = parser.extract()
        assert isinstance(product, ExtractedProduct)

    def test_extract_populates_title(self):
        parser = _make_parser()
        product = parser.extract()
        assert product.title == "TestBrand Витамин C таблетки"

    def test_extract_populates_price(self):
        parser = _make_parser()
        product = parser.extract()
        # Vue.js sets price to 6.39 EUR
        assert product.price_eur == "6.39"

    def test_extract_sets_handle_from_url_slug(self):
        parser = _make_parser(url="https://benu.bg/my-product-slug")
        product = parser.extract()
        assert product.handle == "my-product-slug"
