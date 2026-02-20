"""
Regression tests grounded in real data bugs found in benu.bg crawl data.

Each test documents a specific inconsistency that was observed in production,
and verifies that our validators now catch it.

Bug history:
  a9b6d3b  Image URLs used pharmacy.example.com instead of benu.bg
           (source_domain not forwarded to per-product extractor)
  CSV data  Two Vichy Dercos combo products have no price (extraction failure)
  CSV data  119 duplicate SKUs — 106 near-expiry "Годен до" variants,
           13 true duplicates (e.g. SKU 24782, same handle & title)
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from src.extraction.validator import SpecificationValidator, _is_placeholder_domain
from src.models import ExtractedProduct, ProductImage
from src.validation.crawl_tracker import CrawlQualityTracker

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _valid_product(**overrides) -> ExtractedProduct:
    defaults = dict(
        title="Валиден Продукт Тест 500mg",
        url="https://benu.bg/validni-produkt",
        brand="BrandBG",
        sku="SKU-REG-001",
        price="15.99",
        category_path=["Vitamins"],
        handle="validni-produkt",
        images=[ProductImage(source_url="https://benu.bg/media/img1.jpg", position=1)],
        description="<p>Описание.</p>",
    )
    defaults.update(overrides)
    return ExtractedProduct(**defaults)


# ---------------------------------------------------------------------------
# Regression 1 — placeholder image domain (commit a9b6d3b)
# ---------------------------------------------------------------------------

class TestPlaceholderImageDomainRegression:
    """
    When BenuExtractor was renamed to PharmacyExtractor the default
    site_domain changed from 'benu.bg' to 'pharmacy.example.com'.
    BulkExtractor never passed site_domain to the per-product extractor,
    so every image URL in the 2026-02-19 crawl used pharmacy.example.com.
    Shopify reported "Media processing failed" on all imported products.
    """

    @pytest.mark.parametrize("bad_domain", [
        "pharmacy.example.com",
        "example.com",
        "www.example.com",
        "cdn.example.com",
        "localhost",
        "via.placeholder.com",
    ])
    def test_broken_image_domain_is_flagged(self, bad_domain):
        p = _valid_product(images=[
            ProductImage(source_url=f"https://{bad_domain}/product/img1.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert result["overall_valid"] is False, \
            f"{bad_domain!r} should make overall_valid False"
        assert any("placeholder domain" in e for e in result["errors"]), \
            f"Expected 'placeholder domain' error for {bad_domain!r}"

    def test_real_benu_domain_passes(self):
        """benu.bg image URLs must not be flagged."""
        p = _valid_product(images=[
            ProductImage(
                source_url="https://benu.bg/media/cache/product_view_default/images/img.jpg",
                position=1,
            )
        ])
        result = SpecificationValidator(p).validate()
        assert not any("placeholder domain" in e for e in result["errors"])

    @pytest.mark.parametrize("good_domain", [
        "benu.bg",
        "cdn.benu.bg",
        "images.benu.bg",
        "shopify-cdn.com",
        "cdn.shopify.com",
    ])
    def test_real_cdn_domains_pass(self, good_domain):
        p = _valid_product(images=[
            ProductImage(source_url=f"https://{good_domain}/img.jpg", position=1)
        ])
        result = SpecificationValidator(p).validate()
        assert not any("placeholder domain" in e for e in result["errors"]), \
            f"{good_domain!r} should not be flagged"

    def test_is_placeholder_domain_helper(self):
        """Unit test for the domain check helper."""
        assert _is_placeholder_domain("pharmacy.example.com")
        assert _is_placeholder_domain("example.com")
        assert _is_placeholder_domain("www.example.com")
        assert _is_placeholder_domain("localhost")
        assert _is_placeholder_domain("via.placeholder.com")
        assert not _is_placeholder_domain("benu.bg")
        assert not _is_placeholder_domain("cdn.benu.bg")
        assert not _is_placeholder_domain("cdn.shopify.com")


# ---------------------------------------------------------------------------
# Regression 2 — missing price (Vichy Dercos combo products)
# ---------------------------------------------------------------------------

class TestMissingPriceRegression:
    """
    Two Vichy Dercos combo products have an empty Price field in the CSV
    because benu.bg renders combo prices differently.
    """

    def test_missing_price_is_error(self):
        p = _valid_product(price="")
        result = SpecificationValidator(p).validate()
        assert result["overall_valid"] is False
        assert any("price: missing" in e for e in result["errors"])

    def test_price_zero_is_error(self):
        """Price of 0.00 is indistinguishable from 'not extracted'."""
        p = _valid_product(price="0.00")
        result = SpecificationValidator(p).validate()
        assert any("price" in e and "> 0" in e for e in result["errors"])

    @pytest.mark.skipif(
        not Path("data/benu.bg/raw/products.csv").exists(),
        reason="No raw CSV — run a crawl first"
    )
    def test_vichy_missing_price_products_found_in_csv(self):
        """
        Confirms the two known bad products still exist in the current CSV
        so we can verify the validator would catch them.
        """
        missing_price_handles = []
        with open("data/benu.bg/raw/products.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("Title", "").strip() and not row.get("Price", "").strip():
                    missing_price_handles.append(row.get("URL handle", ""))

        assert len(missing_price_handles) == 2, (
            f"Expected 2 missing-price products, found {len(missing_price_handles)}: "
            f"{missing_price_handles}"
        )
        assert all("vichy-dercos" in h for h in missing_price_handles)


# ---------------------------------------------------------------------------
# Regression 3 — duplicate SKUs (benu.bg near-expiry "Годен до" pattern)
# ---------------------------------------------------------------------------

class TestDuplicateSkuRegression:
    """
    benu.bg lists near-expiry products as separate pages with the same base
    SKU but an expiry-date suffix in the title, e.g.:
      SKU 8825 → 'АБГ Кардио х30'
      SKU 8825 → 'АБГ Кардио х30 Годен до: 30.4.2026 г.'
    CrawlQualityTracker must detect and count these.
    """

    def test_tracker_catches_godendo_sku_pattern(self):
        """The near-expiry variant duplicates the base product's SKU."""
        tracker = CrawlQualityTracker()

        base = _valid_product(handle="abg-kardio-h30", sku="8825")
        base.title = "АБГ Кардио капсули х30"

        expiry = _valid_product(
            handle="abg-kardio-h30698ae6f8c3347",
            sku="8825",
        )
        expiry.title = "АБГ Кардио капсули х30 Годен до: 30.4.2026 г."

        tracker.record(base, {"errors": [], "warnings": []})
        tracker.record(expiry, {"errors": [], "warnings": []})

        assert "8825" in tracker.duplicate_skus
        assert tracker.field_error_counts["sku_duplicate"] >= 1

    @pytest.mark.skipif(
        not Path("data/benu.bg/raw/products.csv").exists(),
        reason="No raw CSV — run a crawl first"
    )
    def test_real_csv_has_119_duplicate_skus(self):
        """
        Confirms the known scale of the duplicate SKU problem in the
        current crawl data (119 groups, mostly near-expiry variants).
        """
        from collections import Counter
        skus: list[str] = []
        with open("data/benu.bg/raw/products.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("Title", "").strip():
                    sku = row.get("SKU", "").strip()
                    if sku:
                        skus.append(sku)

        counts = Counter(skus)
        duplicate_groups = [sku for sku, n in counts.items() if n > 1]

        assert len(duplicate_groups) == 119, (
            f"Expected 119 duplicate SKU groups, found {len(duplicate_groups)}. "
            "Update this test if crawl data changes."
        )


# ---------------------------------------------------------------------------
# Regression 4 — validate_crawl.py catches real CSV issues
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not Path("data/benu.bg/raw/products.csv").exists(),
    reason="No raw CSV — run a crawl first"
)
class TestValidateCrawlOnRealData:
    """
    Run the same field-level checks as scripts/validate_crawl.py against
    the real CSV and verify that the known issues are detected.
    """

    @pytest.fixture(scope="class")
    def csv_rows(self):
        rows = []
        with open("data/benu.bg/raw/products.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("Title", "").strip():
                    rows.append(row)
        return rows

    def test_no_placeholder_image_domains(self, csv_rows):
        """After a9b6d3b fix, no image URLs should use example.com."""
        bad = [
            row.get("Product image URL", "")
            for row in csv_rows
            if "example.com" in row.get("Product image URL", "")
            or "localhost" in row.get("Product image URL", "")
        ]
        assert bad == [], f"Found {len(bad)} placeholder image URLs: {bad[:3]}"

    def test_two_products_have_missing_price(self, csv_rows):
        """Known: 2 Vichy Dercos combo products have empty Price."""
        missing = [r for r in csv_rows if not r.get("Price", "").strip()]
        assert len(missing) == 2, (
            f"Expected 2 missing-price products, found {len(missing)}"
        )

    def test_no_invalid_handles(self, csv_rows):
        """All handles must match [a-z0-9-]+."""
        bad = [
            r.get("URL handle", "")
            for r in csv_rows
            if r.get("URL handle", "") and
            not re.fullmatch(r"[a-z0-9-]+", r.get("URL handle", ""))
        ]
        assert bad == [], f"Found {len(bad)} invalid handles: {bad[:3]}"

    def test_duplicate_sku_count(self, csv_rows):
        """119 duplicate SKU groups exist in the current data."""
        from collections import Counter
        counts = Counter(r.get("SKU", "") for r in csv_rows if r.get("SKU", ""))
        dups = [sku for sku, n in counts.items() if n > 1]
        assert len(dups) == 119
