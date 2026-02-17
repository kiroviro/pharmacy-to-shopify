#!/usr/bin/env python3
"""
Demo Script - Pharmacy Product Extraction

Demonstrates the extraction capabilities without requiring credentials or real websites.
Uses sample HTML to show how the tool extracts structured product data.

Usage:
    python scripts/demo.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.pharmacy_extractor import PharmacyExtractor  # noqa: I001


# Sample HTML representing a typical pharmacy product page
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="bg">
<head>
    <title>Витамин C 1000mg таблетки - Pharmacy Demo</title>
    <meta property="og:title" content="Витамин C 1000mg таблетки">
    <meta property="og:description" content="Мощна имунна защита с витамин C">
</head>
<body>
    <nav class="breadcrumbs">
        <a href="/">Начало</a>
        <a href="/vitamini-i-dobavki">Витамини и добавки</a>
        <a href="/vitamini-i-dobavki/vitamin-c">Витамин C</a>
    </nav>

    <h1 itemprop="name">Витамин C 1000mg таблетки x 30</h1>

    <div class="product-info">
        <div class="product-prices">
            <span class="price">15.99 лв.</span>
            <span class="price-eur">8.18 €</span>
        </div>
        <div class="stock" itemprop="availability">В наличност</div>
    </div>

    <div itemprop="description">
        <h3>Основни ползи:</h3>
        <ul>
            <li>Подпомага имунната система</li>
            <li>Мощен антиоксидант</li>
            <li>Подходящ за възрастни и деца над 12 години</li>
            <li>Ежедневна защита през студените месеци</li>
        </ul>
    </div>

    <div class="product-tabs">
        <h3>Състав</h3>
        <p>Всяка таблетка съдържа: Витамин C (аскorbинова киселина) 1000mg,
        Шипка екстракт 50mg, Цинк 10mg</p>

        <h3>Дозировка и употреба</h3>
        <p>Приемайте по 1 таблетка дневно след хранене с вода.
        Не превишавайте препоръчителната дневна доза.</p>

        <h3>Противопоказания</h3>
        <p>Не приемайте при алергия към някоя от съставките.
        Консултирайте се с лекар при бременност.</p>

        <h3>Допълнителна информация</h3>
        <p>Марка: DemoPharm<br>
        Баркод: 3800123456789<br>
        Тегло: 150g<br>
        Произход: България</p>
    </div>

    <table class="additional-attributes">
        <tr>
            <th>Марка</th>
            <td>DemoPharm</td>
        </tr>
        <tr>
            <th>Форма</th>
            <td>Таблетки</td>
        </tr>
        <tr>
            <th>Количество</th>
            <td>30 бр.</td>
        </tr>
    </table>

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Витамин C 1000mg таблетки x 30",
        "brand": {
            "@type": "Brand",
            "name": "DemoPharm"
        },
        "sku": "VIT-C-1000-30",
        "gtin13": "3800123456789",
        "description": "Мощна имунна защита с витамин C",
        "offers": {
            "@type": "Offer",
            "price": "8.18",
            "priceCurrency": "EUR",
            "availability": "https://schema.org/InStock"
        },
        "image": [
            "https://demo-pharmacy.example.com/images/vitamin-c-1000mg-front.jpg",
            "https://demo-pharmacy.example.com/images/vitamin-c-1000mg-back.jpg"
        ]
    }
    </script>

    <script>
        var someConfig = {
            "initialImages": [
                {
                    "img": "https://demo-pharmacy.example.com/media/cache/product_view/vitamin-c-1000mg-front.jpg",
                    "full": "https://demo-pharmacy.example.com/images/vitamin-c-1000mg-front.jpg",
                    "thumb": "https://demo-pharmacy.example.com/media/cache/thumb/vitamin-c-1000mg-front.jpg",
                    "caption": "Витамин C 1000mg - преден изглед"
                },
                {
                    "img": "https://demo-pharmacy.example.com/media/cache/product_view/vitamin-c-1000mg-back.jpg",
                    "full": "https://demo-pharmacy.example.com/images/vitamin-c-1000mg-back.jpg",
                    "thumb": "https://demo-pharmacy.example.com/media/cache/thumb/vitamin-c-1000mg-back.jpg",
                    "caption": "Витамин C 1000mg - заден изглед"
                }
            ]
        };
    </script>
</body>
</html>
"""


def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print(f"\n{char * 70}")
    print(f" {title}")
    print(f"{char * 70}\n")


def print_field(label: str, value, indent: int = 0):
    """Print a field with label and value."""
    indent_str = "  " * indent
    if isinstance(value, list):
        print(f"{indent_str}{label}:")
        for item in value:
            print(f"{indent_str}  - {item}")
    else:
        print(f"{indent_str}{label}: {value}")


def run_demo():
    """Run the extraction demo."""
    print_section("Pharmacy Product Extraction Demo", "=")

    print("This demo shows how the tool extracts structured product data from")
    print("pharmacy websites. No credentials or real websites required!\n")

    # Initialize extractor
    print("Initializing extractor...")
    extractor = PharmacyExtractor(
        url="https://demo-pharmacy.example.com/vitamin-c-1000mg",
        site_domain="demo-pharmacy.example.com"
    )

    # Load sample HTML
    print("Loading sample product page HTML...")
    extractor.load_html(SAMPLE_HTML)

    # Extract product
    print("Extracting product data...\n")
    product = extractor.extract()

    # Display results
    print_section("Extraction Results", "=")

    print_section("Basic Information", "-")
    print_field("Title", product.title)
    print_field("Brand", product.brand)
    print_field("SKU", product.sku)
    print_field("Barcode (GTIN)", product.barcode)
    print_field("Handle (URL slug)", product.handle)

    print_section("Pricing", "-")
    print_field("Price (BGN)", f"{product.price} лв.")
    print_field("Price (EUR)", f"{product.price_eur} €")
    print_field("Availability", product.availability)

    print_section("Categories & Organization", "-")
    print_field("Category Path", product.category_path)
    print_field("Product Type", product.product_type)
    print_field("Tags", product.tags)

    print_section("Product Details", "-")
    print_field("Highlights", product.highlights)
    print_field("Composition", product.composition[:80] + "..." if product.composition else "N/A")
    print_field("Usage Instructions", product.usage[:80] + "..." if product.usage else "N/A")
    print_field("Application Form", product.application_form)
    print_field("Target Audience", product.target_audience)

    print_section("Images", "-")
    print_field("Total Images", len(product.images))
    for i, img in enumerate(product.images, 1):
        print_field(f"Image {i}", f"{img.source_url}")
        print_field("", f"Alt: {img.alt_text}", indent=1)

    print_section("SEO & Google Shopping", "-")
    print_field("SEO Title", product.seo_title)
    print_field("SEO Description", product.seo_description[:80] + "..." if product.seo_description else "N/A")
    print_field("Google Product Category", product.google_product_category)
    print_field("Google Age Group", product.google_age_group)

    print_section("Shopify Export Fields", "-")
    print_field("Published", "Yes" if product.published else "No")
    print_field("Requires Shipping", "Yes" if product.requires_shipping else "No")
    print_field("Inventory Policy", product.inventory_policy)

    print_section("Summary", "=")
    print(f"✅ Successfully extracted product: {product.title}")
    print(f"📦 Ready for Shopify import with {len(product.images)} images")
    print(f"🏷️  Categorized as: {product.product_type}")
    print(f"💰 Price: {product.price} лв. ({product.price_eur} €)")
    print(f"🔍 SEO optimized with handle: {product.handle}")

    print_section("Next Steps", "=")
    print("1. Run real extraction:")
    print("   python scripts/extract_single.py --url 'https://pharmacy.example.com/product'")
    print()
    print("2. Bulk extract products:")
    print("   python scripts/bulk_extract.py --urls data/urls.txt")
    print()
    print("3. Export to Shopify CSV:")
    print("   python scripts/export_by_brand.py --all-brands")
    print()
    print("4. Import to Shopify:")
    print("   Admin > Products > Import > Upload CSV")
    print()

    print("=" * 70)
    print(" Demo completed! Check out the README for full documentation.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        run_demo()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
