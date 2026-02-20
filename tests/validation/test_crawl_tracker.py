"""Tests for CrawlQualityTracker."""

import pytest

from src.models import ExtractedProduct, ProductImage
from src.validation.crawl_tracker import CrawlQualityTracker


def _product(handle: str = "product-1", price: str = "10.00") -> ExtractedProduct:
    return ExtractedProduct(
        title="Test Product Name",
        url="https://benu.bg/product",
        brand="Brand",
        sku="SKU-001",
        price=price,
        handle=handle,
        images=[ProductImage(source_url="https://cdn.benu.bg/img.jpg", position=1)],
    )


def _result(errors=None, warnings=None) -> dict:
    """Build a minimal validation result dict."""
    return {
        "errors": errors or [],
        "warnings": warnings or [],
        "issues": (errors or []) + (warnings or []),
        "overall_valid": not bool(errors),
    }


class TestBasicCounting:
    def test_initial_state(self):
        t = CrawlQualityTracker()
        assert t.total == 0
        assert t.valid == 0
        assert t.warnings_only == 0
        assert t.errors == 0

    def test_valid_product_counted(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result())
        assert t.total == 1
        assert t.valid == 1
        assert t.warnings_only == 0
        assert t.errors == 0

    def test_product_with_warnings_only(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result(warnings=["description: empty"]))
        assert t.warnings_only == 1
        assert t.errors == 0
        assert t.valid == 0

    def test_product_with_errors(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result(errors=["brand: missing"]))
        assert t.errors == 1
        assert t.valid == 0
        assert t.warnings_only == 0


class TestFieldErrorCounting:
    def test_field_errors_counted(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result(errors=["brand: missing", "sku: missing or empty"]))
        assert t.field_error_counts["brand"] == 1
        assert t.field_error_counts["sku"] == 1

    def test_same_field_error_accumulates(self):
        t = CrawlQualityTracker()
        t.record(_product("p1"), _result(errors=["brand: missing"]))
        t.record(_product("p2"), _result(errors=["brand: missing"]))
        assert t.field_error_counts["brand"] == 2

    def test_multiple_products_multiple_fields(self):
        t = CrawlQualityTracker()
        t.record(_product("p1"), _result(errors=["brand: missing", "images: no images found"]))
        t.record(_product("p2"), _result(errors=["brand: missing"]))
        assert t.field_error_counts["brand"] == 2
        assert t.field_error_counts["images"] == 1

    def test_warnings_also_counted_in_field_error_counts(self):
        # Consistency warnings (warnings-only, never errors) must still appear
        # in field_error_counts so they show up in the per-field quality report.
        t = CrawlQualityTracker()
        t.record(_product(), _result(warnings=["consistency_price: Vue=20.00 vs JSON-LD=25.00"]))
        assert t.field_error_counts["consistency_price"] == 1

    def test_both_errors_and_warnings_counted(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result(
            errors=["brand: missing"],
            warnings=["consistency_price: Vue=20.00 vs JSON-LD=25.00"],
        ))
        assert t.field_error_counts["brand"] == 1
        assert t.field_error_counts["consistency_price"] == 1


class TestDuplicateHandleDetection:
    def test_first_handle_not_duplicate(self):
        t = CrawlQualityTracker()
        t.record(_product("my-product"), _result())
        assert t.duplicate_handles == []

    def test_duplicate_handle_detected(self):
        t = CrawlQualityTracker()
        t.record(_product("my-product"), _result())
        t.record(_product("my-product"), _result())
        assert "my-product" in t.duplicate_handles

    def test_duplicate_handle_counted_in_field_errors(self):
        t = CrawlQualityTracker()
        t.record(_product("dup"), _result())
        t.record(_product("dup"), _result())
        assert t.field_error_counts["handle_duplicate"] == 1

    def test_different_handles_not_flagged(self):
        t = CrawlQualityTracker()
        t.record(_product("product-a"), _result())
        t.record(_product("product-b"), _result())
        assert t.duplicate_handles == []

    def test_empty_handle_not_tracked(self):
        t = CrawlQualityTracker()
        p = _product(handle="")
        p.handle = ""
        t.record(p, _result())
        assert t.duplicate_handles == []


class TestPriceTracking:
    def test_price_min_max(self):
        t = CrawlQualityTracker()
        t.record(_product(price="5.00"), _result())
        t.record(_product(price="50.00"), _result())
        t.record(_product(price="25.00"), _result())
        assert t.price_min == pytest.approx(5.0)
        assert t.price_max == pytest.approx(50.0)

    def test_invalid_price_skipped(self):
        t = CrawlQualityTracker()
        t.record(_product(price="not-a-number"), _result())
        assert t.price_min is None
        assert t.price_max is None


class TestHasCriticalFailures:
    def test_no_failures(self):
        t = CrawlQualityTracker()
        for i in range(10):
            t.record(_product(f"p{i}"), _result())
        assert not t.has_critical_failures()

    def test_below_threshold(self):
        t = CrawlQualityTracker()
        # 4 errors out of 100 = 4% < 5%
        for i in range(96):
            t.record(_product(f"ok{i}"), _result())
        for i in range(4):
            t.record(_product(f"err{i}"), _result(errors=["brand: missing"]))
        assert not t.has_critical_failures()

    def test_above_threshold(self):
        t = CrawlQualityTracker()
        # 6 errors out of 100 = 6% > 5%
        for i in range(94):
            t.record(_product(f"ok{i}"), _result())
        for i in range(6):
            t.record(_product(f"err{i}"), _result(errors=["brand: missing"]))
        assert t.has_critical_failures()

    def test_custom_threshold(self):
        t = CrawlQualityTracker()
        # 15 errors out of 100 = 15%
        for i in range(85):
            t.record(_product(f"ok{i}"), _result())
        for i in range(15):
            t.record(_product(f"err{i}"), _result(errors=["brand: missing"]))
        assert t.has_critical_failures(threshold_pct=10.0)
        assert not t.has_critical_failures(threshold_pct=20.0)

    def test_empty_tracker_no_failures(self):
        t = CrawlQualityTracker()
        assert not t.has_critical_failures()


class TestPeriodicSummary:
    def test_print_periodic_summary_no_crash(self, capsys):
        t = CrawlQualityTracker()
        t.record(_product(), _result())
        t.print_periodic_summary(100)
        captured = capsys.readouterr()
        assert "Progress 100" in captured.out

    def test_print_periodic_summary_shows_pct(self, capsys):
        t = CrawlQualityTracker()
        t.record(_product("p1"), _result())                          # valid
        t.record(_product("p2"), _result(errors=["brand: missing"])) # error
        t.print_periodic_summary(200)
        captured = capsys.readouterr()
        assert "50.0%" in captured.out  # 1/2 valid

    def test_empty_tracker_summary_no_crash(self, capsys):
        t = CrawlQualityTracker()
        t.print_periodic_summary(0)
        # Should not raise; empty tracker just returns


class TestDuplicateSkuDetection:
    def test_first_sku_not_duplicate(self):
        t = CrawlQualityTracker()
        t.record(_product(), _result())
        assert t.duplicate_skus == []

    def test_duplicate_sku_detected(self):
        t = CrawlQualityTracker()
        p1 = _product("prod-1")
        p1.sku = "SKU-SAME"
        p2 = _product("prod-2")
        p2.sku = "SKU-SAME"
        t.record(p1, _result())
        t.record(p2, _result())
        assert "SKU-SAME" in t.duplicate_skus

    def test_duplicate_sku_counted_in_field_errors(self):
        t = CrawlQualityTracker()
        p1 = _product("h1")
        p1.sku = "DUP"
        p2 = _product("h2")
        p2.sku = "DUP"
        t.record(p1, _result())
        t.record(p2, _result())
        assert t.field_error_counts["sku_duplicate"] == 1

    def test_different_skus_not_flagged(self):
        t = CrawlQualityTracker()
        p1 = _product("h1")
        p1.sku = "SKU-A"
        p2 = _product("h2")
        p2.sku = "SKU-B"
        t.record(p1, _result())
        t.record(p2, _result())
        assert t.duplicate_skus == []

    def test_godendo_pattern_duplicate_sku_is_detected(self):
        """
        Regression: benu.bg lists near-expiry products as separate entries
        but with the same base SKU — e.g. SKU '8825' for both
        'АБГ Кардио х30' and 'АБГ Кардио х30 Годен до: 30.4.2026 г.'
        Both get crawled; the duplicate SKU must be flagged.
        """
        t = CrawlQualityTracker()
        p1 = _product("abg-kardio-kapsuli-h30")
        p1.sku = "8825"
        p2 = _product("abg-kardio-kapsuli-h30698ae6f8c3347")  # hash suffix handle
        p2.sku = "8825"
        t.record(p1, _result())
        t.record(p2, _result())
        assert "8825" in t.duplicate_skus


class TestFinalReport:
    def test_print_final_report_no_crash(self, capsys):
        t = CrawlQualityTracker()
        for i in range(5):
            t.record(_product(f"p{i}"), _result())
        t.print_final_report()
        captured = capsys.readouterr()
        assert "Quality Report" in captured.out

    def test_final_report_shows_pass(self, capsys):
        t = CrawlQualityTracker()
        for i in range(10):
            t.record(_product(f"p{i}"), _result())
        t.print_final_report()
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_final_report_shows_fail(self, capsys):
        t = CrawlQualityTracker()
        for i in range(6):
            t.record(_product(f"err{i}"), _result(errors=["brand: missing"]))
        for i in range(94):
            t.record(_product(f"ok{i}"), _result())
        t.print_final_report()
        captured = capsys.readouterr()
        assert "FAIL" in captured.out
