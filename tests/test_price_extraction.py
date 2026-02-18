"""
Unit tests for price extraction functionality.

Ensures that price extraction:
1. Prioritizes JSON-LD structured data (most reliable)
2. Falls back to CSS selectors correctly
3. Handles promotional pricing (old-price vs new-price)
4. Avoids false matches (shipping thresholds, promo text)
5. Converts EUR ↔ BGN correctly

These tests prevent regression of the price extraction bug that caused
87% of products to have incorrect prices (fixed 2026-02-17).
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for proper package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.constants import EUR_TO_BGN
from src.extraction.pharmacy_extractor import PharmacyExtractor


class TestPriceExtractionJsonLD:
    """Test JSON-LD price extraction (primary source)"""

    def test_json_ld_price_extraction(self):
        """Extract price from JSON-LD Product schema"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "http://schema.org",
                "@type": "Product",
                "name": "Test Product",
                "offers": {
                    "@type": "Offer",
                    "price": "10.48",
                    "priceCurrency": "EUR"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "10.48"
        assert float(price_bgn) == pytest.approx(10.48 * EUR_TO_BGN, rel=0.01)

    def test_json_ld_offers_array(self):
        """Handle offers as array (multiple offers)"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": [
                    {"@type": "Offer", "price": "25.99", "priceCurrency": "EUR"},
                    {"@type": "Offer", "price": "30.00", "priceCurrency": "EUR"}
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should take first offer
        assert price_eur == "25.99"

    def test_json_ld_comma_decimal(self):
        """Handle comma as decimal separator"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "12,50"}}
            </script>
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "12.50"

    def test_json_ld_takes_priority_over_css(self):
        """JSON-LD should be used even if CSS elements have different price"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "20.00"}}
            </script>
        </head>
        <body>
            <div class="product-prices">
                <span class="price">99.99 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # JSON-LD price should win
        assert price_eur == "20.00"


class TestPriceExtractionCSSFallback:
    """Test CSS selector fallback when JSON-LD is missing"""

    def test_product_prices_selector(self):
        """Extract from .product-prices .price selector (HTML fallback)"""
        html = '''
        <html>
        <body>
            <div class="product-prices">
                <span class="price">19.99 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should extract from .product-prices .price:not(.old-price) selector
        assert price_eur == "19.99"

    def test_regular_price_selector(self):
        """Extract from .price when no promotion"""
        html = '''
        <html>
        <body>
            <div class="product-prices">
                <span class="price">15.50 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "15.50"

    def test_price_selector_without_class(self):
        """Extract from .price selector (HTML fallback)"""
        html = '''
        <html>
        <body>
            <div class="product-prices">
                <span class="price">24.50 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Code extracts EUR and converts to BGN
        assert price_eur == "24.50"
        assert float(price_bgn) == pytest.approx(24.50 * EUR_TO_BGN, rel=0.01)


class TestPriceExtractionEdgeCases:
    """Test edge cases and potential false matches"""

    def test_ignore_shipping_threshold(self):
        """Should NOT match shipping threshold text"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "5.99"}}
            </script>
        </head>
        <body>
            <div class="free-shipping-banner">
                Безплатна доставка за поръчки над 60 лв
            </div>
            <div class="product-prices">
                <span class="price">5.99 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should get actual price, not 60 from shipping text
        assert price_eur == "5.99"
        assert float(price_bgn) < 20  # Not 60 лв

    def test_ignore_promo_text(self):
        """Should NOT match promotional text amounts"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "12.00"}}
            </script>
        </head>
        <body>
            <div class="promo-banner">
                Получете подарък при покупка над 100 лв!
            </div>
            <div class="product-prices">
                <span class="price">12.00 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "12.00"
        assert float(price_bgn) < 30  # Not 100 лв

    def test_no_price_returns_empty(self):
        """Return empty strings when no price found"""
        html = '''
        <html>
        <body>
            <h1>Product Without Price</h1>
            <p>Description only, no price info</p>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_bgn == ""
        assert price_eur == ""

    def test_malformed_json_ld_fallback(self):
        """Fall back to CSS when JSON-LD is malformed"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {invalid json here}
            </script>
        </head>
        <body>
            <div class="product-prices">
                <span class="price">7.50 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should fall back to CSS selector
        assert price_eur == "7.50"


class TestRealWorldPriceExamples:
    """Test with real benu.bg HTML patterns"""

    def test_boiron_homeopathic(self):
        """Real BOIRON homeopathic product (standard price)"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Bellis perennis 9 ch",
                "offers": {
                    "@type": "Offer",
                    "price": 2.60,
                    "priceCurrency": "EUR",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </head>
        <body>
            <div class="product-info">
                <div class="product-prices">
                    <span class="price">2.60 € / 5.09 лв</span>
                </div>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/bellis-perennis-9-ch")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "2.60"
        assert float(price_bgn) == pytest.approx(5.09, rel=0.01)

    def test_promotional_product(self):
        """Product on promotion (has old-price and new-price)"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "Promo Product",
                "offers": {"price": "15.99", "priceCurrency": "EUR"}
            }
            </script>
        </head>
        <body>
            <div class="product-prices">
                <span class="old-price">24.99 €</span>
                <span class="new-price">15.99 €</span>
                <span class="discount">-36%</span>
            </div>
            <div class="promo-info">
                Промоцията е валидна за периода: 01.02.2026 - 28.02.2026
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/promo-product")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should get current selling price (new-price), not original
        assert price_eur == "15.99"
        assert float(price_eur) < 20  # Not 24.99

    def test_complex_page_with_distractions(self):
        """Complex page with many price-like numbers"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "8.84"}}
            </script>
        </head>
        <body>
            <header>
                <div class="free-shipping">Безплатна доставка над 30.68 € / 60 лв</div>
            </header>
            <div class="promo-banner">
                Подарък при поръчка над 51.13 € / 100 лв!
            </div>
            <div class="product-info">
                <h1>InoPharm Pure elements Серум 6% Фукогел</h1>
                <div class="product-prices">
                    <span class="price">8.84 € / 17.29 лв</span>
                </div>
                <div class="unit-price">11.73 € / 100мл</div>
            </div>
            <div class="similar-products">
                <span class="price">12.50 €</span>
                <span class="price">45.00 €</span>
            </div>
        </body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/inopharm-serum")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        # Should get exact product price from JSON-LD, not distractions
        assert price_eur == "8.84"
        assert float(price_bgn) == pytest.approx(17.29, rel=0.01)


class TestPriceConversion:
    """Test EUR to BGN conversion accuracy"""

    def test_eur_to_bgn_conversion(self):
        """Verify EUR to BGN conversion uses correct rate"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Product", "offers": {"price": "10.00"}}
            </script>
        </head>
        <body></body>
        </html>
        '''
        extractor = PharmacyExtractor("https://benu.bg/test")
        extractor.load_html(html)
        price_bgn, price_eur = extractor._extract_prices()

        assert price_eur == "10.00"
        # EUR_TO_BGN = 1.95583
        assert float(price_bgn) == pytest.approx(19.56, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
