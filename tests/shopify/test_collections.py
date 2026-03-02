"""Tests for src/shopify/collections.py"""

import csv

import pytest

from src.shopify.collections import ShopifyCollectionCreator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SHOPIFY_CSV_COLUMNS = ["Title", "Tags", "Vendor", "SKU", "Price"]


def _write_csv(path, rows: list[dict]) -> str:
    """Write a minimal Shopify CSV to *path* and return its string path.

    Each dict in *rows* may contain any subset of SHOPIFY_CSV_COLUMNS;
    missing keys default to "".
    """
    filepath = path / "products.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHOPIFY_CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in SHOPIFY_CSV_COLUMNS})
    return str(filepath)


def _creator(dry_run: bool = True) -> ShopifyCollectionCreator:
    """Return a dry-run creator that never touches a real Shopify store."""
    return ShopifyCollectionCreator(
        shop="test-store",
        access_token="shpat_fake",
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# _count_tags
# ---------------------------------------------------------------------------

class TestCountTags:
    def test_counts_individual_tags(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Tags": "vitamins, supplements"},
            {"Title": "Product B", "Tags": "vitamins"},
            {"Title": "Product C", "Tags": "skincare"},
        ])
        creator = _creator()
        counts = creator._count_tags(csv_path)

        assert counts["vitamins"] == 2
        assert counts["supplements"] == 1
        assert counts["skincare"] == 1

    def test_skips_rows_without_title(self, tmp_path):
        """iter_product_rows filters out rows with empty Title."""
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Tags": "vitamins"},
            {"Title": "", "Tags": "vitamins"},  # image-only continuation row
            {"Title": "Product B", "Tags": "vitamins"},
        ])
        creator = _creator()
        counts = creator._count_tags(csv_path)

        assert counts["vitamins"] == 2

    def test_empty_tags_ignored(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Tags": ""},
            {"Title": "Product B", "Tags": "vitamins"},
        ])
        creator = _creator()
        counts = creator._count_tags(csv_path)

        assert counts["vitamins"] == 1
        assert len(counts) == 1

    def test_whitespace_in_tags_stripped(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Tags": "  vitamins , supplements  "},
        ])
        creator = _creator()
        counts = creator._count_tags(csv_path)

        assert counts["vitamins"] == 1
        assert counts["supplements"] == 1

    def test_empty_csv_returns_empty_counter(self, tmp_path):
        csv_path = _write_csv(tmp_path, [])
        creator = _creator()
        counts = creator._count_tags(csv_path)

        assert len(counts) == 0

    def test_nonexistent_file_returns_empty_counter(self, tmp_path):
        creator = _creator()
        counts = creator._count_tags(str(tmp_path / "does_not_exist.csv"))

        assert len(counts) == 0


# ---------------------------------------------------------------------------
# _count_vendors
# ---------------------------------------------------------------------------

class TestCountVendors:
    def test_counts_vendors(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Vendor": "Nivea"},
            {"Title": "Product B", "Vendor": "Nivea"},
            {"Title": "Product C", "Vendor": "Bioderma"},
        ])
        creator = _creator()
        counts = creator._count_vendors(csv_path)

        assert counts["Nivea"] == 2
        assert counts["Bioderma"] == 1

    def test_skips_rows_without_title(self, tmp_path):
        """iter_product_rows filters out rows with empty Title."""
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Vendor": "Nivea"},
            {"Title": "", "Vendor": "Nivea"},  # image-only row
            {"Title": "Product B", "Vendor": "Nivea"},
        ])
        creator = _creator()
        counts = creator._count_vendors(csv_path)

        assert counts["Nivea"] == 2

    def test_empty_vendor_ignored(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Vendor": ""},
            {"Title": "Product B", "Vendor": "Nivea"},
        ])
        creator = _creator()
        counts = creator._count_vendors(csv_path)

        assert counts["Nivea"] == 1
        assert len(counts) == 1

    def test_vendor_whitespace_stripped(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "Product A", "Vendor": "  Nivea  "},
        ])
        creator = _creator()
        counts = creator._count_vendors(csv_path)

        assert counts["Nivea"] == 1

    def test_nonexistent_file_returns_empty_counter(self, tmp_path):
        creator = _creator()
        counts = creator._count_vendors(str(tmp_path / "missing.csv"))

        assert len(counts) == 0


# ---------------------------------------------------------------------------
# _create_collection (dry-run)
# ---------------------------------------------------------------------------

class TestCreateCollectionDryRun:
    def test_dry_run_returns_true(self):
        creator = _creator(dry_run=True)
        result = creator._create_collection(
            title="Vitamins",
            column="tag",
            condition="Vitamins",
        )
        assert result is True

    def test_dry_run_does_not_call_api(self):
        creator = _creator(dry_run=True)
        # Replace rest_request so any call would be visible
        original_rest = creator.client.rest_request
        calls = []
        creator.client.rest_request = lambda *a, **kw: calls.append((a, kw))

        creator._create_collection(title="Vitamins", column="tag", condition="Vitamins")

        assert len(calls) == 0

    def test_dry_run_prints_preview(self, capsys):
        creator = _creator(dry_run=True)
        creator._create_collection(
            title="Skincare",
            column="tag",
            condition="Skincare",
        )
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Skincare" in captured.out

    def test_vendor_collection_dry_run(self):
        creator = _creator(dry_run=True)
        result = creator.create_vendor_collection("Nivea")
        assert result is True


# ---------------------------------------------------------------------------
# Brand-tag dedup in create_collections_from_csv
# ---------------------------------------------------------------------------

class TestBrandTagDedup:
    """When skip_brands=True, tags matching vendor names are excluded."""

    @staticmethod
    def _build_csv(tmp_path) -> str:
        """CSV where some tags duplicate vendor names."""
        return _write_csv(tmp_path, [
            # 3 products with vendor "BrandA" — the tag "BrandA" should be skippable
            {"Title": "P1", "Vendor": "BrandA", "Tags": "BrandA, vitamins"},
            {"Title": "P2", "Vendor": "BrandA", "Tags": "BrandA, vitamins"},
            {"Title": "P3", "Vendor": "BrandA", "Tags": "BrandA, vitamins"},
            # 3 products with vendor "BrandB" and tag "BrandB"
            {"Title": "P4", "Vendor": "BrandB", "Tags": "BrandB, skincare"},
            {"Title": "P5", "Vendor": "BrandB", "Tags": "BrandB, skincare"},
            {"Title": "P6", "Vendor": "BrandB", "Tags": "BrandB, skincare"},
        ])

    def test_skip_brands_true_removes_vendor_tags(self, tmp_path):
        csv_path = self._build_csv(tmp_path)
        creator = _creator(dry_run=True)

        creator.create_collections_from_csv(
            csv_path,
            min_products=1,
            skip_existing=True,
            skip_brands=True,
        )

        # "BrandA" and "BrandB" tags should be skipped (they match vendors)
        created = creator.created_collections
        assert "BrandA" not in created
        assert "BrandB" not in created
        # Non-brand tags should still be created
        assert "vitamins" in created
        assert "skincare" in created

    def test_skip_brands_false_keeps_vendor_tags(self, tmp_path):
        csv_path = self._build_csv(tmp_path)
        creator = _creator(dry_run=True)

        creator.create_collections_from_csv(
            csv_path,
            min_products=1,
            skip_existing=True,
            skip_brands=False,
        )

        created = creator.created_collections
        assert "BrandA" in created
        assert "BrandB" in created
        assert "vitamins" in created
        assert "skincare" in created

    def test_skip_brands_case_insensitive(self, tmp_path):
        """Vendor 'NiVeA' should match tag 'nivea' (case-insensitive)."""
        csv_path = _write_csv(tmp_path, [
            {"Title": "P1", "Vendor": "NiVeA", "Tags": "nivea, hydration"},
            {"Title": "P2", "Vendor": "NiVeA", "Tags": "nivea, hydration"},
            {"Title": "P3", "Vendor": "NiVeA", "Tags": "nivea, hydration"},
        ])
        creator = _creator(dry_run=True)

        creator.create_collections_from_csv(
            csv_path,
            min_products=1,
            skip_existing=True,
            skip_brands=True,
        )

        assert "nivea" not in creator.created_collections
        assert "hydration" in creator.created_collections

    def test_min_products_filters_low_count_tags(self, tmp_path):
        csv_path = _write_csv(tmp_path, [
            {"Title": "P1", "Vendor": "Acme", "Tags": "popular, rare-tag"},
            {"Title": "P2", "Vendor": "Acme", "Tags": "popular"},
            {"Title": "P3", "Vendor": "Acme", "Tags": "popular"},
        ])
        creator = _creator(dry_run=True)

        creator.create_collections_from_csv(
            csv_path,
            min_products=3,
            skip_existing=True,
            skip_brands=True,
        )

        # "popular" has 3 products, "rare-tag" has 1
        assert "popular" in creator.created_collections
        assert "rare-tag" not in creator.created_collections
