"""Integration tests for PharmacyExtractor.extract() — the public assembly method.

All existing tests target private methods (_extract_prices, _extract_barcode, etc.).
These tests verify the full extraction pipeline wires everything together correctly:
fields are populated, the returned ExtractedProduct has the right structure, and
nothing breaks in the assembly logic.
"""


from src.extraction.pharmacy_extractor import PharmacyExtractor
from src.models.product import ExtractedProduct

# Minimal benu.bg-style HTML with all three data sources
PRODUCT_HTML = '''
<!DOCTYPE html>
<html lang="bg">
<head>
    <title>TestBrand Витамин C 500mg таблетки - benu.bg</title>
</head>
<body>
    <nav class="breadcrumbs">
        <a href="/">Начало</a>
        <a href="/vitamini">Витамини и добавки</a>
        <a href="/vitamini/vitamin-c">Витамин C</a>
    </nav>

    <h1 itemprop="name">TestBrand Витамин C 500mg таблетки</h1>

    <add-to-cart :product="{
        &quot;id&quot;: 12345,
        &quot;name&quot;: &quot;TestBrand Витамин C 500mg таблетки&quot;,
        &quot;price&quot;: 6.39,
        &quot;sku&quot;: &quot;TST-VIT-001&quot;,
        &quot;variants&quot;: [{
            &quot;id&quot;: 99999,
            &quot;price&quot;: 6.39,
            &quot;discountedPrice&quot;: 6.39,
            &quot;sku&quot;: &quot;TST-VIT-001&quot;
        }]
    }"></add-to-cart>

    <div itemprop="description">
        <ul>
            <li>Подпомага имунната система</li>
            <li>Съдържа витамин С и цинк</li>
        </ul>
    </div>

    <table class="additional-attributes">
        <tr><th>Марка</th><td>TestBrand</td></tr>
        <tr><th>Тегло</th><td>250 g</td></tr>
    </table>

    <div class="stock" itemprop="availability">В наличност</div>

    <div class="tab-group">
        <div class="js-tab-content" data-tab-title="Какво представлява">
            Витамин С е есенциален за имунната система.
        </div>
        <div class="js-tab-content" data-tab-title="Активни съставки">
            Витамин C 500mg, Цинк 10mg
        </div>
        <div class="js-tab-content" data-tab-title="Дозировка и начин на употреба">
            Приемайте по 1 таблетка дневно.
        </div>
        <div class="js-tab-content" data-tab-title="Допълнителна информация">
            Баркод: 3800123456789
        </div>
    </div>

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "TestBrand Витамин C 500mg таблетки",
        "brand": {"@type": "Brand", "name": "TestBrand"},
        "sku": "TST-VIT-001",
        "gtin13": "3800123456789",
        "offers": {
            "@type": "Offer",
            "price": "6.39",
            "priceCurrency": "EUR",
            "availability": "https://schema.org/InStock"
        },
        "image": ["/uploads/images/products/test/vitamin-c.jpg"]
    }
    </script>

    <script>
        var someConfig = {
            "initialImages": [
                {
                    "img": "https://benu.bg/media/cache/product_view_default/images/products/test/vitamin-c.jpg",
                    "full": "https://benu.bg/uploads/images/products/test/vitamin-c.jpg",
                    "thumb": "https://benu.bg/media/cache/product_thumb/images/products/test/vitamin-c.jpg",
                    "caption": "TestBrand Витамин C"
                }
            ]
        };
    </script>
</body>
</html>
'''

# Minimal HTML — only Vue component, bare minimum for extract() to succeed
MINIMAL_HTML = '''
<html><body>
    <h1 itemprop="name">Simple Product 100ml</h1>
    <add-to-cart :product="{
        &quot;price&quot;: 3.50,
        &quot;sku&quot;: &quot;SMP-001&quot;,
        &quot;variants&quot;: [{
            &quot;price&quot;: 3.50,
            &quot;discountedPrice&quot;: 3.50,
            &quot;sku&quot;: &quot;SMP-001&quot;
        }]
    }"></add-to-cart>
</body></html>
'''


class TestExtractReturnsProduct:
    """extract() returns a properly populated ExtractedProduct."""

    def test_returns_extracted_product(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()
        assert isinstance(product, ExtractedProduct)

    def test_core_fields_populated(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert "Витамин C 500mg" in product.title
        assert product.url == "https://benu.bg/test-product"
        assert product.sku == "TST-VIT-001"
        assert product.brand == "TestBrand"

    def test_price_from_vue_component(self):
        """Price always comes from Vue data (primary source)."""
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.price_eur == "6.39"
        assert float(product.price) > 0  # BGN price computed from EUR

    def test_original_price_always_empty(self):
        """Business rule: no compare-at price, always sell at regular price."""
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.original_price == ""

    def test_handle_generated(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.handle
        assert " " not in product.handle  # handles are URL-safe
        assert product.handle == product.handle.lower()  # lowercase

    def test_barcode_extracted(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.barcode == "3800123456789"

    def test_categories_from_breadcrumbs(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert len(product.category_path) > 0
        assert product.tags  # tags derived from categories

    def test_images_extracted(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert len(product.images) >= 1
        assert product.images[0].source_url

    def test_seo_fields_generated(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.seo_title
        assert product.seo_description

    def test_description_html_generated(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.description  # non-empty HTML description


class TestExtractMinimalInput:
    """extract() handles minimal HTML gracefully."""

    def test_minimal_html_succeeds(self):
        extractor = PharmacyExtractor("https://benu.bg/simple-product")
        extractor.load_html(MINIMAL_HTML)
        product = extractor.extract()

        assert isinstance(product, ExtractedProduct)
        assert "Simple Product" in product.title
        assert product.price_eur == "3.50"

    def test_missing_barcode_returns_empty(self):
        extractor = PharmacyExtractor("https://benu.bg/simple-product")
        extractor.load_html(MINIMAL_HTML)
        product = extractor.extract()

        assert product.barcode == ""

    def test_missing_breadcrumbs_returns_empty_categories(self):
        extractor = PharmacyExtractor("https://benu.bg/simple-product")
        extractor.load_html(MINIMAL_HTML)
        product = extractor.extract()

        assert product.category_path == []


class TestExtractFieldConsistency:
    """Cross-field consistency in the assembled product."""

    def test_product_type_matches_first_category(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        if product.category_path:
            assert product.product_type == product.category_path[0]

    def test_google_mpn_matches_sku(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.google_mpn == product.sku

    def test_published_defaults_true(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.published is True

    def test_requires_shipping_defaults_true(self):
        extractor = PharmacyExtractor("https://benu.bg/test-product")
        extractor.load_html(PRODUCT_HTML)
        product = extractor.extract()

        assert product.requires_shipping is True
