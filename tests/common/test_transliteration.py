"""Tests for src/common/transliteration.py"""

from src.common.transliteration import generate_handle, transliterate


class TestTransliterate:
    def test_cyrillic_to_latin(self):
        assert transliterate("Козметика") == "Kozmetika"

    def test_mixed_text(self):
        result = transliterate("Hello Свят")
        assert result == "Hello Svyat"

    def test_latin_passthrough(self):
        assert transliterate("Hello World") == "Hello World"

    def test_special_chars_preserved(self):
        result = transliterate("Тест-123!")
        assert result == "Test-123!"

    def test_empty_string(self):
        assert transliterate("") == ""


class TestGenerateHandle:
    def test_basic_handle(self):
        handle = generate_handle("Козметика за лице")
        assert handle == "kozmetika-za-litse"

    def test_handle_with_prefix(self):
        handle = generate_handle("Nivea", prefix="brand-")
        assert handle == "brand-nivea"

    def test_consecutive_hyphens_collapsed(self):
        handle = generate_handle("Test  --  Product")
        assert "--" not in handle

    def test_special_chars_removed(self):
        handle = generate_handle("Test! @Product# $100")
        assert handle == "test-product-100"

    def test_leading_trailing_hyphens_stripped(self):
        handle = generate_handle(" -Test Product- ")
        assert not handle.startswith("-")
        assert not handle.endswith("-")

    def test_empty_string(self):
        handle = generate_handle("")
        assert handle == ""

    def test_numbers_preserved(self):
        handle = generate_handle("Vitamin C 500mg")
        assert "500mg" in handle
