"""Tests for scripts/price_sync.py"""

import csv
from unittest.mock import MagicMock, patch

from scripts.price_sync import (
    compare_prices,
    fetch_shopify_price,
    generate_shopify_csv,
    load_handles_from_csv,
)
from src.common.price_change import PriceChange

# ── fetch_shopify_price ──────────────────────────────────────────────────────


class TestFetchShopifyPrice:
    def test_parses_price_correctly(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "product": {
                "variants": [{"price": "19.99"}],
            }
        }
        session.get.return_value = mock_resp

        bgn, eur, err = fetch_shopify_price(session, "test-product")

        assert bgn == 19.99
        assert eur is not None
        assert err is None

    def test_handles_404(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        session.get.return_value = mock_resp

        bgn, eur, err = fetch_shopify_price(session, "nonexistent")

        assert bgn is None
        assert eur is None
        assert "Not found" in err

    def test_handles_no_variants(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"product": {"variants": []}}
        session.get.return_value = mock_resp

        bgn, eur, err = fetch_shopify_price(session, "no-variants")

        assert bgn is None
        assert err == "No variants"

    def test_handles_exception(self):
        session = MagicMock()
        session.get.side_effect = ConnectionError("Network error")

        bgn, eur, err = fetch_shopify_price(session, "error-product")

        assert bgn is None
        assert err is not None


# ── load_handles_from_csv ────────────────────────────────────────────────────


class TestLoadHandlesFromCSV:
    def test_loads_handles_and_titles(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "Title,URL handle\n"
            "Product A,product-a\n"
            "Product B,product-b\n",
            encoding="utf-8",
        )

        result = load_handles_from_csv(str(csv_file))

        assert result == [("product-a", "Product A"), ("product-b", "Product B")]

    def test_skips_rows_without_title(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "Title,URL handle\n"
            "Product A,product-a\n"
            ",variant-row\n"
            "Product B,product-b\n",
            encoding="utf-8",
        )

        result = load_handles_from_csv(str(csv_file))

        assert len(result) == 2
        assert result[0][0] == "product-a"
        assert result[1][0] == "product-b"

    def test_skips_rows_without_handle(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "Title,URL handle\n"
            "Product A,product-a\n"
            "No Handle,\n",
            encoding="utf-8",
        )

        result = load_handles_from_csv(str(csv_file))

        assert len(result) == 1


# ── compare_prices ───────────────────────────────────────────────────────────


class TestComparePrices:
    def test_detects_price_increase(self):
        products = [("prod-a", "Product A")]

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            return_value=(10.00, 5.11, None),
        ), patch(
            "scripts.price_sync.fetch_source_price",
            return_value=(15.00, 7.67, None),
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 1
        assert changes[0].change_pct > 0
        assert changes[0].new_bgn == 15.00

    def test_detects_price_decrease(self):
        products = [("prod-a", "Product A")]

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            return_value=(20.00, 10.22, None),
        ), patch(
            "scripts.price_sync.fetch_source_price",
            return_value=(10.00, 5.11, None),
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 1
        assert changes[0].change_pct < 0

    def test_ignores_within_tolerance(self):
        products = [("prod-a", "Product A")]

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            return_value=(10.00, 5.11, None),
        ), patch(
            "scripts.price_sync.fetch_source_price",
            return_value=(10.10, 5.16, None),
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 0

    def test_skips_shopify_error(self):
        products = [("prod-a", "Product A")]

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            return_value=(None, None, "Not found on Shopify"),
        ), patch(
            "scripts.price_sync.fetch_source_price",
            return_value=(10.00, 5.11, None),
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 0

    def test_skips_benu_error(self):
        products = [("prod-a", "Product A")]

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            return_value=(10.00, 5.11, None),
        ), patch(
            "scripts.price_sync.fetch_source_price",
            return_value=(None, None, "Product not found (404)"),
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 0

    def test_multiple_products(self):
        products = [
            ("prod-a", "Product A"),
            ("prod-b", "Product B"),
        ]

        shopify_prices = {
            "prod-a": (10.00, 5.11, None),
            "prod-b": (20.00, 10.22, None),
        }
        benu_prices = {
            "prod-a": (15.00, 7.67, None),  # increase
            "prod-b": (20.10, 10.27, None),  # within tolerance
        }

        with patch(
            "scripts.price_sync.fetch_shopify_price",
            side_effect=lambda s, h: shopify_prices[h],
        ), patch(
            "scripts.price_sync.fetch_source_price",
            side_effect=lambda s, h: benu_prices[h],
        ), patch("scripts.price_sync.time.sleep"):
            changes = compare_prices(products, delay=0)

        assert len(changes) == 1
        assert changes[0].handle == "prod-a"


# ── generate_shopify_csv ─────────────────────────────────────────────────────


class TestGenerateShopifyCSV:
    def test_writes_correct_columns(self, tmp_path):
        output = tmp_path / "updates.csv"
        changes = [
            PriceChange(
                handle="prod-a",
                title="Product A",
                old_bgn=10.00,
                new_bgn=15.00,
                old_eur=5.11,
                new_eur=7.67,
                change_pct=50.0,
                source_url="https://benu.bg/prod-a",
                shopify_url="https://viapharma.us/products/prod-a",
            ),
        ]

        generate_shopify_csv(changes, str(output))

        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["Handle"] == "prod-a"
        assert rows[0]["Variant Price"] == "15.00"
        assert "Title" in rows[0]

    def test_handles_empty_changes(self, tmp_path):
        output = tmp_path / "empty.csv"
        generate_shopify_csv([], str(output))

        with open(output, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0
