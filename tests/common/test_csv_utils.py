"""Tests for src/common/csv_utils.py — configure_csv and iter_product_rows."""

import csv

import pytest

from src.common.csv_utils import configure_csv, iter_product_rows

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSV_COLUMNS = ["Title", "Price", "Vendor", "Tags"]


def _write_csv(tmp_path, rows: list[dict], filename: str = "products.csv") -> str:
    """Write a minimal CSV and return its path as a string."""
    filepath = tmp_path / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})
    return str(filepath)


# ---------------------------------------------------------------------------
# configure_csv
# ---------------------------------------------------------------------------


class TestConfigureCsv:
    def test_default_sets_10mb_limit(self):
        configure_csv()
        # csv.field_size_limit() with no args returns the current limit
        assert csv.field_size_limit() == 10 * 1024 * 1024

    def test_custom_limit(self):
        configure_csv(field_size_limit=5_000_000)
        assert csv.field_size_limit() == 5_000_000
        # Restore default
        configure_csv()

    def test_called_on_module_import(self):
        """csv_utils calls configure_csv() at module level, so the limit
        should already be 10MB after import."""
        assert csv.field_size_limit() == 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# iter_product_rows
# ---------------------------------------------------------------------------


class TestIterProductRows:
    def test_yields_rows_with_title(self, tmp_path):
        csv_path = _write_csv(
            tmp_path,
            [
                {"Title": "Aspirin 500mg", "Price": "3.99", "Vendor": "Bayer"},
                {"Title": "Ibuprofen 200mg", "Price": "2.50", "Vendor": "Advil"},
            ],
        )
        rows = list(iter_product_rows(csv_path))

        assert len(rows) == 2
        assert rows[0]["Title"] == "Aspirin 500mg"
        assert rows[1]["Title"] == "Ibuprofen 200mg"

    def test_skips_empty_title(self, tmp_path):
        csv_path = _write_csv(
            tmp_path,
            [
                {"Title": "Product A", "Price": "10.00"},
                {"Title": "", "Price": "5.00"},  # image-only continuation row
                {"Title": "Product B", "Price": "8.00"},
            ],
        )
        rows = list(iter_product_rows(csv_path))

        assert len(rows) == 2
        assert rows[0]["Title"] == "Product A"
        assert rows[1]["Title"] == "Product B"

    def test_skips_whitespace_only_title(self, tmp_path):
        csv_path = _write_csv(
            tmp_path,
            [
                {"Title": "Real Product", "Price": "1.00"},
                {"Title": "   ", "Price": "2.00"},
                {"Title": "\t", "Price": "3.00"},
            ],
        )
        rows = list(iter_product_rows(csv_path))

        assert len(rows) == 1
        assert rows[0]["Title"] == "Real Product"

    def test_empty_csv_yields_nothing(self, tmp_path):
        csv_path = _write_csv(tmp_path, [])
        rows = list(iter_product_rows(csv_path))

        assert rows == []

    def test_header_only_csv_yields_nothing(self, tmp_path):
        """A CSV with headers but no data rows."""
        filepath = tmp_path / "empty.csv"
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

        rows = list(iter_product_rows(str(filepath)))
        assert rows == []

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(iter_product_rows(str(tmp_path / "nonexistent.csv")))

    def test_returns_dict_rows(self, tmp_path):
        csv_path = _write_csv(
            tmp_path,
            [{"Title": "Cream", "Price": "5.00", "Vendor": "Nivea", "Tags": "skincare"}],
        )
        rows = list(iter_product_rows(csv_path))

        assert len(rows) == 1
        row = rows[0]
        assert isinstance(row, dict)
        assert row["Price"] == "5.00"
        assert row["Vendor"] == "Nivea"
        assert row["Tags"] == "skincare"

    def test_is_generator(self, tmp_path):
        """iter_product_rows returns a generator, not a list."""
        csv_path = _write_csv(tmp_path, [{"Title": "X"}])
        result = iter_product_rows(csv_path)

        import types

        assert isinstance(result, types.GeneratorType)

    def test_all_rows_empty_title_yields_nothing(self, tmp_path):
        csv_path = _write_csv(
            tmp_path,
            [
                {"Title": "", "Price": "1.00"},
                {"Title": "", "Price": "2.00"},
                {"Title": "  ", "Price": "3.00"},
            ],
        )
        rows = list(iter_product_rows(csv_path))

        assert rows == []
