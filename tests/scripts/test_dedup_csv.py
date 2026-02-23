"""Tests for scripts/dedup_csv.py"""

from __future__ import annotations

import csv

from scripts.dedup_csv import dedup_csv, is_expiry_variant

# ── is_expiry_variant ─────────────────────────────────────────────────────────


class TestIsExpiryVariant:
    def test_detects_godendo_suffix(self):
        assert is_expiry_variant("АБГ Кардио х30 Годен до: 30.04.2026 г.")

    def test_detects_single_digit_day_month(self):
        assert is_expiry_variant("Продукт Годен до: 1.4.2026 г.")

    def test_detects_two_digit_values(self):
        assert is_expiry_variant("Product Name Годен до: 28.02.2026 г.")

    def test_plain_title_returns_false(self):
        assert not is_expiry_variant("АБГ Кардио х30")

    def test_empty_string_returns_false(self):
        assert not is_expiry_variant("")


# ── dedup_csv ─────────────────────────────────────────────────────────────────

FIELDNAMES = ["Title", "URL handle", "SKU", "Price"]


def _write_csv(path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestDedupCsv:
    def test_empty_csv_returns_zero_stats(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        _write_csv(csv_file, [])
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["total"] == 0
        assert stats["kept"] == 0
        assert stats["removed"] == 0

    def test_no_dupes_passthrough(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Product A", "URL handle": "a", "SKU": "100", "Price": "9.99"},
            {"Title": "Product B", "URL handle": "b", "SKU": "200", "Price": "14.99"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["total"] == 2
        assert stats["kept"] == 2
        assert stats["removed"] == 0
        assert stats["expiry_removed"] == 0
        assert stats["true_dupes_removed"] == 0
        result = _read_csv(out)
        assert len(result) == 2

    def test_expiry_variant_removed_when_base_exists(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "АБГ Кардио х30", "URL handle": "abg", "SKU": "8825", "Price": "9.99"},
            {"Title": "АБГ Кардио х30 Годен до: 30.04.2026 г.", "URL handle": "abg-exp", "SKU": "8825", "Price": "8.99"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["expiry_removed"] == 1
        assert stats["true_dupes_removed"] == 0
        assert stats["kept"] == 1
        result = _read_csv(out)
        assert len(result) == 1
        assert result[0]["Title"] == "АБГ Кардио х30"

    def test_latest_expiry_kept_when_all_are_expiry(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Prod Годен до: 31.03.2026 г.", "URL handle": "p1", "SKU": "999", "Price": "5.00"},
            {"Title": "Prod Годен до: 30.06.2026 г.", "URL handle": "p2", "SKU": "999", "Price": "5.00"},
            {"Title": "Prod Годен до: 28.02.2026 г.", "URL handle": "p3", "SKU": "999", "Price": "5.00"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["expiry_removed"] == 2
        result = _read_csv(out)
        assert len(result) == 1
        assert "30.06.2026" in result[0]["Title"]

    def test_true_dupe_keeps_first_occurrence(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Widget", "URL handle": "widget-1", "SKU": "42", "Price": "10.00"},
            {"Title": "Widget Duplicate", "URL handle": "widget-2", "SKU": "42", "Price": "10.00"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["true_dupes_removed"] == 1
        assert stats["expiry_removed"] == 0
        result = _read_csv(out)
        assert len(result) == 1
        assert result[0]["URL handle"] == "widget-1"

    def test_mixed_expiry_and_true_dupe_same_sku(self, tmp_path):
        """SKU with both a base, a true dup (same title), and an expiry variant."""
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Alpha", "URL handle": "alpha-1", "SKU": "77", "Price": "7.00"},
            {"Title": "Alpha", "URL handle": "alpha-2", "SKU": "77", "Price": "7.00"},  # true dup
            {"Title": "Alpha Годен до: 30.04.2026 г.", "URL handle": "alpha-exp", "SKU": "77", "Price": "6.50"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        # Expiry pass removes the expiry variant; then true-dupe pass removes 1 of the 2 base rows
        assert stats["expiry_removed"] == 1
        assert stats["true_dupes_removed"] == 1
        assert stats["kept"] == 1
        result = _read_csv(out)
        assert len(result) == 1

    def test_stats_dict_keys_present(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        _write_csv(csv_file, [])
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert set(stats.keys()) == {"total", "kept", "removed", "expiry_removed", "true_dupes_removed"}

    def test_removed_equals_expiry_plus_true_dupes(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "A", "URL handle": "a1", "SKU": "1", "Price": "1.00"},
            {"Title": "A Годен до: 01.01.2026 г.", "URL handle": "a2", "SKU": "1", "Price": "1.00"},
            {"Title": "B", "URL handle": "b1", "SKU": "2", "Price": "2.00"},
            {"Title": "B", "URL handle": "b2", "SKU": "2", "Price": "2.00"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["removed"] == stats["expiry_removed"] + stats["true_dupes_removed"]

    def test_output_file_written(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        _write_csv(csv_file, [{"Title": "X", "URL handle": "x", "SKU": "1", "Price": "1.00"}])
        out = tmp_path / "out.csv"

        dedup_csv(str(csv_file), str(out))

        assert out.exists()

    def test_no_output_path_skips_write(self, tmp_path):
        """Passing output_path=None returns stats without writing any file."""
        csv_file = tmp_path / "products.csv"
        _write_csv(csv_file, [{"Title": "X", "URL handle": "x", "SKU": "1", "Price": "1.00"}])

        stats = dedup_csv(str(csv_file), None)

        assert stats["total"] == 1
        # No output file created
        assert not (tmp_path / "out.csv").exists()

    def test_rows_without_sku_always_kept(self, tmp_path):
        """Rows with empty SKU are never deduplicated against each other."""
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Product A", "URL handle": "a", "SKU": "", "Price": "9.99"},
            {"Title": "Product B", "URL handle": "b", "SKU": "", "Price": "4.99"},
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        stats = dedup_csv(str(csv_file), str(out))

        assert stats["kept"] == 2
        assert stats["removed"] == 0

    def test_non_title_rows_preserved(self, tmp_path):
        """Rows with empty Title (variant image rows) are passed through unchanged."""
        csv_file = tmp_path / "products.csv"
        rows = [
            {"Title": "Product A", "URL handle": "a", "SKU": "10", "Price": "9.99"},
            {"Title": "", "URL handle": "a", "SKU": "", "Price": ""},  # variant image row
        ]
        _write_csv(csv_file, rows)
        out = tmp_path / "out.csv"

        dedup_csv(str(csv_file), str(out))

        result = _read_csv(out)
        assert len(result) == 2
