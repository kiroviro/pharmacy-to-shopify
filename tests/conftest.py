"""Shared test fixtures."""

from pathlib import Path

import pytest

from src.models import ExtractedProduct, ProductImage

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def product_page_html():
    """Load the product page HTML fixture."""
    return (FIXTURES_DIR / "product_page.html").read_text(encoding="utf-8")


@pytest.fixture
def product_jsonld():
    """Load the product JSON-LD fixture."""
    import json
    return json.loads((FIXTURES_DIR / "product_jsonld.json").read_text(encoding="utf-8"))


@pytest.fixture
def dl4objects_js():
    """Load the dl4Objects JavaScript fixture."""
    return (FIXTURES_DIR / "dl4objects.js").read_text(encoding="utf-8")


@pytest.fixture
def minimal_product():
    """Create a minimal product with only required fields."""
    return ExtractedProduct(
        title="Test Product 500mg",
        url="https://pharmacy.example.com/test-product-500mg",
        brand="TestBrand",
        sku="TST-001",
        price="12.50",
    )


@pytest.fixture
def full_product():
    """Create a fully populated product with all fields."""
    return ExtractedProduct(
        title="TestBrand Витамин C 500mg таблетки",
        url="https://pharmacy.example.com/testbrand-vitamin-c-500mg",
        brand="TestBrand",
        sku="TST-002",
        price="12.50",
        barcode="3800123456789",
        price_eur="6.39",
        original_price="15.00",
        availability="В наличност",
        category_path=["Витамини и добавки", "Витамин C"],
        highlights=["Подпомага имунната система", "Съдържа витамин С и цинк"],
        details="Витамин С е есенциален за имунната система.",
        composition="Витамин C 500mg, Цинк 10mg",
        usage="Приемайте по 1 таблетка дневно.",
        contraindications="Не приемайте при алергия.",
        more_info="Баркод: 3800123456789\nТегло: 250g",
        description="<h3>Описание</h3><p>Витамин С е есенциален.</p>",
        images=[
            ProductImage(source_url="https://pharmacy.example.com/img1.jpg", position=1, alt_text="Image 1"),
            ProductImage(source_url="https://pharmacy.example.com/img2.jpg", position=2, alt_text="Image 2"),
        ],
        handle="testbrand-vitamin-c-500mg",
        product_type="Витамини и добавки",
        tags=["Витамини и добавки", "Витамин C"],
        application_form="Таблетки",
        target_audience="Възрастни",
        weight_grams=250,
        weight_unit="kg",
        published=True,
        seo_title="TestBrand Витамин C 500mg | ViaPharma",
        seo_description="Купете TestBrand Витамин C 500mg таблетки.",
        google_product_category="Health & Beauty > Health Care",
        google_mpn="TST-002",
        google_age_group="adult",
        inventory_quantity=0,
        inventory_policy="deny",
        requires_shipping=True,
    )


@pytest.fixture
def sample_known_brands():
    """Small brand set for BrandMatcher tests."""
    return {
        "TestBrand",
        "Nivea",
        "La Roche-Posay",
        "AboPharma",
        "Nature's Way",
        "A-Derma",
        "Garnier",
    }


@pytest.fixture
def sample_categories():
    """Small category dict for config_loader tests."""
    return {
        "Козметика": ["Козметика за лице", "Козметика за тяло"],
        "Мама и бебе": ["Бебешка козметика", "Бебешка храна"],
        "Витамини и добавки": ["Витамин C", "Мултивитамини"],
    }
