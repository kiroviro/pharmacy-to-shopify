"""
Unit tests for Vue.js component price extraction.

This is the PRIMARY price extraction method as of Feb 2026.
These tests ensure the most critical code path is thoroughly tested.

Covers:
1. Basic Vue component extraction (happy path)
2. Promotional product (price != discountedPrice)
3. Regular product (price == discountedPrice)
4. HTML-encoded JSON (&quot;, entities)
5. Malformed JSON (error handling)
6. Missing :product attribute (fallback behavior)
7. Multiple variants
8. EUR to BGN conversion
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for proper package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.constants import EUR_TO_BGN
from src.extraction.pharmacy_extractor import PharmacyExtractor


class TestVueComponentParsing:
    """Test Vue.js component data parsing"""

    def test_basic_vue_component_extraction(self):
        """Extract price from Vue.js <add-to-cart> component"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;price&quot;: 10.50,
                &quot;variants&quot;: [{
                    &quot;price&quot;: 10.50,
                    &quot;discountedPrice&quot;: 10.50
                }]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "10.50"
        assert float(price_bgn) == pytest.approx(10.50 * EUR_TO_BGN, rel=0.01)

    def test_promotional_product(self):
        """Extract promotional price (discounted)"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;price&quot;: 13.75,
                &quot;variants&quot;: [{
                    &quot;price&quot;: 13.75,
                    &quot;discountedPrice&quot;: 11.65,
                    &quot;discountStartDate&quot;: &quot;01.02.2026&quot;,
                    &quot;discountEndDate&quot;: &quot;28.02.2026&quot;
                }]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        # Current price should be discounted price
        price_bgn, price_eur = extractor._extract_prices()
        assert price_eur == "11.65"
        assert float(price_bgn) == pytest.approx(11.65 * EUR_TO_BGN, rel=0.01)

        # Original price should be regular price
        original_price = extractor._extract_original_price()
        assert original_price == f"{13.75 * EUR_TO_BGN:.2f}"

    def test_regular_product_no_discount(self):
        """Extract regular price (not on promotion)"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;price&quot;: 5.26,
                &quot;variants&quot;: [{
                    &quot;price&quot;: 5.26,
                    &quot;discountedPrice&quot;: 5.26
                }]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        # Current price
        price_bgn, price_eur = extractor._extract_prices()
        assert price_eur == "5.26"

        # Original price should be empty (no promotion)
        original_price = extractor._extract_original_price()
        assert original_price == ""


class TestVueHTMLEncoding:
    """Test HTML encoding handling in Vue component data"""

    def test_html_encoded_json(self):
        """Handle &quot; entities in :product attribute"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{&quot;price&quot;: 12.99, &quot;variants&quot;: [{&quot;price&quot;: 12.99, &quot;discountedPrice&quot;: 12.99}]}"></add-to-cart>
        </body>
        </html>
        '''
        # Note: Beautiful Soup auto-decodes HTML entities, but test the parsing logic
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "12.99"

    def test_html_entities_in_json(self):
        """Handle HTML entities in JSON values"""
        # Simulate how benu.bg actually encodes the data
        html = '''
        <html>
        <body>
            <add-to-cart :product="{&quot;price&quot;: 8.50, &quot;variants&quot;: [{&quot;price&quot;: 8.50, &quot;discountedPrice&quot;: 8.50}]}"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "8.50"


class TestVueErrorHandling:
    """Test error handling for malformed Vue component data"""

    def test_malformed_json(self):
        """Gracefully handle malformed JSON in :product"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{ invalid json here }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        # Should return None (triggers fallback)
        product_data = extractor._parse_vue_product_data()
        assert product_data is None

    def test_missing_product_attribute(self):
        """Handle <add-to-cart> without :product attribute"""
        html = '''
        <html>
        <body>
            <add-to-cart></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        # Should return None
        product_data = extractor._parse_vue_product_data()
        assert product_data is None

    def test_no_vue_component(self):
        """Handle page with no <add-to-cart> component"""
        html = '''
        <html>
        <body>
            <div class="product">No Vue component here</div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        # Should return None
        product_data = extractor._parse_vue_product_data()
        assert product_data is None

    def test_empty_variants_array(self):
        """Handle Vue component with empty variants array"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{&quot;price&quot;: 10.00, &quot;variants&quot;: []}"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should fail extraction (empty prices)
        assert price_eur == ""
        assert price_bgn == ""

    def test_missing_price_fields(self):
        """Handle variant with missing price/discountedPrice fields"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{&quot;variants&quot;: [{&quot;someOtherField&quot;: &quot;value&quot;}]}"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should fail gracefully
        assert price_eur == ""


class TestVueMultipleVariants:
    """Test handling of multiple variants"""

    def test_multiple_variants_takes_first(self):
        """Should use first variant when multiple exist"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;variants&quot;: [
                    {&quot;price&quot;: 15.00, &quot;discountedPrice&quot;: 15.00},
                    {&quot;price&quot;: 20.00, &quot;discountedPrice&quot;: 20.00}
                ]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should use first variant (15.00)
        assert price_eur == "15.00"


class TestVuePricingAccuracy:
    """Test price conversion accuracy"""

    def test_eur_to_bgn_conversion(self):
        """Verify EUR to BGN conversion uses correct rate"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;variants&quot;: [{&quot;price&quot;: 10.00, &quot;discountedPrice&quot;: 10.00}]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # EUR_TO_BGN = 1.95583
        expected_bgn = 10.00 * EUR_TO_BGN
        assert float(price_bgn) == pytest.approx(expected_bgn, rel=0.001)

    def test_price_precision(self):
        """Verify prices are formatted to 2 decimal places"""
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;variants&quot;: [{&quot;price&quot;: 7.123, &quot;discountedPrice&quot;: 7.123}]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should round to 2 decimals
        assert price_eur == "7.12"
        assert len(price_bgn.split('.')[1]) == 2  # 2 decimal places


class TestVueFallbackBehavior:
    """Test fallback to JSON-LD when Vue fails"""

    def test_vue_missing_falls_back_to_jsonld(self):
        """Should fall back to JSON-LD when Vue component is missing"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {"price": "20.00"}
            }
            </script>
        </head>
        <body>
            <!-- No Vue component -->
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should get JSON-LD price
        assert price_eur == "20.00"

    def test_vue_takes_priority_over_jsonld(self):
        """Vue component should take priority over JSON-LD"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {"price": "99.99"}
            }
            </script>
        </head>
        <body>
            <add-to-cart :product="{
                &quot;variants&quot;: [{&quot;price&quot;: 25.00, &quot;discountedPrice&quot;: 25.00}]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should use Vue price (25.00), not JSON-LD (99.99)
        assert price_eur == "25.00"


class TestRealWorldVueExamples:
    """Test with real-world product examples"""

    def test_benu_promotional_product(self):
        """Real promotional product from benu.bg"""
        # Based on: apivita-just-bee-clear-pochistvasht-gel-za-lice-200ml
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;price&quot;: 13.75,
                &quot;variants&quot;: [{
                    &quot;price&quot;: 13.75,
                    &quot;discountedPrice&quot;: 11.65,
                    &quot;discountStartDate&quot;: &quot;01.02.2026&quot;,
                    &quot;discountEndDate&quot;: &quot;28.02.2026&quot;
                }]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        price_bgn, price_eur = extractor._extract_prices()
        original_price = extractor._extract_original_price()

        # Current price (discounted)
        assert price_eur == "11.65"
        assert float(price_bgn) == pytest.approx(22.79, abs=0.01)

        # Original price (before discount)
        assert float(original_price) == pytest.approx(26.89, abs=0.01)

    def test_benu_regular_product(self):
        """Real regular product from benu.bg"""
        # Based on: aroma-izmiven-gel-zdrave-akne-stop-v-glen-150ml
        html = '''
        <html>
        <body>
            <add-to-cart :product="{
                &quot;price&quot;: 5.26,
                &quot;variants&quot;: [{
                    &quot;price&quot;: 5.26,
                    &quot;discountedPrice&quot;: 5.26
                }]
            }"></add-to-cart>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)

        price_bgn, price_eur = extractor._extract_prices()
        original_price = extractor._extract_original_price()

        # Current price (regular)
        assert price_eur == "5.26"
        assert float(price_bgn) == pytest.approx(10.29, abs=0.01)

        # No original price (not on promotion)
        assert original_price == ""


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
