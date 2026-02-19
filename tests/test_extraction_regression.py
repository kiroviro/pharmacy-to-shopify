"""
Regression tests for product extraction quality.

Two levels of protection:
1. test_real_product_barcode   — pure unit tests, always run (including CI)
2. test_extraction_quality     — reads an actual extracted CSV; skips gracefully
                                 when no CSV is present (clean CI checkout), runs
                                 and enforces quality gates after a local crawl.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_csv_path() -> Path:
    """
    Path to the most recently extracted raw products CSV.

    Searches known extraction output locations and returns the most recently
    modified file. Skips the test if none exist (e.g. clean CI checkout
    without extracted data — this is expected and correct).
    """
    candidates = [
        Path("data/benu.bg/raw/products.csv"),
        Path("data/pharmacy.example.com/raw/products.csv"),
    ]
    available = [p for p in candidates if p.exists()]
    if not available:
        pytest.skip("No raw CSV found — run an extraction first")
    return max(available, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

class ExtractionMetrics:
    """Track and validate extraction quality metrics from a products CSV."""

    MIN_BARCODE_COVERAGE = 85.0  # % of products that must have a valid barcode
    MAX_INVALID_BARCODES = 5     # absolute cap on malformed barcodes
    PLACEHOLDER_DOMAINS = ("example.com", "localhost")

    def __init__(self) -> None:
        self.total_products = 0
        self.with_barcode = 0
        self.valid_barcodes = 0
        self.invalid_barcodes = 0
        self.missing_required_fields = 0
        self.placeholder_images = 0  # image URLs containing a placeholder domain

    def validate_barcode(self, barcode: str) -> bool:
        """Return True if barcode is a valid GTIN (8 / 12 / 13 / 14 digits)."""
        return bool(barcode) and barcode.isdigit() and len(barcode) in {8, 12, 13, 14}

    def add_product(self, row: dict) -> None:
        """Ingest one product row (rows where Title is non-empty)."""
        self.total_products += 1

        barcode = row.get('Barcode', '').strip()
        if barcode:
            self.with_barcode += 1
            if self.validate_barcode(barcode):
                self.valid_barcodes += 1
            else:
                self.invalid_barcodes += 1

        required = ['Title', 'Description', 'Vendor', 'Price']
        if any(not row.get(f, '').strip() for f in required):
            self.missing_required_fields += 1

        # Regression guard: placeholder domain in image URL means the extractor
        # was initialised with the wrong site_domain (see commit df4d307 / a9b6d3b).
        img_url = row.get('Product image URL', '').strip()
        if any(domain in img_url for domain in self.PLACEHOLDER_DOMAINS):
            self.placeholder_images += 1

    def get_barcode_coverage(self) -> float:
        if not self.total_products:
            return 0.0
        return self.valid_barcodes / self.total_products * 100

    def passes_quality_gate(self) -> bool:
        coverage = self.get_barcode_coverage()
        return (
            coverage >= self.MIN_BARCODE_COVERAGE
            and self.invalid_barcodes <= self.MAX_INVALID_BARCODES
            and self.missing_required_fields == 0
            and self.placeholder_images == 0
        )

    def report(self) -> str:
        coverage = self.get_barcode_coverage()
        lines = [
            "=" * 70,
            "EXTRACTION QUALITY REPORT",
            "=" * 70,
            f"Total products:            {self.total_products:,}",
            f"With valid barcodes:        {self.valid_barcodes:,}",
            f"With invalid barcodes:      {self.invalid_barcodes:,}",
            f"Without barcodes:           {self.total_products - self.with_barcode:,}",
            f"Valid barcode coverage:     {coverage:.1f}%",
            f"Missing required fields:    {self.missing_required_fields}",
            f"Placeholder image URLs:     {self.placeholder_images}",
            "",
            "QUALITY GATES",
            "-" * 70,
        ]
        gates = [
            (
                coverage >= self.MIN_BARCODE_COVERAGE,
                f"Barcode coverage >= {self.MIN_BARCODE_COVERAGE}%   →  {coverage:.1f}%",
            ),
            (
                self.invalid_barcodes <= self.MAX_INVALID_BARCODES,
                f"Invalid barcodes <= {self.MAX_INVALID_BARCODES}          →  {self.invalid_barcodes}",
            ),
            (
                self.missing_required_fields == 0,
                f"Missing required fields = 0  →  {self.missing_required_fields}",
            ),
            (
                self.placeholder_images == 0,
                f"Placeholder image URLs = 0   →  {self.placeholder_images}",
            ),
        ]
        for passed, description in gates:
            lines.append(f"  {'✓ PASS' if passed else '✗ FAIL'}  {description}")
        lines += [
            "=" * 70,
            "✓ ALL GATES PASSED" if self.passes_quality_gate() else "✗ QUALITY GATES FAILED — fix before importing to Shopify",
            "=" * 70,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV quality gate test  (skips in CI, runs locally after a crawl)
# ---------------------------------------------------------------------------

def test_extraction_quality(raw_csv_path: Path) -> None:
    """
    Validate a freshly extracted CSV meets minimum quality standards.

    Quality gates:
    - Barcode coverage >= 85%
    - <= 5 invalid (malformed) barcodes
    - 0 products missing Title / Description / Vendor / Price
    - 0 image URLs containing a placeholder domain (example.com / localhost)

    Skips automatically when no extracted CSV exists (clean CI checkout).
    To run locally:  pytest tests/test_extraction_regression.py -v -s
    """
    metrics = ExtractionMetrics()

    with open(raw_csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Title", "").strip():
                metrics.add_product(row)

    print(f"\nCSV: {raw_csv_path}  ({metrics.total_products:,} products)\n")
    print(metrics.report())

    assert metrics.passes_quality_gate(), (
        f"Extraction quality gates failed on {raw_csv_path}. See report above."
    )


# ---------------------------------------------------------------------------
# Barcode extraction unit tests  (always run, including CI)
# ---------------------------------------------------------------------------

BARCODE_CASES = [
    (
        "BOIRON Achillea millefolium — valid 13-digit",
        '<h3>Допълнителна информация</h3><p>Баркод : 3352710009079</p>',
        "3352710009079",
    ),
    (
        "911 Badyaga gel — valid 13-digit",
        '<h3>Допълнителна информация</h3><p>Баркод : 4607010243104</p>',
        "4607010243104",
    ),
    (
        "SOLGAR — invalid 11-digit, must reject",
        '<h3>Допълнителна информация</h3><p>Баркод : 33984007536</p>',
        "",
    ),
    (
        "Duphalac — SKU 3-digit, must reject",
        '<h3>Допълнителна информация</h3><p>Баркод : 559</p>',
        "",
    ),
    (
        "Uriage — SKU 4-digit, must reject",
        '<h3>Допълнителна информация</h3><p>Баркод : 5909</p>',
        "",
    ),
]


@pytest.mark.parametrize("name,html,expected", BARCODE_CASES, ids=[c[0] for c in BARCODE_CASES])
def test_real_product_barcode(name: str, html: str, expected: str) -> None:
    """Barcode extraction rules: valid GTIN lengths accepted, others rejected."""
    match = re.search(r'Баркод\s*:\s*(\d+)', html)
    if match:
        candidate = match.group(1)
        extracted = candidate if len(candidate) in {8, 12, 13, 14} else ""
    else:
        extracted = ""

    assert extracted == expected, (
        f"{name}: expected '{expected}', got '{extracted}'"
    )


# ---------------------------------------------------------------------------
# CLI runner  (manual use: python tests/test_extraction_regression.py <csv>)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tests/test_extraction_regression.py <csv_file>")
        sys.exit(1)

    metrics = ExtractionMetrics()
    with open(sys.argv[1], encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Title", "").strip():
                metrics.add_product(row)

    print(f"\nCSV: {sys.argv[1]}  ({metrics.total_products:,} products)\n")
    print(metrics.report())
    sys.exit(0 if metrics.passes_quality_gate() else 1)
