"""Tests for src/shopify/menus.py"""

import csv
from pathlib import Path

import pytest

from src.shopify.menus import ShopifyMenuCreator


@pytest.fixture
def creator():
    """Create a ShopifyMenuCreator in dry_run mode."""
    return ShopifyMenuCreator(
        shop="test-store",
        access_token="shpat_test",
        dry_run=True,
    )


def _write_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a minimal Shopify-format CSV and return its path.

    All rows must use standard Shopify column names (Title, Tags, Vendor, etc.).
    Rows with an empty Title are treated as image-only continuation rows by
    iter_product_rows and will be skipped.
    """
    if not rows:
        raise ValueError("rows must not be empty")

    fieldnames = list(rows[0].keys())
    csv_path = tmp_path / "products.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


class TestBuildCollectionUrl:
    def test_returns_collections_path(self, creator):
        assert creator.build_collection_url("skincare") == "/collections/skincare"

    def test_handles_hyphenated_handle(self, creator):
        assert creator.build_collection_url("brand-nivea") == "/collections/brand-nivea"


class TestBuildMenuItem:
    def test_returns_correct_keys(self, creator):
        item = creator._build_menu_item("Skincare")
        assert set(item.keys()) == {"title", "url", "type"}

    def test_title_matches_input(self, creator):
        item = creator._build_menu_item("Skincare")
        assert item["title"] == "Skincare"

    def test_type_is_http(self, creator):
        item = creator._build_menu_item("Skincare")
        assert item["type"] == "HTTP"

    def test_url_starts_with_collections(self, creator):
        item = creator._build_menu_item("Skincare")
        assert item["url"].startswith("/collections/")

    def test_handle_prefix_appears_in_url(self, creator):
        item = creator._build_menu_item("Nivea", handle_prefix="brand-")
        assert "/collections/brand-nivea" == item["url"]

    def test_cyrillic_title_transliterated_in_url(self, creator):
        item = creator._build_menu_item("Козметика")
        assert item["title"] == "Козметика"
        assert item["url"] == "/collections/kozmetika"


class TestAnalyzeTagsFromCsv:
    def test_counts_tags_above_min_products(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Tags": "skincare, moisturizer"},
            {"Title": "Product B", "Tags": "skincare, sunscreen"},
            {"Title": "Product C", "Tags": "skincare, moisturizer"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_tags_from_csv(str(csv_path), min_products=2)

        assert result["skincare"] == 3
        assert result["moisturizer"] == 2
        assert "sunscreen" not in result  # only 1 occurrence, below min_products=2

    def test_min_products_default_filters_correctly(self, creator, tmp_path):
        rows = [
            {"Title": f"Product {i}", "Tags": "common, rare"}
            for i in range(3)
        ]
        # "common" appears 3 times, "rare" appears 3 times
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_tags_from_csv(str(csv_path), min_products=3)

        assert result["common"] == 3
        assert result["rare"] == 3

    def test_skips_rows_without_title(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Tags": "tagA"},
            {"Title": "", "Tags": "tagA"},  # image-only row, skipped
            {"Title": "Product B", "Tags": "tagA"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_tags_from_csv(str(csv_path), min_products=1)

        assert result["tagA"] == 2  # not 3

    def test_empty_tags_ignored(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Tags": ""},
            {"Title": "Product B", "Tags": "tagX"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_tags_from_csv(str(csv_path), min_products=1)

        assert result == {"tagX": 1}

    def test_whitespace_in_tags_stripped(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Tags": " skincare , moisturizer "},
            {"Title": "Product B", "Tags": "skincare,moisturizer"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_tags_from_csv(str(csv_path), min_products=1)

        assert result["skincare"] == 2
        assert result["moisturizer"] == 2

    def test_nonexistent_csv_returns_empty(self, creator, tmp_path):
        result = creator.analyze_tags_from_csv(str(tmp_path / "missing.csv"), min_products=1)
        assert result == {}


class TestAnalyzeVendorsFromCsv:
    def test_counts_vendors_above_min_products(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Vendor": "Nivea"},
            {"Title": "Product B", "Vendor": "Nivea"},
            {"Title": "Product C", "Vendor": "Bioderma"},
            {"Title": "Product D", "Vendor": "Nivea"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_vendors_from_csv(str(csv_path), min_products=2)

        assert result["Nivea"] == 3
        assert "Bioderma" not in result  # only 1, below min_products=2

    def test_skips_rows_without_title(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Vendor": "Nivea"},
            {"Title": "", "Vendor": "Nivea"},  # image-only row, skipped
            {"Title": "Product B", "Vendor": "Nivea"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_vendors_from_csv(str(csv_path), min_products=1)

        assert result["Nivea"] == 2

    def test_empty_vendor_ignored(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Vendor": ""},
            {"Title": "Product B", "Vendor": "Roche"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_vendors_from_csv(str(csv_path), min_products=1)

        assert result == {"Roche": 1}

    def test_whitespace_vendor_stripped(self, creator, tmp_path):
        rows = [
            {"Title": "Product A", "Vendor": " Nivea "},
            {"Title": "Product B", "Vendor": "Nivea"},
        ]
        csv_path = _write_csv(tmp_path, rows)

        result = creator.analyze_vendors_from_csv(str(csv_path), min_products=1)

        assert result["Nivea"] == 2

    def test_nonexistent_csv_returns_empty(self, creator, tmp_path):
        result = creator.analyze_vendors_from_csv(str(tmp_path / "missing.csv"), min_products=1)
        assert result == {}
