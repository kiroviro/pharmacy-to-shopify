"""Tests for src/common/price_fetcher.py"""

import json
from unittest.mock import MagicMock

import pytest
import requests

from src.common.constants import EUR_TO_BGN
from src.common.price_fetcher import fetch_source_price


def _make_session(html: str = "", status: int = 200) -> MagicMock:
    """Return a mock Session whose .get() returns a response with given HTML."""
    session = MagicMock(spec=requests.Session)
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    session.get.return_value = resp
    return session


def _product_html(price: str = "12.99", offers_as_list: bool = False) -> str:
    """Minimal HTML page with a JSON-LD Product schema."""
    if offers_as_list:
        offers = [{"price": price, "priceCurrency": "EUR"}]
    else:
        offers = {"price": price, "priceCurrency": "EUR"}
    ld = json.dumps({"@type": "Product", "name": "Test", "offers": offers})
    return f'<html><head><script type="application/ld+json">{ld}</script></head></html>'


# ── Happy path ───────────────────────────────────────────────────────────────


def _vue_html(price: float = 12.99) -> str:
    """Minimal HTML page with Vue.js <add-to-cart> component."""
    vue_json = json.dumps({"variants": [{"price": price, "discountedPrice": price}]})
    escaped = vue_json.replace('"', "&quot;")
    return f'<html><body><add-to-cart :product="{escaped}"></add-to-cart></body></html>'


class TestFetchSourcePrice:
    def test_vue_price_preferred_over_json_ld(self):
        """Vue.js component price takes precedence over JSON-LD."""
        ld = json.dumps({"@type": "Product", "offers": {"price": "5.00"}})
        vue_json = json.dumps({"variants": [{"price": 9.99, "discountedPrice": 9.99}]})
        escaped = vue_json.replace('"', "&quot;")
        html = (
            f'<html><head><script type="application/ld+json">{ld}</script></head>'
            f'<body><add-to-cart :product="{escaped}"></add-to-cart></body></html>'
        )
        session = _make_session(html)
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(9.99, abs=0.01)

    def test_vue_price_extraction(self):
        """Price from Vue.js component data is extracted correctly."""
        session = _make_session(_vue_html(7.50))
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(7.50, abs=0.01)
        assert bgn == pytest.approx(7.50 * EUR_TO_BGN, abs=0.01)

    def test_successful_price_from_json_ld(self):
        session = _make_session(_product_html("12.99"))
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(12.99, abs=0.01)
        assert bgn == pytest.approx(12.99 * EUR_TO_BGN, abs=0.01)

    def test_price_with_list_offers(self):
        """When `offers` is a list, the first item is used."""
        session = _make_session(_product_html("9.50", offers_as_list=True))
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(9.50, abs=0.01)

    def test_price_eur_to_bgn_conversion(self):
        """BGN is EUR × EUR_TO_BGN (1.95583), rounded to 2 decimals."""
        session = _make_session(_product_html("10.00"))
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert bgn == round(10.00 * EUR_TO_BGN, 2)

    def test_comma_decimal_price(self):
        """Price '19,99' (comma separator) is parsed as 19.99."""
        session = _make_session(_product_html("19,99"))
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(19.99, abs=0.01)

    def test_multiple_json_ld_scripts_picks_product(self):
        """When multiple JSON-LD blocks exist, the Product block is used."""
        breadcrumb = json.dumps({"@type": "BreadcrumbList", "itemListElement": []})
        product = json.dumps({"@type": "Product", "offers": {"price": "5.00"}})
        html = (
            f'<script type="application/ld+json">{breadcrumb}</script>'
            f'<script type="application/ld+json">{product}</script>'
        )
        session = _make_session(html)
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert err is None
        assert eur == pytest.approx(5.00, abs=0.01)


# ── Error paths ──────────────────────────────────────────────────────────────


class TestFetchSourcePriceErrors:
    def test_404_returns_not_found_error(self):
        session = _make_session("", status=404)
        bgn, eur, err = fetch_source_price(session, "nonexistent")

        assert bgn is None
        assert eur is None
        assert "404" in err

    def test_http_500_returns_error(self):
        session = _make_session("", status=500)
        bgn, eur, err = fetch_source_price(session, "broken-product")

        assert bgn is None
        assert err is not None

    def test_network_error_returns_error(self):
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.ConnectionError("Network down")

        bgn, eur, err = fetch_source_price(session, "test-product")

        assert bgn is None
        assert err is not None

    def test_no_json_ld_returns_error(self):
        session = _make_session("<html><body>No JSON-LD here</body></html>")
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert bgn is None
        assert "No price" in err

    def test_json_ld_not_product_type_returns_error(self):
        """Non-Product JSON-LD (e.g. BreadcrumbList) is skipped."""
        ld = json.dumps({"@type": "BreadcrumbList", "itemListElement": []})
        html = f'<script type="application/ld+json">{ld}</script>'
        session = _make_session(html)
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert bgn is None
        assert err is not None

    def test_product_without_price_in_offers_returns_error(self):
        """Product schema with empty offers returns no-price error."""
        ld = json.dumps({"@type": "Product", "offers": {}})
        html = f'<script type="application/ld+json">{ld}</script>'
        session = _make_session(html)
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert bgn is None
        assert err is not None

    def test_malformed_json_in_script_is_skipped(self):
        """Invalid JSON in script tag is silently skipped."""
        html = '<script type="application/ld+json">NOT VALID JSON {</script>'
        session = _make_session(html)
        bgn, eur, err = fetch_source_price(session, "test-product")

        assert bgn is None
        assert err is not None
