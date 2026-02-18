"""
Unit tests for barcode extraction functionality.

Ensures that barcode extraction:
1. Accepts valid GTINs (8, 12, 13, 14 digits)
2. Rejects invalid barcodes (3-7, 9-11, 15+ digits)
3. Extracts from multiple sources (JSON-LD, meta tags, text)
4. Handles edge cases (HTML entities, whitespace, etc.)
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for proper package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.pharmacy_extractor import PharmacyExtractor


class TestBarcodeValidation:
    """Test barcode validation logic"""

    def test_valid_ean8(self):
        """Accept 8-digit EAN-8 barcodes"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 12345678</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "12345678"

    def test_valid_upc_a(self):
        """Accept 12-digit UPC-A barcodes"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 123456789012</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "123456789012"

    def test_valid_ean13(self):
        """Accept 13-digit EAN-13 barcodes"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 3352710009079</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_valid_gtin14(self):
        """Accept 14-digit GTIN-14 barcodes"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 12345678901234</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "12345678901234"

    def test_reject_3_digits(self):
        """Reject 3-digit SKUs"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 559</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == ""

    def test_reject_4_digits(self):
        """Reject 4-digit SKUs"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 5909</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == ""

    def test_reject_5_digits(self):
        """Reject 5-digit SKUs"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 25145</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == ""

    def test_reject_11_digits(self):
        """Reject 11-digit codes (common SOLGAR issue)"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 33984007536</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == ""

    def test_reject_15_digits(self):
        """Reject 15-digit internal IDs"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод : 202501240000001</p></body></html>'
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == ""


class TestBarcodeExtractionSources:
    """Test barcode extraction from different sources"""

    def test_extract_from_json_ld(self):
        """Extract from JSON-LD structured data"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "http://schema.org",
                "@type": "Product",
                "name": "Test Product",
                "gtin13": "3352710009079"
            }
            </script>
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_extract_from_meta_tag(self):
        """Extract from meta tags"""
        html = '''
        <html>
        <head>
            <meta property="product:gtin" content="3600523908639" />
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "3600523908639"

    def test_extract_from_additional_info_section(self):
        """Extract from Допълнителна информация section"""
        html = '''
        <html>
        <body>
            <h3>Допълнителна информация</h3>
            <p>Производител : BOIRON</p>
            <p>Баркод : 3352710009079</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_source_priority_json_ld_wins(self):
        """JSON-LD should take priority over meta tags"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"gtin13": "1111111111111"}
            </script>
            <meta property="product:gtin" content="2222222222222" />
        </head>
        <body>
            <h3>Допълнителна информация</h3>
            <p>Баркод : 3333333333333</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com")
        extractor.load_html(html)
        barcode = extractor._extract_barcode()
        assert barcode == "1111111111111"


class TestBarcodeEdgeCases:
    """Test edge cases and data cleaning"""

    def test_barcode_with_whitespace(self):
        """Handle barcodes with whitespace"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод :   3352710009079  </p></body></html>'
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_ean_label(self):
        """Accept EAN: label"""
        html = '<html><body><h3>Допълнителна информация</h3><p>EAN : 3352710009079</p></body></html>'
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_gtin_label(self):
        """Accept GTIN: label"""
        html = '<html><body><h3>Допълнителна информация</h3><p>GTIN : 3352710009079</p></body></html>'
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"

    def test_no_barcode_returns_empty(self):
        """Return empty string when no barcode found"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Производител : BOIRON</p></body></html>'
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == ""

    def test_html_entities_in_barcode(self):
        """Handle HTML entities (though unlikely in barcodes)"""
        html = '<html><body><h3>Допълнителна информация</h3><p>Баркод&nbsp;:&nbsp;3352710009079</p></body></html>'
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        # Should still extract correctly
        assert len(barcode) == 13 or barcode == "3352710009079"


class TestRealWorldExamples:
    """Test with real examples from benu.bg"""

    def test_boiron_product(self):
        """Real BOIRON product (has valid 13-digit barcode)"""
        html = '''
        <html>
        <body>
            <h3>Допълнителна информация</h3>
            <p>Производител : BOIRON</p>
            <p>Баркод : 3352710009079</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == "3352710009079"
        assert len(barcode) == 13

    def test_solgar_product_invalid(self):
        """Real SOLGAR product (has invalid 11-digit code - should reject)"""
        html = '''
        <html>
        <body>
            <h3>Допълнителна информация</h3>
            <p>Производител : SOLGAR</p>
            <p>Баркод : 33984007536</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == ""  # Should reject 11-digit code

    def test_911_product(self):
        """Real 911 brand product (has valid barcode)"""
        html = '''
        <html>
        <body>
            <h3>Допълнителна информация</h3>
            <p>Производител : TWINS INC</p>
            <p>Баркод : 4607010243104</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://example.com", html)
        barcode = extractor._extract_barcode()
        assert barcode == "4607010243104"
        assert len(barcode) == 13


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
