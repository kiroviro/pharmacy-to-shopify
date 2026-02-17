"""
Barcode validation tests - ensures we only accept valid GTINs.

Tests validate the CRITICAL distinction:
- GTIN/EAN/Barcode: Global standard (8/12/13/14 digits) ✓ ACCEPT
- SKU: Internal retailer code (any length) ✗ REJECT
"""

import re


def is_valid_gtin(barcode: str) -> bool:
    """
    Validate if a barcode is a valid GTIN format.

    Valid GTINs:
    - EAN-8: 8 digits
    - UPC-A: 12 digits
    - EAN-13: 13 digits
    - GTIN-14: 14 digits

    Invalid:
    - SKUs (3-7 digits)
    - Truncated GTINs (9-11 digits)
    - Internal IDs (15+ digits)
    """
    if not barcode:
        return False

    # Must be digits only
    if not barcode.isdigit():
        return False

    # Must be exactly 8, 12, 13, or 14 digits
    return len(barcode) in [8, 12, 13, 14]


# Test cases: (barcode, expected_valid, description)
TEST_CASES = [
    # Valid GTINs - SHOULD ACCEPT
    ("12345678", True, "EAN-8: 8 digits"),
    ("123456789012", True, "UPC-A: 12 digits"),
    ("3352710009079", True, "EAN-13: 13 digits (BOIRON product)"),
    ("4607010243104", True, "EAN-13: 13 digits (911 product)"),
    ("12345678901234", True, "GTIN-14: 14 digits"),

    # SKUs - SHOULD REJECT
    ("559", False, "SKU: 3 digits (Duphalac)"),
    ("5909", False, "SKU: 4 digits (Uriage)"),
    ("25145", False, "SKU: 5 digits (Uriage)"),
    ("11700", False, "SKU: 5 digits (Mask)"),
    ("890601", False, "SKU: 6 digits"),
    ("9476945", False, "SKU: 7 digits"),

    # Invalid/Truncated GTINs - SHOULD REJECT
    ("123456789", False, "Invalid: 9 digits"),
    ("1234567890", False, "Invalid: 10 digits"),
    ("33984007536", False, "Invalid: 11 digits (SOLGAR - truncated)"),

    # Internal IDs - SHOULD REJECT
    ("202501240000001", False, "Internal ID: 15 digits (benu.bg package ID)"),

    # Edge cases
    ("", False, "Empty string"),
    ("abc123", False, "Contains letters"),
    ("12-34-56", False, "Contains hyphens"),
]


def test_all_cases():
    """Run all validation tests"""
    passed = 0
    failed = 0

    print("=" * 80)
    print("BARCODE VALIDATION TESTS")
    print("=" * 80)
    print()

    for barcode, expected_valid, description in TEST_CASES:
        result = is_valid_gtin(barcode)
        status = "✓ PASS" if result == expected_valid else "✗ FAIL"

        if result == expected_valid:
            passed += 1
        else:
            failed += 1

        expected_str = "ACCEPT" if expected_valid else "REJECT"
        actual_str = "ACCEPT" if result else "REJECT"

        print(f"{status} | {description:40} | Barcode: {barcode:20} | Expected: {expected_str:6} | Got: {actual_str:6}")

    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_all_cases()
    exit(0 if success else 1)
