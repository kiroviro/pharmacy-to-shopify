"""Tests for scripts/monitor_dsa_campaign.py — is_google_ads_order and compute_revenue."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.monitor_dsa_campaign import compute_revenue, is_google_ads_order

# ---------------------------------------------------------------------------
# is_google_ads_order — table-driven parametrized tests
# ---------------------------------------------------------------------------


class TestIsGoogleAdsOrder:
    """All 6 code paths + edge cases for is_google_ads_order."""

    @pytest.mark.parametrize(
        "order, expected, reason",
        [
            # --- Path 1: gclid in landing_site ---
            pytest.param(
                {"landing_site": "/products/aspirin?gclid=abc123"},
                True,
                "gclid param in landing_site",
                id="path1-gclid-in-landing",
            ),
            pytest.param(
                {"landing_site": "/page?foo=bar&gclid=xyz&utm_source=google"},
                True,
                "gclid among multiple query params",
                id="path1-gclid-with-other-params",
            ),
            # --- Path 2: google in referrer AND (gclid or ads) ---
            pytest.param(
                {"referring_site": "https://www.google.com/search?gclid=abc"},
                True,
                "google referrer with gclid",
                id="path2-google-referrer-gclid",
            ),
            pytest.param(
                {"referring_site": "https://www.google.com/ads/landing"},
                True,
                "google referrer with ads path",
                id="path2-google-referrer-ads",
            ),
            pytest.param(
                {"referring_site": "https://www.GOOGLE.com/Ads/page"},
                True,
                "google+ads case-insensitive in referrer",
                id="path2-case-insensitive",
            ),
            # --- Path 3: utm_source=google AND utm_medium=cpc ---
            pytest.param(
                {"landing_site": "/page?utm_source=google&utm_medium=cpc"},
                True,
                "UTM tags for google/cpc",
                id="path3-utm-google-cpc",
            ),
            pytest.param(
                {"landing_site": "/page?utm_source=google&utm_medium=cpc&utm_campaign=dsa"},
                True,
                "UTM tags with extra campaign param",
                id="path3-utm-with-campaign",
            ),
            # --- Path 4: source_name == "google" ---
            pytest.param(
                {"source_name": "google"},
                True,
                "source_name exactly 'google'",
                id="path4-source-name-google",
            ),
            # --- Path 5: google_ads or gclid in tags ---
            pytest.param(
                {"tags": "google_ads, premium"},
                True,
                "google_ads tag present",
                id="path5-google-ads-tag",
            ),
            pytest.param(
                {"tags": "sale, GCLID, promo"},
                True,
                "GCLID tag (uppercase)",
                id="path5-gclid-tag-uppercase",
            ),
            pytest.param(
                {"tags": "Google_Ads"},
                True,
                "Google_Ads mixed case in tags",
                id="path5-google-ads-mixed-case",
            ),
            # --- Path 6: none match → False ---
            pytest.param(
                {
                    "landing_site": "/products/cream",
                    "referring_site": "https://facebook.com",
                    "source_name": "web",
                    "tags": "skincare, sale",
                },
                False,
                "organic order, no google signals",
                id="path6-organic",
            ),
            pytest.param(
                {},
                False,
                "empty dict",
                id="path6-empty-dict",
            ),
            # --- Edge cases ---
            pytest.param(
                {
                    "landing_site": None,
                    "referring_site": None,
                    "source_name": None,
                    "tags": None,
                },
                False,
                "all fields None",
                id="edge-all-none",
            ),
            pytest.param(
                {"referring_site": "https://mail.google.com/inbox"},
                False,
                "google in referrer but no gclid or ads — not an ad click",
                id="edge-mail-google-no-ads",
            ),
            pytest.param(
                {"source_name": "Google"},
                False,
                "source_name 'Google' (capitalized) does not match exact 'google'",
                id="edge-source-name-capitalized",
            ),
            pytest.param(
                {"landing_site": "/page?utm_source=google&utm_medium=organic"},
                False,
                "utm_source=google but utm_medium=organic, not cpc",
                id="edge-utm-organic-not-cpc",
            ),
            pytest.param(
                {"landing_site": "/page?utm_source=facebook&utm_medium=cpc"},
                False,
                "utm_medium=cpc but source is facebook, not google",
                id="edge-facebook-cpc",
            ),
            pytest.param(
                {"referring_site": "https://ads.example.com"},
                False,
                "'ads' in referrer but not google domain",
                id="edge-ads-non-google-referrer",
            ),
            pytest.param(
                {"tags": "google_sheets, organic"},
                False,
                "'google_sheets' does not contain 'google_ads' substring",
                id="edge-google-sheets-tag",
            ),
        ],
    )
    def test_detection(self, order, expected, reason):
        assert is_google_ads_order(order) is expected, reason

    def test_gclid_in_landing_takes_priority(self):
        """When gclid is in landing_site, function returns True immediately
        without checking other fields."""
        order = {
            "landing_site": "/page?gclid=abc",
            "referring_site": "",
            "source_name": "web",
            "tags": "",
        }
        assert is_google_ads_order(order) is True

    def test_multiple_signals_still_true(self):
        """Order with multiple Google Ads signals is still True (not double-counted)."""
        order = {
            "landing_site": "/page?gclid=abc&utm_source=google&utm_medium=cpc",
            "referring_site": "https://www.google.com/ads/",
            "source_name": "google",
            "tags": "google_ads",
        }
        assert is_google_ads_order(order) is True


# ---------------------------------------------------------------------------
# compute_revenue
# ---------------------------------------------------------------------------


class TestComputeRevenue:
    def test_empty_list(self):
        assert compute_revenue([]) == 0.0

    def test_single_order(self):
        orders = [{"total_price": "29.99"}]
        assert compute_revenue(orders) == pytest.approx(29.99)

    def test_multiple_orders(self):
        orders = [
            {"total_price": "10.00"},
            {"total_price": "20.50"},
            {"total_price": "5.25"},
        ]
        assert compute_revenue(orders) == pytest.approx(35.75)

    def test_missing_total_price_defaults_to_zero(self):
        orders = [
            {"total_price": "10.00"},
            {},
            {"total_price": "5.00"},
        ]
        assert compute_revenue(orders) == pytest.approx(15.00)

    def test_string_prices_converted_to_float(self):
        """Shopify returns total_price as a string."""
        orders = [{"total_price": "123.45"}]
        result = compute_revenue(orders)
        assert isinstance(result, float)
        assert result == pytest.approx(123.45)

    def test_zero_price_orders(self):
        orders = [{"total_price": "0.00"}, {"total_price": "0"}]
        assert compute_revenue(orders) == pytest.approx(0.0)
