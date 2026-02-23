"""Tests for scripts/price_monitor.py"""

from unittest.mock import MagicMock, patch

import pytest

from scripts.price_monitor import PriceMonitor, _chunked
from src.common.price_change import PriceChange

# ── _chunked helper ──────────────────────────────────────────────────────────


class TestChunked:
    def test_even_split(self):
        assert _chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_uneven_split(self):
        assert _chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_chunk_larger_than_list(self):
        assert _chunked([1, 2], 10) == [[1, 2]]

    def test_empty_list(self):
        assert _chunked([], 5) == []


# ── fetch_shopify_prices (batched GraphQL) ───────────────────────────────────


class TestFetchShopifyPrices:
    @pytest.fixture()
    def monitor(self):
        m = PriceMonitor(shopify_shop="test", shopify_token="tok")
        m.shopify_client.min_request_interval = 0
        return m

    def test_returns_correct_prices(self, monitor):
        graphql_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "handle": "product-a",
                            "variants": {"edges": [{"node": {"price": "19.99"}}]},
                        }
                    },
                    {
                        "node": {
                            "handle": "product-b",
                            "variants": {"edges": [{"node": {"price": "29.50"}}]},
                        }
                    },
                ]
            }
        }

        with patch.object(
            monitor.shopify_client, "graphql_request", return_value=graphql_response
        ), patch("scripts.price_monitor.time.sleep"):
            result = monitor.fetch_shopify_prices(["product-a", "product-b"])

        assert result["product-a"] == (19.99, None)
        assert result["product-b"] == (29.50, None)

    def test_marks_missing_products(self, monitor):
        graphql_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "handle": "product-a",
                            "variants": {"edges": [{"node": {"price": "10.00"}}]},
                        }
                    }
                ]
            }
        }

        with patch.object(
            monitor.shopify_client, "graphql_request", return_value=graphql_response
        ), patch("scripts.price_monitor.time.sleep"):
            result = monitor.fetch_shopify_prices(["product-a", "product-missing"])

        assert result["product-a"] == (10.00, None)
        assert result["product-missing"] == (None, "Not found")

    def test_handles_no_variants(self, monitor):
        graphql_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "handle": "product-a",
                            "variants": {"edges": []},
                        }
                    }
                ]
            }
        }

        with patch.object(
            monitor.shopify_client, "graphql_request", return_value=graphql_response
        ), patch("scripts.price_monitor.time.sleep"):
            result = monitor.fetch_shopify_prices(["product-a"])

        assert result["product-a"] == (None, "No variants")

    def test_handles_graphql_error(self, monitor):
        with patch.object(
            monitor.shopify_client, "graphql_request", side_effect=Exception("timeout")
        ), patch("scripts.price_monitor.time.sleep"):
            result = monitor.fetch_shopify_prices(["product-a"])

        assert result["product-a"][0] is None
        assert "timeout" in result["product-a"][1]

    def test_no_shopify_client(self):
        monitor = PriceMonitor()
        result = monitor.fetch_shopify_prices(["product-a"])
        assert result == {"product-a": (None, "No Shopify client")}

    def test_batches_handles(self, monitor):
        """Verify handles are batched (not sent one at a time)."""
        handles = [f"product-{i}" for i in range(75)]  # > 50, should create 2 batches
        call_count = 0

        def mock_graphql(query, variables):
            nonlocal call_count
            call_count += 1
            return {"products": {"edges": []}}

        with patch.object(
            monitor.shopify_client, "graphql_request", side_effect=mock_graphql
        ), patch("scripts.price_monitor.time.sleep"):
            monitor.fetch_shopify_prices(handles)

        assert call_count == 2  # 50 + 25

    def test_empty_response(self, monitor):
        with patch.object(
            monitor.shopify_client, "graphql_request", return_value=None
        ), patch("scripts.price_monitor.time.sleep"):
            result = monitor.fetch_shopify_prices(["product-a"])

        assert result["product-a"] == (None, "Not found")


# ── compare_prices ───────────────────────────────────────────────────────────


class TestCompareMonitorPrices:
    @pytest.fixture()
    def monitor(self):
        m = PriceMonitor(shopify_shop="test", shopify_token="tok")
        m.shopify_client.min_request_interval = 0
        return m

    def test_detects_price_increase(self, monitor):
        with patch.object(
            monitor, "fetch_shopify_prices", return_value={"prod-a": (10.00, None)}
        ), patch.object(
            monitor, "fetch_benu_price", return_value=(15.00, 7.67, None)
        ), patch("scripts.price_monitor.time.sleep"):
            changes = monitor.compare_prices(["prod-a"], delay=0)

        assert len(changes) == 1
        assert changes[0].source == "benu"
        assert changes[0].change_pct > 0

    def test_detects_price_decrease(self, monitor):
        with patch.object(
            monitor, "fetch_shopify_prices", return_value={"prod-a": (20.00, None)}
        ), patch.object(
            monitor, "fetch_benu_price", return_value=(10.00, 5.11, None)
        ), patch("scripts.price_monitor.time.sleep"):
            changes = monitor.compare_prices(["prod-a"], delay=0)

        assert len(changes) == 1
        assert changes[0].source == "drift"
        assert changes[0].change_pct < 0

    def test_ignores_within_tolerance(self, monitor):
        with patch.object(
            monitor, "fetch_shopify_prices", return_value={"prod-a": (10.00, None)}
        ), patch.object(
            monitor, "fetch_benu_price", return_value=(10.10, 5.16, None)
        ), patch("scripts.price_monitor.time.sleep"):
            changes = monitor.compare_prices(["prod-a"], delay=0)

        assert len(changes) == 0

    def test_skips_benu_error(self, monitor):
        with patch.object(
            monitor, "fetch_shopify_prices", return_value={"prod-a": (10.00, None)}
        ), patch.object(
            monitor, "fetch_benu_price", return_value=(None, None, "404")
        ), patch("scripts.price_monitor.time.sleep"):
            changes = monitor.compare_prices(["prod-a"], delay=0)

        assert len(changes) == 0


# ── generate_report ──────────────────────────────────────────────────────────


class TestGenerateReport:
    def test_no_changes(self):
        monitor = PriceMonitor()
        report = monitor.generate_report([])
        assert "All prices are in sync" in report

    def test_shows_increases(self):
        monitor = PriceMonitor()
        changes = [
            PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0, "benu"),
        ]
        report = monitor.generate_report(changes)
        assert "PRICE INCREASES" in report
        assert "prod-a" in report

    def test_shows_decreases(self):
        monitor = PriceMonitor()
        changes = [
            PriceChange("prod-b", "Product B", 20.0, 10.0, -50.0, "drift"),
        ]
        report = monitor.generate_report(changes)
        assert "PRICE DECREASES" in report
        assert "prod-b" in report

    def test_mixed_changes(self):
        monitor = PriceMonitor()
        changes = [
            PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0, "benu"),
            PriceChange("prod-b", "Product B", 20.0, 10.0, -50.0, "drift"),
        ]
        report = monitor.generate_report(changes)
        assert "PRICE INCREASES" in report
        assert "PRICE DECREASES" in report


# ── sync_to_shopify ───────────────────────────────────────────────────────────


class TestSyncToShopify:
    def _monitor_with_client(self) -> PriceMonitor:
        monitor = PriceMonitor.__new__(PriceMonitor)
        monitor.shopify_client = MagicMock()
        monitor.changes = []
        monitor._checked_count = 0
        import requests
        monitor.session = requests.Session()
        return monitor

    def test_dry_run_returns_zero_without_api_calls(self):
        monitor = self._monitor_with_client()
        change = PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0)

        updated = monitor.sync_to_shopify([change], dry_run=True)

        assert updated == 0
        monitor.shopify_client.graphql_request.assert_not_called()

    def test_no_client_returns_zero(self):
        monitor = PriceMonitor()  # No client configured
        change = PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0)

        updated = monitor.sync_to_shopify([change], dry_run=False)

        assert updated == 0

    def test_updates_product_price(self):
        monitor = self._monitor_with_client()
        change = PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0)

        # First call: get variant ID; second call: mutation
        monitor.shopify_client.graphql_request.side_effect = [
            {"productByHandle": {"variants": {"edges": [{"node": {"id": "gid://shopify/ProductVariant/123"}}]}}},
            {"productVariantUpdate": {"productVariant": {"id": "gid://...123", "price": "15.0"}, "userErrors": []}},
        ]

        with patch("scripts.price_monitor.time.sleep"):
            updated = monitor.sync_to_shopify([change], dry_run=False)

        assert updated == 1
        # Verify the mutation was called with the new price
        mutation_call_args = monitor.shopify_client.graphql_request.call_args_list[1]
        payload = mutation_call_args[0][1]  # second positional arg = variables
        assert payload["input"]["price"] == "15.0"

    def test_skips_product_not_found_in_shopify(self):
        monitor = self._monitor_with_client()
        change = PriceChange("nonexistent", "Unknown", 10.0, 15.0, 50.0)

        monitor.shopify_client.graphql_request.return_value = {"productByHandle": None}

        with patch("scripts.price_monitor.time.sleep"):
            updated = monitor.sync_to_shopify([change], dry_run=False)

        assert updated == 0

    def test_skips_product_with_user_errors(self):
        monitor = self._monitor_with_client()
        change = PriceChange("prod-a", "Product A", 10.0, 15.0, 50.0)

        monitor.shopify_client.graphql_request.side_effect = [
            {"productByHandle": {"variants": {"edges": [{"node": {"id": "gid://...123"}}]}}},
            {"productVariantUpdate": {"productVariant": None, "userErrors": [{"field": "price", "message": "Invalid"}]}},
        ]

        with patch("scripts.price_monitor.time.sleep"):
            updated = monitor.sync_to_shopify([change], dry_run=False)

        assert updated == 0
