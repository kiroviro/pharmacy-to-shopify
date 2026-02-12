"""Tests for src/common/text_utils.py"""

from src.common.text_utils import remove_source_references


class TestRemoveSourceReferences:
    def test_removes_url(self):
        text = "Visit https://pharmacy.example.com/product for details."
        result = remove_source_references(text, "pharmacy.example.com")
        assert "https://pharmacy.example.com" not in result

    def test_removes_domain_mention(self):
        text = "Available at pharmacy.example.com store."
        result = remove_source_references(text, "pharmacy.example.com")
        assert "pharmacy.example.com" not in result

    def test_removes_domain_name_without_tld(self):
        text = "Product by pharmacy online."
        result = remove_source_references(text, "pharmacy.example.com")
        assert "pharmacy" not in result.lower()

    def test_empty_input(self):
        assert remove_source_references("", "pharmacy.example.com") == ""

    def test_none_input(self):
        assert remove_source_references(None, "pharmacy.example.com") is None

    def test_cleans_extra_whitespace(self):
        text = "Buy from  pharmacy.example.com  today."
        result = remove_source_references(text, "pharmacy.example.com")
        assert "  " not in result
