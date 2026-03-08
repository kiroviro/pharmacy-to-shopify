"""
Tests for BulkExtractor.

Covers domain handling and image URL correctness.
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
        # BulkExtractor no longer passes site_domain; extractors hardcode it
        domain = "benu.bg"
        return ExtractedProduct(
            title="Fake Product",
            url=self.url,
            brand="Brand",
            sku="SKU-001",
            price="10.00",
            handle="fake-product",
            images=[ProductImage(
                source_url=f"https://{domain}/media/cache/product_view_default/images/products/1/1.webp",
                position=1,
                alt_text="Fake Product",
            )],
        )


class TestBulkExtractorDomainHandling:
    """
    Regression tests for domain handling in extracted CSVs.

    Background: extractors now hardcode their domain (benu.bg) instead of
    receiving it as a parameter. These tests verify image URLs in the output
    CSV use the correct domain.
    """

    def test_extraction_produces_csv(self, tmp_path):
        """BulkExtractor produces a CSV with content."""
        FakeExtractor.captured_kwargs = {}
        output_csv = str(tmp_path / "products.csv")

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=str(tmp_path),
        )
        bulk.extract_all(
            urls=["https://benu.bg/fake-product"],
            extractor_class=FakeExtractor,
        )

        with open(output_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        assert rows, "CSV must contain at least one row"

    def test_image_urls_in_csv_use_real_domain(self, tmp_path):
        """Image URLs written to CSV must use the real domain, not the placeholder."""
        output_csv = str(tmp_path / "products.csv")

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=str(tmp_path),
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

    def test_placeholder_domain_not_in_csv(self, tmp_path):
        """The placeholder 'pharmacy.example.com' must never appear in image URLs."""
        output_csv = str(tmp_path / "products.csv")

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=str(tmp_path),
        )
        bulk.extract_all(
            urls=["https://benu.bg/product-1"],
            extractor_class=FakeExtractor,
        )

        with open(output_csv, encoding="utf-8") as f:
            content = f.read()

        assert "pharmacy.example.com" not in content, (
            "Placeholder domain must not appear in CSV"
        )


class _UniqueProductExtractor:
    """Extractor that produces unique products per URL (for resume tests)."""

    def __init__(self, url: str, **kwargs):
        self.url = url
        self.html = None

    def fetch(self) -> None:
        pass

    def extract(self) -> ExtractedProduct:
        # Derive a unique suffix from the URL so each product is distinguishable
        slug = self.url.rstrip("/").rsplit("/", 1)[-1]
        return ExtractedProduct(
            title=f"Product {slug}",
            url=self.url,
            brand="Brand",
            sku=f"SKU-{slug}",
            price="10.00",
            handle=slug,
            images=[ProductImage(
                source_url=f"https://benu.bg/media/cache/product_view_default/images/{slug}.webp",
                position=1,
                alt_text=f"Product {slug}",
            )],
        )


class TestBulkExtractorStateResume:
    """Tests for save/load state and resume functionality."""

    def test_save_load_state_roundtrip(self, tmp_path):
        """save_state() persists state that load_state() fully restores."""
        output_csv = str(tmp_path / "products.csv")
        output_dir = str(tmp_path)

        bulk = BulkExtractor(
            output_csv=output_csv,
            output_dir=output_dir,
            delay=0,
            validate=False,
        )
        # Set known state values
        bulk.processed_urls = {"https://benu.bg/a", "https://benu.bg/b", "https://benu.bg/c"}
        bulk.total_extracted = 3
        bulk.total_image_rows = 6
        bulk.total_images = 9
        bulk.save_state()

        # Create a fresh instance and load the state
        bulk2 = BulkExtractor(
            output_csv=output_csv,
            output_dir=output_dir,
            delay=0,
            validate=False,
        )
        loaded = bulk2.load_state()

        assert loaded is True, "load_state() should return True when state file exists"
        assert bulk2.processed_urls == {"https://benu.bg/a", "https://benu.bg/b", "https://benu.bg/c"}
        assert bulk2.total_extracted == 3
        assert bulk2.total_image_rows == 6
        assert bulk2.total_images == 9

    def test_resume_skips_processed_urls(self, tmp_path):
        """resume=True skips already-processed URLs and appends new products to CSV."""
        output_csv = str(tmp_path / "products.csv")
        output_dir = str(tmp_path)

        # --- First run: extract 2 products ---
        bulk1 = BulkExtractor(
            output_csv=output_csv,
            output_dir=output_dir,
            delay=0,
            validate=False,
        )
        urls_first = ["https://benu.bg/product-1", "https://benu.bg/product-2"]
        bulk1.extract_all(
            urls=urls_first,
            extractor_class=_UniqueProductExtractor,
        )

        assert "https://benu.bg/product-1" in bulk1.processed_urls
        assert "https://benu.bg/product-2" in bulk1.processed_urls
        assert bulk1.total_extracted == 2

        # --- Second run: resume with 3 URLs (2 old + 1 new) ---
        bulk2 = BulkExtractor(
            output_csv=output_csv,
            output_dir=output_dir,
            delay=0,
            validate=False,
        )
        urls_second = [
            "https://benu.bg/product-1",
            "https://benu.bg/product-2",
            "https://benu.bg/product-3",
        ]
        bulk2.extract_all(
            urls=urls_second,
            extractor_class=_UniqueProductExtractor,
            resume=True,
        )

        # total_extracted is cumulative: 2 restored from state + 1 new = 3
        # The key proof that resume worked is that we didn't re-extract the
        # first 2 URLs: total_extracted is 3 (not 3 from scratch, but 2+1).
        assert bulk2.total_extracted == 3, (
            f"Expected 3 total extracted (2 restored + 1 new), got {bulk2.total_extracted}"
        )
        assert "https://benu.bg/product-3" in bulk2.processed_urls

        # CSV should contain all 3 products (2 from first run + 1 appended)
        with open(output_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        titles = [r["Title"] for r in rows if r.get("Title", "").strip()]
        assert len(titles) == 3, f"Expected 3 product rows in CSV, got {len(titles)}: {titles}"
        assert "Product product-1" in titles
        assert "Product product-2" in titles
        assert "Product product-3" in titles


def test_proxy_rotation_sets_session_proxies(tmp_path):
    """When proxies are provided, random.choice picks from the list and sets session.proxies."""
    from unittest.mock import patch

    import requests

    proxies = [
        "http://user:pass@proxy1.example.com:8001",
        "http://user:pass@proxy2.example.com:8002",
    ]
    bulk = BulkExtractor(
        output_csv=str(tmp_path / "out.csv"),
        output_dir=str(tmp_path),
        proxies=proxies,
        validate=False,
    )

    captured_sessions = []
    OriginalSession = requests.Session

    class CapturingSession(OriginalSession):
        def __init__(self):
            super().__init__()
            captured_sessions.append(self)

    with patch("src.extraction.bulk_extractor.requests.Session", CapturingSession):
        with patch("src.extraction.bulk_extractor.random.choice", return_value=proxies[0]) as mock_choice:
            bulk.extract_all(
                urls=["https://benu.bg/product-1"],
                extractor_class=FakeExtractor,
                limit=1,
            )

    mock_choice.assert_called_with(proxies)
    assert len(captured_sessions) == 1
    session = captured_sessions[0]
    assert session.proxies.get("http") == proxies[0]
    assert session.proxies.get("https") == proxies[0]


class TestRetryOnNetworkError:
    """BulkExtractor retries transient network errors before giving up."""

    def _make_extractor_class(self, fail_count: int):
        """Return an extractor class whose fetch() fails `fail_count` times then succeeds."""
        import requests as req
        counter = {"calls": 0}

        class _RetryExtractor:
            def __init__(self, url, **kwargs):
                self.url = url
                self.html = None

            def fetch(self):
                counter["calls"] += 1
                if counter["calls"] <= fail_count:
                    raise req.ConnectionError("transient error")

            def extract(self):
                return ExtractedProduct(
                    title="Retry Product",
                    url=self.url,
                    brand="Brand",
                    sku="SKU-RETRY",
                    price="9.99",
                    handle="retry-product",
                    images=[ProductImage(
                        source_url="https://benu.bg/media/cache/product_view_default/images/1/1.webp",
                        position=1,
                    )],
                )

        return _RetryExtractor, counter

    def test_succeeds_after_one_failure_with_retries(self, tmp_path):
        extractor_class, counter = self._make_extractor_class(fail_count=1)
        bulk = BulkExtractor(
            output_csv=str(tmp_path / "out.csv"),
            output_dir=str(tmp_path),
            delay=0,
            validate=False,
            retries=3,
        )
        bulk.extract_all(urls=["https://benu.bg/product-1"], extractor_class=extractor_class)
        assert bulk.total_extracted == 1
        assert counter["calls"] == 2  # 1 failure + 1 success

    def test_exhausts_retries_and_records_failure(self, tmp_path):
        extractor_class, counter = self._make_extractor_class(fail_count=99)
        bulk = BulkExtractor(
            output_csv=str(tmp_path / "out.csv"),
            output_dir=str(tmp_path),
            delay=0,
            validate=False,
            retries=2,
        )
        bulk.extract_all(
            urls=["https://benu.bg/product-1"],
            extractor_class=extractor_class,
            continue_on_error=True,
        )
        assert bulk.total_extracted == 0
        assert len(bulk.failed_urls) == 1
        assert counter["calls"] == 3  # 1 initial + 2 retries

    def test_no_retries_by_default(self, tmp_path):
        extractor_class, counter = self._make_extractor_class(fail_count=1)
        bulk = BulkExtractor(
            output_csv=str(tmp_path / "out.csv"),
            output_dir=str(tmp_path),
            delay=0,
            validate=False,
        )
        bulk.extract_all(
            urls=["https://benu.bg/product-1"],
            extractor_class=extractor_class,
            continue_on_error=True,
        )
        assert bulk.total_extracted == 0
        assert counter["calls"] == 1  # no retries

    def test_non_network_errors_not_retried(self, tmp_path):
        """ValueError (bad parse) should not be retried — it won't fix itself."""
        counter = {"calls": 0}

        class _ParseErrorExtractor:
            def __init__(self, url, **kwargs):
                self.url = url
                self.html = None

            def fetch(self):
                counter["calls"] += 1

            def extract(self):
                raise ValueError("No product extracted")

        bulk = BulkExtractor(
            output_csv=str(tmp_path / "out.csv"),
            output_dir=str(tmp_path),
            delay=0,
            validate=False,
            retries=3,
        )
        bulk.extract_all(
            urls=["https://benu.bg/product-1"],
            extractor_class=_ParseErrorExtractor,
            continue_on_error=True,
        )
        assert counter["calls"] == 1  # tried once, no retries


def test_no_proxies_by_default(tmp_path):
    """BulkExtractor has no proxies by default."""
    extractor = BulkExtractor(
        output_csv=str(tmp_path / "out.csv"),
        output_dir=str(tmp_path),
    )
    assert extractor.proxies is None


def test_custom_output_dir_receives_state_file(tmp_path):
    """BulkExtractor(output_dir=custom) writes extraction_state.json there, not to 'output/'."""
    custom_dir = tmp_path / "my_output"
    bulk = BulkExtractor(
        output_csv=str(tmp_path / "out.csv"),
        output_dir=str(custom_dir),
        validate=False,
    )
    bulk.extract_all(
        urls=["https://benu.bg/product-1"],
        extractor_class=FakeExtractor,
    )
    assert (custom_dir / "extraction_state.json").exists()


def test_jitter_sleep_calls_uniform_with_correct_range():
    """BulkExtractor._jitter_sleep sleeps for uniform(delay, delay*3)."""
    from unittest.mock import patch

    extractor = BulkExtractor(
        output_csv="/tmp/test_jitter.csv",
        output_dir="/tmp/test_jitter_dir",
        delay=1.0,
    )

    sleep_calls = []
    with patch("src.extraction.bulk_extractor.time.sleep", side_effect=lambda t: sleep_calls.append(t)):
        with patch("src.extraction.bulk_extractor.random.uniform", return_value=2.5) as mock_uniform:
            extractor._jitter_sleep()
            mock_uniform.assert_called_once_with(1.0, 3.0)
    assert sleep_calls == [2.5]
