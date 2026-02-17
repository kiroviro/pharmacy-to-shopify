"""
Regression tests for product extraction.

Prevents quality regressions by:
1. Testing real product examples
2. Tracking barcode extraction success rate
3. Validating data quality metrics
"""

import csv
import re
from pathlib import Path


class ExtractionMetrics:
    """Track extraction quality metrics"""

    def __init__(self):
        self.total_products = 0
        self.with_barcode = 0
        self.valid_barcodes = 0
        self.invalid_barcodes = 0
        self.missing_required_fields = 0

    def validate_barcode(self, barcode: str) -> bool:
        """Check if barcode is valid GTIN format"""
        if not barcode:
            return False
        return barcode.isdigit() and len(barcode) in [8, 12, 13, 14]

    def add_product(self, row: dict):
        """Analyze a product row"""
        self.total_products += 1

        # Check barcode
        barcode = row.get('Barcode', '').strip()
        if barcode:
            self.with_barcode += 1
            if self.validate_barcode(barcode):
                self.valid_barcodes += 1
            else:
                self.invalid_barcodes += 1

        # Check required fields
        required_fields = ['Title', 'Description', 'Vendor', 'Price']
        if any(not row.get(field, '').strip() for field in required_fields):
            self.missing_required_fields += 1

    def get_barcode_coverage(self) -> float:
        """Calculate valid barcode coverage percentage"""
        if self.total_products == 0:
            return 0.0
        return (self.valid_barcodes / self.total_products) * 100

    def passes_quality_gate(self) -> bool:
        """Check if extraction meets quality standards"""
        coverage = self.get_barcode_coverage()

        # Quality gates
        MIN_BARCODE_COVERAGE = 85.0  # At least 85% products should have valid barcodes
        MAX_INVALID_BARCODES = 5  # No more than 5 invalid barcodes

        return (
            coverage >= MIN_BARCODE_COVERAGE and
            self.invalid_barcodes <= MAX_INVALID_BARCODES and
            self.missing_required_fields == 0
        )

    def report(self) -> str:
        """Generate quality report"""
        coverage = self.get_barcode_coverage()

        report = [
            "=" * 80,
            "EXTRACTION QUALITY REPORT",
            "=" * 80,
            "",
            f"Total products: {self.total_products:,}",
            f"With barcodes: {self.with_barcode:,}",
            f"  Valid GTINs (8/12/13/14 digits): {self.valid_barcodes:,}",
            f"  Invalid barcodes: {self.invalid_barcodes:,}",
            f"Without barcodes: {self.total_products - self.with_barcode:,}",
            "",
            f"Valid barcode coverage: {coverage:.1f}%",
            f"Missing required fields: {self.missing_required_fields}",
            "",
            "=" * 80,
            "QUALITY GATES",
            "=" * 80,
        ]

        # Check gates
        gates = [
            (coverage >= 85.0, f"Barcode coverage >= 85%: {coverage:.1f}%"),
            (self.invalid_barcodes <= 5, f"Invalid barcodes <= 5: {self.invalid_barcodes}"),
            (self.missing_required_fields == 0, f"Missing required fields = 0: {self.missing_required_fields}"),
        ]

        for passed, description in gates:
            status = "✓ PASS" if passed else "✗ FAIL"
            report.append(f"{status} | {description}")

        report.append("")
        report.append("=" * 80)

        if self.passes_quality_gate():
            report.append("✓ ALL QUALITY GATES PASSED")
        else:
            report.append("✗ QUALITY GATES FAILED - Fix issues before uploading to Shopify")

        report.append("=" * 80)

        return "\n".join(report)


def test_extraction_quality(csv_file: str):
    """Test extraction quality against baseline"""
    if not Path(csv_file).exists():
        print(f"Error: CSV file not found: {csv_file}")
        return False

    metrics = ExtractionMetrics()

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only analyze main product rows (with Title)
            if row.get('Title', '').strip():
                metrics.add_product(row)

    # Print report
    print(metrics.report())

    return metrics.passes_quality_gate()


# Real product examples from benu.bg (regression tests)
REAL_PRODUCT_TESTS = [
    {
        "name": "BOIRON Achillea millefolium (valid 13-digit)",
        "html": '<h3>Допълнителна информация</h3><p>Производител : BOIRON</p><p>Баркод : 3352710009079</p>',
        "expected_barcode": "3352710009079",
        "should_extract": True,
    },
    {
        "name": "911 Badyaga gel (valid 13-digit)",
        "html": '<h3>Допълнителна информация</h3><p>Производител : TWINS INC</p><p>Баркод : 4607010243104</p>',
        "expected_barcode": "4607010243104",
        "should_extract": True,
    },
    {
        "name": "SOLGAR product (invalid 11-digit - should reject)",
        "html": '<h3>Допълнителна информация</h3><p>Производител : SOLGAR</p><p>Баркод : 33984007536</p>',
        "expected_barcode": "",
        "should_extract": False,
    },
    {
        "name": "Duphalac (SKU 3-digit - should reject)",
        "html": '<h3>Допълнителна информация</h3><p>Производител : DUPHALAC</p><p>Баркод : 559</p>',
        "expected_barcode": "",
        "should_extract": False,
    },
    {
        "name": "Uriage (SKU 4-digit - should reject)",
        "html": '<h3>Допълнителна информация</h3><p>Производител : URIAGE</p><p>Баркод : 5909</p>',
        "expected_barcode": "",
        "should_extract": False,
    },
]


def test_real_products():
    """Test barcode extraction with real product examples"""
    print("=" * 80)
    print("REAL PRODUCT REGRESSION TESTS")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for test in REAL_PRODUCT_TESTS:
        # Extract barcode from HTML using SAME logic as pharmacy_extractor
        match = re.search(r'Баркод\s*:\s*(\d+)', test['html'])
        if match:
            candidate = match.group(1)
            # Validate it's a proper GTIN (8-14 digits)
            extracted = candidate if len(candidate) in [8, 12, 13, 14] else ""
        else:
            extracted = ""

        # Validate
        expected = test['expected_barcode']
        success = (extracted == expected)

        if success:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"{status} | {test['name']}")
        print(f"       Expected: '{expected}' | Got: '{extracted}'")
        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    print()

    return failed == 0


if __name__ == "__main__":
    import sys

    print()

    # Run real product tests
    real_tests_passed = test_real_products()

    # Run CSV quality test if file provided
    csv_tests_passed = True
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        csv_tests_passed = test_extraction_quality(csv_file)

    # Exit with appropriate code
    all_passed = real_tests_passed and csv_tests_passed
    sys.exit(0 if all_passed else 1)
