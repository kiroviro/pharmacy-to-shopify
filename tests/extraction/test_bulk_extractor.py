"""
Tests for BulkExtractor.

Covers the site_domain forwarding contract and image URL correctness.
"""

from __future__ import annotations

import csv

from src.extraction.bulk_extractor import BulkExtractor
from src.models import ExtractedProduct, ProductImage


class FakeExtractor:
    """Minimal extractor that records constructor kwargs and returns a product."""

    captured_kwargs: dict = {}

    def __init__(self, url: str, **kwargs):
        FakeExtractor.captured_kwargs = kwargs
        self.url = url
        self.html = None

    def fetch(self) -> None:
        pass

    def extract(self) -> ExtractedProduct:
        site_domain = FakeExtractor.captured_kwargs.get("site_domain", "missing-domain.invalid")
        return ExtractedProduct(
            title="Fake Product",
            url=self.url,
            brand="Brand",
            sku="SKU-001",
            price="10.00",
            handle="fake-product",
            images=[ProductImage(
                source_url=f"https://{site_domain}/media/cache/product_view_default/images/products/1/1.webp",
                position=1,
                alt_text="Fake Product",
            )],
        )


class TestBulkExtractorSiteDomainForwarding:
    """
    Regression tests for site_domain forwarding.

    Background: commit df4d307 renamed BenuExtractor (default site_domain='benu.bg')
    to PharmacyExtractor (default site_domain='pharmacy.example.com'). Since
    BulkExtractor never explicitly passed site_domain to the per-product extractor,
    all relative image URLs in extracted CSVs silently got the placeholder domain,
    causing Shopify's "Media processing failed" error on import.
    """

    def test_site_domain_forwarded_to_extractor(self, tmp_path):
        """BulkExtractor must pass source_domain as site_domain to each per-product extractor."""
        FakeExtractor.captured_kwargs = {}

        bulk = BulkExtractor(
            output_csv=str(tmp_path / "products.csv"),
            output_dir=str(tmp_path),
            source_domain="benu.bg",
        )
        bulk.extract_all(
            urls=["https://benu.bg/fake-product"],
            extractor_class=FakeExtractor,
        )

        assert FakeExtractor.captured_kwargs.get("site_domain") == "benu.bg"

    def test_image_urls_in_csv_use_real_domain(self, tmp_path):
        """Image URLs written to CSV must use the real domain, not the placeholder."""
        output_csv = str(tmp_path / "products.csv")

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=str(tmp_path),
            source_domain="benu.bg",
        )
        bulk.extract_all(
            urls=["https://benu.bg/fake-product"],
            extractor_class=FakeExtractor,
        )

        with open(output_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows, "CSV must contain at least one row"
        image_url = rows[0]["Product image URL"]
        assert "benu.bg" in image_url, f"Expected real domain in image URL, got: {image_url}"
        assert "example.com" not in image_url, (
            f"Placeholder domain leaked into image URL: {image_url}"
        )

    def test_placeholder_domain_not_used_when_source_domain_set(self, tmp_path):
        """The placeholder 'pharmacy.example.com' must never appear in image URLs
        when BulkExtractor is given a real source_domain."""
        output_csv = str(tmp_path / "products.csv")

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=str(tmp_path),
            source_domain="realpharmacy.bg",
        )
        bulk.extract_all(
            urls=["https://realpharmacy.bg/product-1"],
            extractor_class=FakeExtractor,
        )

        with open(output_csv, encoding="utf-8") as f:
            content = f.read()

        assert "pharmacy.example.com" not in content, (
            "Placeholder domain must not appear in CSV when a real source_domain is given"
        )
