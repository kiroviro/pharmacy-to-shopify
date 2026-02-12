"""Tests for src/shopify/csv_exporter.py"""

import csv
import os

import pytest

from src.models import ProductImage
from src.shopify.csv_exporter import SHOPIFY_FIELDNAMES, ShopifyCSVExporter


@pytest.fixture
def exporter():
    return ShopifyCSVExporter(source_domain="pharmacy.example.com")


class TestShopifyFieldnames:
    def test_fieldnames_count(self):
        # Shopify template has 56 columns (official format)
        assert len(SHOPIFY_FIELDNAMES) == 56

    def test_essential_fields_present(self):
        assert "Title" in SHOPIFY_FIELDNAMES
        assert "URL handle" in SHOPIFY_FIELDNAMES
        assert "SKU" in SHOPIFY_FIELDNAMES
        assert "Price" in SHOPIFY_FIELDNAMES
        assert "Vendor" in SHOPIFY_FIELDNAMES


class TestProductToMainRow:
    def test_returns_correct_keys(self, exporter, full_product):
        row = exporter.product_to_main_row(full_product)
        assert len(row) == len(SHOPIFY_FIELDNAMES)
        for key in SHOPIFY_FIELDNAMES:
            assert key in row

    def test_core_values(self, exporter, full_product):
        row = exporter.product_to_main_row(full_product)
        assert row["Title"] == full_product.title
        assert row["Vendor"] == full_product.brand
        assert row["SKU"] == full_product.sku
        assert row["Price"] == full_product.price

    def test_prescription_product_is_draft(self, exporter, minimal_product):
        minimal_product.availability = "Само с рецепта"
        row = exporter.product_to_main_row(minimal_product)
        assert row["Status"] == "Draft"

    def test_non_prescription_is_active(self, exporter, full_product):
        row = exporter.product_to_main_row(full_product)
        assert row["Status"] == "Active"


class TestImageToRow:
    def test_image_row_has_handle(self, exporter):
        img = ProductImage(source_url="https://example.com/img.jpg", position=2, alt_text="Alt")
        row = exporter.image_to_row("test-handle", img)
        assert row["URL handle"] == "test-handle"
        assert row["Product image URL"] == "https://example.com/img.jpg"
        assert row["Image position"] == "2"
        assert row["Title"] == ""


class TestProductToRows:
    def test_single_image_product(self, exporter, minimal_product):
        minimal_product.images = [
            ProductImage(source_url="https://example.com/img.jpg", position=1, alt_text="Alt")
        ]
        rows = exporter.product_to_rows(minimal_product)
        assert len(rows) == 1  # Only main row, no additional images

    def test_multi_image_product(self, exporter, full_product):
        rows = exporter.product_to_rows(full_product)
        assert len(rows) == 2  # 1 main + 1 additional image


class TestExportSingle:
    def test_creates_valid_csv(self, exporter, full_product, tmp_path):
        output_path = str(tmp_path / "test.csv")
        exporter.export_single(full_product, output_path)

        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) >= 1
        assert rows[0]["Title"] == full_product.title


class TestExportMultiple:
    def test_returns_correct_row_count(self, exporter, full_product, minimal_product, tmp_path):
        output_path = str(tmp_path / "multi.csv")
        row_count = exporter.export_multiple([full_product, minimal_product], output_path)
        # full_product has 2 images (2 rows), minimal has 0 images (1 row)
        assert row_count == 3
