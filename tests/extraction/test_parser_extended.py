"""Extended tests for PharmacyParser: _parse_weight and _extract_tab_content."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from src.extraction.brand_matcher import BrandMatcher
from src.extraction.parser import PharmacyParser

URL = "https://benu.bg/test-product"


def _make_parser(html: str = "<html></html>", url: str = URL) -> PharmacyParser:
    soup = BeautifulSoup(html, "lxml")
    return PharmacyParser(
        soup=soup,
        json_ld=None,
        url=url,
        brand_matcher=BrandMatcher(brands=set()),
    )


# ── _parse_weight ────────────────────────────────────────────────────────────


class TestParseWeightMetric:
    @pytest.mark.parametrize("text, expected", [
        ("100 ml", 100),
        ("100ml", 100),
        ("250 g", 250),
        ("250g", 250),
        ("1.5 kg", 1500),
        ("1.5kg", 1500),
        ("2 kg", 2000),
        ("0.5 kg", 500),
    ])
    def test_standard_units(self, text, expected):
        parser = _make_parser()
        assert parser._parse_weight(text) == expected

    @pytest.mark.parametrize("text, expected", [
        ("500 mg", 1),
        ("100 mg", 1),
        ("1000 mg", 1),
    ])
    def test_milligrams_round_up_to_minimum_1(self, text, expected):
        parser = _make_parser()
        assert parser._parse_weight(text) == expected

    @pytest.mark.parametrize("text, expected", [
        ("1 l", 1000),
        ("0.5 l", 500),
        ("1.5l", 1500),
    ])
    def test_liters(self, text, expected):
        parser = _make_parser()
        assert parser._parse_weight(text) == expected


class TestParseWeightCyrillic:
    @pytest.mark.parametrize("text, expected", [
        ("100мл", 100),
        ("100 мл", 100),
        ("250гр", 250),
        ("250 гр", 250),
        ("1л", 1000),
        ("0.5 л", 500),
    ])
    def test_cyrillic_units(self, text, expected):
        parser = _make_parser()
        assert parser._parse_weight(text) == expected


class TestParseWeightEdgeCases:
    @pytest.mark.parametrize("text, expected", [
        ("", 0),
        ("abc", 0),
        ("no numbers here", 0),
        ("42", 0),  # number without unit
    ])
    def test_no_match_returns_zero(self, text, expected):
        parser = _make_parser()
        assert parser._parse_weight(text) == expected

    def test_decimal_comma_handled(self):
        parser = _make_parser()
        assert parser._parse_weight("1,5 kg") == 1500

    def test_weight_embedded_in_title(self):
        parser = _make_parser()
        assert parser._parse_weight("Витамин C 500mg таблетки") == 1

    def test_first_match_wins(self):
        parser = _make_parser()
        # kg pattern comes before g, so "1.5 kg" should match first
        result = parser._parse_weight("1.5 kg or 1500 g")
        assert result == 1500


# ── _extract_tab_content ─────────────────────────────────────────────────────


class TestExtractTabContent:
    """Test extraction of text between section heading markers."""

    SAMPLE_PAGE = (
        "Какво представлява\n"
        "Това е описание на продукта.\n"
        "Второ изречение.\n"
        "Активни съставки\n"
        "Витамин C 500mg\n"
        "Цинк 10mg\n"
        "Противопоказания\n"
        "Не приемайте при алергия.\n"
        "Допълнителна информация\n"
        "Баркод: 123456\n"
    )

    def test_extracts_first_section(self):
        parser = _make_parser()
        result = parser._extract_tab_content("Какво представлява", self.SAMPLE_PAGE)
        assert "Това е описание на продукта." in result
        assert "Второ изречение." in result
        # Should NOT include the next section's content
        assert "Витамин C 500mg" not in result

    def test_extracts_middle_section(self):
        parser = _make_parser()
        result = parser._extract_tab_content("Активни съставки", self.SAMPLE_PAGE)
        assert "Витамин C 500mg" in result
        assert "Цинк 10mg" in result
        assert "Не приемайте" not in result

    def test_extracts_last_section(self):
        parser = _make_parser()
        result = parser._extract_tab_content("Допълнителна информация", self.SAMPLE_PAGE)
        assert "Баркод: 123456" in result

    def test_section_not_found_returns_empty(self):
        parser = _make_parser()
        result = parser._extract_tab_content("Несъществуваща секция", self.SAMPLE_PAGE)
        assert result == ""

    def test_case_insensitive_lookup(self):
        parser = _make_parser()
        result = parser._extract_tab_content("активни съставки", self.SAMPLE_PAGE)
        assert "Витамин C 500mg" in result

    def test_noise_phrases_are_stripped(self):
        page_text = (
            "Какво представлява\n"
            "Описание на продукта.\n"
            "Попитай магистър-фармацевт за съвет.\n"
            "Активни съставки\n"
        )
        parser = _make_parser()
        result = parser._extract_tab_content("Какво представлява", page_text)
        assert "Описание на продукта." in result
        assert "магистър-фармацевт" not in result

    def test_empty_page_returns_empty(self):
        parser = _make_parser()
        assert parser._extract_tab_content("Какво представлява", "") == ""

    def test_content_truncated_at_1500_chars(self):
        long_content = "A" * 2000
        page_text = f"Какво представлява\n{long_content}\nАктивни съставки\n"
        parser = _make_parser()
        result = parser._extract_tab_content("Какво представлява", page_text)
        assert len(result) <= 1500
