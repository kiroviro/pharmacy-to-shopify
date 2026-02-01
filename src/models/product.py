"""
Product data models.

Pure data classes for representing extracted product information.
No business logic - only data structure definitions.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ProductImage:
    """Product image with metadata."""
    source_url: str
    position: int
    alt_text: str = ""


@dataclass
class ProductVariant:
    """Product variant data."""
    sku: str
    price: str
    compare_at_price: str = ""
    inventory_quantity: int = 0
    option1: str = ""
    option2: str = ""


@dataclass
class ExtractedProduct:
    """
    Complete product data per specification.

    This dataclass represents a fully extracted product,
    ready for export to Shopify CSV format.

    Field Groups:
    - Core fields: Essential product identifiers (title, url, brand, etc.)
    - Content sections: Product description tabs (details, composition, usage, etc.)
    - Images: Product gallery images
    - Variants: Product variants with pricing and inventory
    - Shopify fields: Fields specific to Shopify import (handle, tags, etc.)
    - Shipping info: Weight and shipping requirements
    - SEO: Search engine optimization fields
    - Inventory: Stock and fulfillment settings
    - Metadata: Extraction tracking information
    """

    # Core fields (required)
    title: str
    url: str
    brand: str
    sku: str
    price: str              # Price in BGN (лв.)
    barcode: str = ""       # EAN/barcode from "Допълнителна информация"
    price_eur: str = ""     # Price in EUR (€) - for Euro transition
    original_price: str = ""
    availability: str = ""
    category_path: List[str] = field(default_factory=list)

    # Content sections (from product tabs)
    highlights: List[str] = field(default_factory=list)  # Short bullet points
    details: str = ""           # "Описание" / "Какво представлява"
    composition: str = ""       # "Състав" / "Активни съставки"
    usage: str = ""             # "Начин на употреба" / "Дозировка"
    contraindications: str = "" # "Противопоказания"
    more_info: str = ""         # "Допълнителна информация"
    description: str = ""       # Combined HTML description for Shopify

    # Images (from initialImages array)
    images: List[ProductImage] = field(default_factory=list)

    # Variants (for products with options)
    variants: List[ProductVariant] = field(default_factory=list)

    # Shopify fields
    handle: str = ""            # URL slug (transliterated from title)
    product_type: str = ""      # Shopify product type
    tags: List[str] = field(default_factory=list)  # Category tags

    # Shipping info
    weight_grams: int = 0       # Weight in grams
    weight_unit: str = "kg"     # Display unit (Shopify uses kg)
    published: bool = True      # Published on storefront

    # Shopify SEO
    seo_title: str = ""         # Meta title (max 70 chars)
    seo_description: str = ""   # Meta description (max 155 chars)

    # Google Shopping
    google_product_category: str = ""  # Google taxonomy path
    google_mpn: str = ""               # Manufacturer part number (from SKU)
    google_age_group: str = ""         # "adult" or "kids"

    # Shopify Inventory
    inventory_quantity: int = 0
    inventory_policy: str = "deny"  # "deny" or "continue" selling when OOS
    requires_shipping: bool = True

    # Extraction metadata (tracks which source provided each field)
    extraction_method: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.title:
            raise ValueError("Product title is required")
        if not self.url:
            raise ValueError("Product URL is required")
