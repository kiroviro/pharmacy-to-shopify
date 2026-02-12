"""Tests for src/models/product.py"""

import pytest

from src.models import ExtractedProduct, ProductImage


class TestProductImage:
    def test_create_with_defaults(self):
        img = ProductImage(source_url="https://example.com/img.jpg", position=1)
        assert img.source_url == "https://example.com/img.jpg"
        assert img.position == 1
        assert img.alt_text == ""

    def test_create_with_alt_text(self):
        img = ProductImage(source_url="https://example.com/img.jpg", position=2, alt_text="Product photo")
        assert img.alt_text == "Product photo"


class TestExtractedProduct:
    def test_create_minimal(self, minimal_product):
        assert minimal_product.title == "Test Product 500mg"
        assert minimal_product.url == "https://pharmacy.example.com/test-product-500mg"
        assert minimal_product.brand == "TestBrand"

    def test_default_values(self, minimal_product):
        assert minimal_product.images == []
        assert minimal_product.tags == []
        assert minimal_product.category_path == []
        assert minimal_product.weight_grams == 0
        assert minimal_product.inventory_policy == "deny"
        assert minimal_product.requires_shipping is True
        assert minimal_product.published is True

    def test_raises_on_empty_title(self):
        with pytest.raises(ValueError, match="title is required"):
            ExtractedProduct(title="", url="https://example.com", brand="X", sku="1", price="10")

    def test_raises_on_empty_url(self):
        with pytest.raises(ValueError, match="URL is required"):
            ExtractedProduct(title="Test", url="", brand="X", sku="1", price="10")

    def test_full_product_fields(self, full_product):
        assert full_product.barcode == "3800123456789"
        assert full_product.price_eur == "6.39"
        assert len(full_product.images) == 2
        assert len(full_product.category_path) == 2
        assert full_product.application_form == "Таблетки"
