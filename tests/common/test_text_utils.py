"""Tests for src/common/text_utils.py"""

from src.common.text_utils import remove_source_references


class TestRemoveSourceReferences:
    def test_removes_url(self):
        text = "Visit https://benu.bg/product for details."
        result = remove_source_references(text, "benu.bg")
        assert "https://benu.bg" not in result

    def test_removes_domain_mention(self):
        text = "Available at benu.bg store."
        result = remove_source_references(text, "benu.bg")
        assert "benu.bg" not in result

    def test_removes_domain_name_without_tld(self):
        text = "Product by benu pharmacy."
        result = remove_source_references(text, "benu.bg")
        assert "benu" not in result.lower()

    def test_empty_input(self):
        assert remove_source_references("", "benu.bg") == ""

    def test_none_input(self):
        assert remove_source_references(None, "benu.bg") is None

    def test_cleans_extra_whitespace(self):
        text = "Buy from  benu.bg  today."
        result = remove_source_references(text, "benu.bg")
        assert "  " not in result
