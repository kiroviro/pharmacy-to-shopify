"""Tests for src/extraction/brand_matcher.py"""

import pytest

from src.extraction.brand_matcher import BrandMatcher


@pytest.fixture
def matcher(sample_known_brands):
    """Create a BrandMatcher with test brands (no config I/O)."""
    return BrandMatcher(brands=sample_known_brands)


class TestMatch:
    def test_structured_brand_priority(self, matcher):
        result = matcher.match(
            title="Nivea Creme 150ml",
            structured_brand="StructuredBrand",
            gtm_brand="GTMBrand",
        )
        assert result == "StructuredBrand"

    def test_gtm_brand_second_priority(self, matcher):
        result = matcher.match(
            title="Nivea Creme 150ml",
            structured_brand="",
            gtm_brand="GTMBrand",
        )
        assert result == "GTMBrand"

    def test_title_fallback(self, matcher):
        result = matcher.match(
            title="Nivea Creme 150ml",
            structured_brand="",
            gtm_brand="",
        )
        assert result == "Nivea"

    def test_no_match(self, matcher):
        result = matcher.match(
            title="Unknown Product 100ml",
            structured_brand="",
            gtm_brand="",
        )
        assert result == ""


class TestMatchFromTitle:
    def test_single_word_brand(self, matcher):
        assert matcher.match_from_title("Nivea Creme 150ml") == "Nivea"

    def test_multi_word_brand(self, matcher):
        assert matcher.match_from_title("La Roche-Posay Effaclar Gel 200ml") == "La Roche-Posay"

    def test_no_match(self, matcher):
        assert matcher.match_from_title("UnknownBrand Product 100ml") == ""

    def test_empty_title(self, matcher):
        assert matcher.match_from_title("") == ""

    def test_case_insensitive(self, matcher):
        assert matcher.match_from_title("nivea Creme 150ml") == "Nivea"


class TestIsKnownBrand:
    def test_known_brand(self, matcher):
        assert matcher.is_known_brand("Nivea") is True

    def test_case_insensitive(self, matcher):
        assert matcher.is_known_brand("nivea") is True

    def test_unknown_brand(self, matcher):
        assert matcher.is_known_brand("FakeBrand") is False


class TestGetCanonicalName:
    def test_returns_canonical(self, matcher):
        assert matcher.get_canonical_name("abopharma") == "AboPharma"

    def test_unknown_returns_original(self, matcher):
        assert matcher.get_canonical_name("unknown") == "unknown"


class TestBrandCount:
    def test_brand_count(self, matcher, sample_known_brands):
        assert matcher.brand_count == len(sample_known_brands)
