"""Tests for src/extraction/parsers/structured_data.py"""

import pytest
from bs4 import BeautifulSoup

from src.extraction.parsers.structured_data import StructuredDataParser


def make_soup_with_jsonld(data_str: str) -> BeautifulSoup:
    """Create a BeautifulSoup with a JSON-LD script tag."""
    html = f'<html><head><script type="application/ld+json">{data_str}</script></head><body></body></html>'
    return BeautifulSoup(html, "lxml")


@pytest.fixture
def parser():
    return StructuredDataParser()


class TestParse:
    def test_parse_product_type(self, parser):
        soup = make_soup_with_jsonld('{"@type": "Product", "name": "Test"}')
        data = parser.parse(soup)
        assert data["@type"] == "Product"

    def test_parse_drug_type(self, parser):
        soup = make_soup_with_jsonld('{"@type": "Drug", "name": "Test Drug"}')
        data = parser.parse(soup)
        assert data["@type"] == "Drug"

    def test_parse_invalid_json(self, parser):
        soup = make_soup_with_jsonld("not valid json{{{")
        data = parser.parse(soup)
        assert data == {}

    def test_parse_no_script(self, parser):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        data = parser.parse(soup)
        assert data == {}

    def test_parse_unsupported_type_ignored(self, parser):
        soup = make_soup_with_jsonld('{"@type": "Organization", "name": "Corp"}')
        data = parser.parse(soup)
        assert data == {}


class TestExtractBrand:
    def test_brand_as_dict(self, parser):
        data = {"brand": {"@type": "Brand", "name": "TestBrand"}}
        assert parser.extract_brand(data) == "TestBrand"

    def test_brand_as_string(self, parser):
        data = {"brand": "SimpleString"}
        assert parser.extract_brand(data) == "SimpleString"

    def test_no_brand(self, parser):
        assert parser.extract_brand({}) == ""

    def test_empty_data(self, parser):
        assert parser.extract_brand(None) == ""


class TestExtractPrice:
    def test_single_offer(self, parser):
        data = {"offers": {"price": "7.71"}}
        assert parser.extract_price(data) == "7.71"

    def test_offers_array(self, parser):
        data = {"offers": [{"price": "12.50"}, {"price": "10.00"}]}
        assert parser.extract_price(data) == "12.50"

    def test_no_offers(self, parser):
        assert parser.extract_price({}) == ""


class TestExtractAvailability:
    def test_in_stock(self, parser):
        data = {"offers": {"availability": "https://schema.org/InStock"}}
        assert parser.extract_availability(data) == "В наличност"

    def test_out_of_stock(self, parser):
        data = {"offers": {"availability": "https://schema.org/OutOfStock"}}
        assert parser.extract_availability(data) == "Няма в наличност"

    def test_http_variant(self, parser):
        data = {"offers": {"availability": "http://schema.org/InStock"}}
        assert parser.extract_availability(data) == "В наличност"

    def test_unknown_availability(self, parser):
        data = {"offers": {"availability": "https://schema.org/Unknown"}}
        assert parser.extract_availability(data) == ""


class TestExtractSku:
    def test_extracts_sku(self, parser):
        data = {"sku": "ABC-123"}
        assert parser.extract_sku(data) == "ABC-123"

    def test_numeric_sku(self, parser):
        data = {"sku": 12345}
        assert parser.extract_sku(data) == "12345"

    def test_no_sku(self, parser):
        assert parser.extract_sku({}) == ""


class TestHasData:
    def test_has_brand(self, parser):
        assert parser.has_data({"brand": "Test"}) is True

    def test_has_offers(self, parser):
        assert parser.has_data({"offers": {"price": "10"}}) is True

    def test_empty_data(self, parser):
        assert parser.has_data({}) is False

    def test_none_data(self, parser):
        assert parser.has_data(None) is False
