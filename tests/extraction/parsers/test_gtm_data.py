"""Tests for src/extraction/parsers/gtm_data.py"""

import pytest

from src.extraction.parsers.gtm_data import GTMDataParser


@pytest.fixture
def parser():
    return GTMDataParser()


@pytest.fixture
def sample_data():
    return {
        "item_name": "Test Product 500mg",
        "item_brand": "TestBrand",
        "item_id": "TST-001",
        "price": 6.39,
        "item_stock_status": "In Stock",
        "item_category": "Витамини и добавки",
    }


class TestParse:
    def test_parse_valid_dl4objects(self, parser, dl4objects_js):
        html = f"<html><body><script>{dl4objects_js}</script></body></html>"
        data = parser.parse(html)
        assert data["item_name"] == "Тест Продукт 500mg таблетки"

    def test_parse_missing_dl4objects(self, parser):
        html = "<html><body><script>var other = 1;</script></body></html>"
        data = parser.parse(html)
        assert data == {}

    def test_parse_malformed_json(self, parser):
        html = '<html><body><script>var dl4Objects = [{bad json}];</script></body></html>'
        data = parser.parse(html)
        assert data == {}

    def test_parse_empty_array(self, parser):
        html = "<html><body><script>var dl4Objects = [];</script></body></html>"
        data = parser.parse(html)
        assert data == {}


class TestExtractTitle:
    def test_extracts_title(self, parser, sample_data):
        assert parser.extract_title(sample_data) == "Test Product 500mg"

    def test_empty_data(self, parser):
        assert parser.extract_title({}) == ""


class TestExtractBrand:
    def test_extracts_brand(self, parser, sample_data):
        assert parser.extract_brand(sample_data) == "TestBrand"

    def test_empty_data(self, parser):
        assert parser.extract_brand({}) == ""


class TestExtractSku:
    def test_extracts_sku(self, parser, sample_data):
        assert parser.extract_sku(sample_data) == "TST-001"

    def test_numeric_id(self, parser):
        assert parser.extract_sku({"item_id": 12345}) == "12345"


class TestExtractPrice:
    def test_extracts_price(self, parser, sample_data):
        assert parser.extract_price(sample_data) == "6.39"

    def test_empty_data(self, parser):
        assert parser.extract_price({}) == ""


class TestExtractStockStatus:
    def test_extracts_status(self, parser, sample_data):
        assert parser.extract_stock_status(sample_data) == "In Stock"


class TestExtractCategory:
    def test_extracts_category(self, parser, sample_data):
        assert parser.extract_category(sample_data) == "Витамини и добавки"


class TestHasData:
    def test_has_name(self, parser):
        assert parser.has_data({"item_name": "Test"}) is True

    def test_empty_data(self, parser):
        assert parser.has_data({}) is False

    def test_none_data(self, parser):
        assert parser.has_data(None) is False
