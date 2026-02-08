"""Tests for src/extraction/parsers/html_parser.py"""

import pytest
from bs4 import BeautifulSoup

from src.extraction.parsers.html_parser import HTMLContentParser


def make_parser(html: str) -> HTMLContentParser:
    """Create an HTMLContentParser from an HTML string."""
    soup = BeautifulSoup(html, "lxml")
    return HTMLContentParser(soup, html)


class TestExtractTitle:
    def test_h1_itemprop_name(self):
        parser = make_parser('<html><body><h1 itemprop="name">Product Title</h1></body></html>')
        assert parser.extract_title() == "Product Title"

    def test_plain_h1_fallback(self):
        parser = make_parser("<html><body><h1>Fallback Title</h1></body></html>")
        assert parser.extract_title() == "Fallback Title"

    def test_no_h1_returns_empty(self):
        parser = make_parser("<html><body><p>No heading</p></body></html>")
        assert parser.extract_title() == ""

    def test_whitespace_cleaned(self):
        parser = make_parser("<html><body><h1>  Spaced   Title  </h1></body></html>")
        assert parser.extract_title() == "Spaced Title"


class TestExtractCategories:
    def test_breadcrumb_nav(self):
        html = """
        <html><body>
        <nav class="breadcrumbs">
            <a href="/">Начало</a>
            <a href="/cat1">Category 1</a>
            <a href="/cat2">Category 2</a>
        </nav>
        </body></html>
        """
        parser = make_parser(html)
        categories = parser.extract_categories()
        assert categories == ["Category 1", "Category 2"]

    def test_skips_home(self):
        html = """
        <html><body>
        <nav class="breadcrumbs">
            <a href="/">Home</a>
            <a href="/cat">Category</a>
        </nav>
        </body></html>
        """
        parser = make_parser(html)
        categories = parser.extract_categories()
        assert "Home" not in categories
        assert categories == ["Category"]

    def test_no_breadcrumbs_returns_empty(self):
        parser = make_parser("<html><body><p>No nav</p></body></html>")
        assert parser.extract_categories() == []


class TestExtractWeight:
    def test_weight_from_table(self):
        html = """
        <html><body>
        <table class="additional-attributes">
            <tr><th>Тегло</th><td>500 g</td></tr>
        </table>
        </body></html>
        """
        parser = make_parser(html)
        weight_grams, weight_unit = parser.extract_weight()
        assert weight_grams == 500

    def test_weight_from_text_fallback(self):
        html = "<html><body><h1>Product 250ml Solution</h1></body></html>"
        parser = make_parser(html)
        weight_grams, _ = parser.extract_weight()
        assert weight_grams == 250


class TestConvertToGrams:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.5, "kg", 1500),
        (1.5, "кг", 1500),
        (500, "g", 500),
        (500, "гр", 500),
        (250, "ml", 250),
        (250, "мл", 250),
        (1.5, "l", 1500),
        (1.5, "л", 1500),
        (500, "mg", 1),  # 500mg = 0.5g, max(1, int(0.5)) = 1
        (5000, "mg", 5),
    ])
    def test_unit_conversion(self, value, unit, expected):
        parser = make_parser("<html><body></body></html>")
        result = parser._convert_to_grams(value, unit)
        assert result == expected


class TestExtractBrandFromHtml:
    def test_itemprop_brand(self):
        html = '<html><body><span itemprop="brand">Nivea</span></body></html>'
        parser = make_parser(html)
        assert parser.extract_brand_from_html() == "Nivea"

    def test_no_brand_returns_empty(self):
        parser = make_parser("<html><body><p>No brand</p></body></html>")
        assert parser.extract_brand_from_html() == ""


class TestIsPrescriptionProduct:
    def test_detects_prescription_text(self):
        html = "<html><body><p>Продукти по лекарско предписание</p></body></html>"
        parser = make_parser(html)
        assert parser.is_prescription_product() is True

    def test_non_prescription_product(self):
        html = "<html><body><p>Regular OTC product</p></body></html>"
        parser = make_parser(html)
        assert parser.is_prescription_product() is False


class TestCleanText:
    def test_strips_whitespace(self):
        parser = make_parser("<html><body></body></html>")
        assert parser._clean_text("  hello   world  ") == "hello world"

    def test_empty_returns_empty(self):
        parser = make_parser("<html><body></body></html>")
        assert parser._clean_text("") == ""

    def test_none_returns_empty(self):
        parser = make_parser("<html><body></body></html>")
        assert parser._clean_text(None) == ""
