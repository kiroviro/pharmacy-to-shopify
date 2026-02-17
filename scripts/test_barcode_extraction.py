#!/usr/bin/env python3
"""
Test Improved Barcode Extraction

Quick test script to verify the enhanced barcode extraction logic.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.pharmacy_extractor import PharmacyExtractor  # noqa: I001

def test_barcode_extraction():
    """Test barcode extraction with sample HTML."""

    # Sample HTML with barcode in different locations
    test_cases = [
        {
            "name": "JSON-LD barcode",
            "html": """
            <html>
            <head>
                <script type="application/ld+json">
                {
                    "@type": "Product",
                    "name": "Test Product",
                    "gtin13": "1234567890123"
                }
                </script>
            </head>
            <body><h1>Test Product</h1></body>
            </html>
            """,
            "expected": "1234567890123"
        },
        {
            "name": "Допълнителна информация section",
            "html": """
            <html>
            <body>
                <h1>Test Product 2</h1>
                <div>Допълнителна информация</div>
                <p>Баркод : 9876543210987</p>
            </body>
            </html>
            """,
            "expected": "9876543210987"
        },
        {
            "name": "No barcode",
            "html": """
            <html>
            <body>
                <h1>Test Product 3</h1>
                <p>Some description text</p>
            </body>
            </html>
            """,
            "expected": ""
        },
        {
            "name": "Barcode with spaces",
            "html": """
            <html>
            <body>
                <h1>Test Product 4</h1>
                <div>Допълнителна информация</div>
                <p>Баркод : 123 456 789 0123</p>
            </body>
            </html>
            """,
            "expected": "1234567890123"
        }
    ]

    print("Testing improved barcode extraction...")
    print("=" * 60)

    passed = 0
    failed = 0

    for test in test_cases:
        extractor = PharmacyExtractor(url="https://test.com/product", site_domain="test.com")
        extractor.load_html(test["html"])

        result = extractor._extract_barcode()

        if result == test["expected"]:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"{status} - {test['name']}")
        print(f"   Expected: '{test['expected']}'")
        print(f"   Got:      '{result}'")
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print()

    if failed == 0:
        print("SUCCESS! All tests passed.")
        return 0
    else:
        print("FAILURE! Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test_barcode_extraction())
