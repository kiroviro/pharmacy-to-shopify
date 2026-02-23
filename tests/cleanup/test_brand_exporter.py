"""Tests for BrandExporter._split_brands_into_chunks — greedy bin-packing algorithm.

The algorithm splits brands into file-size-limited chunks while keeping
each brand's products together. Tests cover boundary conditions and edge
cases that are classic pitfalls for bin-packing.
"""

import pytest

from src.cleanup.brand_exporter import BrandExporter

FIELDNAMES = ["Title", "Vendor", "Price", "Tags"]


def _make_exporter(max_size_mb: float = 14.0) -> BrandExporter:
    """Create a BrandExporter with dummy paths (no disk access in unit tests)."""
    return BrandExporter(
        input_csv="/dev/null",
        max_size_mb=max_size_mb,
    )


def _make_brand_rows(brand: str, count: int) -> list[dict]:
    """Generate fake product rows for a brand."""
    return [
        {"Title": f"{brand} Product {i}", "Vendor": brand, "Price": "10.00", "Tags": "tag1, tag2"}
        for i in range(count)
    ]


def _make_products_by_brand(brand_sizes: dict[str, int]) -> dict[str, list[dict]]:
    """Create products_by_brand dict from {brand_name: product_count} mapping."""
    return {brand: _make_brand_rows(brand, count) for brand, count in brand_sizes.items()}


class TestSplitBrandsIntoChunks:
    """Unit tests for the greedy bin-packing algorithm."""

    def test_single_small_brand_one_chunk(self):
        exporter = _make_exporter()
        products = _make_products_by_brand({"BrandA": 5})
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=10_000)
        assert len(chunks) == 1
        assert chunks[0] == ["BrandA"]

    def test_empty_input_no_chunks(self):
        exporter = _make_exporter()
        chunks = exporter._split_brands_into_chunks({}, FIELDNAMES, max_size_bytes=10_000)
        assert chunks == []

    def test_two_brands_fit_in_one_chunk(self):
        exporter = _make_exporter()
        products = _make_products_by_brand({"BrandA": 3, "BrandB": 3})
        # Use a large max size so both fit
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=100_000)
        assert len(chunks) == 1
        assert set(chunks[0]) == {"BrandA", "BrandB"}

    def test_brands_split_when_exceeding_limit(self):
        exporter = _make_exporter()
        products = _make_products_by_brand({"BrandA": 50, "BrandB": 50})
        # Estimate actual size and set limit to force a split
        brand_a_size = exporter._estimate_brand_size(products["BrandA"], FIELDNAMES)
        header_size = exporter._get_header_size(FIELDNAMES)
        # Set limit so one brand fits but not both
        max_size = header_size + brand_a_size + 100  # just enough for one brand
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=max_size)
        assert len(chunks) == 2

    def test_oversized_brand_gets_own_chunk(self):
        """A brand larger than max_size goes into its own file."""
        exporter = _make_exporter()
        products = _make_products_by_brand({"HugeBrand": 100, "SmallBrand": 2})
        header_size = exporter._get_header_size(FIELDNAMES)
        small_size = exporter._estimate_brand_size(products["SmallBrand"], FIELDNAMES)
        # Set limit smaller than HugeBrand but larger than SmallBrand
        max_size = header_size + small_size + 100
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=max_size)
        # HugeBrand should be in its own chunk
        huge_chunk = [c for c in chunks if "HugeBrand" in c]
        assert len(huge_chunk) == 1
        assert huge_chunk[0] == ["HugeBrand"]
        # SmallBrand should be in a separate chunk
        small_chunk = [c for c in chunks if "SmallBrand" in c]
        assert len(small_chunk) == 1

    def test_all_brands_present_in_output(self):
        """No brands lost during splitting."""
        exporter = _make_exporter()
        brand_names = {f"Brand{i}": 5 for i in range(10)}
        products = _make_products_by_brand(brand_names)
        header_size = exporter._get_header_size(FIELDNAMES)
        single_brand_size = exporter._estimate_brand_size(products["Brand0"], FIELDNAMES)
        # Force ~3 brands per chunk
        max_size = header_size + single_brand_size * 3 + 100
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=max_size)
        all_output_brands = {brand for chunk in chunks for brand in chunk}
        assert all_output_brands == set(brand_names.keys())

    def test_no_brand_appears_twice(self):
        """Each brand appears in exactly one chunk."""
        exporter = _make_exporter()
        brand_names = {f"Brand{i}": 10 for i in range(8)}
        products = _make_products_by_brand(brand_names)
        header_size = exporter._get_header_size(FIELDNAMES)
        single_brand_size = exporter._estimate_brand_size(products["Brand0"], FIELDNAMES)
        max_size = header_size + single_brand_size * 3 + 100
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=max_size)
        all_brands = [brand for chunk in chunks for brand in chunk]
        assert len(all_brands) == len(set(all_brands))

    def test_largest_brands_sorted_first(self):
        """Largest brands are placed first (greedy packing)."""
        exporter = _make_exporter()
        products = _make_products_by_brand({"Small": 1, "Medium": 10, "Large": 50})
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=1_000_000)
        # All fit in one chunk; largest brand should be first
        assert chunks[0][0] == "Large"

    def test_many_tiny_brands_packed_efficiently(self):
        """Many tiny brands should be packed into few chunks."""
        exporter = _make_exporter()
        products = _make_products_by_brand({f"Tiny{i}": 1 for i in range(20)})
        header_size = exporter._get_header_size(FIELDNAMES)
        single_size = exporter._estimate_brand_size(products["Tiny0"], FIELDNAMES)
        # Fit 10 brands per chunk
        max_size = header_size + single_size * 10 + 100
        chunks = exporter._split_brands_into_chunks(products, FIELDNAMES, max_size_bytes=max_size)
        assert len(chunks) <= 3  # 20 brands / ~10 per chunk = 2-3 chunks


class TestEstimateBrandSize:
    """Size estimation for splitting decisions."""

    def test_size_proportional_to_row_count(self):
        exporter = _make_exporter()
        small = _make_brand_rows("A", 5)
        large = _make_brand_rows("A", 50)
        small_size = exporter._estimate_brand_size(small, FIELDNAMES)
        large_size = exporter._estimate_brand_size(large, FIELDNAMES)
        assert large_size > small_size
        # Roughly 10x rows should be roughly 10x size
        assert large_size / small_size == pytest.approx(10.0, rel=0.3)

    def test_empty_brand_has_zero_size(self):
        exporter = _make_exporter()
        size = exporter._estimate_brand_size([], FIELDNAMES)
        assert size == 0

    def test_header_size_positive(self):
        exporter = _make_exporter()
        size = exporter._get_header_size(FIELDNAMES)
        assert size > 0
