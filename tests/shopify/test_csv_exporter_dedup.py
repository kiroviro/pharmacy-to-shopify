"""Tests for csv_exporter append dedup and inventory quantity."""

import csv
import os

import pytest

from src.models import ExtractedProduct, ProductImage
from src.shopify.csv_exporter import ShopifyCSVExporter


@pytest.fixture
def exporter():
    return ShopifyCSVExporter(source_domain="benu.bg")


@pytest.fixture
def product_a():
    return ExtractedProduct(
        title="Product A",
        url="https://benu.bg/product-a",
        brand="Brand",
        sku="A-001",
        price="10.00",
        handle="product-a",
        images=[ProductImage(source_url="https://example.com/a.jpg", position=1, alt_text="A")],
    )


@pytest.fixture
def product_b():
    return ExtractedProduct(
        title="Product B",
        url="https://benu.bg/product-b",
        brand="Brand",
        sku="B-001",
        price="20.00",
        handle="product-b",
        images=[ProductImage(source_url="https://example.com/b.jpg", position=1, alt_text="B")],
    )


class TestAppendDedup:
    def test_append_creates_file(self, exporter, product_a, tmp_path):
        output = str(tmp_path / "out.csv")
        exporter.append_product(product_a, output)
        assert os.path.exists(output)

    def test_append_skips_duplicate_handle(self, exporter, product_a, tmp_path):
        output = str(tmp_path / "out.csv")
        exporter.append_product(product_a, output)
        exporter.append_product(product_a, output)  # Same handle

        with open(output, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # Should only have 1 product row (not duplicated)
        product_rows = [r for r in rows if r["Title"].strip()]
        assert len(product_rows) == 1

    def test_append_allows_different_handles(self, exporter, product_a, product_b, tmp_path):
        output = str(tmp_path / "out.csv")
        exporter.append_product(product_a, output)
        exporter.append_product(product_b, output)

        with open(output, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        product_rows = [r for r in rows if r["Title"].strip()]
        assert len(product_rows) == 2


class TestInventoryQuantity:
    def test_default_inventory_is_11(self, exporter, product_a):
        row = exporter.product_to_main_row(product_a)
        assert row["Inventory quantity"] == 11

    def test_custom_inventory_quantity(self, exporter, product_a):
        product_a.inventory_quantity = 50
        row = exporter.product_to_main_row(product_a)
        assert row["Inventory quantity"] == 50

    def test_zero_inventory_falls_back_to_11(self, exporter, product_a):
        product_a.inventory_quantity = 0
        row = exporter.product_to_main_row(product_a)
        assert row["Inventory quantity"] == 11
